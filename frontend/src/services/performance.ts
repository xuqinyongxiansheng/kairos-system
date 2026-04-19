/**
 * 前端性能优化模块
 *
 * 提供：
 * - 请求缓存（内存 + TTL）
 * - 请求去重（避免重复请求）
 * - 性能指标收集
 * - 防抖/节流工具
 */

// ==================== 请求缓存 ====================

interface CacheEntry<T> {
  data: T
  timestamp: number
  ttl: number
}

export class RequestCache {
  private _cache = new Map<string, CacheEntry<any>>()
  private _maxSize: number

  constructor(maxSize = 100) {
    this._maxSize = maxSize
  }

  /** 获取缓存 */
  get<T>(key: string): T | null {
    const entry = this._cache.get(key)
    if (!entry) return null

    // 检查TTL
    if (Date.now() - entry.timestamp > entry.ttl) {
      this._cache.delete(key)
      return null
    }

    return entry.data as T
  }

  /** 设置缓存 */
  set<T>(key: string, data: T, ttl = 30000): void {
    // 超出最大容量时清理过期条目
    if (this._cache.size >= this._maxSize) {
      this.evictExpired()
    }

    this._cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl,
    })
  }

  /** 检查缓存是否存在且有效 */
  has(key: string): boolean {
    return this.get(key) !== null
  }

  /** 删除缓存条目 */
  delete(key: string): boolean {
    return this._cache.delete(key)
  }

  /** 清除所有缓存 */
  clear(): void {
    this._cache.clear()
  }

  /** 获取缓存统计 */
  getStats(): { size: number; maxSize: number; hitRate: number } {
    return {
      size: this._cache.size,
      maxSize: this._maxSize,
      hitRate: this._hits / (this._hits + this._misses) || 0,
    }
  }

  private _hits = 0
  private _misses = 0

  /** 带统计的获取 */
  getWithStats<T>(key: string): T | null {
    const result = this.get<T>(key)
    if (result !== null) {
      this._hits++
    } else {
      this._misses++
    }
    return result
  }

  /** 清理过期条目 */
  private evictExpired(): void {
    const now = Date.now()
    for (const [key, entry] of this._cache.entries()) {
      if (now - entry.timestamp > entry.ttl) {
        this._cache.delete(key)
      }
    }
  }
}

/** 全局请求缓存实例 */
export const requestCache = new RequestCache()

// ==================== 请求去重 ====================

const pendingRequests = new Map<string, Promise<any>>()

/** 去重请求包装器 - 相同key的并发请求只执行一次 */
export async function deduplicatedRequest<T>(
  key: string,
  fn: () => Promise<T>,
  cacheTTL?: number,
): Promise<T> {
  // 检查缓存
  if (cacheTTL) {
    const cached = requestCache.getWithStats<T>(key)
    if (cached !== null) return cached
  }

  // 检查是否有进行中的相同请求
  const pending = pendingRequests.get(key)
  if (pending) return pending as Promise<T>

  // 发起新请求
  const promise = fn().then((result) => {
    pendingRequests.delete(key)
    if (cacheTTL) {
      requestCache.set(key, result, cacheTTL)
    }
    return result
  }).catch((err) => {
    pendingRequests.delete(key)
    throw err
  })

  pendingRequests.set(key, promise)
  return promise
}

// ==================== 性能指标 ====================

export interface PerformanceMetric {
  name: string
  startTime: number
  endTime: number
  duration: number
  metadata?: Record<string, any>
}

class PerformanceMonitor {
  private _metrics: PerformanceMetric[] = []
  private _maxMetrics = 500
  private _activeTimers = new Map<string, number>()

  /** 开始计时 */
  startTimer(name: string): void {
    this._activeTimers.set(name, Date.now())
  }

  /** 结束计时并记录 */
  endTimer(name: string, metadata?: Record<string, any>): PerformanceMetric | null {
    const startTime = this._activeTimers.get(name)
    if (!startTime) return null

    this._activeTimers.delete(name)
    const endTime = Date.now()
    const metric: PerformanceMetric = {
      name,
      startTime,
      endTime,
      duration: endTime - startTime,
      metadata,
    }

    this._metrics.push(metric)
    if (this._metrics.length > this._maxMetrics) {
      this._metrics = this._metrics.slice(-this._maxMetrics)
    }

    return metric
  }

  /** 包装异步函数，自动计时 */
  async measure<T>(name: string, fn: () => Promise<T>): Promise<T> {
    this.startTimer(name)
    try {
      const result = await fn()
      this.endTimer(name, { success: true })
      return result
    } catch (err) {
      this.endTimer(name, { success: false, error: String(err) })
      throw err
    }
  }

  /** 获取所有指标 */
  getMetrics(): PerformanceMetric[] {
    return [...this._metrics]
  }

  /** 获取指定名称的指标 */
  getMetricsByName(name: string): PerformanceMetric[] {
    return this._metrics.filter(m => m.name === name)
  }

  /** 获取平均耗时 */
  getAverageDuration(name: string): number {
    const metrics = this.getMetricsByName(name)
    if (metrics.length === 0) return 0
    return metrics.reduce((sum, m) => sum + m.duration, 0) / metrics.length
  }

  /** 获取P95耗时 */
  getP95Duration(name: string): number {
    const metrics = this.getMetricsByName(name)
    if (metrics.length === 0) return 0
    const sorted = metrics.map(m => m.duration).sort((a, b) => a - b)
    const idx = Math.ceil(sorted.length * 0.95) - 1
    return sorted[idx] || 0
  }

  /** 清除所有指标 */
  clear(): void {
    this._metrics = []
    this._activeTimers.clear()
  }

  /** 生成性能摘要 */
  getSummary(): Record<string, { count: number; avgMs: number; p95Ms: number; maxMs: number }> {
    const names = new Set(this._metrics.map(m => m.name))
    const summary: Record<string, any> = {}

    for (const name of names) {
      const metrics = this.getMetricsByName(name)
      const durations = metrics.map(m => m.duration)
      summary[name] = {
        count: metrics.length,
        avgMs: Math.round(this.getAverageDuration(name)),
        p95Ms: Math.round(this.getP95Duration(name)),
        maxMs: Math.max(...durations),
      }
    }

    return summary
  }
}

export const perfMonitor = new PerformanceMonitor()

// ==================== 防抖/节流 ====================

/** 防抖函数 */
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number,
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout> | null = null

  return function (this: any, ...args: Parameters<T>) {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      fn.apply(this, args)
      timer = null
    }, delay)
  }
}

/** 节流函数 */
export function throttle<T extends (...args: any[]) => any>(
  fn: T,
  interval: number,
): (...args: Parameters<T>) => void {
  let lastTime = 0
  let timer: ReturnType<typeof setTimeout> | null = null

  return function (this: any, ...args: Parameters<T>) {
    const now = Date.now()
    const remaining = interval - (now - lastTime)

    if (remaining <= 0) {
      if (timer) {
        clearTimeout(timer)
        timer = null
      }
      fn.apply(this, args)
      lastTime = now
    } else if (!timer) {
      timer = setTimeout(() => {
        fn.apply(this, args)
        lastTime = Date.now()
        timer = null
      }, remaining)
    }
  }
}
