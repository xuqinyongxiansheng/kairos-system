/**
 * 统一错误处理系统
 *
 * 提供全局错误边界、错误分类、自动重试、
 * 错误恢复策略和用户友好的错误展示。
 *
 * 架构：
 *   组件 → ErrorBoundary → ErrorHandler → [重试/降级/上报]
 */

import { ApiError } from '../services/api/unifiedClient'
import { uiActions } from '../state'

// ==================== 错误分类 ====================

export enum ErrorCategory {
  /** 网络错误（无法连接） */
  NETWORK = 'network',
  /** 认证错误（401） */
  AUTH = 'auth',
  /** 权限错误（403） */
  FORBIDDEN = 'forbidden',
  /** 资源不存在（404） */
  NOT_FOUND = 'not_found',
  /** 请求频率限制（429） */
  RATE_LIMIT = 'rate_limit',
  /** 服务端错误（5xx） */
  SERVER = 'server',
  /** 客户端错误（4xx） */
  CLIENT = 'client',
  /** 超时错误 */
  TIMEOUT = 'timeout',
  /** 数据验证错误 */
  VALIDATION = 'validation',
  /** 未知错误 */
  UNKNOWN = 'unknown',
}

export interface ClassifiedError {
  /** 原始错误 */
  original: Error
  /** 错误分类 */
  category: ErrorCategory
  /** 用户友好消息 */
  userMessage: string
  /** 是否可重试 */
  retryable: boolean
  /** 建议的重试延迟(ms) */
  retryDelay: number
  /** 错误严重级别 */
  severity: 'low' | 'medium' | 'high' | 'critical'
  /** 建议的恢复操作 */
  recoveryAction?: ErrorRecoveryAction
}

export interface ErrorRecoveryAction {
  type: 'retry' | 'reconnect' | 'reauth' | 'dismiss' | 'navigate'
  label: string
  handler: () => void | Promise<void>
}

// ==================== 错误分类器 ====================

export function classifyError(err: unknown): ClassifiedError {
  // API错误
  if (err instanceof ApiError) {
    return classifyApiError(err)
  }

  // 标准Error
  if (err instanceof Error) {
    return classifyStandardError(err)
  }

  // 未知类型
  return {
    original: new Error(String(err)),
    category: ErrorCategory.UNKNOWN,
    userMessage: '发生未知错误',
    retryable: false,
    retryDelay: 0,
    severity: 'medium',
  }
}

function classifyApiError(err: ApiError): ClassifiedError {
  if (err.isNetworkError) {
    return {
      original: err,
      category: ErrorCategory.NETWORK,
      userMessage: '无法连接到后端服务',
      retryable: true,
      retryDelay: 3000,
      severity: 'high',
      recoveryAction: {
        type: 'retry',
        label: '重新连接',
        handler: async () => {
          const { unifiedClient } = await import('../services/api/unifiedClient')
          await unifiedClient.quickHealthCheck()
        },
      },
    }
  }

  if (err.isAuthError) {
    return {
      original: err,
      category: ErrorCategory.AUTH,
      userMessage: '认证已过期，请重新登录',
      retryable: false,
      retryDelay: 0,
      severity: 'medium',
      recoveryAction: {
        type: 'reauth',
        label: '重新登录',
        handler: () => {
          const { connectionActions } = require('../state')
          connectionActions.setAuthenticated(false)
        },
      },
    }
  }

  if (err.statusCode === 403) {
    return {
      original: err,
      category: ErrorCategory.FORBIDDEN,
      userMessage: '权限不足，无法执行此操作',
      retryable: false,
      retryDelay: 0,
      severity: 'medium',
    }
  }

  if (err.statusCode === 404) {
    return {
      original: err,
      category: ErrorCategory.NOT_FOUND,
      userMessage: '请求的资源不存在',
      retryable: false,
      retryDelay: 0,
      severity: 'low',
    }
  }

  if (err.statusCode === 429) {
    return {
      original: err,
      category: ErrorCategory.RATE_LIMIT,
      userMessage: '请求过于频繁，请稍后再试',
      retryable: true,
      retryDelay: 5000,
      severity: 'medium',
    }
  }

  if (err.isServerError) {
    return {
      original: err,
      category: ErrorCategory.SERVER,
      userMessage: '服务器内部错误，请稍后再试',
      retryable: true,
      retryDelay: 2000,
      severity: 'high',
      recoveryAction: {
        type: 'retry',
        label: '重试',
        handler: async () => {
          // 由调用方实现具体重试逻辑
        },
      },
    }
  }

  return {
    original: err,
    category: ErrorCategory.CLIENT,
    userMessage: err.getUserMessage(),
    retryable: false,
    retryDelay: 0,
    severity: 'medium',
  }
}

function classifyStandardError(err: Error): ClassifiedError {
  const message = err.message.toLowerCase()

  if (message.includes('timeout') || message.includes('aborted')) {
    return {
      original: err,
      category: ErrorCategory.TIMEOUT,
      userMessage: '请求超时，请检查网络连接',
      retryable: true,
      retryDelay: 2000,
      severity: 'medium',
    }
  }

  if (message.includes('network') || message.includes('fetch') || message.includes('econnrefused')) {
    return {
      original: err,
      category: ErrorCategory.NETWORK,
      userMessage: '网络连接失败',
      retryable: true,
      retryDelay: 3000,
      severity: 'high',
    }
  }

  if (message.includes('validation') || message.includes('invalid')) {
    return {
      original: err,
      category: ErrorCategory.VALIDATION,
      userMessage: '数据验证失败',
      retryable: false,
      retryDelay: 0,
      severity: 'low',
    }
  }

  return {
    original: err,
    category: ErrorCategory.UNKNOWN,
    userMessage: err.message || '发生未知错误',
    retryable: false,
    retryDelay: 0,
    severity: 'medium',
  }
}

// ==================== 自动重试 ====================

export interface RetryConfig {
  /** 最大重试次数 */
  maxRetries: number
  /** 初始延迟(ms) */
  initialDelay: number
  /** 最大延迟(ms) */
  maxDelay: number
  /** 退避因子 */
  backoffFactor: number
  /** 是否添加随机抖动 */
  jitter: boolean
  /** 判断是否可重试的函数 */
  retryable?: (err: ClassifiedError) => boolean
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  initialDelay: 1000,
  maxDelay: 10000,
  backoffFactor: 2,
  jitter: true,
}

export async function withRetry<T>(
  fn: () => Promise<T>,
  config: Partial<RetryConfig> = {},
): Promise<T> {
  const cfg = { ...DEFAULT_RETRY_CONFIG, ...config }
  let lastError: ClassifiedError | null = null

  for (let attempt = 0; attempt <= cfg.maxRetries; attempt++) {
    try {
      return await fn()
    } catch (err) {
      lastError = classifyError(err)

      const shouldRetry = cfg.retryable
        ? cfg.retryable(lastError)
        : lastError.retryable

      if (!shouldRetry || attempt >= cfg.maxRetries) {
        throw lastError.original
      }

      const delay = calculateDelay(attempt, cfg)
      await sleep(delay)
    }
  }

  throw lastError?.original || new Error('重试次数已耗尽')
}

function calculateDelay(attempt: number, config: RetryConfig): number {
  const base = config.initialDelay * Math.pow(config.backoffFactor, attempt)
  const capped = Math.min(base, config.maxDelay)

  if (config.jitter) {
    return capped * (0.5 + Math.random() * 0.5)
  }
  return capped
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

// ==================== 全局错误处理器 ====================

class GlobalErrorHandler {
  private _errorLog: ClassifiedError[] = []
  private _maxLogSize = 100

  /** 处理错误：分类、记录、通知 */
  handle(err: unknown, context?: string): ClassifiedError {
    const classified = classifyError(err)

    // 记录错误日志
    this.logError(classified, context)

    // 根据严重级别决定是否通知用户
    if (classified.severity === 'high' || classified.severity === 'critical') {
      this.notifyUser(classified)
    }

    return classified
  }

  /** 获取错误日志 */
  getErrorLog(): ClassifiedError[] {
    return [...this._errorLog]
  }

  /** 清除错误日志 */
  clearLog(): void {
    this._errorLog = []
  }

  private logError(error: ClassifiedError, context?: string): void {
    const entry = {
      ...error,
      original: error.original,
      context,
    }

    this._errorLog.unshift(entry)
    if (this._errorLog.length > this._maxLogSize) {
      this._errorLog = this._errorLog.slice(0, this._maxLogSize)
    }

    // 控制台输出
    const prefix = context ? `[${context}]` : ''
    console.error(
      `[ErrorHandler]${prefix} ${error.category} (${error.severity}): ${error.userMessage}`,
      error.original,
    )
  }

  private notifyUser(error: ClassifiedError): void {
    try {
      uiActions.addNotification({
        type: error.severity === 'critical' ? 'error' : 'warning',
        message: error.userMessage,
        autoDismiss: error.severity !== 'critical',
      })
    } catch {
      // 通知系统可能不可用
    }
  }
}

export const errorHandler = new GlobalErrorHandler()

// ==================== 安全执行包装 ====================

/** 安全执行异步函数，自动处理错误 */
export async function safeExecute<T>(
  fn: () => Promise<T>,
  fallback?: T,
  context?: string,
): Promise<T | undefined> {
  try {
    return await fn()
  } catch (err) {
    errorHandler.handle(err, context)
    return fallback
  }
}

/** 安全执行同步函数，自动处理错误 */
export function safeExecuteSync<T>(
  fn: () => T,
  fallback?: T,
  context?: string,
): T | undefined {
  try {
    return fn()
  } catch (err) {
    errorHandler.handle(err, context)
    return fallback
  }
}
