<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { User, Monitor, Plus, Delete } from '@element-plus/icons-vue';
import { useAuthStore } from '@/stores/auth';
import apiClient from '@/api/client';
import { useChatStore } from '@/stores/chat';
import { useStreamChat, type StreamMessage } from '@/composables/useStreamChat';
import type { ChatSource } from '@/api/types';

const authStore = useAuthStore();
const router = useRouter();
const chatStore = useChatStore();
const {
  messages,
  isStreaming,
  sessionId,
  send,
  adoptSession,
  newSession,
  stop,
} = useStreamChat();

const inputText = ref('');
const scrollContainer = ref<HTMLElement | null>(null);

function getUserId(): number {
  return authStore.user?.id ?? 1;
}

async function refreshSessions(): Promise<void> {
  try {
    await chatStore.fetchSessions(getUserId());
  } catch {
    /* session 加载尽力而为，失败不影响界面 */
  }
}

onMounted(refreshSessions);

async function scrollToBottom(): Promise<void> {
  await nextTick();
  if (scrollContainer.value) {
    scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight;
  }
}

async function handleSend(): Promise<void> {
  const text = inputText.value.trim();
  if (!text || isStreaming.value) return;
  inputText.value = '';
  scrollToBottom();
  try {
    await send(
      text,
      getUserId(),
      (sid) => {
        chatStore.setCurrent(sid);
        void refreshSessions();
      },
    );
  } catch {
    ElMessage.error('请求失败，请稍后重试');
  }
  scrollToBottom();
}

async function openSession(sessionId: string): Promise<void> {
  if (isStreaming.value) return;
  try {
    const history = await chatStore.loadHistory(sessionId);
    const restored: StreamMessage[] = history.map((m) => ({
      role: m.role,
      content: m.content,
      timestamp: new Date().toISOString(),
    }));
    adoptSession(sessionId, restored);
    scrollToBottom();
  } catch {
    ElMessage.warning('会话已过期或不存在');
    await refreshSessions();
  }
}

async function handleNewSession(): Promise<void> {
  if (isStreaming.value) return;
  // 收尾当前会话：整段压缩成 1 条终末摘要（后端保留 7 天），再开新会话
  const current = chatStore.currentSessionId;
  if (current) {
    try {
      await apiClient.post(`/chat/sessions/${current}/finalize`, {});
    } catch {
      /* 收尾尽力而为，失败不阻断新建 */
    }
  }
  newSession();
  chatStore.setCurrent(null);
}

async function handleDeleteSession(sessionId: string): Promise<void> {
  await chatStore.deleteSession(sessionId, getUserId());
  if (chatStore.currentSessionId === null) newSession();
}

function toggleSources(msg: StreamMessage): void {
  msg.showSources = !msg.showSources;
}

function handleEnter(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    handleSend();
  }
}

function handleLogout(): void {
  authStore.logout();
  router.push('/login');
}

onUnmounted(() => stop());
</script>

<template>
  <div class="chat-layout">
    <aside class="chat-sidebar">
      <el-button class="new-session-btn" @click="handleNewSession">
        <el-icon><Plus /></el-icon>
        新会话
      </el-button>
      <div class="session-list">
        <div
          v-for="session in chatStore.sessions"
          :key="session.session_id"
          :class="[
            'session-item',
            { 'session-item--active': session.session_id === sessionId },
          ]"
          @click="openSession(session.session_id)"
        >
          <span class="session-item__title">{{ session.last_message || '（新会话）' }}</span>
          <el-icon
            class="session-item__delete"
            @click.stop="handleDeleteSession(session.session_id)"
          >
            <Delete />
          </el-icon>
        </div>
        <p v-if="chatStore.sessions.length === 0" class="session-empty">
          暂无历史会话
        </p>
      </div>

      <nav class="side-nav">
        <button class="nav-link nav-link--active" @click="router.push('/chat')">
          AI 安全问答
        </button>
        <button class="nav-link" @click="router.push('/docs')">文档查询</button>
        <button class="nav-link" @click="router.push('/exam')">考试中心</button>
      </nav>

      <div class="sidebar-footer">
        <div class="user-card">
          <div class="user-card__avatar">
            <el-icon :size="18"><User /></el-icon>
          </div>
          <div class="user-card__info">
            <span class="user-card__name">
              {{ authStore.user?.real_name || authStore.user?.username || '未登录' }}
            </span>
            <span class="user-card__meta">
              {{ authStore.user?.position ?? '' }}
              {{ authStore.user?.position ? '·' : '' }}
              {{ authStore.isAdmin ? '管理员' : '作业人员' }}
            </span>
          </div>
        </div>
        <div class="sidebar-footer__actions">
          <el-button v-if="authStore.isAdmin" size="small" @click="router.push('/admin')">
            管理后台
          </el-button>
          <el-button size="small" type="danger" plain @click="handleLogout">退出</el-button>
        </div>
      </div>
    </aside>

    <div class="chat-container">
      <div ref="scrollContainer" class="chat-messages">
        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['chat-message', `chat-message--${msg.role}`]"
        >
          <div class="chat-message__avatar">
            <el-icon v-if="msg.role === 'user'" :size="20"><User /></el-icon>
            <el-icon v-else :size="20"><Monitor /></el-icon>
          </div>
          <div class="chat-message__body">
            <div class="chat-message__content">
              {{ msg.content }}
              <span v-if="msg.streaming" class="chat-cursor">▊</span>
            </div>
            <div v-if="msg.sources && msg.sources.length > 0" class="chat-sources">
              <button class="sources-toggle" @click="toggleSources(msg)">
                {{ msg.showSources ? '▼' : '▶' }} 引用来源 ({{ msg.sources.length }})
              </button>
              <div v-if="msg.showSources" class="sources-list">
                <div
                  v-for="(source, sIndex) in msg.sources"
                  :key="sIndex"
                  class="source-item"
                >
                  <div class="source-item__header">
                    <el-tag size="small" type="info">{{ source.doc_type }}</el-tag>
                    <span class="source-item__score">
                      相似度: {{ (source.score * 100).toFixed(1) }}%
                    </span>
                  </div>
                  <p class="source-item__text">{{ source.text }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-if="messages.length === 0" class="chat-empty">
          <p class="chat-empty__text">开始与工安卫士对话，输入您的安全问题</p>
        </div>
      </div>

      <div class="chat-input-area">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="2"
          placeholder="输入您的问题... (Enter 发送, Shift+Enter 换行)"
          resize="none"
          :disabled="isStreaming"
          @keyup.enter="handleEnter"
        />
        <div class="chat-input-actions">
          <el-button
            v-if="!isStreaming"
            type="primary"
            :disabled="inputText.trim().length === 0"
            @click="handleSend"
          >
            发送
          </el-button>
          <el-button v-else type="danger" @click="stop">
            停止生成
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-layout {
  display: flex;
  height: 100vh;
  max-width: 1200px;
  margin: 0 auto;
}

.chat-sidebar {
  width: 240px;
  flex-shrink: 0;
  border-right: 1px solid #ebeef5;
  background: #fafbfc;
  display: flex;
  flex-direction: column;
  padding: 12px;
}

.new-session-btn {
  width: 100%;
  margin-bottom: 12px;
}

.session-list {
  flex: 1;
  overflow-y: auto;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 4px;
  font-size: 13px;
  color: #303133;
}

.session-item:hover {
  background: #eef2f7;
}

.session-item--active {
  background: #e6f0fa;
}

.session-item__title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-item__delete {
  color: #c0c4cc;
  flex-shrink: 0;
}

.session-item__delete:hover {
  color: #f56c6c;
}

.session-empty {
  text-align: center;
  color: #909399;
  font-size: 12px;
  padding: 16px 0;
}

.side-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  border-top: 1px solid #ebeef5;
  padding-top: 10px;
  margin-bottom: 8px;
}

.nav-link {
  text-align: left;
  padding: 8px 10px;
  border: none;
  background: none;
  color: #606266;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

.nav-link:hover {
  background: #eef2f7;
  color: #303133;
}

.nav-link--active {
  background: #e6f0fa;
  color: #2b6cb0;
  font-weight: 600;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #fff;
}

.chat-message {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.chat-message--user {
  flex-direction: row-reverse;
}

.chat-message--user .chat-message__body {
  align-items: flex-end;
}

.chat-message__avatar {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e6f0fa;
  color: #1a2a3a;
}

.chat-message--user .chat-message__avatar {
  background: #1a2a3a;
  color: #fff;
}

.chat-message__body {
  display: flex;
  flex-direction: column;
  max-width: 70%;
}

.chat-message__content {
  padding: 12px 16px;
  border-radius: 8px;
  background: #f5f7fa;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.chat-message--user .chat-message__content {
  background: #1a2a3a;
  color: #fff;
}

.chat-cursor {
  display: inline-block;
  animation: blink 1s steps(2) infinite;
  color: #409eff;
}

@keyframes blink {
  0% { opacity: 1; }
  50% { opacity: 0; }
}

.chat-sources {
  margin-top: 8px;
  width: 100%;
}

.sources-toggle {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 13px;
  color: #409eff;
  padding: 4px 0;
}

.sources-toggle:hover {
  text-decoration: underline;
}

.sources-list {
  margin-top: 8px;
  padding: 8px 12px;
  background: #f9fafc;
  border-radius: 6px;
}

.source-item {
  margin-bottom: 12px;
}

.source-item:last-child {
  margin-bottom: 0;
}

.source-item__header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.source-item__score {
  font-size: 12px;
  color: #909399;
}

.source-item__text {
  margin: 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}

.chat-empty {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.sidebar-footer {
  border-top: 1px solid #ebeef5;
  padding-top: 12px;
  margin-top: 12px;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.user-card__avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #e6f0fa;
  color: #14508a;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-card__info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.user-card__name {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-card__meta {
  font-size: 12px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-footer__actions {
  display: flex;
  gap: 8px;
}

.sidebar-footer__actions .el-button {
  flex: 1;
}

.chat-empty__text {
  color: #909399;
  font-size: 15px;
}

.chat-input-area {
  padding: 16px 20px;
  border-top: 1px solid #ebeef5;
  background: #fff;
}

.chat-input-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
</style>
