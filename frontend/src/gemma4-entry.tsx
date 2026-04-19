#!/usr/bin/env node
/**
 * 鸿蒙小雨 Gemma4 终端 UI
 * 从零构建，仅借鉴 Ink 布局模式，不依赖 cc-haha-main 源码
 * 服务于本地 Ollama 大模型，不涉及任何云服务功能
 */

import React, { useState, useEffect, useCallback } from 'react'
import { render, Box, Text, useInput, useApp, measureElement } from './ink.js'

// ==================== 配置 ====================

const CONFIG = {
  API_BASE: process.env.GEMMA4_API_URL || 'http://localhost:8000',
  DEFAULT_MODEL: 'gemma4:e4b',
  APP_NAME: '鸿蒙小雨 Gemma4',
  APP_VERSION: '4.0.0',
  MAX_HISTORY: 50,
  STREAM_ENABLED: true,
}

// ==================== API 客户端 ====================

class LocalApiClient {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  async health(): Promise<{ status: string; models?: string[] }> {
    const resp = await fetch(`${this.baseUrl}/api/health`)
    return resp.json()
  }

  async chat(message: string, model?: string, history?: Array<{role: string, content: string}>): Promise<string> {
    const resp = await fetch(`${this.baseUrl}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, model: model || CONFIG.DEFAULT_MODEL, history }),
    })
    const data = await resp.json()
    if (data.status === 'error') throw new Error(data.response)
    return data.response
  }

  async *chatStream(message: string, model?: string, history?: Array<{role: string, content: string}>): AsyncGenerator<string> {
    const resp = await fetch(`${this.baseUrl}/api/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, model: model || CONFIG.DEFAULT_MODEL, history }),
    })
    const reader = resp.body?.getReader()
    if (!reader) throw new Error('无法获取响应流')

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6).trim()
        if (!data) continue

        try {
          const event = JSON.parse(data)
          if (event.type === 'token' && event.content) {
            yield event.content
          } else if (event.type === 'error') {
            throw new Error(event.message)
          }
        } catch (e) {
          if (e instanceof SyntaxError) continue
          throw e
        }
      }
    }
  }

  async listModels(): Promise<string[]> {
    const resp = await fetch(`${this.baseUrl}/api/models`)
    const data = await resp.json()
    return (data.models || []).map((m: any) => m.name || m)
  }

  async systemOverview(): Promise<any> {
    const resp = await fetch(`${this.baseUrl}/api/core`)
    return resp.json()
  }
}

const api = new LocalApiClient(CONFIG.API_BASE)

// ==================== 类型定义 ====================

interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
}

type AppView = 'chat' | 'dashboard' | 'help'

// ==================== 组件 ====================

function Header({ connected }: { connected: boolean }) {
  return (
    <Box borderStyle="double" borderColor="magenta" paddingX={2} marginBottom={0}>
      <Text color="magenta" bold>{CONFIG.APP_NAME}</Text>
      <Text dimColor> v{CONFIG.APP_VERSION}</Text>
      <Text> │ </Text>
      <Text color={connected ? 'green' : 'red'}>
        {connected ? '● 已连接' : '○ 未连接'}
      </Text>
    </Box>
  )
}

function StatusBar({ model, view, streaming }: { model: string, view: AppView, streaming: boolean }) {
  const viewLabels: Record<AppView, string> = {
    chat: '对话',
    dashboard: '仪表盘',
    help: '帮助',
  }
  return (
    <Box borderStyle="single" borderColor="cyan" paddingX={1}>
      <Text color="cyan">模型: {model}</Text>
      <Text> │ </Text>
      <Text>视图: {viewLabels[view]}</Text>
      {streaming && <><Text> │ </Text><Text color="yellow">⚡ 流式输出中</Text></>}
    </Box>
  )
}

function MessageList({ messages, streamingContent }: { messages: ChatMessage[], streamingContent: string }) {
  const visible = messages.slice(-20)
  return (
    <Box flexDirection="column" flexGrow={1} paddingX={1}>
      {visible.length === 0 && (
        <Text dimColor>欢迎使用{CONFIG.APP_NAME}！输入消息开始对话，输入 /help 查看帮助。</Text>
      )}
      {visible.map((msg, i) => (
        <Box key={i} marginBottom={0}>
          {msg.role === 'user' ? (
            <><Text color="cyan" bold>你: </Text><Text>{msg.content}</Text></>
          ) : msg.role === 'system' ? (
            <><Text color="yellow" bold>系统: </Text><Text color="yellow">{msg.content}</Text></>
          ) : (
            <><Text color="green" bold>小雨: </Text><Text>{msg.content}</Text></>
          )}
        </Box>
      ))}
      {streamingContent && (
        <Box marginBottom={0}>
          <Text color="green" bold>小雨: </Text>
          <Text color="green">{streamingContent}</Text>
          <Text color="yellow">▌</Text>
        </Box>
      )}
    </Box>
  )
}

function InputBar({ value, placeholder }: { value: string, placeholder: string }) {
  return (
    <Box borderStyle="single" borderColor="blue" paddingX={1}>
      <Text color="blue" bold>{'❯ '}</Text>
      <Text>{value}</Text>
      {value.length === 0 && <Text dimColor>{placeholder}</Text>}
    </Box>
  )
}

function HelpView() {
  return (
    <Box flexDirection="column" padding={1}>
      <Text color="magenta" bold>帮助 - 可用命令</Text>
      <Text> </Text>
      <Text color="cyan">/help</Text><Text>     - 显示此帮助</Text>
      <Text color="cyan">/clear</Text><Text>    - 清空对话历史</Text>
      <Text color="cyan">/model</Text><Text>    - 切换模型</Text>
      <Text color="cyan">/models</Text><Text>   - 列出可用模型</Text>
      <Text color="cyan">/status</Text><Text>   - 查看系统状态</Text>
      <Text color="cyan">/stream</Text><Text>   - 切换流式/同步模式</Text>
      <Text color="cyan">/quit</Text><Text>     - 退出程序</Text>
      <Text> </Text>
      <Text dimColor>按 ESC 返回对话</Text>
    </Box>
  )
}

function DashboardView({ overview, model, connected }: { overview: any, model: string, connected: boolean }) {
  return (
    <Box flexDirection="column" padding={1}>
      <Text color="magenta" bold>系统仪表盘</Text>
      <Text> </Text>
      <Text>系统名称: {overview?.name || CONFIG.APP_NAME}</Text>
      <Text>版本: {overview?.version || CONFIG.APP_VERSION}</Text>
      <Text>架构: {overview?.architecture || '鸿蒙分布式架构'}</Text>
      <Text>默认模型: {overview?.default_model || model}</Text>
      <Text>连接状态: {connected ? '已连接' : '未连接'}</Text>
      <Text>API地址: {CONFIG.API_BASE}</Text>
      <Text>流式模式: {CONFIG.STREAM_ENABLED ? '开启' : '关闭'}</Text>
      <Text> </Text>
      <Text dimColor>按 ESC 返回对话</Text>
    </Box>
  )
}

// ==================== 主应用 ====================

function Gemma4App() {
  const { exit } = useApp()
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [connected, setConnected] = useState(false)
  const [model, setModel] = useState(CONFIG.DEFAULT_MODEL)
  const [view, setView] = useState<AppView>('chat')
  const [streaming, setStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [streamEnabled, setStreamEnabled] = useState(CONFIG.STREAM_ENABLED)
  const [overview, setOverview] = useState<any>(null)
  const [history, setHistory] = useState<Array<{role: string, content: string}>>([])

  useEffect(() => {
    api.health().then(data => {
      setConnected(data.status === 'ok')
    }).catch(() => setConnected(false))

    api.systemOverview().then(data => {
      setOverview(data)
      if (data.default_model) setModel(data.default_model)
    }).catch(() => {})
  }, [])

  const addMessage = useCallback((role: ChatMessage['role'], content: string) => {
    setMessages(prev => [...prev, { role, content, timestamp: Date.now() }])
  }, [])

  const handleSend = useCallback(async (text: string) => {
    addMessage('user', text)
    const newHistory = [...history, { role: 'user', content: text }]

    if (streamEnabled) {
      setStreaming(true)
      setStreamingContent('')
      let fullContent = ''
      try {
        for await (const token of api.chatStream(text, model, history)) {
          fullContent += token
          setStreamingContent(fullContent)
        }
        addMessage('assistant', fullContent)
        setHistory([...newHistory, { role: 'assistant', content: fullContent }])
      } catch (err: any) {
        addMessage('system', `流式对话失败: ${err.message}`)
      } finally {
        setStreaming(false)
        setStreamingContent('')
      }
    } else {
      try {
        const response = await api.chat(text, model, history)
        addMessage('assistant', response)
        setHistory([...newHistory, { role: 'assistant', content: response }])
      } catch (err: any) {
        addMessage('system', `对话失败: ${err.message}`)
      }
    }
  }, [history, model, streamEnabled, addMessage])

  const handleCommand = useCallback(async (cmd: string) => {
    const parts = cmd.slice(1).split(' ')
    const command = parts[0].toLowerCase()
    const arg = parts.slice(1).join(' ')

    switch (command) {
      case 'help':
        setView('help')
        break
      case 'clear':
        setMessages([])
        setHistory([])
        addMessage('system', '对话历史已清空')
        break
      case 'model':
        if (arg) {
          setModel(arg)
          addMessage('system', `模型已切换为: ${arg}`)
        } else {
          addMessage('system', `当前模型: ${model}`)
        }
        break
      case 'models':
        try {
          const models = await api.listModels()
          addMessage('system', `可用模型: ${models.join(', ')}`)
        } catch {
          addMessage('system', '获取模型列表失败')
        }
        break
      case 'status':
        setView('dashboard')
        break
      case 'stream':
        setStreamEnabled(prev => {
          const next = !prev
          addMessage('system', `流式模式: ${next ? '开启' : '关闭'}`)
          return next
        })
        break
      case 'quit':
      case 'exit':
        exit()
        break
      default:
        addMessage('system', `未知命令: /${command}，输入 /help 查看帮助`)
    }
  }, [model, addMessage, exit])

  useInput((char, key) => {
    if (key.escape) {
      if (view !== 'chat') {
        setView('chat')
        return
      }
      exit()
      return
    }

    if (view !== 'chat') return

    if (key.return && input.trim()) {
      const text = input.trim()
      setInput('')
      if (text.startsWith('/')) {
        handleCommand(text)
      } else {
        handleSend(text)
      }
      return
    }

    if (key.backspace || key.delete) {
      setInput(prev => prev.slice(0, -1))
      return
    }

    if (key.ctrl) {
      if (char === 'c') { exit(); return }
      return
    }

    if (char && !key.meta) {
      setInput(prev => prev + char)
    }
  })

  return (
    <Box flexDirection="column" padding={1}>
      <Header connected={connected} />
      <StatusBar model={model} view={view} streaming={streaming} />

      {view === 'chat' && (
        <>
          <MessageList messages={messages} streamingContent={streamingContent} />
          <InputBar value={input} placeholder={streaming ? '等待响应...' : '输入消息，回车发送，/help 帮助'} />
        </>
      )}
      {view === 'help' && <HelpView />}
      {view === 'dashboard' && <DashboardView overview={overview} model={model} connected={connected} />}
    </Box>
  )
}

render(<Gemma4App />)
