<script setup lang="ts">
withDefaults(
  defineProps<{
    /** list：多行卡片骨架；table：表格骨架；chart：图表骨架 */
    type?: 'list' | 'table' | 'chart'
    rows?: number
  }>(),
  { type: 'list', rows: 3 },
)
</script>

<template>
  <div class="space-y-3">
    <template v-if="type === 'list'">
      <div
        v-for="i in rows"
        :key="i"
        class="card p-4 flex items-center gap-4"
      >
        <el-skeleton-item variant="circle" style="width: 40px; height: 40px" />
        <div class="flex-1 space-y-2">
          <el-skeleton-item variant="text" style="width: 45%" />
          <el-skeleton-item variant="text" style="width: 80%" />
        </div>
        <el-skeleton-item variant="button" style="width: 72px" />
      </div>
    </template>
    <template v-else-if="type === 'table'">
      <div class="card p-4">
        <el-skeleton :rows="rows" animated />
      </div>
    </template>
    <template v-else>
      <div class="card p-4">
        <el-skeleton-item variant="rect" style="width: 100%; height: 260px; border-radius: 12px" />
      </div>
    </template>
  </div>
</template>
