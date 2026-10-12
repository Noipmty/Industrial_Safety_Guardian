<script setup lang="ts">
import { nextTick, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { User, Monitor } from '@element-plus/icons-vue';
import { useAuthStore } from '@/stores/auth';
import { useStreamChat, type StreamMessage } from '@/composables/useStreamChat';

/**
 * 管理端 AI 问答 —— 与前台问答的差异：
 * 1. scope=admin：全库检索，不按文档类型过滤（后端校验 admin 角色）；
 * 2. 独立的检索详情面板：每条引用展示文档类型 / 权限等级 / 相似度，
 *    便于管理员验证知识库召回质量。
 */
const props = defineProps<{ adminUserId: number }>();

const authStore = useAuthStore();
const { messages, isStreaming, send, stop } = useStreamChat();

const inputText = ref('');
const detailVisible = ref(false);
const detailSource = ref<StreamMessage['sources'] | null>(null);
const scrollContainer = ref<HTMLElement | null>(null);

const DEFAULT_USER_ID = 1;

async function handleSend(): Promise<void> {
  const text = inputText.value.trim();
  if (!text || isStreaming.value) return;
  inputText.value = '';
  try {
    await send(text, props.adminUserId || DEFAULT_USER_ID, undefined, 'admin');
  } catch {
    ElMessage.error('请求失败，请稍后重试');
  }
  await nextTick();
  if (scrollContainer.value) {
    scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight;
  }
}

function showDetail(msg: StreamMessage): void {
  detailSource.value = msg.sources ?? null;
  detailVisible.value = true;
}

function handleEnter(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    handleSend();
  }
}

function accessLabel(level: string | null | undefined): string {
  if (level === 'internal') return '内部';
  if (level === 'public') return '公开';
  return '未知';
}
</script>

<template>
  <div class="qa-panel">
    <div ref="scrollContainer" class="qa-messages">
      <div
        v-for="(msg, index) in messages"
        :key="index"
        :class="['qa-msg', `qa-msg--${msg.role}`]"
      >
        <div class="qa-msg__avatar">
          <el-icon v-if="msg.role === 'user'" :size="18"><User /></el-icon>
          <el-icon v-else :size="18"><Monitor /></el-icon>
        </div>
        <div class="qa-msg__body">
          <div class="qa-msg__content">
            {{ msg.content }}
            <span v-if="msg.streaming" class="qa-cursor">▊</span>
          </div>
          <el-button
            v-if="msg.sources && msg.sources.length > 0"
            size="small"
            text
            type="primary"
            @click="showDetail(msg)"
          >
            检索详情 ({{ msg.sources.length }})
          </el-button>
        </div>
      </div>
      <div v-if="messages.length === 0" class="qa-empty">
        <p>管理端问答：全库知识检索（含内部资料），回答附带召回详情。</p>
      </div>
    </div>

    <div class="qa-input">
      <el-input
        v-model="inputText"
        type="textarea"
        :rows="2"
        placeholder="向知识库提问... (Enter 发送)"
        resize="none"
        :disabled="isStreaming"
        @keyup.enter="handleEnter"
      />
      <el-button
        v-if="!isStreaming"
        type="primary"
        :disabled="inputText.trim().length === 0"
        @click="handleSend"
      >
        发送
      </el-button>
      <el-button v-else type="danger" @click="stop">停止</el-button>
    </div>

    <el-drawer v-model="detailVisible" title="检索命中详情" size="40%">
      <div
        v-for="(s, i) in detailSource ?? []"
        :key="i"
        class="qa-detail__item"
      >
        <div class="qa-detail__head">
          <el-tag size="small" type="info">{{ s.doc_type }}</el-tag>
          <el-tag size="small" :type="s.access_level === 'internal' ? 'warning' : 'success'">
            {{ accessLabel(s.access_level) }}
          </el-tag>
          <span class="qa-detail__score">相似度 {{ (s.score * 100).toFixed(1) }}%</span>
          <span v-if="s.position" class="qa-detail__pos">{{ s.position }}</span>
        </div>
        <p class="qa-detail__text">{{ s.text }}</p>
      </div>
      <el-empty
        v-if="(detailSource ?? []).length === 0"
        description="该回答无引用来源"
      />
    </el-drawer>
  </div>
</template>

<style scoped>
.qa-panel {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 160px);
  min-height: 420px;
  overflow: hidden;
}

.qa-messages {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}

.qa-msg {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
}

.qa-msg--user {
  flex-direction: row-reverse;
}

.qa-msg__avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #e6f0fa;
  color: #1a2a3a;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.qa-msg--user .qa-msg__avatar {
  background: #1a2a3a;
  color: #fff;
}

.qa-msg__body {
  max-width: 68%;
  min-width: 0;
}

.qa-msg__content {
  padding: 10px 14px;
  border-radius: 8px;
  background: #f5f7fa;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-all;
}

.qa-msg--user .qa-msg__content {
  background: #1a2a3a;
  color: #fff;
}

.qa-cursor {
  color: #409eff;
  animation: blink 1s steps(2) infinite;
}

@keyframes blink {
  0% { opacity: 1; }
  50% { opacity: 0; }
}

.qa-empty {
  text-align: center;
  color: #909399;
  font-size: 13px;
  padding-top: 60px;
}

.qa-input {
  display: flex;
  gap: 10px;
  margin-top: 12px;
  align-items: flex-end;
  flex-shrink: 0;
}

.qa-detail__item {
  margin-bottom: 16px;
  padding: 12px 14px;
  background: #f9fafc;
  border-radius: 6px;
  border: 1px solid #ebeef5;
}

.qa-detail__head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
  color: #909399;
  flex-wrap: wrap;
}

.qa-detail__pos {
  word-break: break-all;
}

.qa-detail__text {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #444;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-all;
}
</style>
