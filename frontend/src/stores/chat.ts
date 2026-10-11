import { defineStore } from 'pinia';
import apiClient from '@/api/client';
import type { ChatSession } from '@/api/types';

interface ChatState {
  sessions: ChatSession[];
  currentSessionId: string | null;
  loading: boolean;
}

export const useChatStore = defineStore('chat', {
  state: (): ChatState => ({
    sessions: [],
    currentSessionId: null,
    loading: false,
  }),

  actions: {
    async fetchSessions(userId: number): Promise<void> {
      this.loading = true;
      try {
        this.sessions = await apiClient.get<ChatSession[]>(
          `/chat/sessions?user_id=${userId}`,
        );
      } finally {
        this.loading = false;
      }
    },

    async loadHistory(
      sessionId: string,
    ): Promise<Array<{ role: 'user' | 'assistant'; content: string }>> {
      const messages = await apiClient.get<
        Array<{ role: 'user' | 'assistant'; content: string }>
      >(`/chat/sessions/${sessionId}/messages`);
      this.currentSessionId = sessionId;
      return messages;
    },

    async deleteSession(sessionId: string, userId: number): Promise<void> {
      await apiClient.delete(`/chat/sessions/${sessionId}`);
      this.sessions = this.sessions.filter((s) => s.session_id !== sessionId);
      if (this.currentSessionId === sessionId) {
        this.currentSessionId = null;
      }
      await this.fetchSessions(userId);
    },

    setCurrent(sessionId: string | null): void {
      this.currentSessionId = sessionId;
    },
  },
});
