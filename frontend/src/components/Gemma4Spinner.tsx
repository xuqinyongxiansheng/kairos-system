import React, { useState, useEffect } from 'react';
import { Text, Box } from 'ink';

interface Gemma4SpinnerProps {
  text: string;
}

/**
 * Gemma4 加载状态组件
 * 复刻目标UI的加载状态功能
 */
const Gemma4Spinner: React.FC<Gemma4SpinnerProps> = ({ text }) => {
  const [frame, setFrame] = useState(0);
  const frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];

  useEffect(() => {
    const interval = setInterval(() => {
      setFrame((prevFrame) => (prevFrame + 1) % frames.length);
    }, 100);

    return () => clearInterval(interval);
  }, [frames.length]);

  return (
    <Box alignItems="center">
      <Text>{frames[frame]}</Text>
      <Text marginLeft={1}>{text}</Text>
    </Box>
  );
};

export default Gemma4Spinner;
