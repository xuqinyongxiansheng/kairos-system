import React, { useRef, useEffect } from 'react';
import { Text, Box, useInput } from 'ink';

interface TextInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  placeholder?: string;
}

/**
 * 文本输入组件
 */
const TextInput: React.FC<TextInputProps> = ({ value, onChange, onSubmit, placeholder = '' }) => {
  const inputRef = useRef<HTMLInputElement>(null);

  // 处理键盘输入
  useInput((input, key) => {
    if (key.return) {
      onSubmit(value);
    } else if (key.backspace) {
      onChange(value.slice(0, -1));
    } else if (input) {
      onChange(value + input);
    }
  });

  return (
    <Box borderTop={1} paddingX={2} paddingY={1}>
      <Text color="yellow">> </Text>
      <Text>{value || placeholder}</Text>
    </Box>
  );
};

export default TextInput;
