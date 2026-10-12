<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useExamStore } from '@/stores/exam'
import VChart from '@/components/charts/VChart.vue'
import AppSkeleton from '@/components/common/AppSkeleton.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import type { EChartsOption } from 'echarts'
import type { Question } from '@/types'

const route = useRoute()
const router = useRouter()
const exam = useExamStore()
const examId = computed(() => String(route.params.id ?? ''))
const loading = ref(true)

const TYPE_LABEL: Record<Question['type'], string> = {
  single: '单选',
  multiple: '多选',
  judge: '判断',
  short_answer: '主观',
}

const result = computed(() => exam.result)

const scoreOption = computed<EChartsOption>(() => ({
  series: [
    {
      type: 'gauge',
      startAngle: 220,
      endAngle: -40,
      radius: '95%',
      center: ['50%', '58%'],
      min: 0,
      max: 100,
      progress: { show: true, width: 14, itemStyle: { color: '#14B8A6' } },
      axisLine: { lineStyle: { width: 14, color: [[1, '#E8EDF3']] } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      pointer: { show: false },
      anchor: { show: false },
      title: { show: false },
      detail: {
        valueAnimation: true,
        offsetCenter: [0, '0%'],
        fontSize: 40,
        fontWeight: 700,
        color: '#0B1F33',
        formatter: '{value}',
      },
      data: [{ value: result.value?.gotScore ?? 0 }],
    },
  ],
}))

const radarOption = computed<EChartsOption>(() => {
  const rubric = result.value?.rubric ?? []
  return {
    radar: {
      indicator: rubric.map((r) => ({ name: r.dimension, max: r.full })),
      radius: '65%',
      splitNumber: 4,
      axisName: { color: '#1F2937', fontSize: 11 },
      splitArea: { areaStyle: { color: ['#F5F7FA', '#fff'] } },
      splitLine: { lineStyle: { color: '#E0E6EE' } },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: rubric.map((r) => r.score),
            name: '得分',
            areaStyle: { color: 'rgba(255,122,26,0.18)' },
            lineStyle: { color: '#FF7A1A', width: 2 },
            itemStyle: { color: '#FF7A1A' },
          },
        ],
      },
    ],
  }
})

function isObjective(q: Question): boolean {
  return q.type !== 'short_answer'
}

onMounted(async () => {
  try {
    await exam.loadResult(examId.value)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-4">
    <!-- 顶栏 -->
    <div class="flex items-center gap-3">
      <button class="text-graphite/50 hover:text-navy" @click="router.push('/worker/exams')">
        <el-icon :size="20"><ArrowLeft /></el-icon>
      </button>
      <h1 class="text-xl font-bold text-navy">成绩详情</h1>
    </div>

    <AppSkeleton v-if="loading" type="list" :rows="4" />
    <template v-else-if="result">
      <el-alert
        v-if="exam.idempotentNotice"
        :title="exam.idempotentNotice"
        type="success"
        show-icon
        :closable="false"
        class="rounded-xl!"
      />

      <!-- 总分卡 -->
      <div class="card p-4 grid grid-cols-2 gap-4 items-center">
        <div class="h-44">
          <VChart :option="scoreOption" height="100%" />
        </div>
        <div class="space-y-3">
          <div>
            <p class="text-sm font-bold text-navy leading-snug">{{ result.exam.title }}</p>
            <p class="text-[11px] text-graphite/45 mt-0.5">
              {{ result.exam.position }} · {{ result.exam.deadline }}
            </p>
          </div>
          <div>
            <div class="flex justify-between text-xs mb-1">
              <span class="text-graphite/55">客观题正确率</span>
              <span class="font-bold text-navy">{{ Math.round(result.objectiveCorrectRate * 100) }}%</span>
            </div>
            <el-progress
              :percentage="Math.round(result.objectiveCorrectRate * 100)"
              :stroke-width="8"
              color="#14B8A6"
              :show-text="false"
            />
          </div>
          <div>
            <p class="text-xs text-graphite/55 mb-1.5">薄弱知识点</p>
            <div class="flex flex-wrap gap-1">
              <span
                v-for="t in result.weakTags"
                :key="t"
                class="chip bg-red-50 text-red-500 border border-red-200"
              >{{ t }}</span>
              <span v-if="!result.weakTags.length" class="text-[11px] text-graphite/40">无</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 主观题 rubric 雷达 -->
      <div class="card p-4">
        <p class="section-title mb-1"><el-icon><DataAnalysis /></el-icon>主观题批改 · rubric 四维评分</p>
        <p class="text-[11px] text-graphite/45 mb-2">由 RAG 增强评分工作流自动评定，依据检索到的规程片段比对参考答案</p>
        <VChart :option="radarOption" height="240px" />
      </div>

      <!-- 错题解析 -->
      <div class="space-y-3">
        <p class="section-title"><el-icon><Reading /></el-icon>逐题解析</p>
        <div
          v-for="(q, i) in result.questions"
          :key="q.id"
          class="card p-4 space-y-3"
        >
          <div class="flex items-start gap-2">
            <span
              class="w-6 h-6 rounded-lg text-xs font-bold flex items-center justify-center shrink-0 mt-0.5"
              :class="isObjective(q)
                ? (q.grading?.gotScore ?? 0) === q.score ? 'bg-teal-500 text-white' : 'bg-red-400 text-white'
                : 'bg-safety text-white'"
            >{{ i + 1 }}</span>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-graphite leading-relaxed">{{ q.stem }}</p>
              <div class="flex flex-wrap gap-1.5 mt-1.5">
                <span class="chip bg-mist text-graphite/55 border border-gray-200">{{ TYPE_LABEL[q.type] }}</span>
                <span class="chip bg-mist text-graphite/55 border border-gray-200">满分 {{ q.score }}</span>
                <span
                  class="chip"
                  :class="isObjective(q)
                    ? (q.grading?.gotScore ?? 0) === q.score
                      ? 'bg-teal-50 text-teal-600 border border-teal-200'
                      : 'bg-red-50 text-red-500 border border-red-200'
                    : 'bg-safety-light text-safety-dark border border-orange-200'"
                >得 {{ q.grading?.gotScore ?? 0 }} 分</span>
              </div>
            </div>
          </div>

          <!-- 客观题对错 -->
          <div v-if="isObjective(q)" class="grid sm:grid-cols-2 gap-2 text-sm">
            <div class="rounded-xl bg-mist p-3">
              <p class="text-[11px] text-graphite/45 mb-1">我的答案</p>
              <p class="font-semibold" :class="(q.grading?.gotScore ?? 0) === q.score ? 'text-teal-600' : 'text-red-500'">
                {{ q.grading?.userAnswer || '—（未作答）' }}
              </p>
            </div>
            <div class="rounded-xl bg-teal-50 p-3">
              <p class="text-[11px] text-teal-600/70 mb-1">正确答案</p>
              <p class="font-semibold text-teal-700">
                <template v-if="q.type === 'judge'">{{ q.answer }}</template>
                <template v-else>{{ q.answer }}<span class="font-normal text-teal-600/80 text-xs">（{{ q.options[q.answer.charCodeAt(0) - 65] }}）</span></template>
              </p>
            </div>
          </div>

          <!-- 主观题 rubric 明细 -->
          <div v-else class="space-y-2">
            <div class="rounded-xl bg-mist p-3">
              <p class="text-[11px] text-graphite/45 mb-1">我的作答</p>
              <p class="text-sm text-graphite leading-relaxed">{{ q.grading?.userAnswer || '（未作答）' }}</p>
            </div>
            <div
              v-if="q.grading?.rubricScores && Object.keys(q.grading.rubricScores).length"
              class="flex flex-wrap gap-2"
            >
              <div
                v-for="(v, k) in q.grading.rubricScores"
                :key="k"
                class="rounded-lg border border-gray-100 px-3 py-1.5 text-center"
              >
                <p class="text-[10px] text-graphite/45">{{ k }}</p>
                <p class="text-sm font-bold text-safety">{{ v }}</p>
              </div>
            </div>
          </div>

          <!-- 评分理由 -->
          <div class="rounded-xl border border-[#C9D9EA] bg-[#EAF1F8]/60 p-3 space-y-1.5">
            <p class="text-[11px] font-semibold text-navy flex items-center gap-1">
              <el-icon><MagicStick /></el-icon>AI 批改意见
            </p>
            <p class="text-xs text-graphite/75 leading-relaxed">{{ q.grading?.reason }}</p>
            <ul v-if="q.grading?.references.length" class="space-y-1 pt-1">
              <li
                v-for="(r, ri) in q.grading.references"
                :key="ri"
                class="text-[11px] text-graphite/55 leading-relaxed pl-3 relative before:absolute before:left-0 before:top-[7px] before:w-1.5 before:h-1.5 before:rounded-full before:bg-teal-400"
              >
                引用依据：{{ r }}
              </li>
            </ul>
          </div>
        </div>
      </div>

      <el-button size="large" round class="w-full!" @click="router.push('/worker/exams')">
        返回考试中心
      </el-button>
    </template>

    <div v-else class="card">
      <EmptyState description="未找到该考试的成绩，可能尚未参加考试">
        <el-button type="primary" round @click="router.push('/worker/exams')">去考试中心</el-button>
      </EmptyState>
    </div>
  </div>
</template>
