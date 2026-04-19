import React, { useState, useEffect } from 'react';
import { Text, Box, Newline } from 'ink';
import Messages from './Messages.js';
import TextInput from './TextInput.js';
import { useBackend } from '../context/backendContext.js';
import { localBackend } from '../services/api/localBackend.js';

/**
 * Gemma4 自主工作系统主界面
 *
 * 已桥接到本地FastAPI后端，支持：
 * - 实时AI对话（通过本地/api/chat端点）
 * - 系统状态显示（从后端实时获取）
 * - 健康检查与性能监控
 */
const App: React.FC = () => {
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([
    {
      role: 'assistant',
      content: 'Welcome to Gemma4 Autonomous Work System! I am your intelligent assistant, how can I help you?'
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // 获取后端状态
  const { health, coreInfo, performance, config, isLoading: isBackendLoading, error: backendError } = useBackend();

  // 与本地FastAPI后端通信（替换原来的模拟代码）
  const handleSubmit = async (value: string) => {
    if (!value.trim()) return;

    // 添加用户消息
    setMessages(prev => [...prev, { role: 'user', content: value }]);
    setInput('');
    setIsLoading(true);

    try {
      // 调用本地FastAPI的 /api/chat 端点
      const response = await localBackend.chat({
        message: value,
        model: coreInfo?.default_model || undefined,
      });

      if (response.status === 'ok') {
        setMessages(prev => [...prev, { role: 'assistant', content: response.response }]);
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: `[Error] ${response.response}` }]);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      setMessages(prev => [...prev, { role: 'assistant', content: `[Connection Error] ${errorMessage}\n\nPlease ensure the backend server is running on http://localhost:8000` }]);
    } finally {
      setIsLoading(false);
    }
  };

  // 构建系统状态栏文本
  const buildStatusBarText = (): string => {
    const parts: string[] = [];

    // 后端连接状态
    if (config.mode === 'local') {
      if (config.isHealthy === true) {
        parts.push('Backend: [OK]');
      } else if (config.isHealthy === false) {
        parts.push('Backend: [FAIL]');
      } else {
        parts.push('Backend: [CHECKING...]');
      }

      // 系统版本
      if (coreInfo) {
        parts.push(`${coreInfo.name} v${coreInfo.version}`);
      }

      // 性能指标
      if (performance) {
        const memPercent = performance.system.memory_percent.toFixed(1);
        const cpuPercent = performance.system.cpu_percent.toFixed(1);
        parts.push(`MEM:${memPercent}% CPU:${cpuPercent}%`);
      }
    } else {
      parts.push('Mode: Cloud API');
    }

    return parts.join(' | ');
  };

  return (
    <Box flexDirection="column" height="100%">
      {/* 系统状态栏 */}
      <Box backgroundColor="gray" paddingX={1}>
        <Text dimColor bold>{buildStatusBarText()}</Text>
      </Box>

      {/* 错误提示 */}
      {backendError && (
        <Box backgroundColor="red" paddingX={1}>
          <Text color="white">[ERROR] {backendError.message}</Text>
        </Box>
      )}

      {/* 主消息区域 */}
      <Box flex={1} overflow="scroll">
        <Messages messages={messages} />
        {isLoading && (
          <Box paddingX={2}>
            <Text>Thinking...</Text>
          </Box>
        )}
      </Box>

      {/* 输入框 */}
      <TextInput value={input} onChange={setInput} onSubmit={handleSubmit} placeholder="Enter your command..." />
    </Box>
  );
};

export default App;
