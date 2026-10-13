import type { ExamResult, ExamSummary, Position, Question } from '@/types'
import { http } from './http'

/**
 * 考试 API —— 真实后端：/api/v1/exam/*
 * 后端字段与前端类型差异较大，此处做 DTO 映射。
 */

// ---------------------------------------------------------------------------
// DTO（后端返回形状）
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

// ---------------------------------------------------------------------------
// 前端需要的辅助：把后端 question_type 映射到前端 Question.type
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// 列表
// ---------------------------------------------------------------------------

const POSITION_MAP: Record<string, Position> = {
  司钻: '司钻',
  副司钻: '副司钻',
  井架工: '井架工',
  钻工: '钻工',
  泥浆工: '泥浆工',
}

export async function fetchExamList(userId: number): Promise<ExamSummary[]> {
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
}

// ---------------------------------------------------------------------------
// 试卷详情（含题目，不含答案）
// ---------------------------------------------------------------------------

export async function fetchPaper(examId: string): Promise<Question[]> {
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
}

// ---------------------------------------------------------------------------
// 提交试卷（幂等）
// ---------------------------------------------------------------------------

export async function submitPaper(
  examId: string,
  answers: Record<string, string>,
): Promise<ExamResult> {
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
  // 兜底：后端未判分，用提交响应拼一个
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

// ---------------------------------------------------------------------------
// 成绩查询
// ---------------------------------------------------------------------------

export async function fetchExamResult(examId: string): Promise<ExamResult | null> {
  try {
    const { data } = await http.get<BackendExamResult>(`/exam/${examId}/result`)
    void data // 见下方 graded 映射
    return await _mapResult(data)
  } catch {
    return null
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
// AI 出卷（管理端调用真实后端）
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
