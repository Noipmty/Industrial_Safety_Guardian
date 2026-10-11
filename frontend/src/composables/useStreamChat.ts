import { ref } from 'vue';
import { apiClient, ApiError } from '@/api/client';
import type { ChatSource } from '@/api/types';

export interface StreamMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: ChatSource[];
  streaming?: boolean;
  showSources?: boolean;
  timestamp: string;
}

/**
 * 流式对话交互状态（通过 apiClient.streamChat 走 SSE）。
 * 手写的 ReadableStream 解析逻辑位于 api/client.ts。
 */
export function useStreamChat() {
  const messages = ref<StreamMessage[]>([]);
  const isStreaming = ref(false);
  const sessionId = ref<string | null>(null);
  const abortController = ref<AbortController | null>(null);

  async function send(
    text: string,
    userId: number,
    onSessionId?: (sessionId: string) => void,
    scope?: 'admin' | null,
  ): Promise<void> {
    if (!text.trim() || isStreaming.value) return;

    messages.value.push({
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    });
    const assistant: StreamMessage = {
      role: 'assistant',
      content: '',
      streaming: true,
      showSources: false,
      timestamp: new Date().toISOString(),
    };
    messages.value.push(assistant);

    isStreaming.value = true;
    abortController.value = new AbortController();

    try {
      await apiClient.streamChat(
        {
          session_id: sessionId.value ?? undefined,
          message: text,
          user_id: userId,
          stream: true,
          scope: scope ?? undefined,
        },
        {
          onToken: (token: string) => {
            assistant.content += token;
          },
          onSources: (sources: ChatSource[]) => {
            assistant.sources = sources;
          },
          onDone: () => {
            assistant.streaming = false;
          },
        },
        abortController.value.signal,
      );
      if (onSessionId && sessionId.value) {
        onSessionId(sessionId.value);
      }
    } catch (error) {
      assistant.streaming = false;
      if (error instanceof DOMException && error.name === 'AbortError') {
        assistant.content += '\n\n[已停止生成]';
      } else if (error instanceof ApiError) {
        assistant.content += `\n\n[错误: ${error.message}]`;
        throw error;
      } else {
        assistant.content += '\n\n[请求失败]';
        throw error;
      }
    } finally {
      assistant.streaming = false;
      isStreaming.value = false;
      abortController.value = null;
    }
  }

  /** 绑定已有 session（加载历史记录）以继续对话。 */
  function adoptSession(id: string, history: StreamMessage[]): void {
    sessionId.value = id;
    messages.value = history;
  }

  function newSession(): void {
    sessionId.value = null;
    messages.value = [];
  }

  function stop(): void {
    abortController.value?.abort();
  }

  return {
    messages,
    isStreaming,
    sessionId,
    send,
    adoptSession,
    newSession,
    stop,
  };
}
