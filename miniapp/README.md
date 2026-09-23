# 校园互助跑腿 · 用户端（uni-app Vue3 + uni-ui）

面向学生 / 跑腿员两类使用者（同一账号，`is_runner` 控制跑腿员入口），实现《docs/API契约.md》第 1–6 节的全部用户端接口。

## 运行方式

### 方式一：HBuilderX（推荐，零配置）

1. HBuilderX 3.8+（需带 uni-app Vue3 编译器）→「文件 / 打开目录」选择本目录 `miniapp/`（打开含 `src/` 的工程根目录，不是 `src/`）。
2. 菜单「运行 / 运行到浏览器 / Chrome」跑 H5；或「运行到小程序模拟器 / 微信开发者工具」。
3. HBuilderX 会自动识别 `src/manifest.json` 的 `vueVersion: "3"` 与 `src/pages.json`，无需 `npm install`。

### 方式二：CLI

```bash
npm install
npm run dev:h5            # 开发服务器
npm run build:h5          # 生产构建 → dist/build/h5
npm run build:mp-weixin   # 微信小程序 → dist/build/mp-weixin（用微信开发者工具导入）
```

### 后端地址

`src/utils/config.js` 的 `BASE_URL` 默认 `http://127.0.0.1:8000/api/v1`；真机 / 小程序调试改成局域网地址。
浏览器直连后端需后端允许该源（CORS），或前端起代理。

## 约定

- 统一响应 `{code,message,data}`；`code!==0` 由 `src/utils/request.js` 统一 `uni.showToast`，页面只处理成功分支。
- 40100：用 refresh 静默续签一次，GET 自动重放，写操作提示重试；续签失败 `reLaunch` 到登录页。
- 轮询：我的订单（学生）5s、消息通知 10s、订单详情 8s，均在 `onHide/onUnload` 清理定时器。
- 文件：`POST /files`（`evidence` / `student_card` / `appeal`）；凭证读取走鉴权下载，H5 内联用 `fileDataUrl`。
- 模拟支付页常驻「模拟资金，无真实交易」提示，支付带 `Idempotency-Key`。

## 校验脚本

```bash
node scripts/gen-icons.mjs   # 重新生成 tabBar 图标（纯 Node，无需依赖）
node scripts/verify-h5.mjs   # 需先 build:h5，且 npx playwright 可用；无浏览器时自动 SKIP
```

## 未实装

- 微信授权登录：`src/api/auth.js` 的 `wxLogin` 仅占位（后端未提供接口）。
- 管理员端接口（契约第 7 节）不属于用户端，未实现。
