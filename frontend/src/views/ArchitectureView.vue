<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function onBack(): void {
  router.back()
}

const workflows = [
  {
    name: '安全问答工作流',
    icon: 'ChatDotRound',
    color: 'teal',
    nodes: ['查询理解', '缓存查找', 'FAQ 查找', '记忆检索', '工具规划', '并行执行', '质量门控', '结果融合'],
    desc: 'LangGraph 状态机编排，检索类确定性任务全部离开 LLM',
  },
  {
    name: '自动出卷工作流',
    icon: 'EditPen',
    color: 'orange',
    nodes: ['意图检测', '结构化生成', '质量校验'],
    desc: '按岗位 / 知识点 / 难度分布约束生成，校验失败自动重试',
  },
  {
    name: '智能批改工作流',
    icon: 'Finished',
    color: 'navy',
    nodes: ['客观题精确匹配', '主观题 RAG 增强评分'],
    desc: 'rubric 四维评分：准确性 / 完整性 / 条理性 / 规范性',
  },
]

const cacheLayers = [
  { name: 'L1 Redis 精确缓存', hit: 'Q&A 全文 · 命中 <5ms', rate: 21, color: '#DC2626' },
  { name: 'L2 语义缓存', hit: '向量相似度 ≥0.92 · 命中 ~80ms', rate: 40, color: '#14B8A6' },
  { name: 'L3 FAQ 高频库', hit: '问题改写归一匹配 · 命中 ~60ms', rate: 15, color: '#FF7A1A' },
  { name: 'L4 完整 RAG', hit: '混合检索 + 图谱 + 生成兜底', rate: 24, color: '#64748B' },
]

const guardLayers = [
  { step: '网关层', detail: 'JWT 校验 + 角色 / 岗位声明解析，匿名请求直接 401' },
  { step: '检索层', detail: 'Milvus expr 按 access ∈ {public, internal} 预过滤，secret 片段不进上下文' },
  { step: '生成层', detail: 'LLM 守卫校验：注入检测 + 引用白名单 + 空输出降级，杜绝越权内容' },
]

const stack = [
  'FastAPI', 'Vue 3', 'LangGraph', 'qwen-flash / qwen-plus', 'BGE-M3', 'Milvus',
  'Neo4j', 'Redis', 'MySQL', 'PostgreSQL / pgvector', 'Docker', 'Prometheus + Grafana', 'Langfuse',
]

</script>

<template>
  <div class="min-h-screen bg-mist pb-16">
    <!-- Hero -->
    <header class="navy-hero text-white">
      <div class="max-w-4xl mx-auto px-4 sm:px-6 py-10 sm:py-14 space-y-4">
        <button
          class="text-white/60 hover:text-white text-sm inline-flex items-center gap-1"
          @click="onBack"
        >
          <el-icon><Back /></el-icon>返回
        </button>
        <div class="flex items-center gap-3">
          <div class="w-12 h-12 rounded-2xl bg-white/10 border border-white/15 flex items-center justify-center shrink-0">
            <svg viewBox="0 0 24 24" class="w-7 h-7" fill="none" aria-hidden="true">
              <path d="M12 3L5 21M12 3l7 18M8.2 13.5h7.6M9.6 9.5h4.8" stroke="#FF7A1A" stroke-width="1.8" stroke-linecap="round" />
            </svg>
          </div>
          <div>
            <h1 class="text-2xl sm:text-3xl font-bold">系统架构演示</h1>
            <p class="text-white/55 text-sm mt-1">工安卫士 · 石油井场安全培训系统</p>
          </div>
        </div>
        <p class="text-white/70 text-sm sm:text-base leading-relaxed max-w-2xl">
          单 Agent 意图识别 + 多工作流分发：LLM 只负责<b class="text-white">意图识别</b>和<b class="text-white">结果生成</b>，
          检索、出题、批改等确定性任务交给专用工作流，让钻井现场工人在权限边界内快速拿到可信的安全知识答案。
        </p>
      </div>
    </header>

    <main class="max-w-4xl mx-auto px-4 sm:px-6 -mt-6 space-y-5 relative z-10">
      <!-- 单 Agent 多工作流 -->
      <section class="card p-5 sm:p-6 space-y-4">
        <h2 class="section-title"><el-icon><Share /></el-icon>单 Agent + 多工作流分发</h2>
        <div class="flex items-center justify-center">
          <div class="px-5 py-3 rounded-2xl navy-hero text-white text-center shadow-card">
            <p class="text-sm font-bold">主 Agent</p>
            <p class="text-[11px] text-white/60">意图识别 · 路由分发</p>
          </div>
        </div>
        <div class="hidden sm:flex justify-center text-gray-300 text-lg select-none" aria-hidden="true">↓ ↓ ↓</div>
        <div class="grid md:grid-cols-3 gap-3">
          <div
            v-for="w in workflows"
            :key="w.name"
            class="rounded-xl border p-4 space-y-3"
            :class="{
              'border-teal-200 bg-teal-50/50': w.color === 'teal',
              'border-orange-200 bg-safety-light/60': w.color === 'orange',
              'border-[#C9D9EA] bg-[#EAF1F8]/60': w.color === 'navy',
            }"
          >
            <p class="font-semibold text-navy text-sm flex items-center gap-1.5">
              <el-icon><component :is="w.icon" /></el-icon>{{ w.name }}
            </p>
            <div class="flex flex-wrap gap-1">
              <template v-for="(n, i) in w.nodes" :key="n">
                <span class="chip bg-white text-graphite border border-gray-200">{{ n }}</span>
                <span v-if="i < w.nodes.length - 1" class="text-gray-300 text-xs self-center" aria-hidden="true">→</span>
              </template>
            </div>
            <p class="text-[11px] text-graphite/55 leading-relaxed">{{ w.desc }}</p>
          </div>
        </div>
      </section>

      <!-- 四级缓存 -->
      <section class="card p-5 sm:p-6 space-y-4">
        <h2 class="section-title"><el-icon><Lightning /></el-icon>四级缓存 · 由近及远逐层命中</h2>
        <div class="space-y-2.5">
          <div v-for="l in cacheLayers" :key="l.name" class="flex items-center gap-3">
            <span class="w-28 sm:w-36 text-xs font-semibold text-graphite shrink-0">{{ l.name }}</span>
            <div class="flex-1 h-8 rounded-lg bg-mist overflow-hidden relative">
              <div
                class="h-full rounded-lg flex items-center px-3"
                :style="{ width: `${l.rate * 2}%`, background: `${l.color}1a`, borderRight: `3px solid ${l.color}` }"
              >
                <span class="text-xs font-bold" :style="{ color: l.color }">{{ l.rate }}%</span>
              </div>
            </div>
            <span class="hidden sm:block w-56 text-[11px] text-graphite/50 shrink-0">{{ l.hit }}</span>
          </div>
        </div>
        <p class="text-[11px] text-graphite/45 leading-relaxed">
          命中即短路：任一层命中直接返回并跳过后续步骤（演示环境 61.2% 请求不触达 LLM）。
        </p>
      </section>

      <!-- 混合检索 + 权限 -->
      <div class="grid md:grid-cols-2 gap-5">
        <section class="card p-5 sm:p-6 space-y-3">
          <h2 class="section-title"><el-icon><Search /></el-icon>混合检索</h2>
          <div class="space-y-2 text-xs">
            <div class="flex items-center gap-2">
              <span class="chip bg-teal-50 text-teal-700 border border-teal-200 w-24 justify-center">Dense 稠密</span>
              <span class="text-graphite/60">BGE-M3 向量 · 1024 维 · 余弦 Top-K</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="chip bg-safety-light text-safety-dark border border-orange-200 w-24 justify-center">Sparse 稀疏</span>
              <span class="text-graphite/60">BM25 / 稀疏向量 · 关键词精确召回</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="chip bg-[#EAF1F8] text-navy border border-[#C9D9EA] w-24 justify-center">RRF 融合</span>
              <span class="text-graphite/60">倒数排序融合 → 重排 → Top-5 引用</span>
            </div>
          </div>
          <div class="rounded-xl bg-mist p-3 text-[11px] text-graphite/60 leading-relaxed">
            <b class="text-navy">图谱增强：</b>关系类问题追加 graph_rag 工具，从 Neo4j 社区摘要中补充多跳关系
            （如 溢流—处置措施→软关井程序—使用设备→防喷器组）。
          </div>
        </section>

        <section class="card p-5 sm:p-6 space-y-3">
          <h2 class="section-title"><el-icon><Lock /></el-icon>权限三层闭环</h2>
          <div class="space-y-2">
            <div
              v-for="(g, i) in guardLayers"
              :key="g.step"
              class="flex gap-3"
            >
              <div class="flex flex-col items-center">
                <span class="w-6 h-6 rounded-full bg-safety text-white text-xs font-bold flex items-center justify-center">{{ i + 1 }}</span>
                <span v-if="i < guardLayers.length - 1" class="w-px flex-1 bg-orange-200 my-1" />
              </div>
              <div class="pb-2">
                <p class="text-sm font-semibold text-navy">{{ g.step }}</p>
                <p class="text-[11px] text-graphite/60 leading-relaxed mt-0.5">{{ g.detail }}</p>
              </div>
            </div>
          </div>
          <p class="text-[11px] text-graphite/45">三层层层收口：即使某层被绕过，下一层仍会拦截越权内容。</p>
        </section>
      </div>

      <!-- LLM 降级 + 技术栈 -->
      <div class="grid md:grid-cols-2 gap-5">
        <section class="card p-5 sm:p-6 space-y-3">
          <h2 class="section-title"><el-icon><Connection /></el-icon>LLM 三层降级</h2>
          <div class="flex items-center gap-2 flex-wrap">
            <span class="px-4 py-2.5 rounded-xl bg-teal-50 border border-teal-200 text-center">
              <p class="text-xs font-bold text-teal-700">qwen-flash</p>
              <p class="text-[10px] text-teal-600/70">主力 · 低成本高并发</p>
            </span>
            <span class="text-gray-300" aria-hidden="true">→</span>
            <span class="px-4 py-2.5 rounded-xl bg-[#EAF1F8] border border-[#C9D9EA] text-center">
              <p class="text-xs font-bold text-navy">qwen-plus</p>
              <p class="text-[10px] text-navy/60">超时 / 质量门控失败时升级</p>
            </span>
            <span class="text-gray-300" aria-hidden="true">→</span>
            <span class="px-4 py-2.5 rounded-xl bg-gray-50 border border-dashed border-gray-300 text-center">
              <p class="text-xs font-bold text-gray-500">mock 兜底</p>
              <p class="text-[10px] text-gray-400">全链路不可用 · 拒答话术</p>
            </span>
          </div>
          <p class="text-[11px] text-graphite/45 leading-relaxed">
            每次回答携带 route 标签，降级次数作为核心 KPI 在仪表盘暴露告警。
          </p>
        </section>

        <section class="card p-5 sm:p-6 space-y-3">
          <h2 class="section-title"><el-icon><Collection /></el-icon>技术栈</h2>
          <div class="flex flex-wrap gap-1.5">
            <span v-for="s in stack" :key="s" class="chip bg-mist text-graphite/70 border border-gray-200">{{ s }}</span>
          </div>
          <p class="text-[11px] text-graphite/45 leading-relaxed">
            可观测性：Prometheus 指标 + Grafana 面板 + Langfuse 全链路 Trace。
          </p>
        </section>
      </div>

      <div class="text-center pt-2">
        <router-link to="/login" class="btn-hero w-auto inline-flex items-center justify-center gap-2 px-8">
          <el-icon><User /></el-icon>返回登录，进入演示
        </router-link>
      </div>
    </main>
  </div>
</template>
