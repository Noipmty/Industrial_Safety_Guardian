<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useAdminStore } from '@/stores/admin'
import VChart from '@/components/charts/VChart.vue'
import AppSkeleton from '@/components/common/AppSkeleton.vue'
import type { EChartsOption } from 'echarts'

const admin = useAdminStore()
const loading = ref(true)
const running = ref(false)
const progress = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

const datasets = computed(() => [...new Set(admin.evals.map((e) => e.dataset))])
const activeDataset = ref('')
const current = computed(() => {
  const d = activeDataset.value || datasets.value[0] || ''
  return admin.evals.filter((e) => e.dataset === d)
})

const METRIC_LABEL: Record<string, string> = {
  faithfulness: '忠实度 faithfulness',
  answer_relevancy: '答案相关性 answer_relevancy',
  context_precision: '上下文精确率 context_precision',
  context_recall: '上下文召回率 context_recall',
}

const barOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v: unknown) => `${v}` },
  grid: { left: 8, right: 16, top: 16, bottom: 0, containLabel: true },
  xAxis: {
    type: 'value',
    min: 0,
    max: 1,
    splitLine: { lineStyle: { color: '#EEF2F7' } },
    axisLabel: { color: '#6B7280', fontSize: 10 },
  },
  yAxis: {
    type: 'category',
    data: current.value.map((e) => METRIC_LABEL[e.metric] ?? e.metric),
    axisLabel: { color: '#1F2937', fontSize: 11 },
    axisLine: { show: false },
    axisTick: { show: false },
  },
  series: [
    {
      type: 'bar',
      barWidth: 18,
      itemStyle: { borderRadius: [0, 9, 9, 0], color: '#14B8A6' },
      label: { show: true, position: 'right', formatter: '{c}', color: '#0B1F33', fontWeight: 600 },
      data: current.value.map((e) => e.score),
    },
  ],
}))

function runEval(): void {
  if (running.value) return
  running.value = true
  progress.value = 0
  timer = setInterval(() => {
    progress.value += Math.random() * 18
    if (progress.value >= 100) {
      progress.value = 100
      if (timer) clearInterval(timer)
      running.value = false
      ElMessage.success('评测完成：6 个指标已更新（演示环境复用上次结果）')
    }
  }, 300)
}

onMounted(async () => {
  try {
    await admin.loadEvals()
    activeDataset.value = datasets.value[0] ?? ''
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center gap-3">
      <el-radio-group v-model="activeDataset">
        <el-radio-button v-for="d in datasets" :key="d" :value="d">{{ d }}</el-radio-button>
      </el-radio-group>
      <span class="flex-1" />
      <el-button type="primary" :loading="running" @click="runEval">
        <el-icon v-if="!running" class="mr-1"><VideoPlay /></el-icon>
        {{ running ? '评测中…' : '运行 RAGAS 评测' }}
      </el-button>
    </div>

    <el-progress
      v-if="running"
      :percentage="Math.round(progress)"
      :stroke-width="10"
      color="#14B8A6"
    />

    <div class="grid lg:grid-cols-2 gap-4 items-start">
      <div class="card p-4">
        <p class="section-title mb-3"><el-icon><DataAnalysis /></el-icon>RAGAS 四维指标</p>
        <AppSkeleton v-if="loading" type="chart" />
        <VChart v-else :option="barOption" height="260px" />
        <p class="text-[11px] text-graphite/45 mt-2 leading-relaxed">
          忠实度：答案是否可由引用片段推出；相关性：答案与问题匹配度；上下文精确率 / 召回率：检索质量。
        </p>
      </div>

      <div class="card p-2">
        <el-table :data="current" stripe>
          <el-table-column label="指标" min-width="200">
            <template #default="{ row }">
              <span class="text-xs font-mono text-graphite">{{ row.metric }}</span>
            </template>
          </el-table-column>
          <el-table-column label="得分" width="120">
            <template #default="{ row }">
              <el-progress
                :percentage="Math.round(row.score * 100)"
                :stroke-width="8"
                :color="row.score >= 0.9 ? '#14B8A6' : row.score >= 0.85 ? '#FF7A1A' : '#DC2626'"
              />
            </template>
          </el-table-column>
          <el-table-column label="环比" width="90" align="center">
            <template #default="{ row }">
              <span
                class="text-xs font-semibold"
                :class="row.delta >= 0 ? 'text-teal-600' : 'text-red-500'"
              >
                {{ row.delta >= 0 ? '▲' : '▼' }} {{ Math.abs(row.delta).toFixed(2) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="runAt" label="评测日期" width="110">
            <template #default="{ row }"><span class="font-mono text-xs text-graphite/50">{{ row.runAt }}</span></template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>
