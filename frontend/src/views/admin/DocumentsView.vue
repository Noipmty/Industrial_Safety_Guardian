<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useAdminStore } from '@/stores/admin'
import AppSkeleton from '@/components/common/AppSkeleton.vue'
import PermTag from '@/components/common/PermTag.vue'
import type { AccessLevel } from '@/types'

const admin = useAdminStore()
const loading = ref(true)
const keyword = ref('')
const accessFilter = ref<AccessLevel | ''>('')

const STATUS: Record<string, { label: string; type: 'success' | 'warning' | 'danger' }> = {
  indexed: { label: '已入库', type: 'success' },
  indexing: { label: '解析中', type: 'warning' },
  failed: { label: '失败', type: 'danger' },
}

const list = computed(() =>
  admin.documents.filter(
    (d) =>
      (!keyword.value || d.name.includes(keyword.value)) &&
      (!accessFilter.value || d.access === accessFilter.value),
  ),
)

const uploadVisible = ref(false)
const uploadForm = ref({ name: '', docType: '规程标准', access: 'internal' as AccessLevel })
const totalChunks = computed(() => admin.documents.reduce((s, d) => s + d.chunks, 0))
const stats = computed(() => [
  { label: '文档总数', value: String(admin.documents.length), warn: false },
  { label: 'Chunks 已向量化', value: String(totalChunks.value), warn: false },
  { label: '解析中', value: String(admin.documents.filter((d) => d.status === 'indexing').length), warn: false },
  { label: '解析失败', value: String(admin.documents.filter((d) => d.status === 'failed').length), warn: true },
])

function confirmUpload(): void {
  if (!uploadForm.value.name.trim()) {
    ElMessage.warning('请填写文档名称')
    return
  }
  admin.documents.unshift({
    id: `d-${Date.now()}`,
    name: uploadForm.value.name,
    docType: uploadForm.value.docType,
    access: uploadForm.value.access,
    chunks: 0,
    status: 'indexing',
    updatedAt: new Date().toISOString().slice(0, 10),
    sizeKb: 128,
  })
  uploadVisible.value = false
  ElMessage.success('已提交解析任务：切块 → BGE-M3 向量化 → 入库 Milvus（演示）')
  uploadForm.value = { name: '', docType: '规程标准', access: 'internal' }
}

onMounted(async () => {
  try {
    await admin.loadDocuments()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-4">
    <!-- 工具栏 -->
    <div class="flex flex-wrap items-center gap-2">
      <el-input
        v-model="keyword"
        placeholder="搜索文档名称"
        clearable
        class="w-56!"
        prefix-icon="Search"
      />
      <el-select v-model="accessFilter" placeholder="可见级别" clearable class="w-36!">
        <el-option label="public 公开" value="public" />
        <el-option label="internal 内部" value="internal" />
        <el-option label="secret 机密" value="secret" />
      </el-select>
      <span class="text-xs text-graphite/45 flex-1 hidden sm:block">
        共 {{ admin.documents.length }} 篇 · {{ totalChunks }} chunks 已向量化
      </span>
      <el-button type="primary" @click="uploadVisible = true">
        <el-icon class="mr-1"><Upload /></el-icon>上传文档
      </el-button>
    </div>

    <!-- 统计面板 -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div v-for="s in stats" :key="s.label" class="card p-3.5">
        <p class="text-xs text-graphite/50">{{ s.label }}</p>
        <p class="text-xl font-bold tabular-nums mt-0.5" :class="s.warn ? 'text-red-500' : 'text-navy'">{{ s.value }}</p>
      </div>
    </div>

    <AppSkeleton v-if="loading" type="table" :rows="6" />
    <div v-else class="card p-2">
      <el-table :data="list" stripe>
        <el-table-column prop="name" label="文档名称" min-width="240" show-overflow-tooltip />
        <el-table-column prop="docType" label="类型" width="100" />
        <el-table-column label="可见级别" width="130">
          <template #default="{ row }"><PermTag :access="row.access" /></template>
        </el-table-column>
        <el-table-column prop="chunks" label="Chunks" width="90" align="center" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="STATUS[row.status as keyof typeof STATUS]?.type" size="small" round>
              {{ STATUS[row.status as keyof typeof STATUS]?.label ?? row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="90" align="right">
          <template #default="{ row }">
            <span class="font-mono text-xs">{{ (row.sizeKb / 1024).toFixed(1) }}MB</span>
          </template>
        </el-table-column>
        <el-table-column prop="updatedAt" label="更新时间" width="110" />
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="ElMessage.info('演示环境：查看切块预览')">切块预览</el-button>
            <el-button
              link
              size="small"
              :type="row.status === 'failed' ? 'danger' : 'default'"
              @click="ElMessage[row.status === 'failed' ? 'error' : 'info'](row.status === 'failed' ? '解析失败：PDF 页面损坏，请重新上传' : '演示环境：重新索引')"
            >
              {{ row.status === 'failed' ? '重试' : '重建索引' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 上传弹窗 -->
    <el-dialog v-model="uploadVisible" title="上传文档" width="440px">
      <div class="space-y-4">
        <el-alert
          title="解析流水线：PyMuPDF 切块 → BGE-M3 向量化 → Milvus 入库 → 图谱抽取"
          type="info"
          :closable="false"
          class="rounded-lg!"
        />
        <el-form label-width="80px">
          <el-form-item label="文档名称">
            <el-input v-model="uploadForm.name" placeholder="如：钻井井控技术规程 2026 修订版" />
          </el-form-item>
          <el-form-item label="类型">
            <el-select v-model="uploadForm.docType" class="w-full">
              <el-option v-for="t in ['规程标准', '操作手册', '应急预案', '管理制度', '配置标准']" :key="t" :label="t" :value="t" />
            </el-select>
          </el-form-item>
          <el-form-item label="可见级别">
            <el-radio-group v-model="uploadForm.access">
              <el-radio-button value="public">public</el-radio-button>
              <el-radio-button value="internal">internal</el-radio-button>
              <el-radio-button value="secret">secret</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmUpload">提交解析</el-button>
      </template>
    </el-dialog>
  </div>
</template>
