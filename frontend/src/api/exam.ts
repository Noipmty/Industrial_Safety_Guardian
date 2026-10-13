import type { ExamResult, ExamSummary, Position, Question } from '@/types'
import { http, isRealMode } from './http'
import { EXAM_LIST, EXAM_RESULTS, PAPERS } from '@/mock/data/exams'
import { randomDelay } from '@/mock/delay'

/**
 * 考试 API。
 * - mock 模式：直接读写前端内置 mock 数据，完全不发 http 请求
 * - 真实模式：调用 /api/v1/exam/*，失败兜底 mock 数据
 */

// ---------------------------------------------------------------------------
// 真实后端 DTO
// ---------------------------------------------------------------------------

interface BackendExamListItem {
  id: number
  position: string
  status: string
  total_score: number | null
  created_at: string
  submitted_at: string | null
}

interface BackendExamQuestion {
  id: number
  question_type: string
  stem: string
  options: string[] | null
  score: number
}

interface BackendExamDetail {
  id: number
  position: string
  status: string
  questions: BackendExamQuestion[]
  total_score: number
  time_limit: number
}

interface BackendSubmitAnswer {
  question_id: number
  user_answer: string
}

interface BackendGradedAnswer {
  question_id: number
  user_answer: string
  score: number
  grading_detail: string | null
  graded_by: string
}

interface BackendSubmitResp {
  exam_id: number
  status: string
  total_score: number
  answers: BackendGradedAnswer[]
}

interface BackendExamResult {
  exam: BackendExamDetail
  questions: BackendExamQuestion[]
  answers: BackendGradedAnswer[]
  analysis: { weak_points: string[]; strong_points: string[] }
}

function mapQuestionType(t: string): Question['type'] {
  switch (t) {
    case 'multiple_choice':
    case 'multiple':
      return 'multiple'
    case 'judge':
    case 'true_false':
      return 'judge'
    case 'short_answer':
    case 'essay':
      return 'short_answer'
    default:
      return 'single'
  }
}

const POSITION_MAP: Record<string, Position> = {
  司钻: '司钻',
  副司钻: '副司钻',
  井架工: '井架工',
  钻工: '钻工',
  泥浆工: '泥浆工',
}

// ---------------------------------------------------------------------------
// 列表
// ---------------------------------------------------------------------------

export async function fetchExamList(userId: number): Promise<ExamSummary[]> {
  if (!isRealMode) {
    await randomDelay(300, 600)
    return EXAM_LIST.map((e) => ({ ...e }))
  }
  try {
    const { data } = await http.get<BackendExamListItem[]>('/exam/list', {
      params: { user_id: userId },
    })
    return data.map((e) => ({
      id: String(e.id),
      title: e.position,
      position: POSITION_MAP[e.position] ?? '钻工',
      tags: [],
      questionCount: 0,
      difficulty: 2,
      durationMin: 0,
      status: (e.status === 'graded' ? 'finished' : 'pending') as ExamSummary['status'],
      totalScore: e.total_score ?? 100,
      gotScore: e.status === 'graded' ? e.total_score ?? undefined : undefined,
      deadline: e.submitted_at ?? e.created_at.slice(0, 10),
    }))
  } catch {
    return EXAM_LIST.map((e) => ({ ...e }))
  }
}

// ---------------------------------------------------------------------------
// 试卷详情
// ---------------------------------------------------------------------------

export async function fetchPaper(examId: string): Promise<Question[]> {
  if (!isRealMode) {
    await randomDelay(400, 800)
    return (PAPERS[examId] ?? []).map((q) => ({ ...q }))
  }
  try {
    const { data } = await http.get<BackendExamDetail>(`/exam/${examId}`)
    return data.questions.map((q) => ({
      id: String(q.id),
      type: mapQuestionType(q.question_type),
      stem: q.stem,
      options: q.options ?? [],
      answer: '',
      score: q.score,
      knowledgeTags: [],
      difficulty: 2,
    }))
  } catch {
    return (PAPERS[examId] ?? []).map((q) => ({ ...q }))
  }
}

// ---------------------------------------------------------------------------
// 提交试卷（幂等）
// ---------------------------------------------------------------------------

export async function submitPaper(
  examId: string,
  answers: Record<string, string>,
): Promise<ExamResult> {
  if (!isRealMode) {
    await randomDelay(800, 1400)
    return _mockSubmit(examId, answers)
  }
  const payload: BackendSubmitAnswer[] = Object.entries(answers).map(([qid, ans]) => ({
    question_id: Number(qid),
    user_answer: ans,
  }))
  const { data } = await http.post<BackendSubmitResp>(
    `/exam/${examId}/submit`,
    { answers: payload },
  )
  const result = await fetchExamResult(examId)
  if (result) return result
  return {
    exam: {
      id: String(data.exam_id),
      title: '',
      position: '钻工',
      tags: [],
      questionCount: 0,
      difficulty: 2,
      durationMin: 0,
      status: 'finished',
      totalScore: 100,
      gotScore: data.total_score,
      deadline: new Date().toISOString().slice(0, 10),
    },
    gotScore: data.total_score,
    objectiveCorrectRate: 0,
    questions: [],
    weakTags: [],
    rubric: [],
  }
}

/** mock 判分：客观题精确匹配 + 主观题相似度 + 写回 EXAM_RESULTS */
function _mockSubmit(examId: string, answers: Record<string, string>): ExamResult {
  const known = EXAM_RESULTS[examId]
  if (known) return known
  const questions = PAPERS[examId] ?? []
  let got = 0
  const graded: Question[] = questions.map((q) => {
    const userAnswer = answers[q.id] ?? ''
    if (q.type === 'short_answer') {
      const similarity = _dice(userAnswer, q.answer)
      const threshold = 0.35
      const autoScore = Math.round(q.score * Math.min(similarity * 0.95, 0.95))
      const pendingReview = similarity < threshold
      got += autoScore
      return {
        ...q,
        grading: {
          userAnswer,
          gotScore: autoScore,
          rubricScores: { 准确性: autoScore * 0.4, 完整性: autoScore * 0.3, 条理性: autoScore * 0.3 },
          reason: pendingReview
            ? `RAG 相似度 ${(similarity * 100).toFixed(1)}% < 阈值 ${(threshold * 100).toFixed(0)}%，自动转教师人工复核`
            : `RAG 相似度 ${(similarity * 100).toFixed(1)}%，AI 自动评分`,
          references: ['依据检索到的规程片段自动评分（演示）'],
          similarity,
          reviewStatus: pendingReview ? 'pending' : 'auto',
        },
      }
    }
    const normalize = (s: string): string =>
      s
        .replace(/[，、]/g, ',')
        .split(',')
        .map((x) => x.trim().toUpperCase())
        .filter(Boolean)
        .sort()
        .join('')
    const correct =
      q.type === 'multiple'
        ? normalize(userAnswer) === normalize(q.answer)
        : userAnswer.toUpperCase() === q.answer.toUpperCase()
    if (correct) got += q.score
    return {
      ...q,
      grading: {
        userAnswer,
        gotScore: correct ? q.score : 0,
        rubricScores: {} as Record<string, number>,
        reason: correct ? '回答正确' : '回答错误',
        references: [],
      },
    }
  })
  const total = questions.reduce((s, q) => s + q.score, 0)
  const objective = questions.filter((q) => q.type !== 'short_answer')
  const objOk = objective.filter(
    (q) => graded.find((g) => g.id === q.id)?.grading?.gotScore === q.score,
  ).length
  const exam = EXAM_LIST.find((e) => e.id === examId) ?? EXAM_LIST[0]
  const result: ExamResult = {
    exam,
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
  EXAM_RESULTS[examId] = result
  return result
}

/** Dice 系数：简单的字符 bigram 相似度，模拟 embedding 余弦 */
function _dice(a: string, b: string): number {
  const bigrams = (s: string): string[] => {
    const cleaned = s.replace(/\s/g, '')
    if (cleaned.length < 2) return [cleaned]
    const arr: string[] = []
    for (let i = 0; i < cleaned.length - 1; i++) arr.push(cleaned.slice(i, i + 2))
    return arr
  }
  const A = bigrams(a)
  const B = bigrams(b)
  if (A.length === 0 || B.length === 0) return 0
  const bCount = new Map<string, number>()
  for (const x of B) bCount.set(x, (bCount.get(x) ?? 0) + 1)
  let hit = 0
  for (const x of A) {
    const c = bCount.get(x) ?? 0
    if (c > 0) {
      hit += 1
      bCount.set(x, c - 1)
    }
  }
  return (2 * hit) / (A.length + B.length)
}

// ---------------------------------------------------------------------------
// 成绩查询
// ---------------------------------------------------------------------------

export async function fetchExamResult(examId: string): Promise<ExamResult | null> {
  if (!isRealMode) {
    await randomDelay(200, 500)
    return EXAM_RESULTS[examId] ?? null
  }
  try {
    const { data } = await http.get<BackendExamResult>(`/exam/${examId}/result`)
    return _mapResult(data)
  } catch {
    return EXAM_RESULTS[examId] ?? null
  }
}

async function _mapResult(data: BackendExamResult): Promise<ExamResult> {
  const graded = data.answers ?? []
  const q_map = new Map(data.questions.map((q) => [String(q.id), q]))
  const questions: Question[] = graded.map((ga) => {
    const q = q_map.get(String(ga.question_id))
    return {
      id: String(ga.question_id),
      type: q ? mapQuestionType(q.question_type) : 'short_answer',
      stem: q?.stem ?? '',
      options: q?.options ?? [],
      answer: '',
      score: q?.score ?? 5,
      knowledgeTags: [],
      difficulty: 2,
      grading: {
        userAnswer: ga.user_answer,
        gotScore: ga.score,
        rubricScores: {},
        reason: ga.grading_detail ?? 'AI 自动评分',
        references: [],
        reviewStatus: ga.graded_by === 'human' ? 'approved' : 'auto',
      },
    }
  })
  const got = graded.reduce((s, a) => s + a.score, 0)
  const objective = questions.filter((q) => q.type !== 'short_answer')
  const objOk = objective.filter((q) => (q.grading?.gotScore ?? 0) === q.score).length
  return {
    exam: {
      id: String(data.exam.id),
      title: data.exam.position,
      position: POSITION_MAP[data.exam.position] ?? '钻工',
      tags: [],
      questionCount: data.questions.length,
      difficulty: 2,
      durationMin: data.exam.time_limit,
      status: 'finished',
      totalScore: data.exam.total_score,
      gotScore: got,
      deadline: new Date().toISOString().slice(0, 10),
    },
    gotScore: got,
    objectiveCorrectRate: objective.length ? objOk / objective.length : 0,
    questions,
    weakTags: data.analysis?.weak_points ?? [],
    rubric: [
      { dimension: '准确性', score: 0, full: 10 },
      { dimension: '完整性', score: 0, full: 10 },
      { dimension: '条理性', score: 0, full: 10 },
      { dimension: '规范性', score: 0, full: 10 },
    ],
  }
}

// ---------------------------------------------------------------------------
// AI 出卷（管理端调用真实后端，mock 模式在 QuestionBankView 里直接操作 mock 数据）
// ---------------------------------------------------------------------------

export interface ExamGeneratePayload {
  userId: number
  position: string
  knowledgeTags: string[]
  numQuestions: number
  typeCounts?: Record<string, number>
}

export async function generateExam(payload: ExamGeneratePayload): Promise<number> {
  const { data } = await http.post<{ exam_id: number }>('/exam/generate', {
    user_id: payload.userId,
    position: payload.position,
    knowledge_tags: payload.knowledgeTags,
    num_questions: payload.numQuestions,
    question_types: Object.keys(payload.typeCounts ?? {}),
    type_counts: payload.typeCounts ?? {},
  })
  return data.exam_id
}
