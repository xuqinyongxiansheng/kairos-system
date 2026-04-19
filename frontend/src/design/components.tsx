/**
 * UI设计系统 - 可复用组件
 *
 * 基于Ink终端UI框架的可复用组件库，
 * 遵循统一的设计令牌和交互规范。
 */

import React from 'react'
import { Box, Text } from '../ink.js'
import {
  colors,
  spacing,
  icons,
  layout,
  borders,
  typography,
  getStatusDisplay,
  getSeverityDisplay,
  truncate,
  formatDuration,
} from './tokens'

// ==================== 布局组件 ====================

/** 页面容器 */
export function Page({ children, title }: { children: React.ReactNode; title?: string }) {
  return (
    <Box flexDirection="column" padding={spacing.md}>
      {title && (
        <Box marginBottom={spacing.sm}>
          <Text bold color={colors.ink.heading}>{title}</Text>
        </Box>
      )}
      {children}
    </Box>
  )
}

/** 卡片容器 */
export function Card({
  children,
  title,
  width,
  borderColor = colors.neutral.border,
}: {
  children: React.ReactNode
  title?: string
  width?: number
  borderColor?: string
}) {
  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor={borderColor}
      padding={spacing.sm}
      width={width}
    >
      {title && (
        <Box marginBottom={spacing.xs}>
          <Text bold color={colors.ink.heading}>{title}</Text>
        </Box>
      )}
      {children}
    </Box>
  )
}

/** 分割线 */
export function Divider({ label, width = 60 }: { label?: string; width?: number }) {
  if (label) {
    const sideLen = Math.floor((width - label.length - 2) / 2)
    return (
      <Box>
        <Text dimColor>{'─'.repeat(sideLen)} {label} {'─'.repeat(sideLen)}</Text>
      </Box>
    )
  }
  return <Text dimColor>{'─'.repeat(width)}</Text>
}

/** 间距 */
export function Spacer({ size = spacing.md }: { size?: number }) {
  return <Box height={size} />
}

// ==================== 状态指示组件 ====================

/** 连接状态指示器 */
export function ConnectionIndicator({ status }: { status: string }) {
  const display = getStatusDisplay(status)
  return (
    <Text color={display.color}>
      {display.icon} {display.text}
    </Text>
  )
}

/** 健康状态徽章 */
export function HealthBadge({ status }: { status: 'ok' | 'error' | string }) {
  const isOk = status === 'ok'
  return (
    <Text color={isOk ? colors.success.main : colors.error.main}>
      {isOk ? icons.success : icons.error} {isOk ? '健康' : '异常'}
    </Text>
  )
}

/** 严重级别徽章 */
export function SeverityBadge({ severity }: { severity: string }) {
  const display = getSeverityDisplay(severity)
  return (
    <Text color={display.color}>
      {display.icon} {severity.toUpperCase()}
    </Text>
  )
}

// ==================== 数据展示组件 ====================

/** 键值对行 */
export function KVRow({
  label,
  value,
  labelWidth = 16,
  valueColor,
}: {
  label: string
  value: string | number | null | undefined
  labelWidth?: number
  valueColor?: string
}) {
  const displayValue = value != null ? String(value) : '-'
  return (
    <Box>
      <Box width={labelWidth}>
        <Text dimColor>{label}:</Text>
      </Box>
      <Text color={valueColor || colors.neutral.text}>{displayValue}</Text>
    </Box>
  )
}

/** 数据网格 */
export function DataGrid({
  data,
  columns,
  columnWidths,
}: {
  data: Array<Record<string, any>>
  columns: Array<{ key: string; label: string; color?: string }>
  columnWidths?: number[]
}) {
  return (
    <Box flexDirection="column">
      {/* 表头 */}
      <Box>
        {columns.map((col, i) => (
          <Box key={col.key} width={columnWidths?.[i] || 20}>
            <Text bold dimColor>{col.label}</Text>
          </Box>
        ))}
      </Box>
      <Text dimColor>{'─'.repeat(columnWidths?.reduce((a, b) => a + b, 60) || 60)}</Text>
      {/* 数据行 */}
      {data.map((row, rowIdx) => (
        <Box key={rowIdx}>
          {columns.map((col, colIdx) => (
            <Box key={col.key} width={columnWidths?.[colIdx] || 20}>
              <Text color={col.color}>{String(row[col.key] ?? '-')}</Text>
            </Box>
          ))}
        </Box>
      ))}
    </Box>
  )
}

/** 统计卡片 */
export function StatCard({
  label,
  value,
  unit,
  trend,
  color,
}: {
  label: string
  value: string | number
  unit?: string
  trend?: 'up' | 'down' | 'stable'
  color?: string
}) {
  const trendIcon = trend === 'up' ? icons.arrowUp : trend === 'down' ? icons.arrowDown : ''
  const trendColor = trend === 'up' ? colors.success.main : trend === 'down' ? colors.error.main : colors.neutral.textDim

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={colors.neutral.border} padding={spacing.xs} width={20}>
      <Text dimColor>{label}</Text>
      <Box>
        <Text bold color={color || colors.neutral.text}>{String(value)}</Text>
        {unit && <Text dimColor> {unit}</Text>}
        {trend && <Text color={trendColor}> {trendIcon}</Text>}
      </Box>
    </Box>
  )
}

// ==================== 交互组件 ====================

/** 导航标签栏 */
export function TabBar({
  tabs,
  activeIndex,
  onSelect,
}: {
  tabs: Array<{ key: string; label: string; icon?: string }>
  activeIndex: number
  onSelect: (index: number) => void
}) {
  return (
    <Box>
      {tabs.map((tab, i) => {
        const isActive = i === activeIndex
        return (
          <Box key={tab.key} marginRight={spacing.md}>
            <Text
              color={isActive ? colors.primary.main : colors.neutral.textDim}
              bold={isActive}
              inverse={isActive}
            >
              {tab.icon ? `${tab.icon} ` : ''}{tab.label}
            </Text>
          </Box>
        )
      })}
    </Box>
  )
}

/** 通知条 */
export function NotificationBar({
  type,
  message,
  onDismiss,
}: {
  type: 'info' | 'success' | 'warning' | 'error'
  message: string
  onDismiss?: () => void
}) {
  const colorMap = {
    info: colors.info.main,
    success: colors.success.main,
    warning: colors.warning.main,
    error: colors.error.main,
  }
  const iconMap = {
    info: icons.info,
    success: icons.success,
    warning: icons.warning,
    error: icons.error,
  }

  return (
    <Box backgroundColor={colorMap[type]} padding={spacing.xs}>
      <Text>{iconMap[type]} {message}</Text>
      {onDismiss && (
        <Text> [{icons.close}]</Text>
      )}
    </Box>
  )
}

// ==================== 加载组件 ====================

/** 加载指示器 */
export function LoadingSpinner({ label }: { label?: string }) {
  return (
    <Box>
      <Text color={colors.primary.main}>{icons.loading}</Text>
      {label && <Text dimColor> {label}...</Text>}
    </Box>
  )
}

/** 骨架屏 */
export function Skeleton({ width = 30, height = 1 }: { width?: number; height?: number }) {
  const lines = Array.from({ length: height }, (_, i) => {
    const lineLen = i === height - 1 ? Math.floor(width * 0.6) : width
    return '░'.repeat(lineLen)
  })
  return (
    <Box flexDirection="column">
      {lines.map((line, i) => (
        <Text key={i} dimColor>{line}</Text>
      ))}
    </Box>
  )
}

// ==================== 空状态 ====================

/** 空状态占位 */
export function EmptyState({
  icon = icons.dot,
  title,
  description,
}: {
  icon?: string
  title: string
  description?: string
}) {
  return (
    <Box flexDirection="column" alignItems="center" padding={spacing.xl}>
      <Text color={colors.neutral.textDim}>{icon}</Text>
      <Text bold color={colors.neutral.textDim}>{title}</Text>
      {description && <Text dimColor>{description}</Text>}
    </Box>
  )
}

// ==================== 错误展示 ====================

/** 错误展示组件 */
export function ErrorDisplay({
  message,
  detail,
  onRetry,
}: {
  message: string
  detail?: string
  onRetry?: () => void
}) {
  return (
    <Box flexDirection="column" borderStyle="round" borderColor={colors.error.main} padding={spacing.md}>
      <Box marginBottom={spacing.xs}>
        <Text color={colors.error.main} bold>{icons.error} 错误</Text>
      </Box>
      <Text color={colors.neutral.text}>{message}</Text>
      {detail && <Text dimColor>{detail}</Text>}
      {onRetry && (
        <Box marginTop={spacing.sm}>
          <Text color={colors.primary.main}>[↻ 重试]</Text>
        </Box>
      )}
    </Box>
  )
}
