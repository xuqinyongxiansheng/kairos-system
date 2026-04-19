/**
 * DiagnosticTrackingService - 诊断跟踪服务
 *
 * 管理代码诊断数据的获取、缓存和对比。
 * 支持三种运行模式：
 *   1. IDE集成模式：通过MCP协议从IDE获取实时诊断
 *   2. 后端API模式：从FastAPI后端获取诊断数据（预留）
 *   3. 本地模式：使用内置演示数据，支持离线展示
 *
 * @module services/diagnosticTracking
 */

import figures from 'figures'
import { logError } from 'src/utils/log.js'

/** 尝试导入MCP相关模块（可选依赖） */
let callIdeRpc: any = null;
let MCPServerConnection: any = null;
try {
  const mcpClient = require('../services/mcp/client.js');
  callIdeRpc = mcpClient.callIdeRpc;
  const mcpTypes = require('../services/mcp/types.js');
  MCPServerConnection = mcpTypes.MCPServerConnection;
} catch {
  // MCP模块未安装或不可用，将使用本地模式
}

/** 尝试导入IDE工具模块 */
let getConnectedIdeClient: any = null;
try {
  const ideUtils = require('../utils/ide.js');
  getConnectedIdeClient = ideUtils.getConnectedIdeClient;
} catch {
  // IDE工具模块未安装或不可用
}

/** 尝试导入路径和错误处理模块 */
let normalizePathForComparison: any;
let pathsEqual: any;
let ClaudeError: any;
let jsonParse: any;
try {
  const fileUtils = require('../utils/file.js');
  normalizePathForComparison = fileUtils.normalizePathForComparison;
  pathsEqual = fileUtils.pathsEqual;
  const errorUtils = require('../utils/errors.js');
  ClaudeError = errorUtils.ClaudeError;
  const slowOps = require('../utils/slowOperations.js');
  jsonParse = slowOps.jsonParse;
} catch {
  // 工具模块加载失败，将使用简化实现
}

/** 自定义诊断错误类 */
class DiagnosticsTrackingError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'DiagnosticsTrackingError';
  }
}

/** 诊断摘要最大字符数 */
const MAX_DIAGNOSTICS_SUMMARY_CHARS = 4000;

/**
 * 单条诊断信息接口
 */
export interface Diagnostic {
  message: string;
  severity: 'Error' | 'Warning' | 'Info' | 'Hint';
  range: {
    start: { line: number; character: number };
    end: { line: number; character: number };
  };
  source?: string;
  code?: string;
}

/**
 * 文件诊断集合接口
 */
export interface DiagnosticFile {
  uri: string;
  diagnostics: Diagnostic[];
}

/** 运行模式枚举 */
export enum DiagnosticsMode {
  /** IDE集成模式 - 通过MCP获取实时诊断 */
  IDE_INTEGRATED = 'ide_integrated',
  /** 后端API模式 - 从FastAPI后端获取 */
  BACKEND_API = 'backend_api',
  /** 本地模式 - 使用内置演示数据 */
  LOCAL_DEMO = 'local_demo',
}

/**
 * 诊断跟踪服务类（单例）
 *
 * 提供诊断数据的统一管理接口，
 * 支持多种数据源和运行模式。
 */
export class DiagnosticTrackingService {
  private static instance: DiagnosticTrackingService | undefined;

  /** 基线诊断数据（用于对比新增问题） */
  private baseline: Map<string, Diagnostic[]> = new Map();

  /** 初始化状态标志 */
  private initialized = false;

  /** MCP客户端引用（IDE集成模式） */
  private mcpClient: any;

  /** 当前运行模式 */
  private mode: DiagnosticsMode = DiagnosticsMode.LOCAL_DEMO;

  /** 文件处理时间戳追踪 */
  private lastProcessedTimestamps: Map<string, number> = new Map();

  /** 右侧文件诊断状态追踪 */
  private rightFileDiagnosticsState: Map<string, Diagnostic[]> = new Map();

  /** 本地演示数据缓存 */
  private demoData: DiagnosticFile[] | null = null;

  /**
   * 获取单例实例
   */
  static getInstance(): DiagnosticTrackingService {
    if (!DiagnosticTrackingService.instance) {
      DiagnosticTrackingService.instance = new DiagnosticTrackingService();
    }
    return DiagnosticTrackingService.instance;
  }

  /** 是否已初始化 */
  get isInitialized(): boolean {
    return this.initialized;
  }

  /** 是否有已连接的客户端 */
  get hasConnectedClient(): boolean {
    return !!this.mcpClient && this.mcpClient.type === 'connected';
  }

  /** 当前运行模式 */
  get currentMode(): DiagnosticsMode {
    return this.mode;
  }

  /**
   * 初始化服务（IDE集成模式）
   * @param mcpClient MCP服务器连接实例
   */
  initialize(mcpClient?: any): void {
    if (this.initialized) {
      return;
    }
    if (mcpClient) {
      this.mcpClient = mcpClient;
      this.mode = DiagnosticsMode.IDE_INTEGRATED;
    } else if (!callIdeRpc) {
      this.mode = DiagnosticsMode.LOCAL_DEMO;
    } else {
      this.mode = DiagnosticsMode.IDE_INTEGRATED;
    }
    this.initialized = true;
  }

  /**
   * 切换到本地演示模式
   */
  enableDemoMode(): void {
    this.mode = DiagnosticsMode.LOCAL_DEMO;
    this.initialized = true;
  }

  /**
   * 关闭服务并清理资源
   */
  async shutdown(): Promise<void> {
    this.initialized = false;
    this.baseline.clear();
    this.rightFileDiagnosticsState.clear();
    this.lastProcessedTimestamps.clear();
    this.demoData = null;
  }

  /**
   * 重置跟踪状态（保留初始化状态）
   */
  reset(): void {
    this.baseline.clear();
    this.rightFileDiagnosticsState.clear();
    this.lastProcessedTimestamps.clear();
  }

  /**
   * 规范化文件URI
   * 移除协议前缀并标准化路径格式
   */
  private normalizeFileUri(fileUri: string): string {
    const protocolPrefixes = [
      'file://',
      '_claude_fs_right:',
      '_claude_fs_left:',
    ];

    let normalized = fileUri;
    for (const prefix of protocolPrefixes) {
      if (fileUri.startsWith(prefix)) {
        normalized = fileUri.slice(prefix.length);
        break;
      }
    }

    if (normalizePathForComparison) {
      return normalizePathForComparison(normalized);
    }
    return normalized.replace(/\\/g, '/');
  }

  /**
   * 获取新诊断数据
   *
   * 根据当前运行模式从不同数据源获取诊断：
   * - IDE模式：通过MCP RPC调用
   * - 本地模式：返回演示数据
   *
   * @returns 新增的诊断文件列表
   */
  async getNewDiagnostics(): Promise<DiagnosticFile[]> {
    switch (this.mode) {
      case DiagnosticsMode.IDE_INTEGRATED:
        return this.getDiagnosticsFromIDE();
      case DiagnosticsMode.BACKEND_API:
        return this.getDiagnosticsFromBackend();
      case DiagnosticsMode.LOCAL_DEMO:
      default:
        return this.getDemoDiagnostics();
    }
  }

  /**
   * 从IDE获取诊断数据（MCP模式）
   */
  private async getDiagnosticsFromIDE(): Promise<DiagnosticFile[]> {
    if (!this.initialized || !this.mcpClient || this.mcpClient.type !== 'connected') {
      return [];
    }

    try {
      const result = await callIdeRpc('getDiagnostics', {}, this.mcpClient);
      const allDiagnosticFiles = this.parseDiagnosticResult(result);

      return this.filterNewDiagnostics(allDiagnosticFiles);
    } catch (error) {
      logError(error as Error);
      return [];
    }
  }

  /**
   * 从后端API获取诊断数据（预留接口）
   */
  private async getDiagnosticsFromBackend(): Promise<DiagnosticFile[]> {
    try {
      const { localBackend } = await import('../services/api/localBackend.js');
      const response = await (localBackend as any).getDiagnostics?.();
      if (response?.files) {
        return response.files as DiagnosticFile[];
      }
      return [];
    } catch {
      return [];
    }
  }

  /**
   * 过滤出新增的诊断项（不在基线中的）
   */
  private filterNewDiagnostics(allFiles: DiagnosticFile[]): DiagnosticFile[] {
    const filesWithBaselines = allFiles.filter(file =>
      this.baseline.has(this.normalizeFileUri(file.uri))
    ).filter(file => file.uri.startsWith('file://'));

    const rightFilesMap = new Map<string, DiagnosticFile>();
    allFiles
      .filter(file => this.baseline.has(this.normalizeFileUri(file.uri)))
      .filter(file => file.uri.startsWith('_claude_fs_right:'))
      .forEach(file => {
        rightFilesMap.set(this.normalizeFileUri(file.uri), file);
      });

    const newDiagnosticFiles: DiagnosticFile[] = [];

    for (const file of filesWithBaselines) {
      const normalizedPath = this.normalizeFileUri(file.uri);
      const baselineDiagnostics = this.baseline.get(normalizedPath) || [];
      const rightFile = rightFilesMap.get(normalizedPath);

      let fileToUse = file;
      if (rightFile) {
        const prevRight = this.rightFileDiagnosticsState.get(normalizedPath);
        if (!prevRight || !this.areDiagnosticArraysEqual(prevRight, rightFile.diagnostics)) {
          fileToUse = rightFile;
        }
        this.rightFileDiagnosticsState.set(normalizedPath, rightFile.diagnostics);
      }

      const newDiagnostics = fileToUse.diagnostics.filter(
        d => !baselineDiagnostics.some(b => this.areDiagnosticsEqual(d, b))
      );

      if (newDiagnostics.length > 0) {
        newDiagnosticFiles.push({ uri: file.uri, diagnostics: newDiagnostics });
      }
      this.baseline.set(normalizedPath, fileToUse.diagnostics);
    }

    return newDiagnosticFiles;
  }

  /**
   * 解析诊断结果数据
   */
  private parseDiagnosticResult(result: unknown): DiagnosticFile[] {
    if (Array.isArray(result)) {
      const textBlock = result.find((block: any) => block.type === 'text');
      if (textBlock && 'text' in textBlock) {
        const parsed = jsonParse ? jsonParse(textBlock.text) : JSON.parse(textBlock.text);
        return parsed || [];
      }
    }
    return [];
  }

  /**
   * 比较两条诊断是否相同
   */
  private areDiagnosticsEqual(a: Diagnostic, b: Diagnostic): boolean {
    return (
      a.message === b.message &&
      a.severity === b.severity &&
      a.source === b.source &&
      a.code === b.code &&
      a.range.start.line === b.range.start.line &&
      a.range.start.character === b.range.start.character &&
      a.range.end.line === b.range.end.line &&
      a.range.end.character === b.range.end.character
    );
  }

  /**
   * 比较两个诊断数组是否相等
   */
  private areDiagnosticArraysEqual(a: Diagnostic[], b: Diagnostic[]): boolean {
    if (a.length !== b.length) return false;
    return (
      a.every(diagA => b.some(diagB => this.areDiagnosticsEqual(diagA, diagB))) &&
      b.every(diagB => a.some(diagA => this.areDiagnosticsEqual(diagA, diagB)))
    );
  }

  /**
   * 处理新查询开始事件
   * 自动初始化或重置诊断跟踪状态
   */
  async handleQueryStart(clients?: any[]): Promise<void> {
    if (!this.initialized) {
      if (clients && getConnectedIdeClient) {
        const connectedClient = getConnectedIdeClient(clients);
        if (connectedClient) {
          this.initialize(connectedClient);
          return;
        }
      }
      this.enableDemoMode();
    } else {
      this.reset();
    }
  }

  /**
   * 格式化诊断摘要为可读字符串
   */
  static formatDiagnosticsSummary(files: DiagnosticFile[]): string {
    const truncationMarker = '…[truncated]';
    const result = files.map(file => {
      const filename = file.uri.split('/').pop() || file.uri;
      const diagnostics = file.diagnostics.map(d => {
        const symbol = DiagnosticTrackingService.getSeveritySymbol(d.severity);
        return `  ${symbol} [Line ${d.range.start.line + 1}:${d.range.start.character + 1}] ${d.message}${d.code ? ` [${d.code}]` : ''}${d.source ? ` (${d.source})` : ''}`;
      }).join('\n');
      return `${filename}:\n${diagnostics}`;
    }).join('\n\n');

    if (result.length > MAX_DIAGNOSTICS_SUMMARY_CHARS) {
      return result.slice(0, MAX_DIAGNOSTICS_SUMMARY_CHARS - truncationMarker.length) + truncationMarker;
    }
    return result;
  }

  /**
   * 获取严重性对应的符号
   * 包含figures库的容错处理
   */
  static getSeveritySymbol(severity: Diagnostic['severity']): string {
    try {
      const symbols: Record<string, string> = {
        Error: figures.cross,
        Warning: figures.warning,
        Info: figures.info,
        Hint: figures.star,
      };
      return symbols[severity] || figures.bullet;
    } catch {
      const fallback: Record<string, string> = {
        Error: 'X',
        Warning: '!',
        Info: 'i',
        Hint: '*',
      };
      return fallback[severity] || '-';
    }
  }

  /**
   * 获取内置演示诊断数据
   *
   * 返回模拟的IDE诊断数据，用于：
   * - 本地模式下的UI展示测试
   * - 无IDE连接时的功能演示
   * - 开发调试时的界面验证
   */
  static getDemoDiagnostics(): DiagnosticFile[] {
    return [
      {
        uri: 'file://demo/example.tsx',
        diagnostics: [
          {
            message: '未使用的变量 "count" 应被移除或使用',
            severity: 'Warning',
            range: { start: { line: 12, character: 5 }, end: { line: 12, character: 10 } },
            source: 'typescript-eslint',
            code: 'no-unused-vars',
          },
          {
            message: '此表达式始终返回 true，可能是逻辑错误',
            severity: 'Error',
            range: { start: { line: 25, character: 3 }, end: { line: 25, character: 18 } },
            source: 'typescript',
            code: 'TS2367',
          },
          {
            message: '建议使用 const 替代 let 以提高代码可读性',
            severity: 'Hint',
            range: { start: { line: 8, character: 1 }, end: { line: 8, character: 4 } },
            source: 'eslint',
            code: 'prefer-const',
          },
        ],
      },
      {
        uri: 'file://demo/utils/helper.py',
        diagnostics: [
          {
            message: '函数缺少类型注解的返回值声明',
            severity: 'Info',
            range: { start: { line: 5, character: 0 }, end: { line: 5, character: 20 } },
            source: 'pyright',
            code: 'reportMissingTypeArgument',
          },
          {
            message: '潜在的资源泄漏: 文件句柄未在 finally 块中关闭',
            severity: 'Warning',
            range: { start: { line: 18, character: 4 }, end: { line: 22, character: 12 } },
            source: 'pylint',
            code: 'W1509',
          },
        ],
      },
    ];
  }

  /**
   * 获取断连状态的attachment数据
   * 用于在无连接时显示友好的状态提示
   */
  static getDisconnectedAttachment(): any {
    return {
      type: 'diagnostics',
      files: [],
      isNew: false,
      isDisconnected: true,
    };
  }

  /**
   * 获取演示模式的attachment数据
   */
  static getDemoAttachment(): any {
    return {
      type: 'diagnostics',
      files: this.getDemoDiagnostics(),
      isNew: true,
      isDisconnected: false,
      isDemo: true,
    };
  }
}

/** 全局单例导出 */
export const diagnosticTracker = DiagnosticTrackingService.getInstance();
