import type {
  AuditItem,
  DocItem,
  EvalItem,
  FaqItem,
  GraphData,
  KpiSet,
  RecentQa,
  ReviewDecision,
  ReviewItem,
  TrendPoint,
  UserItem,
} from '@/types'
import {
  AUDITS,
  DOCUMENTS,
  EVALS,
  FAQS,
  GRAPH_DATA,
  GRAPH_STATS,
  KPIS,
  RECENT_QA,
  TREND_24H,
  USERS,
} from '@/mock/data/admin'
import { EXAM_RESULTS } from '@/mock/data/exams'
import { randomDelay } from '@/mock/delay'

/** 管理端 API（mock）。真实后端：/api/v1/admin/*。 */

export async function fetchKpis(): Promise<KpiSet> {
  await randomDelay(300, 600)
  return { ...KPIS }
}

export async function fetchTrend(): Promise<TrendPoint[]> {
  await randomDelay(300, 600)
  return TREND_24H
}

export async function fetchRecentQa(): Promise<RecentQa[]> {
  await randomDelay(300, 600)
  return RECENT_QA
}

export async function fetchDocuments(): Promise<DocItem[]> {
  await randomDelay(400, 800)
  return DOCUMENTS.map((d) => ({ ...d }))
}

export async function fetchFaqs(): Promise<FaqItem[]> {
  await randomDelay(400, 800)
  return FAQS.map((f) => ({ ...f }))
}

export async function fetchUsers(): Promise<UserItem[]> {
  await randomDelay(400, 800)
  return USERS.map((u) => ({ ...u }))
}

export async function fetchAudits(): Promise<AuditItem[]> {
  await randomDelay(400, 800)
  return AUDITS.map((a) => ({ ...a }))
}

export async function fetchEvals(): Promise<EvalItem[]> {
  await randomDelay(400, 800)
  return EVALS.map((e) => ({ ...e }))
}

export async function fetchGraph(): Promise<{
  data: GraphData
  stats: typeof GRAPH_STATS
}> {
  await randomDelay(500, 900)
  return { data: GRAPH_DATA, stats: { ...GRAPH_STATS } }
}

// ---- 主观题人工复核 ----

/** 复核队列：展开所有成绩中带批改结果的主观题（真实后端：GET /api/v1/admin/review/queue） */
export async function fetchReviewQueue(): Promise<ReviewItem[]> {
  await randomDelay(400, 800)
  const items: ReviewItem[] = []
  for (const result of Object.values(EXAM_RESULTS)) {
    for (const q of result.questions) {
      if (q.type === 'short_answer' && q.grading) {
        items.push({
          examId: result.exam.id,
          examTitle: result.exam.title,
          worker: USERS[0]?.name ?? '张建国',
          questionId: q.id,
          stem: q.stem,
          userAnswer: q.grading.userAnswer,
          referenceAnswer: q.answer,
          similarity: q.grading.similarity ?? 0,
          gotScore: q.grading.gotScore,
          fullScore: q.score,
          knowledgeTags: q.knowledgeTags,
          reviewStatus: q.grading.reviewStatus ?? 'auto',
        })
      }
    }
  }
  return items
}

/**
 * 复核裁决（真实后端：POST /api/v1/admin/review/{examId}/{questionId}）：
 * confirm=确认 AI 评分；adjust=教师改分。裁决后按差值重算该卷总分。
 */
export async function submitReview(decision: ReviewDecision): Promise<void> {
  await randomDelay(500, 900)
  const result = EXAM_RESULTS[decision.examId]
  if (!result) throw new Error('成绩不存在')
  const q = result.questions.find((x) => x.id === decision.questionId)
  if (!q?.grading) throw new Error('题目或批改记录不存在')
  const old = q.grading.gotScore
  q.grading.reviewStatus = 'approved'
  q.grading.reviewer = '刘安全（admin）'
  if (decision.action === 'adjust' && decision.newScore !== undefined) {
    const s = Math.max(0, Math.min(q.score, decision.newScore))
    q.grading.gotScore = s
    q.grading.reason += ` 教师复核改分：${old} → ${s}。`
  } else {
    q.grading.reason += ' 教师复核：确认 AI 评分。'
  }
  result.gotScore = result.gotScore - old + q.grading.gotScore
}

export { GRAPH_STATS }
