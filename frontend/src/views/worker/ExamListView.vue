<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useExamStore } from '@/stores/exam'
import AppSkeleton from '@/components/common/AppSkeleton.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorRetry from '@/components/common/ErrorRetry.vue'
import type { ExamSummary } from '@/types'

const exam = useExamStore()
const auth = useAuthStore()
const tab = ref<'pending' | 'finished'>('pending')
const failed = ref(false)

const list = computed(() => exam.exams.filter((e) => e.status === tab.value))

async function load(): Promise<void> {
  failed.value = false
  try {
    await exam.loadExams(auth.user?.id ?? 1)
  } catch {
    failed.value = true
  }
}
onMounted(load)

const DIFF = ['', '★', '★★', '★★★', '★★★★', '★★★★★']

function targetOf(e: ExamSummary): string {
  return e.status === 'finished'
    ? `/worker/exams/${e.id}/result`
    : `/worker/exams/${e.id}/take`
}
</script>

<template>
  <div class="space-y-4">
    <h1 class="text-xl font-bold text-navy">考试中心</h1>

    <el-tabs v-model="tab" class="exam-tabs">
      <el-tab-pane label="待考" name="pending" />
      <el-tab-pane label="已完成" name="finished" />
    </el-tabs>

    <ErrorRetry v-if="failed" @retry="load" />
    <AppSkeleton v-else-if="exam.loading" type="list" :rows="3" />
    <EmptyState
      v-else-if="!list.length"
      :description="tab === 'pending' ? '暂无待考考试，请耐心等待安全员发布' : '还没有完成过考试'"
    />

    <div v-else class="space-y-3">
      <router-link
        v-for="e in list"
        :key="e.id"
        :to="targetOf(e)"
        class="card p-4 block space-y-3 hover:shadow-pop transition-shadow"
      >
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <p class="font-bold text-navy">{{ e.title }}</p>
            <div class="flex flex-wrap gap-1 mt-1.5">
              <span class="chip bg-[#EAF1F8] text-navy border border-[#C9D9EA]">{{ e.position }}</span>
              <span v-for="t in e.tags" :key="t" class="chip bg-mist text-graphite/60 border border-gray-200">{{ t }}</span>
            </div>
          </div>
          <span
            class="chip shrink-0"
            :class="e.status === 'pending'
              ? 'bg-safety-light text-safety-dark border border-orange-200'
              : 'bg-teal-50 text-teal-700 border border-teal-200'"
          >
            {{ e.status === 'pending' ? '待考' : `已得 ${e.gotScore} 分` }}
          </span>
        </div>
        <div class="grid grid-cols-4 gap-2 text-center">
          <div>
            <p class="text-xs text-graphite/45">题量</p>
            <p class="text-sm font-bold text-navy">{{ e.questionCount }}</p>
          </div>
          <div>
            <p class="text-xs text-graphite/45">难度</p>
            <p class="text-sm text-safety">{{ DIFF[e.difficulty] }}</p>
          </div>
          <div>
            <p class="text-xs text-graphite/45">时长</p>
            <p class="text-sm font-bold text-navy">{{ e.durationMin }}min</p>
          </div>
          <div>
            <p class="text-xs text-graphite/45">截止</p>
            <p class="text-sm font-bold text-navy">{{ e.deadline.slice(5) }}</p>
          </div>
        </div>
        <el-button
          :type="e.status === 'pending' ? 'primary' : 'default'"
          class="w-full!"
          round
          size="large"
        >
          {{ e.status === 'pending' ? '开始考试' : '查看成绩详情' }}
        </el-button>
      </router-link>
    </div>
  </div>
</template>
