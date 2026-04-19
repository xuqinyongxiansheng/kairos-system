/**
 * 本地FastAPI后端客户端封装
 *
 * 封装所有18个后端端点，提供类型安全的TypeScript调用接口。
 * 支持JWT认证、错误重试、SSE流式响应等功能。
 *
 * 使用方式：
 *   import { localBackend } from './localBackend';
 *   const health = await localBackend.health();
 */

// ==================== 类型定义 ====================

/** 认证请求 */
export interface AuthRequest {
  api_key: string;
  user_id: string;
}

/** 认证响应 */
export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

/** 认证验证响应 */
export interface AuthVerifyResponse {
  status: string;
  user_id: string;
  authenticated: boolean;
}

/** 系统核心信息响应 */
export interface SystemCoreResponse {
  name: string;
  version: string;
  architecture: string;
  default_model: string;
  status: string;
}

/** 健康检查响应 */
export interface HealthResponse {
  status: 'ok' | 'error';
  models: string[];
  default_model: string;
  cache_age: number | null;
}

/** 详细健康检查响应 */
export interface DetailedHealthResponse {
  database: { status: string; latency_ms?: number };
  redis: { status: string; latency_ms?: number };
  models: { status: string; count: number };
  overall: string;
}

/** 就绪/存活检查响应 */
export interface ReadinessResponse {
  status: 'ready' | 'not_ready';
  message: string;
}

/** 性能统计数据 */
export interface PerformanceStats {
  requests: {
    total: number;
    success: number;
    error: number;
    avg_latency_ms: number;
  };
  system: {
    memory_percent: number;
    memory_available_mb: number;
    cpu_percent: number;
  };
  cache: {
    enabled: boolean;
    entries: number;
  };
}

/** 聊天请求 */
export interface ChatRequest {
  message: string;
  model?: string;
}

/** 聊天响应 */
export interface ChatResponse {
  response: string;
  model: string;
  status: 'ok' | 'error';
}

/** Wiki文档请求 */
export interface WikiAddRequest {
  title: string;
  content: string;
  source?: string;
  source_url?: string;
  metadata?: Record<string, any>;
}

/** Wiki文档条目 */
export interface WikiDocument {
  id: string;
  title: string;
  content: string;
  source_type: string;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
}

/** Wiki文档列表响应 */
export interface WikiListResponse {
  documents: WikiDocument[];
  total: number;
  limit: number;
  offset: number;
}

/** Wiki查询请求 */
export interface WikiQueryRequest {
  question: string;
  top_k?: number;
  generate_answer?: boolean;
}

/** Wiki搜索结果 */
export interface WikiSearchResult {
  id: string;
  title: string;
  score: number;
  snippet: string;
}

/** Wiki健康检查响应 */
export interface WikiHealthResponse {
  status: string;
  document_count: number;
  index_status: string;
}

/** API版本信息 */
export interface ApiVersionsResponse {
  current_version: string;
  api_version: string;
  supported_versions: string[];
  deprecated_versions: string[];
}

/** V2聊天请求（支持流式） */
export interface ChatRequestV2 {
  message: string;
  model?: string;
  stream?: boolean;
  context?: Record<string, any>;
}

/** V2聊天响应 */
export interface ChatResponseV2 {
  response: string;
  model: string;
  status: string;
  version: string;
  processing_time_ms?: number;
  cached: boolean;
}

/** V2核心信息响应（含特性标志） */
export interface SystemCoreV2Response extends SystemCoreResponse {
  api_version: string;
  features: {
    rate_limiting: boolean;
    audit_logging: boolean;
    signature_verification: boolean;
    ip_filtering: boolean;
    response_caching: boolean;
  };
}

/** 模型列表响应 */
export interface ModelsV2Response {
  models: string[];
  default: string;
  cache_age: number | null;
}

/** 缓存统计响应 */
export interface CacheStatsResponse {
  enabled: boolean;
  ttl: number;
  entries: number;
}

/** 根路径欢迎信息 */
export interface RootResponse {
  name: string;
  version: string;
  status: string;
  message: string;
  endpoints: Record<string, string>;
}

/** SSE消息回调类型 */
export type SSEMessageCallback = (data: string) => void;

/** 客户端配置选项 */
export interface LocalBackendConfig {
  /** FastAPI服务器基础URL，默认 http://localhost:8000 */
  baseURL?: string;
  /** 请求超时时间（毫秒），默认 30000 */
  timeout?: number;
  /** 最大重试次数，默认 3 */
  maxRetries?: number;
  /** 是否启用调试日志，默认 false */
  debug?: boolean;
}

// ==================== 错误类 ====================

/** 后端API错误 */
export class BackendError extends Error {
  constructor(
    public statusCode: number,
    public statusText: string,
    public body?: any,
  ) {
    super(`Backend Error ${statusCode}: ${statusText}`);
    this.name = 'BackendError';
  }
}

/** 网络错误 */
export class NetworkError extends Error {
  constructor(message: string, public cause?: Error) {
    super(message);
    this.name = 'NetworkError';
  }
}

/** 认证错误 */
export class AuthenticationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'AuthenticationError';
  }
}

// ==================== 主客户端类 ====================

class LocalBackendClient {
  private baseURL: string;
  private timeout: number;
  private maxRetries: number;
  private debug: boolean;
  private token: string | null = null;

  constructor(config: LocalBackendConfig = {}) {
    this.baseURL = config.baseURL || process.env.LOCAL_API_URL || 'http://localhost:8000';
    this.timeout = config.timeout || 30000;
    this.maxRetries = config.maxRetries || 3;
    this.debug = config.debug || false;
  }

  // ==================== 私有方法 ====================

  private log(...args: any[]): void {
    if (this.debug) {
      console.log('[LocalBackend]', ...args);
    }
  }

  private async request<T>(
    method: string,
    path: string,
    body?: any,
    options: RequestInit = {},
  ): Promise<T> {
    const url = `${this.baseURL}${path}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        this.log(`${method} ${url} (attempt ${attempt + 1}/${this.maxRetries + 1})`);

        const response = await fetch(url, {
          method,
          headers,
          body: body ? JSON.stringify(body) : undefined,
          signal: AbortSignal.timeout(this.timeout),
          ...options,
        });

        if (response.status === 401) {
          throw new AuthenticationError('认证失败或令牌已过期');
        }

        if (!response.ok) {
          const errorBody = await response.text().catch(() => '');
          throw new BackendError(
            response.status,
            response.statusText,
            errorBody ? JSON.parse(errorBody) : undefined,
          );
        }

        // 处理空响应
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('text/plain')) {
          return (await response.text()) as unknown as T;
        }

        return await response.json() as T;
      } catch (error) {
        lastError = error as Error;

        // 不重试认证错误和4xx错误
        if (error instanceof AuthenticationError) {
          throw error;
        }
        if (error instanceof BackendError && error.statusCode < 500) {
          throw error;
        }

        // 最后一次尝试不再等待
        if (attempt < this.maxRetries) {
          const delay = Math.min(1000 * Math.pow(2, attempt), 5000);
          this.log(`请求失败，${delay}ms后重试...`, error.message);
          await new Promise(resolve => setTimeout(resolve, delay));
        }
      }
    }

    throw lastError || new NetworkError('请求失败');
  }

  private async requestSSE(
    path: string,
    body: any,
    onMessage: SSEMessageCallback,
    onComplete?: () => void,
    onError?: (error: Error) => void,
  ): Promise<void> {
    const url = `${this.baseURL}${path}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      this.log(`POST-SSE ${url}`);

      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(this.timeout),
      });

      if (!response.ok) {
        throw new BackendError(response.status, response.statusText);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('无法获取响应流');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || trimmed.startsWith(':')) continue;

          if (trimmed.startsWith('data: ')) {
            const data = trimmed.slice(6);
            if (data === '[DONE]') {
              onComplete?.();
              return;
            }
            onMessage(data);
          }
        }
      }

      onComplete?.();
    } catch (error) {
      onError?.(error as Error);
      throw error;
    }
  }

  // ==================== 认证相关 ====================

  /**
   * 获取JWT访问令牌
   */
  async authenticate(apiKey: string, userId: string): Promise<AuthResponse> {
    const result = await this.request<AuthResponse>('POST', '/api/auth/token', {
      api_key: apiKey,
      user_id: userId,
    });
    this.token = result.access_token;
    return result;
  }

  /**
   * 验证当前令牌是否有效
   */
  async verifyAuth(): Promise<AuthVerifyResponse> {
    return this.request<AuthVerifyResponse>('GET', '/api/auth/verify');
  }

  /**
   * 设置已有的令牌（从外部存储恢复）
   */
  setToken(token: string): void {
    this.token = token;
  }

  /**
   * 清除当前令牌
   */
  clearToken(): void {
    this.token = null;
  }

  /**
   * 检查是否已认证
   */
  isAuthenticated(): boolean {
    return !!this.token;
  }

  // ==================== 系统信息 ====================

  /**
   * 获取根路径欢迎信息
   */
  async root(): Promise<RootResponse> {
    return this.request<RootResponse>('GET', '/');
  }

  /**
   * 获取系统核心信息
   */
  async coreInfo(): Promise<SystemCoreResponse> {
    return this.request<SystemCoreResponse>('GET', '/api/core');
  }

  /**
   * 获取V2版本系统核心信息（含特性标志）
   */
  async coreInfoV2(): Promise<SystemCoreV2Response> {
    return this.request<SystemCoreV2Response>('GET', '/api/v2/core');
  }

  /**
   * 获取API版本信息
   */
  async versions(): Promise<ApiVersionsResponse> {
    return this.request<ApiVersionsResponse>('GET', '/api/versions');
  }

  // ==================== 健康检查 ====================

  /**
   * 基本健康检查
   */
  async health(): Promise<HealthResponse> {
    return this.request<HealthResponse>('GET', '/api/health');
  }

  /**
   * 详细健康检查（含数据库、Redis等）
   */
  async detailedHealth(): Promise<DetailedHealthResponse> {
    return this.request<DetailedHealthResponse>('GET', '/api/health/detailed');
  }

  /**
   * V2健康检查
   */
  async healthV2(): Promise<{ status: string; version: string; api_version: string; features: string[] }> {
    return this.request('GET', '/api/v2/health');
  }

  /**
   * 就绪检查（用于K8s/readiness probe）
   */
  async readiness(): Promise<ReadinessResponse> {
    try {
      return await this.request<ReadinessResponse>('GET', '/api/ready');
    } catch (error) {
      if (error instanceof BackendError && error.statusCode === 503) {
        return { status: 'not_ready', message: '服务未就绪' };
      }
      throw error;
    }
  }

  /**
   * 存活检查（用于K8s/liveness probe）
   */
  async liveness(): Promise<{ status: string }> {
    try {
      return await this.request<{ status: string }>('GET', '/api/live');
    } catch (error) {
      if (error instanceof BackendError && error.statusCode === 503) {
        return { status: 'terminating' };
      }
      throw error;
    }
  }

  // ==================== 性能与监控 ====================

  /**
   * 获取性能统计数据
   * @param endpoint 可选：指定端点名称过滤
   */
  async performance(endpoint?: string): Promise<PerformanceStats> {
    const params = endpoint ? `?endpoint=${encodeURIComponent(endpoint)}` : '';
    return this.request<PerformanceStats>('GET', `/api/performance${params}`);
  }

  /**
   * 获取Prometheus格式指标
   */
  async metrics(): Promise<string> {
    return this.request<string>('GET', '/metrics');
  }

  // ==================== 模型管理 ====================

  /**
   * 刷新模型缓存
   */
  async refreshModels(): Promise<{ status: string; models: string[] }> {
    return this.request('POST', '/api/refresh-models');
  }

  /**
   * 获取V2模型列表
   */
  async listModelsV2(): Promise<ModelsV2Response> {
    return this.request<ModelsV2Response>('GET', '/api/v2/models');
  }

  /**
   * 获取V2缓存统计
   */
  async cacheStatsV2(): Promise<CacheStatsResponse> {
    return this.request<CacheStatsResponse>('GET', '/api/v2/cache/stats');
  }

  /**
   * 清除V2缓存
   */
  async clearCacheV2(): Promise<{ status: string }> {
    return this.request('DELETE', '/api/v2/cache');
  }

  // ==================== AI聊天 ====================

  /**
   * 发送聊天消息（非流式）
   */
  async chat(request: ChatRequest): Promise<ChatResponse> {
    return this.request<ChatResponse>('POST', '/api/chat', request);
  }

  /**
   * 发送V2聊天消息（支持流式）
   * @param request 聊天请求
   * @param onMessage 流式消息回调
   * @param onComplete 完成回调
   * @param onError 错误回调
   */
  async chatV2(
    request: ChatRequestV2,
    onMessage?: SSEMessageCallback,
    onComplete?: () => void,
    onError?: (error: Error) => void,
  ): Promise<ChatResponseV2> {
    if (request.stream && onMessage) {
      await this.requestSSE('/api/v2/chat', request, onMessage, onComplete, onError);
      return {
        response: '',
        model: request.model || 'unknown',
        status: 'ok',
        version: 'v2',
        cached: false,
      };
    }
    return this.request<ChatResponseV2>('POST', '/api/v2/chat', request);
  }

  // ==================== Wiki文档管理 ====================

  /**
   * 添加新文档到知识库
   */
  async addDocument(request: WikiAddRequest): Promise<any> {
    return this.request('POST', '/api/v1/documents', request);
  }

  /**
   * 获取单个文档详情
   */
  async getDocument(docId: string): Promise<WikiDocument> {
    return this.request<WikiDocument>(`GET`, `/api/v1/documents/${encodeURIComponent(docId)}`);
  }

  /**
   * 列出文档（支持分页和筛选）
   * @param sourceType 可选：按来源类型筛选
   * @param limit 返回数量限制，默认20
   * @param offset 偏移量，默认0
   */
  async listDocuments(sourceType?: string, limit = 20, offset = 0): Promise<WikiListResponse> {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    if (sourceType) params.set('source_type', sourceType);
    return this.request<WikiListResponse>('GET', `/api/v1/documents?${params.toString()}`);
  }

  /**
   * 语义搜索文档
   * @param query 搜索关键词
   * @param limit 返回数量，默认5
   * @param sourceType 可选：按来源类型筛选
   */
  async searchDocuments(query: string, limit = 5, sourceType?: string): Promise<WikiSearchResult[]> {
    const params = new URLSearchParams({
      q: query,
      limit: String(limit),
    });
    if (sourceType) params.set('source_type', sourceType);
    return this.request<WikiSearchResult[]>('GET', `/api/v1/search?${params.toString()}`);
  }

  /**
   * 自然语言查询文档（支持AI生成答案）
   */
  async queryDocuments(request: WikiQueryRequest): Promise<any> {
    return this.request('POST', '/api/v1/query', request);
  }

  /**
   * 删除文档
   */
  async deleteDocument(docId: string): Promise<{ status: string; doc_id: string }> {
    return this.request('DELETE', `/api/v1/documents/${encodeURIComponent(docId)}`);
  }

  /**
   * Wiki子系统健康检查
   */
  async wikiHealth(): Promise<WikiHealthResponse> {
    return this.request<WikiHealthResponse>('GET', '/api/v1/health');
  }

  // ==================== 便捷方法 ====================

  /**
   * 快速健康检查（仅返回布尔值）
   */
  async isHealthy(): Promise<boolean> {
    try {
      const result = await this.health();
      return result.status === 'ok';
    } catch {
      return false;
    }
  }

  /**
   * 获取完整的系统状态概览（聚合多个端点）
   */
  async getSystemOverview(): Promise<{
    core: SystemCoreResponse;
    health: HealthResponse;
    performance: PerformanceStats;
    wikiHealth: WikiHealthResponse | null;
  }> {
    const [core, health, performance, wikiHealth] = await Promise.all([
      this.coreInfo().catch(() => null),
      this.health().catch(() => null),
      this.performance().catch(() => null),
      this.wikiHealth().catch(() => null),
    ]);

    return {
      core: core!,
      health: health!,
      performance: performance!,
      wikiHealth,
    };
  }
}

// ==================== 单例导出 ====================

const _instance = new LocalBackendClient();

/**
 * 本地FastAPI后端客户端实例
 *
 * 使用示例：
 * ```typescript
 * import { localBackend } from './localBackend';
 *
 * // 健康检查
 * const health = await localBackend.health();
 * console.log(health.status); // "ok"
 *
 * // 聊天
 * const response = await localBackend.chat({ message: '你好' });
 * console.log(response.response);
 *
 * // Wiki文档列表
 * const docs = await localBackend.listDocuments();
 * console.log(docs.documents);
 * ```
 */
export const localBackend = _instance;

/**
 * 创建新的后端客户端实例（自定义配置）
 */
export function createLocalBackend(config: LocalBackendConfig): LocalBackendClient {
  return new LocalBackendClient(config);
}

// 导出所有类型
export type {
  AuthRequest,
  AuthResponse,
  AuthVerifyResponse,
  SystemCoreResponse,
  HealthResponse,
  DetailedHealthResponse,
  ReadinessResponse,
  PerformanceStats,
  ChatRequest,
  ChatResponse,
  WikiAddRequest,
  WikiDocument,
  WikiListResponse,
  WikiQueryRequest,
  WikiSearchResult,
  WikiHealthResponse,
  ApiVersionsResponse,
  ChatRequestV2,
  ChatResponseV2,
  SystemCoreV2Response,
  ModelsV2Response,
  CacheStatsResponse,
  RootResponse,
};
