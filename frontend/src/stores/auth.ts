import { defineStore } from 'pinia'
import client from '@/api/client'

type UserRole = 'admin' | 'worker' | 'supervisor'

interface UserInfo {
  id: number
  username: string
  real_name: string
  position: string
  role: UserRole
}

interface LoginPayload {
  username: string
  password: string
}

interface LoginResponse {
  access_token: string
  token_type: string
  user: UserInfo
}

interface AuthState {
  token: string
  user: UserInfo | null
}

const STORAGE_KEY = 'gongan-auth'

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: '',
    user: null
  }),

  getters: {
    isAuthenticated: (state): boolean => !!state.token,

    isAdmin: (state): boolean => state.user?.role === 'admin'
  },

  actions: {
    async login(username: string, password: string): Promise<void> {
      const response = await client.post<LoginResponse>(
        '/api/v1/auth/login',
        { username, password } satisfies LoginPayload
      )
      this.token = response.access_token
      this.user = response.user
      this.persist()
      localStorage.setItem('gongan_access_token', this.token)
    },

    logout(): void {
      this.token = ''
      this.user = null
      localStorage.removeItem(STORAGE_KEY)
      localStorage.removeItem('gongan_access_token')
    },

    loadFromStorage(): void {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (!stored) return
      try {
        const data = JSON.parse(stored) as AuthState
        this.token = data.token
        this.user = data.user
        if (this.token) {
          localStorage.setItem('gongan_access_token', this.token)
        }
      } catch {
        localStorage.removeItem(STORAGE_KEY)
      }
    },

    persist(): void {
      const data: AuthState = {
        token: this.token,
        user: this.user
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
    }
  }
})
