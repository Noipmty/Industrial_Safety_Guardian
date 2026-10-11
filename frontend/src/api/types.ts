export interface ErrorResponse {
  code: string;
  message: string;
  trace_id: string;
  /** FastAPI 参数校验错误（422）返回的 detail 数组 */
  detail?: Array<{ loc?: string[]; msg?: string; type?: string }>;
}

export interface User {
  id: number;
  username: string;
  real_name: string;
  position: string;
  role: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: 'bearer';
  user: User;
}

export interface RegisterRequest {
  username: string;
  password: string;
  real_name: string;
  position: string;
  role?: string;
}

export interface RegisterResponse {
  id: number;
  username: string;
  position: string;
  role: string;
}

export interface RefreshResponse {
  access_token: string;
  token_type: 'bearer';
}

export interface ChatSource {
  doc_type: string;
  score: number;
  text: string;
  doc_id?: number | null;
  chunk_id?: string | null;
  position?: string | null;
  access_level?: string | null;
}

export interface ChatRequest {
  session_id?: string;
  message: string;
  user_id: number;
  stream?: boolean;
  scope?: 'admin' | null;
}

/** 文档查询列表项（/documents，权限过滤后） */
export interface DocQueryItem {
  id: number;
  title: string;
  doc_type: string;
  version: string;
  created_at: string;
  access_level: string;
  chunks?: Array<{ chunk_index: number; text: string }>;
}

export interface ChatResponse {
  response: string;
  intent: string;
  sources: ChatSource[];
  session_id: string;
  trace_id: string;
}

export interface ChatSession {
  session_id: string;
  last_message: string;
  created_at: string;
  updated_at: string;
}

export type ChatMessageRole = 'user' | 'assistant';

export interface ChatMessage {
  role: ChatMessageRole;
  content: string;
  created_at: string;
}

export interface SSEEvent {
  type: 'token' | 'sources' | 'done';
  content: string;
}

export interface ExamGenerateRequest {
  user_id: number;
  position: string;
  question_types: string[];
  num_questions: number;
  knowledge_tags?: string[];
}

export interface ExamGenerateResponse {
  exam_id: number;
  status: 'generating';
}

export interface ExamQuestion {
  id: number;
  question_type: string;
  stem: string;
  options?: string[];
  score: number;
}

export interface ExamDetail {
  id: number;
  position: string;
  status: string;
  questions: ExamQuestion[];
  total_score: number;
  time_limit: number;
}

export interface ExamAnswerItem {
  question_id: number;
  user_answer: string;
}

export interface ExamSubmitRequest {
  answers: ExamAnswerItem[];
}

export interface GradedAnswer {
  question_id: number;
  user_answer: string;
  score: number;
  grading_detail?: string;
  graded_by: string;
}

export interface ExamSubmitResponse {
  exam_id: number;
  status: 'graded';
  total_score: number;
  answers: GradedAnswer[];
}

export interface ExamResultAnalysis {
  weak_points: string[];
  strong_points: string[];
}

export interface ExamResult {
  exam: ExamDetail;
  questions: ExamQuestion[];
  answers: GradedAnswer[];
  analysis: ExamResultAnalysis;
}

export interface ExamListItem {
  id: number;
  position: string;
  status: string;
  total_score: number;
  created_at: string;
  submitted_at?: string;
}

export interface DocumentUploadResponse {
  doc_id: number;
  status: 'processing';
}

export interface DocumentListItem {
  id: number;
  title: string;
  doc_type: string;
  version: string;
  status: string;
  created_at: string;
}

export interface DocumentStatus {
  id: number;
  status: string;
  progress: number;
  chunks_count: number;
  error?: string;
}

export interface AdminUser {
  id: number;
  username: string;
  real_name: string;
  position: string;
  role: string;
  created_at: string;
}

export interface AdminStats {
  total_users: number;
  total_docs: number;
  total_exams: number;
  total_questions: number;
  avg_score: number;
}

export interface HealthResponse {
  status: 'ok';
  version: string;
  checks: {
    mysql: 'up';
    redis: 'up';
  };
}
