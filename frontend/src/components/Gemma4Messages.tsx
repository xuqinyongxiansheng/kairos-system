import React, { useMemo } from 'react';
import { Box, Text, Newline } from 'ink';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface Gemma4MessagesProps {
  messages: Message[];
  isTranscriptMode: boolean;
  showAllInTranscript: boolean;
  streamingText: string | null;
}

/**
 * Gemma4 消息显示组件
 * 复刻目标UI的消息显示功能
 */
const Gemma4Messages: React.FC<Gemma4MessagesProps> = ({ 
  messages, 
  isTranscriptMode, 
  showAllInTranscript, 
  streamingText 
}) => {
  // 处理消息截断
  const displayedMessages = useMemo(() => {
    if (!isTranscriptMode || showAllInTranscript) {
      return messages;
    }
    // 在转录模式下默认只显示最近的30条消息
    const MAX_MESSAGES = 30;
    if (messages.length > MAX_MESSAGES) {
      return messages.slice(-MAX_MESSAGES);
    }
    return messages;
  }, [messages, isTranscriptMode, showAllInTranscript]);

  // 渲染单个消息
  const renderMessage = (message: Message, index: number) => {
    const isUser = message.role === 'user';
    const isAssistant = message.role === 'assistant';
    
    return (
      <Box key={index} marginBottom={2}>
        <Box marginBottom={1}>
          <Text color={isUser ? 'green' : 'blue'}>
            {isUser ? 'User' : 'Gemma4'}:
          </Text>
        </Box>
        <Box paddingLeft={4}>
          {message.content.split('\n').map((line, lineIndex) => (
            <React.Fragment key={lineIndex}>
              <Text>{line}</Text>
              <Newline />
            </React.Fragment>
          ))}
        </Box>
      </Box>
    );
  };

  // 渲染流式文本
  const renderStreamingText = () => {
    if (!streamingText) return null;
    
    return (
      <Box marginBottom={2}>
        <Box marginBottom={1}>
          <Text color="blue">Gemma4:</Text>
        </Box>
        <Box paddingLeft={4}>
          {streamingText.split('\n').map((line, lineIndex) => (
            <React.Fragment key={lineIndex}>
              <Text>{line}</Text>
              <Newline />
            </React.Fragment>
          ))}
        </Box>
      </Box>
    );
  };

  // 渲染截断提示
  const renderTruncationIndicator = () => {
    if (!isTranscriptMode || showAllInTranscript || messages.length <= 30) {
      return null;
    }
    
    const hiddenCount = messages.length - 30;
    return (
      <Box marginBottom={2}>
        <Box borderStyle="single" paddingX={2} paddingY={1}>
          <Text dimColor>
            {hiddenCount} previous messages hidden · Ctrl+E to show all
          </Text>
        </Box>
      </Box>
    );
  };

  return (
    <Box flexDirection="column" paddingX={2} paddingY={1}>
      {renderTruncationIndicator()}
      {displayedMessages.map(renderMessage)}
      {renderStreamingText()}
    </Box>
  );
};

export default Gemma4Messages;
