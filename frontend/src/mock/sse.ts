import type { QaAnswer, QueryType } from '@/types'

/**
 * SSE 流式回答模拟器。
 *
 * 真实后端使用 text/event-stream；此处在浏览器侧用定时器逐字吐出，
 * 接口形状与 fetch+ReadableStream 消费方式一致，便于日后替换。
 */

export interface SsePlan {
  steps: { key: string; label: string; ms: number; detail?: string }[]
  answer: QaAnswer
}

export interface SseHandlers {
  onStep: (index: number, detail?: string) => void
  onDelta: (text: string) => void
  onAnswer: (answer: QaAnswer) => void
}

let seq = 0

function cancelToken(): { cancelled: boolean } {
  return { cancelled: false }
}

/** 依次播放检索步骤 → 逐字输出答案 → 回调最终答案对象。返回取消函数。 */
export function runMockSse(plan: SsePlan, handlers: SseHandlers): () => void {
  const token = cancelToken()
  void (async () => {
    for (let i = 0; i < plan.steps.length; i++) {
      if (token.cancelled) return
      const step = plan.steps[i]
      await sleep(step.ms, token)
      if (token.cancelled) return
      handlers.onStep(i, step.detail)
    }
    // 逐字输出（每次 2-4 字符，20ms 节奏）
    const text = plan.answer.text
    for (let i = 0; i < text.length; ) {
      if (token.cancelled) return
      const size = 2 + Math.floor(Math.random() * 3)
      handlers.onDelta(text.slice(i, i + size))
      i += size
      await sleep(18, token)
    }
    if (token.cancelled) return
    handlers.onAnswer(plan.answer)
  })()
  return () => {
    token.cancelled = true
  }
}

function sleep(ms: number, token: { cancelled: boolean }): Promise<void> {
  return new Promise((resolve) => {
    const t = setTimeout(resolve, ms)
    // 若被取消则尽快结束
    const check = setInterval(() => {
      if (token.cancelled) {
        clearTimeout(t)
        clearInterval(check)
        resolve()
      }
    }, 40)
    setTimeout(() => clearInterval(check), ms + 10)
  })
}

/** 依据问题关键词构造一份"检索计划"（演示用启发式）。 */
export function buildPlan(
  question: string,
  knowledge: Record<string, QaAnswer>,
): SsePlan {
  let answer: QaAnswer | undefined
  let key = ''
  for (const k of Object.keys(knowledge)) {
    if (question.includes(k)) {
      answer = knowledge[k]
      key = k
      break
    }
  }
  if (!answer) {
    answer = knowledge['默认']
    key = '默认'
  }
  const queryType: QueryType = answer.queryType
  const base = [
    { key: 'understand', label: '查询理解', ms: 320, detail: `意图=${queryType} · 改写「${question.slice(0, 18)}」` },
    { key: 'cache', label: '缓存查找', ms: 220 },
    { key: 'faq', label: 'FAQ 查找', ms: 200 },
    { key: 'memory', label: '记忆检索', ms: 260 },
    { key: 'plan', label: '工具规划', ms: 220 },
    { key: 'tools', label: '并行执行', ms: 620 },
    { key: 'gate', label: '质量门控', ms: 280 },
    { key: 'fuse', label: '结果融合', ms: 240 },
  ]
  if (answer.cacheKind === 'redis_exact') {
    // 缓存命中：跳过 FAQ/工具/门控，直接融合
    base[2].ms = 90
    base[2].detail = '未命中'
    base.splice(4, 3)
  } else if (answer.cacheKind === 'faq') {
    base[2].detail = `FAQ 相似度 ${answer.cacheScore?.toFixed(2) ?? '0.86'}`
    base.splice(3, 4)
  } else {
    base[1].detail = '未命中'
    base[2].detail = '未命中'
    base[4].detail =
      queryType === 'relational'
        ? 'hybrid_search + graph_rag'
        : 'hybrid_search'
  }
  if (key !== '默认') base[0].detail += ` · 知识点「${key}」`
  return { steps: base, answer }
}

export function nextId(prefix: string): string {
  seq += 1
  return `${prefix}-${Date.now().toString(36)}-${seq}`
}
