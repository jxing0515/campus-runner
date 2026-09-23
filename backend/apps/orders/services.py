"""订单业务：发布/支付/接单/打卡/确认/取消/评价/申诉/仲裁/异常处理。"""
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.common import rules
from apps.common.errors import BizError, conflict
from apps.common.models import FileAsset
from apps.common.notify import notify, notify_admins
from apps.credit import services as credit_services
from apps.finance import services as finance
from apps.orders import state
from apps.orders.models import Appeal, Order, Review

S = Order.Status


def minutes(value):
    return timezone.now() + timedelta(minutes=int(value))


def new_order_no():
    for _ in range(3):
        no = finance.gen_no()
        if not Order.objects.filter(order_no=no).exists():
            return no
    raise BizError("订单号生成失败，请重试", code=50000)


def get_order(order_no):
    order = Order.objects.filter(order_no=order_no).first()
    if order is None:
        raise BizError("订单不存在", code=40400, http_status=404)
    return order


def _file(file_id, kind=FileAsset.Kind.EVIDENCE):
    if not file_id:
        return None
    asset = FileAsset.objects.filter(pk=file_id).first()
    if asset is None:
        raise BizError("凭证文件不存在", code=40400, http_status=404)
    return asset


def _assert_participant(order, user):
    if user.id not in (order.student_id, order.runner_id) and not user.is_admin:
        raise BizError("无权操作该订单", code=40300, http_status=403)


@transaction.atomic
def create_order(student, data):
    limits = credit_services.limits_of(student)
    if not limits["can_publish"]:
        raise BizError(f"信用等级为{limits['level_label']}，暂不可发布新单", code=40300, http_status=403)
    mode = data.get("item_fee_mode") or Order.ItemFeeMode.NONE
    if mode == Order.ItemFeeMode.PLATFORM and not limits["can_prepay"]:
        raise BizError(f"信用等级为{limits['level_label']}，不可使用平台代付", code=40300, http_status=403)
    if data["time_window_start"] >= data["time_window_end"]:
        raise BizError("时间窗口不合法：开始时间需早于结束时间")
    if finance.money(data["runner_fee"]) <= 0:
        raise BizError("跑腿费必须大于 0")
    if mode != Order.ItemFeeMode.PLATFORM:
        data["item_fee_estimate"] = Decimal("0.00")
    return Order.objects.create(order_no=new_order_no(), student=student, status=S.PENDING_PAY, **data)


@transaction.atomic
def pay(user, order_no, idem_key=None):
    order = Order.objects.select_for_update().filter(order_no=order_no).first()
    if order is None:
        raise BizError("订单不存在", code=40400, http_status=404)
    if order.student_id != user.id:
        raise BizError("只能支付自己发布的订单", code=40300, http_status=403)
    finance.pay_order(order, idem_key)
    order.refresh_from_db()
    if order.status == S.PENDING_PAY:
        state.transition(order, S.PENDING_ACCEPT, user, "模拟支付成功，资金进入托管")
        order.paid_at = timezone.now()
        order.save(update_fields=["paid_at", "updated_at"])
    notify(user, "支付成功", f"订单 {order.order_no} 已进入托管，等待跑腿员接单", order_no=order.order_no)
    return order


@transaction.atomic
def accept(runner, order_no):
    if not runner.is_runner:
        raise BizError("请先通过跑腿员认证", code=40300, http_status=403)
    limits = credit_services.limits_of(runner)
    if not limits["can_accept"]:
        raise BizError(f"信用等级为{limits['level_label']}，暂不可接单", code=40300, http_status=403)
    order = get_order(order_no)
    if order.student_id == runner.id:
        raise BizError("不能接自己发布的订单", code=40001)
    now = timezone.now()
    # 原子抢占：一单仅一人成功
    updated = Order.objects.filter(pk=order.pk, status=S.PENDING_ACCEPT, runner__isnull=True).update(
        runner=runner, status=S.ACCEPTED, accept_at=now, updated_at=now
    )
    if not updated:
        order.refresh_from_db()
        raise conflict("订单已被他人接单或状态已变更")
    state.log(order, S.PENDING_ACCEPT, S.ACCEPTED, runner, "跑腿员接单")
    order.refresh_from_db()
    notify(order.student, "订单已被接单", f"跑腿员已接受订单 {order.order_no}", order_no=order.order_no)
    return order


@transaction.atomic
def pickup(runner, order_no, file_id=None):
    order = Order.objects.select_for_update().filter(order_no=order_no).first()
    if order is None:
        raise BizError("订单不存在", code=40400, http_status=404)
    if order.runner_id != runner.id:
        raise BizError("仅接单跑腿员可打卡", code=40300, http_status=403)
    if order.status not in (S.ACCEPTED, S.PICKED):
        raise conflict(f"订单当前状态为 {order.get_status_display()}，不可取件打卡")
    order.pickup_at = timezone.now()
    order.pickup_file = _file(file_id)
    if order.item_fee_mode == Order.ItemFeeMode.PLATFORM:
        order.prepaid = True  # 代付模式取件即垫付物品费
    order.save(update_fields=["pickup_at", "pickup_file", "prepaid", "updated_at"])
    state.transition(order, S.DELIVERING, runner, "取件打卡，开始配送")
    notify(order.student, "跑腿员已取件", f"订单 {order.order_no} 配送中", order_no=order.order_no)
    return order


@transaction.atomic
def deliver(runner, order_no, file_id=None, actual_item_fee=None):
    order = Order.objects.select_for_update().filter(order_no=order_no).first()
    if order is None:
        raise BizError("订单不存在", code=40400, http_status=404)
    if order.runner_id != runner.id:
        raise BizError("仅接单跑腿员可打卡", code=40300, http_status=403)
    if order.status != S.DELIVERING:
        raise conflict(f"订单当前状态为 {order.get_status_display()}，不可送达打卡")
    if order.item_fee_mode == Order.ItemFeeMode.PLATFORM:
        if actual_item_fee is None:
            raise BizError("平台代付模式需填写实际物品费")
        order.actual_item_fee = finance.money(actual_item_fee)
    order.deliver_at = timezone.now()
    order.deliver_file = _file(file_id)
    order.auto_confirm_deadline = minutes(rules.get_rule("timeout_confirm_minutes"))
    order.save(update_fields=["deliver_at", "deliver_file", "actual_item_fee", "auto_confirm_deadline", "updated_at"])
    state.transition(order, S.PENDING_CONFIRM, runner, "送达打卡，等待学生确认")
    notify(order.student, "跑腿员已送达", f"订单 {order.order_no} 待确认，请及时确认", order_no=order.order_no)
    return order


@transaction.atomic
def confirm(user, order_no):
    order = Order.objects.select_for_update().filter(order_no=order_no).first()
    if order is None:
        raise BizError("订单不存在", code=40400, http_status=404)
    if order.student_id != user.id:
        raise BizError("仅发单学生可确认完成", code=40300, http_status=403)
    if order.status == S.COMPLETED:  # 幂等：重复确认返回既有结果
        return order
    if order.status != S.PENDING_CONFIRM:
        raise conflict(f"订单当前状态为 {order.get_status_display()}，不可确认")
    finance.settle_order(order)
    order.refresh_from_db()
    state.transition(order, S.COMPLETED, user, "学生确认完成，已结算")
    order.completed_at = timezone.now()
    order.review_deadline = order.completed_at + timedelta(days=int(rules.get_rule("review_deadline_days")))
    order.save(update_fields=["completed_at", "review_deadline", "updated_at"])
    if order.runner_id:
        from apps.accounts.models import User

        runner = User.objects.filter(pk=order.runner_id).first()
        notify(runner, "订单已完成", f"订单 {order.order_no} 已结算，酬金 {order.final_reward} 元（模拟）", order_no=order.order_no)
    return order


@transaction.atomic
def cancel(user, order_no, reason="", by_system=False):
    order = Order.objects.select_for_update().filter(order_no=order_no).first()
    if order is None:
        raise BizError("订单不存在", code=40400, http_status=404)
    is_student = order.student_id == user.id if user else False
    is_runner = order.runner_id == user.id if user else False
    student_ok, runner_ok, note = state.cancel_policy(order)
    if is_student and not student_ok:
        if order.prepaid:
            raise conflict("平台代付且跑腿员已垫付，请发起申诉由管理员仲裁")
        raise conflict(f"当前状态（{order.get_status_display()}）不可取消：{note}")
    if is_runner and not runner_ok:
        raise conflict(f"当前状态（{order.get_status_display()}）不可取消：{note}")
    if not (is_student or is_runner or by_system or (user and user.is_admin)):
        raise BizError("无权取消该订单", code=40300, http_status=403)
    if order.status != S.PENDING_PAY:
        finance.refund_order(order, None, reason or "订单取消全额退款")
        order.refresh_from_db()
    order.cancel_reason = reason[:200]
    order.cancel_by = user
    order.save(update_fields=["cancel_reason", "cancel_by", "updated_at"])
    state.transition(order, S.CANCELLED, user, reason or "订单取消")
    # 信用：爽约场景见取消矩阵
    if is_runner and order.status == S.CANCELLED and order.accept_at:
        credit_services.on_no_show(user, order, "跑腿员弃单")
    elif is_student and not reason and order.accept_at and not order.prepaid:
        credit_services.on_no_show(user, order, "学生无理由取消")
    notify(order.student, "订单已取消", f"订单 {order.order_no} 已取消：{reason or '无'}", order_no=order.order_no)
    if order.runner_id:
        notify(order.runner, "订单已取消", f"订单 {order.order_no} 已取消", order_no=order.order_no)
    return order


@transaction.atomic
def review(reviewer, order_no, score, content=""):
    order = Order.objects.select_for_update().filter(order_no=order_no).first()
    if order is None:
        raise BizError("订单不存在", code=40400, http_status=404)
    _assert_participant(order, reviewer)
    if order.status != S.COMPLETED:
        raise conflict("仅在订单已完成且无申诉时可评价")
    if order.appeals.filter(status__in=[Appeal.Status.PENDING, Appeal.Status.PROCESSING]).exists():
        raise conflict("订单存在申诉，评价已冻结")
    if order.review_deadline and timezone.now() > order.review_deadline:
        raise conflict("评价已逾期，视为放弃")
    if not 1 <= int(score) <= 5:
        raise BizError("星级需为 1–5")
    reviewee_id = order.runner_id if reviewer.id == order.student_id else order.student_id
    if not reviewee_id:
        raise conflict("对方不存在，无法评价")
    if Review.objects.filter(order=order, reviewer=reviewer).exists():
        raise conflict("你已评价过该订单")
    from apps.accounts.models import User

    reviewee = User.objects.get(pk=reviewee_id)
    record = Review.objects.create(order=order, reviewer=reviewer, reviewee=reviewee, score=int(score), content=content[:500])
    credit_services.on_review(reviewee, score, record)
    reviewee.review_count += 1
    if int(score) >= int(rules.get_rule("review_good_star")):
        reviewee.good_reviews += 1
    reviewee.save(update_fields=["review_count", "good_reviews", "updated_at"])
    notify(reviewee, "收到新评价", f"订单 {order.order_no} 收到 {score} 星评价", order_no=order.order_no)
    return record


@transaction.atomic
def appeal(user, order_no, appeal_type="dispute", description="", file_id=None):
    order = Order.objects.select_for_update().filter(order_no=order_no).first()
    if order is None:
        raise BizError("订单不存在", code=40400, http_status=404)
    _assert_participant(order, user)
    if order.status not in (S.COMPLETED, S.PENDING_CONFIRM):
        raise conflict(f"订单当前状态为 {order.get_status_display()}，不可申诉")
    if order.appeals.filter(status__in=[Appeal.Status.PENDING, Appeal.Status.PROCESSING]).exists():
        raise conflict("该订单已有进行中的申诉")
    respondent_id = order.runner_id if user.id == order.student_id else order.student_id
    record = Appeal.objects.create(
        order=order,
        initiator=user,
        respondent_id=respondent_id,
        appeal_type=appeal_type,
        description=description[:500],
        evidence=_file(file_id, FileAsset.Kind.APPEAL),
        deadline=timezone.now() + timedelta(hours=int(rules.get_rule("appeal_deadline_hours"))),
    )
    state.transition(order, S.APPEALING, user, f"发起申诉#{record.pk}，资金暂缓结算")
    notify_admins("新的争议申诉", f"订单 {order.order_no} 发起申诉，请及时仲裁")
    return record


@transaction.atomic
def arbitrate(appeal_row, admin, winner, student_ratio=None, remark=""):
    appeal_row = Appeal.objects.select_for_update().get(pk=appeal_row.pk)
    order = Order.objects.select_for_update().get(pk=appeal_row.order_id)
    if appeal_row.status not in (Appeal.Status.PENDING, Appeal.Status.PROCESSING):
        raise conflict("该申诉已处理")
    if winner == Appeal.Winner.STUDENT:
        ratio = 100
    elif winner == Appeal.Winner.RUNNER:
        ratio = 0
    else:
        ratio = int(student_ratio if student_ratio is not None else 50)
        if not 0 <= ratio <= 100:
            raise BizError("资金分配比例需在 0–100 之间")
    # 只动用"仍在托管中"的真实资金：已完成订单的申诉仅处理信用/评价争议，不回溯已结算资金
    from django.db.models import Sum

    from apps.finance.models import FundFlow

    escrow = finance.money(
        FundFlow.objects.filter(order=order, type=FundFlow.Type.ESCROW, status=FundFlow.Status.ESCROWED).aggregate(
            s=Sum("amount")
        )["s"]
    )
    suffix = f"appeal{appeal_row.pk}"
    if escrow <= 0:
        target = S.COMPLETED if order.prev_status == S.COMPLETED else S.CANCELLED
        remark = (remark or "") + "（资金已结算，不回溯资金，仅恢复信用）"
    elif ratio == 100:
        finance.refund_order(order, escrow, remark or "仲裁：学生胜诉全额退款", suffix)
        target = S.REFUNDED
    elif ratio == 0:
        finance.settle_order(order, suffix)
        target = S.COMPLETED
    else:
        refund_part = finance.money(escrow * Decimal(ratio) / Decimal(100))
        reward = min(escrow - refund_part, finance.final_reward(order))
        refund_part = escrow - reward
        finance.payout(order, reward, refund_part, suffix, Order.SettleStatus.PARTIAL, remark or f"仲裁：按 {ratio}:{100 - ratio} 比例出账")
        target = S.REFUNDED if ratio >= 50 else S.COMPLETED
    order.refresh_from_db()
    if order.status == S.APPEALING:
        state.transition(order, target, admin, f"仲裁出账（学生获退 {ratio}%）")
    if order.status == S.COMPLETED and order.completed_at is None:
        order.completed_at = timezone.now()
        order.save(update_fields=["completed_at", "updated_at"])
    # 申诉成功：恢复本次争议所扣分的变动前原值
    if (appeal_row.initiator_id == order.student_id and ratio > 0) or (appeal_row.initiator_id == order.runner_id and ratio < 100):
        credit_services.restore(appeal_row.initiator, appeal_row, order)
    appeal_row.status = Appeal.Status.RESOLVED
    appeal_row.winner = winner
    appeal_row.student_ratio = ratio
    appeal_row.handler = admin
    appeal_row.result = (remark or "")[:300]
    appeal_row.handled_at = timezone.now()
    appeal_row.save()
    notify(order.student, "申诉已裁决", f"订单 {order.order_no} 申诉结果：学生获退 {ratio}%", order_no=order.order_no)
    if order.runner_id:
        notify(order.runner, "申诉已裁决", f"订单 {order.order_no} 申诉结果：跑腿员得 {100 - ratio}%", order_no=order.order_no)
    return appeal_row


@transaction.atomic
def resolve_abnormal(order_no, admin, action, remark=""):
    """异常单人工处理：确认完成（结算）或取消（退款）。"""
    order = Order.objects.select_for_update().filter(order_no=order_no).first()
    if order is None:
        raise BizError("订单不存在", code=40400, http_status=404)
    if order.status != S.ABNORMAL:
        raise conflict("仅异常订单可人工处理")
    if action == "complete":
        if order.runner_id is None:
            raise conflict("无跑腿员，不能结算，请选择取消退款")
        order.actual_item_fee = order.actual_item_fee if order.actual_item_fee is not None else order.item_fee_estimate
        order.save(update_fields=["actual_item_fee", "updated_at"])
        finance.settle_order(order, suffix="admin")
        order.refresh_from_db()
        state.transition(order, S.COMPLETED, admin, remark or "管理员核验凭证后确认完成")
        order.completed_at = timezone.now()
        order.save(update_fields=["completed_at", "updated_at"])
    else:
        finance.refund_order(order, None, remark or "管理员核验后取消退款", suffix="admin")
        order.refresh_from_db()
        order.cancel_reason = (remark or "异常订单人工取消")[:200]
        order.cancel_by = admin
        order.save(update_fields=["cancel_reason", "cancel_by", "updated_at"])
        state.transition(order, S.CANCELLED, admin, remark or "管理员核验后取消退款")
    return order
