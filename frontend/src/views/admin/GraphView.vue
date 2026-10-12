<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useAdminStore } from '@/stores/admin'
import VChart from '@/components/charts/VChart.vue'
import AppSkeleton from '@/components/common/AppSkeleton.vue'
import type { EChartsOption } from 'echarts'
import type { GraphData, GraphNode } from '@/types'

const admin = useAdminStore()
const loading = ref(true)
const selected = ref<GraphNode | null>(null)
const typeFilter = ref('')
const searchId = ref('')

const presentTypes = computed(() => [
  ...new Set(admin.graph?.nodes.map((n) => n.entityType) ?? []),
])

/** 类型过滤后的子图（保留两端都在子图内的边） */
const filteredGraph = computed<GraphData | null>(() => {
  const g = admin.graph
  if (!g) return null
  if (!typeFilter.value) return g
  const nodes = g.nodes.filter((n) => n.entityType === typeFilter.value)
  const names = new Set(nodes.map((n) => n.name))
  return { ...g, nodes, links: g.links.filter((l) => names.has(l.source) && names.has(l.target)) }
})

watch(searchId, (id) => {
  selected.value = admin.graph?.nodes.find((n) => n.id === id) ?? null
})

/** 实体类型配色 —— 对应后端 GraphRAG 抽取的真实 entity_type 枚举 */
const TYPE_COLOR: Record<string, string> = {
  作业类型: '#2563EB',
  岗位角色: '#DB2777',
  管理职责: '#0B1F33',
  风险因素: '#DC2626',
  安全措施: '#14B8A6',
  法规标准: '#FF7A1A',
  设备设施: '#6D28D9',
  作业环节: '#0891B2',
  防护程序: '#059669',
  化学物质: '#B45309',
}

const typeColor = (t: string): string => TYPE_COLOR[t] ?? '#94A3B8'

const statsCards = computed(() => {
  const s = admin.graphStats
  if (!s) return []
  return [
    { label: '实体总数', value: s.entities.toLocaleString(), icon: 'CircleCheck' },
    { label: '关系总数', value: s.relations.toLocaleString(), icon: 'Connection' },
    { label: '社区数量', value: String(s.communities), icon: 'Grid' },
    {
      label: '概览子图',
      value: `${admin.graph?.nodes.length ?? 0} 节点`,
      icon: 'Timer',
    },
  ]
})

/** 关系类型分布（由子图真实边聚合，替代后端未返回的社区明细） */
const relStats = computed(() => {
  const m = new Map<string, number>()
  for (const l of admin.graph?.links ?? []) m.set(l.relation, (m.get(l.relation) ?? 0) + 1)
  return [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10)
})

const graphOption = computed<EChartsOption>(() => {
  const g = filteredGraph.value
  if (!g) return {}
  return {
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        data: g.nodes.map((n) => ({
          id: n.id,
          name: n.name,
          // 度数最高 195，sqrt 缩放避免巨节点
          symbolSize: 10 + Math.sqrt(n.degree) * 3,
          itemStyle: {
            color: typeColor(n.entityType),
            borderColor: g.anchors.includes(n.name) ? '#FF7A1A' : '#fff',
            borderWidth: g.anchors.includes(n.name) ? 3.5 : 2,
          },
          label: { show: true, fontSize: 11, color: '#1F2937' },
          value: n.degree,
        })),
        links: g.links.map((l) => ({
          source: l.source,
          target: l.target,
          // 线宽随后端抽取置信度变化
          lineStyle: { color: '#C6D0DC', width: 0.7 + (l.confidence ?? 0.7) * 1.5, curveness: 0.12 },
          emphasis: {
            label: {
              show: true,
              formatter: `${l.relation} ${((l.confidence ?? 0.7) * 100).toFixed(0)}%`,
              fontSize: 10,
              color: '#FF7A1A',
            },
          },
        })),
        force: { repulsion: 700, edgeLength: 70, gravity: 0.09 },
        emphasis: { focus: 'adjacency', lineStyle: { width: 3, color: '#FF7A1A' } },
      },
    ],
  }
})

function onNodeClick(p: unknown): void {
  const id = (p as { data?: { id?: string } }).data?.id
  selected.value = admin.graph?.nodes.find((x) => x.id === id) ?? null
}

const rel = computed(() => {
  const g = admin.graph
  if (!g || !selected.value) return []
  return g.links.filter((l) => l.source === selected.value?.name || l.target === selected.value?.name)
})

onMounted(async () => {
  try {
    await admin.loadGraph()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-4">
    <!-- 统计 -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div v-for="s in statsCards" :key="s.label" class="card p-4 flex items-center gap-3">
        <span class="w-10 h-10 rounded-xl bg-[#EAF1F8] text-navy flex items-center justify-center">
          <el-icon :size="19"><component :is="s.icon" /></el-icon>
        </span>
        <div>
          <p class="text-xs text-graphite/50">{{ s.label }}</p>
          <p class="text-xl font-bold text-navy tabular-nums">{{ s.value }}</p>
        </div>
      </div>
    </div>

    <div class="grid lg:grid-cols-3 gap-4 items-start">
      <!-- 图谱 -->
      <div class="lg:col-span-2 card p-4">
        <div class="flex items-center justify-between mb-2 gap-2 flex-wrap">
          <p class="section-title"><el-icon><Share /></el-icon>安全知识图谱（Neo4j · Leiden 社区划分）</p>
          <el-select
            v-model="searchId"
            filterable
            clearable
            placeholder="搜索实体定位"
            size="small"
            class="w-44!"
          >
            <el-option
              v-for="n in admin.graph?.nodes ?? []"
              :key="n.id"
              :label="`${n.name}（${n.entityType}）`"
              :value="n.id"
            />
          </el-select>
        </div>
        <div class="flex flex-wrap items-center gap-1.5 mb-3">
          <button
            class="px-2.5 py-1 rounded-full text-xs border transition-colors"
            :class="!typeFilter ? 'bg-navy text-white border-navy' : 'bg-white text-graphite/60 border-gray-200'"
            @click="typeFilter = ''"
          >全部</button>
          <button
            v-for="t in presentTypes"
            :key="t"
            class="px-2.5 py-1 rounded-full text-xs border flex items-center gap-1.5 transition-colors"
            :class="typeFilter === t ? 'bg-navy text-white border-navy' : 'bg-white text-graphite/60 border-gray-200'"
            @click="typeFilter = typeFilter === t ? '' : t"
          >
            <span class="w-2 h-2 rounded-full" :style="{ background: typeColor(t) }" />
            {{ t }}
          </button>
          <span class="text-[11px] text-graphite/40 ml-auto hidden sm:inline">拖拽 / 缩放浏览 · 点击节点查看关系</span>
        </div>
        <AppSkeleton v-if="loading" type="chart" />
        <VChart
          v-else
          :option="graphOption"
          height="480px"
          @chart-click="onNodeClick"
        />
      </div>

      <!-- 侧栏 -->
      <div class="space-y-4">
        <div class="card p-4 space-y-2 min-h-40">
          <p class="section-title"><el-icon><InfoFilled /></el-icon>节点详情</p>
          <template v-if="selected">
            <div class="flex items-center gap-2">
              <span class="chip text-white border-0" :style="{ background: typeColor(selected.entityType) }">
                {{ selected.entityType }}
              </span>
              <span class="font-bold text-navy text-base">{{ selected.name }}</span>
            </div>
            <p class="text-xs text-graphite/50">连接度 {{ selected.degree }} · 关系 {{ rel.length }} 条</p>
            <ul class="space-y-1.5 pt-1">
              <li v-for="(l, i) in rel" :key="i" class="text-xs text-graphite/70 bg-mist rounded-lg px-2.5 py-1.5">
                <b class="text-safety-dark">{{ l.relation }}</b>
                {{ l.source === selected.name ? '→ ' + l.target : '← ' + l.source }}
                <span v-if="l.confidence" class="text-graphite/40 ml-1">{{ (l.confidence * 100).toFixed(0) }}%</span>
              </li>
            </ul>
          </template>
          <p v-else class="text-xs text-graphite/40 py-4 text-center">点击图谱中的节点查看关联关系</p>
        </div>

        <div class="card p-4 space-y-2">
          <p class="section-title"><el-icon><Collection /></el-icon>关系类型 Top{{ relStats.length }}</p>
          <div
            v-for="[name, count] in relStats"
            :key="name"
            class="flex items-center gap-2 rounded-xl bg-mist px-3 py-2"
          >
            <span class="text-xs text-graphite w-16 shrink-0">{{ name }}</span>
            <div class="flex-1 h-2 rounded-full bg-white overflow-hidden">
              <div
                class="h-full rounded-full bg-safety"
                :style="{ width: `${(count / relStats[0][1]) * 100}%` }"
              />
            </div>
            <span class="chip bg-white text-navy border border-gray-200">{{ count }}</span>
          </div>
          <p class="text-[11px] text-graphite/40 pt-1">实体类型配色与关系标签均来自后端 Neo4j 实际数据</p>
        </div>
      </div>
    </div>
  </div>
</template>
