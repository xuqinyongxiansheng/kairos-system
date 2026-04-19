#!/usr/bin/env node
/**
 * 鸿蒙小雨 Gemma4 终端 UI
 * 完全从零构建，不依赖任何 cc-haha-main 源码
 * 使用 Node.js 原生 stdin/stdout 实现终端交互
 * 服务于本地 Ollama 大模型，不涉及任何云服务功能
 *
 * 集成服务：命令系统、工具系统、MCP、压缩、LSP
 */

const readline = require('readline')
const fetch = require('node-fetch')

const CONFIG = {
  API_BASE: process.env.GEMMA4_API_URL || 'http://localhost:8000',
  DEFAULT_MODEL: 'gemma4:e4b',
  APP_NAME: '鸿蒙小雨 Gemma4',
  APP_VERSION: '4.0.0',
}

const C = {
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
  gray: '\x1b[90m',
}

function colorize(text: string, ...codes: string[]): string {
  return codes.join('') + text + C.reset
}

// ==================== API 客户端 ====================

async function apiGet(path: string): Promise<any> {
  const resp = await fetch(`${CONFIG.API_BASE}${path}`)
  return resp.json()
}

async function apiPost(path: string, body: any): Promise<any> {
  const resp = await fetch(`${CONFIG.API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return resp.json()
}

async function apiChat(message: string, model?: string, history?: any[]): Promise<any> {
  return apiPost('/api/chat', { message, model: model || currentModel, history })
}

async function apiChatStream(message: string, model?: string, history?: any[]): Promise<string> {
  const resp = await fetch(`${CONFIG.API_BASE}/api/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, model: model || currentModel, history }),
  })

  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  if (!resp.body) throw new Error('无法获取响应流')

  const decoder = new (require('string_decoder').StringDecoder)()
  let buffer = ''
  let fullContent = ''

  for await (const chunk of resp.body) {
    buffer += decoder.write(chunk)
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const data = line.slice(6).trim()
      if (!data) continue
      try {
        const event = JSON.parse(data)
        if (event.type === 'token' && event.content) {
          process.stdout.write(event.content)
          fullContent += event.content
        } else if (event.type === 'done') {
          // 流结束
        } else if (event.type === 'error') {
          throw new Error(event.message)
        }
      } catch (e) {
        if (e instanceof SyntaxError) continue
        throw e
      }
    }
  }
  return fullContent
}

async function apiExecuteCommand(input: string): Promise<any> {
  return apiPost('/api/services/commands/execute', { input })
}

async function apiExecuteTool(toolName: string, params: any = {}): Promise<any> {
  return apiPost('/api/services/tools/execute', { tool_name: toolName, params })
}

// ==================== 状态 ====================

const messages: Array<{role: string, content: string}> = []
let chatHistory: Array<{role: string, content: string}> = []
let currentModel = CONFIG.DEFAULT_MODEL
let streamEnabled = true
let connected = false
let commandMode = true

// ==================== 终端 UI ====================

function clearScreen() {
  process.stdout.write('\x1b[2J\x1b[H')
}

function printBanner() {
  console.log(colorize(`  ╔══════════════════════════════════════════╗`, C.magenta, C.bold))
  console.log(colorize(`  ║   ${CONFIG.APP_NAME} v${CONFIG.APP_VERSION}   ║`, C.magenta, C.bold))
  console.log(colorize(`  ╚══════════════════════════════════════════╝`, C.magenta, C.bold))
  console.log()
  console.log(`  ${connected ? colorize('● 已连接', C.green) : colorize('○ 未连接', C.red)}  │  模型: ${colorize(currentModel, C.cyan)}  │  流式: ${streamEnabled ? colorize('开启', C.green) : colorize('关闭', C.yellow)}`)
  console.log(colorize(`  ──────────────────────────────────────────`, C.gray))
  console.log()
}

function printMessages() {
  const visible = messages.slice(-15)
  for (const msg of visible) {
    if (msg.role === 'user') {
      console.log(`  ${colorize('你:', C.cyan, C.bold)} ${msg.content}`)
    } else if (msg.role === 'system') {
      console.log(`  ${colorize('系统:', C.yellow, C.bold)} ${colorize(msg.content, C.yellow)}`)
    } else if (msg.role === 'tool') {
      console.log(`  ${colorize('工具:', C.blue, C.bold)} ${colorize(msg.content, C.dim)}`)
    } else {
      console.log(`  ${colorize('小雨:', C.green, C.bold)} ${msg.content}`)
    }
  }
  console.log()
}

function refreshScreen() {
  clearScreen()
  printBanner()
  printMessages()
  process.stdout.write(`  ${colorize('❯', C.blue, C.bold)} `)
}

// ==================== 命令处理 ====================

const LOCAL_COMMANDS: Record<string, (args: string) => Promise<void>> = {
  'stream': async () => {
    streamEnabled = !streamEnabled
    messages.push({ role: 'system', content: `流式模式: ${streamEnabled ? '开启' : '关闭'}` })
  },
  'quit': async () => {
    console.log(colorize('\n  再见！', C.magenta))
    process.exit(0)
  },
  'exit': async () => {
    console.log(colorize('\n  再见！', C.magenta))
    process.exit(0)
  },
  'q': async () => {
    console.log(colorize('\n  再见！', C.magenta))
    process.exit(0)
  },
}

async function handleCommand(input: string) {
  const parts = input.slice(1).split(' ')
  const cmd = parts[0].toLowerCase()
  const args = parts.slice(1).join(' ')

  if (LOCAL_COMMANDS[cmd]) {
    await LOCAL_COMMANDS[cmd](args)
    return
  }

  if (!connected) {
    messages.push({ role: 'system', content: '后端未连接，无法执行服务端命令' })
    return
  }

  try {
    const result = await apiExecuteCommand(input)

    if (result.success) {
      if (result.data && result.data.quit) {
        console.log(colorize('\n  再见！', C.magenta))
        process.exit(0)
      }

      const output = result.output || ''
      if (output) {
        const role = result.command_name === 'compact' || result.command_name === 'doctor' ? 'system' : 'system'
        messages.push({ role, content: output })
      }

      if (result.data && result.data.current_model) {
        currentModel = result.data.current_model
      }

      if (result.command_name === 'clear') {
        messages.length = 0
        chatHistory = []
        messages.push({ role: 'system', content: '对话历史已清空' })
      }
    } else {
      messages.push({ role: 'system', content: `命令失败: ${result.error || '未知错误'}` })
    }
  } catch (err: any) {
    messages.push({ role: 'system', content: `命令执行失败: ${err.message}` })
  }
}

async function handleChat(input: string) {
  messages.push({ role: 'user', content: input })
  chatHistory.push({ role: 'user', content: input })

  if (streamEnabled) {
    process.stdout.write(`  ${colorize('小雨:', C.green, C.bold)} `)
    try {
      const streamContent = await apiChatStream(input, currentModel, chatHistory.slice(0, -1))
      if (streamContent) {
        chatHistory.push({ role: 'assistant', content: streamContent })
        messages.push({ role: 'assistant', content: streamContent })
      }
    } catch (err: any) {
      console.log(colorize(`\n  流式对话失败: ${err.message}`, C.red))
    }
    console.log()
  } else {
    try {
      const data = await apiChat(input, currentModel, chatHistory.slice(0, -1))
      if (data.status === 'error') {
        messages.push({ role: 'system', content: `对话失败: ${data.response}` })
      } else {
        messages.push({ role: 'assistant', content: data.response })
        chatHistory.push({ role: 'assistant', content: data.response })
      }
    } catch (err: any) {
      messages.push({ role: 'system', content: `对话失败: ${err.message}` })
    }
  }
}

// ==================== 主循环 ====================

async function main() {
  try {
    const health = await apiGet('/api/health')
    connected = health.status === 'ok' || health.status === 'healthy'
    if (health.default_model) currentModel = health.default_model
  } catch {
    connected = false
  }

  refreshScreen()

  if (!connected) {
    console.log(colorize('  ⚠ 后端未连接，请确保 FastAPI 服务运行在 ' + CONFIG.API_BASE, C.yellow))
    console.log(colorize('  ⚠ 运行: python -m uvicorn main:app --port 8000', C.yellow))
    console.log()
  } else {
    try {
      const cmds = await apiGet('/api/services/commands')
      if (cmds.success && cmds.commands) {
        console.log(colorize(`  已加载 ${cmds.commands.length} 个服务端命令`, C.dim))
      }
      const tools = await apiGet('/api/services/tools')
      if (tools.success && tools.tools) {
        console.log(colorize(`  已加载 ${tools.tools.length} 个工具`, C.dim))
      }
      console.log()
    } catch {}
  }

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: `  ${colorize('❯', C.blue, C.bold)} `,
  })

  rl.prompt()

  rl.on('line', async (line: string) => {
    const input = line.trim()
    if (!input) {
      rl.prompt()
      return
    }

    if (input.startsWith('/')) {
      await handleCommand(input)
      refreshScreen()
    } else {
      refreshScreen()
      await handleChat(input)
      refreshScreen()
    }
    rl.prompt()
  })

  rl.on('close', () => {
    console.log(colorize('\n  再见！', C.magenta))
    process.exit(0)
  })
}

main().catch(err => {
  console.error(colorize(`启动失败: ${err.message}`, C.red))
  process.exit(1)
})
