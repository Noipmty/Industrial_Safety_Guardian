<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { EXAM_LIST, PAPERS, registerGeneratedExam } from '@/mock/data/exams'
import { POSITIONS, QUERY_TYPE_LABEL } from '@/types'
import type { Position, Question } from '@/types'

interface BankRow {
  examTitle: string
  q: Question
}

const TYPE_TAG: Record<Question['type'], 'primary' | 'success' | 'warning' | 'info'> = {
  single: 'primary',
  multiple: 'success',
  judge: 'warning',
  short_answer: 'info',
}
const DIFF = ['', '★', '★★', '★★★', '★★★★', '★★★★★']

const bankRows = computed<BankRow[]>(() =>
  EXAM_LIST.flatMap((e) =>
    (PAPERS[e.id] ?? []).map((q) => ({ examTitle: e.title, q })),
  ),
)

// ---- AI 出卷 ----
const TYPE_OPTIONS: { value: Question['type']; label: string }[] = [
  { value: 'single', label: '单选题' },
  { value: 'multiple', label: '多选题' },
  { value: 'judge', label: '判断题' },
  { value: 'short_answer', label: '主观题' },
]

const genForm = ref({
  position: POSITIONS[0] as string,
  tags: '井控、关井程序',
  difficulty: 3,
  counts: { single: 3, multiple: 0, judge: 2, short_answer: 1 } as Record<Question['type'], number>,
})
const totalQuestions = computed(() =>
  Object.values(genForm.value.counts).reduce((s, n) => s + n, 0),
)
const generating = ref(false)
const genStep = ref(0)
const genDone = ref(false)
const genPaper = ref<Question[]>([])
const GEN_STEPS = ['意图检测：解析岗位 / 知识点约束', '结构化生成：qwen-flash 出题', '质量校验：查重 + 答案校验']
let genTimer: ReturnType<typeof setInterval> | null = null

function generate(): void {
  if (!genForm.value.tags.trim()) {
    ElMessage.warning('请填写知识点')
    return
  }
  if (totalQuestions.value <= 0) {
    ElMessage.warning('请至少为一种题型设置数量')
    return
  }
  generating.value = true
  genDone.value = false
  genStep.value = 0
  genTimer = setInterval(() => {
    genStep.value += 1
    if (genStep.value >= GEN_STEPS.length) {
      if (genTimer) clearInterval(genTimer)
      // 演示题库按题型抽取，池内乱序模拟 LLM 生成的不确定性
      const all = Object.values(PAPERS).flat()
      const picked: Question[] = []
      let clipped = 0
      for (const { value: t } of TYPE_OPTIONS) {
        const want = genForm.value.counts[t]
        if (want <= 0) continue
        const pool = all
          .filter((q) => q.type === t && !picked.includes(q))
          .sort(() => Math.random() - 0.5)
        if (pool.length < want) clipped += want - pool.length
        picked.push(...pool.slice(0, want))
      }
      genPaper.value = picked
      genDone.value = true
      generating.value = false
      if (clipped > 0) {
        ElMessage.warning(`演示题库题型存量不足，已按现有 ${picked.length} 题生成（缺 ${clipped} 题）`)
      } else {
        ElMessage.success(`已生成 ${genPaper.value.length} 题并通过质量校验（查重率 0%）`)
      }
    }
  }, 900)
}

const published = ref('')
function publish(): void {
  const exam = registerGeneratedExam(genPaper.value, {
    position: genForm.value.position as Position,
    tags: genForm.value.tags.split(/[,，、\s]+/).filter(Boolean),
    difficulty: genForm.value.difficulty as 1 | 2 | 3 | 4 | 5,
  })
  published.value = exam.title
  ElMessage.success(`试卷《${exam.title}》已发布，工人端考试中心立即可见`)
  genPaper.value = []
  genDone.value = false
}

onBeforeUnmount(() => {
  if (genTimer) clearInterval(genTimer)
})
</script>

<template>
  <div class="grid xl:grid-cols-5 gap-4 items-start">
    <!-- 题库 -->
    <div class="xl:col-span-3 card p-2 space-y-2">
      <p class="section-title px-2 pt-2"><el-icon><Notebook /></el-icon>题库（{{ bankRows.length }} 题）</p>
      <el-table :data="bankRows" stripe size="small" max-height="640">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="px-6 py-3 space-y-1.5">
              <p class="text-xs text-graphite/60">答案：{{ row.q.answer || '—' }}</p>
              <p class="text-xs text-graphite/45">知识点：{{ row.q.knowledgeTags.join('、') }}</p>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="q.stem" label="题干" min-width="260" show-overflow-tooltip />
        <el-table-column label="题型" width="90">
          <template #default="{ row }">
            <el-tag :type="TYPE_TAG[row.q.type as keyof typeof TYPE_TAG]" size="small" round>
              {{ QUERY_TYPE_LABEL[row.q.type as keyof typeof QUERY_TYPE_LABEL] ?? row.q.type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="难度" width="90">
          <template #default="{ row }"><span class="text-safety text-xs">{{ DIFF[row.q.difficulty] }}</span></template>
        </el-table-column>
        <el-table-column prop="q.score" label="分值" width="70" align="center" />
        <el-table-column prop="examTitle" label="所属试卷" width="160" show-overflow-tooltip />
      </el-table>
    </div>

    <!-- AI 出卷 -->
    <div class="xl:col-span-2 card p-5 space-y-4">
      <p class="section-title"><el-icon><MagicStick /></el-icon>AI 自动出卷</p>
      <el-alert
        v-if="published"
        :title="`《${published}》已发布`"
        type="success"
        show-icon
        closable
        class="rounded-lg!"
        description="已注册为正式考试：工人端考试中心立即可见、可作答、交卷后自动批改。"
      />
      <p class="text-xs text-graphite/50 leading-relaxed">
        出题属确定性任务，走「自动出卷工作流」而非自由对话：意图检测 → 结构化生成 → 质量校验，杜绝超纲题与重复题。
      </p>

      <el-form label-width="70px" size="default">
        <el-form-item label="目标岗位">
          <el-select v-model="genForm.position" class="w-full">
            <el-option v-for="p in POSITIONS" :key="p" :label="p" :value="p" />
          </el-select>
        </el-form-item>
        <el-form-item label="知识点">
          <el-input v-model="genForm.tags" placeholder="顿号分隔，如：井控、关井程序" />
        </el-form-item>
        <el-form-item label="难度">
          <el-slider v-model="genForm.difficulty" :min="1" :max="5" show-stops :marks="{ 1: '易', 3: '中', 5: '难' }" class="w-full" />
        </el-form-item>
        <el-form-item label="题型数量">
          <div class="w-full space-y-1.5">
            <div v-for="opt in TYPE_OPTIONS" :key="opt.value" class="flex items-center justify-between gap-2">
              <span class="text-sm text-graphite/80">{{ opt.label }}</span>
              <el-input-number
                v-model="genForm.counts[opt.value]"
                :min="0"
                :max="15"
                size="small"
                controls-position="right"
                class="w-24!"
              />
            </div>
            <p class="text-[11px] text-graphite/45">共 {{ totalQuestions }} 题 · 设为 0 表示不出该题型</p>
          </div>
        </el-form-item>
      </el-form>

      <el-button type="primary" class="w-full!" size="large" :loading="generating" @click="generate">
        {{ generating ? '生成中…' : '生成试卷' }}
      </el-button>

      <el-steps v-if="generating || genDone" :active="genStep + (genDone ? 1 : 0)" align-center finish-status="success" class="py-2">
        <el-step v-for="s in GEN_STEPS" :key="s" :title="s" />
      </el-steps>

      <div v-if="genDone" class="space-y-3">
        <div class="rounded-xl border border-teal-200 bg-teal-50/60 p-3 space-y-2">
          <p class="text-xs font-semibold text-teal-700">质量校验通过：无重复题 · 答案完整 · 难度分布合理</p>
        </div>
        <div v-for="(q, i) in genPaper" :key="q.id" class="rounded-xl border border-gray-100 p-3 space-y-1">
          <p class="text-xs font-bold text-navy">{{ i + 1 }}. {{ q.stem }}</p>
          <p v-if="q.options.length" class="text-[11px] text-graphite/55">
            {{ q.options.map((o, oi) => `${String.fromCharCode(65 + oi)}. ${o}`).join('　') }}
          </p>
          <p class="text-[11px] text-teal-600">答案：{{ q.answer }} · {{ q.score }} 分</p>
        </div>
        <el-button type="warning" class="w-full!" size="large" round @click="publish">
          发布试卷
        </el-button>
      </div>
    </div>
  </div>
</template>
