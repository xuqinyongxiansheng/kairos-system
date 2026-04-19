/**
 * UI设计系统 - 设计令牌（Design Tokens）
 *
 * 定义所有视觉属性的基础值，确保UI一致性。
 * 包括颜色、间距、字体、动画等。
 */

// ==================== 颜色系统 ====================

export const colors = {
  // 主色
  primary: {
    main: 'cyan',
    light: '#67e8f9',
    dark: '#0e7490',
    contrast: 'black',
  },

  // 语义色
  success: {
    main: 'green',
    light: '#86efac',
    dark: '#166534',
  },
  warning: {
    main: 'yellow',
    light: '#fde047',
    dark: '#854d0e',
  },
  error: {
    main: 'red',
    light: '#fca5a5',
    dark: '#991b1b',
  },
  info: {
    main: 'blue',
    light: '#93c5fd',
    dark: '#1e40af',
  },

  // 中性色
  neutral: {
    bg: '#1a1a2e',
    surface: '#16213e',
    border: '#334155',
    text: '#e2e8f0',
    textDim: '#94a3b8',
    textMuted: '#64748b',
  },

  // 状态色
  status: {
    online: 'green',
    offline: 'red',
    checking: 'yellow',
    streaming: 'magenta',
    idle: 'gray',
  },

  // Ink终端颜色映射
  ink: {
    brand: 'cyan',
    heading: 'cyan',
    link: 'blue',
    code: 'magenta',
    quote: 'gray',
    list: 'white',
    dimmed: 'gray',
  },
} as const

// ==================== 间距系统 ====================

export const spacing = {
  xs: 0,
  sm: 1,
  md: 2,
  lg: 3,
  xl: 4,
  xxl: 6,
} as const

// ==================== 边框 ====================

export const borders = {
  none: '',
  thin: '─',
  thick: '━',
  double: '═',
  rounded: '─',
  cornerTL: '┌',
  cornerTR: '┐',
  cornerBL: '└',
  cornerBR: '┘',
  vertical: '│',
  horizontal: '─',
} as const

// ==================== 图标 ====================

export const icons = {
  // 状态图标
  success: '✓',
  error: '✗',
  warning: '⚠',
  info: 'ℹ',
  loading: '◌',
  streaming: '◉',

  // 导航图标
  arrowRight: '→',
  arrowLeft: '←',
  arrowUp: '↑',
  arrowDown: '↓',
  chevronRight: '›',
  chevronLeft: '‹',

  // 功能图标
  chat: '💬',
  dashboard: '📊',
  monitor: '📈',
  security: '🔒',
  wiki: '📚',
  settings: '⚙',
  search: '🔍',
  refresh: '↻',
  close: '✕',
  check: '✓',
  star: '★',
  bullet: '•',
  dot: '●',
  circle: '○',

  // 连接状态
  connected: '●',
  disconnected: '○',
  checking: '◌',
} as const

// ==================== 动画 ====================

export const animation = {
  spinnerFrames: ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
  spinnerInterval: 80,
  pulseFrames: ['●', '◌', '○', '◌'],
  pulseInterval: 500,
  fadeInterval: 100,
} as const

// ==================== 布局 ====================

export const layout = {
  statusBarHeight: 1,
  navBarHeight: 1,
  inputBarHeight: 3,
  minContentHeight: 10,
  sidebarWidth: 20,
  maxLineWidth: 120,
  defaultPadding: 1,
} as const

// ==================== 文本样式 ====================

export const typography = {
  heading: {
    bold: true,
    color: colors.ink.heading,
  },
  subheading: {
    bold: true,
    color: colors.neutral.text,
  },
  body: {
    color: colors.neutral.text,
  },
  caption: {
    dimColor: true,
    color: colors.neutral.textDim,
  },
  code: {
    color: colors.ink.code,
  },
  link: {
    color: colors.ink.link,
  },
} as const

// ==================== 格式化工具 ====================

/** 状态文本映射 */
export function getStatusDisplay(status: string): { icon: string; color: string; text: string } {
  switch (status) {
    case 'ok':
    case 'connected':
    case 'online':
      return { icon: icons.connected, color: colors.status.online, text: '在线' }
    case 'error':
    case 'disconnected':
    case 'offline':
      return { icon: icons.disconnected, color: colors.status.offline, text: '离线' }
    case 'checking':
      return { icon: icons.checking, color: colors.status.checking, text: '检测中' }
    case 'streaming':
      return { icon: icons.streaming, color: colors.status.streaming, text: '生成中' }
    default:
      return { icon: icons.dot, color: colors.neutral.textDim, text: status }
  }
}

/** 严重级别显示 */
export function getSeverityDisplay(severity: string): { icon: string; color: string } {
  switch (severity) {
    case 'critical':
      return { icon: icons.error, color: colors.error.main }
    case 'high':
      return { icon: icons.warning, color: colors.warning.main }
    case 'medium':
      return { icon: icons.info, color: colors.info.main }
    case 'low':
      return { icon: icons.success, color: colors.success.main }
    default:
      return { icon: icons.dot, color: colors.neutral.textDim }
  }
}

/** 进度条 */
export function progressBar(current: number, total: number, width = 20): string {
  const ratio = Math.min(current / total, 1)
  const filled = Math.round(ratio * width)
  const empty = width - filled
  return `${'█'.repeat(filled)}${'░'.repeat(empty)} ${Math.round(ratio * 100)}%`
}

/** 截断文本 */
export function truncate(text: string, maxLength: number, suffix = '…'): string {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength - suffix.length) + suffix
}

/** 格式化字节 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

/** 格式化持续时间 */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  const minutes = Math.floor(ms / 60000)
  const seconds = Math.floor((ms % 60000) / 1000)
  return `${minutes}m${seconds}s`
}

/** 格式化时间戳 */
export function formatTimestamp(ts: number): string {
  const date = new Date(ts)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()

  if (diffMs < 60000) return '刚刚'
  if (diffMs < 3600000) return `${Math.floor(diffMs / 60000)}分钟前`
  if (diffMs < 86400000) return `${Math.floor(diffMs / 3600000)}小时前`

  return date.toLocaleDateString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
