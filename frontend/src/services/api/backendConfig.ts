/**
 * 后端配置管理模块
 *
 * 管理前端与后端的连接配置，支持：
 * - LOCAL_API=true 环境变量切换本地/云端模式
 * - 自动检测后端可用性
 * - 配置持久化到localStorage
 * - React Context集成
 */

import { localBackend, type LocalBackendConfig } from './localBackend';

// ==================== 常量定义 ====================

/** 本地模式环境变量名 */
export const ENV_LOCAL_API = 'LOCAL_API';

/** localStorage键名 */
export const STORAGE_KEY_BACKEND_MODE = 'backend_mode';
export const STORAGE_KEY_API_URL = 'local_api_url';
export const STORAGE_KEY_AUTH_TOKEN = 'auth_token';

/** 后端模式枚举 */
export enum BackendMode {
  /** 使用本地FastAPI后端 */
  LOCAL = 'local',
  /** 使用Anthropic Cloud API */
  CLOUD = 'cloud',
}

// ==================== 配置接口 ====================

/** 后端完整配置 */
export interface BackendConfiguration {
  /** 当前模式 */
  mode: BackendMode;
  /** 本地API URL */
  localApiUrl: string;
  /** 是否已认证 */
  isAuthenticated: boolean;
  /** 最后一次健康检查时间 */
  lastHealthCheck: number | null;
  /** 健康状态 */
  isHealthy: boolean | null;
}

// ==================== 配置管理类 ====================

class BackendConfigManager {
  private _mode: BackendMode;
  private _localApiUrl: string;
  private _isHealthy: boolean | null = null;
  private _lastHealthCheck: number | null = null;
  private _listeners: Array<(config: BackendConfiguration) => void> = [];
  private _healthCheckInterval: ReturnType<typeof setInterval> | null = null;

  constructor() {
    // 优先级：环境变量 > localStorage > 默认值
    this._mode = this.detectMode();
    this._localApiUrl = this.loadLocalApiUrl();

    // 启动自动健康检查
    this.startHealthCheck();
  }

  /**
   * 检测当前应该使用的模式
   */
  private detectMode(): BackendMode {
    // 1. 检查环境变量
    if (typeof process !== 'undefined' && process.env?.[ENV_LOCAL_API] === 'true') {
      return BackendMode.LOCAL;
    }

    // 2. 检查localStorage
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const stored = window.localStorage.getItem(STORAGE_KEY_BACKEND_MODE);
        if (stored === BackendMode.LOCAL || stored === BackendMode.CLOUD) {
          return stored as BackendMode;
        }
      }
    } catch {
      // localStorage不可用时忽略
    }

    // 3. 默认使用本地模式（因为我们的目标是桥接到本地后端）
    return BackendMode.LOCAL;
  }

  /**
   * 加载本地API URL
   */
  private loadLocalApiUrl(): string {
    // 优先从环境变量读取
    if (typeof process !== 'undefined' && process.env?.LOCAL_API_URL) {
      return process.env.LOCAL_API_URL;
    }

    // 其次从localStorage读取
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const stored = window.localStorage.getItem(STORAGE_KEY_API_URL);
        if (stored) return stored;
      }
    } catch {
      // 忽略
    }

    // 默认值
    return 'http://localhost:8000';
  }

  /**
   * 获取当前配置
   */
  getConfiguration(): BackendConfiguration {
    return {
      mode: this._mode,
      localApiUrl: this._localApiUrl,
      isAuthenticated: localBackend.isAuthenticated(),
      lastHealthCheck: this._lastHealthCheck,
      isHealthy: this._isHealthy,
    };
  }

  /**
   * 切换后端模式
   */
  async switchMode(mode: BackendMode): Promise<void> {
    this._mode = mode;

    // 持久化到localStorage
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem(STORAGE_KEY_BACKEND_MODE, mode);
      }
    } catch {
      // 忽略
    }

    // 如果切换到本地模式，更新客户端URL并立即检查健康状态
    if (mode === BackendMode.LOCAL) {
      localBackend.setToken(this.getStoredToken() || '');
      await this.checkHealth();
    }

    this.notifyListeners();
  }

  /**
   * 更新本地API URL
   */
  setLocalApiUrl(url: string): void {
    this._localApiUrl = url;

    // 更新客户端实例的baseURL需要重新创建实例
    // 这里我们暂时只保存配置，实际使用时会读取

    // 持久化
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem(STORAGE_KEY_API_URL, url);
      }
    } catch {
      // 忽略
    }

    this.notifyListeners();
  }

  /**
   * 执行健康检查
   */
  async checkHealth(): Promise<boolean> {
    if (this._mode !== BackendMode.LOCAL) {
      this._isHealthy = null;
      this._lastHealthCheck = Date.now();
      this.notifyListeners();
      return false;
    }

    try {
      // 创建临时客户端用于健康检查（使用最新URL）
      const client = createLocalBackend({
        baseURL: this._localApiUrl,
        debug: false,
      });

      const healthy = await client.isHealthy();
      this._isHealthy = healthy;
      this._lastHealthCheck = Date.now();

      // 如果健康检查通过，恢复令牌
      const token = this.getStoredToken();
      if (token) {
        localBackend.setToken(token);
      }

      this.notifyListeners();
      return healthy;
    } catch (error) {
      console.warn('[BackendConfig] 健康检查失败:', error);
      this._isHealthy = false;
      this._lastHealthCheck = Date.now();
      this.notifyListeners();
      return false;
    }
  }

  /**
   * 启动定期健康检查（每30秒）
   */
  private startHealthCheck(): void {
    // 仅在浏览器环境中启动定时器
    if (typeof window === 'undefined') return;

    // 首次检查延迟5秒
    setTimeout(() => this.checkHealth(), 5000);

    // 之后每30秒检查一次
    this._healthCheckInterval = setInterval(() => {
      this.checkHealth().catch(console.error);
    }, 30000);

    // 页面隐藏时停止检查，显示时重新开始
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        if (this._healthCheckInterval) {
          clearInterval(this._healthCheckInterval);
          this._healthCheckInterval = null;
        }
      } else {
        this.startHealthCheck();
      }
    });
  }

  /**
   * 停止健康检查
   */
  stopHealthCheck(): void {
    if (this._healthCheckInterval) {
      clearInterval(this._healthCheckInterval);
      this._healthCheckInterval = null;
    }
  }

  /**
   * 注册配置变更监听器
   */
  addListener(listener: (config: BackendConfiguration) => void): () => void {
    this._listeners.push(listener);
    return () => {
      this._listeners = this._listeners.filter(l => l !== listener);
    };
  }

  /**
   * 通知所有监听器
   */
  private notifyListeners(): void {
    const config = this.getConfiguration();
    this._listeners.forEach(listener => {
      try {
        listener(config);
      } catch (error) {
        console.error('[BackendConfig] 监听器执行失败:', error);
      }
    });
  }

  /**
   * 获取存储的认证令牌
   */
  getStoredToken(): string | null {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        return window.localStorage.getItem(STORAGE_KEY_AUTH_TOKEN);
      }
    } catch {
      // 忽略
    }
    return null;
  }

  /**
   * 存储认证令牌
   */
  storeToken(token: string): void {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem(STORAGE_KEY_AUTH_TOKEN, token);
      }
      localBackend.setToken(token);
      this.notifyListeners();
    } catch {
      // 忽略
    }
  }

  /**
   * 清除存储的认证令牌
   */
  clearStoredToken(): void {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.removeItem(STORAGE_KEY_AUTH_TOKEN);
      }
      localBackend.clearToken();
      this.notifyListeners();
    } catch {
      // 忽略
    }
  }

  /**
   * 获取当前模式的API客户端配置
   */
  getClientConfig(): LocalBackendConfig {
    return {
      baseURL: this._localApiUrl,
      timeout: 30000,
      maxRetries: 3,
      debug: typeof process !== 'undefined' && process.env?.NODE_ENV === 'development',
    };
  }
}

// ==================== 单例导出 ====================

/**
 * 全局后端配置管理器实例
 *
 * 使用示例：
 * ```typescript
 * import { backendConfig, BackendMode } from './backendConfig';
 *
 * // 获取当前配置
 * const config = backendConfig.getConfiguration();
 * console.log(config.mode); // "local" | "cloud"
 *
 * // 切换到本地模式
 * await backendConfig.switchMode(BackendMode.LOCAL);
 *
 * // 监听配置变更
 * const unsubscribe = backendConfig.addListener((config) => {
 *   console.log('配置更新:', config);
 * });
 * ```
 */
export const backendConfig = new BackendConfigManager();

/**
 * 创建新的本地后端客户端实例（使用当前配置）
 */
export function createCurrentClient() {
  return createLocalBackend(backendConfig.getClientConfig());
}

// 重新导出createLocalBackend以保持向后兼容
export { createLocalBackend } from './localBackend';
