<script setup lang="ts">
withDefaults(defineProps<{ description?: string }>(), {
  description: '暂无数据',
})
</script>

<template>
  <div class="py-12 flex flex-col items-center gap-3 text-center">
    <svg viewBox="0 0 120 90" class="w-28 h-21 opacity-70" aria-hidden="true">
      <rect x="22" y="18" width="76" height="54" rx="8" fill="#E8EDF3" />
      <rect x="34" y="32" width="34" height="5" rx="2.5" fill="#C6D0DC" />
      <rect x="34" y="44" width="52" height="5" rx="2.5" fill="#D5DDE7" />
      <rect x="34" y="56" width="24" height="5" rx="2.5" fill="#D5DDE7" />
      <circle cx="88" cy="30" r="9" fill="#fff" stroke="#C6D0DC" stroke-width="2" />
      <path d="M84.5 30l2.5 2.5 4.5-5" stroke="#14B8A6" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
    <p class="text-sm text-graphite/60">{{ description }}</p>
    <div v-if="$slots.default">
      <slot />
    </div>
  </div>
</template>
