import { defineStore } from 'pinia'
import type { ExamSummary, Question } from '@/types'
import { fetchExamList, fetchExamResult, fetchPaper, submitPaper } from '@/api/exam'
import type { ExamResult } from '@/types'

const SAVE_KEY = 'gw_exam_answers'

interface ExamState {
  exams: ExamSummary[]
  loading: boolean
  paper: Question[]
  paperExamId: string
  answers: Record<string, Record<string, string>>
  submitting: boolean
  result: ExamResult | null
  /** 幂等锁提示（Redis SETNX + DB 唯一约束） */
  idempotentNotice: string
}

export const useExamStore = defineStore('exam', {
  state: (): ExamState => ({
    exams: [],
    loading: false,
    paper: [],
    paperExamId: '',
    answers: {},
    submitting: false,
    result: null,
    idempotentNotice: '',
  }),
  actions: {
    async loadExams() {
      this.loading = true
      try {
        this.exams = await fetchExamList()
      } finally {
        this.loading = false
      }
    },
    async loadPaper(examId: string) {
      this.paper = await fetchPaper(examId)
      this.paperExamId = examId
      const saved = localStorage.getItem(`${SAVE_KEY}:${examId}`)
      this.answers[examId] = saved
        ? (JSON.parse(saved) as Record<string, string>)
        : {}
    },
    setAnswer(examId: string, qid: string, value: string) {
      if (!this.answers[examId]) this.answers[examId] = {}
      this.answers[examId][qid] = value
      // 自动保存（模拟 3s 防抖落库）
      localStorage.setItem(
        `${SAVE_KEY}:${examId}`,
        JSON.stringify(this.answers[examId]),
      )
    },
    async submit(examId: string) {
      this.submitting = true
      this.idempotentNotice = ''
      try {
        this.result = await submitPaper(
          examId,
          this.answers[examId] ?? {},
        )
        localStorage.removeItem(`${SAVE_KEY}:${examId}`)
        this.idempotentNotice =
          '提交成功（幂等锁：Redis SETNX + DB 唯一约束，重复提交返回同一成绩）'
      } finally {
        this.submitting = false
      }
    },
    /** 成绩页加载：优先用刚提交的结果，否则按 examId 查询。 */
    async loadResult(examId: string) {
      if (this.result?.exam.id === examId) return
      this.result = await fetchExamResult(examId)
    },
  },
})
