<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const menu = [
  { index: '/admin/dashboard', label: '运维仪表盘', icon: 'Odometer' },
  { index: '/admin/documents', label: '文档管理', icon: 'Document' },
  { index: '/admin/faq', label: 'FAQ 管理', icon: 'ChatDotRound' },
  { index: '/admin/users', label: '用户与权限', icon: 'User' },
  { index: '/admin/question-bank', label: '题库与出卷', icon: 'EditPen' },
  { index: '/admin/review', label: '主观题复核', icon: 'Finished' },
  { index: '/admin/qa-test', label: '问答检索测试', icon: 'ChatLineSquare' },
  { index: '/admin/graph', label: '知识图谱', icon: 'Share' },
  { index: '/admin/audit', label: '审计日志', icon: 'DocumentChecked' },
  { index: '/admin/eval', label: 'RAGAS 评测', icon: 'TrendCharts' },
]

const pageTitle = computed(() => {
  const hit = menu.find((m) => m.index === route.path)
  return hit?.label ?? '运维控制台'
})

async function onLogout(): Promise<void> {
  await auth.logout()
  if (auth.logoutNotice) {
    ElMessage({ message: `登出成功，${auth.logoutNotice}`, type: 'success', duration: 3200 })
  }
  router.push('/login')
}
</script>

<template>
  <div class="min-h-screen bg-mist">
    <!-- 侧边栏 -->
    <aside class="fixed left-0 top-0 bottom-0 w-60 navy-hero z-40 flex flex-col hidden lg:flex">
      <div class="h-16 flex items-center gap-2.5 px-5 shrink-0">
        <div class="w-9 h-9 rounded-xl bg-white/10 flex items-center justify-center">
          <svg viewBox="0 0 24 24" class="w-5 h-5" fill="none" aria-hidden="true">
            <path d="M12 3L5 21M12 3l7 18M8.2 13.5h7.6M9.6 9.5h4.8" stroke="#FF7A1A" stroke-width="1.8" stroke-linecap="round" />
          </svg>
        </div>
        <div>
          <p class="text-white font-bold text-[15px] leading-tight">工安卫士</p>
          <p class="text-white/40 text-[10px] leading-tight">管理控制台</p>
        </div>
      </div>
      <el-menu
        :default-active="route.path"
        router
        class="admin-menu flex-1 border-0!"
      >
        <el-menu-item v-for="m in menu" :key="m.index" :index="m.index">
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.label }}</span>
        </el-menu-item>
      </el-menu>
      <div class="p-4 shrink-0 space-y-2">
        <router-link
          to="/architecture"
          class="flex items-center gap-2 px-3 py-2 rounded-xl text-white/55 hover:text-white hover:bg-white/5 text-xs transition-colors"
        >
          <el-icon><Guide /></el-icon>系统架构演示
        </router-link>
        <div class="text-[10px] text-white/25 leading-relaxed px-3">
          mock 演示数据 · 非生产环境
        </div>
      </div>
    </aside>

    <!-- 主区域 -->
    <div class="lg:ml-60 flex flex-col min-h-screen">
      <!-- 顶栏 -->
      <header class="h-16 bg-white/90 backdrop-blur border-b border-gray-100 sticky top-0 z-30 flex items-center px-4 sm:px-6 gap-3">
        <h1 class="text-lg font-bold text-navy flex-1">{{ pageTitle }}</h1>
        <span class="chip bg-teal-50 text-teal-600 border border-teal-200 hidden sm:inline-flex">
          <span class="w-1.5 h-1.5 rounded-full bg-teal-500"></span>系统运行正常
        </span>
        <el-dropdown trigger="click">
          <button class="flex items-center gap-2 px-2 py-1.5 rounded-xl hover:bg-mist transition-colors">
            <span class="w-8 h-8 rounded-full navy-hero text-white text-xs font-bold flex items-center justify-center">
              {{ auth.user?.name.slice(0, 1) ?? '管' }}
            </span>
            <span class="text-sm text-graphite hidden sm:inline">{{ auth.user?.name }}</span>
            <el-icon :size="12" class="text-graphite/40"><ArrowDown /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>管理员 · admin</el-dropdown-item>
              <el-dropdown-item divided @click="onLogout">
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </header>

      <main class="flex-1 p-4 sm:p-6 max-w-[1400px] w-full mx-auto">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.admin-menu {
  background: transparent;
  padding: 8px 12px;
}
.admin-menu .el-menu-item {
  color: rgba(255, 255, 255, 0.6);
  border-radius: 10px;
  height: 44px;
  margin-bottom: 2px;
}
.admin-menu .el-menu-item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}
.admin-menu .el-menu-item.is-active {
  background: rgba(255, 122, 26, 0.16);
  color: #ff8a33;
  font-weight: 600;
}
</style>
