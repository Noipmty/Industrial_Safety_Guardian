import { reactive } from 'vue'
import { defineStore } from 'pinia'
import type { ChatMessage, RetrievalStep } from '@/types'
import { streamChat } from '@/api/qa'
import { QA_KNOWLEDGE } from '@/mock/data/knowledge'

let uid = 0
function mid(): string {
  uid += 1
  return `m${uid}`
}

interface QaState {
  messages: ChatMessage[]
  sending: boolean
  /** 当前流式消息的检索步骤 */
  activeSteps: RetrievalStep[]
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
  }),
  actions: {
    /** 发送问题；返回取消函数（停止流式渲染）。 */
    ask(question: string): () => void {
      if (this.sending || !question.trim()) return () => undefined
      this.sending = true
      this.activeSteps = []
      const isInjection = question.includes('忽略以上') || question.includes('系统提示词')
      this.messages.push({ id: mid(), role: 'user', content: question })
      const bubble = reactive<ChatMessage>({
        id: mid(),
        role: 'assistant',
        content: '',
        streaming: true,
        steps: [],
      })
      this.messages.push(bubble)

      const cancel = streamChat(question, {
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
        onDone: (payload) => {
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
          } else {
            const answer = JSON.parse(payload) as (typeof QA_KNOWLEDGE)['默认']
            bubble.content = answer.text
            bubble.answer = answer
          }
        },
      })
      return cancel
    },
  },
})
