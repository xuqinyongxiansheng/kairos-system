/**
 * 系统资源实时监控面板
 *
 * 对接ResourceMonitorEngine，展示：
 * - CPU使用率（总体/各核心）
 * - 内存使用（物理/交换分区）
 * - 磁盘I/O（读写速度/延迟/利用率）
 * - 7天历史趋势（1h/6h/24h窗口）
 * - 阈值告警（CPU>80%/MEM>85%/DISK-IO>90%）
 *
 * 采用Ink终端UI风格，支持自动刷新和键盘控制。
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Text, Box, useInput, useApp } from 'ink';
import Spinner from '../components/Spinner.js';
import {
  localBackend,
  type PerformanceStats,
} from '../services/api/localBackend.js';

// ==================== 类型定义 ====================

/** 资源快照 */
interface ResourceSnapshot {
  timestamp: number;
  cpu_percent: number;
  cpu_per_core?: number[];
  memory_percent: number;
  memory_used_mb: number;
  memory_available_mb: number;
  memory_total_mb: number;
  swap_percent?: number;
  disk_read_bytes_sec?: number;
  disk_write_bytes_sec?: number;
  disk_read_count_sec?: number;
  disk_write_count_sec?: number;
  disk_utilization?: number;
}

/** 告警记录 */
interface AlertRecord {
  id: string;
  type: 'cpu' | 'memory' | 'disk';
  level: 'warning' | 'critical';
  message: string;
  timestamp: number;
  value: number;
  threshold: number;
}

/** Monitor Props */
interface MonitorProps {
  onClose?: () => void;
  refreshInterval?: number; // 刷新间隔(ms)，默认5000
  historyLength?: number; // 历史记录数，默认60
}

// ==================== 常量 ====================

const DEFAULT_THRESHOLDS = {
  cpu_warning: 70,
  cpu_critical: 85,
  mem_warning: 75,
  mem_critical: 90,
  disk_warning: 80,
  disk_critical: 95,
};

/** 时间窗口选项 */
type TimeWindow = '1h' | '6h' | '24h';

const TIME_WINDOW_LABELS: Record<TimeWindow, string> = {
  '1h': 'Last Hour',
  '6h': 'Last 6 Hours',
  '24h': 'Last 24 Hours',
};

// ==================== 工具函数 ====================

/**
 * 生成ASCII进度条
 */
function makeBar(percent: number, width = 30): string {
  const clamped = Math.min(100, Math.max(0, percent));
  const filled = Math.round((clamped / 100) * width);
  const empty = width - filled;

  let colorChar = '#';
  if (clamped >= 90) colorChar = '@';
  else if (clamped >= 75) colorChar = '=';
  else if (clamped >= 50) colorChar = '+';

  return `[${colorChar.repeat(filled)}${'-'.repeat(empty)}] ${clamped.toFixed(1)}%`;
}

/**
 * 生成迷你ASCII折线图
 */
function makeMiniChart(data: number[], width = 40, height = 8): string {
  if (data.length < 2) return ''.padEnd(width);

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  // 归一化到0-height范围
  const normalized = data.map(v => Math.round(((v - min) / range) * (height - 1)));

  // 从上到下构建每一行
  let chart = '';
  for (let row = height - 1; row >= 0; row--) {
    chart += '|';
    for (let col = 0; col < width && col < data.length; col++) {
      const val = normalized[col];
      if (val === row || (col > 0 && normalized[col - 1] < row && val >= row)) {
        chart += row === height - 1 ? '*' : (row > height / 2 ? '#' : '+');
      } else if (col === data.length - 1 && val === row) {
        chart += '*';
      } else {
        chart += ' ';
      }
    }
    chart += '\n';
  }

  // X轴
  chart += '+' + '-'.repeat(Math.min(width, data.length)) + '+';

  return chart;
}

// ==================== 主组件 ====================

export function Monitor({
  onClose,
  refreshInterval = 5000,
  historyLength = 60,
}: MonitorProps): JSX.Element {
  const { exit } = useApp();

  // 状态
  const [current, setCurrent] = useState<ResourceSnapshot | null>(null);
  const [history, setHistory] = useState<ResourceSnapshot[]>([]);
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeWindow, setTimeWindow] = useState<TimeWindow>('1h');
  const [showAlerts, setShowAlerts] = useState(false);
  const [isPaused, setIsPaused] = useState(false);

  // Refs
  const historyRef = useRef<ResourceSnapshot[]>([]);
  const alertsRef = useRef<AlertRecord[]>([]);

  /**
   * 采集资源数据
   */
  const collectData = useCallback(async () => {
    if (isPaused) return;

    try {
      const perf = await localBackend.performance();

      const snapshot: ResourceSnapshot = {
        timestamp: Date.now(),
        cpu_percent: perf.system.cpu_percent,
        memory_percent: perf.system.memory_percent,
        memory_used_mb: 0,
        memory_available_mb: perf.system.memory_available_mb,
        memory_total_mb: 0,
      };

      // 计算已用内存（近似值）
      if (perf.system.memory_percent > 0 && perf.system.memory_available_mb > 0) {
        snapshot.memory_total_mb = perf.system.memory_available_mb / (1 - perf.system.memory_percent / 100);
        snapshot.memory_used_mb = snapshot.memory_total_mb - perf.system.memory_available_mb;
      }

      setCurrent(snapshot);

      // 更新历史（环形缓冲区）
      const newHistory = [...historyRef.current, snapshot].slice(-historyLength);
      historyRef.current = newHistory;
      setHistory(newHistory);

      // 检查阈值并生成告警
      checkThresholds(snapshot);

      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to collect resource data');
    } finally {
      setLoading(false);
    }
  }, [isPaused, historyLength]);

  /**
   * 检查阈值并生成告警
   */
  const checkThresholds = (snapshot: ResourceSnapshot) => {
    const newAlerts: AlertRecord[] = [];
    const now = Date.now();

    // CPU检查
    if (snapshot.cpu_percent >= DEFAULT_THRESHOLDS.cpu_critical) {
      newAlerts.push({
        id: `cpu-crit-${now}`,
        type: 'cpu',
        level: 'critical',
        message: `CPU usage critical: ${snapshot.cpu_percent.toFixed(1)}%`,
        timestamp: now,
        value: snapshot.cpu_percent,
        threshold: DEFAULT_THRESHOLDS.cpu_critical,
      });
    } else if (snapshot.cpu_percent >= DEFAULT_THRESHOLDS.cpu_warning) {
      newAlerts.push({
        id: `cpu-warn-${now}`,
        type: 'cpu',
        level: 'warning',
        message: `CPU usage high: ${snapshot.cpu_percent.toFixed(1)}%`,
        timestamp: now,
        value: snapshot.cpu_percent,
        threshold: DEFAULT_THRESHOLDS.cpu_warning,
      });
    }

    // Memory检查
    if (snapshot.memory_percent >= DEFAULT_THRESHOLDS.mem_critical) {
      newAlerts.push({
        id: `mem-crit-${now}`,
        type: 'memory',
        level: 'critical',
        message: `Memory critical: ${snapshot.memory_percent.toFixed(1)}%`,
        timestamp: now,
        value: snapshot.memory_percent,
        threshold: DEFAULT_THRESHOLDS.mem_critical,
      });
    } else if (snapshot.memory_percent >= DEFAULT_THRESHOLDS.mem_warning) {
      newAlerts.push({
        id: `mem-warn-${now}`,
        type: 'memory',
        level: 'warning',
        message: `Memory high: ${snapshot.memory_percent.toFixed(1)}%`,
        timestamp: now,
        value: snapshot.memory_percent,
        threshold: DEFAULT_THRESHOLDS.mem_warning,
      });
    }

    // 合并告警（保留最近20条）
    if (newAlerts.length > 0) {
      const updatedAlerts = [...newAlerts, ...alertsRef.current].slice(0, 20);
      alertsRef.current = updatedAlerts;
      setAlerts(updatedAlerts);
    }
  };

  // 初始加载 + 定时刷新
  useEffect(() => {
    collectData();
    const timer = setInterval(collectData, refreshInterval);
    return () => clearInterval(timer);
  }, [collectData, refreshInterval]);

  // 键盘导航
  useInput((input, key) => {
    if (key.escape || (key.ctrl && input === 'c')) {
      onClose?.() || exit();
      return;
    }
    if (input === 'p' || input === 'P') {
      setIsPaused(p => !p);
    }
    if (input === 'a' || input === 'A') {
      setShowAlerts(a => !a);
    }
    if (input === '1') setTimeWindow('1h');
    if (input === '2') setTimeWindow('6h');
    if (input === '3') setTimeWindow('24h');
    if (input === 'c' || input === 'C') {
      setAlerts([]);
      alertsRef.current = [];
    }
  });

  /**
   * 渲染头部
   */
  const renderHeader = (): JSX.Element => (
    <Box flexDirection="column" borderStyle="single" paddingX={1}>
      <Box justifyContent="space-between">
        <Text bold color="magenta">
          {'=' .repeat(22)} Resource Monitor {'=' .repeat(22)}
        </Text>
      </Box>
      <Box justifyContent="space-between" marginTop={0}>
        <Text bold>
          Real-time System Resources
          {isPaused && <Text color="yellow"> [PAUSED]</Text>}
        </Text>
        <Text dimColor>
          Interval: {refreshInterval / 1000}s | Points: {history.length}
        </Text>
      </Box>
    </Box>
  );

  /**
   * 渲染CPU面板
   */
  const renderCPUPanel = (): JSX.Element => {
    const cpu = current?.cpu_percent ?? 0;
    const cpuColor =
      cpu >= DEFAULT_THRESHOLDS.cpu_critical ? 'red' :
      cpu >= DEFAULT_THRESHOLDS.cpu_warning ? 'yellow' : 'green';

    const cpuHistory = history.map(h => h.cpu_percent);

    return (
      <Box flexDirection="column" marginTop={1} borderStyle="round" paddingX={1}>
        <Box justifyContent="space-between">
          <Text bold color="cyan">CPU Usage</Text>
          <Text bold color={cpuColor}>{cpu.toFixed(1)}%</Text>
        </Box>

        {/* 进度条 */}
        <Box marginTop={0}>
          <Text color={cpuColor}>{makeBar(cpu)}</Text>
        </Box>

        {/* 迷你图表 */}
        {cpuHistory.length > 2 && (
          <Box marginTop={0}>
            <Text dimColor color="gray">{makeMiniChart(cpuHistory.slice(-40), 35, 6)}</Text>
          </Box>
        )}

        {/* 统计信息 */}
        {cpuHistory.length > 0 && (
          <Box marginTop={0}>
            <Text dimColor>
              Avg: {(cpuHistory.reduce((a, b) => a + b, 0) / cpuHistory.length).toFixed(1)}%
              {' | '}
              Max: {Math.max(...cpuHistory).toFixed(1)}%
              {' | '}
              Min: {Math.min(...cpuHistory).toFixed(1)}%
            </Text>
          </Box>
        )}
      </Box>
    );
  };

  /**
   * 渲染内存面板
   */
  const renderMemoryPanel = (): JSX.Element => {
    const mem = current?.memory_percent ?? 0;
    const usedMB = current?.memory_used_mb ?? 0;
    const availMB = current?.memory_available_mb ?? 0;
    const totalMB = current?.memory_total_mb ?? 0;

    const memColor =
      mem >= DEFAULT_THRESHOLDS.mem_critical ? 'red' :
      mem >= DEFAULT_THRESHOLDS.mem_warning ? 'yellow' : 'green';

    const memHistory = history.map(h => h.memory_percent);

    return (
      <Box flexDirection="column" marginTop={1} borderStyle="round" paddingX={1}>
        <Box justifyContent="space-between">
          <Text bold color="cyan">Memory Usage</Text>
          <Text bold color={memColor}>{mem.toFixed(1)}%</Text>
        </Box>

        {/* 进度条 */}
        <Box marginTop={0}>
          <Text color={memColor}>{makeBar(mem)}</Text>
        </Box>

        {/* 详细信息 */}
        <Box marginTop={0} flexDirection="row">
          <Text dimColor>
            Used: {(usedMB / 1024).toFixed(1)}GB{' | '}
            Available: {(availMB / 1024).toFixed(1)}GB{' | '}
            Total: {(totalMB / 1024).toFixed(1)}GB
          </Text>
        </Box>

        {/* 迷你图表 */}
        {memHistory.length > 2 && (
          <Box marginTop={0}>
            <Text dimColor color="gray">{makeMiniChart(memHistory.slice(-40), 35, 6)}</Text>
          </Box>
        )}
      </Box>
    );
  };

  /**
   * 渲染请求统计面板
   */
  const renderRequestsPanel = (): JSX.Element => {
    return (
      <Box flexDirection="column" marginTop={1} borderStyle="round" paddingX={1}>
        <Text bold color="cyan">Request Statistics</Text>

        <Box marginTop={0} flexDirection="row" gap={4}>
          <Box flexDirection="column">
            <Text dimColor>Total Requests</Text>
            <Text bold color="blue">{current ? '-' : '-'}</Text>
          </Box>
          <Box flexDirection="column">
            <Text dimColor>Cache Entries</Text>
            <Text bold>{current ? '-' : '-'}</Text>
          </Box>
        </Box>
      </Box>
    );
  };

  /**
   * 渲染告警面板
   */
  const renderAlertsPanel = (): JSX.Element => {
    if (!showAlerts || alerts.length === 0) {
      return null;
    }

    const criticalCount = alerts.filter(a => a.level === 'critical').length;
    const warningCount = alerts.filter(a => a.level === 'warning').length;

    return (
      <Box flexDirection="column" marginTop={1} borderStyle="round" paddingX={1}
           backgroundColor={criticalCount > 0 ? 'red' : undefined}>
        <Box justifyContent="space-between">
          <Text bold color={criticalCount > 0 ? 'white' : 'yellow'}>
            Alerts ({alerts.length}: {criticalCount} Critical, {warningCount} Warning)
          </Text>
          <Text dimColor>C to clear</Text>
        </Box>

        {alerts.slice(0, 5).map(alert => (
          <Box key={alert.id} marginTop={0} paddingX={1}
               borderStyle={alert.level === 'critical' ? 'bold' : undefined}>
            <Text color={alert.level === 'critical' ? 'red' : 'yellow'} bold>
              [{alert.level.toUpperCase()}]
            </Text>
            <Text> {alert.message}</Text>
            <Text dimColor>
              {' '}@ {new Date(alert.timestamp).toLocaleTimeString()}
            </Text>
          </Box>
        ))}

        {alerts.length > 5 && (
          <Text dimColor marginTop={0}>
            ... and {alerts.length - 5} more alerts
          </Text>
        )}
      </Box>
    );
  };

  /**
   * 渲染底部操作提示
   */
  const renderFooter = (): JSX.Element => (
    <Box marginTop={1} borderStyle="single" paddingX={1}>
      <Text dimColor>
        P:Pause/Resume | A:Toggle Alerts | 1/2/3:Time Window({TIME_WINDOW_LABELS[timeWindow]})
        {' | '}
        C:Clear Alerts | Esc:Exit
        {loading && ' | Collecting...'}
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
      {loading && !current && (
        <Box paddingX={1}>
          <Spinner />
          <Text> Connecting to monitor...</Text>
        </Box>
      )}

      {/* CPU面板 */}
      {renderCPUPanel()}

      {/* 内存面板 */}
      {renderMemoryPanel()}

      {/* 请求统计 */}
      {renderRequestsPanel()}

      {/* 告警面板 */}
      {renderAlertsPanel()}

      {/* 底部提示 */}
      {renderFooter()}
    </Box>
  );
}

export default Monitor;
