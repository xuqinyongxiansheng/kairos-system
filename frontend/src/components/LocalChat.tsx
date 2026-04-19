/**
 * 本地后端Chat组件
 *
 * 支持SSE流式输出的智能对话组件，特性：
 * - 实时打字机效果（SSE streaming）
 * - 消息历史管理
 * - 自动重连与错误恢复
 * - 上下文感知（传递对话历史）
 * - 支持V2 API的streaming模式
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Text, Box, useInput } from 'ink';
import Spinner from '../components/Spinner.js';
import { localBackend, type ChatRequestV2 } from '../services/api/localBackend.js';

// ==================== 类型定义 ====================

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'error';
  content: string;
  timestamp: number;
  isStreaming?: boolean;
}

interface LocalChatProps {
  /** 初始消息列表 */
  initialMessages?: Message[];
  /** 系统提示词 */
  systemPrompt?: string;
  /** 默认模型 */
  defaultModel?: string;
  /** 是否启用流式输出 */
  enableStreaming?: boolean;
  /** 最大保留消息数 */
  maxHistoryLength?: number;
  /** 发送消息回调 */
  onMessageSent?: (message: string) => void;
  /** 收到回复回调 */
  onMessageReceived?: (response: string) => void;
  /** 错误回调 */
  onError?: (error: Error) => void;
}

// ==================== 常量 ====================

const DEFAULT_SYSTEM_PROMPT = `You are Gemma4, an intelligent assistant powered by a local FastAPI backend.
You are helpful, concise, and accurate. When responding:
1. Use clear formatting with markdown when appropriate
2. Provide code examples when relevant
3. If you don't know something, say so honestly
4. Keep responses focused and to the point`;

// ==================== 主组件 ====================

export function LocalChat({
  initialMessages,
  systemPrompt = DEFAULT_SYSTEM_PROMPT,
  defaultModel,
  enableStreaming = true,
  maxHistoryLength = 50,
  onMessageSent,
  onMessageReceived,
  onError,
}: LocalChatProps): JSX.Element {
  // 状态管理
  const [messages, setMessages] = useState<Message[]>(
    initialMessages || [
      {
        id: 'welcome',
        role: 'assistant',
        content: 'Welcome! I am your intelligent assistant connected to the local backend. How can I help you?',
        timestamp: Date.now(),
      },
    ],
  );
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentStreamingId, setCurrentStreamingId] = useState<string | null>(null);

  // Refs用于避免闭包问题
  const messagesRef = useRef(messages);
  const inputRef = useRef(input);
  const abortControllerRef = useRef<AbortController | null>(null);

  // 保持ref同步
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    inputRef.current = input;
  }, [input]);

  /**
   * 生成唯一ID
   */
  const generateId = (): string => {
    return `${Date.now()}-${Math.random().toString(36).substring(7)}`;
  };

  /**
   * 添加消息到列表
   */
  const addMessage = useCallback((message: Message) => {
    setMessages(prev => {
      const newMessages = [...prev, message];
      // 限制历史长度
      if (newMessages.length > maxHistoryLength) {
        return newMessages.slice(-maxHistoryLength);
      }
      return newMessages;
    });
  }, [maxHistoryLength]);

  /**
   * 更新正在流式传输的消息内容
   */
  const updateStreamingMessage = useCallback((id: string, content: string) => {
    setMessages(prev =>
      prev.map(msg =>
        msg.id === id ? { ...msg, content, isStreaming: true } : msg,
      ),
    );
  }, []);

  /**
   * 标记流式消息完成
   */
  const finishStreamingMessage = useCallback((id: string) => {
    setMessages(prev =>
      prev.map(msg =>
        msg.id === id ? { ...msg, isStreaming: false } : msg,
      ),
    );
    setCurrentStreamingId(null);
  }, []);

  /**
   * 发送消息并获取响应
   */
  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content: text.trim(),
      timestamp: Date.now(),
    };

    addMessage(userMessage);
    setInput('');
    setIsLoading(true);
    onMessageSent?.(text.trim());

    try {
      // 准备请求体（包含上下文）
      const recentMessages = messagesRef.current
        .filter(m => m.role === 'user' || m.role === 'assistant')
        .slice(-10); // 最近10条消息作为上下文

      const request: ChatRequestV2 = {
        message: text.trim(),
        model: defaultModel,
        stream: enableStreaming,
        context: {
          system_prompt: systemPrompt,
          conversation_history: recentMessages.map(m => ({
            role: m.role,
            content: m.content,
          })),
        },
      };

      if (enableStreaming) {
        // 使用SSE流式模式
        const assistantMsgId = generateId();
        const assistantMsg: Message = {
          id: assistantMsgId,
          role: 'assistant',
          content: '',
          timestamp: Date.now(),
          isStreaming: true,
        };
        addMessage(assistantMsg);
        setCurrentStreamingId(assistantMsgId);

        await localBackend.chatV2(
          request,
          // onMessage callback - 接收每个chunk
          (data: string) => {
            try {
              const parsed = JSON.parse(data);
              const chunk = parsed.response || parsed.content || data;
              updateStreamingMessage(
                assistantMsgId,
                messagesRef.current.find(m => m.id === assistantMsgId)?.content + chunk,
              );
              onMessageReceived?.(chunk);
            } catch {
              // 如果不是JSON，直接追加文本
              updateStreamingMessage(
                assistantMsgId,
                messagesRef.current.find(m => m.id === assistantMsgId)?.content + data,
              );
              onMessageReceived?.(data);
            }
          },
          // onComplete callback
          () => {
            finishStreamingMessage(assistantMsgId);
            setIsLoading(false);
          },
          // onError callback
          (error: Error) => {
            finishStreamingMessage(assistantMsgId);
            setIsLoading(false);

            // 添加错误消息
            addMessage({
              id: generateId(),
              role: 'error',
              content: `[Error] ${error.message}`,
              timestamp: Date.now(),
            });
            onError?.(error);
          },
        );
      } else {
        // 非流式模式
        const response = await localBackend.chatV2(request);

        addMessage({
          id: generateId(),
          role: 'assistant',
          content: response.response,
          timestamp: Date.now(),
        });
        setIsLoading(false);
        onMessageReceived?.(response.response);
      }
    } catch (error) {
      setIsLoading(false);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';

      addMessage({
        id: generateId(),
        role: 'error',
        content: `[Connection Error] ${errorMessage}\n\nTips:\n- Ensure the backend server is running on http://localhost:8000\n- Check network connectivity\n- Try again later`,
        timestamp: Date.now(),
      });
      onError?.(error as Error);
    }
  }, [
    isLoading,
    defaultModel,
    enableStreaming,
    systemPrompt,
    addMessage,
    updateStreamingMessage,
    finishStreamingMessage,
    onMessageSent,
    onMessageReceived,
    onError,
  ]);

  /**
   * 中止当前请求
   */
  const abortRequest = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    if (currentStreamingId) {
      finishStreamingMessage(currentStreamingId);
    }

    setIsLoading(false);
  }, [currentStreamingId, finishStreamingMessage]);

  /**
   * 清空消息历史
   */
  const clearMessages = useCallback(() => {
    setMessages([
      {
        id: generateId(),
        role: 'system',
        content: '[Conversation cleared]',
        timestamp: Date.now(),
      },
    ]);
  }, []);

  // 键盘输入处理
  useInput((inputChar, key) => {
    // Ctrl+C 或 Escape 中止当前请求
    if ((key.ctrl && inputChar === 'c') || key.escape) {
      if (isLoading) {
        abortRequest();
        return;
      }
    }

    // Enter 发送消息
    if (key.return && inputRef.current.trim()) {
      sendMessage(inputRef.current);
      return;
    }
  });

  /**
   * 渲染单条消息
   */
  const renderMessage = (message: Message): JSX.Element => {
    const isUser = message.role === 'user';
    const isError = message.role === 'error';
    const isSystem = message.role === 'system';

    let prefix = '';
    let color: string | undefined;

    switch (message.role) {
      case 'user':
        prefix = '> ';
        color = 'cyan';
        break;
      case 'assistant':
        prefix = '';
        color = undefined;
        break;
      case 'error':
        prefix = '[ERROR] ';
        color = 'red';
        break;
      case 'system':
        prefix = '[SYSTEM] ';
        color = 'yellow';
        break;
    }

    return (
      <Box key={message.id} flexDirection="column" marginBottom={1} paddingX={1}>
        <Box>
          <Text bold color={isUser ? 'cyan' : isError ? 'red' : 'yellow'}>
            {prefix}
          </Text>
          <Text color={color} wrap="wrap">
            {message.content}
            {message.isStreaming && <Text dimColor>▌</Text>}
          </Text>
        </Box>
        {!isSystem && (
          <Text dimColor>
            {new Date(message.timestamp).toLocaleTimeString()}
          </Text>
        )}
      </Box>
    );
  };

  return (
    <Box flexDirection="column" height="100%">
      {/* 消息列表 */}
      <Box flex={1} overflow="scroll" paddingX={1}>
        {messages.map(renderMessage)}

        {/* 加载状态 */}
        {isLoading && !currentStreamingId && (
          <Box paddingX={1}>
            <Spinner />
            <Text> Thinking...</Text>
          </Box>
        )}
      </Box>

      {/* 输入区域 */}
      <Box borderStyle="single" paddingX={1}>
        <Box flexDirection="row">
          <Text bold color="green">{'> '}</Text>
          <Text wrap="wrap" color={isLoading ? 'dim' : undefined}>
            {input || (isLoading ? '(processing...)' : '(type your message and press Enter)')}
          </Text>
          {isLoading && (
            <Text color="yellow"> [Ctrl+C to cancel]</Text>
          )}
        </Box>

        {/* 操作提示 */}
        <Box marginTop={0}>
          <Text dimColor>
            Enter:Send | Ctrl+C:Cancel{enableStreaming ? ' | Streaming:ON' : ''}
          </Text>
        </Box>
      </Box>
    </Box>
  );
}

export default LocalChat;
