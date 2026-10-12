<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useExamStore } from '@/stores/exam'
import AppSkeleton from '@/components/common/AppSkeleton.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import type { Question } from '@/types'

const route = useRoute()
const router = useRouter()
const exam = useExamStore()
const examId = computed(() => String(route.params.id ?? ''))

const loading = ref(true)
const remaining = ref(0)
const savedAt = ref('')
let timer: ReturnType<typeof setInterval> | null = null

const TYPE_LABEL: Record<Question['type'], string> = {
  single: '单选题',
  multiple: '多选题',
  judge: '判断题',
  short_answer: '主观题',
}
const DIFF = ['', '★', '★★', '★★★', '★★★★', '★★★★★']

const examInfo = computed(() => exam.exams.find((e) => e.id === examId.value))
const answers = computed(() => exam.answers[examId.value] ?? {})
const answeredCount = computed(
  () => exam.paper.filter((q) => (answers.value[q.id] ?? '') !== '').length,
)
const timeText = computed(() => {
  const m = Math.floor(remaining.value / 60)
  const s = remaining.value % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})
const timeDanger = computed(() => remaining.value <= 60)

function answerOf(qid: string): string {
  return answers.value[qid] ?? ''
}

function setAnswer(qid: string, value: string): void {
  exam.setAnswer(examId.value, qid, value)
  savedAt.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
}

function toggleMulti(q: Question, idx: number): void {
  const cur = answerOf(q.id)
  const letter = String.fromCharCode(65 + idx)
  const set = new Set(cur.split(',').filter(Boolean))
  if (set.has(letter)) set.delete(letter)
  else set.add(letter)
  setAnswer(q.id, [...set].sort().join(','))
}

function isChecked(q: Question, idx: number): boolean {
  return answerOf(q.id).split(',').includes(String.fromCharCode(65 + idx))
}

async function onSubmit(): Promise<void> {
  const unanswered = exam.paper.length - answeredCount.value
  try {
    await ElMessageBox.confirm(
      unanswered > 0
        ? `还有 ${unanswered} 题未作答，未答题按 0 分计。确定提交吗？`
        : '全部题目已作答，确定提交吗？',
      '提交确认',
      {
        confirmButtonText: '确认提交',
        cancelButtonText: '继续答题',
        type: 'warning',
        dangerouslyUseHTMLString: false,
      },
    )
  } catch {
    return
  }
  exam.submitting = true
  try {
    await exam.submit(examId.value)
    ElMessage.success('批改完成：客观题精确匹配 · 主观题 RAG 增强评分')
    void router.replace(`/worker/exams/${examId.value}/result`)
  } finally {
    exam.submitting = false
  }
}

onMounted(async () => {
  try {
    await exam.loadExams()
    const info = exam.exams.find((e) => e.id === examId.value)
    if (info?.status === 'finished') {
      ElMessage.info('该考试已完成，为您跳转成绩详情')
      void router.replace(`/worker/exams/${examId.value}/result`)
      return
    }
    await exam.loadPaper(examId.value)
    if (!exam.paper.length) {
      ElMessage.warning('试卷不存在或已被撤回')
      void router.replace('/worker/exams')
      return
    }
    remaining.value = (info?.durationMin ?? 15) * 60
    timer = setInterval(() => {
      remaining.value -= 1
      if (remaining.value <= 0) {
        if (timer) clearInterval(timer)
        ElMessage.warning('时间到，已自动提交')
        void onSubmit()
      }
    }, 1000)
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div class="space-y-4">
    <!-- 顶部：标题 + 倒计时 -->
    <div class="card p-4 flex items-center gap-3 sticky top-[60px] z-20">
      <button class="text-graphite/50 hover:text-navy shrink-0" @click="router.back()">
        <el-icon :size="20"><ArrowLeft /></el-icon>
      </button>
      <div class="flex-1 min-w-0">
        <p class="font-bold text-navy truncate">{{ examInfo?.title ?? '答题中' }}</p>
        <p class="text-[11px] text-graphite/50" v-if="savedAt">
          <el-icon class="align-[-1px]"><CircleCheck /></el-icon> 已自动保存 {{ savedAt }}
        </p>
        <p class="text-[11px] text-graphite/40" v-else>作答自动保存至本地，断网可恢复</p>
      </div>
      <div
        class="px-3 py-1.5 rounded-xl font-mono font-bold text-lg tabular-nums shrink-0"
        :class="timeDanger ? 'bg-red-50 text-red-500 animate-pulse' : 'bg-mist text-navy'"
      >
        {{ timeText }}
      </div>
    </div>

    <AppSkeleton v-if="loading" type="list" :rows="4" />
    <EmptyState v-else-if="!exam.paper.length" description="试卷加载失败" />

    <template v-else>
      <!-- 题号导航 -->
      <div class="card p-3.5">
        <div class="flex items-center justify-between mb-2">
          <p class="text-xs font-semibold text-graphite/60">答题卡</p>
          <p class="text-xs text-graphite/45">{{ answeredCount }}/{{ exam.paper.length }} 已答</p>
        </div>
        <div class="flex flex-wrap gap-1.5">
          <a
            v-for="(q, i) in exam.paper"
            :key="q.id"
            :href="`#q-${q.id}`"
            class="w-8 h-8 rounded-lg text-xs font-bold flex items-center justify-center border transition-colors"
            :class="answerOf(q.id)
              ? 'bg-safety border-safety text-white'
              : 'bg-white border-gray-200 text-graphite/50'"
          >{{ i + 1 }}</a>
        </div>
      </div>

      <!-- 题目列表 -->
      <div
        v-for="(q, i) in exam.paper"
        :id="`q-${q.id}`"
        :key="q.id"
        class="card p-4 sm:p-5 space-y-4 scroll-mt-32"
      >
        <div class="flex items-start gap-2.5">
          <span class="w-6 h-6 rounded-lg bg-navy text-white text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
            {{ i + 1 }}
          </span>
          <div class="flex-1 min-w-0">
            <p class="text-[15px] font-medium text-graphite leading-relaxed">{{ q.stem }}</p>
            <div class="flex flex-wrap gap-1.5 mt-2">
              <span class="chip bg-mist text-graphite/60 border border-gray-200">{{ TYPE_LABEL[q.type] }}</span>
              <span class="chip bg-mist text-safety border border-gray-200">{{ DIFF[q.difficulty] }}</span>
              <span class="chip bg-mist text-graphite/60 border border-gray-200">{{ q.score }} 分</span>
              <span v-for="t in q.knowledgeTags" :key="t" class="chip bg-[#EAF1F8] text-navy border border-[#C9D9EA]">{{ t }}</span>
            </div>
          </div>
        </div>

        <!-- 单选 -->
        <div v-if="q.type === 'single'" class="space-y-2">
          <label
            v-for="(opt, oi) in q.options"
            :key="oi"
            class="flex items-center gap-3 rounded-xl border-2 px-4 py-3 cursor-pointer transition-colors text-[15px]"
            :class="answerOf(q.id) === String.fromCharCode(65 + oi)
              ? 'border-safety bg-safety-light/50 text-navy font-semibold'
              : 'border-gray-100 hover:border-gray-200'"
            @click="setAnswer(q.id, String.fromCharCode(65 + oi))"
          >
            <span
              class="w-7 h-7 rounded-full border-2 flex items-center justify-center text-xs font-bold shrink-0"
              :class="answerOf(q.id) === String.fromCharCode(65 + oi)
                ? 'bg-safety border-safety text-white'
                : 'border-gray-200 text-graphite/50'"
            >{{ String.fromCharCode(65 + oi) }}</span>
            {{ opt }}
          </label>
        </div>

        <!-- 多选 -->
        <div v-else-if="q.type === 'multiple'" class="space-y-2">
          <label
            v-for="(opt, oi) in q.options"
            :key="oi"
            class="flex items-center gap-3 rounded-xl border-2 px-4 py-3 cursor-pointer transition-colors text-[15px]"
            :class="isChecked(q, oi)
              ? 'border-safety bg-safety-light/50 text-navy font-semibold'
              : 'border-gray-100 hover:border-gray-200'"
            @click="toggleMulti(q, oi)"
          >
            <span
              class="w-7 h-7 rounded-lg border-2 flex items-center justify-center text-xs font-bold shrink-0"
              :class="isChecked(q, oi)
                ? 'bg-safety border-safety text-white'
                : 'border-gray-200 text-graphite/50'"
            >{{ isChecked(q, oi) ? '✓' : String.fromCharCode(65 + oi) }}</span>
            {{ opt }}
          </label>
        </div>

        <!-- 判断 -->
        <div v-else-if="q.type === 'judge'" class="grid grid-cols-2 gap-2">
          <button
            class="h-12 rounded-xl border-2 text-base font-semibold transition-colors"
            :class="answerOf(q.id) === '对'
              ? 'border-teal-400 bg-teal-50 text-teal-700'
              : 'border-gray-100 text-graphite/60'"
            @click="setAnswer(q.id, '对')"
          >✓ 正确</button>
          <button
            class="h-12 rounded-xl border-2 text-base font-semibold transition-colors"
            :class="answerOf(q.id) === '错'
              ? 'border-red-400 bg-red-50 text-red-500'
              : 'border-gray-100 text-graphite/60'"
            @click="setAnswer(q.id, '错')"
          >✗ 错误</button>
        </div>

        <!-- 主观题 -->
        <el-input
          v-else
          :model-value="answerOf(q.id)"
          type="textarea"
          :rows="4"
          maxlength="500"
          show-word-limit
          placeholder="请结合规程要点作答，将按「准确性 / 完整性 / 条理性 / 规范性」四个维度评分"
          @update:model-value="(v: string) => setAnswer(q.id, v)"
        />
      </div>

      <!-- 提交 -->
      <div class="card p-4 space-y-2">
        <el-button
          type="primary"
          size="large"
          round
          class="w-full!"
          :loading="exam.submitting"
          @click="onSubmit"
        >
          {{ exam.submitting ? '正在批改…' : '交卷' }}
        </el-button>
        <p class="text-[10px] text-graphite/40 text-center leading-relaxed">
          提交受幂等锁保护：Redis SETNX + DB 唯一约束，重复点击不会产生多份成绩
        </p>
      </div>
    </template>
  </div>
</template>
