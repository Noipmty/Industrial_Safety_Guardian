import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/worker/home' },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: '登录', public: true },
  },
  {
    path: '/architecture',
    name: 'architecture',
    component: () => import('@/views/ArchitectureView.vue'),
    meta: { title: '系统架构演示', public: true },
  },
  {
    path: '/worker',
    component: () => import('@/layouts/WorkerLayout.vue'),
    children: [
      { path: '', redirect: '/worker/home' },
      {
        path: 'home',
        name: 'worker-home',
        component: () => import('@/views/worker/HomeView.vue'),
        meta: { title: '首页' },
      },
      {
        path: 'chat',
        name: 'worker-chat',
        component: () => import('@/views/worker/ChatView.vue'),
        meta: { title: '安全问答' },
      },
      {
        path: 'exams',
        name: 'exam-list',
        component: () => import('@/views/worker/ExamListView.vue'),
        meta: { title: '考试中心' },
      },
      {
        path: 'exams/:id/take',
        name: 'exam-take',
        component: () => import('@/views/worker/ExamTakeView.vue'),
        meta: { title: '答题' },
      },
      {
        path: 'exams/:id/result',
        name: 'exam-result',
        component: () => import('@/views/worker/ExamResultView.vue'),
        meta: { title: '成绩详情' },
      },
    ],
  },
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAdmin: true },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      {
        path: 'dashboard',
        name: 'admin-dashboard',
        component: () => import('@/views/admin/DashboardView.vue'),
        meta: { title: '运维仪表盘' },
      },
      {
        path: 'documents',
        name: 'admin-documents',
        component: () => import('@/views/admin/DocumentsView.vue'),
        meta: { title: '文档管理' },
      },
      {
        path: 'faq',
        name: 'admin-faq',
        component: () => import('@/views/admin/FaqView.vue'),
        meta: { title: 'FAQ 管理' },
      },
      {
        path: 'users',
        name: 'admin-users',
        component: () => import('@/views/admin/UsersView.vue'),
        meta: { title: '用户与权限' },
      },
      {
        path: 'question-bank',
        name: 'admin-question-bank',
        component: () => import('@/views/admin/QuestionBankView.vue'),
        meta: { title: '题库与出卷' },
      },
      {
        path: 'review',
        name: 'admin-review',
        component: () => import('@/views/admin/ReviewView.vue'),
        meta: { title: '主观题复核' },
      },
      {
        path: 'qa-test',
        name: 'admin-qa-test',
        component: () => import('@/views/admin/QaTestView.vue'),
        meta: { title: '问答检索测试' },
      },
      {
        path: 'graph',
        name: 'admin-graph',
        component: () => import('@/views/admin/GraphView.vue'),
        meta: { title: '知识图谱' },
      },
      {
        path: 'audit',
        name: 'admin-audit',
        component: () => import('@/views/admin/AuditView.vue'),
        meta: { title: '审计日志' },
      },
      {
        path: 'eval',
        name: 'admin-eval',
        component: () => import('@/views/admin/EvalView.vue'),
        meta: { title: 'RAGAS 评测' },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/worker/home' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && auth.user?.role !== 'admin') {
    return { path: '/worker/home' }
  }
  document.title = to.meta.title
    ? `${String(to.meta.title)} · 工安卫士`
    : '工安卫士 · 石油井场安全培训系统'
  return true
})

export default router
