<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { ArrowLeft } from '@element-plus/icons-vue';
import apiClient from '@/api/client';
import type { ExamResult } from '@/api/types';

const route = useRoute();
const router = useRouter();

const result = ref<ExamResult | null>(null);
const loading = ref(true);
const appealDialogVisible = ref(false);
const appealQuestionId = ref<number>(0);
const appealText = ref('');

const examId = computed(() => Number(route.params.examId));

async function fetchResult(): Promise<void> {
  loading.value = true;
  try {
    result.value = await apiClient.get<ExamResult>(`/exam/${examId.value}/result`);
  } catch {
    ElMessage.error('加载考试结果失败');
    router.push('/exam');
  } finally {
    loading.value = false;
  }
}

function scoreTagType(score: number, maxScore: number): '' | 'success' | 'warning' | 'danger' {
  const ratio = maxScore > 0 ? score / maxScore : 0;
  if (ratio >= 0.8) return 'success';
  if (ratio >= 0.6) return 'warning';
  return 'danger';
}

function openAppeal(qid: number): void {
  appealQuestionId.value = qid;
  appealText.value = '';
  appealDialogVisible.value = true;
}

async function submitAppeal(): Promise<void> {
  if (!appealText.value.trim()) {
    ElMessage.warning('请填写申诉理由');
    return;
  }
  ElMessage.info('申诉已记录，管理员将尽快复核');
  appealDialogVisible.value = false;
}

const totalScore = computed(() => {
  return result.value?.answers.reduce((sum, a) => sum + a.score, 0).toFixed(1) ?? '0';
});

const maxScore = computed(() => {
  return result.value?.questions.reduce((sum, q) => sum + q.score, 0).toFixed(1) ?? '0';
});

const scorePercent = computed(() => {
  const max = parseFloat(maxScore.value);
  if (max <= 0) return 0;
  return Math.round((parseFloat(totalScore.value) / max) * 100);
});

onMounted(fetchResult);
</script>

<template>
  <div v-loading="loading" class="min-h-screen bg-gray-50 py-4 px-4">
    <div class="max-w-3xl mx-auto" v-if="result">
      <!-- 顶部信息 -->
      <div class="flex items-center gap-3 mb-4">
        <el-button :icon="ArrowLeft" circle @click="router.push('/exam')" />
        <h1 class="text-lg font-bold text-gray-800">
          考试结果 — 试卷 #{{ result.exam.id }}
        </h1>
        <el-button text @click="router.push('/chat')">返回主页</el-button>
      </div>

      <!-- 得分汇总 -->
      <el-card shadow="never" class="mb-4">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-3xl font-bold" :class="scorePercent >= 60 ? 'text-green-600' : 'text-red-500'">
              {{ totalScore }} <span class="text-base text-gray-400">/ {{ maxScore }}</span>
            </div>
            <div class="text-sm text-gray-500 mt-1">得分率 {{ scorePercent }}%</div>
          </div>
          <el-progress
            type="circle"
            :percentage="scorePercent"
            :color="scorePercent >= 60 ? '#67c23a' : '#f56c6c'"
            :width="80"
          />
        </div>
      </el-card>

      <!-- 分析 -->
      <div v-if="result.analysis.weak_points.length > 0 || result.analysis.strong_points.length > 0" class="mb-4">
        <el-card shadow="never">
          <div v-if="result.analysis.strong_points.length > 0" class="mb-2">
            <span class="text-green-600 font-medium">掌握良好：</span>
            <el-tag
              v-for="tag in result.analysis.strong_points"
              :key="tag"
              type="success"
              size="small"
              class="mr-1"
            >{{ tag }}</el-tag>
          </div>
          <div v-if="result.analysis.weak_points.length > 0">
            <span class="text-red-500 font-medium">薄弱知识点：</span>
            <el-tag
              v-for="tag in result.analysis.weak_points"
              :key="tag"
              type="danger"
              size="small"
              class="mr-1"
            >{{ tag }}</el-tag>
          </div>
        </el-card>
      </div>

      <!-- 逐题解析 -->
      <div class="space-y-3">
        <el-card
          v-for="(q, idx) in result.questions"
          :key="q.id"
          shadow="never"
        >
          <template #header>
            <div class="flex items-center justify-between">
              <span>
                <span class="text-blue-500 font-bold">{{ idx + 1 }}.</span>
                <span class="ml-1">{{ q.stem }}</span>
              </span>
              <div class="flex items-center gap-2">
                <el-tag
                  :type="scoreTagType(
                    result.answers.find(a => a.question_id === q.id)?.score ?? 0,
                    q.score
                  )"
                  size="small"
                >
                  {{ result.answers.find(a => a.question_id === q.id)?.score ?? 0 }}/{{ q.score }}
                </el-tag>
              </div>
            </div>
          </template>

          <div v-if="q.options" class="space-y-1 mb-2">
            <div
              v-for="(opt, oi) in q.options"
              :key="oi"
              class="text-sm"
            >
              <span class="text-gray-400">{{ String.fromCharCode(65 + oi) }}.</span>
              {{ opt }}
            </div>
          </div>

          <div class="border-t pt-2 mt-2 text-sm space-y-1">
            <div>
              <span class="text-gray-500">你的答案：</span>
              <span class="font-medium">
                {{ result.answers.find(a => a.question_id === q.id)?.user_answer || '（未作答）' }}
              </span>
            </div>
            <div v-if="result.answers.find(a => a.question_id === q.id)?.grading_detail">
              <span class="text-gray-500">评分理由：</span>
              <span class="text-gray-700">
                {{ result.answers.find(a => a.question_id === q.id)?.grading_detail }}
              </span>
            </div>
          </div>

          <div class="border-t pt-2 mt-2">
            <el-button
              text
              size="small"
              type="warning"
              @click="openAppeal(q.id)"
            >申请复核</el-button>
          </div>
        </el-card>
      </div>
    </div>

    <el-dialog v-model="appealDialogVisible" title="成绩复核申诉" width="420px">
      <el-input
        v-model="appealText"
        type="textarea"
        :rows="4"
        placeholder="请说明你认为评分有误的理由..."
      />
      <template #footer>
        <el-button @click="appealDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAppeal">提交申诉</el-button>
      </template>
    </el-dialog>
  </div>
</template>
