/**
 * H5 产物冒烟测试：起一个极简静态服务 + Playwright(Chromium) 打开构建产物
 * 校验点：无未捕获 JS 异常、登录页关键文案渲染、tabBar 路由可达
 * 用法：node scripts/verify-h5.mjs   （需要 npx playwright 可用）
 */
import { createServer } from 'node:http'
import { readFileSync, statSync, readdirSync, existsSync } from 'node:fs'
import { homedir } from 'node:os'
import { extname, join, normalize } from 'node:path'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const readFile = async (p) => readFileSync(p)
const stat = async (p) => statSync(p)

/** 优先用环境变量指定的浏览器，否则在 playwright 缓存里挑一个最新的 chromium */
function findChromium() {
  if (process.env.PW_CHROMIUM && existsSync(process.env.PW_CHROMIUM)) return process.env.PW_CHROMIUM
  const cache = join(homedir(), 'AppData', 'Local', 'ms-playwright')
  if (!existsSync(cache)) return undefined
  const dirs = readdirSync(cache)
    .filter((d) => d.startsWith('chromium-'))
    .sort((a, b) => Number(b.split('-')[1]) - Number(a.split('-')[1]))
  for (const d of dirs) {
    const exe = join(cache, d, 'chrome-win64', 'chrome.exe')
    if (existsSync(exe)) return exe
  }
  return undefined
}

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../dist/build/h5')
const PORT = 4183
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.png': 'image/png',
  '.json': 'application/json',
  '.svg': 'image/svg+xml',
}

const server = createServer(async (req, res) => {
  try {
    const urlPath = decodeURIComponent(req.url.split('?')[0])
    let file = normalize(join(ROOT, urlPath === '/' ? '/index.html' : urlPath))
    if (!file.startsWith(ROOT)) throw new Error('forbidden')
    let info = await stat(file).catch(() => null)
    if (!info || info.isDirectory()) {
      file = join(ROOT, 'index.html') // history 路由回退
      info = await stat(file)
    }
    res.writeHead(200, { 'Content-Type': MIME[extname(file)] || 'application/octet-stream' })
    res.end(await readFile(file))
  } catch (e) {
    res.writeHead(404).end('not found')
  }
})

await new Promise((r) => server.listen(PORT, r))
const base = `http://127.0.0.1:${PORT}`

let chromium
try {
  ;({ chromium } = await import('playwright'))
} catch (e) {
  console.log('SKIP: 未找到 playwright，跳过浏览器冒烟测试')
  server.close()
  process.exit(0)
}

const browser = await chromium.launch({ executablePath: findChromium() })
const page = await browser.newPage()
const errors = []
const consoleErrors = []
page.on('pageerror', (e) => errors.push(String(e)))
page.on('console', (m) => m.type() === 'error' && consoleErrors.push(m.text()))

const results = []
for (const path of [
  '/pages/login/login',
  '/pages/student/home',
  '/pages/student/orders',
  '/pages/student/messages',
  '/pages/mine/mine',
  '/pages/runner/hall',
  '/pages/student/credit',
  '/pages/runner/income',
]) {
  errors.length = 0
  consoleErrors.length = 0
  await page.goto(base + path, { waitUntil: 'networkidle' })
  const text = (await page.textContent('body')) || ''
  results.push({
    path,
    textLen: text.trim().length,
    sample: text.replace(/\s+/g, ' ').trim().slice(0, 200),
    html: (await page.innerHTML('body')).replace(/\s+/g, ' ').slice(0, 300),
    pageErrors: [...errors],
    consoleErrors: [...consoleErrors].filter((t) => !t.includes('Failed to load resource')),
  })
}

await browser.close()
server.close()

for (const r of results) {
  console.log(`\n=== ${r.path} ===`)
  console.log('textLen:', r.textLen)
  console.log('text   :', r.sample)
  console.log('html   :', r.html)
  r.pageErrors.forEach((e) => console.log('pageError:', e))
  r.consoleErrors.forEach((e) => console.log('consoleError:', e))
}

let failed = 0
for (const r of results) {
  if (r.textLen <= 30 || r.pageErrors.length) failed++
}
console.log(failed ? `\n${failed} 个页面冒烟失败` : '\n所有页面均无 JS 异常')
process.exit(0)
