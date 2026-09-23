"""主流程、状态机与认证接口测试。"""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.common import locks
from apps.orders import services
from apps.orders.models import Order, OrderStatusLog
from tests.conftest import PASSWORD, client_for, mkuser, order_payload, publish, run_full_flow


def test_register_login_and_me(db):
    anon = APIClient()
    resp = anon.post("/api/v1/auth/register", {"username": "newstu", "password": "Abcd1234", "name": "新同学"}, format="json")
    assert resp.status_code == 201 and resp.json()["code"] == 0

    weak = anon.post("/api/v1/auth/register", {"username": "weak", "password": "abcdefgh"}, format="json")
    assert weak.status_code == 400 and weak.json()["code"] == 40001

    login = anon.post("/api/v1/auth/login", {"username": "newstu", "password": "Abcd1234"}, format="json")
    assert login.json()["code"] == 0 and login.json()["data"]["access"]

    anon.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['data']['access']}")
    me = anon.get("/api/v1/auth/me")
    assert me.json()["data"]["username"] == "newstu"
    assert me.json()["data"]["limits"]["can_publish"] is True


def test_login_lock_after_failures(db):
    anon = APIClient()
    for _ in range(5):
        anon.post("/api/v1/auth/login", {"username": "ghost", "password": "bad12345"}, format="json")
    resp = anon.post("/api/v1/auth/login", {"username": "ghost", "password": "bad12345"}, format="json")
    assert resp.status_code == 403 and "锁定" in resp.json()["message"]


def test_main_flow_and_status_logs(student, runner):
    client = client_for(student)
    created = client.post("/api/v1/orders", order_payload(), format="json")
    assert created.status_code == 201
    no = created.json()["data"]["order_no"]
    assert created.json()["data"]["status"] == "pending_pay"

    paid = client.post(f"/api/v1/orders/{no}/pay", {}, format="json")
    assert paid.json()["data"]["status"] == "pending_accept"

    runner_client = client_for(runner)
    accepted = runner_client.post(f"/api/v1/orders/{no}/accept", {}, format="json")
    assert accepted.json()["data"]["status"] == "accepted"
    assert runner_client.post(f"/api/v1/orders/{no}/pickup", {}, format="json").json()["data"]["status"] == "delivering"
    assert runner_client.post(f"/api/v1/orders/{no}/deliver", {}, format="json").json()["data"]["status"] == "pending_confirm"

    done = client.post(f"/api/v1/orders/{no}/confirm", {}, format="json")
    assert done.json()["data"]["status"] == "completed"

    detail = client.get(f"/api/v1/orders/{no}")
    chain = [(log["from"], log["to"]) for log in detail.json()["data"]["status_logs"]]
    assert ("pending_pay", "pending_accept") in chain and ("delivering", "pending_confirm") in chain
    assert OrderStatusLog.objects.filter(order__order_no=no).count() >= 5


def test_self_accept_forbidden(student, student2, runner):
    # 学生兼跑腿员（认证通过）自接自己的单 → 400
    both = mkuser("both1", runner=True)
    order = publish(both)
    services.pay(both, order.order_no)
    resp = client_for(both).post(f"/api/v1/orders/{order.order_no}/accept", {}, format="json")
    assert resp.status_code == 400 and "自己" in resp.json()["message"]
    # 未通过认证的学生接单 → 403
    unauth = client_for(student2).post(f"/api/v1/orders/{order.order_no}/accept", {}, format="json")
    assert unauth.status_code == 403


def test_confirm_is_idempotent(student, runner):
    no = run_full_flow(student, runner)
    client = client_for(student)
    first = client.post(f"/api/v1/orders/{no}/confirm", {}, format="json")
    runner.refresh_from_db()
    balance_after_first = runner.runner_balance
    second = client.post(f"/api/v1/orders/{no}/confirm", {}, format="json")
    runner.refresh_from_db()
    assert first.json()["code"] == 0 and second.json()["code"] == 0
    assert runner.runner_balance == balance_after_first
    assert Order.objects.get(order_no=no).status == "completed"


def test_cancel_matrix(student, student2, runner):
    # 待接单取消：全额退款
    order = publish(student)
    services.pay(student, order.order_no)
    resp = client_for(student).post(f"/api/v1/orders/{order.order_no}/cancel", {"reason": "临时不需要了"}, format="json")
    assert resp.json()["data"]["status"] == "cancelled"
    assert Order.objects.get(order_no=order.order_no).settle_status == "refunded"

    # 配送中不可取消
    no = run_full_flow(student, runner)
    order = Order.objects.get(order_no=no)
    Order.objects.filter(pk=order.pk).update(status=Order.Status.DELIVERING)
    blocked = client_for(student).post(f"/api/v1/orders/{no}/cancel", {"reason": "x"}, format="json")
    assert blocked.status_code == 409

    # 委托代付已垫付 → 转仲裁提示
    order2 = publish(student2, mode="platform", estimate="20.00")
    services.pay(student2, order2.order_no)
    services.accept(runner, order2.order_no)
    services.pickup(runner, order2.order_no)  # 代付取件即垫付
    conflict = client_for(student2).post(f"/api/v1/orders/{order2.order_no}/cancel", {"reason": "不要了"}, format="json")
    assert conflict.status_code == 409 and "仲裁" in conflict.json()["message"]


def test_runner_cancel_penalizes_credit(student, runner):
    order = publish(student)
    services.pay(student, order.order_no)
    services.accept(runner, order.order_no)
    before = runner.credit_score
    resp = client_for(runner).post(f"/api/v1/orders/{order.order_no}/cancel", {"reason": "弃单"}, format="json")
    runner.refresh_from_db()
    assert resp.json()["code"] == 0
    assert runner.credit_score == before - 10


def test_review_rules(student, runner):
    no = run_full_flow(student, runner)
    services.confirm(student, no)
    client = client_for(student)
    assert client.post(f"/api/v1/orders/{no}/review", {"score": 5, "content": "很好"}, format="json").status_code == 201
    dup = client.post(f"/api/v1/orders/{no}/review", {"score": 5}, format="json")
    assert dup.status_code == 409
    # 跑腿员可反评学生（双向互评）
    assert client_for(runner).post(f"/api/v1/orders/{no}/review", {"score": 4}, format="json").status_code == 201
    order = Order.objects.get(order_no=no)
    assert order.reviews.count() == 2


def test_abnormal_order_resolution(student, runner, admin):
    no = run_full_flow(student, runner)
    order = Order.objects.get(order_no=no)
    order.auto_confirm_deadline = timezone.now()
    order.save(update_fields=["auto_confirm_deadline"])
    from apps.orders import state

    state.transition(order, Order.Status.ABNORMAL, None, "测试转异常")
    resolved = client_for(admin).post(f"/api/v1/admin/orders/{no}/resolve", {"action": "complete", "remark": "凭证核验通过"}, format="json")
    assert resolved.json()["data"]["status"] == "completed"
    assert Order.objects.get(order_no=no).settle_status == "settled"
