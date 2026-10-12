<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useAdminStore } from '@/stores/admin'
import VChart from '@/components/charts/VChart.vue'
import AppSkeleton from '@/components/common/AppSkeleton.vue'
import ErrorRetry from '@/components/common/ErrorRetry.vue'
import CacheBadge from '@/components/common/CacheBadge.vue'
import RouteBadge from '@/components/common/RouteBadge.vue'
import { QUERY_TYPE_LABEL } from '@/types'
import type { EChartsOption } from 'echarts'
import { CACHE_PIE, TOOL_BAR } from '@/mock/data/admin'

const admin = useAdminStore()
const failed = ref(false)

async function load(): Promise<void> {
  failed.value = false
  try {
    await admin.loadDashboard()
  } catch {
    failed.value = true
  }
}
onMounted(load)

interface KpiCard {
  label: string
  value: string
  sub: string
  icon: string
  warn?: boolean
}
const kpiCards = computed<KpiCard[]>(() => {
  const k = admin.kpis
  if (!k) return []
  return [
    { label: 'QPS', value: k.qps.toFixed(1), sub: '峰值 21.3 · 近 1h', icon: 'DataLine' },
    { label: 'P95 延迟', value: `${k.p95Ms}ms`, sub: '阈值 3000ms', icon: 'Timer', warn: k.p95Ms > 2500 },
    { label: '5xx 错误', value: String(k.err5xx), sub: '近 24h · 阈值 10', icon: 'WarningFilled', warn: k.err5xx > 5 },
    { label: '缓存命中率', value: `${Math.round(k.cacheHitRate * 100)}%`, sub: '四级缓存整体', icon: 'Lightning' },
    { label: 'FAQ 命中率', value: `${Math.round(k.faqHitRate * 100)}%`, sub: '高频问题库', icon: 'ChatDotSquare' },
    { label: 'LLM 降级次数', value: String(k.llmFallbacks), sub: '近 24h · 告警阈值 5', icon: 'Connection', warn: k.llmFallbacks >= 5 },
    { label: 'Top-5 引用命中', value: `${Math.round(k.top5HitRate * 100)}%`, sub: '人工评测抽样', icon: 'Aim' },
    { label: '图谱构建耗时', value: `${k.graphBuildSec}s`, sub: '327 chunks 全量', icon: 'Share' },
  ]
})

const trendOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['QPS', 'P95 延迟(ms)'], top: 0, textStyle: { color: '#1F2937' } },
  grid: { left: 8, right: 8, top: 32, bottom: 0, containLabel: true },
  xAxis: {
    type: 'category',
    data: admin.trend.map((t) => t.time),
    axisLabel: { color: '#6B7280', fontSize: 10, interval: 3 },
    axisLine: { lineStyle: { color: '#E0E6EE' } },
  },
  yAxis: [
    { type: 'value', name: 'QPS', splitLine: { lineStyle: { color: '#EEF2F7' } }, axisLabel: { color: '#6B7280', fontSize: 10 } },
    { type: 'value', name: 'ms', splitLine: { show: false }, axisLabel: { color: '#6B7280', fontSize: 10 } },
  ],
  series: [
    {
      name: 'QPS',
      type: 'line',
      smooth: true,
      symbol: 'none',
      data: admin.trend.map((t) => t.qps),
      lineStyle: { color: '#14B8A6', width: 2 },
      areaStyle: { color: 'rgba(20,184,166,0.10)' },
    },
    {
      name: 'P95 延迟(ms)',
      type: 'line',
      smooth: true,
      symbol: 'none',
      yAxisIndex: 1,
      data: admin.trend.map((t) => t.p95Ms),
      lineStyle: { color: '#FF7A1A', width: 2 },
    },
  ],
}))

const cacheOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, textStyle: { color: '#1F2937', fontSize: 11 } },
  color: ['#DC2626', '#14B8A6', '#FF7A1A', '#64748B'],
  series: [
    {
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['50%', '44%'],
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      data: CACHE_PIE,
    },
  ],
}))

const toolOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: 8, right: 16, top: 8, bottom: 0, containLabel: true },
  xAxis: { type: 'value', splitLine: { lineStyle: { color: '#EEF2F7' } }, axisLabel: { color: '#6B7280', fontSize: 10 } },
  yAxis: {
    type: 'category',
    data: TOOL_BAR.map((t) => t.name),
    axisLabel: { color: '#1F2937', fontSize: 11, fontFamily: 'monospace' },
    axisLine: { show: false },
    axisTick: { show: false },
  },
  series: [
    {
      type: 'bar',
      barWidth: 14,
      itemStyle: { borderRadius: [0, 7, 7, 0], color: '#0B1F33' },
      data: TOOL_BAR.map((t) => t.value),
    },
  ],
}))

</script>

<template>
  <div class="space-y-5">
    <ErrorRetry v-if="failed" @retry="load" />
    <AppSkeleton v-else-if="admin.loading && !admin.kpis" type="chart" />

    <template v-else>
      <!-- KPI 卡片 -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div
          v-for="k in kpiCards"
          :key="k.label"
          class="card p-4 flex items-start gap-3"
        >
          <span
            class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
            :class="k.warn ? 'bg-red-50 text-red-500' : 'bg-[#EAF1F8] text-navy'"
          >
            <el-icon :size="19"><component :is="k.icon" /></el-icon>
          </span>
          <div class="min-w-0">
            <p class="text-xs text-graphite/50 truncate">{{ k.label }}</p>
            <p class="text-xl font-bold tabular-nums" :class="k.warn ? 'text-red-500' : 'text-navy'">{{ k.value }}</p>
            <p class="text-[10px] text-graphite/40 truncate">{{ k.sub }}</p>
          </div>
        </div>
      </div>

      <!-- 图表行 -->
      <div class="grid lg:grid-cols-3 gap-4">
        <div class="card p-4 lg:col-span-2">
          <p class="section-title mb-3"><el-icon><TrendCharts /></el-icon>24h 流量与延迟</p>
          <VChart :option="trendOption" height="280px" />
        </div>
        <div class="card p-4">
          <p class="section-title mb-3"><el-icon><PieChart /></el-icon>缓存命中分布</p>
          <VChart :option="cacheOption" height="280px" />
        </div>
      </div>

      <div class="grid lg:grid-cols-3 gap-4">
        <div class="card p-4">
          <p class="section-title mb-3"><el-icon><SetUp /></el-icon>工具调用次数</p>
          <VChart :option="toolOption" height="240px" />
        </div>
        <div class="card p-4 lg:col-span-2">
          <p class="section-title mb-3"><el-icon><ChatLineSquare /></el-icon>最近问答</p>
          <el-table :data="admin.recentQa" size="small" stripe>
            <el-table-column prop="user" label="用户" width="90" />
            <el-table-column prop="question" label="问题" min-width="180" show-overflow-tooltip />
            <el-table-column label="意图" width="90">
              <template #default="{ row }">{{ QUERY_TYPE_LABEL[row.queryType as keyof typeof QUERY_TYPE_LABEL] }}</template>
            </el-table-column>
            <el-table-column label="缓存" width="150">
              <template #default="{ row }">
                <CacheBadge :kind="row.cacheKind" />
              </template>
            </el-table-column>
            <el-table-column label="路由" width="130">
              <template #default="{ row }"><RouteBadge :route="row.route" /></template>
            </el-table-column>
            <el-table-column label="延迟" width="90" align="right">
              <template #default="{ row }">
                <span class="font-mono text-xs">{{ row.latencyMs }}ms</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </template>
  </div>
</template>
