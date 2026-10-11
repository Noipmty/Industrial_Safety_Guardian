<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Clock, Check } from '@element-plus/icons-vue';
import { useAuthStore } from '@/stores/auth';
import apiClient from '@/api/client';
import type { ExamDetail, ExamSubmitResponse, ExamAnswerItem } from '@/api/types';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const exam = ref<ExamDetail | null>(null);
const loading = ref(true);
const submitting = ref(false);

// 用户答案：{ [question_id]: string }
const answers = reactive<Record<number, string>>({});

// 倒计时
const remainingSeconds = ref(0);
let timer: ReturnType<typeof setInterval> | null = null;

const examId = computed(() => Number(route.params.examId));

const formattedTime = computed(() => {
  const m = Math.floor(remainingSeconds.value / 60);
  const s = remainingSeconds.value % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
});

const answeredCount = computed(() => {
  return Object.values(answers).filter((v) => v && v.trim().length > 0).length;
});

const totalQuestions = computed(() => exam.value?.questions.length ?? 0);

async function fetchExam(): Promise<void> {
  loading.value = true;
  try {
    exam.value = await apiClient.get<ExamDetail>(`/exam/${examId.value}`);
    remainingSeconds.value = exam.value.time_limit;
    startTimer();
  } catch {
    ElMessage.error('加载试卷失败');
    router.push('/exam');
  } finally {
    loading.value = false;
  }
}

function startTimer(): void {
  if (timer) clearInterval(timer);
  timer = setInterval(() => {
    remainingSeconds.value--;
    if (remainingSeconds.value <= 0) {
      if (timer) clearInterval(timer);
      ElMessage.warning('考试时间到，自动提交');
      handleSubmit(true);
    }
  }, 1000);
}

function selectOption(qid: number, option: string): void {
  answers[qid] = option;
}

function toggleMultiple(qid: number, option: string): void {
  const current = answers[qid] || '';
  const selected = current.split('').filter((c) => c);
  const idx = selected.indexOf(option);
  if (idx >= 0) {
    selected.splice(idx, 1);
  } else {
    selected.push(option);
  }
  selected.sort();
  answers[qid] = selected.join('');
}

function toggleJudge(qid: number, val: string): void {
  answers[qid] = answers[qid] === val ? '' : val;
}

async function handleSubmit(auto = false): Promise<void> {
  if (!auto) {
    const unanswered = totalQuestions.value - answeredCount.value;
    if (unanswered > 0) {
      try {
        await ElMessageBox.confirm(
          `还有 ${unanswered} 遘题未作答，确定提交吗？`,
          '提交确认',
          { type: 'warning' },
        );
      } catch {
        return;
      }
    } else {
      try {
        await ElMessageBox.confirm('确定提交试卷吗？提交后不可修改。', '提交确认', {
          type: 'warning',
        });
      } catch {
        return;
      }
    }
  }

  submitting.value = true;
  if (timer) clearInterval(timer);

  const answerItems: ExamAnswerItem[] = (exam.value?.questions ?? []).map((q) => ({
    question_id: q.id,
    user_answer: answers[q.id] || '（未作答）',
  }));

  try {
    const resp = await apiClient.post<ExamSubmitResponse>(
      `/exam/${examId.value}/submit`,
      { answers: answerItems },
    );
    ElMessage.success(`试卷已批改，总分: ${resp.total_score}`);
    router.push(`/exam/result/${examId.value}`);
  } catch {
    ElMessage.error('提交失败，请重试');
    startTimer();
  } finally {
    submitting.value = false;
  }
}

function optionLabel(idx: number): string {
  return String.fromCharCode(65 + idx);
}

onMounted(fetchExam);
onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<template>
  <div v-loading="loading" class="min-h-screen bg-gray-50 py-4 px-4">
    <div class="max-w-3xl mx-auto" v-if="exam">
      <!-- 顶部标题与倒计时 -->
      <div class="flex items-center justify-between mb-4 sticky top-0 bg-gray-50 z-10 py-2">
        <h1 class="text-lg font-bold text-gray-800">
          试卷 #{{ exam.id }} — {{ exam.position }}
        </h1>
        <div class="flex items-center gap-3">
          <div
            class="flex items-center gap-1 px-3 py-1 rounded-full"
            :class="remainingSeconds < 60 ? 'bg-red-100 text-red-600' : 'bg-blue-100 text-blue-600'"
          >
            <el-icon :size="16"><Clock /></el-icon>
            <span class="font-mono font-bold">{{ formattedTime }}</span>
          </div>
          <el-button
            type="primary"
            :icon="Check"
            :loading="submitting"
            @click="handleSubmit(false)"
          >
            交卷
          </el-button>
        </div>
      </div>

      <!-- 进度条 -->
      <el-progress
        :percentage="totalQuestions > 0 ? Math.round((answeredCount / totalQuestions) * 100) : 0"
        :stroke-width="4"
        class="mb-4"
      />

      <!-- 题目 -->
      <div class="space-y-4">
        <el-card
          v-for="(q, idx) in exam.questions"
          :key="q.id"
          shadow="never"
          class="mb-3"
        >
          <div class="flex gap-2">
            <span class="text-blue-500 font-bold flex-shrink-0">{{ idx + 1 }}.</span>
            <div class="flex-1">
              <div class="mb-3">
                <span class="font-medium">{{ q.stem }}</span>
                <el-tag size="small" class="ml-2" type="info">
                  {{ q.question_type === 'single' ? '单选' : q.question_type === 'multiple' ? '多选' : q.question_type === 'judge' ? '判断' : '简答' }}
                </el-tag>
                <span class="ml-2 text-gray-400 text-sm">{{ q.score }}分</span>
              </div>

              <!-- 单选题 -->
              <div v-if="q.question_type === 'single'" class="space-y-2">
                <div
                  v-for="(opt, oi) in q.options"
                  :key="oi"
                  class="flex items-center gap-2 p-2 rounded cursor-pointer hover:bg-blue-50"
                  :class="answers[q.id] === optionLabel(oi) ? 'bg-blue-100 border border-blue-300' : ''"
                  @click="selectOption(q.id, optionLabel(oi))"
                >
                  <span class="w-6 h-6 rounded-full border flex items-center justify-center text-sm"
                    :class="answers[q.id] === optionLabel(oi) ? 'bg-blue-500 text-white border-blue-500' : 'border-gray-300'"
                  >{{ optionLabel(oi) }}</span>
                  <span>{{ opt }}</span>
                </div>
              </div>

              <!-- 多选题 -->
              <div v-else-if="q.question_type === 'multiple'" class="space-y-2">
                <div
                  v-for="(opt, oi) in q.options"
                  :key="oi"
                  class="flex items-center gap-2 p-2 rounded cursor-pointer hover:bg-blue-50"
                  :class="(answers[q.id] || '').includes(optionLabel(oi)) ? 'bg-blue-100 border border-blue-300' : ''"
                  @click="toggleMultiple(q.id, optionLabel(oi))"
                >
                  <span class="w-6 h-6 rounded border flex items-center justify-center text-sm"
                    :class="(answers[q.id] || '').includes(optionLabel(oi)) ? 'bg-blue-500 text-white border-blue-500' : 'border-gray-300'"
                  >{{ optionLabel(oi) }}</span>
                  <span>{{ opt }}</span>
                </div>
              </div>

              <!-- 判断题 -->
              <div v-else-if="q.question_type === 'judge'" class="flex gap-3">
                <el-button
                  :type="answers[q.id] === '对' ? 'success' : 'default'"
                  @click="toggleJudge(q.id, '对')"
                >对</el-button>
                <el-button
                  :type="answers[q.id] === '错' ? 'danger' : 'default'"
                  @click="toggleJudge(q.id, '错')"
                >错</el-button>
              </div>

              <!-- 简答题 -->
              <el-input
                v-else
                v-model="answers[q.id]"
                type="textarea"
                :rows="4"
                placeholder="请输入答案..."
              />
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>
