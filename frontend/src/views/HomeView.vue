<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

function goToChat(): void {
  router.push(authStore.isAuthenticated ? '/chat' : '/login')
}

function goToExam(): void {
  router.push(authStore.isAuthenticated ? '/exam' : '/login')
}

function goToWorkbench(): void {
  router.push(authStore.isAuthenticated ? '/chat' : '/login')
}
</script>

<template>
  <div class="home-hero">
    <div class="home-hero__content">
      <div class="home-badge">工业安全 AI 助手平台</div>
      <h1 class="home-title">工安卫士</h1>
      <p class="home-subtitle">智能安全问答 · 岗位安全考试 · 隐患知识速查</p>

      <div class="home-actions">
        <button class="home-btn home-btn--primary" @click="goToChat">开始对话</button>
        <button class="home-btn home-btn--ghost" @click="goToExam">安全考试</button>
        <button class="home-btn home-btn--ghost" @click="goToWorkbench">
          {{ authStore.isAuthenticated ? '进入工作台' : '登录' }}
        </button>
      </div>

      <p v-if="authStore.isAuthenticated" class="home-welcome">
        欢迎回来，{{ authStore.user?.real_name || authStore.user?.username }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.home-hero {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f2b46 0%, #14508a 55%, #1a6fb5 100%);
}

.home-hero__content {
  text-align: center;
  padding: 0 24px;
}

.home-badge {
  display: inline-block;
  padding: 6px 16px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.35);
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.85);
  font-size: 13px;
  letter-spacing: 2px;
}

.home-title {
  margin: 24px 0 0;
  font-size: 52px;
  letter-spacing: 8px;
  color: #fff;
}

.home-subtitle {
  margin: 16px 0 0;
  font-size: 17px;
  color: rgba(255, 255, 255, 0.72);
}

.home-actions {
  margin-top: 44px;
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
}

.home-btn {
  min-width: 150px;
  padding: 12px 32px;
  font-size: 16px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.home-btn--primary {
  background: #fff;
  color: #14508a;
  font-weight: 600;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.18);
}

.home-btn--primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.24);
}

.home-btn--ghost {
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.35);
}

.home-btn--ghost:hover {
  background: rgba(255, 255, 255, 0.24);
}

.home-welcome {
  margin-top: 28px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
}
</style>
