/**
 * H5 实时预览联调脚本：用 Playwright 打开 dev server，真实登录后端并截图关键页面。
 * 用法：node scripts/verify-live.mjs [baseUrl]
 *   前置：后端 runserver 127.0.0.1:8000、本工程 npm run dev:h5（默认 127.0.0.1:5180）
 */
import { existsSync, readdirSync, mkdirSync } from 'node:fs'
import { homedir } from 'node:os'
import { join, resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const BASE = process.argv[2] || 'http://127.0.0.1:5180'
const OUT = resolve(dirname(fileURLToPath(import.meta.url)), '../screenshots')

function findChromium() {
  const cache = join(homedir(), 'AppData', 'Local', 'ms-playwright')
  if (!existsSync(cache)) return undefined
  for (const d of readdirSync(cache).filter((x) => x.startsWith('chromium-')).sort((a, b) => Number(b.split('-')[1]) - Number(a.split('-')[1]))) {
    for (const inner of ['chrome-win64', 'chrome-win']) {
      const exe = join(cache, d, inner, 'chrome.exe')
      if (existsSync(exe)) return exe
    }
  }
  return undefined
}

const { chromium } = await import('playwright')
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ executablePath: findChromium() })
const page = await browser.newPage({ viewport: { width: 414, height: 860 } })
const errors = []
page.on('pageerror', (e) => errors.push(String(e)))
page.on('console', (m) => m.type() === 'error' && !m.text().includes('Failed to load resource') && errors.push('console: ' + m.text()))

async function shot(name) {
  await page.screenshot({ path: join(OUT, `${name}.png`) })
  const text = ((await page.textContent('body')) || '').replace(/\s+/g, ' ').trim()
  console.log(`--- ${name} --- ${page.url()}\n${text.slice(0, 160)}\n`)
}

/** uni-app 的 uni-input 需真实键盘输入才会触发 v-model（fill() 不生效），且切换焦点后首次按键可能丢字，故输入后校验重试 */
async function typeInto(loc, text) {
  for (let i = 0; i < 3; i++) {
    await loc.click()
    await page.waitForTimeout(250)
    await loc.press('Control+A')
    await loc.press('Delete')
    await page.keyboard.type(text, { delay: 30 })
    await page.waitForTimeout(200)
    if ((await loc.inputValue()) === text) return
  }
  throw new Error(`输入未生效：期望 ${text}，实际 ${await loc.inputValue()}`)
}

async function login(username, password) {
  for (let attempt = 1; attempt <= 2; attempt++) {
    await page.goto(`${BASE}/#/pages/login/login`, { waitUntil: 'networkidle' })
    await page.waitForTimeout(1200)
    const inputs = page.locator('input')
    await typeInto(inputs.nth(0), username)
    await typeInto(inputs.nth(1), password)
    await page.locator('uni-button.btn-primary').click()
    await page.waitForTimeout(3000)
    const url = page.url()
    if (!url.endsWith('/#/') && !url.includes('/pages/login/')) return url
    // 登录失败：多为接口限流（同 IP+账号 5 次/分钟），等窗口过期后重试一次
    if (attempt === 1) {
      console.log(`(登录未进入内页：${url}，等待 62s 重试 ${username})`)
      await page.waitForTimeout(62000)
    }
  }
  return page.url()
}

async function visit(name, path) {
  await page.goto(`${BASE}/#${path}`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1600)
  await shot(name)
}

await login('s001', 'Student@123')
await shot('01-student-home')
for (const [name, path] of [
  ['02-student-orders', '/pages/student/orders'],
  ['03-student-credit', '/pages/student/credit'],
  ['04-student-messages', '/pages/student/messages'],
  ['05-student-publish', '/pages/student/publish'],
]) await visit(name, path)

await login('r001', 'Runner@123')
await shot('06-runner-hall')
for (const [name, path] of [
  ['07-runner-tasks', '/pages/runner/tasks'],
  ['08-runner-income', '/pages/runner/income'],
  ['09-runner-withdraw', '/pages/runner/withdraw'],
  ['10-mine', '/pages/mine/mine'],
]) await visit(name, path)

await browser.close()
console.log('截图目录：', OUT)
console.log('页面异常：', errors.length ? errors : '无')
process.exit(errors.length ? 1 : 0)
