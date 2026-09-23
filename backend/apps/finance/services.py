"""资金闭环：支付→托管→结算/退款→提现，全程模拟记账，无真实资金。"""
import random
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.common.errors import BizError, conflict
from apps.finance.models import FundFlow, PlatformAccount, Withdrawal
from apps.orders.models import Order

CENT = Decimal("0.01")
CHANNEL = "平台模拟"


def money(value):
    return Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP)


def gen_no(prefix=""):
    return f"{prefix}{timezone.localtime():%Y%m%d}{random.randint(0, 99999999):08d}"


def _new_flow(**kwargs):
    for _ in range(3):
        kwargs.setdefault("flow_no", gen_no("FL"))
        kwargs.setdefault("external_no", gen_no("SIM"))
        try:
            return FundFlow.objects.create(**kwargs)
        except Exception:
            kwargs.pop("flow_no", None)
            kwargs.pop("external_no", None)
    raise BizError("流水号冲突，请重试", code=50000)


def escrow_amount(order):
    """托管金额 = 跑腿费（+ 代付模式物品预估费）。"""
    if order.item_fee_mode == Order.ItemFeeMode.PLATFORM:
        return money(order.runner_fee) + money(order.item_fee_estimate)
    return money(order.runner_fee)


def final_reward(order):
    """最终酬金 = 跑腿费 + min(实际物品费, 物品预估费)（仅平台代付模式计入物品费）。"""
    reward = money(order.runner_fee)
    if order.item_fee_mode == Order.ItemFeeMode.PLATFORM:
        reward += min(money(order.actual_item_fee), money(order.item_fee_estimate))
    return reward


def account_escrow_total():
    """Σ 托管中流水。"""
    return money(
        FundFlow.objects.filter(type=FundFlow.Type.ESCROW, status=FundFlow.Status.ESCROWED).aggregate(s=Sum("amount"))["s"]
    )


def account_balance_total():
    """Σ 用户可提现余额（对账用）。"""
    return money(User.objects.filter(role=User.Role.USER).aggregate(s=Sum("runner_balance"))["s"])


@transaction.atomic
def pay_order(order, idem_key=None):
    """模拟支付：学生出账 → 平台托管；重复请求直接返回既有结果（幂等）。"""
    order = Order.objects.select_for_update().get(pk=order.pk)
    idem = idem_key or f"pay:{order.order_no}"
    existing = FundFlow.objects.filter(idem_key=idem).first()
    if existing:
        return existing
    if order.status != Order.Status.PENDING_PAY:
        raise conflict(f"订单当前状态为 {order.get_status_display()}，不可支付")
    amount = escrow_amount(order)
    if amount <= 0:
        raise BizError("订单金额非法")
    account = PlatformAccount.load(for_update=True)
    account.escrow_total = money(account.escrow_total) + amount
    account.total_paid = money(account.total_paid) + amount
    account.save(update_fields=["escrow_total", "total_paid", "updated_at"])
    _new_flow(
        order=order, user=order.student, amount=amount, direction=FundFlow.Direction.IN,
        type=FundFlow.Type.PAY, status=FundFlow.Status.PAID,
        runner_fee_part=money(order.runner_fee), item_fee_part=amount - money(order.runner_fee),
        balance_after=account.escrow_total, idem_key=idem, remark="模拟支付",
    )
    return _new_flow(
        order=order, user=order.student, amount=amount, direction=FundFlow.Direction.IN,
        type=FundFlow.Type.ESCROW, status=FundFlow.Status.ESCROWED,
        runner_fee_part=money(order.runner_fee), item_fee_part=amount - money(order.runner_fee),
        balance_after=account.escrow_total, idem_key=f"escrow:{order.order_no}", remark="进入平台托管",
    )


def _close_escrow(order, status):
    FundFlow.objects.filter(order=order, type=FundFlow.Type.ESCROW, status=FundFlow.Status.ESCROWED).update(status=status)


@transaction.atomic
def payout(order, reward, refund_amount, suffix, settle_status, remark=""):
    """托管出账：按比例分别结算给跑腿员、退回学生；托管全额清零并收口。"""
    order = Order.objects.select_for_update().get(pk=order.pk)
    escrow = escrow_amount(order)
    reward = min(money(reward), escrow)
    refund_amount = min(money(refund_amount), escrow - reward)
    account = PlatformAccount.load(for_update=True)
    account.escrow_total = max(money(account.escrow_total) - (reward + refund_amount), Decimal("0.00"))
    runner = None
    if reward > 0:
        if order.runner_id is None:
            raise BizError("订单尚无跑腿员，无法结算")
        runner = User.objects.select_for_update().get(pk=order.runner_id)
        runner.runner_balance = money(runner.runner_balance) + reward
        runner.completed_count += 1
        runner.save(update_fields=["runner_balance", "completed_count", "updated_at"])
        account.total_settled = money(account.total_settled) + reward
        _new_flow(
            order=order, user=runner, amount=reward, direction=FundFlow.Direction.OUT,
            type=FundFlow.Type.SETTLE, status=FundFlow.Status.SETTLED,
            runner_fee_part=min(money(order.runner_fee), reward),
            item_fee_part=max(reward - money(order.runner_fee), Decimal("0.00")),
            balance_after=runner.runner_balance, idem_key=f"settle:{order.order_no}:{suffix}",
            remark=remark or "结算入跑腿员余额",
        )
    if refund_amount > 0:
        account.total_refunded = money(account.total_refunded) + refund_amount
        _new_flow(
            order=order, user=order.student, amount=refund_amount, direction=FundFlow.Direction.OUT,
            type=FundFlow.Type.REFUND, status=FundFlow.Status.REFUNDED,
            runner_fee_part=Decimal("0.00"), item_fee_part=refund_amount,
            balance_after=account.escrow_total, idem_key=f"refund:{order.order_no}:{suffix}",
            remark=remark or "退回学生（模拟出账）",
        )
    account.save(update_fields=["escrow_total", "total_settled", "total_refunded", "updated_at"])
    _close_escrow(order, FundFlow.Status.SETTLED if reward > 0 else FundFlow.Status.REFUNDED)
    order.final_reward = reward
    order.settle_status = settle_status
    order.save(update_fields=["final_reward", "settle_status", "updated_at"])
    return order, runner


@transaction.atomic
def settle_order(order, suffix="full"):
    """正常结算（含代付差额退回学生）。重复调用幂等。"""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if FundFlow.objects.filter(idem_key=f"settle:{order.order_no}:{suffix}").exists():
        return order
    escrow = escrow_amount(order)
    reward = final_reward(order)
    order, runner = payout(order, reward, escrow - reward, suffix, Order.SettleStatus.SETTLED)
    from apps.credit import services as credit_services

    for user in filter(None, [User.objects.filter(pk=order.student_id).first(), runner]):
        credit_services.on_order_complete(user, order)
    return order


@transaction.atomic
def refund_order(order, amount=None, reason="退款", suffix="full"):
    """退款：托管出账冲销（学生侧无钱包，不产生真实资金）。"""
    order = Order.objects.select_for_update().get(pk=order.pk)
    if FundFlow.objects.filter(idem_key=f"refund:{order.order_no}:{suffix}").exists():
        return order
    amount = escrow_amount(order) if amount is None else money(amount)
    if amount <= 0:
        return order
    order, _ = payout(order, Decimal("0.00"), amount, suffix, Order.SettleStatus.REFUNDED)
    return order


@transaction.atomic
def apply_withdrawal(runner, amount, method, account):
    """提现申请：申请即扣减冻结，防双花。"""
    amount = money(amount)
    if amount <= 0:
        raise BizError("提现金额必须大于 0")
    runner = User.objects.select_for_update().get(pk=runner.pk)
    if not runner.is_runner:
        raise BizError("仅认证跑腿员可提现", code=40300, http_status=403)
    if money(runner.runner_balance) < amount:
        raise BizError("可提现余额不足")
    before = money(runner.runner_balance)
    runner.runner_balance = before - amount
    runner.save(update_fields=["runner_balance", "updated_at"])
    wd = Withdrawal.objects.create(
        runner=runner, amount=amount, balance_before=before, balance_after=runner.runner_balance,
        method=method, account=account,
    )
    flow = _new_flow(
        user=runner, withdrawal=wd, amount=amount, direction=FundFlow.Direction.OUT,
        type=FundFlow.Type.WITHDRAW, status=FundFlow.Status.FROZEN,
        balance_after=runner.runner_balance, idem_key=f"withdraw:{wd.pk}", remark="提现申请冻结",
    )
    wd.flow_no = flow.flow_no
    wd.save(update_fields=["flow_no", "updated_at"])
    return wd


@transaction.atomic
def audit_withdrawal(wd, approve, reason="", handler=None):
    wd = Withdrawal.objects.select_for_update().get(pk=wd.pk)
    if wd.status != Withdrawal.Status.PENDING:
        raise conflict("该提现已处理")
    runner = User.objects.select_for_update().get(pk=wd.runner_id)
    if approve:
        FundFlow.objects.filter(idem_key=f"withdraw:{wd.pk}").update(status=FundFlow.Status.PAID_OUT)
        wd.status = Withdrawal.Status.APPROVED
    else:
        runner.runner_balance = money(runner.runner_balance) + money(wd.amount)
        runner.save(update_fields=["runner_balance", "updated_at"])
        FundFlow.objects.filter(idem_key=f"withdraw:{wd.pk}").update(status=FundFlow.Status.RETURNED)
        _new_flow(
            user=runner, withdrawal=wd, amount=money(wd.amount), direction=FundFlow.Direction.IN,
            type=FundFlow.Type.WITHDRAW_RETURN, status=FundFlow.Status.RETURNED,
            balance_after=runner.runner_balance, idem_key=f"withdraw-return:{wd.pk}",
            remark=f"提现驳回退回：{reason}",
        )
        wd.status = Withdrawal.Status.REJECTED
        wd.reject_reason = reason
    wd.handler = handler
    wd.handled_at = timezone.now()
    wd.save(update_fields=["status", "reject_reason", "handler", "handled_at", "updated_at"])
    return wd
