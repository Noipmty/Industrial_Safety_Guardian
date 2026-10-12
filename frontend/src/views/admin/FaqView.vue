<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useAdminStore } from '@/stores/admin'
import AppSkeleton from '@/components/common/AppSkeleton.vue'
import type { FaqItem } from '@/types'

const admin = useAdminStore()
const loading = ref(true)
const stats = computed(() => [
  { label: 'FAQ 总数', value: String(admin.faqs.length), warn: false },
  { label: '已启用', value: String(admin.faqs.filter((f) => f.enabled).length), warn: false },
  { label: '已停用', value: String(admin.faqs.filter((f) => !f.enabled).length), warn: true },
  { label: '累计命中', value: String(admin.faqs.reduce((s, f) => s + f.hitCount, 0)), warn: false },
])

const dialogVisible = ref(false)
const editing = ref<FaqItem | null>(null)
const form = ref({ question: '', answer: '', tags: '' })

function openAdd(): void {
  editing.value = null
  form.value = { question: '', answer: '', tags: '' }
  dialogVisible.value = true
}

function openEdit(row: FaqItem): void {
  editing.value = row
  form.value = { question: row.question, answer: row.answer, tags: row.tags.join('、') }
  dialogVisible.value = true
}

function save(): void {
  if (!form.value.question.trim() || !form.value.answer.trim()) {
    ElMessage.warning('问题和答案不能为空')
    return
  }
  const tags = form.value.tags.split(/[,，、\s]+/).filter(Boolean)
  if (editing.value) {
    Object.assign(editing.value, { question: form.value.question, answer: form.value.answer, tags })
    ElMessage.success('FAQ 已更新')
  } else {
    admin.faqs.unshift({
      id: `f-${Date.now()}`,
      question: form.value.question,
      answer: form.value.answer,
      tags,
      hitCount: 0,
      enabled: true,
    })
    ElMessage.success('FAQ 已添加，将参与 L3 缓存匹配')
  }
  dialogVisible.value = false
}

function toggle(row: FaqItem): void {
  ElMessage.success(row.enabled ? '已启用该 FAQ' : '已停用该 FAQ（不再参与命中）')
}

onMounted(async () => {
  try {
    await admin.loadFaqs()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center gap-2">
      <span class="text-xs text-graphite/45 flex-1">
        FAQ 是三级缓存（L3）：问题改写归一后精确/相似匹配，命中即跳过完整 RAG
      </span>
      <el-button type="primary" @click="openAdd"><el-icon class="mr-1"><Plus /></el-icon>新增 FAQ</el-button>
    </div>

    <!-- 统计面板 -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div v-for="s in stats" :key="s.label" class="card p-3.5">
        <p class="text-xs text-graphite/50">{{ s.label }}</p>
        <p class="text-xl font-bold tabular-nums mt-0.5" :class="s.warn ? 'text-safety' : 'text-navy'">{{ s.value }}</p>
      </div>
    </div>

    <AppSkeleton v-if="loading" type="table" :rows="5" />
    <div v-else class="card p-2">
      <el-table :data="admin.faqs" stripe>
        <el-table-column prop="question" label="问题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="answer" label="标准答案" min-width="240" show-overflow-tooltip />
        <el-table-column label="标签" width="140">
          <template #default="{ row }">
            <span v-for="t in row.tags" :key="t" class="chip bg-[#EAF1F8] text-navy border border-[#C9D9EA] mr-1">{{ t }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="hitCount" label="命中次数" width="100" align="center" sortable />
        <el-table-column label="启用" width="80">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" size="small" @change="toggle(row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑 FAQ' : '新增 FAQ'" width="480px">
      <el-form label-width="70px">
        <el-form-item label="问题">
          <el-input v-model="form.question" placeholder="如：发现溢流第一步做什么？" />
        </el-form-item>
        <el-form-item label="标准答案">
          <el-input v-model="form.answer" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="form.tags" placeholder="用顿号或逗号分隔，如：井控、溢流" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
