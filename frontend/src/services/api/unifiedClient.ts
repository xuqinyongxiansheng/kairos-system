/**
 * 统一API通信层
 *
 * 抽象LOCAL/CLOUD双通道，提供单一入口点进行所有API调用。
 * 自动路由请求到正确的后端，处理认证、重试、错误转换。
 *
 * 架构：
 *   组件 → unifiedClient → [LOCAL: localBackend.ts → FastAPI]
 *                           [CLOUD: claude.ts → Anthropic API]
 */

import {
  localBackend,
  BackendError,
  NetworkError,
  AuthenticationError,
  type ChatRequest,
  type ChatResponse,
  type ChatRequestV2,
  type ChatResponseV2,
  type HealthResponse,
  type SystemCoreResponse,
  type PerformanceStats,
  type WikiAddRequest,
  type WikiDocument,
  type WikiListResponse,
  type WikiSearchResult,
  type WikiQueryRequest,
  type WikiHealthResponse,
  type AuthResponse,
  type AuthVerifyResponse,
  type ModelsV2Response,
  type CacheStatsResponse,
  type SSEMessageCallback,
} from './localBackend'
import { backendConfig, BackendMode } from './backendConfig'

// ==================== 通信协议类型 ====================

/** 统一请求上下文 */
export interface RequestContext {
  /** 请求唯一ID */
  requestId: string
  /** 请求时间戳 */
  timestamp: number
  /** 目标模式 */
  mode: BackendMode
  /** 请求来源 */
  source: string
}

/** 统一响应包装 */
export interface UnifiedResponse<T> {
  /** 响应数据 */
  data: T
  /** 是否来自缓存 */
  cached: boolean
  /** 响应延迟(ms) */
  latencyMs: number
  /** 请求上下文 */
  context: RequestContext
  /** 使用的后端模式 */
  mode: BackendMode
}

/** 流式消息事件 */
export interface StreamEvent {
  /** 事件类型 */
  type: 'token' | 'done' | 'error' | 'metadata'
  /** 事件数据 */
  data: string
  /** 时间戳 */
  timestamp: number
}

/** 连接状态 */
export type ConnectionStatus = 'connected' | 'disconnected' | 'checking' | 'error'

/** 连接状态变更回调 */
export type ConnectionStatusCallback = (status: ConnectionStatus) => void

// ==================== 统一API客户端 ====================

class UnifiedApiClient {
  private _connectionStatus: ConnectionStatus = 'checking'
  private _statusListeners: ConnectionStatusCallback[] = []
  private _requestCount = 0
  private _lastError: Error | null = null

  // ==================== 连接状态管理 ====================

  get connectionStatus(): ConnectionStatus {
    return this._connectionStatus
  }

  get lastError(): Error | null {
    return this._lastError
  }

  onStatusChange(callback: ConnectionStatusCallback): () => void {
    this._statusListeners.push(callback)
    return () => {
      this._statusListeners = this._statusListeners.filter(cb => cb !== callback)
    }
  }

  private setConnectionStatus(status: ConnectionStatus): void {
    const prev = this._connectionStatus
    this._connectionStatus = status
    if (prev !== status) {
      this._statusListeners.forEach(cb => {
        try { cb(status) } catch { /* 忽略回调错误 */ }
      })
    }
  }

  // ==================== 请求上下文 ====================

  private createRequestContext(source: string): RequestContext {
    return {
      requestId: `req_${Date.now()}_${++this._requestCount}`,
      timestamp: Date.now(),
      mode: backendConfig.getConfiguration().mode,
      source,
    }
  }

  private wrapResponse<T>(
    data: T,
    context: RequestContext,
    startTime: number,
    cached = false,
  ): UnifiedResponse<T> {
    return {
      data,
      cached,
      latencyMs: Date.now() - startTime,
      context,
      mode: context.mode,
    }
  }

  // ==================== 核心API方法 ====================

  /** 健康检查 */
  async health(source = 'unified'): Promise<UnifiedResponse<HealthResponse>> {
    const ctx = this.createRequestContext(source)
    const start = Date.now()
    this.setConnectionStatus('checking')

    try {
      const data = await localBackend.health()
      this.setConnectionStatus('connected')
      this._lastError = null
      return this.wrapResponse(data, ctx, start)
    } catch (err) {
      this._lastError = err as Error
      this.setConnectionStatus('error')
      throw this.transformError(err)
    }
  }

  /** 系统核心信息 */
  async coreInfo(source = 'unified'): Promise<UnifiedResponse<SystemCoreResponse>> {
    const ctx = this.createRequestContext(source)
    const start = Date.now()

    try {
      const data = await localBackend.coreInfo()
      return this.wrapResponse(data, ctx, start)
    } catch (err) {
      throw this.transformError(err)
    }
  }

  /** 性能统计 */
  async performance(source = 'unified'): Promise<UnifiedResponse<PerformanceStats>> {
    const ctx = this.createRequestContext(source)
    const start = Date.now()

    try {
      const data = await localBackend.performance()
      return this.wrapResponse(data, ctx, start)
    } catch (err) {
      throw this.transformError(err)
    }
  }

  /** 聊天（非流式） */
  async chat(
    request: ChatRequest,
    source = 'chat',
  ): Promise<UnifiedResponse<ChatResponse>> {
    const ctx = this.createRequestContext(source)
    const start = Date.now()

    try {
      const data = await localBackend.chat(request)
      return this.wrapResponse(data, ctx, start)
    } catch (err) {
      throw this.transformError(err)
    }
  }

  /** 聊天（流式SSE） */
  async chatStream(
    request: ChatRequestV2,
    onToken: (token: string) => void,
    onDone?: () => void,
    source = 'chat-stream',
  ): Promise<void> {
    const ctx = this.createRequestContext(source)

    try {
      await localBackend.chatV2(
        { ...request, stream: true },
        (data) => {
          try {
            const parsed = JSON.parse(data)
            if (parsed.token) {
              onToken(parsed.token)
            } else if (parsed.text) {
              onToken(parsed.text)
            } else {
              onToken(data)
            }
          } catch {
            onToken(data)
          }
        },
        onDone,
        (err) => {
          this._lastError = err
          throw this.transformError(err)
        },
      )
    } catch (err) {
      throw this.transformError(err)
    }
  }

  /** 认证 */
  async authenticate(
    apiKey: string,
    userId: string,
    source = 'auth',
  ): Promise<UnifiedResponse<AuthResponse>> {
    const ctx = this.createRequestContext(source)
    const start = Date.now()

    try {
      const data = await localBackend.authenticate(apiKey, userId)
      backendConfig.storeToken(data.access_token)
      return this.wrapResponse(data, ctx, start)
    } catch (err) {
      throw this.transformError(err)
    }
  }

  /** 验证认证 */
  async verifyAuth(source = 'auth'): Promise<UnifiedResponse<AuthVerifyResponse>> {
    const ctx = this.createRequestContext(source)
    const start = Date.now()

    try {
      const data = await localBackend.verifyAuth()
      return this.wrapResponse(data, ctx, start)
    } catch (err) {
      throw this.transformError(err)
    }
  }

  // ==================== Wiki文档管理 ====================

  /** 添加文档 */
  async addDocument(
    request: WikiAddRequest,
    source = 'wiki',
  ): Promise<UnifiedResponse<any>> {
    const ctx = this.createRequestContext(source)
    const start = Date.now()

    try {
      const data = await localBackend.addDocument(request)
      return this.wrapResponse(data, ctx, start)
    } catch (err) {
      throw this.transformError(err)
    }
  }

  /** 获取文档 */
  async getDocument(
    docId: string,
    source = 'wiki',
  ): Promise<UnifiedResponse<WikiDocument>> {
    const ctx = this.createRequestContext(source)
    const start = Date.now()

    try {
      const data = await localBackend.getDocument(docId)
      return this.wrapResponse(data, ctx, start)
    } catch (err) {
      throw this.transformError(err)
    }
  }

  /** 文档列表 */
  async listDocuments(
    sourceType?: string,
    limit = 20,
    offset = 0,
    source = 'wiki',
  ): Promise<UnifiedResponse<WikiListResponse>> {
    const ctx = this.createRequestContext(source)
    const start = Date.now()

    try {
      const data = await localBackend.listDocuments(sourceType, limit, offset)
      return this.wrapResponse(data, ctx, start)
    } catch (err) {
      throw this.transformError(err)
    }
  }

  /** 搜索文档 */
  async searchDocuments(
    query: string,
    limit = 5,
    sourceType?: string,
    source = 'wiki',
  ): Promise<UnifiedResponse<WikiSearchResult[]>> {
    const ctx = this.createRequestContext(source)
    const start = Date.now()

    try {
      const data = await localBackend.searchDocuments(query, limit, sourceType)
      return this.wrapResponse(data, ctx, start)
    } catch (err) {
      throw this.transformError(err)
    }
  }

  /** 查询文档（AI生成答案） */
  async queryDocuments(
    request: WikiQueryRequest,
    source = 'wiki',
  ): Promise<UnifiedResponse<any>> {
    const ctx = this.createRequestContext(source)
    const start = Date.now()

    try {
      const data = await localBackend.queryDocuments(request)
      return this.wrapResponse(data, ctx, start)
    } catch (err) {
      throw this.transformError(err)
    }
  }

  /** 删除文档 */
  async deleteDocument(
    docId: string,
    source = 'wiki',
  ): Promise<UnifiedResponse<{ status: string; doc_id: string }>> {
    const ctx = this.createRequestContext(source)
    const start = Date.now()

    try {
      const data = await localBackend.deleteDocument(docId)
      return this.wrapResponse(data, ctx, start)
    } catch (err) {
      throw this.transformError(err)
    }
  }

  /** Wiki健康检查 */
  async wikiHealth(source = 'wiki'): Promise<UnifiedResponse<WikiHealthResponse>> {
    const ctx = this.createRequestContext(source)
    const start = Date.now()

    try {
      const data = await localBackend.wikiHealth()
      return this.wrapResponse(data, ctx, start)
    } catch (err) {
      throw this.transformError(err)
    }
  }

  // ==================== 模型与缓存 ====================

  /** 获取模型列表 */
  async listModels(source = 'models'): Promise<UnifiedResponse<ModelsV2Response>> {
    const ctx = this.createRequestContext(source)
    const start = Date.now()

    try {
      const data = await localBackend.listModelsV2()
      return this.wrapResponse(data, ctx, start)
    } catch (err) {
      throw this.transformError(err)
    }
  }

  /** 刷新模型缓存 */
  async refreshModels(source = 'models'): Promise<UnifiedResponse<{ status: string; models: string[] }>> {
    const ctx = this.createRequestContext(source)
    const start = Date.now()

    try {
      const data = await localBackend.refreshModels()
      return this.wrapResponse(data, ctx, start)
    } catch (err) {
      throw this.transformError(err)
    }
  }

  /** 缓存统计 */
  async cacheStats(source = 'cache'): Promise<UnifiedResponse<CacheStatsResponse>> {
    const ctx = this.createRequestContext(source)
    const start = Date.now()

    try {
      const data = await localBackend.cacheStatsV2()
      return this.wrapResponse(data, ctx, start)
    } catch (err) {
      throw this.transformError(err)
    }
  }

  /** 清除缓存 */
  async clearCache(source = 'cache'): Promise<UnifiedResponse<{ status: string }>> {
    const ctx = this.createRequestContext(source)
    const start = Date.now()

    try {
      const data = await localBackend.clearCacheV2()
      return this.wrapResponse(data, ctx, start)
    } catch (err) {
      throw this.transformError(err)
    }
  }

  // ==================== 聚合查询 ====================

  /** 获取完整系统概览 */
  async getSystemOverview(source = 'overview') {
    const ctx = this.createRequestContext(source)
    const start = Date.now()

    try {
      const data = await localBackend.getSystemOverview()
      return this.wrapResponse(data, ctx, start)
    } catch (err) {
      throw this.transformError(err)
    }
  }

  /** 快速连接测试 */
  async quickHealthCheck(): Promise<boolean> {
    try {
      const result = await localBackend.isHealthy()
      this.setConnectionStatus(result ? 'connected' : 'disconnected')
      return result
    } catch {
      this.setConnectionStatus('error')
      return false
    }
  }

  // ==================== 错误转换 ====================

  private transformError(err: unknown): Error {
    if (err instanceof BackendError) {
      return new ApiError(
        err.statusCode,
        err.statusText,
        err.body,
        'BACKEND_ERROR',
      )
    }
    if (err instanceof NetworkError) {
      this.setConnectionStatus('error')
      return new ApiError(0, '网络不可达', err.message, 'NETWORK_ERROR')
    }
    if (err instanceof AuthenticationError) {
      return new ApiError(401, '认证失败', err.message, 'AUTH_ERROR')
    }
    if (err instanceof Error) {
      this._lastError = err
      return new ApiError(500, '未知错误', err.message, 'UNKNOWN_ERROR')
    }
    return new ApiError(500, '未知错误', String(err), 'UNKNOWN_ERROR')
  }
}

// ==================== 统一API错误类 ====================

export class ApiError extends Error {
  constructor(
    public readonly statusCode: number,
    public readonly statusText: string,
    public readonly detail?: any,
    public readonly code: string = 'API_ERROR',
  ) {
    super(`[${code}] ${statusCode} ${statusText}`)
    this.name = 'ApiError'
  }

  /** 是否为网络错误 */
  get isNetworkError(): boolean {
    return this.code === 'NETWORK_ERROR' || this.statusCode === 0
  }

  /** 是否为认证错误 */
  get isAuthError(): boolean {
    return this.code === 'AUTH_ERROR' || this.statusCode === 401
  }

  /** 是否为服务端错误 */
  get isServerError(): boolean {
    return this.statusCode >= 500
  }

  /** 是否可重试 */
  get isRetryable(): boolean {
    return this.isNetworkError || this.isServerError
  }

  /** 获取用户友好的错误消息 */
  getUserMessage(): string {
    switch (this.code) {
      case 'NETWORK_ERROR':
        return '无法连接到后端服务，请检查网络连接和服务状态'
      case 'AUTH_ERROR':
        return '认证失败，请重新登录'
      case 'BACKEND_ERROR':
        if (this.statusCode === 404) return '请求的资源不存在'
        if (this.statusCode === 429) return '请求过于频繁，请稍后再试'
        if (this.statusCode >= 500) return '服务器内部错误，请稍后再试'
        return `请求失败: ${this.statusText}`
      default:
        return '发生未知错误'
    }
  }
}

// ==================== 单例导出 ====================

export const unifiedClient = new UnifiedApiClient()
export default unifiedClient
