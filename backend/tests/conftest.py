"""pytest 公共夹具：三角色账号、鉴权客户端、发单助手。"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.common import rules
from apps.orders import services as order_services
from apps.orders.models import Order

PASSWORD = "Passw0rd!"


@pytest.fixture(autouse=True)
def _rules(db):
    rules.ensure_default_rules()
    rules.invalidate_rule_cache()
    yield
    rules.invalidate_rule_cache()


def mkuser(username, role="user", admin_level="none", runner=False, score=100, **extra):
    user = User.objects.create_user(username=username, password=PASSWORD, name=username, credit_score=score, **extra)
    user.role = role
    user.admin_level = admin_level
    if runner:
        user.cert_status = User.CertStatus.APPROVED
        user.is_runner = True
    user.save()
    return user


def client_for(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


def order_payload(mode="none", fee="10.00", estimate="0.00"):
    now = timezone.now()
    return {
        "description": "代取快递",
        "pickup_address": "菜鸟驿站 1 号柜",
        "delivery_address": "5 号楼 302",
        "time_window_start": (now + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
        "time_window_end": (now + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
        "runner_fee": fee,
        "item_fee_mode": mode,
        "item_fee_estimate": estimate,
    }


def publish(student, mode="none", fee="10.00", estimate="0.00"):
    return order_services.create_order(student, {
        "description": "代取快递",
        "pickup_address": "菜鸟驿站 1 号柜",
        "delivery_address": "5 号楼 302",
        "time_window_start": timezone.now() + timedelta(hours=1),
        "time_window_end": timezone.now() + timedelta(hours=3),
        "runner_fee": Decimal(fee),
        "item_fee_mode": mode,
        "item_fee_estimate": Decimal(estimate),
    })


def run_full_flow(student, runner, mode="none", fee="10.00", estimate="0.00", actual=None):
    """发单→支付→接单→取件→送达 返回 order_no。"""
    order = publish(student, mode, fee, estimate)
    no = order.order_no
    order_services.pay(student, no)
    order_services.accept(runner, no)
    order_services.pickup(runner, no)
    order_services.deliver(runner, no, actual_item_fee=actual)
    return no


@pytest.fixture
def student(db):
    return mkuser("stu1")


@pytest.fixture
def student2(db):
    return mkuser("stu2")


@pytest.fixture
def runner(db):
    return mkuser("run1", runner=True)


@pytest.fixture
def runner2(db):
    return mkuser("run2", runner=True)


@pytest.fixture
def admin(db):
    return mkuser("admin1", role="admin", admin_level="super_admin")


@pytest.fixture
def operator(db):
    return mkuser("op1", role="admin", admin_level="operator")


@pytest.fixture
def order_factory(db):
    return publish
