import type { ExamResult, ExamSummary, Question } from '@/types'
import { EXAM_LIST, EXAM_RESULTS, PAPERS } from '@/mock/data/exams'
import { randomDelay } from '@/mock/delay'

/** 考试 API（mock）。真实后端：/api/v1/exams。 */

export async function fetchExamList(): Promise<ExamSummary[]> {
  await randomDelay(400, 800)
  return EXAM_LIST.map((e) => ({ ...e }))
}

export async function fetchPaper(examId: string): Promise<Question[]> {
  await randomDelay(500, 900)
  return (PAPERS[examId] ?? []).map((q) => ({ ...q }))
}

/** 已批改成绩查询（刷新 / 直接访问成绩页时兜底）。 */
export async function fetchExamResult(examId: string): Promise<ExamResult | null> {
  await randomDelay(300, 600)
  const known = EXAM_RESULTS[examId]
  return known ? { ...known } : null
}

/**
 * 文本相似度（字符 bigram 的 Dice 系数）——mock 层面模拟 embedding 余弦相似度。
 * 真实后端：批改工作流用 BGE-M3 对「作答 vs RAG 检索片段/参考答案」编码后算 cosine。
 */
function textSimilarity(a: string, b: string): number {
  const norm = (s: string): string => s.replace(/[\s，。、；：!！?？]/g, '')
  const sa = norm(a)
  const sb = norm(b)
  if (!sa || !sb) return 0
  if (sa.length < 2 || sb.length < 2) return sa === sb ? 1 : 0
  const grams = (s: string): Set<string> => {
    const g = new Set<string>()
    for (let i = 0; i < s.length - 1; i++) g.add(s.slice(i, i + 2))
    return g
  }
  const ga = grams(sa)
  const gb = grams(sb)
  let inter = 0
  ga.forEach((g) => {
    if (gb.has(g)) inter += 1
  })
  return inter / (ga.size + gb.size - inter)
}

/** RAG 相似度低于该阈值（或未作答）的主观题 → 转教师人工复核 */
const REVIEW_THRESHOLD = 0.35

/**
 * 提交试卷 —— 幂等 mock：
 * 真实后端以 Redis SETNX(exam:{id}:submit:{uid}) + DB 唯一约束双重保证，
 * 重复提交返回既有成绩而非报错。
 */
export async function submitPaper(
  examId: string,
  answers: Record<string, string>,
): Promise<ExamResult> {
  await randomDelay(900, 1400)
  const known = EXAM_RESULTS[examId]
  if (known) return { ...known }
  // 未预置成绩的试卷：按 mock 答案精确匹配客观题 + RAG 增强评分主观题
  const questions = PAPERS[examId] ?? []
  let got = 0
  const graded = questions.map((q): Question => {
    const userAnswer = answers[q.id] ?? ''
    if (q.type === 'short_answer') {
      const sim = textSimilarity(userAnswer, q.answer)
      // rubric 折扣：相似度不直接等于得分率，上限 95%
      const ratio = Math.min(0.95, sim * 1.25)
      const s = Math.round(q.score * ratio)
      const needsReview = !userAnswer.trim() || sim < REVIEW_THRESHOLD
      const simText = (sim * 100).toFixed(1)
      got += s
      return {
        ...q,
        grading: {
          userAnswer,
          gotScore: s,
          rubricScores: {
            准确性: Math.round(s * 0.4 * 10) / 10,
            完整性: Math.round(s * 0.3 * 10) / 10,
            条理性: Math.round(s * 0.3 * 10) / 10,
          },
          reason: !userAnswer.trim()
            ? '未作答（RAG 相似度 0.0%），AI 预评 0 分，已转教师人工复核，最终成绩以复核为准。'
            : needsReview
              ? `RAG 检索规程片段比对：作答与参考答案相似度仅 ${simText}%（阈值 35%），AI 预评 ${s} 分，已转教师人工复核，最终成绩以复核为准。`
              : `RAG 增强评分：与规程参考答案相似度 ${simText}%，按 rubric 三维加权自动评定，可在管理端复核确认。`,
          references: [`依据 RAG 检索片段自动评分（知识点：${q.knowledgeTags.join('、')}）`],
          similarity: Number(sim.toFixed(2)),
          reviewStatus: needsReview ? 'pending' : 'auto',
        },
      }
    }
    const normalize = (s: string): string =>
      s
        .replace(/[，、]/g, ',')
        .split(',')
        .map((x: string) => x.trim().toUpperCase())
        .filter(Boolean)
        .sort()
        .join('')
    const correct =
      q.type === 'multiple'
        ? normalize(userAnswer) === normalize(q.answer)
        : userAnswer.toUpperCase() === q.answer.toUpperCase()
    if (correct) got += q.score
    return { ...q, grading: { userAnswer, gotScore: correct ? q.score : 0, rubricScores: {}, reason: correct ? '回答正确' : '回答错误', references: [] } }
  })
  const total = questions.reduce((s, q) => s + q.score, 0)
  const objective = questions.filter((q) => q.type !== 'short_answer')
  const objOk = objective.filter(
    (q) => graded.find((g) => g.id === q.id)?.grading?.gotScore === q.score,
  ).length
  const exam = EXAM_LIST.find((e) => e.id === examId)
  const result: ExamResult = {
    exam: exam ?? EXAM_LIST[0],
    gotScore: got,
    objectiveCorrectRate: objective.length ? objOk / objective.length : 0,
    weakTags: ['关井程序'],
    rubric: [
      { dimension: '准确性', score: 9, full: 10 },
      { dimension: '完整性', score: 8, full: 10 },
      { dimension: '条理性', score: 8.5, full: 10 },
      { dimension: '规范性', score: 9, full: 10 },
    ],
    questions: graded,
  }
  void total
  // 写回 mock 层：幂等重放返回同一成绩；管理端复核队列可见新提交的主观题
  EXAM_RESULTS[examId] = result
  return result
}
