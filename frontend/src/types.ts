/** 全局领域类型定义 —— 对应后端 gongan 的领域模型。 */

// ---------------------------------------------------------------------------
// 用户与权限
// ---------------------------------------------------------------------------

export type Role = 'worker' | 'admin'

/** 文档可见级别：public 任何人可见 / internal 仅登录可见 / secret 高权限 */
export type AccessLevel = 'public' | 'internal' | 'secret'

export const POSITIONS = [
  '司钻',
  '副司钻',
  '井架工',
  '钻工',
  '泥浆工',
] as const
export type Position = (typeof POSITIONS)[number]

export interface User {
  id: number
  username: string
  name: string
  role: Role
  position: Position
}

// ---------------------------------------------------------------------------
// 安全问答
// ---------------------------------------------------------------------------

export type QueryType = 'factual' | 'relational' | 'visual' | 'structural'

export const QUERY_TYPE_LABEL: Record<QueryType, string> = {
  factual: '事实查询',
  relational: '关系推理',
  visual: '图表理解',
  structural: '体系结构',
}

export type CacheKind =
  | 'redis_exact'
  | 'semantic'
  | 'faq'
  | 'full_rag'

export const CACHE_LABEL: Record<CacheKind, string> = {
  redis_exact: 'Redis 精确命中',
  semantic: '语义缓存',
  faq: 'FAQ 命中',
  full_rag: '完整 RAG',
}

/** LLM 降级路由标签 */
export type LlmRoute = 'qwen-flash' | 'qwen-plus' | 'mock'

export interface RetrievalStep {
  key: string
  label: string
  status: 'pending' | 'running' | 'done' | 'skipped' | 'failed'
  durationMs?: number
  detail?: string
}

export interface Source {
  index: number
  docName: string
  chapter: string
  snippet: string
  score: number
  access: Exclude<AccessLevel, 'secret'>
}

export interface GraphEdge {
  subject: string
  relation: string
  object: string
}

export interface QaAnswer {
  text: string
  sources: Source[]
  graphEdges: GraphEdge[]
  cacheKind: CacheKind
  cacheScore?: number
  queryType: QueryType
  route: LlmRoute
  guardBlocked?: boolean
  permissionDenied?: boolean
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  streaming?: boolean
  answer?: QaAnswer
  steps?: RetrievalStep[]
}

// ---------------------------------------------------------------------------
// 考试
// ---------------------------------------------------------------------------

export type QuestionType = 'single' | 'multiple' | 'judge' | 'short_answer'

export interface Question {
  id: string
  type: QuestionType
  stem: string
  options: string[]
  answer: string
  score: number
  knowledgeTags: string[]
  difficulty: 1 | 2 | 3 | 4 | 5
  /** 主观题批改结果 */
  grading?: {
    userAnswer: string
    gotScore: number
    rubricScores: Record<string, number>
    reason: string
    references: string[]
    /** 作答与 RAG 检索规程片段 / 参考答案的相似度（0-1，两位小数） */
    similarity?: number
    /** 人工复核状态：auto=AI 自动评分；pending=待教师复核；approved=教师已复核 */
    reviewStatus?: 'auto' | 'pending' | 'approved'
    /** 复核人（reviewStatus=approved 时有值） */
    reviewer?: string
  }
}

export type ExamStatus = 'pending' | 'finished'

export interface ExamSummary {
  id: string
  title: string
  position: Position
  tags: string[]
  questionCount: number
  difficulty: 1 | 2 | 3 | 4 | 5
  durationMin: number
  status: ExamStatus
  totalScore: number
  gotScore?: number
  deadline: string
}

export interface ExamResult {
  exam: ExamSummary
  gotScore: number
  objectiveCorrectRate: number
  questions: Question[]
  weakTags: string[]
  rubric: { dimension: string; score: number; full: number }[]
}

/** 管理端主观题人工复核队列条目 */
export interface ReviewItem {
  examId: string
  examTitle: string
  worker: string
  questionId: string
  stem: string
  userAnswer: string
  referenceAnswer: string
  /** AI 预评分时的 RAG 相似度（0-1） */
  similarity: number
  gotScore: number
  fullScore: number
  knowledgeTags: string[]
  reviewStatus: 'auto' | 'pending' | 'approved'
}

/** 人工复核裁决：confirm=确认 AI 评分；adjust=教师改分 */
export interface ReviewDecision {
  examId: string
  questionId: string
  action: 'confirm' | 'adjust'
  newScore?: number
}

// ---------------------------------------------------------------------------
// 管理端
// ---------------------------------------------------------------------------

export interface KpiSet {
  qps: number
  p95Ms: number
  err5xx: number
  cacheHitRate: number
  faqHitRate: number
  llmFallbacks: number
  top5HitRate: number
  graphBuildSec: number
}

export interface TrendPoint {
  time: string
  qps: number
  p95Ms: number
  cacheRate: number
}

export interface RecentQa {
  id: string
  user: string
  question: string
  queryType: QueryType
  cacheKind: CacheKind
  route: LlmRoute
  latencyMs: number
  time: string
}

export interface DocItem {
  id: string
  name: string
  docType: string
  access: AccessLevel
  chunks: number
  status: 'indexed' | 'indexing' | 'failed'
  updatedAt: string
  sizeKb: number
}

export interface FaqItem {
  id: string
  question: string
  answer: string
  tags: string[]
  hitCount: number
  enabled: boolean
}

export interface UserItem {
  id: number
  name: string
  username: string
  role: Role
  position: Position | '-'
  active: boolean
  lastLogin: string
}

export interface AuditItem {
  id: string
  actor: string
  action: string
  target: string
  result: 'success' | 'denied' | 'failed'
  ip: string
  time: string
}

export interface EvalItem {
  id: string
  dataset: string
  metric: string
  score: number
  delta: number
  runAt: string
}

/** 与后端 GET /api/v1/admin/graph/overview 返回结构对齐（entity_type → entityType） */
export interface GraphNode {
  id: string
  name: string
  entityType: string
  degree: number
}

export interface GraphLink {
  source: string
  target: string
  relation: string
  confidence?: number
}

export interface GraphData {
  nodes: GraphNode[]
  links: GraphLink[]
  anchors: string[]
}
