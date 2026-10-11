import type {
  ChatRequest,
  ChatResponse,
  ErrorResponse,
  SSEEvent,
} from './types';

const TOKEN_KEY = 'gongan_access_token';
const LOGIN_PATH = '/login';

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

interface RequestOptions {
  method?: HttpMethod;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  skipAuthRetry?: boolean;
}

class ApiError extends Error {
  public readonly status: number;
  public readonly traceId: string;
  public readonly code: string;

  constructor(status: number, code: string, message: string, traceId: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.traceId = traceId;
  }
}

interface StreamChatCallbacks {
  onToken: (token: string) => void;
  onSources?: (sources: ChatResponse['sources']) => void;
  onDone?: (fullResponse: string) => void;
}

let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

function getBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (typeof envUrl === 'string' && envUrl.length > 0) {
    return envUrl;
  }
  return '/api/v1';
}

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

function redirectToLogin(): void {
  if (window.location.pathname !== LOGIN_PATH) {
    window.location.href = LOGIN_PATH;
  }
}

function showToast(message: string): void {
  window.dispatchEvent(
    new CustomEvent('api-error', { detail: { message } }),
  );
}

function buildUrl(path: string): string {
  const base = getBaseUrl();
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  if (base.endsWith('/api/v1') && normalizedPath.startsWith('/api/v1/')) {
    return `${base}${normalizedPath.slice(7)}`;
  }
  return `${base}${normalizedPath}`;
}

/** 把 FastAPI 422 校验错误的英文 msg 转成用户能懂的中文提示。 */
function humanizeValidationError(body: ErrorResponse): string | null {
  const detail = body.detail;
  if (!Array.isArray(detail) || detail.length === 0) return null;
  const first = detail[0];
  const field = first.loc?.[first.loc.length - 1];
  const msg = first.msg ?? '';
  if (field === 'password' && msg.includes('at least 8 characters')) {
    return '密码长度至少 8 位，且需同时包含字母和数字';
  }
  if (msg.includes('Password must contain')) {
    return '密码必须同时包含字母和数字';
  }
  if (field && msg) {
    return `${field === 'password' ? '密码' : field === 'username' ? '用户名' : field} 格式不正确：${msg}`;
  }
  return null;
}

async function parseErrorResponse(response: Response): Promise<ApiError> {
  const traceId = response.headers.get('x-trace-id') ?? '';
  try {
    const body = (await response.json()) as ErrorResponse;
    const friendly =
      response.status === 422 ? humanizeValidationError(body) : null;
    return new ApiError(
      response.status,
      body.code ?? 'UNKNOWN',
      friendly ?? body.message ?? '请求失败',
      body.trace_id ?? traceId,
    );
  } catch {
    return new ApiError(
      response.status,
      'UNKNOWN',
      `请求失败 (${response.status})`,
      traceId,
    );
  }
}

async function refreshToken(): Promise<boolean> {
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }

  isRefreshing = true;
  refreshPromise = (async () => {
    try {
      const resp = await fetch(buildUrl('/auth/refresh'), {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken() ?? ''}`,
        },
      });
      if (!resp.ok) {
        clearToken();
        redirectToLogin();
        return false;
      }
      const data = await resp.json();
      setToken(data.access_token);
      return true;
    } catch {
      clearToken();
      redirectToLogin();
      return false;
    } finally {
      isRefreshing = false;
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

class ApiClient {
  public async request<T>(
    path: string,
    options: RequestOptions = {},
  ): Promise<T> {
    const {
      method = 'GET',
      body,
      headers = {},
      signal,
      skipAuthRetry = false,
    } = options;

    const requestHeaders: Record<string, string> = { ...headers };
    const token = getToken();
    if (token) {
      requestHeaders.Authorization = `Bearer ${token}`;
    }

    let requestBody: BodyInit | undefined;
    if (body !== undefined && body !== null) {
      if (body instanceof FormData) {
        requestBody = body;
      } else {
        requestHeaders['Content-Type'] = 'application/json';
        requestBody = JSON.stringify(body);
      }
    }

    const response = await fetch(buildUrl(path), {
      method,
      headers: requestHeaders,
      body: requestBody,
      signal,
    });

    if (response.status === 401) {
      if (skipAuthRetry) {
        clearToken();
        redirectToLogin();
        throw new ApiError(401, 'UNAUTHORIZED', '认证失败', '');
      }
      const refreshed = await refreshToken();
      if (refreshed) {
        return this.request<T>(path, { ...options, skipAuthRetry: true });
      }
      throw new ApiError(401, 'UNAUTHORIZED', '认证已过期', '');
    }

    if (response.status >= 500) {
      const error = await parseErrorResponse(response);
      showToast(error.message);
      throw error;
    }

    if (response.status === 204) {
      return undefined as T;
    }

    if (!response.ok) {
      throw await parseErrorResponse(response);
    }

    const contentType = response.headers.get('content-type') ?? '';
    if (contentType.includes('application/json')) {
      return (await response.json()) as T;
    }
    return (await response.text()) as unknown as T;
  }

  public get<T>(path: string, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
    return this.request<T>(path, { ...options, method: 'GET' });
  }

  public post<T>(
    path: string,
    body?: unknown,
    options?: Omit<RequestOptions, 'method' | 'body'>,
  ): Promise<T> {
    return this.request<T>(path, { ...options, method: 'POST', body });
  }

  public put<T>(
    path: string,
    body?: unknown,
    options?: Omit<RequestOptions, 'method' | 'body'>,
  ): Promise<T> {
    return this.request<T>(path, { ...options, method: 'PUT', body });
  }

  public patch<T>(
    path: string,
    body?: unknown,
    options?: Omit<RequestOptions, 'method' | 'body'>,
  ): Promise<T> {
    return this.request<T>(path, { ...options, method: 'PATCH', body });
  }

  public delete<T>(path: string, options?: Omit<RequestOptions, 'method' | 'body'>): Promise<T> {
    return this.request<T>(path, { ...options, method: 'DELETE' });
  }

  public async streamChat(
    chatRequest: ChatRequest,
    callbacks: StreamChatCallbacks,
    signal?: AbortSignal,
  ): Promise<void> {
    const token = getToken();
    const response = await fetch(buildUrl('/chat'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ ...chatRequest, stream: true }),
      signal,
    });

    if (!response.ok) {
      throw await parseErrorResponse(response);
    }

    if (!response.body) {
      throw new ApiError(500, 'NO_BODY', '响应体为空', '');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullResponse = '';

    const parseSSEEvents = (rawText: string): SSEEvent[] => {
      const events: SSEEvent[] = [];
      const chunks = rawText.split('\n\n');
      for (const chunk of chunks) {
        const lines = chunk.split('\n');
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data:')) {
            continue;
          }
          const dataStr = trimmed.slice(5).trim();
          if (dataStr.length === 0 || dataStr === '[DONE]') {
            continue;
          }
          try {
            const parsed = JSON.parse(dataStr) as SSEEvent;
            events.push(parsed);
          } catch {
            // 跳过无法解析的 JSON
          }
        }
      }
      return events;
    };

    const processEvents = (events: SSEEvent[]): void => {
      for (const event of events) {
        if (event.type === 'token') {
          fullResponse += event.content;
          callbacks.onToken(event.content);
        } else if (event.type === 'sources') {
          if (callbacks.onSources) {
            try {
              const sources = JSON.parse(event.content) as ChatResponse['sources'];
              callbacks.onSources(sources);
            } catch {
              // 跳过无法解析的 sources
            }
          }
        } else if (event.type === 'done') {
          if (callbacks.onDone) {
            callbacks.onDone(fullResponse);
          }
        }
      }
    };

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          const remaining = parseSSEEvents(buffer);
          processEvents(remaining);
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        const lastDoubleNewline = buffer.lastIndexOf('\n\n');
        if (lastDoubleNewline !== -1) {
          const complete = buffer.slice(0, lastDoubleNewline + 2);
          buffer = buffer.slice(lastDoubleNewline + 2);
          const events = parseSSEEvents(complete);
          processEvents(events);
        }
      }
    } finally {
      reader.releaseLock();
    }
  }
}

export const apiClient = new ApiClient();

export default apiClient;

export { ApiError, TOKEN_KEY };
