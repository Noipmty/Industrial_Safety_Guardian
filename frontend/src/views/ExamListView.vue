<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Document, Plus, Clock } from '@element-plus/icons-vue';
import { useAuthStore } from '@/stores/auth';
import apiClient from '@/api/client';
import type {
  ExamListItem,
  ExamGenerateRequest,
  ExamGenerateResponse,
} from '@/api/types';

const router = useRouter();
const authStore = useAuthStore();

const exams = ref<ExamListItem[]>([]);
const loading = ref(false);
const generateDialogVisible = ref(false);

const generateForm = reactive({
  position: authStore.user?.position ?? '司钻',
  question_types: ['single', 'multiple', 'judge'] as string[],
  num_questions: 5,
  knowledge_tags: '' as string,
});

const questionTypeOptions = [
  { label: '单选题', value: 'single' },
  { label: '多选题', value: 'multiple' },
  { label: '判断题', value: 'judge' },
  { label: '简答题', value: 'short_answer' },
];

function getUserId(): number {
  return authStore.user?.id ?? 1;
}

async function fetchExams(): Promise<void> {
  loading.value = true;
  try {
    exams.value = await apiClient.get<ExamListItem[]>(
      `/exam/list?user_id=${getUserId()}`,
    );
  } catch {
    ElMessage.error('加载考试列表失败');
  } finally {
    loading.value = false;
  }
}

async function openGenerate(): Promise<void> {
  generateDialogVisible.value = true;
}

async function handleGenerate(): Promise<void> {
  if (generateForm.question_types.length === 0) {
    ElMessage.warning('请至少选择一种题型');
    return;
  }
  const tags = generateForm.knowledge_tags
    .split(/[,，\s]+/)
    .map((t) => t.trim())
    .filter((t) => t.length > 0);

  const payload: ExamGenerateRequest = {
    user_id: getUserId(),
    position: generateForm.position,
    question_types: generateForm.question_types,
    num_questions: generateForm.num_questions,
    knowledge_tags: tags.length > 0 ? tags : undefined,
  };

  try {
    const resp = await apiClient.post<ExamGenerateResponse>(
      '/exam/generate',
      payload,
    );
    ElMessage.success(`试卷已生成（ID: ${resp.exam_id}）`);
    generateDialogVisible.value = false;
    await fetchExams();
    router.push(`/exam/take/${resp.exam_id}`);
  } catch {
    ElMessage.error('生成试卷失败');
  }
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    created: '待考试',
    submitted: '已提交',
    graded: '已批改',
  };
  return map[status] ?? status;
}

function statusTagType(status: string): '' | 'success' | 'warning' | 'info' {
  const map: Record<string, '' | 'success' | 'warning' | 'info'> = {
    created: 'warning',
    submitted: 'info',
    graded: 'success',
  };
  return map[status] ?? 'info';
}

function goToExam(exam: ExamListItem): void {
  if (exam.status === 'created') {
    router.push(`/exam/take/${exam.id}`);
  } else {
    router.push(`/exam/result/${exam.id}`);
  }
}

onMounted(fetchExams);
</script>

<template>
  <div class="min-h-screen bg-gray-50 py-4 px-4">
    <div class="max-w-4xl mx-auto">
      <div class="flex items-center justify-between mb-6">
        <h1 class="text-xl font-bold text-gray-800">考试中心</h1>
        <el-button type="primary" :icon="Plus" @click="openGenerate">
          生成试卷
        </el-button>
      </div>

      <el-card v-loading="loading" shadow="never" class="mb-4">
        <el-empty
          v-if="exams.length === 0"
          description="暂无考试记录，点击右上角生成试卷"
        />
        <div v-else class="space-y-3">
          <div
            v-for="exam in exams"
            :key="exam.id"
            class="flex items-center justify-between p-4 rounded-lg border border-gray-200 hover:border-blue-400 hover:bg-blue-50 cursor-pointer transition-colors"
            @click="goToExam(exam)"
          >
            <div class="flex items-center gap-3">
              <el-icon :size="24" class="text-blue-500"><Document /></el-icon>
              <div>
                <div class="font-medium text-gray-800">
                  试卷 #{{ exam.id }} — {{ exam.position }}
                </div>
                <div class="text-sm text-gray-500 flex items-center gap-2">
                  <el-icon :size="14"><Clock /></el-icon>
                  {{ new Date(exam.created_at).toLocaleString() }}
                  <span v-if="exam.total_score !== null">
                    | 总分: {{ exam.total_score }}
                  </span>
                </div>
              </div>
            </div>
            <el-tag :type="statusTagType(exam.status)" size="small">
              {{ statusLabel(exam.status) }}
            </el-tag>
          </div>
        </div>
      </el-card>
    </div>

    <el-dialog v-model="generateDialogVisible" title="生成试卷" width="480px">
      <el-form label-width="80px">
        <el-form-item label="岗位">
          <el-input v-model="generateForm.position" disabled />
        </el-form-item>
        <el-form-item label="题型">
          <el-checkbox-group v-model="generateForm.question_types">
            <el-checkbox
              v-for="opt in questionTypeOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="题量">
          <el-input-number
            v-model="generateForm.num_questions"
            :min="1"
            :max="50"
          />
        </el-form-item>
        <el-form-item label="知识点">
          <el-input
            v-model="generateForm.knowledge_tags"
            placeholder="井控,硫化氢,应急管理（逗号分隔，可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="generateDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleGenerate">生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>
