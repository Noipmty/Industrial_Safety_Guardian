<script setup lang="ts">
import type { Source } from '@/types'
import PermTag from '@/components/common/PermTag.vue'

defineProps<{ source: Source }>()
</script>

<template>
  <div class="rounded-xl border border-gray-100 bg-mist/60 p-3 space-y-1.5">
    <div class="flex items-center gap-2">
      <span
        class="w-5 h-5 rounded-md bg-safety text-white text-[11px] font-bold flex items-center justify-center shrink-0"
      >{{ source.index }}</span>
      <span class="text-[13px] font-semibold text-navy truncate flex-1">{{ source.docName }}</span>
      <PermTag :access="source.access" />
    </div>
    <p class="text-[11px] text-graphite/50 font-medium">{{ source.chapter }}</p>
    <p class="text-xs text-graphite/75 leading-relaxed">“{{ source.snippet }}”</p>
    <div class="flex items-center gap-2">
      <span class="text-[10px] text-graphite/45">相关度</span>
      <div class="flex-1 h-1 rounded-full bg-gray-200 overflow-hidden max-w-32">
        <div
          class="h-full rounded-full bg-teal-400"
          :style="{ width: `${Math.round(source.score * 100)}%` }"
        />
      </div>
      <span class="text-[10px] font-mono text-teal-600">{{ source.score.toFixed(2) }}</span>
    </div>
  </div>
</template>
