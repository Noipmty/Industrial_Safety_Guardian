<script setup lang="ts">
</script>

<template>
  <RouterView />
</template>

<style>
@tailwind base;
@tailwind components;
@tailwind utilities;

html {
  /* 固定亮色主题，避免系统暗色模式下未设背景的区域被渲染成黑色 */
  color-scheme: light;
}

html,
body,
#app {
  margin: 0;
  padding: 0;
  height: 100%;
  background: #f5f7fa;
  color: #303133;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    sans-serif;
}
</style>
