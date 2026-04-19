/**
 * Gemma4 系统主应用入口（重构版）
 *
 * 重构改进：
 * - 使用统一API客户端和状态管理
 * - 使用UI设计系统组件
 * - 连接状态实时显示
 * - 错误边界和降级处理
 * - 通知系统
 *
 * 页面路由：
 * - /          AI对话界面
 * - /dashboard 16模块仪表盘
 * - /monitor   实时资源监控
 * - /security  安全中心
 * - /wiki      知识库管理
 * - /settings  系统设置
 */

import React, { useEffect } from 'react'
import { Text, Box, useApp } from '../ink.js'
import { BackendProvider, useBackend } from '../context/backendContext.js'
import {
  useAppRouter,
  NavBar,
  ShortcutHelp,
  useKeyboardNavigation,
} from '../services/router.js'
import {
  colors,
  icons,
  layout,
  spacing,
  getStatusDisplay,
  formatDuration,
  ConnectionIndicator,
  NotificationBar,
  ErrorDisplay,
  LoadingSpinner,
  Divider,
} from '../design/index.js'
import {
  uiStore,
  uiActions,
  chatStore,
  chatActions,
  type AppRoute,
  type Notification,
} from '../state/index.js'

// 页面组件（懒加载）
import App from '../components/App.js'
import Dashboard from '../screens/Dashboard.js'
import Monitor from '../screens/Monitor.js'
import Security from '../screens/Security.js'
import WikiPage from '../screens/Wiki.js'

// ==================== 通知容器 ====================

function NotificationContainer() {
  const notifications = uiStore.state.notifications

  if (notifications.length === 0) return null

  return (
    <Box flexDirection="column">
      {notifications.slice(0, 3).map((notif) => (
        <NotificationBar
          key={notif.id}
          type={notif.type}
          message={notif.message}
          onDismiss={() => uiActions.removeNotification(notif.id)}
        />
      ))}
    </Box>
  )
}

// ==================== 全局状态栏 ====================

function StatusBar() {
  const { config, connectionStatus, health, coreInfo } = useBackend()

  const statusDisplay = getStatusDisplay(connectionStatus)
  const modelInfo = health?.default_model || coreInfo?.default_model || '?'
  const modelCount = health?.models?.length || 0

  return (
    <Box
      backgroundColor={colors.neutral.bg}
      paddingX={spacing.sm}
      height={layout.statusBarHeight}
      justifyContent="space-between"
    >
      <Box>
        <Text bold color={colors.primary.main}>
          {icons.chat} Gemma4
        </Text>
        <Text dimColor> │ </Text>
        <Text dimColor>Mode: </Text>
        <Text bold>{config.mode.toUpperCase()}</Text>
        <Text dimColor> │ </Text>
        <ConnectionIndicator status={connectionStatus} />
      </Box>

      <Box>
        {health?.status === 'ok' && (
          <>
            <Text dimColor>v{modelInfo}</Text>
            <Text dimColor> │ Models: {modelCount}</Text>
          </>
        )}
      </Box>
    </Box>
  )
}

// ==================== 错误边界 ====================

function ErrorBoundary({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <Box flexDirection="column" padding={spacing.md}>
      <ErrorDisplay
        message="系统初始化失败"
        detail={error.message}
        onRetry={onRetry}
      />
    </Box>
  )
}

// ==================== 主应用组件 ====================

function Gemma4App(): JSX.Element {
  const { exit } = useApp()
  const { config, connectionStatus, error, reconnect, isLoading } = useBackend()
  const { currentRoute, navigate, navigateByShortcut } = useAppRouter()

  // 键盘导航处理
  useKeyboardNavigation(navigateByShortcut, () => exit())

  // 同步路由到状态管理
  useEffect(() => {
    uiActions.navigate(currentRoute as AppRoute)
  }, [currentRoute])

  /** 渲染当前激活的页面 */
  const renderCurrentPage = (): JSX.Element | null => {
    // 加载状态
    if (isLoading && !config.isHealthy) {
      return (
        <Box flexDirection="column" padding={spacing.xl} alignItems="center">
          <LoadingSpinner label="正在连接后端服务" />
        </Box>
      )
    }

    // 连接错误
    if (connectionStatus === 'error' && error) {
      return <ErrorBoundary error={error} onRetry={reconnect} />
    }

    // 路由渲染
    switch (currentRoute) {
      case '/':
        return <App />
      case '/dashboard':
        return <Dashboard onClose={() => navigate('/')} />
      case '/monitor':
        return <Monitor onClose={() => navigate('/')} />
      case '/security':
        return <Security onClose={() => navigate('/')} />
      case '/wiki':
        return <WikiPage onClose={() => navigate('/')} />
      default:
        return <App />
    }
  }

  return (
    <Box flexDirection="column" height="100%">
      {/* 通知栏 */}
      <NotificationContainer />

      {/* 全局状态栏 */}
      <StatusBar />

      {/* 导航栏 */}
      <NavBar currentRoute={currentRoute} onNavigate={navigate} />

      {/* 分割线 */}
      <Divider />

      {/* 当前页面内容 */}
      <Box flex={1} overflow="scroll">
        {renderCurrentPage()}
      </Box>

      {/* 快捷键帮助 */}
      <ShortcutHelp />
    </Box>
  )
}

// ==================== 根组件（带Provider） ====================

export default function RootApp(): JSX.Element {
  return (
    <BackendProvider>
      <Gemma4App />
    </BackendProvider>
  )
}
