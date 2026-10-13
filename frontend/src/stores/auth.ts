import { defineStore } from 'pinia'
import type { Role, User } from '@/types'
import {
  loginByRole,
  loginWithPassword,
  logoutApiMock,
  logoutApiReal,
  isRealAuthMode,
} from '@/api/auth'

const TOKEN_KEY = 'gw_token'

interface AuthState {
  token: string
  user: User | null
  /** 登出时的黑名单提示 */
  logoutNotice: string
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: '',
    user: null,
    logoutNotice: '',
  }),
  getters: {
    isWorker: (s) => s.user?.role === 'worker',
    isAdmin: (s) => s.user?.role === 'admin',
    roleLabel: (s) => (s.user?.role === 'admin' ? '管理员' : '工人'),
    isRealMode: () => isRealAuthMode(),
  },
  actions: {
    /** App 挂载时从 localStorage 恢复会话。 */
    restore() {
      const raw = localStorage.getItem(TOKEN_KEY)
      if (!raw) return
      try {
        const { token, user, expiresAt } = JSON.parse(raw) as {
          token: string
          user: User
          expiresAt: number
        }
        if (expiresAt > Date.now()) {
          this.token = token
          this.user = user
        } else {
          localStorage.removeItem(TOKEN_KEY)
        }
      } catch {
        localStorage.removeItem(TOKEN_KEY)
      }
    },
    /** mock 模式：按角色一键登录 */
    async login(role: Role) {
      const resp = await loginByRole(role)
      this.token = resp.token
      this.user = resp.user
      localStorage.setItem(
        TOKEN_KEY,
        JSON.stringify({
          token: resp.token,
          user: resp.user,
          expiresAt: resp.expiresAt,
        }),
      )
    },
    /** 真实模式：用户名密码登录 */
    async loginWithCreds(username: string, password: string) {
      const resp = await loginWithPassword(username, password)
      this.token = resp.token
      this.user = resp.user
      localStorage.setItem(
        TOKEN_KEY,
        JSON.stringify({
          token: resp.token,
          user: resp.user,
          expiresAt: resp.expiresAt,
        }),
      )
    },
    async logout() {
      if (this.token) {
        try {
          this.logoutNotice = isRealAuthMode()
            ? await logoutApiReal()
            : await logoutApiMock(this.token)
        } catch {
          this.logoutNotice = ''
        }
      }
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
    },
  },
})
