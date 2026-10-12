<script setup lang="ts">
import { computed } from 'vue'
import type { AccessLevel } from '@/types'

const props = defineProps<{ access: AccessLevel }>()

const STYLE: Record<AccessLevel, string> = {
  public: 'bg-teal-50 text-teal-700 border border-teal-200',
  internal: 'bg-safety-light text-safety-dark border border-orange-200',
  secret: 'bg-gray-100 text-gray-500 border border-gray-200',
}
const LABEL: Record<AccessLevel, string> = {
  public: 'public 公开',
  internal: 'internal 内部',
  secret: 'secret 机密',
}
const cls = computed(() => STYLE[props.access])
const label = computed(() => LABEL[props.access])
</script>

<template>
  <span class="chip" :class="cls">{{ label }}</span>
</template>
