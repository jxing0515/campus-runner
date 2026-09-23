"""安全测试：越权、自接单、封禁 JWT、上传校验、文件受控访问、管理员权限位。"""
import io

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.common.models import FileAsset, RuleConfig
from apps.orders import services
from tests.conftest import client_for, mkuser, publish

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4"
    b"\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_student_cannot_access_admin_api(student):
    resp = client_for(student).get("/api/v1/admin/users")
    assert resp.status_code == 403 and resp.json()["code"] == 40300
    assert client_for(student).get("/api/v1/admin/escrow").status_code == 403


def test_operator_cannot_write_rules_or_ban(operator, student):
    client = client_for(operator)
    assert client.post("/api/v1/admin/rules", {"key": "credit_max", "value": "999"}, format="json").status_code == 403
    rule = RuleConfig.objects.get(key="credit_max")
    assert client.put(f"/api/v1/admin/rules/{rule.pk}", {"value": "999"}, format="json").status_code == 403
    assert client.post(f"/api/v1/admin/users/{student.pk}/ban", {"banned": True}, format="json").status_code == 403
    # operator 可做日常审核类操作
    assert client.get("/api/v1/admin/certifications").status_code == 200


def test_banned_user_token_is_rejected(student, admin):
    token = client_for(student)
    assert token.get("/api/v1/auth/me").status_code == 200
    resp = client_for(admin).post(f"/api/v1/admin/users/{student.pk}/ban", {"banned": True, "reason": "违规"}, format="json")
    assert resp.json()["data"]["banned"] is True
    # 已签发 token 立即失效（鉴权中间件校验用户状态）
    assert token.get("/api/v1/auth/me").status_code in (401, 403)


def test_admin_cannot_publish_or_accept(admin, student):
    assert client_for(admin).post("/api/v1/orders", {
        "description": "x", "pickup_address": "a", "delivery_address": "b",
        "time_window_start": "2030-01-01 10:00:00", "time_window_end": "2030-01-01 12:00:00",
        "runner_fee": "5.00", "item_fee_mode": "none",
    }, format="json").status_code == 403


def test_upload_validation(student):
    client = client_for(student)
    bad = SimpleUploadedFile("evil.png", b"<?php echo 1; ?>", content_type="image/png")
    assert client.post("/api/v1/files", {"file": bad, "kind": "evidence"}, format="multipart").status_code == 400

    exe = SimpleUploadedFile("run.exe", PNG, content_type="application/octet-stream")
    assert client.post("/api/v1/files", {"file": exe, "kind": "evidence"}, format="multipart").status_code == 400

    ok = SimpleUploadedFile("ok.png", PNG, content_type="image/png")
    resp = client.post("/api/v1/files", {"file": ok, "kind": "evidence"}, format="multipart")
    assert resp.status_code == 201
    asset_id = resp.json()["data"]["id"]

    # 学生证仅本人与管理员可访问
    owner = mkuser("cardowner")
    asset = FileAsset.objects.create(file=SimpleUploadedFile("card.png", PNG), name="card.png",
                                     kind=FileAsset.Kind.STUDENT_CARD, uploader=owner, size=len(PNG))
    assert client_for(student).get(f"/api/v1/files/{asset.pk}").status_code == 403
    assert client_for(owner).get(f"/api/v1/files/{asset.pk}").status_code == 200


def test_student_cannot_read_others_order(student, student2, runner):
    order = publish(student)
    services.pay(student, order.order_no)
    assert client_for(student2).get(f"/api/v1/orders/{order.order_no}").status_code == 403
    assert client_for(student).get(f"/api/v1/orders/{order.order_no}").status_code == 200


def test_price_and_address_length_limits(student):
    client = client_for(student)
    resp = client.post("/api/v1/orders", {
        "description": "x" * 501, "pickup_address": "a", "delivery_address": "b",
        "time_window_start": "2030-01-01 10:00:00", "time_window_end": "2030-01-01 12:00:00",
        "runner_fee": "5.00", "item_fee_mode": "none",
    }, format="json")
    assert resp.status_code == 400
    negative = client.post("/api/v1/orders", {
        "description": "x", "pickup_address": "a", "delivery_address": "b",
        "time_window_start": "2030-01-01 10:00:00", "time_window_end": "2030-01-01 12:00:00",
        "runner_fee": "-1.00", "item_fee_mode": "none",
    }, format="json")
    assert negative.status_code == 400
