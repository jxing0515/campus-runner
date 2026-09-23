"""信用体系测试：边界、星级判定、叠加、等级权限、申诉恢复、周期恢复与规则缓存。"""
from datetime import timedelta

from django.utils import timezone

from apps.common import rules
from apps.credit import services as credit_services
from apps.credit.models import CreditLog
from apps.orders import services
from apps.orders.models import Appeal, Order
from tests.conftest import client_for, mkuser, publish, run_full_flow


def test_complete_and_review_stack(student, runner):
    no = run_full_flow(student, runner)
    services.confirm(student, no)
    runner.refresh_from_db()
    assert runner.credit_score == 101  # 完成 +1（学生同样 +1）
    student.refresh_from_db()
    assert student.credit_score == 101
    services.review(student, no, 5, "好评")
    runner.refresh_from_db()
    assert runner.credit_score == 103  # 完成 +1 与好评 +2 叠加
    logs = CreditLog.objects.filter(user=runner).order_by("id")
    assert [log.delta for log in logs] == [1, 2]


def test_star_rules(student, runner):
    no = run_full_flow(student, runner)
    services.confirm(student, no)
    runner.refresh_from_db()
    before = runner.credit_score
    services.review(student, no, 3, "中评")
    runner.refresh_from_db()
    assert runner.credit_score == before  # 3 星不加不减

    no2 = run_full_flow(student, runner)
    services.confirm(student, no2)
    runner.refresh_from_db()
    before = runner.credit_score
    services.review(student, no2, 1, "差评")
    runner.refresh_from_db()
    assert runner.credit_score == before - 5


def test_credit_bounds(student):
    credit_services.change(student, 200, CreditLog.Reason.ADMIN_ADJUST)
    student.refresh_from_db()
    assert student.credit_score == 150  # 封顶
    credit_services.change(student, -500, CreditLog.Reason.ADMIN_ADJUST)
    student.refresh_from_db()
    assert student.credit_score == 0  # 触底不减（温和约束，不归零禁入）


def test_level_limits(student, runner):
    limited = mkuser("lim1", runner=True, score=55)
    assert credit_services.limits_of(limited)["can_publish"] is False
    assert credit_services.limits_of(limited)["can_accept"] is False
    resp = client_for(limited).post("/api/v1/orders", {
        "description": "x", "pickup_address": "a", "delivery_address": "b",
        "time_window_start": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
        "time_window_end": (timezone.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
        "runner_fee": "5.00", "item_fee_mode": "none",
    }, format="json")
    assert resp.status_code == 403

    normal = mkuser("norm1", runner=True, score=70)
    assert credit_services.limits_of(normal)["can_publish"] is True
    assert credit_services.limits_of(normal)["can_prepay"] is False  # 一般等级禁平台代付

    good = mkuser("good1", runner=True, score=85)
    assert credit_services.limits_of(good)["can_prepay"] is True


def test_appeal_restores_credit(student, runner, admin):
    no = run_full_flow(student, runner)
    services.confirm(student, no)
    runner.refresh_from_db()
    before = runner.credit_score
    services.review(student, no, 1, "差评")
    runner.refresh_from_db()
    assert runner.credit_score == before - 5

    appeal = services.appeal(runner, no, "review", "差评不实，申请仲裁")
    order = Order.objects.get(order_no=no)
    assert order.status == Order.Status.APPEALING  # 申诉中：进入占位态
    services.arbitrate(appeal, admin, Appeal.Winner.RUNNER, None, "凭证有效，撤销差评扣分")
    runner.refresh_from_db()
    assert runner.credit_score == before  # 恢复至本次争议所扣分的变动前原值
    order.refresh_from_db()
    assert order.status == Order.Status.COMPLETED  # 恢复到 prev_status
    restored = CreditLog.objects.filter(user=runner, reason_code=CreditLog.Reason.APPEAL_RESTORE).first()
    assert restored is not None and restored.restore_of is not None
    assert CreditLog.objects.get(pk=restored.restore_of_id).restored is True


def test_rule_change_takes_effect_after_cache_invalidation(student, runner):
    no = run_full_flow(student, runner)
    rules.set_rule("credit_delta_complete", 5)
    services.confirm(student, no)
    runner.refresh_from_db()
    assert runner.credit_score == 105  # 规则修改后立刻生效（缓存键已删）
    rules.set_rule("credit_delta_complete", 1)


def test_period_recover_only_below_target(student):
    student.credit_score = 60
    student.save(update_fields=["credit_score"])
    log = CreditLog.objects.create(
        user=student, delta=-40, score_before=100, score_after=60, reason_code=CreditLog.Reason.ADMIN_ADJUST
    )
    CreditLog.objects.filter(pk=log.pk).update(created_at=timezone.now() - timedelta(days=31))  # 30 天前
    assert credit_services.period_recover() >= 1
    student.refresh_from_db()
    assert student.credit_score == 65  # 每 30 天 +5，不超目标 100
