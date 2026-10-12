<script setup lang="ts">
import type { RetrievalStep } from '@/types'

defineProps<{ steps: RetrievalStep[] }>()
</script>

<template>
  <div class="flex flex-wrap items-stretch gap-x-0 gap-y-1.5">
    <template v-for="(s, i) in steps" :key="s.key">
      <div
        class="flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs border transition-colors"
        :class="{
          'border-teal-300 bg-teal-50 text-teal-700': s.status === 'done' && !s.detail,
          'border-teal-300 bg-teal-50 text-teal-800': s.status === 'done' && !!s.detail,
          'border-orange-300 bg-safety-light text-safety-dark': s.status === 'running',
          'border-gray-200 bg-gray-50 text-gray-400': s.status === 'pending',
          'border-dashed border-gray-200 bg-transparent text-gray-300 line-through': s.status === 'skipped',
          'border-red-200 bg-red-50 text-red-500': s.status === 'failed',
        }"
        :title="s.detail"
      >
        <span
          class="w-3.5 h-3.5 rounded-full flex items-center justify-center text-[9px] font-bold shrink-0"
          :class="{
            'bg-teal-500 text-white': s.status === 'done',
            'bg-safety text-white animate-pulse': s.status === 'running',
            'bg-gray-200 text-gray-400': s.status === 'pending',
            'bg-gray-100 text-gray-300': s.status === 'skipped',
            'bg-red-400 text-white': s.status === 'failed',
          }"
        >{{ s.status === 'done' ? '✓' : i + 1 }}</span>
        <span class="font-medium">{{ s.label }}</span>
        <span v-if="s.detail" class="text-[10px] opacity-80 hidden sm:inline max-w-40 truncate">{{ s.detail }}</span>
      </div>
      <span
        v-if="i < steps.length - 1"
        class="self-center mx-0.5 text-gray-300 text-xs select-none"
        aria-hidden="true"
      >→</span>
    </template>
  </div>
</template>
