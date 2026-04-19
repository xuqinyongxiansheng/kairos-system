/**
 * 应用路由配置
 *
 * 管理所有页面路由和导航状态。
 * 由于是Ink终端UI（非浏览器），使用状态驱动的简单路由方案。
 *
 * 支持的页面：
 * - / (Home) - 主聊天界面
 * - /dashboard - 系统仪表盘
 * - /monitor  - 资源监控
 * - /security - 安全中心
 * - /wiki     - Wiki知识库
 */

import React, { useState, useCallback } from 'react';
import { Text, Box, useInput } from 'ink';

// ==================== 路由定义 ====================

/** 页面路径 */
export type RoutePath =
  | '/'
  | '/dashboard'
  | '/monitor'
  | '/security'
  | '/wiki'
  | '/chat';

/** 路由信息 */
export interface RouteInfo {
  path: RoutePath;
  label: string;
  labelZh: string;
  shortcut: string;
  icon: string;
  description: string;
}

/** 所有可用路由 */
export const ROUTES: RouteInfo[] = [
  {
    path: '/',
    label: 'Home',
    labelZh: '首页',
    shortcut: 'H',
    icon: '[HOME]',
    description: 'AI Chat Interface',
  },
  {
    path: '/dashboard',
    label: 'Dashboard',
    labelZh: '仪表盘',
    shortcut: 'D',
    icon: '[DASH]',
    description: 'System Overview & Modules',
  },
  {
    path: '/monitor',
    label: 'Monitor',
    labelZh: '监控中心',
    shortcut: 'M',
    icon: '[MON]',
    description: 'Real-time Resource Monitor',
  },
  {
    path: '/security',
    label: 'Security',
    labelZh: '安全中心',
    shortcut: 'S',
    icon: '[SEC]',
    description: '115 Rules & OWASP Coverage',
  },
  {
    path: '/wiki',
    label: 'Wiki',
    labelZh: '知识库',
    shortcut: 'W',
    icon: '[WIKI]',
    description: 'Document Management',
  },
];

// ==================== 路由Hook ====================

/**
 * 自定义路由Hook
 *
 * 使用方式：
 * ```tsx
 * function App() {
 *   const { currentRoute, navigate } = useAppRouter();
 *
 *   return (
 *     <>
 *       <NavBar current={currentRoute} onNavigate={navigate} />
 *       {currentRoute === '/' && <HomePage />}
 *       {currentRoute === '/dashboard' && <Dashboard />}
 *       ...
 *     </>
 *   );
 * }
 * ```
 */
export function useAppRouter() {
  const [currentRoute, setCurrentRoute] = useState<RoutePath>('/');

  const navigate = useCallback((path: RoutePath) => {
    setCurrentRoute(path);
  }, []);

  /**
   * 根据快捷键导航
   */
  const navigateByShortcut = useCallback((key: string) => {
    const route = ROUTES.find(r =>
      r.shortcut.toLowerCase() === key.toLowerCase()
    );
    if (route) {
      setCurrentRoute(route.path);
      return true;
    }
    return false;
  }, []);

  return {
    currentRoute,
    navigate,
    navigateByShortcut,
    routes: ROUTES,
  };
}

// ==================== 导航栏组件 ====================

interface NavBarProps {
  currentRoute: RoutePath;
  onNavigate: (path: RoutePath) => void;
}

/**
 * 导航栏组件
 *
 * 显示所有可用的页面入口，高亮当前页面。
 */
export function NavBar({ currentRoute, onNavigate }: NavBarProps): JSX.Element {
  return (
    <Box borderStyle="single" paddingX={1}>
      <Box flexDirection="row" gap={1}>
        {ROUTES.map(route => {
          const isActive = currentRoute === route.path;
          return (
            <Box key={route.path}>
              <Text bold color={isActive ? 'cyan' : 'dimColor'}>
                [{route.shortcut}]
              </Text>
              <Text bold={isActive} color={isActive ? 'white' : 'gray'}>
                {' '}{route.labelZh}
              </Text>
              {isActive && <Text color="cyan"> *</Text>}
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}

// ==================== 快捷键提示 ====================

interface ShortcutHelpProps {
  visible?: boolean;
}

/**
 * 快捷键帮助面板
 */
export function ShortcutHelp({ visible = true }: ShortcutHelpProps): JSX.Element | null {
  if (!visible) return null;

  return (
    <Box marginTop={0} paddingX={1}>
      <Text dimColor>
        Shortcuts:
        {ROUTES.map(r => (
          <span key={r.path}> {r.shortcut}:{r.labelZh}</span>
        ))}
        {' | '}
        Esc:Exit | Tab:Toggle Help
      </Text>
    </Box>
  );
}

// ==================== 键盘路由处理器 ====================

/**
 * 全局键盘路由处理Hook
 *
 * 集成到主应用中，自动处理快捷键导航。
 */
export function useKeyboardNavigation(
  navigateByShortcut: (key: string) => boolean,
  onEscape?: () => void,
) {
  useInput((input, key) => {
    // Escape退出
    if (key.escape || (key.ctrl && input === 'c')) {
      onEscape?.();
      return;
    }

    // 单字符快捷键导航
    if (input.length === 1 && /[hdmsw]/i.test(input)) {
      if (navigateByShortcut(input)) {
        return; // 已处理，不继续传递
      }
    }

    // 数字快捷键
    if (input === '1') navigateByShortcut('h');
    if (input === '2') navigateByShortcut('d');
    if (input === '3') navigateByShortcut('m');
    if (input === '4') navigateByShortcut('s');
    if (input === '5') navigateByShortcut('w');
  });
}

export default useAppRouter;
