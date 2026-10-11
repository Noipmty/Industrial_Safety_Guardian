import { http, HttpResponse, delay } from 'msw';
import type { JsonBodyType } from 'msw';
import type {
  ChatRequest,
  ChatResponse,
  ExamGenerateRequest,
  ExamGenerateResponse,
  ExamDetail,
  ExamSubmitRequest,
  ExamSubmitResponse,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  DocumentUploadResponse,
  DocumentListItem,
  AdminUser,
  AdminStats,
  HealthResponse,
  ChatSession,
  ChatMessage,
  ExamListItem,
  DocumentStatus,
  RefreshResponse,
  User,
} from '../api/types';

const BASE = '/api/v1';

const mockUser: User = {
  id: 1,
  username: 'admin',
  real_name: '系统管理员',
  position: '安全管理员',
  role: 'admin',
};

const mockToken = 'mock-jwt-token-for-development';

function jsonResponse(data: unknown, status: number = 200): HttpResponse<JsonBodyType> {
  return HttpResponse.json(data as JsonBodyType, { status });
}

function createSSEStream(
  tokens: string[],
  sources: ChatResponse['sources'],
): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();

  return new ReadableStream<Uint8Array>({
    async start(controller) {
      const send = (data: unknown): void => {
        const payload = `data: ${JSON.stringify(data)}\n\n`;
        controller.enqueue(encoder.encode(payload));
      };

      if (sources.length > 0) {
        send({ type: 'sources', content: JSON.stringify(sources) });
        await delay(50);
      }

      for (const token of tokens) {
        send({ type: 'token', content: token });
        await delay(40);
      }

      send({ type: 'done', content: '' });
      controller.close();
    },
  });
}

export const handlers = [
  // ─── 健康检查 ─────────────────────────────────────────────
  http.get('/health', () => {
    const body: HealthResponse = {
      status: 'ok',
      version: '0.1.0',
      checks: {
        mysql: 'up',
        redis: 'up',
      },
    };
    return jsonResponse(body);
  }),

  // ─── 认证 ─────────────────────────────────────────────────
  http.post(`${BASE}/auth/login`, async ({ request }) => {
    const reqBody = (await request.json()) as LoginRequest;
    if (!reqBody.username || !reqBody.password) {
      return jsonResponse(
        { code: 'INVALID_CREDENTIALS', message: '用户名或密码不能为空', trace_id: 'mock-trace-001' },
        401,
      );
    }
    const body: LoginResponse = {
      access_token: mockToken,
      token_type: 'bearer',
      user: { ...mockUser, username: reqBody.username },
    };
    return jsonResponse(body);
  }),

  http.post(`${BASE}/auth/register`, async ({ request }) => {
    const reqBody = (await request.json()) as RegisterRequest;
    const body: RegisterResponse = {
      id: Math.floor(Math.random() * 1000) + 1,
      username: reqBody.username,
      position: reqBody.position,
      role: reqBody.role ?? 'worker',
    };
    return jsonResponse(body, 201);
  }),

  http.get(`${BASE}/auth/me`, ({ request }) => {
    const auth = request.headers.get('Authorization');
    if (!auth || !auth.includes('Bearer')) {
      return jsonResponse(
        { code: 'UNAUTHORIZED', message: '未认证', trace_id: 'mock-trace-002' },
        401,
      );
    }
    return jsonResponse(mockUser);
  }),

  http.post(`${BASE}/auth/refresh`, ({ request }) => {
    const auth = request.headers.get('Authorization');
    if (!auth || !auth.includes('Bearer')) {
      return jsonResponse(
        { code: 'UNAUTHORIZED', message: '刷新失败', trace_id: 'mock-trace-003' },
        401,
      );
    }
    const body: RefreshResponse = {
      access_token: `${mockToken}-refreshed`,
      token_type: 'bearer',
    };
    return jsonResponse(body);
  }),

  // ─── 对话 ─────────────────────────────────────────────────
  http.post(`${BASE}/chat`, async ({ request }) => {
    const reqBody = (await request.json()) as ChatRequest;

    if (reqBody.stream) {
      const mockTokens = '根据《安全生产法》规定，生产经营单位应当建立安全生产责任制。具体包括：1. 建立健全全员安全生产责任制；2. 确保安全投入到位；3. 开展安全教育培训。'.split('');
      const mockSources: ChatResponse['sources'] = [
        {
          doc_type: '安全生产法',
          score: 0.95,
          text: '生产经营单位应当建立安全生产责任制，落实全员安全生产责任。',
        },
      ];
      const stream = createSSEStream(mockTokens, mockSources);
      return new HttpResponse(stream, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          Connection: 'keep-alive',
        },
      });
    }

    const body: ChatResponse = {
      response:
        '根据《安全生产法》规定，生产经营单位应当建立安全生产责任制，落实全员安全生产责任。建议定期开展安全培训和隐患排查。',
      intent: 'safety_regulation_query',
      sources: [
        {
          doc_type: '安全生产法',
          score: 0.95,
          text: '生产经营单位应当建立安全生产责任制，落实全员安全生产责任。',
        },
      ],
      session_id: reqBody.session_id ?? `session-${Date.now()}`,
      trace_id: `trace-${Date.now()}`,
    };
    return jsonResponse(body);
  }),

  http.get(`${BASE}/chat/sessions`, ({ request }) => {
    const url = new URL(request.url);
    const userId = url.searchParams.get('user_id');
    if (!userId) {
      return jsonResponse(
        { code: 'BAD_REQUEST', message: '缺少 user_id 参数', trace_id: 'mock-trace-004' },
        400,
      );
    }
    const sessions: ChatSession[] = [
      {
        session_id: 'session-1',
        last_message: '安全生产责任制包括哪些内容？',
        created_at: new Date(Date.now() - 86400000).toISOString(),
        updated_at: new Date(Date.now() - 3600000).toISOString(),
      },
      {
        session_id: 'session-2',
        last_message: '危险化学品如何分类管理？',
        created_at: new Date(Date.now() - 172800000).toISOString(),
        updated_at: new Date(Date.now() - 7200000).toISOString(),
      },
    ];
    return jsonResponse(sessions);
  }),

  http.get(`${BASE}/chat/sessions/:session_id/messages`, ({ params }) => {
    const sessionId = params['session_id'] as string;
    const messages: ChatMessage[] = [
      {
        role: 'user',
        content: '安全生产责任制包括哪些内容？',
        created_at: new Date(Date.now() - 3600000).toISOString(),
      },
      {
        role: 'assistant',
        content:
          '安全生产责任制包括：1. 建立健全全员安全生产责任制；2. 确保安全投入到位；3. 开展安全教育培训。',
        created_at: new Date(Date.now() - 3599000).toISOString(),
      },
    ];
    if (sessionId === 'not-found') {
      return jsonResponse(
        { code: 'NOT_FOUND', message: '会话不存在', trace_id: 'mock-trace-005' },
        404,
      );
    }
    return jsonResponse(messages);
  }),

  http.delete(`${BASE}/chat/sessions/:session_id`, () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // ─── 考试 ─────────────────────────────────────────────────
  http.post(`${BASE}/exam/generate`, async ({ request }) => {
    const reqBody = (await request.json()) as ExamGenerateRequest;
    const body: ExamGenerateResponse = {
      exam_id: Math.floor(Math.random() * 1000) + 1,
      status: 'generating',
    };
    return jsonResponse(body, 202);
  }),

  http.get(`${BASE}/exam/:exam_id`, ({ params }) => {
    const examId = Number(params['exam_id']);
    const body: ExamDetail = {
      id: examId,
      position: '安全管理员',
      status: 'ready',
      questions: [
        {
          id: 1,
          question_type: 'single_choice',
          stem: '《安全生产法》规定，生产经营单位应当建立什么制度？',
          options: ['A. 安全生产责任制', 'B. 质量管理体系', 'C. 环境管理体系', 'D. 职业健康体系'],
          score: 10,
        },
        {
          id: 2,
          question_type: 'multiple_choice',
          stem: '以下属于危险化学品分类的有？',
          options: ['A. 爆炸品', 'B. 压缩气体', 'C. 易燃液体', 'D. 自燃物品'],
          score: 15,
        },
        {
          id: 3,
          question_type: 'essay',
          stem: '简述安全生产管理的基本原则。',
          score: 25,
        },
      ],
      total_score: 50,
      time_limit: 60,
    };
    return jsonResponse(body);
  }),

  http.post(`${BASE}/exam/:exam_id/submit`, async ({ request, params }) => {
    const examId = Number(params['exam_id']);
    const reqBody = (await request.json()) as ExamSubmitRequest;
    const body: ExamSubmitResponse = {
      exam_id: examId,
      status: 'graded',
      total_score: 42,
      answers: reqBody.answers.map((ans, idx) => ({
        question_id: ans.question_id,
        user_answer: ans.user_answer,
        score: idx === 2 ? 12 : 15,
        grading_detail: idx === 2 ? '要点覆盖不全，扣3分' : undefined,
        graded_by: idx === 2 ? 'llm' : 'rule',
      })),
    };
    return jsonResponse(body);
  }),

  http.get(`${BASE}/exam/:exam_id/result`, ({ params }) => {
    const examId = Number(params['exam_id']);
    const body = {
      exam: {
        id: examId,
        position: '安全管理员',
        status: 'graded',
        questions: [
          {
            id: 1,
            question_type: 'single_choice',
            stem: '《安全生产法》规定，生产经营单位应当建立什么制度？',
            options: ['A. 安全生产责任制', 'B. 质量管理体系', 'C. 环境管理体系', 'D. 职业健康体系'],
            score: 10,
          },
        ],
        total_score: 50,
        time_limit: 60,
      },
      questions: [
        {
          id: 1,
          question_type: 'single_choice',
          stem: '《安全生产法》规定，生产经营单位应当建立什么制度？',
          options: ['A. 安全生产责任制', 'B. 质量管理体系', 'C. 环境管理体系', 'D. 职业健康体系'],
          score: 10,
        },
      ],
      answers: [
        {
          question_id: 1,
          user_answer: 'A',
          score: 10,
          graded_by: 'rule',
        },
      ],
      analysis: {
        weak_points: ['危险化学品分类管理'],
        strong_points: ['安全生产责任制', '安全教育培训'],
      },
    };
    return jsonResponse(body);
  }),

  http.get(`${BASE}/exam/list`, ({ request }) => {
    const url = new URL(request.url);
    const userId = url.searchParams.get('user_id');
    if (!userId) {
      return jsonResponse(
        { code: 'BAD_REQUEST', message: '缺少 user_id 参数', trace_id: 'mock-trace-006' },
        400,
      );
    }
    const items: ExamListItem[] = [
      {
        id: 1,
        position: '安全管理员',
        status: 'graded',
        total_score: 42,
        created_at: new Date(Date.now() - 86400000).toISOString(),
        submitted_at: new Date(Date.now() - 80000000).toISOString(),
      },
      {
        id: 2,
        position: '安全管理员',
        status: 'ready',
        total_score: 50,
        created_at: new Date(Date.now() - 43200000).toISOString(),
      },
    ];
    return jsonResponse(items);
  }),

  // ─── 管理 ─────────────────────────────────────────────────
  http.post(`${BASE}/admin/documents`, async ({ request }) => {
    const formData = await request.formData();
    const title = (formData.get('title') as string) ?? '未命名文档';
    const docType = (formData.get('doc_type') as string) ?? 'regulation';
    const body: DocumentUploadResponse = {
      doc_id: Math.floor(Math.random() * 1000) + 1,
      status: 'processing',
    };
    return jsonResponse(body, 202);
  }),

  http.get(`${BASE}/admin/documents`, () => {
    const docs: DocumentListItem[] = [
      {
        id: 1,
        title: '安全生产法（2021修正）',
        doc_type: 'law',
        version: '2021',
        status: 'indexed',
        created_at: new Date(Date.now() - 86400000).toISOString(),
      },
      {
        id: 2,
        title: '危险化学品安全管理条例',
        doc_type: 'regulation',
        version: '2013',
        status: 'indexed',
        created_at: new Date(Date.now() - 172800000).toISOString(),
      },
      {
        id: 3,
        title: '企业安全生产标准化基本规范',
        doc_type: 'standard',
        version: '2017',
        status: 'processing',
        created_at: new Date(Date.now() - 3600000).toISOString(),
      },
    ];
    return jsonResponse(docs);
  }),

  http.get(`${BASE}/admin/documents/:id/status`, ({ params }) => {
    const id = Number(params['id']);
    const body: DocumentStatus = {
      id,
      status: id === 3 ? 'processing' : 'indexed',
      progress: id === 3 ? 0.65 : 1.0,
      chunks_count: id === 3 ? 128 : 256,
    };
    return jsonResponse(body);
  }),

  http.delete(`${BASE}/admin/documents/:id`, () => {
    return new HttpResponse(null, { status: 204 });
  }),

  http.get(`${BASE}/admin/users`, () => {
    const users: AdminUser[] = [
      {
        id: 1,
        username: 'admin',
        real_name: '系统管理员',
        position: '安全管理员',
        role: 'admin',
        created_at: new Date(Date.now() - 86400000 * 30).toISOString(),
      },
      {
        id: 2,
        username: 'worker01',
        real_name: '张三',
        position: '一线操作工',
        role: 'worker',
        created_at: new Date(Date.now() - 86400000 * 15).toISOString(),
      },
      {
        id: 3,
        username: 'supervisor01',
        real_name: '李四',
        position: '车间主任',
        role: 'supervisor',
        created_at: new Date(Date.now() - 86400000 * 7).toISOString(),
      },
    ];
    return jsonResponse(users);
  }),

  http.get(`${BASE}/admin/stats`, () => {
    const body: AdminStats = {
      total_users: 128,
      total_docs: 56,
      total_exams: 342,
      total_questions: 1280,
      avg_score: 78.5,
    };
    return jsonResponse(body);
  }),
];
