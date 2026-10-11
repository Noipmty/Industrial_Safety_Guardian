<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MagicStick } from '@element-plus/icons-vue'
import client from '@/api/client'

interface FaqItem {
  id: number
  question: string
  answer: string
  source: string
  hit_count: number
  enabled: boolean
  created_at: string
}

interface FaqCandidate {
  question: string
  answer: string
}

const items = ref<FaqItem[]>([])
const loading = ref(false)
const mining = ref(false)

const dialogVisible = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const form = ref({ question: '', answer: '' })

const mineDialogVisible = ref(false)
const candidates = ref<FaqCandidate[]>([])
const adopting = ref(-1)

async function load(): Promise<void> {
  loading.value = true
  try {
    items.value = await client.get<FaqItem[]>('/admin/faq')
  } catch {
    ElMessage.error('FAQ 加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  editingId.value = null
  form.value = { question: '', answer: '' }
  dialogVisible.value = true
}

function openEdit(item: FaqItem): void {
  editingId.value = item.id
  form.value = { question: item.question, answer: item.answer }
  dialogVisible.value = true
}

async function save(): Promise<void> {
  if (!form.value.question.trim() || !form.value.answer.trim()) {
    ElMessage.warning('问题和答案均不能为空')
    return
  }
  saving.value = true
  try {
    if (editingId.value === null) {
      await client.post('/admin/faq', form.value)
      ElMessage.success('FAQ 已创建')
    } else {
      await client.put(`/admin/faq/${editingId.value}`, form.value)
      ElMessage.success('FAQ 已更新')
    }
    dialogVisible.value = false
    await load()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(item: FaqItem): Promise<void> {
  try {
    await ElMessageBox.confirm(`确认删除该 FAQ？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await client.delete(`/admin/faq/${item.id}`)
    ElMessage.success('已删除')
    await load()
  } catch {
    ElMessage.error('删除失败')
  }
}

async function toggle(item: FaqItem): Promise<void> {
  try {
    await client.patch(`/admin/faq/${item.id}/toggle`, { enabled: !item.enabled })
    await load()
  } catch {
    ElMessage.error('操作失败')
  }
}

async function mine(): Promise<void> {
  mining.value = true
  try {
    candidates.value = await client.post<FaqCandidate[]>('/admin/faq/mine', {})
    if (candidates.value.length === 0) {
      ElMessage.info('近期会话中没有可挖掘的优质问答')
    } else {
      mineDialogVisible.value = true
    }
  } catch {
    ElMessage.error('挖掘失败，请稍后重试')
  } finally {
    mining.value = false
  }
}

async function adopt(candidate: FaqCandidate, index: number): Promise<void> {
  adopting.value = index
  try {
    await client.post('/admin/faq', candidate)
    ElMessage.success('已采纳入库')
    candidates.value.splice(index, 1)
    await load()
  } catch {
    ElMessage.error('入库失败（可能已存在相似问题）')
  } finally {
    adopting.value = -1
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="faq-toolbar">
      <el-button type="primary" @click="openCreate">新增 FAQ</el-button>
      <el-button :icon="MagicStick" :loading="mining" @click="mine">
        智能挖掘（从近期会话）
      </el-button>
      <span class="faq-hint">
        FAQ 命中后直接返回精校答案，跳过完整 RAG 检索，回答更快更稳定。
      </span>
    </div>

    <el-table :data="items" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="question" label="标准问题" min-width="220" show-overflow-tooltip />
      <el-table-column prop="answer" label="答案" min-width="280" show-overflow-tooltip />
      <el-table-column label="来源" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="row.source === 'mined' ? 'warning' : 'info'">
            {{ row.source === 'mined' ? '挖掘' : '手动' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="hit_count" label="命中" width="70" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-switch
            :model-value="row.enabled"
            @change="() => toggle(row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button size="small" text type="primary" @click="openEdit(row)">
            编辑
          </el-button>
          <el-button size="small" text type="danger" @click="remove(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId === null ? '新增 FAQ' : '编辑 FAQ'"
      width="560px"
    >
      <el-form label-position="top">
        <el-form-item label="标准问题">
          <el-input v-model="form.question" placeholder="通用化的标准问法" />
        </el-form-item>
        <el-form-item label="精校答案">
          <el-input
            v-model="form.answer"
            type="textarea"
            :rows="6"
            placeholder="准确、自包含的标准答案"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="mineDialogVisible" title="挖掘到的 FAQ 候选" width="640px">
      <div
        v-for="(c, i) in candidates"
        :key="i"
        class="faq-candidate"
      >
        <div class="faq-candidate__q">Q: {{ c.question }}</div>
        <div class="faq-candidate__a">A: {{ c.answer }}</div>
        <el-button
          size="small"
          type="primary"
          :loading="adopting === i"
          @click="adopt(c, i)"
        >
          采纳入库
        </el-button>
      </div>
      <el-empty
        v-if="candidates.length === 0"
        description="没有候选"
        :image-size="60"
      />
    </el-dialog>
  </div>
</template>

<style scoped>
.faq-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.faq-hint {
  color: #909399;
  font-size: 12px;
}

.faq-candidate {
  padding: 12px 14px;
  background: #f9fafc;
  border-radius: 6px;
  margin-bottom: 12px;
}

.faq-candidate__q {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 6px;
  color: #303133;
}

.faq-candidate__a {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  margin-bottom: 10px;
  white-space: pre-wrap;
}
</style>
