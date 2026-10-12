<script setup lang="ts">
import { computed } from 'vue'
import type { LlmRoute } from '@/types'

const props = defineProps<{ route: LlmRoute }>()

const STYLE: Record<LlmRoute, string> = {
  'qwen-flash': 'bg-teal-50 text-teal-700 border border-teal-200',
  'qwen-plus': 'bg-[#EAF1F8] text-navy border border-[#C9D9EA]',
  mock: 'bg-gray-100 text-gray-500 border border-dashed border-gray-300',
}
const LABEL: Record<LlmRoute, string> = {
  'qwen-flash': 'route: qwen-flash',
  'qwen-plus': 'route: qwen-plus',
  mock: 'route: mock 兜底',
}
const cls = computed(() => STYLE[props.route])
const label = computed(() => LABEL[props.route])
</script>

<template>
  <span class="chip font-mono" :class="cls">{{ label }}</span>
</template>
