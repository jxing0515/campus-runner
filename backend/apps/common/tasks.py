"""定时任务：超时处理、自动确认、信用恢复、托管清理、每日对账。

由 `manage.py beat` 循环驱动（也可单个命令交给系统 cron/schtasks），
无 Redis/Celery 依赖：互斥锁走缓存 add()，幂等靠状态前置条件。
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from apps.common import rules
from apps.common.locks import task_lock
from apps.common.models import Notification, OperationLog
from apps.common.notify import notify, notify_admins
from apps.common.notify import notify_many
from apps.finance.models import FundFlow, PlatformAccount
from apps.finance import services as finance
from apps.orders import services as order_services
from apps.orders.models import Appeal, Order

S = Order.Status


def _remind_once(order, title, content):
    if Notification.objects.filter(order_no=order.order_no, title=title).exists():
        return False
    notify_many([order.student], title, content)
    return True


def close_unpaid_orders():
    """超时未支付：自动关闭（未支付无退款）。"""
    limit = timezone.now() - timedelta(minutes=int(rules.get_rule("timeout_pay_minutes")))
    closed = 0
    for order in Order.objects.filter(status=S.PENDING_PAY, created_at__lt=limit):
        with task_lock(f"unpaid:{order.pk}"):
            order.refresh_from_db()
            if order.status != S.PENDING_PAY:
                continue
            order.cancel_reason = "超时未支付，系统自动关闭"
            order.save(update_fields=["cancel_reason", "updated_at"])
            from apps.orders import state

            state.transition(order, S.CANCELLED, None, "超时未支付自动关闭")
            notify(order.student, "订单已关闭", f"订单 {order.order_no} 超时未支付，已自动关闭", order_no=order.order_no)
            closed += 1
    return closed


def close_unaccepted_orders():
    """超时未接单：先提醒，仍无人接则关闭并全额退款。"""
    timeout = int(rules.get_rule("timeout_accept_minutes"))
    warn_at = timezone.now() - timedelta(minutes=timeout // 2)
    close_at = timezone.now() - timedelta(minutes=timeout)
    warned = 0
    for order in Order.objects.filter(status=S.PENDING_ACCEPT, created_at__lt=warn_at):
        if _remind_once(order, "订单超时未接单提醒", f"订单 {order.order_no} 尚未有人接单，可撤销并全额退款"):
            warned += 1
    closed = 0
    for order in Order.objects.filter(status=S.PENDING_ACCEPT, created_at__lt=close_at):
        with task_lock(f"unaccepted:{order.pk}"):
            order.refresh_from_db()
            if order.status != S.PENDING_ACCEPT:
                continue
            finance.refund_order(order, None, "超时未接单，系统自动关闭并全额退款")
            order.refresh_from_db()
            order.cancel_reason = "超时未接单，系统自动关闭"
            order.save(update_fields=["cancel_reason", "updated_at"])
            from apps.orders import state

            state.transition(order, S.CANCELLED, None, "超时未接单自动关闭")
            notify(order.student, "订单已关闭", f"订单 {order.order_no} 超时未接单，已全额退款（模拟）", order_no=order.order_no)
            closed += 1
    return {"warned": warned, "closed": closed}


def auto_confirm_orders():
    """学生超时未确认：有送达凭证 → 自动确认结算；无凭证 → 转异常冻结托管。"""
    limit = timezone.now() - timedelta(minutes=int(rules.get_rule("timeout_confirm_minutes")))
    confirmed, abnormal = 0, 0
    for order in Order.objects.filter(status=S.PENDING_CONFIRM, deliver_at__lt=limit):
        with task_lock(f"confirm:{order.pk}"):
            order.refresh_from_db()
            if order.status != S.PENDING_CONFIRM:
                continue
            from apps.orders import state

            if order.deliver_file_id or int(rules.get_rule("auto_confirm_after_deliver")) == 0:
                finance.settle_order(order, suffix="auto")
                order.refresh_from_db()
                state.transition(order, S.COMPLETED, None, "超时自动确认并结算")
                order.completed_at = timezone.now()
                order.save(update_fields=["completed_at", "updated_at"])
                notify(order.student, "订单自动确认", f"订单 {order.order_no} 超时未确认，已自动结算", order_no=order.order_no)
                if order.runner_id:
                    notify(order.runner, "订单自动确认", f"订单 {order.order_no} 已自动结算（模拟）", order_no=order.order_no)
                confirmed += 1
            else:
                state.transition(order, S.ABNORMAL, None, "超时未确认且无送达凭证，转异常")
                notify(order.student, "订单转异常", f"订单 {order.order_no} 无送达凭证，已转人工处理", order_no=order.order_no)
                notify_admins("异常订单待处理", f"订单 {order.order_no} 超时未确认且无送达凭证，资金冻结托管")
                abnormal += 1
    return {"confirmed": confirmed, "abnormal": abnormal}


def cancel_no_pickup_orders():
    """跑腿员超时未取件：先提醒；仍无操作 → 取消 + 全额退款 + 爽约 -10。"""
    warn_minutes = int(rules.get_rule("timeout_pickup_warn_minutes"))
    cancel_minutes = int(rules.get_rule("timeout_pickup_cancel_minutes"))
    warn_before = timezone.now() - timedelta(minutes=warn_minutes)
    cancel_before = timezone.now() - timedelta(minutes=cancel_minutes)
    warned, closed = 0, 0
    active = Order.objects.filter(status__in=[S.ACCEPTED, S.PICKED], accept_at__isnull=False)
    for order in active.filter(accept_at__lt=warn_before, no_show_warned_at__isnull=True):
        notify(order.runner, "取件超时提醒", f"订单 {order.order_no} 尚未取件打卡，请尽快处理", order_no=order.order_no)
        order.no_show_warned_at = timezone.now()
        order.save(update_fields=["no_show_warned_at", "updated_at"])
        warned += 1
    for order in active.filter(accept_at__lt=cancel_before):
        with task_lock(f"nopickup:{order.pk}"):
            order.refresh_from_db()
            if order.status not in (S.ACCEPTED, S.PICKED):
                continue
            finance.refund_order(order, None, "跑腿员超时未取件，系统取消并全额退款")
            order.refresh_from_db()
            order.cancel_reason = "跑腿员超时未取件"
            order.save(update_fields=["cancel_reason", "updated_at"])
            from apps.orders import state

            state.transition(order, S.CANCELLED, None, "跑腿员超时未取件，系统取消")
            from apps.credit import services as credit_services

            if order.runner_id:
                runner = order.runner
                credit_services.on_no_show(runner, order, "跑腿员超时未取件")
                notify(runner, "订单被取消", f"订单 {order.order_no} 因超时未取件被取消，爽约 -10 信用分", order_no=order.order_no)
            notify(order.student, "订单已取消", f"订单 {order.order_no} 跑腿员超时未取件，已全额退款（模拟）", order_no=order.order_no)
            closed += 1
    return {"warned": warned, "closed": closed}


def credit_period_recover():
    from apps.credit import services as credit_services

    return credit_services.period_recover()


def escrow_alert():
    """托管超期 / 申诉超期未裁 → 通知管理员（人工处理路径）。"""
    days = int(rules.get_rule("escrow_alert_days"))
    before = timezone.now() - timedelta(days=days)
    stale_paid = Order.objects.filter(status__in=[S.PENDING_ACCEPT, S.ACCEPTED, S.PICKED, S.DELIVERING], paid_at__lt=before).count()
    stale_appeal = Appeal.objects.filter(status__in=[Appeal.Status.PENDING, Appeal.Status.PROCESSING], created_at__lt=before).count()
    if stale_paid or stale_appeal:
        notify_admins("托管/仲裁超期告警", f"托管超 {days} 天订单 {stale_paid} 笔；申诉超期未裁 {stale_appeal} 笔", super_only=False)
    return {"stale_orders": stale_paid, "stale_appeals": stale_appeal}


def reconcile():
    """每日对账：三处恒等式校验，不一致则紧急通知 super_admin 并落操作日志。"""
    account = PlatformAccount.load()
    escrow_in_flows = finance.account_escrow_total()
    settled = finance.money(FundFlow.objects.filter(type=FundFlow.Type.SETTLE).aggregate(s=Sum("amount"))["s"])
    refunded = finance.money(FundFlow.objects.filter(type=FundFlow.Type.REFUND).aggregate(s=Sum("amount"))["s"])
    paid = finance.money(FundFlow.objects.filter(type=FundFlow.Type.PAY).aggregate(s=Sum("amount"))["s"])
    frozen = finance.money(
        FundFlow.objects.filter(type=FundFlow.Type.WITHDRAW, status=FundFlow.Status.FROZEN).aggregate(s=Sum("amount"))["s"]
    )
    paid_out = finance.money(
        FundFlow.objects.filter(type=FundFlow.Type.WITHDRAW, status=FundFlow.Status.PAID_OUT).aggregate(s=Sum("amount"))["s"]
    )
    from apps.accounts.models import User

    balance_total = finance.money(User.objects.filter(role=User.Role.USER).aggregate(s=Sum("runner_balance"))["s"])
    checks = [
        ("托管账户余额 ≡ Σ托管中流水", finance.money(account.escrow_total) == escrow_in_flows),
        ("Σ结算+Σ退款 ≤ Σ托管入账", settled + refunded <= paid),
        ("Σ结算-已出账提现-冻结提现 ≡ Σ用户可提现余额", settled - paid_out - frozen == balance_total),
    ]
    failed = [name for name, ok in checks if not ok]
    detail = "; ".join(f"{name}={'通过' if ok else '不一致'}" for name, ok in checks)
    OperationLog.objects.create(operator=None, module="对账", action="每日资金对账", detail=detail)
    if failed:
        notify_admins("对账不一致告警", "；".join(failed), super_only=True)
    return {"passed": not failed, "failed": failed, "detail": detail}


TASKS = {
    "unpaid": (close_unpaid_orders, "订单超时未支付", "timeout_pay_minutes"),
    "unaccepted": (close_unaccepted_orders, "订单超时未接单", "timeout_accept_minutes"),
    "unconfirmed": (auto_confirm_orders, "学生超时未确认", "timeout_confirm_minutes"),
    "no_pickup": (cancel_no_pickup_orders, "跑腿员超时未取件", "timeout_pickup_warn_minutes"),
}


def run_all(include_daily=False):
    """扫描频率内执行全部高频任务；daily 任务单独按日触发。"""
    result = {}
    for key, (func, _label, _rule) in TASKS.items():
        with task_lock(f"task:{key}", timeout=120) as acquired:
            if not acquired:
                result[key] = "skipped(locked)"
                continue
            try:
                result[key] = func()
            except Exception as exc:  # 失败退避重试一次，仍失败记录日志
                for _ in range(2):
                    try:
                        result[key] = func()
                        break
                    except Exception as exc2:
                        exc = exc2
                else:
                    OperationLog.objects.create(operator=None, module="定时任务", action=key, detail=f"执行失败：{exc}")
                    result[key] = f"error:{exc}"
    if include_daily:
        result["recover"] = credit_period_recover()
        result["escrow_alert"] = escrow_alert()
        result["reconcile"] = reconcile()
    return result
