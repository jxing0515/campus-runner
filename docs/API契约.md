# API 契约（v1）— 校园互助跑腿系统

- 前缀：`/api/v1/`
- 认证：`Authorization: Bearer <access>`（SimpleJWT，access 30 分钟 / refresh 7 天，refresh 黑名单）
- 统一响应：`{"code":0,"message":"ok","data":...}`；错误码：`0` 成功、`40001` 参数错误、`40100` 未认证、`40300` 无权限、`40400` 不存在、`40900` 状态冲突/重复动作、`50000` 服务端错误
- 分页：`?page=&page_size=`（默认 20，最大 100），`data` 为 `{count,next,previous,results}`
- 时间：`YYYY-MM-DD HH:MM:SS`（Asia/Shanghai）；金额：字符串两位小数
- 角色：`user`（学生/跑腿员同一账号，`is_runner` 控制跑腿员模式）/ `admin`（`super_admin`、`operator`）

## 用户对象

```json
{"id":1,"username":"2021001","name":"张三","role":"user","is_runner":true,
 "cert_status":"approved","credit_score":100,"credit_level":"excellent",
 "runner_balance":"12.00","banned":false,"completed_count":3,"good_rate":1.0,"perms":[]}
```

`credit_level`: `excellent(>=90) / good(80-89) / normal(60-79) / limited(<60)`
`cert_status`: `none/pending/approved/rejected`
订单 `status`：`pending_pay / pending_accept / accepted / picked / delivering / pending_confirm / completed / cancelled / refunded / appealing / abnormal`

## 1. 认证 `/auth`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/auth/register` | `{username,password,name}` → user；密码≥8 位含字母数字 |
| POST | `/auth/login` | `{username,password}` → `{access,refresh,user}`；同 IP+账号 5 次/分钟，失败 5 次锁 15 分钟 |
| POST | `/auth/refresh` | `{refresh}` → `{access}` |
| POST | `/auth/logout` | `{refresh}` → 拉黑 |
| GET | `/auth/me` | 当前用户 |
| POST | `/auth/password` | `{old_password,new_password}` → 拉黑全部 refresh |

## 2. 文件与通知

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/files` | multipart `file`、`kind`(`evidence/student_card/appeal`) → `{id,name}`；仅 jpg/png ≤2MB |
| GET | `/files/<id>` | 鉴权下载（裸 MEDIA 不开放） |
| GET | `/notifications?unread=1&page=` | 消息列表（10s 轮询） |
| POST | `/notifications/<id>/read` | 标记已读 |
| POST | `/notifications/read-all` | 全部已读 |

## 3. 信用

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/credit/me` | `{score,level,limits:{can_publish,can_accept,can_prepay},logs:[]}` |
| GET | `/credit/logs?page=` | 变动记录（含变动前分数、原因码） |

## 4. 跑腿员认证

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/runner/certification` | 认证状态与驳回原因 |
| POST | `/runner/certification` | `{student_no,real_name,card_file_id}` → 待审核 |

## 5. 订单

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/orders` | 发单：`{description,pickup_address,delivery_address,time_window_start,time_window_end,runner_fee,item_fee_mode(none/offline/platform),item_fee_estimate}` |
| GET | `/orders?status=&role=student\|runner&page=` | 我的订单 |
| GET | `/orders/<order_no>` | 详情（状态日志、凭证、评价、资金流水） |
| POST | `/orders/<order_no>/pay` | 模拟支付 → 待接单；`Idempotency-Key` 头生效 |
| POST | `/orders/<order_no>/cancel` | `{reason}` 按取消矩阵 |
| POST | `/orders/<order_no>/confirm` | 确认完成 → 结算（幂等） |
| POST | `/orders/<order_no>/review` | `{score:1-5,content}` 双向评价，仅已完成且无申诉 |
| POST | `/orders/<order_no>/appeal` | `{appeal_type,description,card_file_ids:[]}` → 申诉中（资金留托管） |
| GET | `/orders/available?sort=time\|fee` | 跑腿员待接单列表 |
| POST | `/orders/<order_no>/accept` | 原子抢占；自接单 400/409 |
| POST | `/orders/<order_no>/pickup` | `{file_ids:[]}` → 待取件/配送中 |
| POST | `/orders/<order_no>/deliver` | `{file_ids:[],actual_item_fee}` → 待确认（代付模式必填实际物品费） |

## 6. 收入与提现

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/runner/income` | `{total_income,balance,records:[]}` |
| GET | `/runner/withdrawals?page=` | 我的提现 |
| POST | `/runner/withdrawals` | `{amount,method,account}` 申请即冻结扣减 |

## 7. 管理端 `/admin`（`super_admin` 全部；`operator` 不可改规则/封禁用户/加管理员）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/admin/certifications?status=` | 认证审核列表 |
| POST | `/admin/certifications/<id>/audit` | `{approve,reason}` |
| GET | `/admin/users?keyword=&banned=` | 用户管理 |
| POST | `/admin/users/<id>/ban` | `{banned,reason}`（super_admin）→ JWT 拉黑 |
| POST | `/admin/users/<id>/credit` | `{delta,reason}` 手动调整信用 |
| GET | `/admin/demands?status=` | 需求监控 |
| GET | `/admin/orders?status=&abnormal=1` | 订单监控 |
| GET | `/admin/orders/<order_no>` | 含状态日志 |
| POST | `/admin/orders/<order_no>/resolve` | `{action:complete\|cancel,remark}` 异常单人工处理 |
| GET | `/admin/fund-flows?type=&fee_part=&order_no=` | 支付流水（类型 × 费用构成双维过滤） |
| GET | `/admin/fund-flows/export` | CSV |
| GET | `/admin/escrow` | 托管监控：Σ托管中流水 vs 平台账户 |
| GET | `/admin/settlements` | 结算流水 |
| GET | `/admin/refunds` | 退款流水 |
| GET | `/admin/withdrawals?status=` | 提现审核列表 |
| POST | `/admin/withdrawals/<id>/audit` | `{approve,reason}` |
| GET/POST | `/admin/rules` | 信用/超时规则（super_admin 可写，写入后删缓存） |
| PUT | `/admin/rules/<id>` | 修改规则 |
| GET | `/admin/appeals?status=` | 仲裁列表 |
| POST | `/admin/appeals/<id>/arbitrate` | `{winner:student\|runner\|partial,student_ratio:0-100,remark}` |
| GET | `/admin/stats/overview` | 看板汇总 |
| GET | `/admin/stats/orders-trend?days=7` | 订单量趋势 |
| GET | `/admin/stats/credit-distribution` | 信用分布 |
| GET/POST | `/admin/announcements` | 公告（发布时投递通知） |
| DELETE | `/admin/announcements/<id>` | 删除 |
| GET | `/admin/operation-logs` | 操作日志 |
| GET | `/admin/operation-logs/export` | CSV |
