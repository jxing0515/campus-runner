// 生成 tabBar 图标（8 张 81x81 PNG），运行一次即可：node scripts/gen-icons.mjs
import { deflateSync } from 'node:zlib'
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const OUT = resolve(dirname(fileURLToPath(import.meta.url)), '../src/static/tabbar')
const S = 81
const GRAY = [144, 147, 153]
const BLUE = [41, 121, 255]

const blank = () => new Uint8Array(S * S * 4)

const px = (buf, x, y, [r, g, b]) => {
  if (x < 0 || y < 0 || x >= S || y >= S) return
  const i = (y * S + x) * 4
  buf[i] = r
  buf[i + 1] = g
  buf[i + 2] = b
  buf[i + 3] = 255
}
const rect = (buf, x0, y0, w, h, c) => {
  for (let y = y0; y < y0 + h; y++) for (let x = x0; x < x0 + w; x++) px(buf, x, y, c)
}
const disc = (buf, cx, cy, r, c) => {
  for (let y = cy - r; y <= cy + r; y++)
    for (let x = cx - r; x <= cx + r; x++)
      if ((x - cx) ** 2 + (y - cy) ** 2 <= r * r) px(buf, x, y, c)
}
const ring = (buf, cx, cy, r, w, c) => {
  for (let y = cy - r; y <= cy + r; y++)
    for (let x = cx - r; x <= cx + r; x++) {
      const d = Math.hypot(x - cx, y - cy)
      if (d <= r && d >= r - w) px(buf, x, y, c)
    }
}
// 三角形（用于屋顶/箭头）
const tri = (buf, ax, ay, bx, by, cx2, cy2, c) => {
  const minX = Math.min(ax, bx, cx2), maxX = Math.max(ax, bx, cx2)
  const minY = Math.min(ay, by, cy2), maxY = Math.max(ay, by, cy2)
  const area = (bx - ax) * (cy2 - ay) - (cx2 - ax) * (by - ay)
  for (let y = minY; y <= maxY; y++)
    for (let x = minX; x <= maxX; x++) {
      const w1 = ((bx - ax) * (y - ay) - (x - ax) * (by - ay)) / area
      const w2 = ((cx2 - bx) * (y - by) - (x - bx) * (cy2 - by)) / area
      const w3 = ((ax - cx2) * (y - cy2) - (x - cx2) * (ay - cy2)) / area
      if (w1 >= 0 && w2 >= 0 && w3 >= 0) px(buf, x, y, c)
    }
}

const shapes = {
  home: (b, c) => {
    tri(b, 40, 12, 8, 40, 72, 40, c)
    rect(b, 16, 38, 48, 30, c)
    rect(b, 34, 50, 12, 18, [255, 255, 255])
  },
  order: (b, c) => {
    rect(b, 14, 16, 52, 8, c)
    rect(b, 14, 36, 52, 8, c)
    rect(b, 14, 56, 34, 8, c)
  },
  message: (b, c) => {
    rect(b, 12, 16, 56, 38, c)
    tri(b, 22, 54, 40, 54, 24, 68, c)
  },
  mine: (b, c) => {
    disc(b, 40, 26, 15, c)
    tri(b, 12, 74, 68, 74, 40, 44, c)
  },
}

function png(buf) {
  const raw = Buffer.alloc(S * (S * 4 + 1))
  for (let y = 0; y < S; y++) {
    raw[y * (S * 4 + 1)] = 0
    Buffer.from(buf.buffer, y * S * 4, S * 4).copy(raw, y * (S * 4 + 1) + 1)
  }
  const chunk = (type, data) => {
    const len = Buffer.alloc(4)
    len.writeUInt32BE(data.length)
    const body = Buffer.concat([Buffer.from(type, 'ascii'), data])
    const crc = Buffer.alloc(4)
    crc.writeUInt32BE(crc32(body) >>> 0)
    return Buffer.concat([len, body, crc])
  }
  const ihdr = Buffer.alloc(13)
  ihdr.writeUInt32BE(S, 0)
  ihdr.writeUInt32BE(S, 4)
  ihdr[8] = 8
  ihdr[9] = 6
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ihdr),
    chunk('IDAT', deflateSync(raw)),
    chunk('IEND', Buffer.alloc(0)),
  ])
}

let table = null
const crc32 = (buf) => {
  if (!table) {
    table = []
    for (let n = 0; n < 256; n++) {
      let c = n
      for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1
      table[n] = c >>> 0
    }
  }
  let c = 0xffffffff
  for (const b of buf) c = table[(c ^ b) & 0xff] ^ (c >>> 8)
  return (c ^ 0xffffffff) >>> 0
}

mkdirSync(OUT, { recursive: true })
for (const [name, draw] of Object.entries(shapes)) {
  for (const [suffix, color] of [['', GRAY], ['-active', BLUE]]) {
    const b = blank()
    draw(b, color)
    writeFileSync(resolve(OUT, `${name}${suffix}.png`), png(b))
  }
}
console.log('icons written to', OUT)
