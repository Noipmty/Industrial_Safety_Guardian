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
import { REAL_GRAPH, REAL_GRAPH_STATS } from './graph-real'

export const KPIS: KpiSet = {
  qps: 12.4,
  p95Ms: 1840,
  err5xx: 2,
  cacheHitRate: 0.612,
  faqHitRate: 0.148,
  llmFallbacks: 3,
  top5HitRate: 0.87,
  graphBuildSec: 96,
}

export const TREND_24H: TrendPoint[] = Array.from({ length: 24 }, (_, i) => ({
  time: `${String(i).padStart(2, '0')}:00`,
  qps: +(6 + 8 * Math.sin((i / 24) * Math.PI * 1.4) + Math.random() * 2).toFixed(1),
  p95Ms: Math.round(1400 + 900 * Math.abs(Math.sin((i / 24) * Math.PI * 1.2)) + Math.random() * 220),
  cacheRate: +(0.5 + Math.random() * 0.25).toFixed(3),
}))

export const RECENT_QA: RecentQa[] = [
  { id: 'rq-1', user: '张司钻', question: '发现溢流后第一步做什么？', queryType: 'structural', cacheKind: 'semantic', route: 'qwen-flash', latencyMs: 2120, time: '10-12 14:32' },
  { id: 'rq-2', user: '李钻工', question: '安全帽佩戴有什么要求？', queryType: 'factual', cacheKind: 'faq', route: 'qwen-flash', latencyMs: 640, time: '10-12 14:21' },
  { id: 'rq-3', user: '王井架工', question: '井架工与钻工职责区别', queryType: 'relational', cacheKind: 'full_rag', route: 'qwen-plus', latencyMs: 3350, time: '10-12 13:58' },
  { id: 'rq-4', user: '赵泥浆工', question: '泥浆密度如何测定', queryType: 'factual', cacheKind: 'redis_exact', route: 'qwen-flash', latencyMs: 120, time: '10-12 13:40' },
  { id: 'rq-5', user: '张司钻', question: 'H2S 报警后怎么撤离', queryType: 'structural', cacheKind: 'semantic', route: 'qwen-flash', latencyMs: 1890, time: '10-12 13:11' },
]

export const CACHE_PIE = [
  { name: 'Redis 精确命中', value: 21 },
  { name: '语义缓存', value: 40 },
  { name: 'FAQ 命中', value: 15 },
  { name: '完整 RAG', value: 24 },
]

export const TOOL_BAR = [
  { name: 'hybrid_search', value: 628 },
  { name: 'graph_rag', value: 142 },
  { name: 'multimodal_rag', value: 36 },
  { name: 'sql_query', value: 12 },
]

export const DOCUMENTS: DocItem[] = [
  { id: 'd1', name: '钻井井控技术规程 (Q/SY 1552-2019)', docType: '规程标准', access: 'public', chunks: 48, status: 'indexed', updatedAt: '2026-10-08', sizeKb: 1250 },
  { id: 'd2', name: '含硫油气田硫化氢防护安全规程', docType: '规程标准', access: 'public', chunks: 36, status: 'indexed', updatedAt: '2026-10-08', sizeKb: 980 },
  { id: 'd3', name: '井控设备操作手册（内部）', docType: '操作手册', access: 'internal', chunks: 52, status: 'indexed', updatedAt: '2026-10-09', sizeKb: 2100 },
  { id: 'd4', name: '井场应急处置卡汇编（内部）', docType: '应急预案', access: 'internal', chunks: 28, status: 'indexed', updatedAt: '2026-10-09', sizeKb: 720 },
  { id: 'd5', name: '钻井队坐岗管理制度（内部）', docType: '管理制度', access: 'internal', chunks: 16, status: 'indexing', updatedAt: '2026-10-12', sizeKb: 320 },
  { id: 'd6', name: '井场个人防护装备配置标准', docType: '配置标准', access: 'public', chunks: 22, status: 'indexed', updatedAt: '2026-10-10', sizeKb: 460 },
  { id: 'd7', name: '高处作业安全规范', docType: '规程标准', access: 'public', chunks: 19, status: 'failed', updatedAt: '2026-10-11', sizeKb: 380 },
  { id: 'd8', name: '钻井队岗位职责划分（机密）', docType: '管理制度', access: 'secret', chunks: 0, status: 'indexed', updatedAt: '2026-10-06', sizeKb: 210 },
]

export const FAQS: FaqItem[] = [
  { id: 'f1', question: '发现溢流第一步做什么？', answer: '立即发出长鸣警报，停止无关作业，并按软关井程序准备关井。', tags: ['井控', '溢流'], hitCount: 128, enabled: true },
  { id: 'f2', question: '硫化氢报警阈值是多少？', answer: '10ppm 一级预警、20ppm 二级预警（佩戴正压呼吸器）、100ppm 危险撤离。', tags: ['硫化氢'], hitCount: 96, enabled: true },
  { id: 'f3', question: '安全帽有什么佩戴要求？', answer: '下颏带收紧、帽壳无裂纹、入井场必戴。', tags: ['PPE'], hitCount: 74, enabled: true },
  { id: 'f4', question: '坐岗记录多久填一次？', answer: '每 2 小时巡查并填写一次，异常加密。', tags: ['坐岗'], hitCount: 41, enabled: true },
  { id: 'f5', question: '高处作业安全带怎么挂？', answer: '五点式安全带，高挂低用，挂点承载力不低于 15kN。', tags: ['高处作业'], hitCount: 35, enabled: false },
]

export const USERS: UserItem[] = [
  { id: 1, name: '张建国', username: 'zhangjg', role: 'worker', position: '司钻', active: true, lastLogin: '2026-10-12 08:02' },
  { id: 2, name: '李卫东', username: 'liwd', role: 'worker', position: '钻工', active: true, lastLogin: '2026-10-12 07:45' },
  { id: 3, name: '王小峰', username: 'wangxf', role: 'worker', position: '井架工', active: true, lastLogin: '2026-10-11 19:20' },
  { id: 4, name: '赵有田', username: 'zhaoyt', role: 'worker', position: '泥浆工', active: false, lastLogin: '2026-10-02 16:11' },
  { id: 5, name: '刘安全', username: 'admin', role: 'admin', position: '-', active: true, lastLogin: '2026-10-12 09:00' },
  { id: 6, name: '陈培训', username: 'chensx', role: 'admin', position: '-', active: true, lastLogin: '2026-10-10 11:26' },
]

export const AUDITS: AuditItem[] = [
  { id: 'a1', actor: 'zhangjg', action: '问答提问', target: '发现溢流怎么处置', result: 'success', ip: '10.8.2.14', time: '2026-10-12 14:32' },
  { id: 'a2', actor: 'liwd', action: '访问内部文档', target: '井控设备操作手册 第4章', result: 'denied', ip: '10.8.2.31', time: '2026-10-12 14:05' },
  { id: 'a3', actor: 'admin', action: '上传文档', target: '钻井队坐岗管理制度.pdf', result: 'success', ip: '10.8.1.2', time: '2026-10-12 10:41' },
  { id: 'a4', actor: 'wangxf', action: '提交考试', target: '10 月井控综合考核', result: 'success', ip: '10.8.2.52', time: '2026-10-11 19:26' },
  { id: 'a5', actor: 'zhaoyt', action: '登录系统', target: 'Web 端', result: 'failed', ip: '10.8.3.9', time: '2026-10-11 18:03' },
  { id: 'a6', actor: 'admin', action: '重建知识图谱', target: 'graph-build job#96', result: 'success', ip: '10.8.1.2', time: '2026-10-10 22:15' },
  { id: 'a7', actor: 'chensx', action: '发布试卷', target: '硫化氢防护月度测验', result: 'success', ip: '10.8.1.7', time: '2026-10-10 15:30' },
]

export const EVALS: EvalItem[] = [
  { id: 'e1', dataset: '井控知识集-200', metric: 'faithfulness', score: 0.92, delta: 0.03, runAt: '2026-10-11' },
  { id: 'e2', dataset: '井控知识集-200', metric: 'answer_relevancy', score: 0.88, delta: 0.05, runAt: '2026-10-11' },
  { id: 'e3', dataset: '井控知识集-200', metric: 'context_precision', score: 0.84, delta: 0.02, runAt: '2026-10-11' },
  { id: 'e4', dataset: '井控知识集-200', metric: 'context_recall', score: 0.9, delta: 0.01, runAt: '2026-10-11' },
  { id: 'e5', dataset: '硫化氢防护集-80', metric: 'faithfulness', score: 0.95, delta: 0.02, runAt: '2026-10-09' },
  { id: 'e6', dataset: '硫化氢防护集-80', metric: 'answer_relevancy', score: 0.86, delta: -0.01, runAt: '2026-10-09' },
]

export const GRAPH_DATA: GraphData = REAL_GRAPH

/** 与后端 /admin/graph/overview 的 stats 字段一致（2840 实体 / 3850 关系 / 223 社区） */
export const GRAPH_STATS = { ...REAL_GRAPH_STATS }
