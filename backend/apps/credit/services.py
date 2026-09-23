"""信用体系：分数变动、等级权限映射、申诉恢复、周期恢复。"""
from django.db import transaction

from apps.accounts.models import User
from apps.common import rules
from apps.common.models import RuleConfig
from apps.credit.models import CreditLog

LEVEL_LABELS = {
    "excellent": "优秀",
    "good": "良好",
    "normal": "一般",
    "limited": "受限",
}


def level_of(score):
    if score >= int(rules.get_rule("level_excellent")):
        return "excellent"
    if score >= int(rules.get_rule("level_good")):
        return "good"
    if score >= int(rules.get_rule("level_normal")):
        return "normal"
    return "limited"


def limits_of(user):
    """等级 → 权限映射：受限禁发单/接单，一般及以下禁平台代付。"""
    level = level_of(user.credit_score)
    can_normal = user.credit_score >= int(rules.get_rule("level_normal"))
    can_prepay = user.credit_score >= int(rules.get_rule("level_good"))
    return {
        "level": level,
        "level_label": LEVEL_LABELS[level],
        "can_publish": can_normal,
        "can_accept": can_normal and user.is_runner,
        "can_prepay": can_prepay,
    }


def _clamp(score):
    return max(int(rules.get_rule("credit_min")), min(int(rules.get_rule("credit_max")), score))


@transaction.atomic
def change(user, delta, reason_code, rule=None, order=None, review=None, appeal=None, remark="", restore_of=None):
    """写一条信用变动并同步用户分数；上下限封顶（150 不加、0 不减）。"""
    user = User.objects.select_for_update().get(pk=user.pk)
    before = user.credit_score
    after = _clamp(before + int(delta))
    if after != before:
        user.credit_score = after
        user.save(update_fields=["credit_score", "updated_at"])
    rule_row = rule
    if rule_row is None:
        rule_row = RuleConfig.objects.filter(key=f"credit_delta_{reason_code}").first()
    return CreditLog.objects.create(
        user=user,
        delta=after - before,
        score_before=before,
        score_after=after,
        reason_code=reason_code,
        rule=rule_row,
        order=order,
        review=review,
        appeal=appeal,
        remark=remark,
        restore_of=restore_of,
    )


def on_order_complete(user, order):
    return change(user, int(rules.get_rule("credit_delta_complete")), CreditLog.Reason.ORDER_COMPLETE, order=order)


def on_review(reviewee, score, review):
    """星级判定：4–5 星好评 +2，1–2 星差评 -5，3 星中评不加不减。"""
    score = int(score)
    order = review.order if review.order_id else None
    if score >= int(rules.get_rule("review_good_star")):
        return change(reviewee, int(rules.get_rule("credit_delta_good")), CreditLog.Reason.REVIEW_GOOD,
                      review=review, order=order)
    if score <= int(rules.get_rule("review_bad_star")):
        return change(reviewee, int(rules.get_rule("credit_delta_bad")), CreditLog.Reason.REVIEW_BAD,
                      review=review, order=order)
    return None


def on_no_show(user, order, remark="爽约"):
    return change(user, int(rules.get_rule("credit_no_show")), CreditLog.Reason.NO_SHOW, order=order, remark=remark)


def restore(user, appeal, order=None):
    """申诉成功：恢复本次争议所扣分的变动前原值（只恢复未恢复过的扣分）。"""
    logs = CreditLog.objects.select_for_update().filter(user=user, delta__lt=0, restored=False, order=order or appeal.order)
    restored = []
    for log in logs:
        restored.append(
            change(
                user,
                -log.delta,
                CreditLog.Reason.APPEAL_RESTORE,
                order=log.order,
                appeal=appeal,
                remark="申诉成功恢复",
                restore_of=log,
            )
        )
        CreditLog.objects.filter(pk=log.pk).update(restored=True)
    return restored


def period_recover():
    """周期恢复：仅对 <recover_target 分用户，每 recover_days 天 +recover_points，不超目标。"""
    if not int(rules.get_rule("recover_enabled")):
        return 0
    from datetime import timedelta

    from django.utils import timezone

    target = int(rules.get_rule("recover_target"))
    days = int(rules.get_rule("recover_days"))
    points = int(rules.get_rule("recover_points"))
    threshold = timezone.now() - timedelta(days=days)
    count = 0
    for user in User.objects.filter(credit_score__lt=target, role=User.Role.USER):
        last = CreditLog.objects.filter(user=user).order_by("-created_at").first()
        if last and last.created_at > threshold:
            continue
        delta = min(points, target - user.credit_score)
        if delta > 0:
            change(user, delta, CreditLog.Reason.PERIOD_RECOVER, remark="周期恢复")
            count += 1
    return count
