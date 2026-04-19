"""
命令系统核心框架
借鉴 cc-haha-main 的命令架构模式（union type + 懒加载 + 静态/动态注册），
完全重写实现，适配本地大模型服务场景。

命令类型：
- prompt: 展开为提示词文本，发送给 LLM
- local: 纯函数执行，直接返回结果
"""

import os
import time
import logging
import asyncio
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

logger = logging.getLogger("CommandSystem")


class CommandType(str, Enum):
    PROMPT = "prompt"
    LOCAL = "local"


@dataclass
class CommandResult:
    success: bool
    output: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    command_name: str = ""
    duration_ms: float = 0.0


@dataclass
class CommandDef:
    name: str
    type: CommandType
    description: str
    aliases: List[str] = field(default_factory=list)
    usage: str = ""
    hidden: bool = False
    prompt_template: str = ""
    local_handler: Optional[Callable[..., Awaitable[CommandResult]]] = None
    requires_llm: bool = False
    category: str = "通用"


class CommandRegistry:
    """命令注册中心"""

    def __init__(self):
        self._commands: Dict[str, CommandDef] = {}
        self._aliases: Dict[str, str] = {}
        self._dynamic_commands: Dict[str, CommandDef] = {}
        self._execution_history: List[Dict[str, Any]] = []
        self._max_history = 1000

    @property
    def command_count(self) -> int:
        return len(self._commands) + len(self._dynamic_commands)

    def register(self, cmd: CommandDef) -> None:
        if cmd.name in self._commands:
            logger.warning(f"命令 '{cmd.name}' 已存在，覆盖注册")
        self._commands[cmd.name] = cmd
        for alias in cmd.aliases:
            self._aliases[alias] = cmd.name

    def register_dynamic(self, cmd: CommandDef) -> None:
        self._dynamic_commands[cmd.name] = cmd
        for alias in cmd.aliases:
            self._aliases[alias] = cmd.name
        logger.debug(f"动态注册命令: {cmd.name}")

    def unregister(self, name: str) -> bool:
        cmd = self._commands.pop(name, None) or self._dynamic_commands.pop(name, None)
        if cmd:
            for alias in cmd.aliases:
                self._aliases.pop(alias, None)
            return True
        return False

    def get(self, name: str) -> Optional[CommandDef]:
        if name in self._commands:
            return self._commands[name]
        if name in self._dynamic_commands:
            return self._dynamic_commands[name]
        alias_target = self._aliases.get(name)
        if alias_target:
            return self._commands.get(alias_target) or self._dynamic_commands.get(alias_target)
        return None

    def list_commands(self, include_hidden: bool = False) -> List[CommandDef]:
        all_cmds = {}
        all_cmds.update(self._commands)
        all_cmds.update(self._dynamic_commands)
        result = []
        for cmd in all_cmds.values():
            if include_hidden or not cmd.hidden:
                result.append(cmd)
        return sorted(result, key=lambda c: (c.category, c.name))

    def list_by_category(self) -> Dict[str, List[CommandDef]]:
        result: Dict[str, List[CommandDef]] = {}
        for cmd in self.list_commands():
            cat = cmd.category
            if cat not in result:
                result[cat] = []
            result[cat].append(cmd)
        return result

    def search(self, query: str) -> List[CommandDef]:
        query_lower = query.lower()
        results = []
        for cmd in self.list_commands():
            if (query_lower in cmd.name.lower() or
                query_lower in cmd.description.lower() or
                any(query_lower in a.lower() for a in cmd.aliases)):
                results.append(cmd)
        return results

    def record_execution(self, name: str, result: CommandResult):
        self._execution_history.append({
            "command": name,
            "success": result.success,
            "duration_ms": result.duration_ms,
            "timestamp": time.time(),
        })
        if len(self._execution_history) > self._max_history:
            self._execution_history = self._execution_history[-self._max_history:]

    def get_stats(self) -> Dict[str, Any]:
        if not self._execution_history:
            return {"total_executions": 0}
        total = len(self._execution_history)
        success = sum(1 for e in self._execution_history if e["success"])
        durations = [e["duration_ms"] for e in self._execution_history]
        by_command: Dict[str, int] = {}
        for e in self._execution_history:
            by_command[e["command"]] = by_command.get(e["command"], 0) + 1
        return {
            "total_executions": total,
            "success_rate": success / total if total > 0 else 0,
            "avg_duration_ms": sum(durations) / len(durations),
            "by_command": by_command,
            "registered": len(self._commands) + len(self._dynamic_commands),
        }


class CommandDispatcher:
    """命令调度器"""

    def __init__(self, registry: CommandRegistry):
        self.registry = registry
        self._llm_chat_fn: Optional[Callable] = None
        self._context: Dict[str, Any] = {}

    def set_llm_chat_fn(self, fn: Callable):
        self._llm_chat_fn = fn

    def set_context(self, key: str, value: Any):
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        return self._context.get(key, default)

    def parse_input(self, raw_input: str) -> tuple:
        """解析用户输入，返回 (command_name, args) 或 (None, raw_input)"""
        stripped = raw_input.strip()
        if not stripped.startswith("/"):
            return None, stripped

        parts = stripped[1:].split(None, 1)
        if not parts:
            return None, stripped

        command_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        return command_name, args

    async def dispatch(self, raw_input: str) -> CommandResult:
        """调度执行命令"""
        command_name, args = self.parse_input(raw_input)

        if command_name is None:
            return CommandResult(
                success=False,
                output="",
                error="不是命令输入，请使用 / 开头",
                command_name=""
            )

        cmd = self.registry.get(command_name)
        if cmd is None:
            return CommandResult(
                success=False,
                output="",
                error=f"未知命令: /{command_name}，输入 /help 查看可用命令",
                command_name=command_name
            )

        start = time.time()
        try:
            if cmd.type == CommandType.PROMPT:
                result = await self._execute_prompt(cmd, args)
            elif cmd.type == CommandType.LOCAL:
                result = await self._execute_local(cmd, args)
            else:
                result = CommandResult(
                    success=False,
                    error=f"不支持的命令类型: {cmd.type}",
                    command_name=cmd.name
                )
        except Exception as e:
            duration = (time.time() - start) * 1000
            result = CommandResult(
                success=False,
                error=f"命令执行异常: {str(e)}",
                command_name=cmd.name,
                duration_ms=duration
            )
            logger.error(f"命令 '{cmd.name}' 执行异常: {e}")

        if not result.command_name:
            result.command_name = cmd.name
        if not result.duration_ms:
            result.duration_ms = (time.time() - start) * 1000

        self.registry.record_execution(cmd.name, result)
        return result

    async def _execute_prompt(self, cmd: CommandDef, args: str) -> CommandResult:
        """执行 prompt 类型命令：展开模板后发送给 LLM"""
        if not self._llm_chat_fn:
            return CommandResult(
                success=False,
                error="LLM 对话功能未配置",
                command_name=cmd.name
            )

        prompt = cmd.prompt_template
        if "{args}" in prompt:
            prompt = prompt.replace("{args}", args)
        elif args:
            prompt = f"{prompt}\n\n{args}"

        try:
            response = await self._llm_chat_fn(prompt)
            output = response if isinstance(response, str) else str(response)
            return CommandResult(
                success=True,
                output=output,
                command_name=cmd.name,
                data={"prompt_sent": prompt[:200]}
            )
        except Exception as e:
            return CommandResult(
                success=False,
                error=f"LLM 调用失败: {str(e)}",
                command_name=cmd.name
            )

    async def _execute_local(self, cmd: CommandDef, args: str) -> CommandResult:
        """执行 local 类型命令：直接调用处理函数"""
        if not cmd.local_handler:
            return CommandResult(
                success=False,
                error=f"命令 '{cmd.name}' 未注册处理函数",
                command_name=cmd.name
            )

        result = await cmd.local_handler(args, self._context)
        if not isinstance(result, CommandResult):
            result = CommandResult(
                success=True,
                output=str(result),
                command_name=cmd.name
            )
        if not result.command_name:
            result.command_name = cmd.name
        return result
