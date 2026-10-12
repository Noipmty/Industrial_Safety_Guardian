<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage } from '@/types'
import { renderLiteMarkdown } from '@/utils/md'
import StepFlow from '@/components/common/StepFlow.vue'
import CacheBadge from '@/components/common/CacheBadge.vue'
import RouteBadge from '@/components/common/RouteBadge.vue'
import SourceCard from '@/components/qa/SourceCard.vue'
import GraphChain from '@/components/qa/GraphChain.vue'

const props = defineProps<{ message: ChatMessage }>()

const html = computed(() => renderLiteMarkdown(props.message.content))

const QUERY_LABEL: Record<string, string> = {
  factual: '事实查询',
  relational: '关系推理',
  visual: '图表理解',
  structural: '体系结构',
}
</script>

<template>
  <!-- 用户消息 -->
  <div v-if="message.role === 'user'" class="flex justify-end">
    <div
      class="max-w-[82%] rounded-2xl rounded-br-md bg-safety text-white px-4 py-2.5 text-[15px] leading-relaxed shadow-card"
    >
      {{ message.content }}
    </div>
  </div>

  <!-- 助手消息 -->
  <div v-else class="flex justify-start">
    <div class="max-w-[94%] sm:max-w-[88%] w-fit space-y-2.5">
      <!-- 检索步骤 -->
      <StepFlow v-if="message.steps && message.steps.length" :steps="message.steps" class="card p-3" />

      <!-- 气泡 -->
      <div
        v-if="message.content || message.streaming"
        class="rounded-2xl rounded-tl-md bg-white shadow-card px-4 py-3 text-[15px] leading-relaxed md-answer"
      >
        <span v-html="html" /><span v-if="message.streaming" class="typing-caret" aria-hidden="true" />
      </div>

      <!-- 403 权限提示 -->
      <el-alert
        v-if="message.answer?.permissionDenied"
        type="warning"
        :closable="false"
        show-icon
        title="权限不足（403）"
        description="您正在访问 internal / secret 级别内容。为保护内部资料，系统不会在回答中暴露任何受限片段，请联系管理员开通权限。"
        class="rounded-xl"
      />

      <!-- 守卫拦截提示 -->
      <el-alert
        v-else-if="message.answer?.guardBlocked"
        type="error"
        :closable="false"
        show-icon
        title="内容安全守卫已拦截"
        description="检测到提示词注入行为（试图诱导输出系统指令），本次请求已被拒绝并记录审计日志。"
        class="rounded-xl"
      />

      <!-- 元信息 + 引用 -->
      <template v-if="message.answer && !message.answer.guardBlocked">
        <div v-if="!message.answer.permissionDenied" class="flex flex-wrap items-center gap-1.5">
          <CacheBadge :kind="message.answer.cacheKind" :score="message.answer.cacheScore" />
          <RouteBadge :route="message.answer.route" />
          <span class="chip bg-white text-graphite/60 border border-gray-200">
            <el-icon :size="12"><Aim /></el-icon>{{ QUERY_LABEL[message.answer.queryType] }}
          </span>
        </div>

        <GraphChain v-if="message.answer.graphEdges.length && !message.answer.permissionDenied" :edges="message.answer.graphEdges" />

        <div v-if="message.answer.sources.length" class="space-y-2">
          <p class="text-[11px] font-semibold text-graphite/45 flex items-center gap-1">
            <el-icon :size="12"><Collection /></el-icon>引用来源（{{ message.answer.sources.length }}）
          </p>
          <SourceCard
            v-for="s in message.answer.sources"
            :key="s.index"
            :source="s"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.typing-caret {
  display: inline-block;
  width: 2px;
  height: 1em;
  margin-left: 2px;
  vertical-align: -2px;
  background: #ff7a1a;
  animation: blink 0.9s steps(1) infinite;
}
@keyframes blink {
  50% {
    opacity: 0;
  }
}
</style>
