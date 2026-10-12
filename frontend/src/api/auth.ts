import type { Role, User } from '@/types'
import { randomDelay } from '@/mock/delay'

/**
 * 认证 API（JWT mock）。
 * 演示账号：worker / admin 一键登录。
 * 登出黑名单：真实后端会将 jti 加入 Redis 黑名单，此处模拟提示。
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

export async function loginByRole(role: Role): Promise<LoginResp> {
  await randomDelay(360, 700)
  // 简易 JWT 形状（header.payload.signature，全部 base64 假数据）
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

/** 登出：返回黑名单提示（模拟 Redis blacklist 写入）。 */
export async function logoutApi(token: string): Promise<string> {
  await randomDelay(200, 400)
  const jti = JSON.parse(atob(token.split('.')[1])) as { jti: string }
  return `令牌 ${jti.jti} 已加入黑名单`
}
