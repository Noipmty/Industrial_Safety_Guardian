<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';
import { useAuthStore } from '@/stores/auth';
import { ApiError } from '@/api/client';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const formRef = ref<FormInstance>();
const loading = ref(false);

const form = reactive({
  username: '',
  password: '',
});

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 64, message: '用户名长度 2-64 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 128, message: '密码长度至少 8 个字符', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (value && !(/[A-Za-z]/.test(value) && /\d/.test(value))) {
          callback(new Error('密码必须同时包含字母和数字'));
        } else {
          callback();
        }
      },
      trigger: 'blur',
    },
  ],
};

async function handleLogin(): Promise<void> {
  if (!formRef.value) return;
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    await authStore.login(form.username, form.password);
    ElMessage.success(`欢迎回来，${authStore.user?.username ?? ''}`);
    // 前后台分离：管理员直达控制后台，普通用户进入前台
    const redirect =
      typeof route.query.redirect === 'string' && route.query.redirect
        ? route.query.redirect
        : authStore.isAdmin
          ? '/admin'
          : '/chat';
    router.push(redirect);
  } catch (error) {
    if (error instanceof ApiError) {
      ElMessage.error(error.message);
    } else {
      ElMessage.error('登录失败，请稍后重试');
    }
  } finally {
    loading.value = false;
  }
}

function handleEnter(event: KeyboardEvent): void {
  if (event.key === 'Enter') {
    handleLogin();
  }
}
</script>

<template>
  <div class="login-container">
    <el-card class="login-card" shadow="always">
      <template #header>
        <div class="login-header">
          <h2 class="login-title">工安卫士</h2>
          <p class="login-subtitle">工业安全AI助手</p>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="0"
        size="large"
        @keyup.enter="handleEnter"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            prefix-icon="User"
            clearable
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            show-password
            clearable
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            class="login-button"
            :loading="loading"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="demo-accounts">
        <p class="demo-title">演示账号</p>
        <p class="demo-row">管理员：admin / admin123</p>
        <p class="demo-row">普通用户：worker / worker123</p>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #1a2a3a 0%, #0d1b2a 100%);
}

.login-card {
  width: 420px;
  border-radius: 12px;
}

.login-header {
  text-align: center;
}

.login-title {
  margin: 0;
  font-size: 28px;
  color: #1a2a3a;
  font-weight: 700;
}

.login-subtitle {
  margin: 8px 0 0;
  font-size: 14px;
  color: #909399;
}

.login-button {
  width: 100%;
}

.demo-accounts {
  margin-top: 16px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
  text-align: center;
}

.demo-title {
  margin: 0 0 8px;
  font-size: 13px;
  color: #909399;
  font-weight: 600;
}

.demo-row {
  margin: 4px 0;
  font-size: 13px;
  color: #606266;
}
</style>
