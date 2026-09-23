"""接口冒烟脚本：三角色走通主流程 + 管理端核心接口（只依赖标准库）。

用法：
    python manage.py runserver 127.0.0.1:8000        # 另开终端
    python scripts/smoke_api.py [base_url]
"""
import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
PASSED, FAILED = [], []


def call(method, path, token=None, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"raw": body}


def check(name, cond, detail=""):
    (PASSED if cond else FAILED).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if detail and not cond else ""))


def login(username, password):
    status, body = call("POST", "/api/v1/auth/login", payload={"username": username, "password": password})
    assert status == 200 and body["code"] == 0, f"登录失败 {username}: {body}"
    return body["data"]["access"], body["data"]["user"]


def main():
    student_token, student = login("s001", "Student@123")
    runner_token, runner = login("r001", "Runner@123")
    admin_token, admin = login("admin", "Admin@123")
    check("三角色登录", all([student_token, runner_token, admin_token]))

    status, body = call("GET", "/api/v1/auth/me", student_token)
    check("学生 /auth/me 与等级权限", status == 200 and "limits" in body["data"])

    status, body = call("GET", "/api/v1/orders/available?sort=fee", runner_token)
    check("跑腿员待接单大厅", status == 200 and "results" in body["data"])

    payload = {
        "description": "冒烟：代取快递",
        "pickup_address": "菜鸟驿站 2 号柜",
        "delivery_address": "6 号楼 101",
        "time_window_start": "2030-01-01 10:00:00",
        "time_window_end": "2030-01-01 12:00:00",
        "runner_fee": "9.90",
        "item_fee_mode": "platform",
        "item_fee_estimate": "20.00",
    }
    status, body = call("POST", "/api/v1/orders", student_token, payload)
    check("学生发单", status == 201, str(body))
    no = body["data"]["order_no"]

    status, body = call("POST", f"/api/v1/orders/{no}/pay", student_token, {"idempotency_key": f"smoke-{no}"})
    check("模拟支付进入托管", status == 200 and body["data"]["status"] == "pending_accept", str(body))
    status, body = call("POST", f"/api/v1/orders/{no}/pay", student_token, {"idempotency_key": f"smoke-{no}"})
    check("重复支付幂等", status == 200 and body["code"] == 0)

    status, body = call("POST", f"/api/v1/orders/{no}/accept", runner_token)
    check("跑腿员接单", body["data"]["status"] == "accepted", str(body))
    status, body = call("POST", f"/api/v1/orders/{no}/pickup", runner_token, {})
    check("取件打卡（代付垫付）", body["data"]["prepaid"] is True)
    status, body = call("POST", f"/api/v1/orders/{no}/deliver", runner_token, {"actual_item_fee": "16.50"})
    check("送达打卡（实际物品费）", body["data"]["status"] == "pending_confirm", str(body))

    status, body = call("POST", f"/api/v1/orders/{no}/confirm", student_token, {})
    check("确认完成并结算", body["data"]["status"] == "completed" and body["data"]["final_reward"] == "26.40", str(body))
    status, body = call("POST", f"/api/v1/orders/{no}/review", student_token, {"score": 5, "content": "很快"})
    check("学生评价跑腿员", status == 201, str(body))
    status, body = call("POST", f"/api/v1/orders/{no}/review", runner_token, {"score": 5, "content": "配合好"})
    check("跑腿员反评学生（双向互评）", status == 201, str(body))

    status, body = call("GET", "/api/v1/credit/me", runner_token)
    check("信用中心（含变动记录）", status == 200 and len(body["data"]["logs"]) > 0)
    status, body = call("GET", "/api/v1/runner/income", runner_token)
    check("收入统计", status == 200 and body["data"]["balance"] and body["data"]["total_income"])
    status, body = call("POST", "/api/v1/runner/withdrawals", runner_token, {"amount": "5.00", "account": "smoke-acc"})
    check("提现申请冻结余额", status == 201, str(body))
    wd_id = body["data"]["withdrawal"]["id"] if status == 201 else None

    status, body = call("GET", "/api/v1/admin/stats/overview", admin_token)
    check("管理端看板", status == 200 and body["data"]["order_total"] >= 1, str(body))
    status, body = call("GET", "/api/v1/admin/escrow", admin_token)
    check("托管监控恒等式", status == 200 and body["data"]["matched"] is True, str(body))
    status, body = call("GET", "/api/v1/admin/fund-flows?fee_part=item", admin_token)
    check("流水按费用构成过滤", status == 200 and body["data"]["count"] >= 1)
    status, body = call("POST", f"/api/v1/admin/withdrawals/{wd_id}/audit", admin_token, {"approve": True, "reason": "冒烟通过"})
    check("提现审核通过（模拟出账）", status == 200 and body["data"]["status"] == "approved", str(body))
    status, body = call("POST", "/api/v1/admin/reconcile", admin_token)
    check("每日对账三处恒等式", status == 200 and body["data"]["passed"] is True, str(body))

    status, body = call("GET", "/api/v1/admin/users", student_token)
    check("学生访问管理端接口被拒 403", status == 403 and body["code"] == 40300, str(body))
    status, body = call("POST", f"/api/v1/orders/{no}/confirm", "invalid.token.value", {})
    check("无效 token 被拒 401", status == 401, str(body))

    print(f"\n冒烟结果：{len(PASSED)} 通过 / {len(FAILED)} 失败")
    if FAILED:
        print("失败项：" + "、".join(FAILED))
        sys.exit(1)


if __name__ == "__main__":
    main()
