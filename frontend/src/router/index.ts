import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue')
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue')
  },
  {
    path: '/chat',
    name: 'chat',
    component: () => import('@/views/ChatView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/docs',
    name: 'docs',
    component: () => import('@/views/DocQueryView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/exam',
    name: 'exam',
    component: () => import('@/views/ExamListView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/exam/take/:examId',
    name: 'exam-take',
    component: () => import('@/views/ExamTakeView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/exam/result/:examId',
    name: 'exam-result',
    component: () => import('@/views/ExamResultView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    name: 'admin',
    component: () => import('@/views/AdminView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return { name: 'home' }
  }

  return true
})

export default router
