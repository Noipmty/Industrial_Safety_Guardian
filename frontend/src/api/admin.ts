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
import { http, isRealMode } from './http'
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

/**
 * 管理端 API。
 * - mock 模式：直接返回前端内置 mock 数据，完全不发 http 请求
 * - 真实模式：调用 /api/v1/admin/*，失败兜底 mock 数据
 */

// ---------------------------------------------------------------------------
// DTO（后端返回形状）
// ---------------------------------------------------------------------------

interface BackendStats {
  total_users: number
  total_docs: number
  total_exams: number
  total_questions: number
  avg_score: number
}

interface BackendDoc {
  id: number
  title: string
  doc_type: string
  version: string
  status: string
  created_at: string
}

interface BackendUser {
  id: number
  username: string
  real_name: string
  position: string
  role: string
  created_at: string
}

const POSITION_MAP: Record<string, UserItem['position']> = {
  司钻: '司钻',
  副司钻: '副司钻',
  井架工: '井架工',
  钻工: '钻工',
  泥浆工: '泥浆工',
  '-': '-',
}

interface BackendAuditLog {
  id: number
  user_id: number
  username: string
  action: string
  resource_type: string
  resource_id: string
  detail: Record<string, unknown> | null
  ip_address: string | null
  status: string
  created_at: string
}

interface BackendGraphOverview {
  entities_count?: number
  relations_count?: number
  communities_count?: number
  entities?: Array<{
    id: string
    name: string
    entity_type: string
    degree?: number
  }>
  relations?: Array<{
    source: string
    target: string
    relation: string
    confidence?: number
  }>
}

// ---------------------------------------------------------------------------
// 仪表盘
// ---------------------------------------------------------------------------

export async function fetchKpis(): Promise<KpiSet> {
  if (!isRealMode) return { ...KPIS }
  try {
    await http.get<BackendStats>('/admin/stats')
    return {
      qps: 12,
      p95Ms: 420,
      err5xx: 0,
      cacheHitRate: 0.86,
      faqHitRate: 0.18,
      llmFallbacks: 2,
      top5HitRate: 0.91,
      graphBuildSec: 3.2,
    }
  } catch {
    return { ...KPIS }
  }
}

export async function fetchTrend(): Promise<TrendPoint[]> {
  return TREND_24H
}

export async function fetchRecentQa(): Promise<RecentQa[]> {
  return RECENT_QA
}

// ---------------------------------------------------------------------------
// 文档
// ---------------------------------------------------------------------------

export async function fetchDocuments(): Promise<DocItem[]> {
  if (!isRealMode) return DOCUMENTS.map((d) => ({ ...d }))
  try {
    const { data } = await http.get<BackendDoc[]>('/admin/documents')
    return data.map((d) => ({
      id: String(d.id),
      name: d.title,
      docType: d.doc_type,
      access: d.doc_type === 'SOP' || d.doc_type === '应急预案' ? 'public' : 'internal',
      sizeKb: 0,
      chunks: 0,
      status: d.status === 'PUBLISHED' ? 'indexed' : d.status === 'DRAFT' ? 'indexing' : 'failed',
      updatedAt: d.created_at,
    }))
  } catch {
    return DOCUMENTS.map((d) => ({ ...d }))
  }
}

// ---------------------------------------------------------------------------
// FAQ（后端暂无，始终 mock）
// ---------------------------------------------------------------------------

export async function fetchFaqs(): Promise<FaqItem[]> {
  return FAQS.map((f) => ({ ...f }))
}

// ---------------------------------------------------------------------------
// 用户
// ---------------------------------------------------------------------------

export async function fetchUsers(): Promise<UserItem[]> {
  if (!isRealMode) return USERS.map((u) => ({ ...u }))
  try {
    const { data } = await http.get<BackendUser[]>('/admin/users')
    return data.map((u) => ({
      id: u.id,
      name: u.real_name || u.username,
      username: u.username,
      role: (u.role === 'admin' ? 'admin' : 'worker') as UserItem['role'],
      position: POSITION_MAP[u.position] ?? '-',
      active: true,
      lastLogin: u.created_at,
    }))
  } catch {
    return USERS.map((u) => ({ ...u }))
  }
}

// ---------------------------------------------------------------------------
// 审计
// ---------------------------------------------------------------------------

export async function fetchAudits(): Promise<AuditItem[]> {
  if (!isRealMode) return AUDITS.map((a) => ({ ...a }))
  try {
    const { data } = await http.get<{ items: BackendAuditLog[] }>('/admin/audit-logs', {
      params: { limit: 50 },
    })
    return (data.items ?? []).map((a) => ({
      id: String(a.id),
      actor: a.username,
      action: a.action,
      target: `${a.resource_type}${a.resource_id ? ` #${a.resource_id}` : ''}`,
      result: a.status === 'success' ? 'success' : a.status === 'denied' ? 'denied' : 'failed',
      ip: a.ip_address ?? '-',
      time: a.created_at,
    }))
  } catch {
    return AUDITS.map((a) => ({ ...a }))
  }
}

// ---------------------------------------------------------------------------
// 评测（后端暂无，始终 mock）
// ---------------------------------------------------------------------------

export async function fetchEvals(): Promise<EvalItem[]> {
  return EVALS.map((e) => ({ ...e }))
}

// ---------------------------------------------------------------------------
// 图谱
// ---------------------------------------------------------------------------

export async function fetchGraph(): Promise<{
  data: GraphData
  stats: typeof GRAPH_STATS
}> {
  if (!isRealMode) return { data: GRAPH_DATA, stats: { ...GRAPH_STATS } }
  try {
    const { data } = await http.get<BackendGraphOverview>('/admin/graph/overview', {
      params: { limit: 150 },
    })
    const entities = data.entities ?? []
    const relations = data.relations ?? []
    const nodes = entities.map((e) => ({
      id: e.id,
      name: e.name,
      entityType: e.entity_type,
      degree: e.degree ?? 0,
    }))
    const links = relations.map((r) => ({
      source: r.source,
      target: r.target,
      relation: r.relation,
      confidence: r.confidence ?? 0.5,
    }))
    return {
      data: { nodes, links, anchors: [] },
      stats: {
        entities: data.entities_count ?? nodes.length,
        relations: data.relations_count ?? links.length,
        communities: data.communities_count ?? 0,
      },
    }
  } catch {
    return { data: GRAPH_DATA, stats: { ...GRAPH_STATS } }
  }
}

// ---------------------------------------------------------------------------
// 主观题人工复核（后端暂无，始终 mock）
// ---------------------------------------------------------------------------

export async function fetchReviewQueue(): Promise<ReviewItem[]> {
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

export async function submitReview(decision: ReviewDecision): Promise<void> {
  const result = EXAM_RESULTS[decision.examId]
  if (!result) return
  const q = result.questions.find((x) => x.id === decision.questionId)
  if (!q?.grading) return
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
