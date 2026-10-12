import axios from 'axios'

/**
 * axios 实例 —— 当前所有数据来自 src/mock，不发起真实请求。
 * 接入真实后端时：将各 api/*.ts 中的 mock 调用替换为 http.get/post 即可，
 * BASE_URL 从 .env 的 VITE_API_BASE_URL 读取。
 */
export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  timeout: 15000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('gw_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
