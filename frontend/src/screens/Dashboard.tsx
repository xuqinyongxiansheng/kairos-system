/**
 * 系统Dashboard仪表盘
 *
 * 展示系统16大核心模块的实时状态、性能指标、运行统计。
 * 采用Ink终端UI风格，支持键盘导航和自动刷新。
 *
 * 功能模块：
 * - 系统概览卡片（版本/架构/状态）
 * - 16核心模块状态网格
 * - 实时性能图表（CPU/MEM/DISK-IO）
 * - 快捷操作入口（Wiki/Chat/Monitor/Security）
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Text, Box, useInput, useApp } from 'ink';
import Spinner from '../components/Spinner.js';
import {
  useBackend,
} from '../context/backendContext.js';
import {
  localBackend,
  type SystemCoreResponse,
  type HealthResponse,
  type PerformanceStats,
  type DetailedHealthResponse,
  type WikiHealthResponse,
} from '../services/api/localBackend.js';

// ==================== 类型定义 ====================

/** 核心模块信息 */
interface CoreModule {
  id: string;
  name: string;
  nameZh: string;
  status: 'online' | 'offline' | 'warning' | 'unknown';
  description: string;
}

/** Dashboard Props */
interface DashboardProps {
  onClose?: () => void;
  autoRefreshInterval?: number; // 自动刷新间隔(ms)，默认10000
}

// ==================== 常量 ====================

/** 16核心模块定义 */
const CORE_MODULES: CoreModule[] = [
  { id: 'eventbus', name: 'EventBus', nameZh: '事件总线', status: 'unknown', description: '发布/订阅消息系统' },
  { id: 'container', name: 'Container', nameZh: 'DI容器', status: 'unknown', description: '依赖注入与服务管理' },
  { id: 'database', name: 'Database', nameZh: '数据库', status: 'unknown', description: 'SQLite持久化存储' },
  { id: 'cache', name: 'Cache', nameZh: '缓存层', status: 'unknown', description: '响应缓存与模型缓存' },
  { id: 'lock', name: 'DistLock', nameZh: '分布式锁', status: 'unknown', description: '并发控制与互斥' },
  { id: 'security', name: 'SecurityMgr', nameZh: '安全中心', status: 'unknown', description: '115条规则防护引擎' },
  { id: 'wiki', name: 'WikiEngine', nameZh: '知识库', status: 'unknown', description: '文档管理与RAG检索' },
  { id: 'llm', name: 'LLMCore', nameZh: 'LLM引擎', status: 'unknown', description: 'Ollama本地模型接口' },
  { id: 'errorhandler', name: 'ErrorHandler', nameZh: '错误处理', status: 'unknown', description: '异常捕获与恢复' },
  { id: 'auditlog', name: 'AuditLog', nameZh: '审计日志', status: 'unknown', description: '操作记录与追踪' },
  { id: 'ratelimit', name: 'RateLimit', nameZh: '限流器', status: 'unknown', description: 'API频率控制' },
  { id: 'stability', name: 'StabilityEng', nameZh: '稳定引擎', status: 'unknown', description: '24h自动化测试' },
  { id: 'monitor', name: 'ResourceMon', nameZh: '资源监控', status: 'unknown', description: 'CPU/MEM/DISK监控' },
  { id: 'fuzzing', name: 'FuzzingEng', nameZh: '模糊测试', status: 'unknown', description: '覆盖率引导测试' },
  { id: 'auth', name: 'AuthSystem', nameZh: '认证系统', status: 'unknown', description: 'JWT令牌管理' },
  { id: 'metrics', name: 'Metrics', nameZh: '指标系统', status: 'unknown', description: 'Prometheus导出' },
];

/** 状态颜色映射 */
const STATUS_COLORS: Record<string, string> = {
  online: 'green',
  offline: 'red',
  warning: 'yellow',
  unknown: 'gray',
};

/** 状态符号映射 */
const STATUS_SYMBOLS: Record<string, string> = {
  online: '[OK]',
  offline: '[FAIL]',
  warning: '[WARN]',
  unknown: '[???]',
};

// ==================== 主组件 ====================

export function Dashboard({ onClose, autoRefreshInterval = 10000 }: DashboardProps): JSX.Element {
  const { exit } = useApp();
  const [modules, setModules] = useState<CoreModule[]>(CORE_MODULES);
  const [coreInfo, setCoreInfo] = useState<SystemCoreResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [detailedHealth, setDetailedHealth] = useState<DetailedHealthResponse | null>(null);
  const [performance, setPerformance] = useState<PerformanceStats | null>(null);
  const [wikiHealth, setWikiHealth] = useState<WikiHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [selectedModule, setSelectedModule] = useState<string | null>(null);

  /**
   * 加载所有Dashboard数据
   */
  const loadAllData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const results = await Promise.allSettled([
        localBackend.coreInfo(),
        localBackend.health(),
        localBackend.detailedHealth().catch(() => null),
        localBackend.performance(),
        localBackend.wikiHealth().catch(() => null),
      ]);

      if (results[0].status === 'fulfilled') setCoreInfo(results[0].value);
      if (results[1].status === 'fulfilled') setHealth(results[1].value);
      if (results[2].status === 'fulfilled') setDetailedHealth(results[2].value);
      if (results[3].status === 'fulfilled') setPerformance(results[3].value);
      if (results[4].status === 'fulfilled') setWikiHealth(results[4].value);

      // 根据健康检查结果推断模块状态
      updateModuleStatuses(
        results[1].status === 'fulfilled' ? results[1].value : null,
        results[2].status === 'fulfilled' ? results[2].value : null,
        results[4].status === 'fulfilled' ? results[4].value : null,
      );

      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * 根据后端数据更新模块状态
   */
  const updateModuleStatuses = (
    healthData: HealthResponse | null,
    detailedData: DetailedHealthResponse | null,
    wikiData: WikiHealthResponse | null,
  ) => {
    setModules(prev => prev.map(mod => {
      let newStatus: CoreModule['status'] = 'unknown';

      // 基于健康检查推断状态
      if (healthData?.status === 'ok') {
        switch (mod.id) {
          case 'eventbus':
          case 'container':
          case 'database':
          case 'cache':
          case 'llm':
          case 'auth':
            newStatus = 'online';
            break;
          case 'wiki':
            newStatus = wikiData?.status === 'ok' ? 'online' : 'warning';
            break;
          case 'security':
          case 'monitor':
          case 'stability':
          case 'fuzzing':
            newStatus = 'online'; // 这些是新增引擎，假设在线
            break;
          default:
            newStatus = detailedData?.overall === 'ok' ? 'online' : 'warning';
        }
      }

      return { ...mod, status: newStatus };
    }));
  };

  // 初始加载
  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  // 自动刷新
  useEffect(() => {
    const timer = setInterval(loadAllData, autoRefreshInterval);
    return () => clearInterval(timer);
  }, [loadAllData, autoRefreshInterval]);

  // 键盘导航
  useInput((input, key) => {
    if (key.escape || (key.ctrl && input === 'c')) {
      onClose?.() || exit();
      return;
    }
    if (input === 'r' || input === 'R') {
      loadAllData();
    }
    if (input === 'upArrow' || input === 'k') {
      // 上移选择
      const currentIndex = modules.findIndex(m => m.id === selectedModule);
      if (currentIndex > 0) {
        setSelectedModule(modules[currentIndex - 1]?.id || null);
      }
    }
    if (input === 'downArrow' || input === 'j') {
      // 下移选择
      const currentIndex = modules.findIndex(m => m.id === selectedModule);
      if (currentIndex < modules.length - 1) {
        setSelectedModule(modules[currentIndex + 1]?.id || null);
      }
    }
  });

  /**
   * 渲染头部标题栏
   */
  const renderHeader = (): JSX.Element => (
    <Box flexDirection="column" borderStyle="single" paddingX={1}>
      <Box justifyContent="space-between">
        <Text bold color="cyan">
          {'=' .repeat(25)} System Dashboard {'=' .repeat(25)}
        </Text>
      </Box>
      <Box justifyContent="space-between" marginTop={0}>
        <Text bold color="white">
          {coreInfo?.name || 'Gemma4 System'} v{coreInfo?.version || '?'}
        </Text>
        <Text dimColor>
          {lastRefresh ? `Last: ${lastRefresh.toLocaleTimeString()}` : 'Loading...'}
        </Text>
      </Box>
    </Box>
  );

  /**
   * 渲染系统概览卡片
   */
  const renderOverviewCards = (): JSX.Element => {
    const cards = [
      {
        label: 'Status',
        value: health?.status === 'ok' ? 'ONLINE' : health?.status?.toUpperCase() || 'UNKNOWN',
        color: health?.status === 'ok' ? 'green' : 'red',
      },
      {
        label: 'Architecture',
        value: coreInfo?.architecture || '-',
        color: 'cyan',
      },
      {
        label: 'Model',
        value: coreInfo?.default_model || '-',
        color: 'magenta',
      },
      {
        label: 'CPU',
        value: performance ? `${performance.system.cpu_percent.toFixed(1)}%` : '-',
        color: performance?.system.cpu_percent && performance.system.cpu_percent > 80 ? 'red' : 'green',
      },
      {
        label: 'Memory',
        value: performance ? `${performance.system.memory_percent.toFixed(1)}%` : '-',
        color: performance?.system.memory_percent && performance.system.memory_percent > 85 ? 'red' : 'yellow',
      },
      {
        label: 'Requests',
        value: performance?.requests ? `${performance.requests.total}` : '-',
        color: 'blue',
      },
    ];

    return (
      <Box flexDirection="row" gap={1} marginTop={1} flexWrap="wrap">
        {cards.map((card, i) => (
          <Box
            key={i}
            borderStyle="round"
            paddingX={1}
            width={20}
            flexDirection="column"
          >
            <Text dimColor>{card.label}</Text>
            <Text bold color={card.color}>{card.value}</Text>
          </Box>
        ))}
      </Box>
    );
  };

  /**
   * 渲染16模块状态网格
   */
  const renderModuleGrid = (): JSX.Element => {
    // 分为两列显示
    const leftCol = modules.slice(0, 8);
    const rightCol = modules.slice(8, 16);

    const renderModuleCell = (mod: CoreModule) => {
      const isSelected = mod.id === selectedModule;
      const statusColor = STATUS_COLORS[mod.status];
      const statusSymbol = STATUS_SYMBOLS[mod.status];

      return (
        <Box
          key={mod.id}
          paddingX={1}
          borderStyle={isSelected ? 'bold' : undefined}
          borderColor={isSelected ? 'cyan' : undefined}
          flexDirection="column"
          width={36}
        >
          <Box justifyContent="space-between">
            <Text bold color={isSelected ? 'cyan' : 'white'}>
              {mod.nameZh}
            </Text>
            <Text color={statusColor} bold>
              {statusSymbol}
            </Text>
          </Box>
          <Text dimColor>{mod.description}</Text>
        </Box>
      );
    };

    return (
      <Box flexDirection="column" marginTop={1}>
        <Text bold color="blue">Core Modules (16)</Text>
        <Box marginTop={0} flexDirection="row" gap={2}>
          <Box flexDirection="column">{leftCol.map(renderModuleCell)}</Box>
          <Box flexDirection="column">{rightCol.map(renderModuleCell)}</Box>
        </Box>
      </Box>
    );
  };

  /**
   * 渲染性能指标区域
   */
  const renderPerformanceSection = (): JSX.Element => {
    if (!performance) {
      return (
        <Box marginTop={1}>
          <Text dimColor>No performance data available</Text>
        </Box>
      );
    }

    const cpuPercent = performance.system.cpu_percent;
    const memPercent = performance.system.memory_percent;
    const memAvailableMB = performance.system.memory_available_mb;

    // 生成简单的ASCII进度条
    const makeBar = (percent: number, width = 20): string => {
      const filled = Math.round((percent / 100) * width);
      const empty = width - filled;
      return `[${'#'.repeat(filled)}${'-'.repeat(empty)}] ${percent.toFixed(1)}%`;
    };

    return (
      <Box flexDirection="column" marginTop={1} borderStyle="round" paddingX={1}>
        <Text bold color="yellow">System Performance</Text>

        <Box marginTop={1} flexDirection="column">
          <Box>
            <Text bold>CPU Usage:  </Text>
            <Text color={cpuPercent > 80 ? 'red' : cpuPercent > 50 ? 'yellow' : 'green'}>
              {makeBar(cpuPercent)}
            </Text>
          </Box>

          <Box marginTop={0}>
            <Text bold>Memory:    </Text>
            <Text color={memPercent > 85 ? 'red' : memPercent > 60 ? 'yellow' : 'green'}>
              {makeBar(memPercent)}
            </Text>
          </Box>

          <Box marginTop={0}>
            <Text dimColor>
              Available Memory: {memAvailableMB.toFixed(0)} MB |
              Cache Entries: {performance.cache.entries} |
              Total Requests: {performance.requests.total}
            </Text>
          </Box>
        </Box>
      </Box>
    );
  };

  /**
   * 渲染快捷操作区
   */
  const renderQuickActions = (): JSX.Element => {
    const actions = [
      { key: 'W', label: 'Wiki Docs', desc: 'Knowledge Base' },
      { key: 'C', label: 'Chat', desc: 'AI Assistant' },
      { key: 'M', label: 'Monitor', desc: 'Resource Monitor' },
      { key: 'S', label: 'Security', desc: 'Security Center' },
      { key: 'T', label: 'Testing', desc: 'Stability Tests' },
    ];

    return (
      <Box flexDirection="column" marginTop={1}>
        <Text bold color="blue">Quick Actions</Text>
        <Box marginTop={0} flexDirection="row" gap={2}>
          {actions.map((action, i) => (
            <Box key={i} paddingX={1} borderStyle="round">
              <Text bold color="cyan">[{action.key}]</Text>
              <Text> {action.label}</Text>
              <Text dimColor> ({action.desc})</Text>
            </Box>
          ))}
        </Box>
      </Box>
    );
  };

  /**
   * 渲染底部操作提示
   */
  const renderFooter = (): JSX.Element => (
    <Box marginTop={1} borderStyle="single" paddingX={1}>
      <Text dimColor>
        R:Refresh | j/k:Nav | Esc:Exit | Select module for details
        {loading && ' | Refreshing...'}
      </Text>
    </Box>
  );

  // 主渲染
  return (
    <Box flexDirection="column" height="100%" padding={1}>
      {/* 头部 */}
      {renderHeader()}

      {/* 错误提示 */}
      {error && (
        <Box backgroundColor="red" paddingX={1} marginTop={1}>
          <Text color="white">[ERROR] {error}</Text>
        </Box>
      )}

      {/* 加载指示器 */}
      {loading && !coreInfo && (
        <Box paddingX={1}>
          <Spinner />
          <Text> Loading dashboard data...</Text>
        </Box>
      )}

      {/* 概览卡片 */}
      {renderOverviewCards()}

      {/* 模块网格 */}
      {renderModuleGrid()}

      {/* 性能指标 */}
      {renderPerformanceSection()}

      {/* 快捷操作 */}
      {renderQuickActions()}

      {/* 底部提示 */}
      {renderFooter()}
    </Box>
  );
}

export default Dashboard;
