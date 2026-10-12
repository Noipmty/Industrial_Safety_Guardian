<script setup lang="ts">
import { computed } from 'vue'
import { CACHE_LABEL } from '@/types'
import type { CacheKind } from '@/types'

const props = defineProps<{ kind: CacheKind; score?: number }>()

const STYLE: Record<CacheKind, string> = {
  redis_exact: 'bg-red-50 text-red-600 border border-red-200',
  semantic: 'bg-teal-50 text-teal-700 border border-teal-200',
  faq: 'bg-safety-light text-safety-dark border border-orange-200',
  full_rag: 'bg-slate-100 text-slate-600 border border-slate-200',
}

const label = computed(() => {
  const base = CACHE_LABEL[props.kind]
  if (props.score !== undefined && props.kind !== 'full_rag') {
    return `${base} ${props.score.toFixed(2)}`
  }
  return base
})
</script>

<template>
  <span class="chip" :class="STYLE[kind]">
    <el-icon :size="12"><Lightning /></el-icon>
    {{ label }}
  </span>
</template>
