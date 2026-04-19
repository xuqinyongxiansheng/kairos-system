/**
 * 应用状态分片定义
 *
 * 每个状态分片对应一个独立的Store实例，
 * 管理特定领域的状态数据。
 */

import { Store } from './core'
import { backendConfig, BackendMode } from '../services/api/backendConfig'
import type {
  HealthResponse,
  SystemCoreResponse,
  PerformanceStats,
  ChatResponse,
  WikiDocument,
  WikiListResponse,
  WikiSearchResult,
  ModelsV2Response,
} from '../services/api/localBackend'
import type { ConnectionStatus } from '../services/api/unifiedClient'

// ==================== 连接状态 ====================

export interface ConnectionState {
  status: ConnectionStatus
  mode: BackendMode
  apiUrl: string
  isAuthenticated: boolean
  lastHealthCheck: number | null
  latencyMs: number | null
}

export const connectionStore = new Store<ConnectionState>({
  name: 'connection',
  initialState: {
    status: 'checking',
    mode: backendConfig.getConfiguration().mode,
    apiUrl: backendConfig.getConfiguration().localApiUrl,
    isAuthenticated: backendConfig.getConfiguration().isAuthenticated,
    lastHealthCheck: null,
    latencyMs: null,
  },
})

// ==================== 系统状态 ====================

export interface SystemState {
  coreInfo: SystemCoreResponse | null
  health: HealthResponse | null
  performance: PerformanceStats | null
  models: ModelsV2Response | null
  isLoading: boolean
  error: string | null
  lastUpdated: number | null
}

export const systemStore = new Store<SystemState>({
  name: 'system',
  initialState: {
    coreInfo: null,
    health: null,
    performance: null,
    models: null,
    isLoading: false,
    error: null,
    lastUpdated: null,
  },
})

// ==================== 聊天状态 ====================

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  model?: string
  isStreaming?: boolean
}

export interface ChatState {
  messages: ChatMessage[]
  currentModel: string
  isStreaming: boolean
  isLoading: boolean
  error: string | null
  inputText: string
}

export const chatStore = new Store<ChatState>({
  name: 'chat',
  initialState: {
    messages: [],
    currentModel: 'gemma4:e4b',
    isStreaming: false,
    isLoading: false,
    error: null,
    inputText: '',
  },
  persist: true,
})

// ==================== Wiki状态 ====================

export interface WikiState {
  documents: WikiListResponse | null
  searchResults: WikiSearchResult[]
  selectedDocument: WikiDocument | null
  isLoading: boolean
  error: string | null
  searchQuery: string
  currentPage: number
  pageSize: number
}

export const wikiStore = new Store<WikiState>({
  name: 'wiki',
  initialState: {
    documents: null,
    searchResults: [],
    selectedDocument: null,
    isLoading: false,
    error: null,
    searchQuery: '',
    currentPage: 1,
    pageSize: 20,
  },
})

// ==================== UI状态 ====================

export type AppRoute = '/' | '/dashboard' | '/monitor' | '/security' | '/wiki' | '/settings'

export interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  message: string
  timestamp: number
  autoDismiss?: boolean
}

export interface UIState {
  currentRoute: AppRoute
  sidebarCollapsed: boolean
  notifications: Notification[]
  activeModal: string | null
  isHelpVisible: boolean
  theme: 'dark' | 'light'
}

export const uiStore = new Store<UIState>({
  name: 'ui',
  initialState: {
    currentRoute: '/',
    sidebarCollapsed: false,
    notifications: [],
    activeModal: null,
    isHelpVisible: false,
    theme: 'dark',
  },
  persist: true,
})

// ==================== Action定义 ====================

/** 连接状态Actions */
export const connectionActions = {
  setStatus(status: ConnectionStatus) {
    connectionStore.setState(s => ({ ...s, status }))
  },
  setMode(mode: BackendMode) {
    connectionStore.setState(s => ({ ...s, mode }))
  },
  setLatency(ms: number) {
    connectionStore.setState(s => ({ ...s, latencyMs: ms }))
  },
  setAuthenticated(isAuthenticated: boolean) {
    connectionStore.setState(s => ({ ...s, isAuthenticated }))
  },
}

/** 系统状态Actions */
export const systemActions = {
  setLoading(isLoading: boolean) {
    systemStore.setState(s => ({ ...s, isLoading }))
  },
  setError(error: string | null) {
    systemStore.setState(s => ({ ...s, error }))
  },
  setCoreInfo(coreInfo: SystemCoreResponse) {
    systemStore.setState(s => ({
      ...s,
      coreInfo,
      lastUpdated: Date.now(),
    }))
  },
  setHealth(health: HealthResponse) {
    systemStore.setState(s => ({
      ...s,
      health,
      lastUpdated: Date.now(),
    }))
  },
  setPerformance(performance: PerformanceStats) {
    systemStore.setState(s => ({
      ...s,
      performance,
      lastUpdated: Date.now(),
    }))
  },
  setModels(models: ModelsV2Response) {
    systemStore.setState(s => ({ ...s, models }))
  },
  reset() {
    systemStore.reset()
  },
}

/** 聊天状态Actions */
export const chatActions = {
  addMessage(message: Omit<ChatMessage, 'id' | 'timestamp'>) {
    chatStore.setState(s => ({
      ...s,
      messages: [
        ...s.messages,
        {
          ...message,
          id: `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
          timestamp: Date.now(),
        },
      ],
    }))
  },
  updateLastMessage(content: string) {
    chatStore.setState(s => {
      const messages = [...s.messages]
      if (messages.length > 0) {
        const last = messages[messages.length - 1]
        messages[messages.length - 1] = {
          ...last,
          content: last.content + content,
        }
      }
      return { ...s, messages }
    })
  },
  setStreaming(isStreaming: boolean) {
    chatStore.setState(s => ({ ...s, isStreaming }))
  },
  setLoading(isLoading: boolean) {
    chatStore.setState(s => ({ ...s, isLoading }))
  },
  setError(error: string | null) {
    chatStore.setState(s => ({ ...s, error }))
  },
  setInputText(inputText: string) {
    chatStore.setState(s => ({ ...s, inputText }))
  },
  setModel(currentModel: string) {
    chatStore.setState(s => ({ ...s, currentModel }))
  },
  clearMessages() {
    chatStore.setState(s => ({ ...s, messages: [] }))
  },
}

/** Wiki状态Actions */
export const wikiActions = {
  setLoading(isLoading: boolean) {
    wikiStore.setState(s => ({ ...s, isLoading }))
  },
  setError(error: string | null) {
    wikiStore.setState(s => ({ ...s, error }))
  },
  setDocuments(documents: WikiListResponse) {
    wikiStore.setState(s => ({ ...s, documents }))
  },
  setSearchResults(searchResults: WikiSearchResult[]) {
    wikiStore.setState(s => ({ ...s, searchResults }))
  },
  setSelectedDocument(doc: WikiDocument | null) {
    wikiStore.setState(s => ({ ...s, selectedDocument: doc }))
  },
  setSearchQuery(searchQuery: string) {
    wikiStore.setState(s => ({ ...s, searchQuery }))
  },
  setPage(currentPage: number) {
    wikiStore.setState(s => ({ ...s, currentPage }))
  },
}

/** UI状态Actions */
export const uiActions = {
  navigate(route: AppRoute) {
    uiStore.setState(s => ({ ...s, currentRoute: route }))
  },
  toggleSidebar() {
    uiStore.setState(s => ({ ...s, sidebarCollapsed: !s.sidebarCollapsed }))
  },
  addNotification(notification: Omit<Notification, 'id' | 'timestamp'>) {
    uiStore.setState(s => ({
      ...s,
      notifications: [
        ...s.notifications,
        {
          ...notification,
          id: `notif_${Date.now()}`,
          timestamp: Date.now(),
        },
      ],
    }))
  },
  removeNotification(id: string) {
    uiStore.setState(s => ({
      ...s,
      notifications: s.notifications.filter(n => n.id !== id),
    }))
  },
  showModal(modal: string) {
    uiStore.setState(s => ({ ...s, activeModal: modal }))
  },
  hideModal() {
    uiStore.setState(s => ({ ...s, activeModal: null }))
  },
  toggleHelp() {
    uiStore.setState(s => ({ ...s, isHelpVisible: !s.isHelpVisible }))
  },
  setTheme(theme: 'dark' | 'light') {
    uiStore.setState(s => ({ ...s, theme }))
  },
}
