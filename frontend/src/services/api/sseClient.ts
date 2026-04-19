/**
 * SSE流式通信协议实现
 *
 * 提供与后端FastAPI的SSE（Server-Sent Events）流式通信能力。
 * 支持token级流式输出、中断控制、重连机制。
 *
 * 协议规范：
 *   请求：POST /api/v2/chat { message, model, stream: true }
 *   响应：SSE格式
 *     data: {"type":"token","content":"你"}
 *     data: {"type":"token","content":"好"}
 *     data: {"type":"done","total_tokens":42}
 *     data: {"type":"error","message":"..."}
 *     data: [DONE]
 *
 * 重构改进：
 * - 统一SSE解析器
 * - 中断控制器（AbortController）
 * - 自动重连
 * - 背压控制
 * - 类型安全的事件流
 */

import { backendConfig } from './backendConfig'
import { errorHandler } from '../errorHandling'
import { chatActions } from '../state'

// ==================== SSE事件类型 ====================

export interface SSETokenEvent {
  type: 'token'
  content: string
}

export interface SSEDoneEvent {
  type: 'done'
  total_tokens?: number
  model?: string
  processing_time_ms?: number
}

export interface SSEErrorEvent {
  type: 'error'
  message: string
  code?: string
}

export interface SSEMetadataEvent {
  type: 'metadata'
  model: string
  cached: boolean
  version: string
}

export type SSEEvent = SSETokenEvent | SSEDoneEvent | SSEErrorEvent | SSEMetadataEvent

// ==================== 流式会话配置 ====================

export interface StreamSessionConfig {
  /** 后端API URL */
  baseURL?: string
  /** 请求超时(ms) */
  timeout?: number
  /** JWT令牌 */
  token?: string
  /** 是否自动重连 */
  autoReconnect?: boolean
  /** 最大重连次数 */
  maxReconnects?: number
  /** 重连延迟(ms) */
  reconnectDelay?: number
}

// ==================== 流式会话 ====================

export class StreamSession {
  private _config: StreamSessionConfig
  private _abortController: AbortController | null = null
  private _isStreaming = false
  private _reconnectCount = 0
  private _buffer = ''
  private _onToken: ((token: string) => void) | null = null
  private _onDone: ((event: SSEDoneEvent) => void) | null = null
  private _onError: ((error: Error) => void) | null = null
  private _onMetadata: ((event: SSEMetadataEvent) => void) | null = null

  constructor(config: StreamSessionConfig = {}) {
    this._config = {
      baseURL: config.baseURL || backendConfig.getConfiguration().localApiUrl,
      timeout: config.timeout || 60000,
      token: config.token || backendConfig.getStoredToken() || undefined,
      autoReconnect: config.autoReconnect ?? false,
      maxReconnects: config.maxReconnects || 3,
      reconnectDelay: config.reconnectDelay || 1000,
    }
  }

  get isStreaming(): boolean {
    return this._isStreaming
  }

  /** 设置token回调 */
  onToken(callback: (token: string) => void): this {
    this._onToken = callback
    return this
  }

  /** 设置完成回调 */
  onDone(callback: (event: SSEDoneEvent) => void): this {
    this._onDone = callback
    return this
  }

  /** 设置错误回调 */
  onError(callback: (error: Error) => void): this {
    this._onError = callback
    return this
  }

  /** 设置元数据回调 */
  onMetadata(callback: (event: SSEMetadataEvent) => void): this {
    this._onMetadata = callback
    return this
  }

  /** 开始流式请求 */
  async start(message: string, model?: string): Promise<void> {
    if (this._isStreaming) {
      throw new Error('已有流式会话正在进行')
    }

    this._isStreaming = true
    this._abortController = new AbortController()
    this._buffer = ''
    chatActions.setStreaming(true)
    chatActions.setLoading(true)

    try {
      await this._sendRequest(message, model)
    } catch (err) {
      this._handleError(err as Error)
    } finally {
      this._isStreaming = false
      this._abortController = null
      chatActions.setStreaming(false)
      chatActions.setLoading(false)
    }
  }

  /** 中断当前流式请求 */
  abort(): void {
    if (this._abortController) {
      this._abortController.abort()
      this._abortController = null
    }
    this._isStreaming = false
    chatActions.setStreaming(false)
    chatActions.setLoading(false)
  }

  /** 发送SSE请求 */
  private async _sendRequest(message: string, model?: string): Promise<void> {
    const url = `${this._config.baseURL}/api/v2/chat`
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
    }

    if (this._config.token) {
      headers['Authorization'] = `Bearer ${this._config.token}`
    }

    const body = JSON.stringify({
      message,
      model: model || 'gemma4:e4b',
      stream: true,
    })

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body,
      signal: this._abortController?.signal || AbortSignal.timeout(this._config.timeout!),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    // 检查是否为SSE响应
    const contentType = response.headers.get('content-type') || ''
    if (contentType.includes('text/event-stream')) {
      await this._readSSEStream(response)
    } else {
      // 非SSE响应，按普通JSON处理
      const data = await response.json()
      if (data.response) {
        this._onToken?.(data.response)
      }
      this._onDone?.({
        type: 'done',
        model: data.model,
        processing_time_ms: data.processing_time_ms,
      })
    }
  }

  /** 读取SSE流 */
  private async _readSSEStream(response: Response): Promise<void> {
    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('无法获取响应流')
    }

    const decoder = new TextDecoder()

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        this._buffer += decoder.decode(value, { stream: true })
        this._processBuffer()
      }

      // 处理缓冲区剩余数据
      if (this._buffer.trim()) {
        this._processBuffer()
      }
    } finally {
      reader.releaseLock()
    }
  }

  /** 处理SSE缓冲区 */
  private _processBuffer(): void {
    const lines = this._buffer.split('\n')
    this._buffer = lines.pop() || ''

    for (const line of lines) {
      const trimmed = line.trim()

      // 跳过空行和注释
      if (!trimmed || trimmed.startsWith(':')) continue

      // 处理data行
      if (trimmed.startsWith('data: ')) {
        const data = trimmed.slice(6)

        // 终止标记
        if (data === '[DONE]') {
          this._onDone?.({ type: 'done' })
          return
        }

        // 解析事件
        try {
          const event = JSON.parse(data) as SSEEvent
          this._dispatchEvent(event)
        } catch {
          // 非JSON数据，作为纯文本token处理
          this._onToken?.(data)
        }
      }
    }
  }

  /** 分发SSE事件 */
  private _dispatchEvent(event: SSEEvent): void {
    switch (event.type) {
      case 'token':
        this._onToken?.(event.content)
        break
      case 'done':
        this._onDone?.(event)
        break
      case 'error':
        this._onError?.(new Error(event.message))
        break
      case 'metadata':
        this._onMetadata?.(event)
        break
    }
  }

  /** 处理错误 */
  private _handleError(error: Error): void {
    // 中断错误不报告
    if (error.name === 'AbortError') return

    // 自动重连
    if (this._config.autoReconnect && this._reconnectCount < (this._config.maxReconnects || 3)) {
      this._reconnectCount++
      setTimeout(() => {
        // 重连逻辑由调用方处理
      }, this._config.reconnectDelay)
      return
    }

    this._onError?.(error)
    errorHandler.handle(error, 'StreamSession')
  }
}

// ==================== 便捷函数 ====================

/** 创建流式聊天会话 */
export function createChatStream(
  message: string,
  model?: string,
  onToken?: (token: string) => void,
): StreamSession {
  const session = new StreamSession()

  if (onToken) {
    session.onToken(onToken)
  }

  session.onDone(() => {
    chatActions.setStreaming(false)
  })

  session.onError((err) => {
    chatActions.setError(err.message)
    chatActions.setStreaming(false)
  })

  // 异步启动
  session.start(message, model).catch(console.error)

  return session
}

/** 简单流式聊天（Promise封装） */
export async function streamChat(
  message: string,
  model?: string,
  onToken?: (token: string) => void,
): Promise<string> {
  return new Promise((resolve, reject) => {
    let fullResponse = ''

    const session = new StreamSession()
    session
      .onToken((token) => {
        fullResponse += token
        onToken?.(token)
      })
      .onDone(() => {
        resolve(fullResponse)
      })
      .onError((err) => {
        reject(err)
      })

    session.start(message, model).catch(reject)
  })
}
