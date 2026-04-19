#!/usr/bin/env python3
"""
Ollama HTTP Agent模块
使用HTTP直接与Ollama API通信
"""

import json
import datetime
import os
import sys
import asyncio
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("OllamaHTTPAgent")

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logging.warning("httpx not installed. HTTP functionality will be limited.")


class OllamaHTTPAgent:
    """Ollama HTTP Agent类"""
    
    def __init__(self, model: str = "qwen2.5:3b-instruct-q4_K_M", host: str = "http://localhost:11434"):
        """初始化Ollama HTTP Agent"""
        self.logger = logging.getLogger(__name__)
        self.model = model
        self.host = host
        self.ollama_url = f"{self.host}/api"
        
        if HTTPX_AVAILABLE:
            self.client = httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=15.0))
        else:
            self.client = None
        
        self.messages = [
            {
                "role": "system",
                "content": "你是一个智能助手，可以帮助用户完成各种任务。"
            }
        ]
        
        self.tool_map = {
            "get_time": self._get_time,
            "read_file": self._read_file
        }
        
        self.logger.info(f"Ollama HTTP Agent初始化完成，模型: {self.model}")
    
    def _get_time(self) -> str:
        """获取当前时间"""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _read_file(self, filename: str) -> str:
        """读取文件"""
        try:
            if not os.path.isabs(filename):
                filename = os.path.join(os.getcwd(), filename)
            
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
                if len(content) > 1000:
                    return content[:1000] + "... (内容过长，已截断)"
                return content
        except Exception as e:
            return f"文件 {filename} 不存在或无法读取: {str(e)}"
    
    async def chat(self, user_input: str, system_prompt: str = None) -> str:
        """与Ollama聊天"""
        try:
            if system_prompt:
                self.messages[0]["content"] = system_prompt
            
            self.messages.append({"role": "user", "content": user_input})
            
            if not HTTPX_AVAILABLE or not self.client:
                return "httpx库未安装，无法连接Ollama"
            
            payload = {
                "model": self.model,
                "messages": self.messages,
                "stream": False
            }
            
            response = await self.client.post(f"{self.ollama_url}/chat", json=payload, timeout=60.0)
            response.raise_for_status()
            
            result = response.json()
            reply = result.get("message", {}).get("content", "")
            
            self.messages.append({"role": "assistant", "content": reply})
            
            return reply
            
        except Exception as e:
            self.logger.error(f"与Ollama聊天失败: {e}")
            return f"聊天失败: {str(e)}"
    
    async def chat_with_tools(self, user_input: str, tools: List[Dict] = None) -> Dict[str, Any]:
        """带工具调用的聊天"""
        try:
            self.messages.append({"role": "user", "content": user_input})
            
            if not HTTPX_AVAILABLE or not self.client:
                return {"error": "httpx库未安装，无法连接Ollama"}
            
            payload = {
                "model": self.model,
                "messages": self.messages,
                "tools": tools or [],
                "stream": False
            }
            
            response = await self.client.post(f"{self.ollama_url}/chat", json=payload, timeout=60.0)
            response.raise_for_status()
            
            result = response.json()
            msg = result.get("message", {})
            
            if "tool_calls" in msg:
                tool_results = []
                for tool_call in msg["tool_calls"]:
                    func_name = tool_call["function"]["name"]
                    args = json.loads(tool_call["function"]["arguments"])
                    
                    self.logger.info(f"工具调用: {func_name}({args})")
                    
                    if func_name in self.tool_map:
                        func = self.tool_map[func_name]
                        tool_result = func(**args)
                        tool_results.append({
                            "name": func_name,
                            "result": tool_result
                        })
                        
                        self.messages.append({
                            "role": "tool",
                            "content": str(tool_result),
                            "name": func_name
                        })
                
                final_response = await self.client.post(
                    f"{self.ollama_url}/chat",
                    json={"model": self.model, "messages": self.messages, "stream": False},
                    timeout=60.0
                )
                final_result = final_response.json()
                reply = final_result.get("message", {}).get("content", "")
                
                return {
                    "reply": reply,
                    "tool_calls": tool_results
                }
            else:
                reply = msg.get("content", "")
                self.messages.append({"role": "assistant", "content": reply})
                return {"reply": reply}
                
        except Exception as e:
            self.logger.error(f"带工具的聊天失败: {e}")
            return {"error": str(e)}
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_time",
                    "description": "获取当前日期时间",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "读取本地文件内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string", "description": "文件名"}
                        },
                        "required": ["filename"]
                    }
                }
            }
        ]
    
    async def is_available(self) -> bool:
        """检查Ollama是否可用"""
        try:
            if not HTTPX_AVAILABLE or not self.client:
                return False
            
            response = await self.client.get(f"{self.host}/api/tags", timeout=10.0)
            return response.status_code == 200
        except Exception:
            return False
    
    async def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        try:
            if HTTPX_AVAILABLE and self.client:
                response = await self.client.get(f"{self.host}/api/tags", timeout=10.0)
                response.raise_for_status()
                
                result = response.json()
                models = [model["name"] for model in result.get("models", [])]
                return models
        except Exception as e:
            self.logger.error(f"httpx获取模型列表失败: {e}")
        
        # 备用方案：使用urllib
        try:
            import urllib.request
            req = urllib.request.Request(f"{self.host}/api/tags")
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                models = [model["name"] for model in result.get("models", [])]
                return models
        except Exception as e:
            self.logger.error(f"urllib获取模型列表失败: {e}")
            return []
    
    def clear_history(self):
        """清除对话历史"""
        self.messages = [
            {
                "role": "system",
                "content": "你是一个智能助手，可以帮助用户完成各种任务。"
            }
        ]
    
    def get_status(self) -> Dict[str, Any]:
        """获取Agent状态"""
        return {
            "status": "active",
            "model": self.model,
            "host": self.host,
            "httpx_available": HTTPX_AVAILABLE,
            "message_count": len(self.messages)
        }


_ollama_http_agent = None


def get_ollama_http_agent() -> OllamaHTTPAgent:
    """获取Ollama HTTP Agent实例"""
    global _ollama_http_agent
    
    if _ollama_http_agent is None:
        _ollama_http_agent = OllamaHTTPAgent()
    
    return _ollama_http_agent
