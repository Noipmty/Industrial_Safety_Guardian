<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Search, Document as DocIcon } from '@element-plus/icons-vue';
import { useAuthStore } from '@/stores/auth';
import apiClient from '@/api/client';
import type { DocQueryItem } from '@/api/types';

const router = useRouter();
const authStore = useAuthStore();

const docs = ref<DocQueryItem[]>([]);
const loading = ref(false);
const keyword = ref('');
const filterType = ref<string | null>(null);

const typeOptions = ref<Array<{ value: string; access_level: string }>>([]);

const detailVisible = ref(false);
const detailLoading = ref(false);
const detail = ref<DocQueryItem | null>(null);

async function loadDocs(): Promise<void> {
  loading.value = true;
  try {
    const params = new URLSearchParams();
    if (keyword.value.trim()) params.set('q', keyword.value.trim());
    if (filterType.value) params.set('doc_type', filterType.value);
    const qs = params.toString();
    docs.value = await apiClient.get<DocQueryItem[]>(
      `/documents${qs ? `?${qs}` : ''}`,
    );
  } catch {
    ElMessage.error('文档加载失败');
  } finally {
    loading.value = false;
  }
}

async function openDetail(doc: DocQueryItem): Promise<void> {
  detailVisible.value = true;
  detailLoading.value = true;
  detail.value = null;
  try {
    detail.value = await apiClient.get<DocQueryItem>(`/documents/${doc.id}`);
  } catch {
    ElMessage.error('文档详情加载失败');
    detailVisible.value = false;
  } finally {
    detailLoading.value = false;
  }
}

function accessTag(level: string): { type: 'info' | 'warning'; label: string } {
  return level === 'internal'
    ? { type: 'warning', label: '内部资料' }
    : { type: 'info', label: '全员公开' };
}

function handleLogout(): void {
  authStore.logout();
  router.push('/login');
}

onMounted(() => {
  void loadDocs();
  void apiClient
    .get<Array<{ value: string; access_level: string }>>('/documents/types')
    .then((t) => {
      typeOptions.value = t;
    })
    .catch(() => {
      /* 类型下拉加载失败不阻塞主列表 */
    });
});
</script>

<template>
  <div class="docs-layout">
    <aside class="docs-side">
      <h2 class="docs-side__title">工安卫士</h2>
      <nav class="docs-side__nav">
        <button class="side-link" @click="router.push('/chat')">
          AI 安全问答
        </button>
        <button class="side-link side-link--active">文档查询</button>
        <button class="side-link" @click="router.push('/exam')">考试中心</button>
        <button
          v-if="authStore.isAdmin"
          class="side-link"
          @click="router.push('/admin')"
        >
          管理后台
        </button>
      </nav>
      <div class="docs-side__footer">
        <span class="docs-side__user">
          {{ authStore.user?.real_name || authStore.user?.username || '未登录' }}
        </span>
        <el-button size="small" type="danger" plain @click="handleLogout">
          退出
        </el-button>
      </div>
    </aside>

    <div class="docs-main">
      <div class="docs-toolbar">
        <el-input
          v-model="keyword"
          placeholder="按标题搜索文档..."
          clearable
          class="docs-toolbar__search"
          @keyup.enter="loadDocs"
          @clear="loadDocs"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select
          v-model="filterType"
          placeholder="全部类型"
          clearable
          class="docs-toolbar__type"
          @change="loadDocs"
        >
          <el-option
            v-for="t in typeOptions"
            :key="t.value"
            :label="t.value"
            :value="t.value"
          />
        </el-select>
        <el-button type="primary" @click="loadDocs">查询</el-button>
      </div>

      <p class="docs-hint">
        按角色权限展示：普通员工可见公开资料（操作规程 / 应急处置 / 事故案例），
        主管及以上可查阅内部资料（法规 / 风险管控）。
      </p>

      <div v-loading="loading" class="docs-list">
        <div
          v-for="doc in docs"
          :key="doc.id"
          class="doc-card"
          @click="openDetail(doc)"
        >
          <div class="doc-card__icon">
            <el-icon :size="22"><DocIcon /></el-icon>
          </div>
          <div class="doc-card__body">
            <div class="doc-card__title-row">
              <span class="doc-card__title">{{ doc.title }}</span>
              <el-tag size="small" :type="accessTag(doc.access_level).type">
                {{ accessTag(doc.access_level).label }}
              </el-tag>
            </div>
            <div class="doc-card__meta">
              <el-tag size="small" type="info">{{ doc.doc_type }}</el-tag>
              <span>{{ doc.version }}</span>
              <span>{{ new Date(doc.created_at).toLocaleDateString() }}</span>
            </div>
          </div>
        </div>
        <div v-if="!loading && docs.length === 0" class="docs-empty">
          暂无可见文档
        </div>
      </div>
    </div>

    <el-drawer
      v-model="detailVisible"
      :title="detail?.title ?? '文档详情'"
      size="46%"
    >
      <div v-loading="detailLoading">
        <div v-if="detail" class="doc-detail">
          <div class="doc-detail__meta">
            <el-tag size="small" type="info">{{ detail.doc_type }}</el-tag>
            <el-tag size="small" :type="accessTag(detail.access_level).type">
              {{ accessTag(detail.access_level).label }}
            </el-tag>
            <span>{{ detail.version }}</span>
          </div>
          <div
            v-for="chunk in detail.chunks ?? []"
            :key="chunk.chunk_index"
            class="doc-detail__chunk"
          >
            <span class="doc-detail__index">#{{ chunk.chunk_index + 1 }}</span>
            <p>{{ chunk.text }}</p>
          </div>
          <el-empty
            v-if="(detail.chunks ?? []).length === 0"
            description="该文档尚未完成索引"
          />
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.docs-layout {
  display: flex;
  height: 100vh;
}

.docs-side {
  width: 220px;
  flex-shrink: 0;
  background: #1a2a3a;
  color: #fff;
  display: flex;
  flex-direction: column;
  padding: 20px 14px;
}

.docs-side__title {
  font-size: 18px;
  margin: 0 0 24px;
}

.docs-side__nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.side-link {
  text-align: left;
  padding: 10px 12px;
  border: none;
  background: none;
  color: rgba(255, 255, 255, 0.75);
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.side-link:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.side-link--active {
  background: #2b6cb0;
  color: #fff;
}

.docs-side__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.12);
  padding-top: 12px;
}

.docs-side__user {
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.docs-main {
  flex: 1;
  padding: 20px 28px;
  overflow-y: auto;
  background: #f5f7fa;
}

.docs-toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
}

.docs-toolbar__search {
  max-width: 380px;
}

.docs-toolbar__type {
  width: 160px;
}

.docs-hint {
  color: #909399;
  font-size: 12px;
  margin: 0 0 16px;
}

.docs-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.doc-card {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  background: #fff;
  border-radius: 8px;
  padding: 16px 18px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: border-color 0.15s;
}

.doc-card:hover {
  border-color: #409eff;
}

.doc-card__icon {
  width: 42px;
  height: 42px;
  border-radius: 8px;
  background: #e6f0fa;
  color: #2b6cb0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.doc-card__body {
  flex: 1;
  min-width: 0;
}

.doc-card__title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.doc-card__title {
  font-weight: 600;
  font-size: 15px;
  color: #303133;
}

.doc-card__meta {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #909399;
  font-size: 12px;
}

.docs-empty {
  text-align: center;
  color: #909399;
  padding: 40px 0;
}

.doc-detail__meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  color: #909399;
  font-size: 13px;
}

.doc-detail__chunk {
  display: flex;
  gap: 10px;
  padding: 12px 14px;
  background: #f9fafc;
  border-radius: 6px;
  margin-bottom: 10px;
}

.doc-detail__index {
  color: #409eff;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.doc-detail__chunk p {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: #444;
  white-space: pre-wrap;
}
</style>
