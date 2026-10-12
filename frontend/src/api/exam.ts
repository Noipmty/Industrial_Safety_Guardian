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
      const s = Math.round(q.score * (userAnswer.length > 30 ? 0.9 : 0.6))
      got += s
      return {
        ...q,
        grading: {
          userAnswer,
          gotScore: s,
          rubricScores: { 准确性: s * 0.4, 完整性: s * 0.3, 条理性: s * 0.3 },
          reason:
            'RAG 增强评分：与规程参考答案比对后按 rubric 维度给分，得分仅供参考。',
          references: ['依据检索到的规程片段自动评分（演示）'],
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
  return result
}
