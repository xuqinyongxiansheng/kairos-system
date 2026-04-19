/**
 * DiagnosticsDisplay - 诊断问题显示组件
 *
 * 展示代码诊断信息（错误、警告、提示、建议）。
 * 支持三种运行模式：
 *   1. 后端API模式：从FastAPI后端获取实时诊断数据
 *   2. 本地模式：使用内置演示数据展示UI效果
 *   3. 断连模式：显示友好的连接状态提示
 *
 * @module components/DiagnosticsDisplay
 */

import React, { useState, useCallback, useMemo } from 'react';
import { Box, Text } from '../ink.js';
import { diagnosticTracker, DiagnosticTrackingService } from '../services/diagnosticTracking.js';
import type { Attachment } from '../utils/attachments.js';
import { getCwd } from '../utils/cwd.js';
import { CtrlOToExpand } from './CtrlOToExpand.js';
import { MessageResponse } from './MessageResponse.js';

/** 诊断附件类型定义 */
type DiagnosticsAttachment = Extract<Attachment, {
  type: 'diagnostics';
}>;

/** 组件属性接口 */
interface DiagnosticsDisplayProps {
  attachment: DiagnosticsAttachment;
  verbose: boolean;
}

/** 严重性级别 */
type SeverityLevel = 'Error' | 'Warning' | 'Info' | 'Hint';

/** 严重性配置映射 */
const SEVERITY_CONFIG: Record<SeverityLevel, {
  symbol: string;
  label: string;
  color: string;
}> = {
  Error: { symbol: '✗', label: '错误', color: 'red' },
  Warning: { symbol: '⚠', label: '警告', color: 'yellow' },
  Info: { symbol: 'ℹ', label: '信息', color: 'blue' },
  Hint: { symbol: '★', label: '建议', color: 'cyan' },
};

/**
 * 获取安全的状态符号
 * 防止figures库缺失导致崩溃
 */
function getSafeSeveritySymbol(severity: SeverityLevel): string {
  try {
    return DiagnosticTrackingService.getSeveritySymbol(severity);
  } catch {
    return SEVERITY_CONFIG[severity]?.symbol || '-';
  }
}

/**
 * 格式化文件URI为可读路径
 */
function formatFilePath(uri: string): string {
  try {
    const cleanUri = uri
      .replace('file://', '')
      .replace('_claude_fs_right:', '')
      .replace('_claude_fs_left:', '');
    const { relative } = require('path');
    return relative(getCwd(), cleanUri);
  } catch {
    return uri.split('/').pop() || uri;
  }
}

/**
 * 获取URI协议标签
 */
function getProtocolLabel(uri: string): string {
  if (uri.startsWith('file://')) return '(file://)';
  if (uri.startsWith('_claude_fs_right:')) return '(claude_fs_right)';
  if (uri.startsWith('_claude_fs_left:')) return '(claude_fs_left)';
  const protocol = uri.split(':')[0];
  return `(${protocol})`;
}

/**
 * 单条诊断项渲染组件
 */
function DiagnosticItem({
  diagnostic,
  index,
}: {
  diagnostic: import('../services/diagnosticTracking.js').Diagnostic;
  index: number;
}): React.ReactElement {
  const symbol = getSafeSeveritySymbol(diagnostic.severity as SeverityLevel);
  const config = SEVERITY_CONFIG[diagnostic.severity as SeverityLevel] || SEVERITY_CONFIG.Info;

  return (
    <MessageResponse key={index}>
      <Text dimColor wrap="wrap">
        {'  '}
        <Text color={config.color}>{symbol}</Text>
        {' [Line '}
        {diagnostic.range.start.line + 1}
        {':'}
        {diagnostic.range.start.character + 1}
        {'] '}
        {diagnostic.message}
        {diagnostic.code ? ` [${diagnostic.code}]` : ''}
        {diagnostic.source ? ` (${diagnostic.source})` : ''}
      </Text>
    </MessageResponse>
  );
}

/**
 * 单个文件的诊断列表渲染组件
 */
function DiagnosticFileBlock({
  file,
  fileIndex,
}: {
  file: import('../services/diagnosticTracking.js').DiagnosticFile;
  fileIndex: number;
}): React.ReactElement {
  return (
    <React.Fragment key={fileIndex}>
      <MessageResponse>
        <Text dimColor wrap="wrap">
          <Text bold>{formatFilePath(file.uri)}</Text>
          {' '}
          <Text dimColor>{getProtocolLabel(file.uri)}:</Text>
        </Text>
      </MessageResponse>
      {file.diagnostics.map((diag, idx) => (
        <DiagnosticItem key={idx} diagnostic={diag} index={idx} />
      ))}
    </React.Fragment>
  );
}

/**
 * 断连状态提示面板
 */
function DisconnectedPanel(): React.ReactElement {
  return (
    <Box flexDirection="column" gap={0}>
      <MessageResponse>
        <Text bold color="yellow">{'⚠ 诊断系统'}</Text>
      </MessageResponse>
      <MessageResponse>
        <Text dimColor wrap="wrap">
          {'  '}IDE未连接 — 诊断功能需要通过MCP协议连接到IDE才能获取实时代码分析结果。
        </Text>
      </MessageResponse>
      <MessageResponse>
        <Text dimColor wrap="wrap">
          {'  '}当前状态: <Text color="gray">等待IDE连接</Text> | 模式: <Text color="cyan">独立运行</Text>
        </Text>
      </MessageResponse>
      <MessageResponse>
        <Text dimColor wrap="wrap">
          {'  '}提示: 启动IDE并配置MCP服务后，此处将自动显示代码问题与警告。
        </Text>
      </MessageResponse>
    </Box>
  );
}

/**
 * 空数据状态提示
 */
function EmptyStatePanel(): React.ReactElement {
  return (
    <Box flexDirection="column" gap={0}>
      <MessageResponse>
        <Text bold color="green">{'✓ 诊断系统'}</Text>
      </MessageResponse>
      <MessageResponse>
        <Text dimColor wrap="wrap">
          {'  '}当前没有检测到新的诊断问题。代码状态良好。
        </Text>
      </MessageResponse>
    </Box>
  );
}

/**
 * 主组件 - DiagnosticsDisplay
 *
 * 根据attachment数据和状态渲染不同的诊断视图：
 * - isDisconnected=true: 显示断连提示
 * - files有数据: 显示诊断列表
 * - files为空且非断连: 显示空状态或null（根据verbose）
 */
export function DiagnosticsDisplay({ attachment, verbose }: DiagnosticsDisplayProps): React.ReactElement | null {
  const [expanded, setExpanded] = useState(false);

  const hasFiles = attachment.files && attachment.files.length > 0;
  const isDemo = attachment.isDemo === true;
  const isDisconnected = attachment.isDisconnected === true;

  /** 计算总问题数和文件数 */
  const summary = useMemo(() => {
    if (!hasFiles) return { totalIssues: 0, fileCount: 0 };
    const totalIssues = attachment.files.reduce(
      (sum, file) => sum + file.diagnostics.length,
      0
    );
    return { totalIssues, fileCount: attachment.files.length };
  }, [hasFiles, attachment.files]);

  /** 切换展开/折叠 */
  const toggleExpand = useCallback(() => {
    setExpanded(prev => !prev);
  }, []);

  // 场景1: 断连状态 - 显示连接提示
  if (isDisconnected || (!hasFiles && isDisconnected !== false)) {
    return <DisconnectedPanel />;
  }

  // 场景2: 无数据且非断连模式 - 返回null（保持原有行为）
  if (!hasFiles) {
    return null;
  }

  // 场景3: 有数据 - 详细视图或摘要视图
  if (verbose || expanded) {
    return (
      <Box flexDirection="column">
        {!verbose && hasFiles && (
          <MessageResponse>
            <Text dimColor>
              {'['}<Text color="cyan" onClick={toggleExpand}>收起</Text>{']'}
            </Text>
          </MessageResponse>
        )}
        {attachment.files.map((file, idx) => (
          <DiagnosticFileBlock key={idx} file={file} fileIndex={idx} />
        ))}
        {isDemo && (
          <MessageResponse>
            <Text color="cyan" dimColor>{'  [演示数据]'}</Text>
          </MessageResponse>
        )}
      </Box>
    );
  }

  // 默认: 摘要视图
  const issueText = summary.totalIssues === 1 ? 'issue' : 'issues';
  const fileText = summary.fileCount === 1 ? 'file' : 'files';
  const demoTag = isDemo ? <Text color="cyan"> [演示]</Text> : null;

  return (
    <MessageResponse>
      <Text dimColor wrap="wrap">
        Found <Text bold={true}>{summary.totalIssues}</Text> new diagnostic{' '}
        {issueText} in {summary.fileCount} {fileText}{' '}
        <CtrlOToExpand />
        {demoTag}
      </Text>
    </MessageResponse>
  );
}

/** 导出类型供外部使用 */
export type { DiagnosticsDisplayProps, SeverityLevel };
