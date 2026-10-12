<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useExamStore } from '@/stores/exam'
import AppSkeleton from '@/components/common/AppSkeleton.vue'
import { POSITIONS } from '@/types'

const auth = useAuthStore()
const exam = useExamStore()

onMounted(() => {
  void exam.loadExams()
})

const pendingExams = computed(() => exam.exams.filter((e) => e.status === 'pending').slice(0, 2))
const hour = new Date().getHours()
const greeting = hour < 6 ? '夜班辛苦了' : hour < 12 ? '早上好' : hour < 18 ? '下午好' : '晚上好'

const reminders = [
  '今天井场风力 6 级，高空作业请停止，工具绑定防坠落。',
  '循环罐区域硫化氢探头周检，发现报警立即上风向撤离。',
  '交接班时请核对防喷器试关井记录，确认液动平板阀状态。',
]
const reminder = reminders[new Date().getDate() % reminders.length]

const progress = { done: 12, total: 18 }
const recentQa = [
  { q: '发现溢流后第一步做什么？', t: '昨天 14:32' },
  { q: '硫化氢报警阈值是多少？', t: '10-10 09:12' },
  { q: '高处作业安全带怎么挂？', t: '10-08 16:45' },
]

const entries = [
  { to: '/worker/chat', label: '安全问答', desc: '有问必答 · 带规程引用', icon: 'ChatDotRound', cls: 'bg-safety text-white' },
  { to: '/worker/exams', label: '考试中心', desc: '待考 ' + pendingExams.value.length + ' 场', icon: 'EditPen', cls: 'bg-navy text-white' },
]
</script>

<template>
  <div class="space-y-4">
    <!-- 问候 + 岗位 -->
    <section class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold text-navy">{{ greeting }}，{{ auth.user?.name }}</h1>
        <p class="text-xs text-graphite/50 mt-0.5">祝您今天安全生产</p>
      </div>
      <span class="chip bg-safety-light text-safety-dark border border-orange-200">
        <el-icon><User /></el-icon>{{ auth.user?.position ?? POSITIONS[0] }}
      </span>
    </section>

    <!-- 今日安全提醒 -->
    <section class="navy-hero rounded-2xl p-4 sm:p-5 text-white relative overflow-hidden">
      <svg class="absolute -right-3 -bottom-4 w-28 h-28 opacity-10" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M12 3L5 21M12 3l7 18M8.2 13.5h7.6M9.6 9.5h4.8" stroke="#fff" stroke-width="1.4" stroke-linecap="round" />
      </svg>
      <p class="text-xs font-semibold text-safety flex items-center gap-1 mb-1.5">
        <el-icon><Bell /></el-icon>今日安全提醒
      </p>
      <p class="text-[15px] leading-relaxed">{{ reminder }}</p>
    </section>

    <!-- 快捷入口 -->
    <section class="grid grid-cols-2 gap-3">
      <router-link
        v-for="e in entries"
        :key="e.to"
        :to="e.to"
        class="card p-4 flex flex-col gap-2 hover:shadow-pop transition-shadow"
      >
        <span class="w-10 h-10 rounded-xl flex items-center justify-center" :class="e.cls">
          <el-icon :size="20"><component :is="e.icon" /></el-icon>
        </span>
        <span class="font-bold text-navy">{{ e.label }}</span>
        <span class="text-[11px] text-graphite/50">{{ e.desc }}</span>
      </router-link>
    </section>

    <!-- 学习进度 -->
    <section class="card p-4 space-y-2">
      <div class="flex items-center justify-between">
        <p class="section-title"><el-icon><Notebook /></el-icon>本季度学习进度</p>
        <span class="text-xs text-graphite/50">{{ progress.done }}/{{ progress.total }} 课时</span>
      </div>
      <el-progress :percentage="Math.round((progress.done / progress.total) * 100)" :stroke-width="10" />
      <p class="text-[11px] text-graphite/45">完成全部课时可解锁「井控操作之星」电子徽章</p>
    </section>

    <!-- 待考考试 -->
    <section class="space-y-2">
      <p class="section-title"><el-icon><Calendar /></el-icon>待考考试</p>
      <AppSkeleton v-if="exam.loading" type="list" :rows="2" />
      <template v-else>
        <router-link
          v-for="e in pendingExams"
          :key="e.id"
          :to="`/worker/exams/${e.id}/take`"
          class="card p-4 flex items-center gap-3 hover:shadow-pop transition-shadow"
        >
          <div class="flex-1 min-w-0">
            <p class="font-semibold text-navy text-sm truncate">{{ e.title }}</p>
            <p class="text-[11px] text-graphite/50 mt-0.5">
              {{ e.questionCount }} 题 · {{ e.durationMin }} 分钟 · 截止 {{ e.deadline }}
            </p>
          </div>
          <el-button type="primary" size="small" round>去考试</el-button>
        </router-link>
        <div v-if="!pendingExams.length" class="card p-4 text-sm text-graphite/50 text-center">
          暂无待考考试
        </div>
      </template>
    </section>

    <!-- 最近问答 -->
    <section class="space-y-2">
      <div class="flex items-center justify-between">
        <p class="section-title"><el-icon><ChatLineSquare /></el-icon>最近问答</p>
        <router-link to="/worker/chat" class="text-xs text-safety font-medium">去提问 →</router-link>
      </div>
      <div class="card divide-y divide-gray-50">
        <router-link
          v-for="r in recentQa"
          :key="r.q"
          to="/worker/chat"
          class="flex items-center gap-3 p-3.5 hover:bg-mist/60 transition-colors first:rounded-t-card last:rounded-b-card"
        >
          <el-icon class="text-teal-500 shrink-0"><ChatDotRound /></el-icon>
          <span class="text-sm text-graphite flex-1 truncate">{{ r.q }}</span>
          <span class="text-[10px] text-graphite/40 shrink-0">{{ r.t }}</span>
        </router-link>
      </div>
    </section>
  </div>
</template>
