<script setup lang="ts">
import type { GraphEdge } from '@/types'

defineProps<{ edges: GraphEdge[] }>()
</script>

<template>
  <div v-if="edges.length" class="space-y-1.5">
    <p class="text-[11px] font-semibold text-graphite/45 flex items-center gap-1">
      <el-icon :size="12"><Share /></el-icon>知识图谱关系链
    </p>
    <div class="flex flex-wrap items-center gap-1">
      <template v-for="(e, i) in edges" :key="i">
        <span class="chip bg-[#EAF1F8] text-navy border border-[#C9D9EA]">{{ e.subject }}</span>
        <span class="text-[10px] text-safety-dark font-medium px-0.5">—{{ e.relation }}→</span>
        <span class="chip bg-[#EAF1F8] text-navy border border-[#C9D9EA]">{{ e.object }}</span>
      </template>
    </div>
  </div>
</template>
