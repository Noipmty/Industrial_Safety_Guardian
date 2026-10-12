<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useAdminStore } from '@/stores/admin'
import AppSkeleton from '@/components/common/AppSkeleton.vue'
import { POSITIONS } from '@/types'

const admin = useAdminStore()
const loading = ref(true)
const roleFilter = ref<'all' | 'worker' | 'admin'>('all')
const stats = computed(() => [
  { label: '用户总数', value: String(admin.users.length), warn: false },
  { label: '工人', value: String(admin.users.filter((u) => u.role === 'worker').length), warn: false },
  { label: '管理员', value: String(admin.users.filter((u) => u.role === 'admin').length), warn: false },
  { label: '停用账号', value: String(admin.users.filter((u) => !u.active).length), warn: true },
])

const list = computed(() =>
  admin.users.filter((u) => roleFilter.value === 'all' || u.role === roleFilter.value),
)

const addVisible = ref(false)
const form = ref({ name: '', username: '', role: 'worker' as 'worker' | 'admin', position: POSITIONS[0] })

function addUser(): void {
  if (!form.value.name.trim() || !form.value.username.trim()) {
    ElMessage.warning('姓名与用户名不能为空')
    return
  }
  admin.users.unshift({
    id: Date.now(),
    name: form.value.name,
    username: form.value.username,
    role: form.value.role,
    position: form.value.role === 'worker' ? form.value.position : '-',
    active: true,
    lastLogin: '-',
  })
  addVisible.value = false
  ElMessage.success('用户已创建，初始密码已发送至班组长')
  form.value = { name: '', username: '', role: 'worker', position: POSITIONS[0] }
}

function toggleActive(row: { active: boolean; name: string }): void {
  ElMessage.success(row.active ? `已启用 ${row.name}` : `已停用 ${row.name}（令牌即刻失效）`)
}

onMounted(async () => {
  try {
    await admin.loadUsers()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center gap-2">
      <el-radio-group v-model="roleFilter">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="worker">工人</el-radio-button>
        <el-radio-button value="admin">管理员</el-radio-button>
      </el-radio-group>
      <span class="flex-1" />
      <el-button type="primary" @click="addVisible = true"><el-icon class="mr-1"><Plus /></el-icon>新增用户</el-button>
    </div>

    <!-- 统计面板 -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div v-for="s in stats" :key="s.label" class="card p-3.5">
        <p class="text-xs text-graphite/50">{{ s.label }}</p>
        <p class="text-xl font-bold tabular-nums mt-0.5" :class="s.warn ? 'text-safety' : 'text-navy'">{{ s.value }}</p>
      </div>
    </div>

    <AppSkeleton v-if="loading" type="table" :rows="6" />
    <div v-else class="card p-2">
      <el-table :data="list" stripe>
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="username" label="用户名" width="110">
          <template #default="{ row }"><span class="font-mono text-xs">{{ row.username }}</span></template>
        </el-table-column>
        <el-table-column label="角色" width="90">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'warning' : 'info'" size="small" round>
              {{ row.role === 'admin' ? '管理员' : '工人' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="position" label="岗位" width="90" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-switch v-model="row.active" size="small" @change="toggleActive(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="lastLogin" label="最近登录" width="160">
          <template #default="{ row }"><span class="font-mono text-xs text-graphite/60">{{ row.lastLogin }}</span></template>
        </el-table-column>
        <el-table-column label="权限说明" min-width="180">
          <template #default="{ row }">
            <span class="text-xs text-graphite/50">
              {{ row.role === 'admin' ? '全部文档 + 管理功能' : 'public + internal 文档 · 岗位规程' }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="addVisible" title="新增用户" width="440px">
      <el-form label-width="70px">
        <el-form-item label="姓名"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="用户名"><el-input v-model="form.username" /></el-form-item>
        <el-form-item label="角色">
          <el-radio-group v-model="form.role">
            <el-radio-button value="worker">工人</el-radio-button>
            <el-radio-button value="admin">管理员</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.role === 'worker'" label="岗位">
          <el-select v-model="form.position" class="w-full">
            <el-option v-for="p in POSITIONS" :key="p" :label="p" :value="p" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addVisible = false">取消</el-button>
        <el-button type="primary" @click="addUser">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>
