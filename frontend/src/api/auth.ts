import type { Role, User } from '@/types'
import { http, isRealMode } from './http'
import { randomDelay } from '@/mock/delay'

/**
 * 认证 API。
 * - mock 模式：worker / admin 一键登录，返回假 JWT
 * - 真实模式：POST /auth/login（username + password）
 */

const DEMO_USERS: Record<Role, User> = {
  worker: {
    id: 1,
    username: 'zhangjg',
    name: '张建国',
    role: 'worker',
    position: '司钻',
  },
  admin: {
    id: 5,
    username: 'admin',
    name: '刘安全',
    role: 'admin',
    position: '司钻',
  },
}

export interface LoginResp {
  token: string
  user: User
  expiresAt: number
}

// ---- mock 模式 ----

export async function loginByRole(role: Role): Promise<LoginResp> {
  await randomDelay(360, 700)
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const payload = btoa(
    JSON.stringify({
      sub: DEMO_USERS[role].username,
      role,
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + 7200,
      jti: `mock-${Date.now().toString(36)}`,
    }),
  )
  return {
    token: `${header}.${payload}.mock-signature`,
    user: DEMO_USERS[role],
    expiresAt: Date.now() + 7200_000,
  }
}

/** mock 登出：返回黑名单提示（模拟 Redis blacklist 写入）。 */
export async function logoutApiMock(token: string): Promise<string> {
  await randomDelay(200, 400)
  const jti = JSON.parse(atob(token.split('.')[1])) as { jti: string }
  return `令牌 ${jti.jti} 已加入黑名单`
}

// ---- 真实模式 ----

interface BackendLoginResp {
  access_token: string
  user: {
    id: number
    username: string
    real_name: string
    position: string
    role: string
  }
}

export async function loginWithPassword(
  username: string,
  password: string,
): Promise<LoginResp> {
  const { data } = await http.post<BackendLoginResp>('/auth/login', {
    username,
    password,
  })
  const role = (data.user.role === 'admin' ? 'admin' : 'worker') as Role
  const user: User = {
    id: data.user.id,
    username: data.user.username,
    name: data.user.real_name || data.user.username,
    role,
    position: data.user.position as User['position'],
  }
  return {
    token: data.access_token,
    user,
    expiresAt: Date.now() + 7200_000,
  }
}

/** 真实登出：后端用 refresh 黑名单机制，前端仅清本地 token。 */
export async function logoutApiReal(): Promise<string> {
  return '令牌已在客户端清除'
}

// ---- 统一出口 ----

export function isRealAuthMode(): boolean {
  return isRealMode
}
