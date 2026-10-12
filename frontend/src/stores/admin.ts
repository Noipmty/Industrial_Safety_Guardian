import { defineStore } from 'pinia'
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
  fetchAudits,
  fetchDocuments,
  fetchEvals,
  fetchFaqs,
  fetchGraph,
  fetchKpis,
  fetchRecentQa,
  fetchTrend,
  fetchUsers,
  GRAPH_STATS,
} from '@/api/admin'

interface AdminState {
  kpis: KpiSet | null
  trend: TrendPoint[]
  recentQa: RecentQa[]
  loading: boolean
  documents: DocItem[]
  faqs: FaqItem[]
  users: UserItem[]
  audits: AuditItem[]
  evals: EvalItem[]
  graph: GraphData | null
  graphStats: typeof GRAPH_STATS | null
}

export const useAdminStore = defineStore('admin', {
  state: (): AdminState => ({
    kpis: null,
    trend: [],
    recentQa: [],
    loading: false,
    documents: [],
    faqs: [],
    users: [],
    audits: [],
    evals: [],
    graph: null,
    graphStats: null,
  }),
  actions: {
    async loadDashboard() {
      this.loading = true
      try {
        const [kpis, trend, recentQa] = await Promise.all([
          fetchKpis(),
          fetchTrend(),
          fetchRecentQa(),
        ])
        this.kpis = kpis
        this.trend = trend
        this.recentQa = recentQa
      } finally {
        this.loading = false
      }
    },
    async loadDocuments() {
      this.documents = await fetchDocuments()
    },
    async loadFaqs() {
      this.faqs = await fetchFaqs()
    },
    async loadUsers() {
      this.users = await fetchUsers()
    },
    async loadAudits() {
      this.audits = await fetchAudits()
    },
    async loadEvals() {
      this.evals = await fetchEvals()
    },
    async loadGraph() {
      const { data, stats } = await fetchGraph()
      this.graph = data
      this.graphStats = stats
    },
  },
})
