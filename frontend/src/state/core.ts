/**
 * 集中式状态管理器
 *
 * 轻量级响应式状态管理，基于发布-订阅模式。
 * 提供分片状态管理、派生状态计算、状态持久化等能力。
 *
 * 设计原则：
 * - 单一数据源：每个状态分片有唯一Store
 * - 只读状态：外部只能通过dispatch修改状态
 * - 响应式更新：状态变更自动通知订阅者
 * - 类型安全：完整的TypeScript类型推导
 */

// ==================== 核心类型 ====================

/** 状态变更监听器 */
export type Listener<T> = (state: T, prevState: T) => void

/** 状态变更订阅取消函数 */
export type Unsubscribe = () => void

/** 状态分片配置 */
export interface StoreConfig<T> {
  /** 分片名称 */
  name: string
  /** 初始状态 */
  initialState: T
  /** 是否持久化到localStorage */
  persist?: boolean
  /** localStorage键名（默认使用name） */
  storageKey?: string
  /** 状态比较函数，用于判断是否需要通知 */
  equals?: (a: T, b: T) => boolean
}

// ==================== Store实现 ====================

export class Store<T> {
  private _state: T
  private _listeners: Set<Listener<T>> = new Set()
  private _config: StoreConfig<T>
  private _equals: (a: T, b: T) => boolean

  constructor(config: StoreConfig<T>) {
    this._config = config
    this._equals = config.equals || this.defaultEquals

    // 尝试从持久化存储恢复状态
    const persisted = config.persist ? this.loadFromStorage() : undefined
    this._state = persisted !== undefined ? persisted : config.initialState
  }

  /** 获取当前状态（只读快照） */
  get state(): T {
    return this._state
  }

  /** 获取分片名称 */
  get name(): string {
    return this._config.name
  }

  /** 设置新状态 */
  setState(updater: T | ((prev: T) => T)): void {
    const prev = this._state
    const next = typeof updater === 'function'
      ? (updater as (prev: T) => T)(prev)
      : updater

    if (!this._equals(prev, next)) {
      this._state = next
      this.notifyListeners(prev)
      if (this._config.persist) {
        this.saveToStorage(next)
      }
    }
  }

  /** 订阅状态变更 */
  subscribe(listener: Listener<T>): Unsubscribe {
    this._listeners.add(listener)
    return () => {
      this._listeners.delete(listener)
    }
  }

  /** 获取当前状态的只读快照（用于React Hook） */
  snapshot(): T {
    return this._state
  }

  /** 重置到初始状态 */
  reset(): void {
    const prev = this._state
    this._state = this._config.initialState
    if (!this._equals(prev, this._state)) {
      this.notifyListeners(prev)
      if (this._config.persist) {
        this.clearStorage()
      }
    }
  }

  /** 销毁Store，清理所有监听器 */
  destroy(): void {
    this._listeners.clear()
    if (this._config.persist) {
      this.clearStorage()
    }
  }

  // ==================== 私有方法 ====================

  private notifyListeners(prevState: T): void {
    const currentState = this._state
    this._listeners.forEach(listener => {
      try {
        listener(currentState, prevState)
      } catch (err) {
        console.error(`[Store:${this._config.name}] 监听器执行失败:`, err)
      }
    })
  }

  private defaultEquals(a: T, b: T): boolean {
    return a === b
  }

  private loadFromStorage(): T | undefined {
    try {
      if (typeof window === 'undefined' || !window.localStorage) return undefined
      const key = this._config.storageKey || `store_${this._config.name}`
      const raw = window.localStorage.getItem(key)
      if (raw) return JSON.parse(raw)
    } catch {
      // 忽略存储读取错误
    }
    return undefined
  }

  private saveToStorage(state: T): void {
    try {
      if (typeof window === 'undefined' || !window.localStorage) return
      const key = this._config.storageKey || `store_${this._config.name}`
      window.localStorage.setItem(key, JSON.stringify(state))
    } catch {
      // 忽略存储写入错误
    }
  }

  private clearStorage(): void {
    try {
      if (typeof window === 'undefined' || !window.localStorage) return
      const key = this._config.storageKey || `store_${this._config.name}`
      window.localStorage.removeItem(key)
    } catch {
      // 忽略
    }
  }
}

// ==================== 派生状态 ====================

export class DerivedStore<T, S> {
  private _store: Store<S>
  private _selector: (state: S) => T
  private _listeners: Set<Listener<T>> = new Set()
  private _cachedValue: T

  constructor(store: Store<S>, selector: (state: S) => T) {
    this._store = store
    this._selector = selector
    this._cachedValue = selector(store.state)

    store.subscribe((state) => {
      const newValue = this._selector(state)
      if (newValue !== this._cachedValue) {
        const prev = this._cachedValue
        this._cachedValue = newValue
        this.notifyListeners(prev)
      }
    })
  }

  get state(): T {
    return this._cachedValue
  }

  subscribe(listener: Listener<T>): Unsubscribe {
    this._listeners.add(listener)
    return () => {
      this._listeners.delete(listener)
    }
  }

  private notifyListeners(prevState: T): void {
    const current = this._cachedValue
    this._listeners.forEach(listener => {
      try {
        listener(current, prevState)
      } catch (err) {
        console.error('[DerivedStore] 监听器执行失败:', err)
      }
    })
  }
}

// ==================== React Hook适配 ====================

/**
 * 将Store连接到React组件的Hook
 *
 * 使用示例：
 * ```tsx
 * function MyComponent() {
 *   const state = useStore(chatStore)
 *   return <Text>{state.messages.length}</Text>
 * }
 * ```
 */
export function useStore<T>(store: Store<T>): T {
  const React = require('react')
  const [state, setState] = React.useState(() => store.state)

  React.useEffect(() => {
    return store.subscribe((newState) => {
      setState(newState)
    })
  }, [store])

  return state
}

/**
 * 从Store派生部分状态的Hook
 *
 * 使用示例：
 * ```tsx
 * function MessageCount() {
 *   const count = useDerived(chatStore, s => s.messages.length)
 *   return <Text>{count} messages</Text>
 * }
 * ```
 */
export function useDerived<T, S>(store: Store<S>, selector: (state: S) => T): T {
  const React = require('react')
  const [value, setValue] = React.useState(() => selector(store.state))

  React.useEffect(() => {
    const derived = new DerivedStore(store, selector)
    return derived.subscribe((newValue) => {
      setValue(newValue)
    })
  }, [store])

  return value
}
