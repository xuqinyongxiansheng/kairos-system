import React from 'react';
import { Text, Box, Newline } from 'ink';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface MessagesProps {
  messages: Message[];
}

/**
 * 消息显示组件
 */
const Messages: React.FC<MessagesProps> = ({ messages }) => {
  return (
    <Box flexDirection="column" paddingX={2} paddingY={1}>
      {messages.map((message, index) => (
        <Box key={index} marginBottom={2}>
          <Box marginBottom={1}>
            <Text color={message.role === 'user' ? 'green' : 'blue'}>
              {message.role === 'user' ? '用户' : 'Gemma4'}:
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
      ))}
    </Box>
  );
};

export default Messages;
