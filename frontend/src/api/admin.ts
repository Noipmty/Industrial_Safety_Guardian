import type {
  AuditItem,
  DocItem,
  EvalItem,
  FaqItem,
  GraphData,
  KpiSet,
  RecentQa,
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

export { GRAPH_STATS }
