<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useAdminStore } from '@/stores/admin'
import AppSkeleton from '@/components/common/AppSkeleton.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const admin = useAdminStore()
const loading = ref(true)
const resultFilter = ref<'all' | 'success' | 'denied' | 'failed'>('all')
const keyword = ref('')

const RESULT_TAG: Record<string, { label: string; type: 'success' | 'warning' | 'danger' }> = {
  success: { label: '成功', type: 'success' },
  denied: { label: '拒绝', type: 'warning' },
  failed: { label: '失败', type: 'danger' },
}
const stats = computed(() => [
  { label: '记录总数', value: String(admin.audits.length), warn: false, cls: 'text-navy' },
  { label: '成功', value: String(admin.audits.filter((a) => a.result === 'success').length), warn: false, cls: 'text-teal-600' },
  { label: '越权拒绝', value: String(admin.audits.filter((a) => a.result === 'denied').length), warn: true, cls: 'text-safety' },
  { label: '失败', value: String(admin.audits.filter((a) => a.result === 'failed').length), warn: true, cls: 'text-red-500' },
])

const list = computed(() =>
  admin.audits.filter(
    (a) =>
      (resultFilter.value === 'all' || a.result === resultFilter.value) &&
      (!keyword.value || a.actor.includes(keyword.value) || a.target.includes(keyword.value) || a.action.includes(keyword.value)),
  ),
)

onMounted(async () => {
  try {
    await admin.loadAudits()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center gap-2">
      <el-input v-model="keyword" placeholder="搜索操作人 / 对象" clearable prefix-icon="Search" class="w-56!" />
      <el-radio-group v-model="resultFilter">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="success">成功</el-radio-button>
        <el-radio-button value="denied">拒绝</el-radio-button>
        <el-radio-button value="failed">失败</el-radio-button>
      </el-radio-group>
      <span class="flex-1 hidden sm:block" />
      <span class="text-xs text-graphite/45">全部操作写入 MySQL 审计表 · 越权尝试实时告警</span>
    </div>

    <!-- 统计面板 -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div v-for="s in stats" :key="s.label" class="card p-3.5">
        <p class="text-xs text-graphite/50">{{ s.label }}</p>
        <p class="text-xl font-bold tabular-nums mt-0.5" :class="s.cls">{{ s.value }}</p>
      </div>
    </div>

    <AppSkeleton v-if="loading" type="table" :rows="7" />
    <div v-else-if="!list.length" class="card">
      <EmptyState description="没有符合条件的审计记录" />
    </div>
    <div v-else class="card p-2">
      <el-table :data="list" stripe>
        <el-table-column prop="time" label="时间" width="150">
          <template #default="{ row }"><span class="font-mono text-xs">{{ row.time }}</span></template>
        </el-table-column>
        <el-table-column prop="actor" label="操作人" width="100">
          <template #default="{ row }"><span class="font-mono text-xs">{{ row.actor }}</span></template>
        </el-table-column>
        <el-table-column prop="action" label="操作" width="120" />
        <el-table-column prop="target" label="对象" min-width="200" show-overflow-tooltip />
        <el-table-column label="结果" width="90">
          <template #default="{ row }">
            <el-tag :type="RESULT_TAG[row.result as keyof typeof RESULT_TAG]?.type" size="small" round>
              {{ RESULT_TAG[row.result as keyof typeof RESULT_TAG]?.label ?? row.result }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="来源 IP" width="110">
          <template #default="{ row }"><span class="font-mono text-xs text-graphite/50">{{ row.ip }}</span></template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>
