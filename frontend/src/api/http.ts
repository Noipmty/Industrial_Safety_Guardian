import axios from 'axios'

/**
 * axios 实例。
 * - VITE_API_BASE_URL 为空 → mock 演示模式（不发起真实请求）
 * - VITE_API_BASE_URL 有值 → 对接真实后端
 */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export const isRealMode = API_BASE_URL.length > 0

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
      // legacy: raw token string
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

http.interceptors.response.use(
  (resp) => resp,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('gw_token')
      if (location.pathname !== '/login') {
        location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)
