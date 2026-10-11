<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import type { FormInstance, UploadFile } from 'element-plus'
import client from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import AdminQaPanel from '@/components/AdminQaPanel.vue'
import FaqManagePanel from '@/components/FaqManagePanel.vue'
import type {
  AdminStats,
  AdminUser,
  DocumentListItem,
  DocumentStatus,
  ExamListItem,
} from '@/api/types'

const router = useRouter()
const authStore = useAuthStore()
const activeTab = ref('dashboard')

// ---------------------------------------------------------------------------
// 仪表盘
// ---------------------------------------------------------------------------
const stats = shallowRef<AdminStats | null>(null)
const statsLoading = ref(false)

async function loadStats(): Promise<void> {
  statsLoading.value = true
  try {
    stats.value = await client.get<AdminStats>('/admin/stats')
  } catch (e) {
    console.error('Failed to load stats', e)
  } finally {
    statsLoading.value = false
  }
}

// ---------------------------------------------------------------------------
// 知识库（文档管理）
// ---------------------------------------------------------------------------
const docs = shallowRef<DocumentListItem[]>([])
const docsLoading = ref(false)
const uploading = ref(false)
const uploadProgress = ref<DocumentStatus | null>(null)
const uploadPollingId = ref<number | null>(null)

const docTypeOptions = [
  { label: '操作规程', value: '操作规程' },
  { label: '应急预案', value: '应急预案' },
  { label: '国家标准', value: '国家标准' },
  { label: '行业规范', value: '行业规范' },
  { label: '安全培训', value: '安全培训' },
]

const uploadForm = ref({
  doc_type: '操作规程',
  title: '',
  version: 'v1.0',
})
const uploadFile = ref<File | null>(null)

function onUploadFileChange(file: UploadFile): void {
  if (file.raw) {
    uploadFile.value = file.raw
    if (!uploadForm.value.title) {
      uploadForm.value.title = file.name.replace(/\.[^.]+$/, '')
    }
  }
}

function onUploadRemove(): void {
  uploadFile.value = null
  uploadForm.value.title = ''
}

async function handleUpload(): Promise<void> {
  if (!uploadFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  uploading.value = true
  uploadProgress.value = null

  try {
    const form = new FormData()
    form.append('file', uploadFile.value)
    form.append('doc_type', uploadForm.value.doc_type)
    form.append('title', uploadForm.value.title || uploadFile.value.name)
    form.append('version', uploadForm.value.version)

    const result = await client.post<{ doc_id: number; status: string }>(
      '/admin/documents',
      form,
    )

    ElMessage.success('文档已提交，正在处理…')
    pollDocStatus(result.doc_id)

    uploadFile.value = null
    uploadForm.value = { doc_type: '操作规程', title: '', version: 'v1.0' }
  } catch (e: unknown) {
    const err = e as Error
    ElMessage.error(err.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

async function pollDocStatus(docId: number): Promise<void> {
  const stopPolling = (): void => {
    if (uploadPollingId.value !== null) {
      clearInterval(uploadPollingId.value)
      uploadPollingId.value = null
    }
  }

  uploadPollingId.value = window.setInterval(async () => {
    try {
      const status = await client.get<DocumentStatus>(
        `/admin/documents/${docId}/status`,
      )
      uploadProgress.value = status

      if (status.progress >= 100 || status.error) {
        stopPolling()
        if (status.error) {
          ElMessage.error(`处理失败：${status.error}`)
        } else {
          ElMessage.success(`处理完成，共 ${status.chunks_count} 个片段`)
          await loadDocs()
        }
      }
    } catch (e) {
      console.error('Poll status error', e)
      stopPolling()
    }
  }, 1500)
}

async function loadDocs(): Promise<void> {
  docsLoading.value = true
  try {
    docs.value = await client.get<DocumentListItem[]>('/admin/documents')
  } catch (e) {
    console.error('Failed to load docs', e)
  } finally {
    docsLoading.value = false
  }
}

async function deleteDoc(docId: number): Promise<void> {
  try {
    await ElMessageBox.confirm('确认删除该文档？（进入回收站）', '提示', {
      type: 'warning',
    })
  } catch {
    return
  }

  try {
    await client.delete(`/admin/documents/${docId}`)
    ElMessage.success('已删除')
    await loadDocs()
  } catch (e: unknown) {
    const err = e as Error
    ElMessage.error(err.message || '删除失败')
  }
}

function statusTag(status: string): { type: string; label: string } {
  const map: Record<string, { type: string; label: string }> = {
    draft: { type: 'info', label: '待处理' },
    processing: { type: 'warning', label: '处理中' },
    published: { type: 'success', label: '已发布' },
    error: { type: 'danger', label: '错误' },
    archived: { type: 'info', label: '已归档' },
  }
  return map[status] ?? { type: 'info', label: status }
}

// ---------------------------------------------------------------------------
// 知识检索
// ---------------------------------------------------------------------------
const searchQuery = ref('')
const searchLoading = ref(false)
const searchResults = ref<{
  query: string
  total: number
  hits: Array<{
    chunk_id: string
    doc_id: number
    chunk_index: number
    text: string
    doc_type: string
    position: string
    version: string
    score: number
  }>
} | null>(null)

async function handleSearch(): Promise<void> {
  if (!searchQuery.value.trim()) return
  searchLoading.value = true
  try {
    const params = new URLSearchParams({
      q: searchQuery.value.trim(),
      top_k: '10',
    })
    searchResults.value = await client.get(
      `/admin/search?${params.toString()}`,
    )
  } catch (e: unknown) {
    const err = e as Error
    ElMessage.error(err.message || '搜索失败')
  } finally {
    searchLoading.value = false
  }
}

// ---------------------------------------------------------------------------
// Chunk 预览对话框
// ---------------------------------------------------------------------------
const chunkDialogVisible = ref(false)
const chunkLoading = ref(false)
const chunksData = ref<{
  doc_id: number
  total_chunks: number
  chunks: Array<{
    chunk_id: string
    chunk_index: number
    text: string
    content_hash: string
  }>
} | null>(null)

async function previewChunks(docId: number): Promise<void> {
  chunkDialogVisible.value = true
  chunkLoading.value = true
  chunksData.value = null
  try {
    chunksData.value = await client.get(
      `/admin/documents/${docId}/chunks`,
    )
  } catch (e: unknown) {
    const err = e as Error
    ElMessage.error(err.message || '加载失败（文档可能尚未索引）')
  } finally {
    chunkLoading.value = false
  }
}

// ---------------------------------------------------------------------------
// 用户管理
// ---------------------------------------------------------------------------
const users = shallowRef<AdminUser[]>([])
const usersLoading = ref(false)
const userDialogVisible = ref(false)
const userFormRef = ref<FormInstance>()
const userForm = ref({
  username: '',
  password: '',
  real_name: '',
  position: '司钻',
  role: 'worker' as 'worker' | 'supervisor' | 'admin',
})

const positionOptions = ['司钻', '副钻', '安全员', '值班经理', '技术员']
const roleLabelMap: Record<string, string> = {
  admin: '安全管理员',
  supervisor: '主管',
  worker: '普通员工',
}

async function loadUsers(): Promise<void> {
  usersLoading.value = true
  try {
    users.value = await client.get<AdminUser[]>('/admin/users')
  } catch (e) {
    console.error('Failed to load users', e)
  } finally {
    usersLoading.value = false
  }
}

function openAddUserDialog(): void {
  userForm.value = {
    username: '',
    password: '',
    real_name: '',
    position: '司钻',
    role: 'worker',
  }
  userDialogVisible.value = true
}

async function handleAddUser(): Promise<void> {
  if (!userFormRef.value) return
  const valid = await userFormRef.value.validate().catch(() => false)
  if (!valid) return

  try {
    await client.post('/admin/users', userForm.value)
    ElMessage.success('用户已创建')
    userDialogVisible.value = false
    await loadUsers()
  } catch (e: unknown) {
    const err = e as Error
    ElMessage.error(err.message || '创建失败')
  }
}

async function deleteUser(targetUser: AdminUser): Promise<void> {
  if (targetUser.id === authStore.user?.id) {
    ElMessage.warning('不能删除当前登录用户')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认删除用户 ${targetUser.username}？`,
      '提示',
      { type: 'warning' },
    )
  } catch {
    return
  }

  try {
    await client.delete(`/admin/users/${targetUser.id}`)
    ElMessage.success('已删除')
    await loadUsers()
  } catch (e: unknown) {
    const err = e as Error
    ElMessage.error(err.message || '删除失败')
  }
}

// ---------------------------------------------------------------------------
// 考试管理
// ---------------------------------------------------------------------------
const allExams = shallowRef<ExamListItem[]>([])
const examsLoading = ref(false)

async function loadAllExams(): Promise<void> {
  examsLoading.value = true
  try {
    allExams.value = await client.get<ExamListItem[]>(
      '/exam/list?user_id=-1',
    ).catch(() => [])
  } catch (e) {
    console.error('Failed to load exams', e)
  } finally {
    examsLoading.value = false
  }
}

// 智能组卷
const genForm = ref({
  target_user_id: null as number | null,
  position: '司钻',
  count_single: 9,
  count_multiple: 0,
  count_judge: 0,
  count_short_answer: 1,
})
const generating = ref(false)

const EXAM_POSITIONS = ['司钻', '副司钻', '井架工', '钻工', '泥浆工', '安全管理员']

const examPresets = [
  { label: '小卷 10 题（9 单选 + 1 简答）', single: 9, multiple: 0, judge: 0, short: 1 },
  { label: '中卷 20 题（18 单选 + 2 简答）', single: 18, multiple: 0, judge: 0, short: 2 },
  { label: '大卷 30 题（27 单选 + 3 简答）', single: 27, multiple: 0, judge: 0, short: 3 },
]

function applyPreset(p: (typeof examPresets)[number]): void {
  genForm.value.count_single = p.single
  genForm.value.count_multiple = p.multiple
  genForm.value.count_judge = p.judge
  genForm.value.count_short_answer = p.short
}

function genTotal(): number {
  const f = genForm.value
  return f.count_single + f.count_multiple + f.count_judge + f.count_short_answer
}

async function generateExam(): Promise<void> {
  const f = genForm.value
  if (!f.target_user_id) {
    ElMessage.warning('请选择参考考试的用户')
    return
  }
  if (genTotal() < 1 || genTotal() > 50) {
    ElMessage.warning('题目总数需在 1–50 之间')
    return
  }
  generating.value = true
  try {
    const typeCounts: Record<string, number> = {}
    if (f.count_single > 0) typeCounts.single = f.count_single
    if (f.count_multiple > 0) typeCounts.multiple = f.count_multiple
    if (f.count_judge > 0) typeCounts.judge = f.count_judge
    if (f.count_short_answer > 0) typeCounts.short_answer = f.count_short_answer
    await client.post('/exam/generate', {
      user_id: f.target_user_id,
      position: f.position,
      question_types: Object.keys(typeCounts),
      num_questions: genTotal(),
      type_counts: typeCounts,
    })
    ElMessage.success('组卷任务已提交，AI 正在出题，稍后刷新列表查看')
    await loadAllExams()
  } catch (e: unknown) {
    const err = e as Error
    ElMessage.error(err.message || '组卷失败')
  } finally {
    generating.value = false
  }
}

// ---------------------------------------------------------------------------
// 审计日志
// ---------------------------------------------------------------------------
const auditLogs = shallowRef<Array<{
  id: number
  user_id: number
  username: string
  action: string
  resource_type: string | null
  resource_id: string | null
  detail: Record<string, unknown> | null
  ip_address: string | null
  status: string
  created_at: string
}>>([])
const auditLogsLoading = ref(false)
const auditTotal = ref(0)
const auditLimit = ref(100)
const auditOffset = ref(0)
const auditFilterAction = ref('')
const auditFilterUserId = ref<number | null>(null)

async function loadAuditLogs(): Promise<void> {
  auditLogsLoading.value = true
  try {
    const params = new URLSearchParams({
      limit: String(auditLimit.value),
      offset: String(auditOffset.value),
    })
    if (auditFilterAction.value) params.set('action', auditFilterAction.value)
    if (auditFilterUserId.value !== null) {
      params.set('user_id', String(auditFilterUserId.value))
    }
    const result = await client.get<{
      total: number
      limit: number
      offset: number
      items: typeof auditLogs.value
    }>(`/admin/audit-logs?${params.toString()}`)
    auditLogs.value = result.items
    auditTotal.value = result.total
  } catch (e) {
    console.error('Failed to load audit logs', e)
  } finally {
    auditLogsLoading.value = false
  }
}

function resetAuditFilters(): void {
  auditFilterAction.value = ''
  auditFilterUserId.value = null
  auditOffset.value = 0
  loadAuditLogs()
}

// ---------------------------------------------------------------------------
// 知识图谱（GraphRAG 可视化）
// ---------------------------------------------------------------------------
interface GraphNode {
  id: string
  name: string
  entity_type: string
  degree: number
}
interface GraphEdge {
  source: string
  target: string
  relation: string
  confidence: number
}
interface GraphData {
  stats: { entities: number; relations: number; communities: number }
  nodes: GraphNode[]
  edges: GraphEdge[]
  anchors: string[]
}

const graphData = shallowRef<GraphData | null>(null)
const graphLoading = ref(false)
const graphSearchQuery = ref('')
const graphRebuilding = ref(false)
const graphDom = ref<HTMLDivElement | null>(null)
let graphChart: echarts.ECharts | null = null
let graphStatusTimer: number | null = null

const GRAPH_PALETTE = [
  '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
  '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#8d98b3',
]

function graphTypeColor(t: string): string {
  let h = 0
  for (let i = 0; i < t.length; i++) h = (h * 31 + t.charCodeAt(i)) >>> 0
  return GRAPH_PALETTE[h % GRAPH_PALETTE.length]
}

function graphTypeLegend(): Array<{ type: string; color: string }> {
  const types = new Set((graphData.value?.nodes ?? []).map((n) => n.entity_type))
  return Array.from(types).map((t) => ({ type: t, color: graphTypeColor(t) }))
}

function ensureChart(): echarts.ECharts | null {
  if (!graphDom.value) return null
  if (!graphChart) {
    graphChart = echarts.init(graphDom.value)
    window.addEventListener('resize', handleGraphResize)
  }
  graphChart.resize()
  return graphChart
}

function handleGraphResize(): void {
  graphChart?.resize()
}

function renderGraph(data: GraphData): void {
  const chart = ensureChart()
  if (!chart) return
  const anchors = new Set(data.anchors)
  const nodeCount = data.nodes.length
  const showLabels = nodeCount <= 100
  const option: echarts.EChartsOption = {
    backgroundColor: '#fafbfd',
    tooltip: {
      formatter: (p: unknown) => {
        const params = p as { dataType: string; data: GraphNode & Partial<GraphEdge> }
        if (params.dataType === 'edge') {
          return `${params.data.source}<br/>→ <b>${params.data.relation}</b> →<br/>${params.data.target}`
        }
        const d = params.data as GraphNode
        const anchorTag = anchors.has(d.name) ? '<br/><span style="color:#67c23a">◆ 匹配实体</span>' : ''
        return `<b>${d.name}</b><br/>类型: ${d.entity_type}<br/>关联数: ${d.degree}${anchorTag}`
      },
    },
    animationDuration: 600,
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        data: data.nodes.map((n) => ({
          ...n,
          symbolSize: Math.min(14 + n.degree * 4, 52),
          itemStyle: {
            color: graphTypeColor(n.entity_type),
            borderColor: anchors.has(n.name) ? '#67c23a' : '#fff',
            borderWidth: anchors.has(n.name) ? 3 : 1,
          },
          label: { show: showLabels || n.degree >= 3, fontSize: 10 },
        })),
        links: data.edges.map((e) => ({
          ...e,
          lineStyle: {
            color: '#a3b1bf',
            width: 1.2,
            curveness: 0.15,
            opacity: 0.8,
          },
          label: {
            show: nodeCount <= 60,
            fontSize: 9,
            formatter: (p: unknown) => (p as { data: GraphEdge }).data.relation,
            color: '#606266',
          },
        })),
        force: {
          repulsion: Math.max(80, 3200 / Math.sqrt(Math.max(nodeCount, 1))),
          edgeLength: [40, 120],
          gravity: 0.08,
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 3 },
        },
      },
    ],
  }
  chart.setOption(option, true)
}

async function loadGraphOverview(): Promise<void> {
  graphLoading.value = true
  try {
    const data = await client.get<GraphData>('/admin/graph/overview?limit=200')
    graphData.value = data
    await nextTick()
    renderGraph(data)
  } catch (e) {
    console.error('Failed to load graph', e)
    ElMessage.error('知识图谱加载失败')
  } finally {
    graphLoading.value = false
  }
}

async function searchGraph(): Promise<void> {
  const q = graphSearchQuery.value.trim()
  if (!q) return
  graphLoading.value = true
  try {
    const data = await client.get<GraphData>(
      `/admin/graph/search?q=${encodeURIComponent(q)}`,
    )
    if (!data.nodes.length) {
      ElMessage.warning(`未找到与「${q}」相关的实体`)
      return
    }
    graphData.value = data
    await nextTick()
    renderGraph(data)
  } catch (e) {
    console.error('Graph search failed', e)
    ElMessage.error('图谱搜索失败')
  } finally {
    graphLoading.value = false
  }
}

async function resetGraphView(): Promise<void> {
  graphSearchQuery.value = ''
  await loadGraphOverview()
}

async function rebuildGraph(): Promise<void> {
  try {
    await ElMessageBox.confirm(
      '将基于当前知识库全量重建图谱（AI 抽取实体与关系），耗时约 1–5 分钟，期间可关闭页面。',
      '重建知识图谱',
      { type: 'warning' },
    )
  } catch {
    return
  }
  try {
    await client.post('/admin/graph/rebuild', {})
    graphRebuilding.value = true
    ElMessage.info('重建任务已启动，正在后台执行…')
    pollGraphStatus()
  } catch (e: unknown) {
    const err = e as Error
    ElMessage.error(err.message || '重建启动失败')
  }
}

function pollGraphStatus(): void {
  stopGraphPolling()
  graphStatusTimer = window.setInterval(async () => {
    try {
      const status = await client.get<{ state: string; result?: { entities: number; relations: number }; message?: string }>(
        '/admin/graph/status',
      )
      if (status.state === 'done') {
        stopGraphPolling()
        graphRebuilding.value = false
        ElMessage.success(
          `图谱重建完成：${status.result?.entities ?? 0} 实体 / ${status.result?.relations ?? 0} 关系`,
        )
        await loadGraphOverview()
      } else if (status.state === 'error') {
        stopGraphPolling()
        graphRebuilding.value = false
        ElMessage.error(`重建失败：${status.message ?? '未知错误'}`)
      }
    } catch {
      stopGraphPolling()
      graphRebuilding.value = false
    }
  }, 2500)
}

function stopGraphPolling(): void {
  if (graphStatusTimer !== null) {
    clearInterval(graphStatusTimer)
    graphStatusTimer = null
  }
}

onBeforeUnmount(() => {
  stopGraphPolling()
  window.removeEventListener('resize', handleGraphResize)
  graphChart?.dispose()
  graphChart = null
})

// ---------------------------------------------------------------------------
// Tab 切换
// ---------------------------------------------------------------------------
async function onTabChange(tab: string | number): Promise<void> {
  const t = String(tab)
  if (t === 'dashboard' && !stats.value) await loadStats()
  if (t === 'knowledge') await loadDocs()
  if (t === 'users') await loadUsers()
  if (t === 'exams') {
    await Promise.all([loadAllExams(), users.value.length ? Promise.resolve() : loadUsers()])
  }
  if (t === 'audit') await loadAuditLogs()
  if (t === 'graph') await loadGraphOverview()
}

function handleLogout(): void {
  authStore.logout()
  router.push('/login')
}

onMounted(async () => {
  await loadStats()
})
</script>

<template>
  <el-container class="admin-layout">
    <el-header class="admin-header">
      <div class="header-left">
        <span class="brand">工安卫士 · 管理端</span>
      </div>
      <div class="header-right">
        <span class="user-info">
          {{ authStore.user?.real_name || authStore.user?.username }}
          ({{ roleLabelMap[authStore.user?.role ?? ''] ?? authStore.user?.role }})
        </span>
        <el-button size="small" @click="handleLogout">退出登录</el-button>
      </div>
    </el-header>

    <el-main class="admin-main">
      <el-tabs v-model="activeTab" @tab-change="onTabChange">
        <!-- ======= AI 问答（管理端全库视图） ======= -->
        <el-tab-pane label="AI 问答" name="qa">
          <div class="qa-tab-hint">
            管理端问答视图：全库知识检索（含内部资料），可查看每条引用的召回详情。
          </div>
          <AdminQaPanel :admin-user-id="authStore.user?.id ?? 1" />
        </el-tab-pane>

        <!-- ======= FAQ 管理（永久缓存层） ======= -->
        <el-tab-pane label="FAQ 管理" name="faq" lazy>
          <FaqManagePanel />
        </el-tab-pane>

        <!-- ======= 仪表盘 ======= -->
        <el-tab-pane label="数据概览" name="dashboard">
          <div v-if="statsLoading" class="loading-hint">加载中…</div>
          <div v-else-if="stats" class="stat-grid">
            <el-card shadow="hover" class="stat-card">
              <el-statistic title="用户总数" :value="stats.total_users" />
            </el-card>
            <el-card shadow="hover" class="stat-card">
              <el-statistic title="知识文档" :value="stats.total_docs" />
            </el-card>
            <el-card shadow="hover" class="stat-card">
              <el-statistic title="题库总量" :value="stats.total_questions" />
            </el-card>
            <el-card shadow="hover" class="stat-card">
              <el-statistic title="考试场次" :value="stats.total_exams" />
            </el-card>
            <el-card shadow="hover" class="stat-card">
              <el-statistic
                title="平均分"
                :value="stats.avg_score"
                :precision="1"
                suffix="分"
              />
            </el-card>
          </div>
          <el-empty v-else description="暂无数据" />
        </el-tab-pane>

        <!-- ======= 知识库 ======= -->
        <el-tab-pane label="知识库管理" name="knowledge">
          <!-- 1) 知识库搜索 -->
          <el-card class="search-card" shadow="never">
            <template #header>
              <div class="card-header">
                <span>知识库全文检索（Dense + Sparse Hybrid）</span>
                <el-tag type="success" effect="plain">后端 /admin/search</el-tag>
              </div>
            </template>

            <div class="search-row">
              <el-input
                v-model="searchQuery"
                placeholder="输入自然语言查询，例如：动火作业的审批流程"
                clearable
                @keyup.enter="handleSearch"
                style="flex: 1"
              >
                <template #append>
                  <el-button type="primary" :loading="searchLoading" @click="handleSearch">
                    搜索
                  </el-button>
                </template>
              </el-input>
            </div>

            <div v-if="searchResults" class="search-results">
              <div class="results-meta">
                共 {{ searchResults.total }} 条匹配 · 查询「{{ searchResults.query }}」
              </div>
              <el-table :data="searchResults.hits" stripe size="small" max-height="400">
                <el-table-column label="相似度" width="100">
                  <template #default="{ row }">
                    <el-tag size="small" :type="row.score > 0.7 ? 'success' : row.score > 0.5 ? 'warning' : 'info'">
                      {{ row.score.toFixed(3) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="doc_type" label="类型" width="100" />
                <el-table-column label="片段预览" min-width="400">
                  <template #default="{ row }">
                    <span class="chunk-text">{{ row.text }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="位置" width="140">
                  <template #default="{ row }">
                    <span class="mono">doc={{ row.doc_id }} idx={{ row.chunk_index }}</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <el-empty v-else-if="!searchLoading" description="输入关键词开始搜索" />
          </el-card>

          <!-- 2) 上传 -->
          <el-card class="upload-card" shadow="never">
            <template #header>
              <div class="card-header">
                <span>上传文档</span>
                <el-tag type="info" effect="plain">支持 .txt / .md / .pdf / .docx</el-tag>
              </div>
            </template>

            <div class="upload-form-row">
              <el-upload
                :auto-upload="false"
                :show-file-list="true"
                :limit="1"
                drag
                :on-change="onUploadFileChange"
                :on-remove="onUploadRemove"
              >
                <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                <div class="el-upload__text">拖拽文件到此处，或 <em>点击选择文件</em></div>
              </el-upload>

              <div class="upload-meta">
                <el-form :model="uploadForm" label-width="80px">
                  <el-form-item label="文档类型">
                    <el-select v-model="uploadForm.doc_type" style="width: 200px">
                      <el-option
                        v-for="opt in docTypeOptions"
                        :key="opt.value"
                        :label="opt.label"
                        :value="opt.value"
                      />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="标题">
                    <el-input v-model="uploadForm.title" placeholder="留空则使用文件名" />
                  </el-form-item>
                  <el-form-item label="版本">
                    <el-input v-model="uploadForm.version" placeholder="v1.0" style="width: 200px" />
                  </el-form-item>
                  <el-form-item>
                    <el-button
                      type="primary"
                      :loading="uploading"
                      @click="handleUpload"
                    >
                      {{ uploading ? '处理中…' : '开始上传并索引' }}
                    </el-button>
                  </el-form-item>
                </el-form>

                <div v-if="uploadProgress" class="progress-area">
                  <el-descriptions :column="1" border size="small">
                    <el-descriptions-item label="进度">
                      <el-progress
                        :percentage="Math.round(uploadProgress.progress)"
                        :status="uploadProgress.error ? 'exception' : undefined"
                      />
                    </el-descriptions-item>
                    <el-descriptions-item v-if="uploadProgress.chunks_count > 0" label="已生成片段">
                      {{ uploadProgress.chunks_count }}
                    </el-descriptions-item>
                    <el-descriptions-item v-if="uploadProgress.error" label="错误信息">
                      <span class="text-red-500">{{ uploadProgress.error }}</span>
                    </el-descriptions-item>
                  </el-descriptions>
                </div>
              </div>
            </div>
          </el-card>

          <!-- 3) 文档列表 -->
          <el-card class="docs-list-card" shadow="never">
            <template #header>
              <div class="card-header">
                <span>文档列表（{{ docs.length }}）</span>
                <el-button size="small" :loading="docsLoading" @click="loadDocs">
                  刷新
                </el-button>
              </div>
            </template>

            <el-table :data="docs" v-loading="docsLoading" stripe>
              <el-table-column prop="id" label="ID" width="80" />
              <el-table-column prop="title" label="标题" />
              <el-table-column prop="doc_type" label="类型" width="120" />
              <el-table-column prop="version" label="版本" width="100" />
              <el-table-column label="状态" width="120">
                <template #default="{ row }">
                  <el-tag :type="statusTag(row.status).type as any">
                    {{ statusTag(row.status).label }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="创建时间" width="200" />
              <el-table-column label="操作" width="180" fixed="right">
                <template #default="{ row }">
                  <el-button
                    type="primary"
                    size="small"
                    link
                    @click="previewChunks(row.id)"
                  >
                    预览片段
                  </el-button>
                  <el-button
                    type="danger"
                    size="small"
                    link
                    :disabled="row.status === 'archived'"
                    @click="deleteDoc(row.id)"
                  >
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-tab-pane>

        <!-- ======= 知识图谱 ======= -->
        <el-tab-pane label="知识图谱" name="graph">
          <el-card shadow="never" class="graph-card">
            <template #header>
              <div class="card-header">
                <span>GraphRAG 知识图谱</span>
                <div class="graph-actions">
                  <el-input
                    v-model="graphSearchQuery"
                    placeholder="搜索实体，如：动火 / 有限空间 / 安全带"
                    size="small"
                    clearable
                    style="width: 260px"
                    @keyup.enter="searchGraph"
                  />
                  <el-button size="small" type="primary" :loading="graphLoading" @click="searchGraph">
                    搜索
                  </el-button>
                  <el-button size="small" @click="resetGraphView">全图</el-button>
                  <el-button
                    size="small"
                    type="warning"
                    :loading="graphRebuilding"
                    @click="rebuildGraph"
                  >
                    重建图谱
                  </el-button>
                </div>
              </div>
            </template>

            <!-- 统计条 -->
            <div v-if="graphData" class="graph-stats">
              <el-tag effect="plain">实体 {{ graphData.stats.entities }}</el-tag>
              <el-tag effect="plain" type="success">关系 {{ graphData.stats.relations }}</el-tag>
              <el-tag v-if="graphData.stats.communities" effect="plain" type="warning">
                社区 {{ graphData.stats.communities }}
              </el-tag>
              <span class="graph-legend">
                <span
                  v-for="item in graphTypeLegend()"
                  :key="item.type"
                  class="legend-chip"
                >
                  <i :style="{ background: item.color }" />{{ item.type }}
                </span>
              </span>
            </div>

            <!-- 力导向图 -->
            <div v-loading="graphLoading" class="graph-canvas-wrap">
              <div v-show="graphData && graphData.nodes.length" ref="graphDom" class="graph-canvas" />
              <el-empty
                v-if="graphData && !graphData.nodes.length && !graphLoading"
                description="图谱暂无数据：请先在知识库上传文档，然后点击「重建图谱」"
              />
            </div>
            <p class="graph-tip">
              拖拽节点可调整布局，滚轮缩放，悬浮查看实体/关系详情；搜索时绿色高亮为匹配实体。
            </p>
          </el-card>
        </el-tab-pane>

        <!-- ======= 用户 ======= -->
        <el-tab-pane label="用户管理" name="users">
          <el-card shadow="never">
            <template #header>
              <div class="card-header">
                <span>用户列表（{{ users.length }}）</span>
                <el-button type="primary" size="small" @click="openAddUserDialog">
                  + 新增用户
                </el-button>
              </div>
            </template>

            <el-table :data="users" v-loading="usersLoading" stripe>
              <el-table-column prop="id" label="ID" width="80" />
              <el-table-column prop="username" label="用户名" width="140" />
              <el-table-column prop="real_name" label="姓名" width="120" />
              <el-table-column prop="position" label="岗位" width="120" />
              <el-table-column label="角色" width="140">
                <template #default="{ row }">
                  <el-tag :type="row.role === 'admin' ? 'danger' : row.role === 'supervisor' ? 'warning' : 'info'">
                    {{ roleLabelMap[row.role] ?? row.role }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="创建时间" width="200" />
              <el-table-column label="操作" width="100" fixed="right">
                <template #default="{ row }">
                  <el-button
                    type="danger"
                    size="small"
                    link
                    :disabled="row.id === authStore.user?.id"
                    @click="deleteUser(row)"
                  >
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-dialog v-model="userDialogVisible" title="新增用户" width="480px">
            <el-form ref="userFormRef" :model="userForm" label-width="80px">
              <el-form-item
                label="用户名"
                prop="username"
                :rules="[{ required: true, message: '请输入用户名', trigger: 'blur' }]"
              >
                <el-input v-model="userForm.username" placeholder="2-32 字符" />
              </el-form-item>
              <el-form-item
                label="密码"
                prop="password"
                :rules="[{ required: true, message: '请输入密码（≥6位）', trigger: 'blur', min: 6 }]"
              >
                <el-input v-model="userForm.password" type="password" show-password />
              </el-form-item>
              <el-form-item label="姓名">
                <el-input v-model="userForm.real_name" />
              </el-form-item>
              <el-form-item label="岗位">
                <el-select v-model="userForm.position" style="width: 100%">
                  <el-option
                    v-for="p in positionOptions"
                    :key="p"
                    :label="p"
                    :value="p"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="角色">
                <el-select v-model="userForm.role" style="width: 100%">
                  <el-option label="普通员工" value="worker" />
                  <el-option label="安全管理员" value="admin" />
                </el-select>
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="userDialogVisible = false">取消</el-button>
              <el-button type="primary" @click="handleAddUser">确定</el-button>
            </template>
          </el-dialog>
        </el-tab-pane>

        <!-- ======= 考试 ======= -->
        <el-tab-pane label="考试管理" name="exams">
          <el-card shadow="never" class="exam-gen-card">
            <template #header>
              <div class="card-header">
                <span>智能组卷（AI 出题）</span>
              </div>
            </template>

            <el-form label-width="120px" class="exam-gen-form">
              <el-row :gutter="20">
                <el-col :span="8">
                  <el-form-item label="参考用户">
                    <el-select v-model="genForm.target_user_id" placeholder="选择参加考试的用户" filterable>
                      <el-option
                        v-for="u in users"
                        :key="u.id"
                        :value="u.id"
                        :label="`${u.real_name || u.username}（${u.position}）`"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="岗位">
                    <el-select v-model="genForm.position">
                      <el-option v-for="p in EXAM_POSITIONS" :key="p" :value="p" :label="p" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="快捷预设">
                    <el-select placeholder="选择预设组合" @change="(v: string) => applyPreset(examPresets[Number(v)])">
                      <el-option
                        v-for="(p, i) in examPresets"
                        :key="p.label"
                        :value="String(i)"
                        :label="p.label"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="20">
                <el-col :span="6">
                  <el-form-item label="单选题数">
                    <el-input-number v-model="genForm.count_single" :min="0" :max="50" />
                  </el-form-item>
                </el-col>
                <el-col :span="6">
                  <el-form-item label="多选题数">
                    <el-input-number v-model="genForm.count_multiple" :min="0" :max="50" />
                  </el-form-item>
                </el-col>
                <el-col :span="6">
                  <el-form-item label="判断题数">
                    <el-input-number v-model="genForm.count_judge" :min="0" :max="50" />
                  </el-form-item>
                </el-col>
                <el-col :span="6">
                  <el-form-item label="简答题数">
                    <el-input-number v-model="genForm.count_short_answer" :min="0" :max="50" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-form-item label-width="120px">
                <el-button type="primary" :loading="generating" @click="generateExam">
                  生成试卷（共 {{ genTotal() }} 题）
                </el-button>
              </el-form-item>
            </el-form>
          </el-card>

          <el-card shadow="never">
            <template #header>
              <div class="card-header">
                <span>考试列表（管理员视角）</span>
                <el-button size="small" :loading="examsLoading" @click="loadAllExams">
                  刷新
                </el-button>
              </div>
            </template>

            <el-table :data="allExams" v-loading="examsLoading" stripe>
              <el-table-column prop="id" label="ID" width="80" />
              <el-table-column prop="position" label="岗位" width="120" />
              <el-table-column label="状态" width="120">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'graded' ? 'success' : row.status === 'submitted' ? 'warning' : 'info'">
                    {{ row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="total_score" label="总分" width="100">
                <template #default="{ row }">
                  {{ row.total_score ?? '—' }}
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="创建时间" width="200" />
              <el-table-column prop="submitted_at" label="提交时间" width="200">
                <template #default="{ row }">
                  {{ row.submitted_at ?? '—' }}
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-tab-pane>

        <!-- ======= 题库 ======= -->
        <el-tab-pane label="题库管理" name="questions">
          <el-card shadow="never">
            <el-empty
              description="题库管理功能待扩展（需要后端新增专用 CRUD API）"
            >
              <template #default>
                <p class="tip-text">
                  当前题库由考试生成工作流自动创建。后续版本可在此实现：
                </p>
                <ul class="tip-list">
                  <li>题目手动录入与编辑</li>
                  <li>按岗位 / 知识点筛选与导入</li>
                  <li>题目质量评估与版本管理</li>
                </ul>
              </template>
            </el-empty>
          </el-card>
        </el-tab-pane>

        <!-- ======= 审计日志 ======= -->
        <el-tab-pane label="审计日志" name="audit">
          <el-card shadow="never">
            <template #header>
              <div class="card-header">
                <span>审计追踪（{{ auditTotal }} 条）</span>
                <el-button size="small" :loading="auditLogsLoading" @click="loadAuditLogs">
                  刷新
                </el-button>
              </div>
            </template>

            <div class="audit-filter-bar">
              <el-input
                v-model="auditFilterAction"
                placeholder="动作（如 auth.login）"
                size="small"
                clearable
                style="width: 200px"
                @clear="loadAuditLogs"
              />
              <el-input-number
                v-model="auditFilterUserId"
                :min="1"
                :controls="false"
                placeholder="用户 ID"
                size="small"
                style="width: 120px"
              />
              <el-button size="small" type="primary" @click="auditOffset = 0; loadAuditLogs()">
                查询
              </el-button>
              <el-button size="small" @click="resetAuditFilters">重置</el-button>
            </div>

            <el-table :data="auditLogs" v-loading="auditLogsLoading" stripe size="small" max-height="600">
              <el-table-column prop="id" label="#" width="80" />
              <el-table-column prop="username" label="用户" width="120" />
              <el-table-column prop="action" label="操作" width="160">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain">{{ row.action }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="resource_type" label="资源类型" width="100">
                <template #default="{ row }">{{ row.resource_type ?? '—' }}</template>
              </el-table-column>
              <el-table-column prop="resource_id" label="资源 ID" width="100">
                <template #default="{ row }">{{ row.resource_id ?? '—' }}</template>
              </el-table-column>
              <el-table-column label="详情" min-width="200">
                <template #default="{ row }">
                  <span class="mono">
                    {{ row.detail ? JSON.stringify(row.detail).slice(0, 120) : '—' }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="ip_address" label="IP" width="130">
                <template #default="{ row }">{{ row.ip_address ?? '—' }}</template>
              </el-table-column>
              <el-table-column label="状态" width="80">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
                    {{ row.status === 'success' ? '成功' : '失败' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="时间" width="200" />
            </el-table>
          </el-card>
        </el-tab-pane>
      </el-tabs>

      <!-- Chunk 预览对话框 -->
      <el-dialog
        v-model="chunkDialogVisible"
        :title="`文档片段预览 ${chunksData ? `（${chunksData.total_chunks} 个）` : ''}`"
        width="800px"
      >
        <div v-if="chunkLoading" class="loading-hint">加载中…</div>
        <div v-else-if="chunksData">
          <el-table :data="chunksData.chunks" stripe size="small" max-height="500">
            <el-table-column prop="chunk_index" label="#" width="60" />
            <el-table-column prop="chunk_id" label="Chunk ID" width="130" />
            <el-table-column label="文本内容">
              <template #default="{ row }">
                <pre class="chunk-pre">{{ row.text }}</pre>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <el-empty v-else description="无可预览片段" />
      </el-dialog>
    </el-main>
  </el-container>
</template>

<script lang="ts">
import { UploadFilled } from '@element-plus/icons-vue'
export default { components: { UploadFilled } }
</script>

<style scoped>
.admin-layout {
  min-height: 100vh;
}

.admin-header {
  background: #1a2a3a;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.header-left .brand {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-info {
  font-size: 14px;
  opacity: 0.9;
}

.admin-main {
  background: #f5f7fa;
  padding: 20px 32px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.audit-filter-bar {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.stat-card {
  transition: transform 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
}

.search-card,
.upload-card,
.docs-list-card {
  margin-bottom: 16px;
}

.search-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.search-results {
  margin-top: 8px;
}

.results-meta {
  color: #909399;
  font-size: 13px;
  margin-bottom: 8px;
}

.chunk-text {
  font-size: 13px;
  color: #303133;
  line-height: 1.6;
}

.mono {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  color: #909399;
}

.chunk-pre {
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  font-family: inherit;
  max-height: 200px;
  overflow: auto;
}

.upload-form-row {
  display: grid;
  grid-template-columns: minmax(260px, 360px) 1fr;
  gap: 24px;
}

.progress-area {
  margin-top: 16px;
}

.loading-hint {
  text-align: center;
  padding: 40px;
  color: #909399;
}

.qa-tab-hint {
  color: #909399;
  font-size: 13px;
  margin-bottom: 12px;
}

.text-red-500 {
  color: #f56c6c;
}

.tip-text {
  color: #606266;
  margin-bottom: 12px;
}

.tip-list {
  text-align: left;
  color: #909399;
  padding-left: 20px;
  line-height: 1.8;
}

.graph-card {
  margin-bottom: 16px;
}

.graph-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.graph-stats {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.graph-legend {
  display: inline-flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-left: 12px;
}

.legend-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #606266;
}

.legend-chip i {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.graph-canvas-wrap {
  min-height: 560px;
}

.graph-canvas {
  width: 100%;
  height: 560px;
}

.graph-tip {
  font-size: 12px;
  color: #909399;
  margin: 10px 0 0;
}
</style>
