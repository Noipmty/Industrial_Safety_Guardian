import type { RetrievalStep } from '@/types'
import { API_BASE_URL, isRealMode } from './http'
import { QA_KNOWLEDGE } from '@/mock/data/knowledge'
import { buildPlan, nextId, runMockSse } from '@/mock/sse'

/**
 * 安全问答 API。
 * - mock 模式：runMockSse 在浏览器侧模拟 SSE 步骤流 + 逐字回答
 * - 真实模式：POST /chat (SSE)，GET /chat/sessions 等会话管理
 */

export interface ChatStreamHandlers {
  onSteps: (steps: RetrievalStep[]) => void
  onStepDone: (index: number, detail?: string) => void
  onDelta: (text: string) => void
  onDone: (fullText: string) => void
  /** 真实模式：收到后端返回的 sources（JSON 字符串） */
  onSources?: (sourcesJson: string) => void
  /** 真实模式：收到后端返回的 session_id */
  onSessionId?: (sessionId: string) => void
}

export interface ChatSession {
  session_id: string
  last_message: string
  created_at: string
  updated_at: string
}

export interface ChatHistoryMessage {
  role: string
  content: string
  created_at: string
}

// ---------------------------------------------------------------------------
// mock 模式
// ---------------------------------------------------------------------------

function streamChatMock(
  question: string,
  handlers: ChatStreamHandlers,
): () => void {
  const plan = buildPlan(question, QA_KNOWLEDGE)
  const steps: RetrievalStep[] = plan.steps.map((s) => ({
    key: s.key,
    label: s.label,
    status: 'pending',
    detail: s.detail,
  }))
  handlers.onSteps(steps)

  let acc = ''
  return runMockSse(plan, {
    onStep: (i, detail) => {
      steps[i].status = 'done'
      if (detail) steps[i].detail = detail
      handlers.onStepDone(i, detail)
    },
    onDelta: (t) => {
      acc += t
      handlers.onDelta(t)
    },
    onAnswer: (answer) => {
      handlers.onDone(JSON.stringify(answer))
    },
  })
}

// ---------------------------------------------------------------------------
// 真实模式：fetch SSE 流式
// ---------------------------------------------------------------------------

function streamChatReal(
  question: string,
  handlers: ChatStreamHandlers,
  opts: { sessionId: string | null; userId: number },
): () => void {
  // 真实后端不暴露逐步检索进度，前端展示简化步骤流
  const steps: RetrievalStep[] = [
    { key: 'retrieve', label: '检索知识库', status: 'pending', detail: '混合检索 + GraphRAG' },
    { key: 'generate', label: '生成回答', status: 'pending', detail: 'LLM 融合引用' },
  ]
  handlers.onSteps(steps)
  let stepIdx = 0
  handlers.onStepDone(stepIdx, '检索完成')
  stepIdx = 1

  const controller = new AbortController()
  const token = (() => {
    try {
      const raw = localStorage.getItem('gw_token')
      return raw ? JSON.parse(raw).token : ''
    } catch {
      return localStorage.getItem('gw_token') ?? ''
    }
  })()

  void (async () => {
    try {
      const url = `${API_BASE_URL}/chat`
      const body: Record<string, unknown> = {
        message: question,
        user_id: opts.userId,
        stream: true,
      }
      if (opts.sessionId) body.session_id = opts.sessionId

      const resp = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      })

      if (!resp.ok) {
        const errText = await resp.text().catch(() => resp.statusText)
        throw new Error(`HTTP ${resp.status}: ${errText}`)
      }

      const reader = resp.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let buffer = ''
      let fullText = ''
      let sourcesJson = ''

      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        // SSE: 以 \n\n 分隔事件
        const parts = buffer.split('\n\n')
        buffer = parts.pop() ?? ''

        for (const part of parts) {
          const line = part.trim()
          if (!line.startsWith('data: ')) continue
          const dataStr = line.slice(6)
          if (dataStr === '[DONE]') continue

          try {
            const evt = JSON.parse(dataStr) as {
              type: string
              content: string
            }
            if (evt.type === 'token') {
              fullText += evt.content
              handlers.onDelta(evt.content)
            } else if (evt.type === 'sources') {
              sourcesJson = evt.content
              handlers.onSources?.(evt.content)
            } else if (evt.type === 'done') {
              if (stepIdx < steps.length) {
                steps[stepIdx].status = 'done'
                handlers.onStepDone(stepIdx)
              }
            }
          } catch {
            // 非 JSON 行，跳过
          }
        }
      }

      // 后端可能在非标准的 response header 或首次返回中带 session_id
      // 从 response 中提取（chat.py 在 _touch_session_index 中存入 Redis，
      // 但 SSE 首次返回不显式带 session_id —— 前端用自己传的或新生成的）
      handlers.onDone(fullText || '(空响应)')
      if (sourcesJson) handlers.onSources?.(sourcesJson)
    } catch (err) {
      if (controller.signal.aborted) return
      const msg = err instanceof Error ? err.message : String(err)
      handlers.onDelta(`\n\n[请求失败: ${msg}]`)
      handlers.onDone('')
    }
  })()

  return () => controller.abort()
}

// ---------------------------------------------------------------------------
// 统一入口
// ---------------------------------------------------------------------------

export function streamChat(
  question: string,
  handlers: ChatStreamHandlers,
  opts?: { sessionId: string | null; userId: number },
): () => void {
  if (isRealMode && opts) {
    return streamChatReal(question, handlers, opts)
  }
  return streamChatMock(question, handlers)
}

export function newMessageId(role: 'user' | 'assistant'): string {
  return nextId(role)
}

// ---------------------------------------------------------------------------
// 会话管理 API（仅真实模式有效）
// ---------------------------------------------------------------------------

export async function fetchSessions(userId: number): Promise<ChatSession[]> {
  const token = (() => {
    try {
      const raw = localStorage.getItem('gw_token')
      return raw ? JSON.parse(raw).token : ''
    } catch {
      return localStorage.getItem('gw_token') ?? ''
    }
  })()
  const resp = await fetch(
    `${API_BASE_URL}/chat/sessions?user_id=${userId}`,
    { headers: token ? { Authorization: `Bearer ${token}` } : {} },
  )
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return (await resp.json()) as ChatSession[]
}

export async function fetchHistoryMessages(
  sessionId: string,
): Promise<ChatHistoryMessage[]> {
  const token = (() => {
    try {
      const raw = localStorage.getItem('gw_token')
      return raw ? JSON.parse(raw).token : ''
    } catch {
      return localStorage.getItem('gw_token') ?? ''
    }
  })()
  const resp = await fetch(
    `${API_BASE_URL}/chat/sessions/${sessionId}/messages`,
    { headers: token ? { Authorization: `Bearer ${token}` } : {} },
  )
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return (await resp.json()) as ChatHistoryMessage[]
}

export async function finalizeSession(sessionId: string): Promise<string> {
  const token = (() => {
    try {
      const raw = localStorage.getItem('gw_token')
      return raw ? JSON.parse(raw).token : ''
    } catch {
      return localStorage.getItem('gw_token') ?? ''
    }
  })()
  const resp = await fetch(
    `${API_BASE_URL}/chat/sessions/${sessionId}/finalize`,
    { method: 'POST', headers: token ? { Authorization: `Bearer ${token}` } : {} },
  )
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  const data = (await resp.json()) as { summary: string }
  return data.summary
}

export async function deleteSession(sessionId: string): Promise<void> {
  const token = (() => {
    try {
      const raw = localStorage.getItem('gw_token')
      return raw ? JSON.parse(raw).token : ''
    } catch {
      return localStorage.getItem('gw_token') ?? ''
    }
  })()
  const resp = await fetch(
    `${API_BASE_URL}/chat/sessions/${sessionId}`,
    { method: 'DELETE', headers: token ? { Authorization: `Bearer ${token}` } : {} },
  )
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
}
