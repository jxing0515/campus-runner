"""定时任务测试：超时关闭、自动确认、异常转置、未取件爽约、告警与对账。"""
from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.common import tasks
from apps.common.models import FileAsset
from apps.finance.models import PlatformAccount
from apps.orders import services
from apps.orders.models import Order
from tests.conftest import publish, run_full_flow


def _age(order, minutes, field="created_at"):
    Order.objects.filter(pk=order.pk).update(**{field: timezone.now() - timedelta(minutes=minutes)})


def test_close_unpaid_orders(student):
    order = publish(student)
    _age(order, 31)
    assert tasks.close_unpaid_orders() == 1
    order.refresh_from_db()
    assert order.status == Order.Status.CANCELLED
    assert order.settle_status == Order.SettleStatus.NONE


def test_close_unaccepted_orders_refunds(student):
    order = publish(student)
    services.pay(student, order.order_no)
    _age(order, 61)
    result = tasks.close_unaccepted_orders()
    assert result["closed"] == 1
    order.refresh_from_db()
    assert order.status == Order.Status.CANCELLED
    assert order.settle_status == Order.SettleStatus.REFUNDED
    assert PlatformAccount.load().escrow_total == Decimal("0.00")
    assert tasks.reconcile()["passed"] is True


def test_auto_confirm_with_evidence(student, runner):
    no = run_full_flow(student, runner)
    order = Order.objects.get(order_no=no)
    evidence = FileAsset.objects.create(
        file=SimpleUploadedFile("d.png", b"\x89PNG\r\n\x1a\n"), name="d.png",
        kind=FileAsset.Kind.EVIDENCE, uploader=runner, size=8,
    )
    Order.objects.filter(pk=order.pk).update(deliver_file=evidence)
    _age(order, 1441, "deliver_at")
    result = tasks.auto_confirm_orders()
    assert result["confirmed"] == 1
    order.refresh_from_db()
    runner.refresh_from_db()
    assert order.status == Order.Status.COMPLETED
    assert runner.runner_balance == Decimal("10.00")


def test_auto_confirm_without_evidence_goes_abnormal(student, runner):
    no = run_full_flow(student, runner)
    order = Order.objects.get(order_no=no)
    Order.objects.filter(pk=order.pk).update(deliver_file=None)
    _age(order, 1441, "deliver_at")
    result = tasks.auto_confirm_orders()
    assert result["abnormal"] == 1
    order.refresh_from_db()
    assert order.status == Order.Status.ABNORMAL
    assert PlatformAccount.load().escrow_total == Decimal("10.00")  # 资金冻结在托管
    runner.refresh_from_db()
    assert runner.runner_balance == Decimal("0.00")


def test_no_pickup_warn_then_cancel_with_penalty(student, runner):
    order = publish(student)
    services.pay(student, order.order_no)
    services.accept(runner, order.order_no)
    Order.objects.filter(pk=order.pk).update(accept_at=timezone.now() - timedelta(minutes=35))
    assert tasks.cancel_no_pickup_orders()["warned"] == 1

    Order.objects.filter(pk=order.pk).update(accept_at=timezone.now() - timedelta(minutes=65))
    before = runner.credit_score
    assert tasks.cancel_no_pickup_orders()["closed"] == 1
    order.refresh_from_db()
    runner.refresh_from_db()
    assert order.status == Order.Status.CANCELLED
    assert runner.credit_score == before - 10  # 爽约 -10
    assert order.settle_status == Order.SettleStatus.REFUNDED
    assert tasks.reconcile()["passed"] is True


def test_escrow_alert_and_run_all(student, runner):
    order = publish(student)
    services.pay(student, order.order_no)
    Order.objects.filter(pk=order.pk).update(paid_at=timezone.now() - timedelta(days=8))
    alert = tasks.escrow_alert()
    assert alert["stale_orders"] >= 1

    result = tasks.run_all(include_daily=True)
    assert "reconcile" in result and result["reconcile"]["passed"] is True
    # 幂等：重复扫描不产生副作用
    assert tasks.close_unaccepted_orders()["closed"] == 0
