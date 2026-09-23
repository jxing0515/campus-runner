"""订单状态机：合法迁移表统一收口，禁止前端直改状态。"""
from django.utils import timezone

from apps.common.errors import conflict
from apps.orders.models import Order, OrderStatusLog

S = Order.Status

# 合法迁移表（原状态 → 新状态）
TRANSITIONS = {
    (S.PENDING_PAY, S.PENDING_ACCEPT),
    (S.PENDING_PAY, S.CANCELLED),
    (S.PENDING_ACCEPT, S.ACCEPTED),
    (S.PENDING_ACCEPT, S.CANCELLED),
    (S.ACCEPTED, S.PICKED),
    (S.ACCEPTED, S.DELIVERING),
    (S.ACCEPTED, S.CANCELLED),
    (S.PICKED, S.DELIVERING),
    (S.PICKED, S.CANCELLED),
    (S.DELIVERING, S.PENDING_CONFIRM),
    (S.PENDING_CONFIRM, S.COMPLETED),
    (S.PENDING_CONFIRM, S.ABNORMAL),
    (S.PENDING_CONFIRM, S.APPEALING),
    (S.COMPLETED, S.APPEALING),
    (S.APPEALING, S.COMPLETED),
    (S.APPEALING, S.REFUNDED),
    (S.APPEALING, S.CANCELLED),
    (S.ABNORMAL, S.COMPLETED),
    (S.ABNORMAL, S.CANCELLED),
    (S.ABNORMAL, S.REFUNDED),
}

BUSINESS_STATES = {S.PENDING_PAY, S.PENDING_ACCEPT, S.ACCEPTED, S.PICKED, S.DELIVERING, S.PENDING_CONFIRM, S.COMPLETED}
PLACEHOLDERS = {S.APPEALING, S.ABNORMAL}
FINAL_STATES = {S.COMPLETED, S.CANCELLED, S.REFUNDED}


def can_transition(from_status, to_status):
    return (from_status, to_status) in TRANSITIONS


def transition(order, to_status, operator=None, remark="", save=True):
    """校验并执行一次状态迁移，同时写订单状态日志表。"""
    from_status = order.status
    if from_status == to_status:
        return order
    if not can_transition(from_status, to_status):
        raise conflict(f"非法状态流转：{Order.Status(from_status).label} → {Order.Status(to_status).label}")
    if to_status in PLACEHOLDERS:
        order.prev_status = from_status
    elif from_status in PLACEHOLDERS:
        order.prev_status = ""
    order.status = to_status
    if save:
        order.save(update_fields=["status", "prev_status", "updated_at"])
    OrderStatusLog.objects.create(
        order=order, from_status=from_status, to_status=to_status, operator=operator, remark=remark[:200]
    )
    return order


def log(order, from_status, to_status, operator=None, remark=""):
    """不改变状态，仅补一条审计日志（如退款/结算类附注）。"""
    return OrderStatusLog.objects.create(
        order=order, from_status=from_status, to_status=to_status, operator=operator, remark=remark[:200]
    )


def cancel_policy(order):
    """取消矩阵：返回 (学生可取消, 跑腿员可取消, 说明)。"""
    status = order.status
    prepaid = order.prepaid
    if status == S.PENDING_PAY:
        return True, False, "未支付直接关闭，无退款"
    if status == S.PENDING_ACCEPT:
        return True, False, "全额退款"
    if status in (S.ACCEPTED, S.PICKED):
        if prepaid and order.item_fee_mode == Order.ItemFeeMode.PLATFORM:
            return False, False, "已垫付，需转仲裁裁定退款额"
        return True, True, "未垫付，可取消并全额退款；跑腿员弃单爽约 -10"
    return False, False, "配送中/待确认不支持取消，只能等待确认或申诉"


def deadline(now=None):
    return now or timezone.now()
