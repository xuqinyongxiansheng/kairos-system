# -*- coding: utf-8 -*-
"""
环形缓冲区 + 上下文隔离

CircularBuffer: 零分配固定大小环形缓冲区，自动淘汰最旧条目。
适用于维护滚动窗口数据（如最近查询、性能指标、事件日志）。

ContextIsolator: 基于contextvars的并发隔离，确保多Agent并发执行时
上下文互不干扰。每个Agent拥有独立的上下文变量命名空间。

参考: Claude Code CircularBuffer.ts + agentContext.ts
"""

import contextvars
import logging
import threading
import time
from typing import Dict, List, Any, Optional, TypeVar, Generic, Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircularBuffer(Generic[T]):
    """
    固定大小环形缓冲区，自动淘汰最旧条目。

    特性：
    - O(1) 添加和获取
    - 零额外内存分配（预分配固定数组）
    - 线程安全
    - 支持获取最近N条和全部条目
    """

    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError(f"容量必须大于0，得到: {capacity}")
        self._capacity = capacity
        self._buffer: List[Optional[T]] = [None] * capacity
        self._head = 0
        self._size = 0
        self._lock = threading.Lock()

    def add(self, item: T) -> None:
        """添加条目，满时自动淘汰最旧的"""
        with self._lock:
            self._buffer[self._head] = item
            self._head = (self._head + 1) % self._capacity
            if self._size < self._capacity:
                self._size += 1

    def add_all(self, items: List[T]) -> None:
        """批量添加"""
        for item in items:
            self.add(item)

    def get_recent(self, count: int) -> List[T]:
        """获取最近N条条目（从旧到新排序）"""
        with self._lock:
            if self._size == 0:
                return []

            available = min(count, self._size)
            result: List[T] = []

            start = 0 if self._size < self._capacity else self._head
            for i in range(available):
                index = (start + self._size - available + i) % self._capacity
                item = self._buffer[index]
                if item is not None:
                    result.append(item)

            return result

    def to_array(self) -> List[T]:
        """获取所有条目（从旧到新排序）"""
        with self._lock:
            if self._size == 0:
                return []

            result: List[T] = []
            start = 0 if self._size < self._capacity else self._head

            for i in range(self._size):
                index = (start + i) % self._capacity
                item = self._buffer[index]
                if item is not None:
                    result.append(item)

            return result

    def clear(self) -> None:
        """清空缓冲区"""
        with self._lock:
            self._buffer = [None] * self._capacity
            self._head = 0
            self._size = 0

    @property
    def length(self) -> int:
        """当前条目数"""
        with self._lock:
            return self._size

    @property
    def capacity(self) -> int:
        """容量"""
        return self._capacity

    @property
    def is_full(self) -> bool:
        """是否已满"""
        with self._lock:
            return self._size >= self._capacity

    @property
    def is_empty(self) -> bool:
        """是否为空"""
        with self._lock:
            return self._size == 0


class ContextIsolator:
    """
    基于contextvars的并发上下文隔离器。

    确保多Agent并发执行时上下文互不干扰。
    每个Agent拥有独立的上下文变量命名空间。

    特性：
    - 上下文变量自动隔离，无需手动传递
    - 支持嵌套上下文（子Agent继承父Agent上下文）
    - 上下文快照与恢复
    - 上下文变量生命周期管理
    """

    def __init__(self):
        self._vars: Dict[str, contextvars.ContextVar] = {}
        self._lock = threading.Lock()
        self._contexts: Dict[str, contextvars.Context] = {}

    def register_var(self, name: str, default: Any = None) -> contextvars.ContextVar:
        """注册上下文变量"""
        with self._lock:
            if name not in self._vars:
                self._vars[name] = contextvars.ContextVar(name, default=default)
            return self._vars[name]

    def get_var(self, name: str) -> Optional[contextvars.ContextVar]:
        """获取上下文变量"""
        with self._lock:
            return self._vars.get(name)

    def set(self, name: str, value: Any) -> None:
        """设置当前上下文的变量值"""
        with self._lock:
            if name not in self._vars:
                self._vars[name] = contextvars.ContextVar(name)
        self._vars[name].set(value)

    def get(self, name: str, default: Any = None) -> Any:
        """获取当前上下文的变量值"""
        with self._lock:
            var = self._vars.get(name)
        if var is None:
            return default
        try:
            return var.get()
        except LookupError:
            return default

    def create_context(self, context_id: str) -> contextvars.Context:
        """创建独立上下文"""
        ctx = contextvars.copy_context()
        with self._lock:
            self._contexts[context_id] = ctx
        return ctx

    def run_in_context(self, context_id: str, fn: Callable, *args, **kwargs) -> Any:
        """在指定上下文中运行函数"""
        with self._lock:
            ctx = self._contexts.get(context_id)
        if ctx is None:
            ctx = self.create_context(context_id)
        return ctx.run(fn, *args, **kwargs)

    def delete_context(self, context_id: str) -> bool:
        """删除上下文"""
        with self._lock:
            if context_id in self._contexts:
                del self._contexts[context_id]
                return True
            return False

    def list_contexts(self) -> List[str]:
        """列出所有上下文ID"""
        with self._lock:
            return list(self._contexts.keys())

    def snapshot(self) -> Dict[str, Any]:
        """创建当前上下文快照"""
        snap = {}
        with self._lock:
            for name, var in self._vars.items():
                try:
                    snap[name] = var.get()
                except LookupError:
                    snap[name] = None
        return snap

    def restore(self, snapshot: Dict[str, Any]) -> None:
        """从快照恢复上下文"""
        for name, value in snapshot.items():
            self.set(name, value)

    def get_statistics(self) -> dict:
        """获取统计"""
        with self._lock:
            return {
                "registered_vars": len(self._vars),
                "active_contexts": len(self._contexts),
                "var_names": list(self._vars.keys()),
                "context_ids": list(self._contexts.keys()),
            }


@dataclass
class AgentContext:
    """Agent执行上下文"""
    agent_id: str
    session_id: str
    parent_context_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "parent_context_id": self.parent_context_id,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


class AgentContextManager:
    """
    Agent上下文管理器，整合ContextIsolator与AgentContext。

    为每个Agent提供独立的上下文空间，支持：
    - 上下文创建与销毁
    - 父子上下文继承
    - 上下文变量读写
    - 环形缓冲区集成（每个Agent独立的操作日志）
    """

    DEFAULT_LOG_CAPACITY = 100

    def __init__(self):
        self._isolator = ContextIsolator()
        self._agent_contexts: Dict[str, AgentContext] = {}
        self._agent_logs: Dict[str, CircularBuffer] = {}
        self._lock = threading.Lock()

        self._isolator.register_var("agent_id")
        self._isolator.register_var("session_id")
        self._isolator.register_var("current_query")
        self._isolator.register_var("memory_scope")

    def create_agent_context(self, agent_id: str, session_id: str,
                             parent_context_id: Optional[str] = None,
                             log_capacity: int = DEFAULT_LOG_CAPACITY,
                             metadata: Optional[Dict] = None) -> AgentContext:
        """创建Agent上下文"""
        ctx = AgentContext(
            agent_id=agent_id,
            session_id=session_id,
            parent_context_id=parent_context_id,
            metadata=metadata or {},
        )

        with self._lock:
            self._agent_contexts[agent_id] = ctx
            self._agent_logs[agent_id] = CircularBuffer(log_capacity)

        context = self._isolator.create_context(agent_id)

        def _init_vars():
            self._isolator.set("agent_id", agent_id)
            self._isolator.set("session_id", session_id)

        context.run(_init_vars)

        return ctx

    def get_agent_context(self, agent_id: str) -> Optional[AgentContext]:
        """获取Agent上下文"""
        with self._lock:
            return self._agent_contexts.get(agent_id)

    def set_var(self, agent_id: str, name: str, value: Any) -> bool:
        """在Agent上下文中设置变量"""
        with self._lock:
            if agent_id not in self._agent_contexts:
                return False

        def _set():
            self._isolator.set(name, value)

        return self._isolator.run_in_context(agent_id, _set) is None or True

    def get_var(self, agent_id: str, name: str, default: Any = None) -> Any:
        """在Agent上下文中获取变量"""
        with self._lock:
            if agent_id not in self._agent_contexts:
                return default

        result = [default]

        def _get():
            result[0] = self._isolator.get(name, default)

        try:
            self._isolator.run_in_context(agent_id, _get)
        except Exception:
            pass

        return result[0]

    def log_event(self, agent_id: str, event: Any) -> bool:
        """记录Agent事件到环形缓冲区"""
        with self._lock:
            buf = self._agent_logs.get(agent_id)
            if buf is None:
                return False
        buf.add(event)
        return True

    def get_recent_events(self, agent_id: str, count: int = 10) -> List[Any]:
        """获取Agent最近事件"""
        with self._lock:
            buf = self._agent_logs.get(agent_id)
            if buf is None:
                return []
        return buf.get_recent(count)

    def destroy_agent_context(self, agent_id: str) -> bool:
        """销毁Agent上下文"""
        with self._lock:
            if agent_id not in self._agent_contexts:
                return False
            del self._agent_contexts[agent_id]
            del self._agent_logs[agent_id]

        self._isolator.delete_context(agent_id)
        return True

    def list_agents(self) -> List[str]:
        """列出所有Agent"""
        with self._lock:
            return list(self._agent_contexts.keys())

    def get_statistics(self) -> dict:
        """获取统计"""
        with self._lock:
            return {
                "active_agents": len(self._agent_contexts),
                "agent_ids": list(self._agent_contexts.keys()),
                "isolator_stats": self._isolator.get_statistics(),
            }


_agent_ctx_manager: Optional[AgentContextManager] = None


def get_agent_context_manager() -> AgentContextManager:
    """获取Agent上下文管理器单例"""
    global _agent_ctx_manager
    if _agent_ctx_manager is None:
        _agent_ctx_manager = AgentContextManager()
    return _agent_ctx_manager
