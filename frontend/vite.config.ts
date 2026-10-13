import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// 开发代理目标：.env 里 VITE_API_BASE_URL 的 origin 部分
// 没设就默认代理到 ECS 线上后端（方便本地开发调试真实接口）
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendOrigin = env.VITE_API_BASE_URL
    ? new URL(env.VITE_API_BASE_URL).origin
    : 'http://47.110.42.78'

  return {
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
      proxy: {
        '/api/v1': {
          target: backendOrigin,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  }
})
