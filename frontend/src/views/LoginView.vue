<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { Role } from '@/types'
import { useAuthStore } from '@/stores/auth'
import { isRealMode } from '@/api/http'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const role = ref<Role>('worker')
const loading = ref(false)

// 真实模式表单
const formUser = ref('')
const formPass = ref('')

const DEMO: Record<Role, { username: string; password: string; name: string; position: string; desc: string }> = {
  worker: {
    username: 'zhangjg',
    password: 'zhangjg123',
    name: '张建国',
    position: '司钻',
    desc: '问答 / 考试 / 成绩',
  },
  admin: {
    username: 'admin',
    password: 'admin8888',
    name: '刘安全',
    position: '安全员',
    desc: '仪表盘 / 全部管理功能',
  },
}

const redirect = computed(() => {
  const r = route.query.redirect
  return typeof r === 'string' && r.startsWith('/') ? r : ''
})

async function login(): Promise<void> {
  loading.value = true
  try {
    await auth.login(role.value)
    ElMessage.success(`欢迎回来，${auth.user?.name}`)
    router.push(redirect.value || (role.value === 'admin' ? '/admin/dashboard' : '/worker/home'))
  } finally {
    loading.value = false
  }
}

async function loginReal(): Promise<void> {
  if (!formUser.value.trim() || !formPass.value.trim()) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await auth.loginWithCreds(formUser.value.trim(), formPass.value)
    ElMessage.success(`欢迎回来，${auth.user?.name}`)
    router.push(redirect.value || (auth.isAdmin ? '/admin/dashboard' : '/worker/home'))
  } catch {
    ElMessage.error('登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen navy-hero relative overflow-hidden flex items-center justify-center p-4">
    <!-- 背景装饰：井架剪影 + 网格 -->
    <svg class="absolute bottom-0 left-0 right-0 w-full opacity-[0.08]" viewBox="0 0 1440 320" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
      <path d="M120 320L200 60l80 260M155 200h90M140 250h120M170 120h60" stroke="#fff" stroke-width="6" fill="none" stroke-linecap="round" />
      <path d="M1240 320l70-200 70 200M1268 240h84M1256 280h108" stroke="#fff" stroke-width="5" fill="none" stroke-linecap="round" />
      <circle cx="720" cy="80" r="46" stroke="#FF7A1A" stroke-width="4" fill="none" />
      <path d="M688 80h64M720 48v64" stroke="#FF7A1A" stroke-width="4" />
    </svg>

    <div class="w-full max-w-sm relative z-10 space-y-4">
      <!-- 品牌 -->
      <div class="text-center space-y-2">
        <div class="w-16 h-16 mx-auto rounded-2xl bg-white/10 backdrop-blur flex items-center justify-center border border-white/15">
          <svg viewBox="0 0 24 24" class="w-9 h-9" fill="none" aria-hidden="true">
            <path d="M12 3L5 21M12 3l7 18M8.2 13.5h7.6M9.6 9.5h4.8" stroke="#FF7A1A" stroke-width="1.8" stroke-linecap="round" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-white tracking-wide">工安卫士</h1>
        <p class="text-white/50 text-sm">石油井场安全培训系统 · RAG 智能问答</p>
      </div>

      <!-- 登录卡片 -->
      <div class="bg-white rounded-2xl shadow-pop p-6 space-y-5">
        <el-alert
          v-if="auth.logoutNotice"
          type="info"
          :closable="false"
          show-icon
          :title="`安全提示：${auth.logoutNotice}，旧令牌已失效`"
          class="rounded-xl!"
        />

        <!-- ===== 真实模式：用户名密码表单 ===== -->
        <template v-if="isRealMode">
          <div class="space-y-3">
            <el-input
              v-model="formUser"
              placeholder="用户名"
              size="large"
              prefix-icon="User"
              @keydown.enter="loginReal"
            />
            <el-input
              v-model="formPass"
              type="password"
              placeholder="密码"
              size="large"
              prefix-icon="Lock"
              show-password
              @keydown.enter="loginReal"
            />
          </div>
          <button class="btn-hero" :disabled="loading" @click="loginReal">
            <span v-if="loading" class="inline-flex items-center gap-2">
              <el-icon class="animate-spin"><Loading /></el-icon>登录中…
            </span>
            <span v-else>登录</span>
          </button>
          <div class="rounded-xl border border-dashed border-gray-200 bg-mist/60 p-3 space-y-1 text-xs text-graphite/60">
            <p>测试账号：zhangjg / admin　密码：zhangjg123 / admin8888</p>
          </div>
        </template>

        <!-- ===== Mock 模式：角色切换一键登录 ===== -->
        <template v-else>
          <div>
            <p class="text-xs text-graphite/50 mb-2 font-medium">选择演示角色</p>
            <div class="grid grid-cols-2 gap-2 p-1 bg-mist rounded-xl">
              <button
                v-for="r in (['worker', 'admin'] as const)"
                :key="r"
                class="h-10 rounded-lg text-sm font-semibold transition-all flex items-center justify-center gap-1.5"
                :class="role === r ? 'bg-white text-navy shadow-card' : 'text-graphite/45'"
                @click="role = r"
              >
                <el-icon><component :is="r === 'worker' ? 'User' : 'Setting'" /></el-icon>
                {{ r === 'worker' ? '工人端' : '管理端' }}
              </button>
            </div>
          </div>

          <div class="rounded-xl border border-dashed border-gray-200 bg-mist/60 p-3 space-y-1.5 text-xs text-graphite/70">
            <p class="flex justify-between">
              <span class="text-graphite/45">演示账号</span>
              <span class="font-mono font-semibold">{{ DEMO[role].username }} / {{ DEMO[role].password }}</span>
            </p>
            <p class="flex justify-between">
              <span class="text-graphite/45">身份</span>
              <span>{{ DEMO[role].name }} · {{ DEMO[role].position }}</span>
            </p>
            <p class="flex justify-between">
              <span class="text-graphite/45">可访问</span>
              <span>{{ DEMO[role].desc }}</span>
            </p>
          </div>

          <button class="btn-hero" :disabled="loading" @click="login">
            <span v-if="loading" class="inline-flex items-center gap-2">
              <el-icon class="animate-spin"><Loading /></el-icon>登录中…
            </span>
            <span v-else>一键登录（JWT mock · 2h 有效）</span>
          </button>

          <p class="text-[11px] text-graphite/40 text-center leading-relaxed">
            登出后令牌将加入 Redis 黑名单，防止重放攻击
          </p>
        </template>
      </div>

      <div class="text-center">
        <router-link to="/architecture" class="text-white/55 hover:text-safety text-xs inline-flex items-center gap-1">
          <el-icon><Guide /></el-icon>查看系统架构演示 →
        </router-link>
      </div>
    </div>
  </div>
</template>
