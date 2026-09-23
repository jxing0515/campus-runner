"""并发测试：接单抢占、重复确认、重复提现。"""
import threading
from decimal import Decimal

import pytest
from django.db import connections

from apps.finance import services as finance
from apps.orders import services
from apps.orders.models import Order
from tests.conftest import mkuser, publish, run_full_flow


def run_parallel(func, args_list):
    results = []

    def worker(args):
        try:
            results.append(("ok", func(*args)))
        except Exception as exc:  # 失败也要收集，用于断言成功数
            results.append(("err", str(exc)))
        finally:
            connections.close_all()

    threads = [threading.Thread(target=worker, args=(a,)) for a in args_list]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


@pytest.mark.django_db(transaction=True)
def test_concurrent_accept_only_one_wins(student):
    runners = [mkuser(f"r{i}") for i in range(4)]
    for r in runners:
        r.cert_status = "approved"
        r.is_runner = True
        r.save()
    order = publish(student)
    services.pay(student, order.order_no)
    results = run_parallel(services.accept, [(r, order.order_no) for r in runners])
    ok = [r for r in results if r[0] == "ok"]
    assert len(ok) == 1, results
    order.refresh_from_db()
    assert order.status == Order.Status.ACCEPTED and order.runner_id is not None


@pytest.mark.django_db(transaction=True)
def test_repeat_confirm_settles_once(student, runner):
    no = run_full_flow(student, runner, fee="20.00")
    results = run_parallel(services.confirm, [(student, no)] * 4)
    assert all(r[0] == "ok" for r in results), results  # 幂等：重复确认返回成功
    runner.refresh_from_db()
    assert runner.runner_balance == Decimal("20.00")


@pytest.mark.django_db(transaction=True)
def test_concurrent_withdraw_cannot_double_spend(student, runner):
    no = run_full_flow(student, runner, fee="50.00")
    services.confirm(student, no)
    results = run_parallel(
        finance.apply_withdrawal,
        [(runner, Decimal("40.00"), "模拟收款", "acc")] * 3,
    )
    ok = [r for r in results if r[0] == "ok"]
    assert len(ok) == 1, results
    runner.refresh_from_db()
    assert runner.runner_balance == Decimal("10.00")
    assert runner.runner_balance >= 0
