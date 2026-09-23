import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'

export default defineConfig({
  plugins: [uni()],
  server: {
    host: '127.0.0.1',
    port: 5180, // 与 admin-web(5173) 区分，避免端到端演示时端口歧义
  },
})
