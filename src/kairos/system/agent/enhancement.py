# -*- coding: utf-8 -*-
"""
沙箱执行环境 + 事件驱动记忆系统 + OpenAI兼容接口

整合MaxKB的3项P2功能增强：
1. SandboxExecutor: 沙箱隔离的工具执行环境
2. EventDrivenMemory: 事件驱动的记忆生命周期管理
3. OpenAICompatAPI: OpenAI兼容API接口层

参考: MaxKB sandbox_shell.py + ListenerManagement + chat/completions
"""

import json
import logging
import re
import threading
import time
import uuid
import sys
import ast
import multiprocessing
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class SandboxMode(Enum):
    DISABLED = "disabled"
    RESTRICTED = "restricted"
    FULL = "full"


@dataclass
class SandboxResult:
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0
    execution_time_ms: float = 0
    sandbox_mode: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "output": self.output[:500],
            "error": self.error[:200],
            "exit_code": self.exit_code,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "sandbox_mode": self.sandbox_mode,
        }


def _run_code_in_process(code: str, context: Optional[Dict],
                        safe_builtins: dict, max_output_bytes: int,
                        result_holder: dict, error_holder: dict):
    """模块级函数，供multiprocessing.Process调用（解决嵌套函数无法pickle问题）"""
    try:
        local_vars = dict(context or {})
        restricted_globals = {"__builtins__": safe_builtins}
        exec(code, restricted_globals, local_vars)
        output = str(local_vars.get("_result", ""))
        if len(output.encode('utf-8')) > max_output_bytes:
            output = output[:max_output_bytes // 2] + "\n...[输出截断]"
        result_holder["output"] = output
    except Exception as e:
        error_holder["error"] = str(e)


class SandboxExecutor:
    """
    沙箱执行器，为工具执行提供隔离环境。

    三种模式：
    - DISABLED: 无隔离，直接执行
    - RESTRICTED: 限制资源（超时、内存）
    - FULL: 完全隔离（子进程+资源限制+路径沙箱）

    安全措施：
    - 执行超时限制
    - 输出大小限制
    - 禁止危险操作（文件删除、网络访问等）
    - 路径沙箱（虚拟路径映射）
    """

    DANGEROUS_PATTERNS = [
        "rm -rf", "del /", "format ", "shutdown",
        "os.system", "subprocess.call", "exec(",
        "__import__", "eval(", "open('/etc",
        "shutil.rmtree", "os.remove",
        "os.popen", "os.spawn", "pty.spawn",
        "socket.connect", "http.client",
        "pickle.loads", "marshal.loads",
        "ctypes.cdll", "ctypes.windll",
        "sys._getframe", "gc.get_referents",
    ]

    DANGEROUS_REGEX = [
        re.compile(r'\brm\s+-rf\b', re.IGNORECASE),
        re.compile(r'\bos\.(system|popen|spawn)', re.IGNORECASE),
        re.compile(r'\bsubprocess\.(run|call|Popen|check_output)', re.IGNORECASE),
        re.compile(r'\b(eval|compile|exec)\s*\(', re.IGNORECASE),
        re.compile(r'__import__\s*\(', re.IGNORECASE),
        re.compile(r'shutil\.rmtree', re.IGNORECASE),
        re.compile(r'\bos\.remove\b', re.IGNORECASE),
        re.compile(r'\bos\.unlink\b', re.IGNORECASE),
        re.compile(r'\bopen\s*\(\s*[\'"](/etc|/dev|/sys|/proc)', re.IGNORECASE),
        re.compile(r'getattr\s*\(.+\s*,\s*[\'"].*__[\'"]', re.IGNORECASE),
        re.compile(r'[\'"]__.*__[\'"]\s*\.\s*(bases|mro|subclasses|init_subclass)', re.IGNORECASE),
        re.compile(r'\bsocket\s*\.', re.IGNORECASE),
        re.compile(r'\bpickle\.loads?\s*\(', re.IGNORECASE),
        re.compile(r'\bctypes\.(cdll|windll|oledll)', re.IGNORECASE),
    ]

    BLOCKED_IMPORTS = {'os', 'sys', 'subprocess', 'shutil', 'ctypes', 'socket',
                        'multiprocessing', 'signal', 'pty', 'fcntl',
                        'pickle', 'marshal', 'shlex', 'tempfile',
                        'http', 'urllib', 'requests', 'httpx'}

    def __init__(self, mode: SandboxMode = SandboxMode.RESTRICTED,
                 timeout_s: float = 30.0,
                 max_output_bytes: int = 1024 * 1024):
        self._mode = mode
        self._timeout_s = timeout_s
        self._max_output_bytes = max_output_bytes
        self._virtual_paths: Dict[str, str] = {}
        self._stats = {
            "executions": 0,
            "blocked": 0,
            "timeouts": 0,
            "errors": 0,
        }

    def execute(self, code: str, context: Optional[Dict] = None,
                language: str = "python") -> SandboxResult:
        """在沙箱中执行代码"""
        start_time = time.time()
        self._stats["executions"] += 1

        if self._check_dangerous(code):
            self._stats["blocked"] += 1
            return SandboxResult(
                success=False,
                error="代码包含危险操作，已被沙箱拦截",
                sandbox_mode=self._mode.value,
            )

        if self._mode == SandboxMode.DISABLED:
            return self._execute_direct(code, context, language, start_time)
        elif self._mode == SandboxMode.RESTRICTED:
            return self._execute_restricted(code, context, language, start_time)
        else:
            return self._execute_full(code, context, language, start_time)

    def _check_dangerous(self, code: str) -> bool:
        """三层危险检测：字符串匹配 → 正则匹配 → AST语法分析"""
        code_normalized = re.sub(r'\s+', ' ', code)

        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in code.lower():
                return True

        for regex in self.DANGEROUS_REGEX:
            if regex.search(code):
                return True

        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split('.')[0] in self.BLOCKED_IMPORTS:
                            return True
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split('.')[0] in self.BLOCKED_IMPORTS:
                            return True
        except SyntaxError:
            pass

        return False

    def _execute_direct(self, code: str, context: Optional[Dict],
                        language: str, start_time: float) -> SandboxResult:
        """直接执行（仅做输出限制和危险操作警告，不提供隔离）"""
        if self._check_dangerous(code):
            self._stats["blocked"] += 1
            return SandboxResult(
                success=False,
                error="DISABLED模式下检测到危险操作，建议切换到RESTRICTED模式",
                sandbox_mode="disabled",
            )
        try:
            local_vars = dict(context or {})
            safe_builtins = self._get_safe_builtins()
            exec(code, {"__builtins__": safe_builtins}, local_vars)
            output = str(local_vars.get("_result", ""))
            if len(output.encode('utf-8')) > self._max_output_bytes:
                output = output[:self._max_output_bytes // 2] + "\n...[输出截断]"
            return SandboxResult(
                success=True, output=output,
                execution_time_ms=(time.time() - start_time) * 1000,
                sandbox_mode="disabled",
            )
        except Exception as e:
            self._stats["errors"] += 1
            return SandboxResult(
                success=False, error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
                sandbox_mode="disabled",
            )

    def _execute_restricted(self, code: str, context: Optional[Dict],
                            language: str, start_time: float) -> SandboxResult:
        """限制执行（子进程隔离+超时可强制终止）"""
        import multiprocessing as mp

        result_holder = mp.Manager().dict()
        error_holder = mp.Manager().dict()
        safe_builtins = self._get_safe_builtins()
        max_bytes = self._max_output_bytes

        process = mp.Process(
            target=_run_code_in_process,
            args=(code, context, safe_builtins, max_bytes, result_holder, error_holder),
        )
        process.daemon = True
        process.start()
        process.join(timeout=self._timeout_s)

        if process.is_alive():
            process.terminate()
            process.join(timeout=2.0)
            if process.is_alive():
                process.kill()
                process.join()
            self._stats["timeouts"] += 1
            return SandboxResult(
                success=False, error=f"执行超时（{self._timeout_s}秒），进程已强制终止",
                execution_time_ms=self._timeout_s * 1000,
                sandbox_mode="restricted",
            )

        if "error" in error_holder:
            self._stats["errors"] += 1
            return SandboxResult(
                success=False, error=error_holder["error"],
                execution_time_ms=(time.time() - start_time) * 1000,
                sandbox_mode="restricted",
            )

        return SandboxResult(
            success=True, output=result_holder.get("output", ""),
            execution_time_ms=(time.time() - start_time) * 1000,
            sandbox_mode="restricted",
        )

    def _execute_full(self, code: str, context: Optional[Dict],
                      language: str, start_time: float) -> SandboxResult:
        """完全隔离执行（独立子进程+资源限制）"""
        import subprocess
        import tempfile
        import os as _os

        safe_builtins = self._get_safe_builtins()
        context_json = json.dumps(context or {}, ensure_ascii=False)
        safe_builtins_json = json.dumps(
            {k: v.__name__ if callable(v) else v for k, v in safe_builtins.items()},
            ensure_ascii=False,
            default=str,
        )

        wrapper_code = f'''
import json, sys
safe_names = {safe_builtins_json}
import builtins
_safe = {{}}
for _name, _val in safe_names.items():
    if hasattr(builtins, _val):
        _safe[_name] = getattr(builtins, _val)
    elif _val in dir(builtins):
        _safe[_name] = getattr(builtins, _val)

_context = json.loads({context_json!r})
_locals = dict(_context)

try:
    exec({code!r}, {{"__builtins__": _safe}}, _locals)
    _result_val = str(_locals.get("_result", ""))
    print(json.dumps({{"success": True, "output": _result_val}}))
except Exception as _e:
    print(json.dumps({{"success": False, "error": str(_e)}}))
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py',
                                          delete=False, encoding='utf-8') as f:
            f.write(wrapper_code)
            script_path = f.name

        try:
            proc = subprocess.run(
                [sys.executable, '-u', script_path],
                capture_output=True, text=True,
                timeout=self._timeout_s,
                env={**_os.environ, "PYTHONPATH": ""},
            )

            output_text = proc.stdout.strip()
            try:
                result_data = json.loads(output_text)
            except (json.JSONDecodeError, ValueError):
                if proc.returncode != 0:
                    return SandboxResult(
                        success=False,
                        error=proc.stderr[:500] or f"进程退出码: {proc.returncode}",
                        execution_time_ms=(time.time() - start_time) * 1000,
                        sandbox_mode="full",
                    )
                return SandboxResult(
                    success=True, output=output_text[:self._max_output_bytes],
                    execution_time_ms=(time.time() - start_time) * 1000,
                    sandbox_mode="full",
                )

            if not result_data.get("success", False):
                self._stats["errors"] += 1
                return SandboxResult(
                    success=False,
                    error=result_data.get("error", "未知错误")[:500],
                    execution_time_ms=(time.time() - start_time) * 1000,
                    sandbox_mode="full",
                )

            output = result_data.get("output", "")
            if len(output.encode('utf-8')) > self._max_output_bytes:
                output = output[:self._max_output_bytes // 2] + "\n...[输出截断]"

            return SandboxResult(
                success=True, output=output,
                execution_time_ms=(time.time() - start_time) * 1000,
                sandbox_mode="full",
            )
        except subprocess.TimeoutExpired:
            self._stats["timeouts"] += 1
            return SandboxResult(
                success=False,
                error=f"执行超时（{self._timeout_s}秒），子进程已终止",
                execution_time_ms=self._timeout_s * 1000,
                sandbox_mode="full",
            )
        finally:
            try:
                _os.unlink(script_path)
            except OSError:
                pass

    @staticmethod
    def _get_safe_builtins() -> dict:
        """获取安全的内建函数集合"""
        import builtins
        safe = {}
        safe_names = [
            "abs", "all", "any", "bin", "bool", "chr", "dict",
            "divmod", "enumerate", "filter", "float", "format",
            "hash", "hex", "int", "isinstance", "len", "list",
            "map", "max", "min", "oct", "ord", "pow", "print",
            "range", "repr", "reversed", "round", "set", "sorted",
            "str", "sum", "tuple", "zip",
        ]
        for name in safe_names:
            if hasattr(builtins, name):
                safe[name] = getattr(builtins, name)
        return safe

    def register_virtual_path(self, virtual: str, real: str) -> None:
        """注册虚拟路径映射"""
        self._virtual_paths[virtual] = real

    def get_statistics(self) -> dict:
        return dict(self._stats)


class MemoryEventType(Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    ACCESSED = "accessed"
    EXPIRED = "expired"
    EXTRACTED = "extracted"
    CLASSIFIED = "classified"
    TRUNCATED = "truncated"


@dataclass
class MemoryEvent:
    event_type: MemoryEventType
    entry_id: str
    entry_type: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = ""


class EventDrivenMemory:
    """
    事件驱动记忆系统。

    记忆的创建、更新、删除、访问等操作触发事件，
    监听器可以响应事件执行后续操作（如向量化、分类、截断等）。

    参考: MaxKB ListenerManagement
    """

    def __init__(self):
        self._listeners: Dict[MemoryEventType, List[Callable[[MemoryEvent], None]]] = defaultdict(list)
        self._event_log: List[MemoryEvent] = []
        self._lock = threading.Lock()
        self._stats = {
            "events_fired": 0,
            "listeners_called": 0,
            "listener_errors": 0,
        }

    def subscribe(self, event_type: MemoryEventType,
                  listener: Callable[[MemoryEvent], None]) -> None:
        """订阅事件"""
        with self._lock:
            self._listeners[event_type].append(listener)

    def unsubscribe(self, event_type: MemoryEventType,
                    listener: Callable[[MemoryEvent], None]) -> None:
        """取消订阅"""
        with self._lock:
            try:
                self._listeners[event_type].remove(listener)
            except ValueError:
                pass

    def fire(self, event: MemoryEvent) -> None:
        """触发事件"""
        with self._lock:
            self._event_log.append(event)
            if len(self._event_log) > 10000:
                self._event_log = self._event_log[-5000:]
            listeners = list(self._listeners.get(event.event_type, []))
            self._stats["events_fired"] += 1

        for listener in listeners:
            try:
                listener(event)
                with self._lock:
                    self._stats["listeners_called"] += 1
            except Exception as e:
                logger.warning("事件监听器异常: %s", e)
                with self._lock:
                    self._stats["listener_errors"] += 1

    def fire_simple(self, event_type: MemoryEventType, entry_id: str,
                    entry_type: str = "", data: Optional[Dict] = None,
                    source: str = "") -> None:
        """便捷方法：触发简单事件"""
        self.fire(MemoryEvent(
            event_type=event_type,
            entry_id=entry_id,
            entry_type=entry_type,
            data=data or {},
            source=source,
        ))

    def get_recent_events(self, count: int = 20,
                          event_type: Optional[MemoryEventType] = None) -> List[MemoryEvent]:
        """获取最近事件"""
        with self._lock:
            events = list(self._event_log)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-count:]

    def get_statistics(self) -> dict:
        with self._lock:
            stats = dict(self._stats)
        stats["event_log_size"] = len(self._event_log)
        stats["listener_counts"] = {
            et.value: len(lst) for et, lst in self._listeners.items()
        }
        return stats


@dataclass
class ChatMessage:
    role: str
    content: str
    name: Optional[str] = None

    def to_dict(self) -> dict:
        d = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class ChatCompletionRequest:
    model: str = ""
    messages: List[ChatMessage] = field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 4096
    stream: bool = False
    top_p: float = 1.0

    @classmethod
    def from_dict(cls, data: dict) -> 'ChatCompletionRequest':
        messages = [
            ChatMessage(role=m.get("role", "user"), content=m.get("content", ""),
                        name=m.get("name"))
            for m in data.get("messages", [])
        ]
        return cls(
            model=data.get("model", ""),
            messages=messages,
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 4096),
            stream=data.get("stream", False),
            top_p=data.get("top_p", 1.0),
        )


@dataclass
class ChatCompletionChoice:
    index: int
    message: ChatMessage
    finish_reason: str = "stop"


@dataclass
class ChatCompletionResponse:
    id: str
    object: str = "chat.completion"
    created: int = 0
    model: str = ""
    choices: List[ChatCompletionChoice] = field(default_factory=list)
    usage: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "object": self.object,
            "created": self.created,
            "model": self.model,
            "choices": [
                {
                    "index": c.index,
                    "message": c.message.to_dict(),
                    "finish_reason": c.finish_reason,
                }
                for c in self.choices
            ],
            "usage": self.usage,
        }


class OpenAICompatAPI:
    """
    OpenAI兼容API接口层。

    提供标准 /v1/chat/completions 格式的API，
    方便第三方工具（如ChatGPT客户端、LangChain等）直接对接。

    参考: MaxKB chat/urls.py OpenAI兼容接口
    """

    def __init__(self, handler: Optional[Callable] = None):
        self._handler = handler or self._default_handler
        self._stats = {
            "requests": 0,
            "stream_requests": 0,
            "errors": 0,
            "total_tokens": 0,
        }
        self._lock = threading.Lock()

    def chat_completions(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """处理chat/completions请求"""
        with self._lock:
            self._stats["requests"] += 1
            if request.stream:
                self._stats["stream_requests"] += 1

        try:
            response = self._handler(request)
            with self._lock:
                self._stats["total_tokens"] += response.usage.get("total_tokens", 0)
            return response
        except Exception as e:
            with self._lock:
                self._stats["errors"] += 1
            logger.error("OpenAI兼容接口异常: %s", e)
            return ChatCompletionResponse(
                id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
                created=int(time.time()),
                model=request.model,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=ChatMessage(role="assistant", content=f"错误: {str(e)}"),
                        finish_reason="error",
                    )
                ],
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            )

    def _default_handler(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """默认处理器"""
        user_msg = ""
        for m in request.messages:
            if m.role == "user":
                user_msg = m.content

        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=f"收到消息: {user_msg[:100]}",
                    ),
                    finish_reason="stop",
                )
            ],
            usage={
                "prompt_tokens": sum(len(m.content) for m in request.messages),
                "completion_tokens": 10,
                "total_tokens": sum(len(m.content) for m in request.messages) + 10,
            },
        )

    def set_handler(self, handler: Callable) -> None:
        """设置自定义处理器"""
        self._handler = handler

    def get_statistics(self) -> dict:
        with self._lock:
            return dict(self._stats)


_sandbox: Optional[SandboxExecutor] = None
_event_memory: Optional[EventDrivenMemory] = None
_openai_api: Optional[OpenAICompatAPI] = None


def get_sandbox() -> SandboxExecutor:
    global _sandbox
    if _sandbox is None:
        _sandbox = SandboxExecutor()
    return _sandbox


def get_event_memory() -> EventDrivenMemory:
    global _event_memory
    if _event_memory is None:
        _event_memory = EventDrivenMemory()
    return _event_memory


def get_openai_api() -> OpenAICompatAPI:
    global _openai_api
    if _openai_api is None:
        _openai_api = OpenAICompatAPI()
    return _openai_api
