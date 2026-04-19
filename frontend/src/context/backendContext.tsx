/**
 * 后端状态React Context（重构版）
 *
 * 基于统一API客户端和集中式状态管理，
 * 提供全局后端连接状态、认证状态、健康状态等。
 *
 * 重构改进：
 * - 使用 unifiedClient 替代直接调用 localBackend
 * - 集成状态管理分片（connectionStore/systemStore）
 * - 统一错误处理（errorHandler）
 * - 自动重连和健康检查
 * - SSE流式通信支持
 */

import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react'
import { unifiedClient, type ConnectionStatus } from '../services/api/unifiedClient'
import { backendConfig, BackendMode, type BackendConfiguration } from '../services/api/backendConfig'
import { errorHandler, safeExecute, withRetry } from '../services/errorHandling'
import {
  connectionStore,
  systemStore,
  connectionActions,
  systemActions,
  type SystemCoreResponse,
  type HealthResponse,
  type PerformanceStats,
} from '../state'

// ==================== Context类型定义 ====================

interface BackendContextValue {
  config: BackendConfiguration
  connectionStatus: ConnectionStatus
  coreInfo: SystemCoreResponse | null
  health: HealthResponse | null
  performance: PerformanceStats | null
  isLoading: boolean
  error: Error | null

  switchMode: (mode: BackendMode) => Promise<void>
  refreshHealth: () => Promise<void>
  refreshCoreInfo: () => Promise<void>
  refreshPerformance: () => Promise<void>
  refreshAll: () => Promise<void>
  authenticate: (apiKey: string, userId: string) => Promise<void>
  logout: () => void
  reconnect: () => Promise<void>
}

// ==================== 创建Context ====================

const BackendContext = createContext<BackendContextValue | undefined>(undefined)

// ==================== Provider组件 ====================

interface BackendProviderProps {
  children: React.ReactNode
}

export function BackendProvider({ children }: BackendProviderProps): JSX.Element {
  const [config, setConfig] = useState<BackendConfiguration>(() =>
    backendConfig.getConfiguration(),
  )
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('checking')
  const [coreInfo, setCoreInfo] = useState<SystemCoreResponse | null>(null)
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [performance, setPerformance] = useState<PerformanceStats | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const refreshTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 监听配置变更
  useEffect(() => {
    const unsubscribe = backendConfig.addListener((newConfig) => {
      setConfig(newConfig)
    })
    return unsubscribe
  }, [])

  // 监听连接状态变更
  useEffect(() => {
    const unsubscribe = unifiedClient.onStatusChange((status) => {
      setConnectionStatus(status)
      connectionActions.setStatus(status)
    })
    return unsubscribe
  }, [])

  // 初始数据加载
  useEffect(() => {
    if (config.mode === BackendMode.LOCAL) {
      refreshAll()
      startAutoRefresh()
    }
    return () => stopAutoRefresh()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config.mode])

  /** 启动自动刷新（每30秒） */
  const startAutoRefresh = useCallback(() => {
    stopAutoRefresh()
    refreshTimerRef.current = setInterval(() => {
      refreshHealth().catch(() => { /* 静默失败 */ })
    }, 30000)
  }, [])

  /** 停止自动刷新 */
  const stopAutoRefresh = useCallback(() => {
    if (refreshTimerRef.current) {
      clearInterval(refreshTimerRef.current)
      refreshTimerRef.current = null
    }
  }, [])

  /** 刷新所有数据 */
  const refreshAll = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    systemActions.setLoading(true)

    try {
      const [healthRes, coreRes, perfRes] = await Promise.all([
        unifiedClient.health('init').catch(err => {
          errorHandler.handle(err, 'health')
          return null
        }),
        unifiedClient.coreInfo('init').catch(err => {
          errorHandler.handle(err, 'coreInfo')
          return null
        }),
        unifiedClient.performance('init').catch(err => {
          errorHandler.handle(err, 'performance')
          return null
        }),
      ])

      if (healthRes) {
        setHealth(healthRes.data)
        systemActions.setHealth(healthRes.data)
      }
      if (coreRes) {
        setCoreInfo(coreRes.data)
        systemActions.setCoreInfo(coreRes.data)
      }
      if (perfRes) {
        setPerformance(perfRes.data)
        systemActions.setPerformance(perfRes.data)
      }
    } catch (err) {
      const classified = errorHandler.handle(err, 'refreshAll')
      setError(classified.original)
      systemActions.setError(classified.userMessage)
    } finally {
      setIsLoading(false)
      systemActions.setLoading(false)
    }
  }, [])

  /** 切换模式 */
  const switchMode = useCallback(async (mode: BackendMode) => {
    setIsLoading(true)
    setError(null)
    try {
      await backendConfig.switchMode(mode)
      connectionActions.setMode(mode)

      if (mode === BackendMode.LOCAL) {
        await refreshAll()
        startAutoRefresh()
      } else {
        setCoreInfo(null)
        setHealth(null)
        setPerformance(null)
        systemActions.reset()
        stopAutoRefresh()
      }
    } catch (err) {
      const classified = errorHandler.handle(err, 'switchMode')
      setError(classified.original)
    } finally {
      setIsLoading(false)
    }
  }, [refreshAll, startAutoRefresh, stopAutoRefresh])

  /** 刷新健康状态 */
  const refreshHealth = useCallback(async () => {
    try {
      const result = await unifiedClient.health('manual')
      setHealth(result.data)
      systemActions.setHealth(result.data)
      connectionActions.setLatency(result.latencyMs)
      await backendConfig.checkHealth()
    } catch (err) {
      errorHandler.handle(err, 'refreshHealth')
    }
  }, [])

  /** 刷新核心信息 */
  const refreshCoreInfo = useCallback(async () => {
    try {
      const result = await unifiedClient.coreInfo('manual')
      setCoreInfo(result.data)
      systemActions.setCoreInfo(result.data)
    } catch (err) {
      errorHandler.handle(err, 'refreshCoreInfo')
    }
  }, [])

  /** 刷新性能统计 */
  const refreshPerformance = useCallback(async () => {
    try {
      const result = await unifiedClient.performance('manual')
      setPerformance(result.data)
      systemActions.setPerformance(result.data)
    } catch (err) {
      errorHandler.handle(err, 'refreshPerformance')
    }
  }, [])

  /** 认证 */
  const authenticate = useCallback(async (apiKey: string, userId: string) => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await unifiedClient.authenticate(apiKey, userId, 'login')
      connectionActions.setAuthenticated(true)
      await refreshAll()
    } catch (err) {
      const classified = errorHandler.handle(err, 'authenticate')
      setError(classified.original)
      throw classified.original
    } finally {
      setIsLoading(false)
    }
  }, [refreshAll])

  /** 登出 */
  const logout = useCallback(() => {
    backendConfig.clearStoredToken()
    connectionActions.setAuthenticated(false)
    setCoreInfo(null)
    setHealth(null)
    setPerformance(null)
    systemActions.reset()
  }, [])

  /** 重新连接 */
  const reconnect = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      await withRetry(
        () => unifiedClient.quickHealthCheck(),
        { maxRetries: 3, initialDelay: 1000 },
      )
      await refreshAll()
    } catch (err) {
      const classified = errorHandler.handle(err, 'reconnect')
      setError(classified.original)
    } finally {
      setIsLoading(false)
    }
  }, [refreshAll])

  const value: BackendContextValue = {
    config,
    connectionStatus,
    coreInfo,
    health,
    performance,
    isLoading,
    error,
    switchMode,
    refreshHealth,
    refreshCoreInfo,
    refreshPerformance,
    refreshAll,
    authenticate,
    logout,
    reconnect,
  }

  return (
    <BackendContext.Provider value={value}>
      {children}
    </BackendContext.Provider>
  )
}

// ==================== Hook ====================

export function useBackend(): BackendContextValue {
  const context = useContext(BackendContext)
  if (context === undefined) {
    throw new Error('useBackend must be used within a BackendProvider')
  }
  return context
}

export default BackendContext
