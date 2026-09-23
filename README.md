# 校园互助跑腿接单与信用管理系统

校内零散跑腿需求（取快递、带餐、代取物品）的**发布 → 接单 → 履约 → 结算 → 评价**全流程闭环，
以信用分约束双方行为，以平台托管（**模拟记账**）保障交易安全。

> ⚠️ **合规声明**：系统内「支付 / 托管 / 结算 / 退款 / 提现」**全部为内部模拟记账**，
> 无真实资金、无第三方支付通道、不归集任何真实钱款；所有数据均为演示虚构数据。

## 1. 交付物一览

| 目录 | 内容 | 技术栈 |
|------|------|--------|
| `backend/` | 后端服务 + 定时任务 + 单测 + 初始化脚本 | Django 5.2 + DRF + SimpleJWT + MySQL 8 |
| `admin-web/` | 管理端 Web（平台管理员） | Vue3 + Vite + Element Plus + Pinia + ECharts |
| `miniapp/` | 用户端小程序（学生 / 跑腿员） | Vue3 + uni-app + uni-ui |
| `docs/` | API 契约、数据库设计、部署运维、用户手册、测试报告、演示脚本、覆盖率报告 | — |
| `计划书.md` | 原始项目计划书（方向参考） | — |

## 2. 快速启动

### 2.1 后端（必需）

```bash
# 1) 依赖（Python 3.12）
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend/requirements.txt   # Linux/mac: .venv/bin/python

# 2) 数据库（MySQL 8.0.x，Django 5.2 LTS 兼容 8.0）
mysql -uroot -p -e "CREATE DATABASE db_runner DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 3) 环境变量
copy backend\.env.example backend\.env      # 修改 DB_PASSWORD / DJANGO_SECRET_KEY

# 4) 建表 + 缓存表 + 演示数据
cd backend
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py createcachetable
..\.venv\Scripts\python.exe manage.py seed_demo            # 需要重置加 --reset

# 5) 启动（三选一）
..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000     # 开发
..\.venv\Scripts\python.exe manage.py beat                          # 定时任务循环（另开终端）
..\.venv\Scripts\python.exe scripts\smoke_api.py                    # 接口冒烟（22 项）
```

- 接口前缀 `http://127.0.0.1:8000/api/v1/`
- Swagger：`http://127.0.0.1:8000/api/docs/`

### 2.2 管理端 Web

```bash
cd admin-web
npm install
npm run dev        # http://localhost:5173 （已配 proxy /api → 127.0.0.1:8000）
npm run build      # 产物 dist/
```

### 2.3 用户端小程序

```bash
cd miniapp
npm install
npm run build:h5             # H5 试跑（产物 dist/build/h5）
# 微信小程序：HBuilderX 打开 miniapp 目录 → 运行到微信开发者工具（需填 src/manifest.json 的 appid）
```

## 3. 演示账号（`seed_demo` 生成）

| 角色 | 账号 | 密码 | 说明 |
|------|------|------|------|
| 超级管理员 | `admin` | `Admin@123` | 全部功能（规则配置、封禁、公告） |
| 运营管理员 | `operator` | `Admin@123` | 审核/监控/仲裁/提现，不可改规则与封禁 |
| 学生 | `s001` / `s002` / `s003` | `Student@123` | 发单、支付、确认、评价、申诉 |
| 跑腿员 | `r001` / `r002` | `Runner@123` | 已通过认证，接单、打卡、提现 |

演示数据含 10 笔覆盖**全状态**的订单（待支付/待接单/已接单/配送中/待确认/已完成/已取消/申诉中/异常）、
3 笔提现（待审/通过/驳回）与 1 条公告投递。

## 4. 关键设计

- **状态机收口**：`backend/apps/orders/state.py` 的合法迁移表是唯一入口，每次迁移写状态日志；占位态（申诉中/异常）保存 `prev_status` 快照，退出时恢复。
- **资金闭环**：支付 → 托管 → 结算/退款；`FundFlow.idem_key` 唯一约束防重复支付/结算/提现；代付差额自动退回学生。
- **并发安全**：接单用 `UPDATE ... WHERE status='pending_accept' AND runner_id IS NULL` 原子抢占；金额变动对订单行/用户行/平台账户行 `select_for_update`。
- **无 Redis 依赖**：规则缓存、限流计数、分布式锁全部走 Django 缓存框架（默认 DatabaseCache，`cache.add()` 原子性即互斥锁）。
- **定时任务**：`manage.py beat` 循环驱动 6 类任务 + 每日对账，规则阈值全部存规则配置表可在线调整。
- **信用温和联动**：`[0,150]` 区间 + 等级权限映射（受限禁发单接单、一般禁平台代付）+ 周期恢复 + 申诉恢复原值。

## 5. 测试与验证

```bash
cd backend
..\.venv\Scripts\python.exe -m pytest --cov=apps --cov-report=term-missing
```

- 39 项用例全通过；总覆盖率 74%，核心业务模块 78–97%（详见 `docs/测试报告.md`）
- 覆盖：状态机合法/非法迁移、三种支付模式金额、代付四规则、提现冻结与回滚、对账三恒等式、
  信用边界与叠加、并发接单仅一人成功、重复确认/提现幂等、越权与封禁 JWT 失效
- HTTP 端到端冒烟：`backend/scripts/smoke_api.py`，22 项全通过

## 6. Git 规范

主干 `main`；提交信息遵循 Conventional Commits（`feat` / `fix` / `docs` / `test` / `chore`）；
密钥与 `.env` 不入库（见 `.gitignore`）。
