import { reactive } from 'vue'
import { defineStore } from 'pinia'
import type { ChatMessage, RetrievalStep, Source } from '@/types'
import { streamChat, fetchSessions, fetchHistoryMessages } from '@/api/qa'
import type { ChatSession } from '@/api/qa'
import { isRealMode } from '@/api/http'
import { QA_KNOWLEDGE } from '@/mock/data/knowledge'

let uid = 0
function mid(): string {
  uid += 1
  return `m${uid}`
}

function genSessionId(): string {
  return `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

interface QaState {
  messages: ChatMessage[]
  sending: boolean
  activeSteps: RetrievalStep[]
  /** 真实模式：当前会话 ID（跨消息持久，后端用它做记忆） */
  sessionId: string | null
  /** 真实模式：会话列表 */
  sessions: ChatSession[]
  /** 会话列表加载中 */
  sessionsLoading: boolean
}

export const useQaStore = defineStore('qa', {
  state: (): QaState => ({
    messages: [
      {
        id: mid(),
        role: 'assistant',
        content:
          '您好，我是「工安卫士」安全问答助手。您可以问我井控、硫化氢防护、个人防护装备等安全问题。',
      },
    ],
    sending: false,
    activeSteps: [],
    sessionId: null,
    sessions: [],
    sessionsLoading: false,
  }),
  actions: {
    /** 发送问题；返回取消函数（停止流式渲染）。 */
    ask(question: string, userId?: number): () => void {
      if (this.sending || !question.trim()) return () => undefined
      this.sending = true
      this.activeSteps = []
      const isInjection =
        question.includes('忽略以上') || question.includes('系统提示词')

      this.messages.push({ id: mid(), role: 'user', content: question })
      const bubble = reactive<ChatMessage>({
        id: mid(),
        role: 'assistant',
        content: '',
        streaming: true,
        steps: [],
      })
      this.messages.push(bubble)

      // 真实模式：确保有 sessionId
      const opts =
        isRealMode && userId
          ? { sessionId: this.sessionId, userId }
          : undefined

      const cancel = streamChat(
        question,
        {
          onSteps: (steps) => {
            this.activeSteps = steps
            bubble.steps = steps
          },
          onStepDone: (index) => {
            if (this.activeSteps[index]) {
              this.activeSteps[index].status = 'done'
            }
          },
          onDelta: (text) => {
            bubble.content += text
          },
          onSources: (sourcesJson) => {
            // 真实模式：后端返回 sources JSON
            try {
              const raw = JSON.parse(sourcesJson) as Array<{
                doc_type?: string
                score?: number
                text?: string
                position?: string
                access_level?: string
              }>
              const sources: Source[] = raw.map((s, i) => ({
                index: i + 1,
                docName: s.doc_type ?? '未知文档',
                chapter: s.position ?? '',
                snippet: (s.text ?? '').slice(0, 200),
                score: s.score ?? 0,
                access: (s.access_level === 'internal'
                  ? 'internal'
                  : 'public') as Source['access'],
              }))
              bubble.answer = {
                text: bubble.content,
                sources,
                graphEdges: [],
                cacheKind: 'full_rag',
                queryType: 'factual',
                route: 'qwen-plus',
              }
            } catch {
              // sources 解析失败不阻塞
            }
          },
          onDone: (fullText) => {
            bubble.streaming = false
            this.sending = false
            if (isInjection) {
              bubble.content =
                '您的消息包含不允许的指令内容，请重新描述您的安全问题。'
              bubble.answer = {
                text: bubble.content,
                sources: [],
                graphEdges: [],
                cacheKind: 'full_rag',
                queryType: 'factual',
                route: 'mock',
                guardBlocked: true,
              }
              return
            }
            if (isRealMode && opts) {
              // 真实模式：fullText 已通过 onDelta 累积到 bubble.content
              if (!bubble.answer) {
                bubble.answer = {
                  text: bubble.content || fullText,
                  sources: [],
                  graphEdges: [],
                  cacheKind: 'full_rag',
                  queryType: 'factual',
                  route: 'qwen-plus',
                }
              }
              // 异步刷新会话列表（后端已写入 session index）
              void this.loadSessions(opts.userId)
            } else {
              // mock 模式：fullText 是 JSON 串
              const answer = JSON.parse(fullText) as (typeof QA_KNOWLEDGE)['默认']
              bubble.content = answer.text
              bubble.answer = answer
            }
          },
        },
        opts,
      )
      return cancel
    },

    /** 真实模式：新建会话 */
    newSession(): void {
      this.sessionId = genSessionId()
      this.messages = [
        {
          id: mid(),
          role: 'assistant',
          content:
            '您好，我是「工安卫士」安全问答助手。您可以问我井控、硫化氢防护、个人防护装备等安全问题。',
        },
      ]
      this.activeSteps = []
    },

    /** 真实模式：加载用户会话列表 */
    async loadSessions(userId: number): Promise<void> {
      if (!isRealMode) return
      this.sessionsLoading = true
      try {
        this.sessions = await fetchSessions(userId)
      } catch {
        // 静默失败
      } finally {
        this.sessionsLoading = false
      }
    },

    /** 真实模式：切换到已有会话，加载历史消息 */
    async switchSession(sessionId: string): Promise<void> {
      this.sessionId = sessionId
      try {
        const history = await fetchHistoryMessages(sessionId)
        this.messages = history.map((m) => ({
          id: mid(),
          role: (m.role === 'assistant' ? 'assistant' : 'user') as
            | 'user'
            | 'assistant',
          content: m.content,
        }))
        // 确保有欢迎语
        if (this.messages.length === 0) {
          this.messages.push({
            id: mid(),
            role: 'assistant',
            content: '（会话历史为空）',
          })
        }
      } catch {
        // 加载失败，保持空
      }
    },
  },
})
