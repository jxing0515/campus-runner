"""资金闭环测试：托管、结算、差额退款、提现冻结与对账恒等式。"""
from decimal import Decimal

from django.db.models import Sum

from apps.accounts.models import User
from apps.common.tasks import reconcile
from apps.finance import services as finance
from apps.finance.models import FundFlow, PlatformAccount, Withdrawal
from apps.orders import services
from apps.orders.models import Order
from tests.conftest import client_for, order_payload, publish, run_full_flow


def test_pay_escrow_and_settle_with_difference(student, runner):
    no = run_full_flow(student, runner, mode="platform", fee="10.00", estimate="20.00", actual="12.00")
    order = Order.objects.get(order_no=no)
    # 托管 = 跑腿费 10 + 预估物品费 20
    assert finance.escrow_amount(order) == Decimal("30.00")
    assert PlatformAccount.load().escrow_total == Decimal("30.00")

    services.confirm(student, no)
    runner.refresh_from_db()
    order.refresh_from_db()
    # 最终酬金 = 10 + min(12, 20) = 22；差额 8 退回学生
    assert order.final_reward == Decimal("22.00")
    assert runner.runner_balance == Decimal("22.00")
    assert PlatformAccount.load().escrow_total == Decimal("0.00")
    refund = FundFlow.objects.get(order=order, type=FundFlow.Type.REFUND)
    assert refund.amount == Decimal("8.00")
    assert finance.account_escrow_total() == Decimal("0.00")
    assert reconcile()["passed"] is True


def test_actual_above_estimate_is_capped(student, runner):
    no = run_full_flow(student, runner, mode="platform", fee="10.00", estimate="20.00", actual="35.00")
    services.confirm(student, no)
    runner.refresh_from_db()
    assert runner.runner_balance == Decimal("30.00")  # 10 + min(35, 20)


def test_offline_mode_item_fee_not_settled(student, runner):
    no = run_full_flow(student, runner, mode="offline", fee="8.00")
    order = Order.objects.get(order_no=no)
    assert finance.escrow_amount(order) == Decimal("8.00")
    services.confirm(student, no)
    runner.refresh_from_db()
    assert runner.runner_balance == Decimal("8.00")


def test_withdrawal_freeze_approve_and_reject(student, runner):
    no = run_full_flow(student, runner, fee="30.00")
    services.confirm(student, no)
    runner.refresh_from_db()
    assert runner.runner_balance == Decimal("30.00")

    # 申请即冻结
    first = finance.apply_withdrawal(runner, Decimal("20.00"), "模拟收款", "acc-1")
    runner.refresh_from_db()
    assert runner.runner_balance == Decimal("10.00")
    assert first.status == Withdrawal.Status.PENDING
    assert FundFlow.objects.get(idem_key=f"withdraw:{first.pk}").status == FundFlow.Status.FROZEN

    # 余额不足时二次提现被拒（防双花）
    try:
        finance.apply_withdrawal(runner, Decimal("15.00"), "模拟收款", "acc-1")
        raise AssertionError("应因余额不足被拒绝")
    except Exception as exc:
        assert "余额不足" in str(exc)

    finance.audit_withdrawal(first, False, "账号不符", runner)
    runner.refresh_from_db()
    assert runner.runner_balance == Decimal("30.00")
    assert FundFlow.objects.get(idem_key=f"withdraw:{first.pk}").status == FundFlow.Status.RETURNED

    second = finance.apply_withdrawal(runner, Decimal("10.00"), "模拟收款", "acc-2")
    finance.audit_withdrawal(second, True, "", runner)
    runner.refresh_from_db()
    assert runner.runner_balance == Decimal("20.00")
    assert FundFlow.objects.get(idem_key=f"withdraw:{second.pk}").status == FundFlow.Status.PAID_OUT
    assert runner.runner_balance >= 0
    assert reconcile()["passed"] is True


def test_withdraw_api_does_not_allow_overdraw(student, runner):
    no = run_full_flow(student, runner, fee="5.00")
    services.confirm(student, no)
    resp = client_for(runner).post("/api/v1/runner/withdrawals", {"amount": "100.00", "account": "acc"}, format="json")
    assert resp.status_code == 400 and "余额" in resp.json()["message"]


def test_reconcile_detects_tampering(student, runner):
    no = run_full_flow(student, runner, fee="10.00")
    services.confirm(student, no)
    assert reconcile()["passed"] is True
    User.objects.filter(pk=runner.pk).update(runner_balance=Decimal("999.00"))  # 人为改余额
    result = reconcile()
    assert result["passed"] is False and result["failed"]


def test_zero_item_fee_order_rejected(student):
    """平台代付但未填物品预估费 → 参数错误（由序列化器收口）。"""
    resp = client_for(student).post("/api/v1/orders", order_payload(mode="platform", fee="10.00", estimate="0.00"), format="json")
    assert resp.status_code == 400 and resp.json()["code"] == 40001
