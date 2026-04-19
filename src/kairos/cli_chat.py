#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
鸿蒙小雨 CLI 聊天工具
类似 Claude Code 的命令行交互界面
"""

import sys
import os
import json
import requests
import readline
from datetime import datetime

API_BASE = os.environ.get("GEMMA4_API_URL", "http://127.0.0.1:8000")
MODEL = os.environ.get("GEMMA4_MODEL", "gemma4:e4b")

HISTORY_FILE = os.path.expanduser("~/.hmyx_chat_history")
MAX_HISTORY = 100

BANNER = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🚀 鸿蒙小雨 v4.0.0 - 智能助手 CLI                           ║
║   基于 Ollama + Gemma4 | 对标 Claude Code 核心架构            ║
║                                                               ║
║   命令: /help 帮助 | /clear 清空 | /history 历史 | /exit 退出 ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
可用命令:
  /help      - 显示帮助信息
  /clear     - 清空对话历史
  /history   - 显示对话历史
  /save      - 保存对话到文件
  /load      - 加载对话文件
  /model     - 显示/切换模型
  /stats     - 显示统计信息
  /exit      - 退出程序
  
快捷键:
  ↑/↓        - 浏览历史输入
  Ctrl+C     - 取消当前输入
  Ctrl+D     - 退出程序
"""


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


def print_user(msg):
    print(f"\n{Colors.GREEN}{Colors.BOLD}你:{Colors.END} {msg}")


def print_assistant(msg):
    print(f"\n{Colors.CYAN}{Colors.BOLD}助手:{Colors.END}")
    print(msg)


def print_system(msg):
    print(f"{Colors.DIM}{msg}{Colors.END}")


def print_error(msg):
    print(f"{Colors.RED}错误: {msg}{Colors.END}")


def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return []


def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history[-MAX_HISTORY:], f, ensure_ascii=False, indent=2)
    except:
        pass


def send_message(messages, stream=False):
    try:
        if stream:
            response = requests.post(
                f"{API_BASE}/api/chat/stream",
                json={"messages": messages, "model": MODEL, "stream": True},
                stream=True,
                timeout=120
            )
            if response.status_code != 200:
                return None, f"HTTP {response.status_code}"
            
            full_content = ""
            print(f"\n{Colors.CYAN}{Colors.BOLD}助手:{Colors.END}")
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8').replace('data: ', ''))
                        if 'content' in data:
                            content = data['content']
                            print(content, end='', flush=True)
                            full_content += content
                    except:
                        pass
            print()
            return full_content, None
        else:
            response = requests.post(
                f"{API_BASE}/api/chat",
                json={"messages": messages, "model": MODEL, "stream": False},
                timeout=120
            )
            if response.status_code != 200:
                return None, f"HTTP {response.status_code}"
            
            data = response.json()
            return data.get('response') or data.get('message') or data.get('content', ''), None
    except requests.exceptions.ConnectionError:
        return None, "无法连接到服务器，请确保服务已启动"
    except requests.exceptions.Timeout:
        return None, "请求超时"
    except Exception as e:
        return None, str(e)


def check_server():
    try:
        r = requests.get(f"{API_BASE}/api/health", timeout=5)
        return r.status_code == 200
    except:
        return False


def main():
    print(BANNER)
    
    if not check_server():
        print_error("无法连接到服务器，请先启动服务:")
        print_system(f"  cd project && python -m uvicorn main:app --host 127.0.0.1 --port 8000")
        return
    
    print_info(f"已连接到 {API_BASE}")
    print_info(f"当前模型: {MODEL}")
    print()
    
    messages = []
    session_history = []
    total_tokens = 0
    
    # 初始化 readline 历史
    try:
        readline.read_history_file(HISTORY_FILE + ".input")
    except:
        pass
    
    while True:
        try:
            user_input = input(f"\n{Colors.GREEN}你:{Colors.END} ").strip()
        except EOFError:
            print("\n再见!")
            break
        except KeyboardInterrupt:
            print()
            continue
        
        if not user_input:
            continue
        
        # 处理命令
        if user_input.startswith('/'):
            cmd = user_input.lower().split()[0]
            
            if cmd in ('/exit', '/quit', '/q'):
                print_info("再见!")
                break
            
            elif cmd == '/help':
                print(HELP_TEXT)
            
            elif cmd == '/clear':
                messages = []
                print_info("对话已清空")
            
            elif cmd == '/history':
                if not messages:
                    print_info("暂无对话历史")
                else:
                    print(f"\n{Colors.BOLD}对话历史 ({len(messages)} 条):{Colors.END}")
                    for i, msg in enumerate(messages):
                        role = "你" if msg['role'] == 'user' else "助手"
                        content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                        print(f"  [{i+1}] {role}: {content}")
            
            elif cmd == '/save':
                if not messages:
                    print_info("暂无对话可保存")
                else:
                    filename = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(messages, f, ensure_ascii=False, indent=2)
                    print_info(f"对话已保存到 {filename}")
            
            elif cmd == '/load':
                parts = user_input.split(maxsplit=1)
                if len(parts) < 2:
                    print_info("用法: /load <文件名>")
                else:
                    try:
                        with open(parts[1], 'r', encoding='utf-8') as f:
                            messages = json.load(f)
                        print_info(f"已加载 {len(messages)} 条消息")
                    except Exception as e:
                        print_error(f"加载失败: {e}")
            
            elif cmd == '/model':
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    global MODEL
                    MODEL = parts[1]
                    print_info(f"模型已切换为: {MODEL}")
                else:
                    print_info(f"当前模型: {MODEL}")
            
            elif cmd == '/stats':
                print(f"\n{Colors.BOLD}统计信息:{Colors.END}")
                print(f"  消息数: {len(messages)}")
                print(f"  Token: {total_tokens}")
                print(f"  模型: {MODEL}")
                print(f"  服务器: {API_BASE}")
            
            else:
                print_error(f"未知命令: {cmd}")
                print_info("输入 /help 查看可用命令")
            
            continue
        
        # 发送消息
        messages.append({"role": "user", "content": user_input})
        
        response, error = send_message(messages, stream=True)
        
        if error:
            print_error(error)
            messages.pop()
            continue
        
        if response:
            messages.append({"role": "assistant", "content": response})
            
            # 保存到 readline 历史
            try:
                readline.add_history(user_input)
                readline.write_history_file(HISTORY_FILE + ".input")
            except:
                pass
    
    # 保存会话历史
    if messages:
        save_history(messages)


if __name__ == "__main__":
    main()
