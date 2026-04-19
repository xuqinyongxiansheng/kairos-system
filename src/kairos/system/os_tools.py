"""
OS级工具调用模块
提供文件操作、进程管理、网络请求、系统命令等工具
"""

import os
import sys
import json
import shutil
import logging
import asyncio
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """工具类别"""
    FILE = "file"
    PROCESS = "process"
    NETWORK = "network"
    SYSTEM = "system"
    CODE = "code"
    WEB = "web"


class OSTools:
    """OS级工具集"""
    
    def __init__(self, sandbox_mode: bool = True, allowed_paths: List[str] = None):
        self.sandbox_mode = sandbox_mode
        self.allowed_paths = allowed_paths or [os.getcwd()]
        self.execution_history = []
        self.tools = {}
        
        self._register_tools()
        logger.info(f"OS工具集初始化 (sandbox_mode={sandbox_mode})")
    
    def _register_tools(self):
        """注册所有工具"""
        # 文件工具
        self.tools["file_read"] = {
            "function": self.file_read,
            "description": "读取文件内容",
            "parameters": ["path"],
            "category": ToolCategory.FILE.value
        }
        self.tools["file_write"] = {
            "function": self.file_write,
            "description": "写入文件内容",
            "parameters": ["path", "content"],
            "category": ToolCategory.FILE.value
        }
        self.tools["file_append"] = {
            "function": self.file_append,
            "description": "追加文件内容",
            "parameters": ["path", "content"],
            "category": ToolCategory.FILE.value
        }
        self.tools["file_delete"] = {
            "function": self.file_delete,
            "description": "删除文件",
            "parameters": ["path"],
            "category": ToolCategory.FILE.value
        }
        self.tools["file_copy"] = {
            "function": self.file_copy,
            "description": "复制文件",
            "parameters": ["source", "destination"],
            "category": ToolCategory.FILE.value
        }
        self.tools["file_move"] = {
            "function": self.file_move,
            "description": "移动文件",
            "parameters": ["source", "destination"],
            "category": ToolCategory.FILE.value
        }
        self.tools["file_list"] = {
            "function": self.file_list,
            "description": "列出目录内容",
            "parameters": ["path"],
            "category": ToolCategory.FILE.value
        }
        self.tools["file_exists"] = {
            "function": self.file_exists,
            "description": "检查文件是否存在",
            "parameters": ["path"],
            "category": ToolCategory.FILE.value
        }
        self.tools["file_info"] = {
            "function": self.file_info,
            "description": "获取文件信息",
            "parameters": ["path"],
            "category": ToolCategory.FILE.value
        }
        self.tools["directory_create"] = {
            "function": self.directory_create,
            "description": "创建目录",
            "parameters": ["path"],
            "category": ToolCategory.FILE.value
        }
        self.tools["directory_delete"] = {
            "function": self.directory_delete,
            "description": "删除目录",
            "parameters": ["path"],
            "category": ToolCategory.FILE.value
        }
        
        # 进程工具
        self.tools["process_list"] = {
            "function": self.process_list,
            "description": "列出运行中的进程",
            "parameters": [],
            "category": ToolCategory.PROCESS.value
        }
        self.tools["process_kill"] = {
            "function": self.process_kill,
            "description": "终止进程",
            "parameters": ["pid"],
            "category": ToolCategory.PROCESS.value
        }
        self.tools["command_execute"] = {
            "function": self.command_execute,
            "description": "执行系统命令",
            "parameters": ["command", "timeout"],
            "category": ToolCategory.SYSTEM.value
        }
        
        # 网络工具
        self.tools["http_get"] = {
            "function": self.http_get,
            "description": "发送HTTP GET请求",
            "parameters": ["url", "headers"],
            "category": ToolCategory.NETWORK.value
        }
        self.tools["http_post"] = {
            "function": self.http_post,
            "description": "发送HTTP POST请求",
            "parameters": ["url", "data", "headers"],
            "category": ToolCategory.NETWORK.value
        }
        self.tools["download_file"] = {
            "function": self.download_file,
            "description": "下载文件",
            "parameters": ["url", "destination"],
            "category": ToolCategory.NETWORK.value
        }
        
        # 代码工具
        self.tools["code_analyze"] = {
            "function": self.code_analyze,
            "description": "分析代码结构",
            "parameters": ["code", "language"],
            "category": ToolCategory.CODE.value
        }
        self.tools["json_parse"] = {
            "function": self.json_parse,
            "description": "解析JSON",
            "parameters": ["text"],
            "category": ToolCategory.CODE.value
        }
        self.tools["json_stringify"] = {
            "function": self.json_stringify,
            "description": "序列化为JSON",
            "parameters": ["data"],
            "category": ToolCategory.CODE.value
        }
        
        # 系统工具
        self.tools["system_info"] = {
            "function": self.system_info,
            "description": "获取系统信息",
            "parameters": [],
            "category": ToolCategory.SYSTEM.value
        }
        self.tools["environment_get"] = {
            "function": self.environment_get,
            "description": "获取环境变量",
            "parameters": ["name"],
            "category": ToolCategory.SYSTEM.value
        }
        self.tools["environment_set"] = {
            "function": self.environment_set,
            "description": "设置环境变量",
            "parameters": ["name", "value"],
            "category": ToolCategory.SYSTEM.value
        }
    
    def _check_path_allowed(self, path: str) -> bool:
        """检查路径是否允许访问"""
        if not self.sandbox_mode:
            return True
        
        abs_path = os.path.abspath(path)
        for allowed in self.allowed_paths:
            if abs_path.startswith(os.path.abspath(allowed)):
                return True
        return False
    
    def _record_execution(self, tool_name: str, parameters: Dict[str, Any], 
                         result: Dict[str, Any]):
        """记录执行历史"""
        self.execution_history.append({
            "tool": tool_name,
            "parameters": parameters,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    # ==================== 文件工具 ====================
    
    async def file_read(self, path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """读取文件"""
        try:
            if not self._check_path_allowed(path):
                return {"status": "error", "error": "路径访问被拒绝"}
            
            if not os.path.exists(path):
                return {"status": "error", "error": "文件不存在"}
            
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            
            result = {"status": "success", "content": content, "size": len(content)}
            self._record_execution("file_read", {"path": path}, result)
            return result
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def file_write(self, path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """写入文件"""
        try:
            if not self._check_path_allowed(path):
                return {"status": "error", "error": "路径访问被拒绝"}
            
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            with open(path, 'w', encoding=encoding) as f:
                f.write(content)
            
            result = {"status": "success", "path": path, "size": len(content)}
            self._record_execution("file_write", {"path": path}, result)
            return result
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def file_append(self, path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """追加文件内容"""
        try:
            if not self._check_path_allowed(path):
                return {"status": "error", "error": "路径访问被拒绝"}
            
            with open(path, 'a', encoding=encoding) as f:
                f.write(content)
            
            result = {"status": "success", "path": path}
            self._record_execution("file_append", {"path": path}, result)
            return result
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def file_delete(self, path: str) -> Dict[str, Any]:
        """删除文件"""
        try:
            if not self._check_path_allowed(path):
                return {"status": "error", "error": "路径访问被拒绝"}
            
            if os.path.exists(path):
                os.remove(path)
                result = {"status": "success", "path": path}
            else:
                result = {"status": "error", "error": "文件不存在"}
            
            self._record_execution("file_delete", {"path": path}, result)
            return result
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def file_copy(self, source: str, destination: str) -> Dict[str, Any]:
        """复制文件"""
        try:
            if not self._check_path_allowed(source) or not self._check_path_allowed(destination):
                return {"status": "error", "error": "路径访问被拒绝"}
            
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            shutil.copy2(source, destination)
            
            result = {"status": "success", "source": source, "destination": destination}
            self._record_execution("file_copy", {"source": source, "destination": destination}, result)
            return result
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def file_move(self, source: str, destination: str) -> Dict[str, Any]:
        """移动文件"""
        try:
            if not self._check_path_allowed(source) or not self._check_path_allowed(destination):
                return {"status": "error", "error": "路径访问被拒绝"}
            
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            shutil.move(source, destination)
            
            result = {"status": "success", "source": source, "destination": destination}
            self._record_execution("file_move", {"source": source, "destination": destination}, result)
            return result
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def file_list(self, path: str = ".", pattern: str = "*") -> Dict[str, Any]:
        """列出目录内容"""
        try:
            if not self._check_path_allowed(path):
                return {"status": "error", "error": "路径访问被拒绝"}
            
            items = []
            for item in Path(path).glob(pattern):
                items.append({
                    "name": item.name,
                    "path": str(item),
                    "is_dir": item.is_dir(),
                    "is_file": item.is_file(),
                    "size": item.stat().st_size if item.is_file() else 0
                })
            
            result = {"status": "success", "items": items, "count": len(items)}
            self._record_execution("file_list", {"path": path}, result)
            return result
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def file_exists(self, path: str) -> Dict[str, Any]:
        """检查文件是否存在"""
        exists = os.path.exists(path)
        result = {"status": "success", "exists": exists, "path": path}
        self._record_execution("file_exists", {"path": path}, result)
        return result
    
    async def file_info(self, path: str) -> Dict[str, Any]:
        """获取文件信息"""
        try:
            if not os.path.exists(path):
                return {"status": "error", "error": "文件不存在"}
            
            stat = os.stat(path)
            result = {
                "status": "success",
                "info": {
                    "path": path,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "is_dir": os.path.isdir(path),
                    "is_file": os.path.isfile(path)
                }
            }
            self._record_execution("file_info", {"path": path}, result)
            return result
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def directory_create(self, path: str) -> Dict[str, Any]:
        """创建目录"""
        try:
            if not self._check_path_allowed(path):
                return {"status": "error", "error": "路径访问被拒绝"}
            
            os.makedirs(path, exist_ok=True)
            result = {"status": "success", "path": path}
            self._record_execution("directory_create", {"path": path}, result)
            return result
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def directory_delete(self, path: str, recursive: bool = False) -> Dict[str, Any]:
        """删除目录"""
        try:
            if not self._check_path_allowed(path):
                return {"status": "error", "error": "路径访问被拒绝"}
            
            if recursive:
                shutil.rmtree(path)
            else:
                os.rmdir(path)
            
            result = {"status": "success", "path": path}
            self._record_execution("directory_delete", {"path": path}, result)
            return result
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    # ==================== 进程工具 ====================
    
    async def process_list(self) -> Dict[str, Any]:
        """列出运行中的进程"""
        try:
            import psutil
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                processes.append({
                    "pid": proc.info['pid'],
                    "name": proc.info['name'],
                    "cpu": proc.info['cpu_percent'],
                    "memory": proc.info['memory_percent']
                })
            
            result = {"status": "success", "processes": processes[:50], "count": len(processes)}
            self._record_execution("process_list", {}, result)
            return result
            
        except ImportError:
            return {"status": "error", "error": "psutil未安装"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def process_kill(self, pid: int) -> Dict[str, Any]:
        """终止进程"""
        try:
            import psutil
            proc = psutil.Process(pid)
            proc.terminate()
            
            result = {"status": "success", "pid": pid}
            self._record_execution("process_kill", {"pid": pid}, result)
            return result
            
        except ImportError:
            return {"status": "error", "error": "psutil未安装"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def command_execute(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """执行系统命令"""
        try:
            # 安全检查
            dangerous_commands = ["rm -rf", "del /", "format", "mkfs", "dd if="]
            if any(danger in command.lower() for danger in dangerous_commands):
                return {"status": "error", "error": "危险命令被拒绝"}
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                result = {
                    "status": "success",
                    "return_code": process.returncode,
                    "stdout": stdout.decode('utf-8', errors='replace'),
                    "stderr": stderr.decode('utf-8', errors='replace')
                }
            except asyncio.TimeoutError:
                process.kill()
                result = {"status": "error", "error": f"命令超时 ({timeout}s)"}
            
            self._record_execution("command_execute", {"command": command}, result)
            return result
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    # ==================== 网络工具 ====================
    
    async def http_get(self, url: str, headers: Dict[str, str] = None) -> Dict[str, Any]:
        """发送HTTP GET请求"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers or {}, timeout=30) as response:
                    content = await response.text()
                    result = {
                        "status": "success",
                        "status_code": response.status,
                        "content": content[:10000],  # 限制大小
                        "headers": dict(response.headers)
                    }
            
            self._record_execution("http_get", {"url": url}, result)
            return result
            
        except ImportError:
            # 回退到同步请求
            try:
                import requests
                response = requests.get(url, headers=headers or {}, timeout=30)
                result = {
                    "status": "success",
                    "status_code": response.status_code,
                    "content": response.text[:10000]
                }
                self._record_execution("http_get", {"url": url}, result)
                return result
            except Exception as e:
                return {"status": "error", "error": str(e)}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def http_post(self, url: str, data: Dict[str, Any] = None, 
                       headers: Dict[str, str] = None) -> Dict[str, Any]:
        """发送HTTP POST请求"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers or {}, timeout=30) as response:
                    content = await response.text()
                    result = {
                        "status": "success",
                        "status_code": response.status,
                        "content": content[:10000]
                    }
            
            self._record_execution("http_post", {"url": url}, result)
            return result
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def download_file(self, url: str, destination: str) -> Dict[str, Any]:
        """下载文件"""
        try:
            if not self._check_path_allowed(destination):
                return {"status": "error", "error": "路径访问被拒绝"}
            
            import aiohttp
            
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    with open(destination, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
            
            result = {"status": "success", "url": url, "destination": destination}
            self._record_execution("download_file", {"url": url, "destination": destination}, result)
            return result
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    # ==================== 代码工具 ====================
    
    async def code_analyze(self, code: str, language: str = "python") -> Dict[str, Any]:
        """分析代码结构"""
        try:
            analysis = {
                "language": language,
                "lines": len(code.split('\n')),
                "characters": len(code),
                "functions": [],
                "classes": [],
                "imports": []
            }
            
            if language == "python":
                import ast
                try:
                    tree = ast.parse(code)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            analysis["functions"].append(node.name)
                        elif isinstance(node, ast.ClassDef):
                            analysis["classes"].append(node.name)
                        elif isinstance(node, ast.Import):
                            for alias in node.names:
                                analysis["imports"].append(alias.name)
                        elif isinstance(node, ast.ImportFrom):
                            analysis["imports"].append(node.module)
                except Exception:
                    logger.debug(f"忽略异常: ", exc_info=True)
                    pass
            
            result = {"status": "success", "analysis": analysis}
            self._record_execution("code_analyze", {"language": language}, result)
            return result
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def json_parse(self, text: str) -> Dict[str, Any]:
        """解析JSON"""
        try:
            data = json.loads(text)
            result = {"status": "success", "data": data}
            self._record_execution("json_parse", {}, result)
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def json_stringify(self, data: Any) -> Dict[str, Any]:
        """序列化为JSON"""
        try:
            text = json.dumps(data, ensure_ascii=False, indent=2)
            result = {"status": "success", "text": text}
            self._record_execution("json_stringify", {}, result)
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    # ==================== 系统工具 ====================
    
    async def system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            import platform
            info = {
                "system": platform.system(),
                "node": platform.node(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "cwd": os.getcwd(),
                "environment": dict(os.environ)
            }
            
            result = {"status": "success", "info": info}
            self._record_execution("system_info", {}, result)
            return result
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def environment_get(self, name: str) -> Dict[str, Any]:
        """获取环境变量"""
        value = os.environ.get(name)
        result = {"status": "success", "name": name, "value": value}
        self._record_execution("environment_get", {"name": name}, result)
        return result
    
    async def environment_set(self, name: str, value: str) -> Dict[str, Any]:
        """设置环境变量"""
        os.environ[name] = value
        result = {"status": "success", "name": name, "value": value}
        self._record_execution("environment_set", {"name": name, "value": value}, result)
        return result
    
    # ==================== 工具管理 ====================
    
    def get_tools(self) -> Dict[str, Any]:
        """获取所有工具"""
        return {
            "status": "success",
            "tools": {
                name: {
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                    "category": tool["category"]
                }
                for name, tool in self.tools.items()
            },
            "count": len(self.tools)
        }
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        if tool_name not in self.tools:
            return {"status": "error", "error": f"工具不存在: {tool_name}"}
        
        tool = self.tools[tool_name]
        func = tool["function"]
        
        if asyncio.iscoroutinefunction(func):
            return await func(**kwargs)
        else:
            return await func(**kwargs)
    
    def get_execution_history(self, limit: int = 20) -> Dict[str, Any]:
        """获取执行历史"""
        return {
            "status": "success",
            "history": self.execution_history[-limit:],
            "total": len(self.execution_history)
        }


os_tools = OSTools()
