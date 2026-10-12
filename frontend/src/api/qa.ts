import type { RetrievalStep } from '@/types'
import { QA_KNOWLEDGE } from '@/mock/data/knowledge'
import { buildPlan, nextId, runMockSse } from '@/mock/sse'

/**
 * 安全问答 API。
 * 真实后端：POST /api/v1/chat (text/event-stream)；
 * 此处用 runMockSse 在浏览器侧模拟 SSE 步骤流 + 逐字回答。
 */
export interface ChatStreamHandlers {
  onSteps: (steps: RetrievalStep[]) => void
  onStepDone: (index: number, detail?: string) => void
  onDelta: (text: string) => void
  onDone: (fullText: string) => void
}

export function streamChat(
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

export function newMessageId(role: 'user' | 'assistant'): string {
  return nextId(role)
}
