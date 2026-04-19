"""
工具系统核心框架
借鉴 cc-haha-main 的 buildTool() 工厂模式：
- fail-closed 默认值（安全优先）
- 权限检查
- 并发执行控制
- 统一的工具接口

完全重写实现，适配本地大模型服务场景
"""

import os
import time
import logging
import asyncio
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Awaitable, Type
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

logger = logging.getLogger("ToolSystem")


class PermissionLevel(str, Enum):
    NONE = "none"
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


@dataclass
class ToolResult:
    success: bool
    output: str = ""
    error: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    tool_name: str = ""
    permission_used: PermissionLevel = PermissionLevel.NONE


@dataclass
class ToolParameter:
    name: str
    type: str = "string"
    description: str = ""
    required: bool = True
    default: Any = None


@dataclass
class ToolDef:
    name: str
    description: str
    handler: Optional[Callable[..., Awaitable[ToolResult]]] = None
    parameters: List[ToolParameter] = field(default_factory=list)
    permission: PermissionLevel = PermissionLevel.READ
    is_concurrency_safe: bool = False
    is_read_only: bool = False
    category: str = "通用"
    enabled: bool = True
    timeout_seconds: int = 60
    max_retries: int = 0


class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self._tools: Dict[str, ToolDef] = {}
        self._execution_history: List[Dict[str, Any]] = []
        self._max_history = 2000
        self._running_tools: Dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(10)
        self._permission_checker: Optional[Callable[[str, PermissionLevel], bool]] = None

    @property
    def tool_count(self) -> int:
        return len(self._tools)

    def register(self, tool: ToolDef) -> None:
        if tool.name in self._tools:
            logger.warning(f"工具 '{tool.name}' 已存在，覆盖注册")
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> bool:
        return self._tools.pop(name, None) is not None

    def get(self, name: str) -> Optional[ToolDef]:
        return self._tools.get(name)

    def list_tools(self, include_disabled: bool = False) -> List[Dict[str, Any]]:
        result = []
        for tool in self._tools.values():
            if include_disabled or tool.enabled:
                result.append({
                    "name": tool.name,
                    "description": tool.description,
                    "permission": tool.permission.value,
                    "is_read_only": tool.is_read_only,
                    "is_concurrency_safe": tool.is_concurrency_safe,
                    "category": tool.category,
                    "enabled": tool.enabled,
                    "parameters": [
                        {"name": p.name, "type": p.type, "required": p.required,
                         "description": p.description, "default": p.default}
                        for p in tool.parameters
                    ],
                })
        return sorted(result, key=lambda t: (t["category"], t["name"]))

    def list_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        result: Dict[str, List[Dict[str, Any]]] = {}
        for tool_info in self.list_tools():
            cat = tool_info["category"]
            if cat not in result:
                result[cat] = []
            result[cat].append(tool_info)
        return result

    def set_permission_checker(self, checker: Callable[[str, PermissionLevel], bool]):
        self._permission_checker = checker

    def _check_permission(self, tool_name: str, required: PermissionLevel) -> bool:
        if self._permission_checker is None:
            return True
        return self._permission_checker(tool_name, required)

    def _validate_params(self, tool: ToolDef, params: Dict[str, Any]) -> tuple:
        validated = {}
        for param in tool.parameters:
            value = params.get(param.name, param.default)
            if param.required and value is None:
                return False, f"缺少必需参数: {param.name}"
            validated[param.name] = value
        return True, validated

    async def execute(self, tool_name: str, params: Dict[str, Any] = None,
                      context: Dict[str, Any] = None) -> ToolResult:
        """执行工具"""
        params = params or {}
        context = context or {}

        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(success=False, error=f"未知工具: {tool_name}", tool_name=tool_name)

        if not tool.enabled:
            return ToolResult(success=False, error=f"工具 '{tool_name}' 已禁用", tool_name=tool_name)

        if not self._check_permission(tool_name, tool.permission):
            return ToolResult(
                success=False,
                error=f"权限不足: 执行 '{tool_name}' 需要 {tool.permission.value} 权限",
                tool_name=tool_name,
                permission_used=tool.permission
            )

        valid, validated_params = self._validate_params(tool, params)
        if not valid:
            return ToolResult(success=False, error=validated_params, tool_name=tool_name)

        if not tool.handler:
            return ToolResult(success=False, error=f"工具 '{tool_name}' 未注册处理函数", tool_name=tool_name)

        start = time.time()
        try:
            async with self._semaphore:
                result = await asyncio.wait_for(
                    tool.handler(validated_params, context),
                    timeout=tool.timeout_seconds
                )

            if not isinstance(result, ToolResult):
                result = ToolResult(success=True, output=str(result), tool_name=tool_name)

            if not result.tool_name:
                result.tool_name = tool_name
            result.duration_ms = (time.time() - start) * 1000
            result.permission_used = tool.permission

            self._record_execution(tool_name, True, result.duration_ms)
            return result

        except asyncio.TimeoutError:
            duration = (time.time() - start) * 1000
            self._record_execution(tool_name, False, duration)
            return ToolResult(
                success=False,
                error=f"工具 '{tool_name}' 执行超时（{tool.timeout_seconds}s）",
                tool_name=tool_name,
                duration_ms=duration
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            self._record_execution(tool_name, False, duration)
            logger.error(f"工具 '{tool_name}' 执行异常: {e}")
            return ToolResult(
                success=False,
                error=f"工具执行异常: {str(e)}",
                tool_name=tool_name,
                duration_ms=duration
            )

    def _record_execution(self, tool_name: str, success: bool, duration_ms: float):
        self._execution_history.append({
            "tool": tool_name,
            "success": success,
            "duration_ms": duration_ms,
            "timestamp": time.time(),
        })
        if len(self._execution_history) > self._max_history:
            self._execution_history = self._execution_history[-self._max_history:]

    def get_stats(self) -> Dict[str, Any]:
        if not self._execution_history:
            return {"total_executions": 0, "registered_tools": len(self._tools)}
        total = len(self._execution_history)
        success = sum(1 for e in self._execution_history if e["success"])
        durations = [e["duration_ms"] for e in self._execution_history]
        by_tool: Dict[str, int] = {}
        for e in self._execution_history:
            by_tool[e["tool"]] = by_tool.get(e["tool"], 0) + 1
        return {
            "total_executions": total,
            "success_rate": success / total,
            "avg_duration_ms": sum(durations) / len(durations),
            "by_tool": by_tool,
            "registered_tools": len(self._tools),
        }


def build_tool(name: str, description: str, handler: Callable = None,
               parameters: List[ToolParameter] = None,
               permission: PermissionLevel = PermissionLevel.READ,
               is_concurrency_safe: bool = False,
               is_read_only: bool = False,
               category: str = "通用",
               timeout_seconds: int = 60,
               max_retries: int = 0) -> ToolDef:
    """
    工厂函数：创建工具定义
    借鉴 cc-haha-main 的 buildTool() fail-closed 默认值模式：
    - is_concurrency_safe 默认 False（安全优先）
    - is_read_only 默认 False（安全优先）
    - permission 默认 READ（最小权限）
    - max_retries 默认 0（不重试）
    """
    return ToolDef(
        name=name,
        description=description,
        handler=handler,
        parameters=parameters or [],
        permission=permission,
        is_concurrency_safe=is_concurrency_safe,
        is_read_only=is_read_only,
        category=category,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )


_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
