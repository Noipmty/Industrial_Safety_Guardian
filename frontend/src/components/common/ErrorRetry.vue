<script setup lang="ts">
withDefaults(defineProps<{ description?: string }>(), {
  description: '加载失败，请检查网络后重试',
})
const emit = defineEmits<{ retry: [] }>()
</script>

<template>
  <div class="py-10 flex flex-col items-center gap-3">
    <svg viewBox="0 0 48 48" class="w-12 h-12" aria-hidden="true">
      <circle cx="24" cy="24" r="20" fill="#FFF1E6" />
      <path d="M24 14v12" stroke="#FF7A1A" stroke-width="4" stroke-linecap="round" />
      <circle cx="24" cy="33" r="2.4" fill="#FF7A1A" />
    </svg>
    <p class="text-sm text-graphite/70">{{ description }}</p>
    <el-button size="small" round @click="emit('retry')">
      <el-icon class="mr-1"><RefreshRight /></el-icon>重新加载
    </el-button>
  </div>
</template>
