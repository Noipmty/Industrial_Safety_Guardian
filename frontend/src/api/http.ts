import axios from 'axios'

/**
 * axios 实例。
 *
 * 模式判断（优先级从高到低）：
 * 1. VITE_USE_MOCK=true  → 强制 mock 演示模式（开发本地演示用）
 * 2. VITE_API_BASE_URL 有值 → 对接指定后端
 * 3. 否则 → 默认真实模式，用相对路径 /api/v1（走 nginx 反代）
 *
 * 生产环境 ECS 上 .env 不需要设任何东西，就是默认的真实模式。
 */
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export const isRealMode = !USE_MOCK

export const http = axios.create({
  baseURL: API_BASE_URL || '/api/v1',
  timeout: 30000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('gw_token')
  if (token) {
    try {
      const parsed = JSON.parse(token)
      config.headers.Authorization = `Bearer ${parsed.token}`
    } catch {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

// 延迟注册 router 的硬引用（避免 http.ts → router → 组件 → stores → api 循环依赖）
let _router: { push: (to: string) => void } | null = null
export function registerRouter(router: { push: (to: string) => void }): void {
  _router = router
}

http.interceptors.response.use(
  (resp) => resp,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('gw_token')
      if (location.pathname !== '/login') {
        // 用 router.push 避免整页刷新
        if (_router) _router.push('/login')
        else location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)
