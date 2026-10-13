<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchReviewQueue, submitReview } from '@/api/admin'
import AppSkeleton from '@/components/common/AppSkeleton.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import type { ReviewItem } from '@/types'

const loading = ref(true)
const items = ref<ReviewItem[]>([])

const pendingItems = computed(() => items.value.filter((i) => i.reviewStatus === 'pending'))
const doneItems = computed(() => items.value.filter((i) => i.reviewStatus !== 'pending'))
const avgSimPct = computed(() => {
  const sims = items.value.map((i) => i.similarity)
  return sims.length ? (sims.reduce((a, b) => a + b, 0) / sims.length) * 100 : 0
})

const STATUS_TAG: Record<
  ReviewItem['reviewStatus'],
  { label: string; type: 'warning' | 'success' | 'info' }
> = {
  pending: { label: '待人工复核', type: 'warning' },
  approved: { label: '教师已复核', type: 'success' },
  auto: { label: 'AI 自动评分', type: 'info' },
}

function simColor(sim: number): string {
  return sim >= 0.35 ? '#14B8A6' : '#FF7A1A'
}

async function load(): Promise<void> {
  loading.value = true
  try {
    items.value = await fetchReviewQueue()
  } finally {
    loading.value = false
  }
}

// ---- 复核操作 ----
const submitting = ref(false)
const showAdjust = ref(false)
const adjustTarget = ref<ReviewItem | null>(null)
const adjustScore = ref(0)

async function confirmAi(item: ReviewItem): Promise<void> {
  submitting.value = true
  try {
    await submitReview({ examId: item.examId, questionId: item.questionId, action: 'confirm' })
    ElMessage.success('已确认 AI 评分，该卷总分同步更新')
    await load()
  } finally {
    submitting.value = false
  }
}

function openAdjust(item: ReviewItem): void {
  adjustTarget.value = item
  adjustScore.value = item.gotScore
  showAdjust.value = true
}

async function doAdjust(): Promise<void> {
  const t = adjustTarget.value
  if (!t) return
  submitting.value = true
  try {
    const from = t.gotScore
    await submitReview({
      examId: t.examId,
      questionId: t.questionId,
      action: 'adjust',
      newScore: adjustScore.value,
    })
    ElMessage.success(`改分完成：${from} → ${adjustScore.value} 分，该卷总分同步更新`)
    showAdjust.value = false
    adjustTarget.value = null
    await load()
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-lg font-bold text-navy">主观题人工复核</h1>
        <p class="text-xs text-graphite/45 mt-0.5">
          RAG 相似度低于 35%（或未作答）的主观题自动进入本队列；AI 预评分仅供参考，裁决后总分按差值更新
        </p>
      </div>
    </div>

    <!-- 统计 -->
    <div class="grid grid-cols-3 gap-3">
      <div class="card p-3.5">
        <p class="text-[11px] text-graphite/45">待人工复核</p>
        <p class="text-2xl font-bold text-safety mt-0.5">{{ pendingItems.length }}</p>
      </div>
      <div class="card p-3.5">
        <p class="text-[11px] text-graphite/45">已完成复核 / 总数</p>
        <p class="text-2xl font-bold text-navy mt-0.5">
          {{ doneItems.length }}<span class="text-sm text-graphite/40"> / {{ items.length }}</span>
        </p>
      </div>
      <div class="card p-3.5">
        <p class="text-[11px] text-graphite/45">平均 RAG 相似度</p>
        <p class="text-2xl font-bold text-teal-600 mt-0.5">{{ avgSimPct.toFixed(1) }}%</p>
      </div>
    </div>

    <AppSkeleton v-if="loading" type="table" :rows="5" />
    <div v-else-if="items.length" class="card p-2 space-y-2">
      <p class="section-title px-2 pt-2"><el-icon><Finished /></el-icon>复核队列</p>
      <el-table :data="items" stripe size="small" max-height="620">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="px-6 py-3 grid md:grid-cols-2 gap-3">
              <div class="rounded-lg bg-mist p-3">
                <p class="text-[11px] text-graphite/45 mb-1">工人作答（{{ row.worker }}）</p>
                <p class="text-xs text-graphite leading-relaxed">{{ row.userAnswer || '（未作答）' }}</p>
              </div>
              <div class="rounded-lg bg-teal-50 p-3">
                <p class="text-[11px] text-teal-600/70 mb-1">规程参考答案</p>
                <p class="text-xs text-teal-800/90 leading-relaxed">{{ row.referenceAnswer }}</p>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="worker" label="工人" width="90" />
        <el-table-column prop="examTitle" label="考试" width="180" show-overflow-tooltip />
        <el-table-column prop="stem" label="题干" min-width="220" show-overflow-tooltip />
        <el-table-column label="RAG 相似度" width="150">
          <template #default="{ row }">
            <div class="flex items-center gap-2">
              <el-progress
                class="flex-1"
                :percentage="Math.round(row.similarity * 100)"
                :stroke-width="6"
                :color="simColor(row.similarity)"
                :show-text="false"
              />
              <span class="text-xs font-bold shrink-0" :style="{ color: simColor(row.similarity) }">
                {{ (row.similarity * 100).toFixed(1) }}%
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="AI 预评分" width="90" align="center">
          <template #default="{ row }">
            <span class="font-bold text-safety">{{ row.gotScore }}</span>
            <span class="text-graphite/40 text-xs"> / {{ row.fullScore }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="STATUS_TAG[row.reviewStatus as keyof typeof STATUS_TAG].type" size="small" round>
              {{ STATUS_TAG[row.reviewStatus as keyof typeof STATUS_TAG].label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <template v-if="row.reviewStatus === 'pending'">
              <el-button size="small" type="primary" round :disabled="submitting" @click="confirmAi(row)">
                确认 AI 评分
              </el-button>
              <el-button size="small" round @click="openAdjust(row)">改分</el-button>
            </template>
            <span v-else class="text-[11px] text-graphite/40">复核完成</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div v-else class="card">
      <EmptyState description="暂无需要复核的主观题" />
    </div>

    <!-- 改分弹窗 -->
    <el-dialog v-model="showAdjust" title="教师改分" width="480px">
      <div v-if="adjustTarget" class="space-y-3">
        <p class="text-sm font-semibold text-navy leading-relaxed">{{ adjustTarget.stem }}</p>
        <div class="rounded-lg bg-mist p-3 text-xs text-graphite leading-relaxed">
          {{ adjustTarget.userAnswer || '（未作答）' }}
        </div>
        <div class="flex items-center gap-3 text-xs">
          <span class="text-graphite/55">RAG 相似度</span>
          <span class="font-bold" :style="{ color: simColor(adjustTarget.similarity) }">
            {{ (adjustTarget.similarity * 100).toFixed(1) }}%
          </span>
          <span class="text-graphite/55">AI 预评</span>
          <span class="font-bold text-safety">{{ adjustTarget.gotScore }} / {{ adjustTarget.fullScore }} 分</span>
        </div>
        <el-input-number v-model="adjustScore" :min="0" :max="adjustTarget.fullScore" class="w-full!" />
      </div>
      <template #footer>
        <el-button round @click="showAdjust = false">取消</el-button>
        <el-button type="primary" round :loading="submitting" @click="doAdjust">确认改分</el-button>
      </template>
    </el-dialog>
  </div>
</template>
