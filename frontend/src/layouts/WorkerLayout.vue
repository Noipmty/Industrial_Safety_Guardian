<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const tabs = [
  { to: '/worker/home', label: '首页', icon: 'HomeFilled' },
  { to: '/worker/chat', label: '安全问答', icon: 'ChatDotRound' },
  { to: '/worker/exams', label: '考试中心', icon: 'EditPen' },
]

function isActive(to: string): boolean {
  if (to === '/worker/home') return route.path === to
  return route.path.startsWith(to)
}

async function onLogout(): Promise<void> {
  await auth.logout()
  if (auth.logoutNotice) {
    ElMessage({ message: `登出成功，${auth.logoutNotice}`, type: 'success', duration: 3200 })
  }
  router.push('/login')
}
</script>

<template>
  <div class="min-h-screen bg-mist flex flex-col">
    <!-- 顶部栏 -->
    <header class="glass sticky top-0 z-30 border-b border-white/60">
      <div class="max-w-2xl mx-auto px-4 h-14 flex items-center gap-3">
        <div class="w-9 h-9 rounded-xl navy-hero flex items-center justify-center shrink-0 shadow-card">
          <svg viewBox="0 0 24 24" class="w-5 h-5" fill="none" aria-hidden="true">
            <path d="M12 3L5 21M12 3l7 18M8.2 13.5h7.6M9.6 9.5h4.8" stroke="#FF7A1A" stroke-width="1.8" stroke-linecap="round" />
          </svg>
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-[15px] font-bold text-navy leading-tight">工安卫士</p>
          <p class="text-[10px] text-graphite/45 leading-tight">石油井场安全培训系统</p>
        </div>
        <router-link
          to="/architecture"
          class="text-xs text-graphite/50 hover:text-safety hidden sm:flex items-center gap-1"
        >
          <el-icon><Guide /></el-icon>架构演示
        </router-link>
        <el-dropdown trigger="click">
          <button class="flex items-center gap-1.5 px-2 py-1 rounded-full bg-white shadow-card text-xs text-graphite">
            <span class="w-6 h-6 rounded-full bg-safety-light text-safety-dark text-[11px] font-bold flex items-center justify-center">
              {{ auth.user?.name.slice(0, 1) ?? '工' }}
            </span>
            <span class="max-w-20 truncate">{{ auth.user?.name }}</span>
            <el-icon :size="12"><ArrowDown /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>
                {{ auth.roleLabel }} · {{ auth.user?.position }}
              </el-dropdown-item>
              <el-dropdown-item divided @click="onLogout">
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <!-- 内容 -->
    <main class="flex-1 w-full max-w-2xl mx-auto px-4 py-4 pb-24">
      <router-view />
    </main>

    <!-- 底部导航（移动优先） -->
    <nav class="fixed bottom-0 inset-x-0 z-30 glass border-t border-white/70 pb-[env(safe-area-inset-bottom)]">
      <div class="max-w-2xl mx-auto grid grid-cols-3 h-16">
        <router-link
          v-for="t in tabs"
          :key="t.to"
          :to="t.to"
          class="flex flex-col items-center justify-center gap-0.5 text-[11px]"
          :class="isActive(t.to) ? 'text-safety font-semibold' : 'text-graphite/45'"
        >
          <el-icon :size="20"><component :is="t.icon" /></el-icon>
          {{ t.label }}
        </router-link>
      </div>
    </nav>
  </div>
</template>
