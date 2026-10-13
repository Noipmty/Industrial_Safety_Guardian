import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// .env 里的 VITE_API_BASE_URL（如 http://47.110.42.78/api/v1）
const backendOrigin = process.env.VITE_API_BASE_URL
  ? new URL(process.env.VITE_API_BASE_URL).origin
  : ''

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5174,
    host: true,
    // 开发代理：前端 /api/v1/* → 真实后端（跳过 CORS）
    proxy: backendOrigin
      ? {
          '/api/v1': {
            target: backendOrigin,
            changeOrigin: true,
            secure: false,
          },
        }
      : undefined,
  },
})
