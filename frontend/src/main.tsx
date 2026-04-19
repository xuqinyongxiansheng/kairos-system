import React from 'react';
import { render } from 'ink';
import Gemma4App from './components/Gemma4App.js';

/**
 * Gemma4 自主工作系统前端入口
 * 与Python后端集成的终端UI
 * 复刻目标UI的设计和功能
 */
export function main() {
  console.log('='.repeat(60));
  console.log('  Gemma4 Autonomous Work System');
  console.log('  Version: 1.0.0');
  console.log('  Mode: Frontend Terminal Interface');
  console.log('='.repeat(60));
  console.log('');
  console.log('Starting frontend interface...');
  console.log('');

  // 渲染Ink终端UI
  render(<Gemma4App />);
}

// 直接运行（如果作为主模块）
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
