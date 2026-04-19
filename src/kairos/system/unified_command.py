"""
import logging
统一命令调度系统 - 整合CLI-Anything的CLI模式
logger = logging.getLogger("unified_command")

设计模式来源:
- cli_hub/cli.py: Click命令组模式
- 多个*_cli.py: 命令分发模式

核心特性:
1. 命令注册与发现
2. 命令分组管理
3. 参数解析与验证
4. 命令历史记录
5. 命令别名支持
"""

from __future__ import annotations

import argparse
import json
import shlex
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class CommandStatus(Enum):
    """命令状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CommandCategory(Enum):
    """命令分类枚举"""
    SYSTEM = "system"
    FILE = "file"
    NETWORK = "network"
    DATABASE = "database"
    SKILL = "skill"
    AGENT = "agent"
    MEMORY = "memory"
    CUSTOM = "custom"


@dataclass
class CommandArgument:
    """命令参数定义"""
    name: str
    type: type = str
    default: Any = None
    required: bool = False
    help: str = ""
    choices: Optional[List[str]] = None
    nargs: Optional[str] = None
    action: Optional[str] = None
    
    def to_argparse_kwargs(self) -> Dict[str, Any]:
        kwargs = {
            "type": self.type,
            "default": self.default,
            "help": self.help,
        }
        if self.choices:
            kwargs["choices"] = self.choices
        if self.nargs:
            kwargs["nargs"] = self.nargs
        if self.action:
            kwargs["action"] = self.action
        return kwargs


@dataclass
class CommandOption:
    """命令选项定义"""
    name: str
    short_name: Optional[str] = None
    type: type = str
    default: Any = None
    help: str = ""
    is_flag: bool = False
    choices: Optional[List[str]] = None
    multiple: bool = False
    
    def get_flags(self) -> List[str]:
        flags = [f"--{self.name}"]
        if self.short_name:
            flags.append(f"-{self.short_name}")
        return flags
    
    def to_argparse_kwargs(self) -> Dict[str, Any]:
        kwargs = {
            "type": self.type if not self.is_flag else None,
            "default": self.default,
            "help": self.help,
        }
        if self.is_flag:
            kwargs["action"] = "store_true"
        if self.choices:
            kwargs["choices"] = self.choices
        if self.multiple:
            kwargs["action"] = "append"
        return kwargs


@dataclass
class CommandResult:
    """命令执行结果"""
    success: bool
    output: Any = None
    error: Optional[str] = None
    status: CommandStatus = CommandStatus.SUCCESS
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata
        }


@dataclass
class CommandHistory:
    """命令历史记录"""
    command: str
    args: Dict[str, Any]
    result: CommandResult
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "args": self.args,
            "result": self.result.to_dict(),
            "timestamp": self.timestamp.isoformat()
        }


class Command(ABC):
    """
    命令基类
    
    所有命令都应继承此类并实现execute方法
    """
    
    name: str = ""
    description: str = ""
    category: CommandCategory = CommandCategory.CUSTOM
    aliases: List[str] = []
    arguments: List[CommandArgument] = []
    options: List[CommandOption] = []
    
    def __init__(self):
        self._parser: Optional[argparse.ArgumentParser] = None
    
    @abstractmethod
    def execute(self, args: Dict[str, Any]) -> CommandResult:
        """执行命令"""
        pass
    
    def validate(self, args: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """验证参数"""
        for arg in self.arguments:
            if arg.required and arg.name not in args:
                return False, f"缺少必需参数: {arg.name}"
        return True, None
    
    def get_parser(self) -> argparse.ArgumentParser:
        """获取参数解析器"""
        if self._parser is not None:
            return self._parser
        
        self._parser = argparse.ArgumentParser(
            prog=self.name,
            description=self.description
        )
        
        for arg in self.arguments:
            self._parser.add_argument(arg.name, **arg.to_argparse_kwargs())
        
        for opt in self.options:
            flags = opt.get_flags()
            self._parser.add_argument(*flags, **opt.to_argparse_kwargs())
        
        return self._parser
    
    def parse_args(self, args: List[str]) -> Dict[str, Any]:
        """解析参数"""
        parser = self.get_parser()
        namespace = parser.parse_args(args)
        return vars(namespace)
    
    def get_help(self) -> str:
        """获取帮助信息"""
        return self.get_parser().format_help()


class CommandGroup:
    """
    命令组
    
    用于组织相关命令
    """
    
    def __init__(
        self,
        name: str,
        description: str = "",
        category: CommandCategory = CommandCategory.CUSTOM
    ):
        self.name = name
        self.description = description
        self.category = category
        self._commands: Dict[str, Command] = {}
        self._aliases: Dict[str, str] = {}
        self._subgroups: Dict[str, 'CommandGroup'] = {}
        self._lock = threading.RLock()
    
    def register(self, command: Command) -> None:
        """注册命令"""
        with self._lock:
            self._commands[command.name] = command
            for alias in command.aliases:
                self._aliases[alias] = command.name
    
    def unregister(self, name: str) -> bool:
        """注销命令"""
        with self._lock:
            if name in self._commands:
                cmd = self._commands.pop(name)
                for alias in cmd.aliases:
                    self._aliases.pop(alias, None)
                return True
            return False
    
    def get(self, name: str) -> Optional[Command]:
        """获取命令"""
        with self._lock:
            if name in self._commands:
                return self._commands[name]
            if name in self._aliases:
                return self._commands[self._aliases[name]]
            return None
    
    def list_commands(self) -> List[str]:
        """列出所有命令"""
        with self._lock:
            return list(self._commands.keys())
    
    def add_subgroup(self, group: 'CommandGroup') -> None:
        """添加子命令组"""
        with self._lock:
            self._subgroups[group.name] = group
    
    def get_subgroup(self, name: str) -> Optional['CommandGroup']:
        """获取子命令组"""
        with self._lock:
            return self._subgroups.get(name)


class CommandDispatcher:
    """
    命令调度器
    
    整合了CLI-Anything中的命令分发模式:
    - 命令注册与发现
    - 命令分组管理
    - 参数解析与验证
    - 命令历史记录
    """
    
    def __init__(
        self,
        name: str = "cli",
        description: str = "",
        history_size: int = 100,
        history_file: Optional[str] = None
    ):
        self.name = name
        self.description = description
        self.history_size = history_size
        self.history_file = Path(history_file) if history_file else None
        
        self._root_group = CommandGroup(name, description)
        self._groups: Dict[str, CommandGroup] = {name: self._root_group}
        self._history: List[CommandHistory] = []
        self._lock = threading.RLock()
        
        self._pre_hooks: List[Callable[[str, Dict], None]] = []
        self._post_hooks: List[Callable[[str, Dict, CommandResult], None]] = []
        
        self._load_history()
    
    def register(self, command: Command, group: Optional[str] = None) -> None:
        """注册命令"""
        target_group = self._groups.get(group, self._root_group)
        target_group.register(command)
    
    def register_group(self, group: CommandGroup) -> None:
        """注册命令组"""
        with self._lock:
            self._groups[group.name] = group
            self._root_group.add_subgroup(group)
    
    def unregister(self, name: str, group: Optional[str] = None) -> bool:
        """注销命令"""
        target_group = self._groups.get(group, self._root_group)
        return target_group.unregister(name) if target_group else False
    
    def get_command(self, name: str, group: Optional[str] = None) -> Optional[Command]:
        """获取命令"""
        if group:
            target_group = self._groups.get(group)
            return target_group.get(name) if target_group else None
        return self._root_group.get(name)
    
    def dispatch(
        self,
        command_line: str,
        context: Optional[Dict[str, Any]] = None
    ) -> CommandResult:
        """
        调度命令执行
        
        Args:
            command_line: 命令行字符串
            context: 执行上下文
            
        Returns:
            命令执行结果
        """
        import time
        
        start_time = time.time()
        
        try:
            parts = shlex.split(command_line)
        except ValueError as e:
            return CommandResult(
                success=False,
                error=f"命令解析错误: {e}",
                status=CommandStatus.FAILED
            )
        
        if not parts:
            return CommandResult(
                success=False,
                error="空命令",
                status=CommandStatus.FAILED
            )
        
        command_name = parts[0]
        args_list = parts[1:]
        
        command = self.get_command(command_name)
        if not command:
            return CommandResult(
                success=False,
                error=f"未知命令: {command_name}",
                status=CommandStatus.FAILED
            )
        
        try:
            args = command.parse_args(args_list)
        except SystemExit:
            return CommandResult(
                success=False,
                error="参数解析失败",
                status=CommandStatus.FAILED
            )
        except Exception as e:
            return CommandResult(
                success=False,
                error=f"参数解析错误: {e}",
                status=CommandStatus.FAILED
            )
        
        valid, error_msg = command.validate(args)
        if not valid:
            return CommandResult(
                success=False,
                error=error_msg,
                status=CommandStatus.FAILED
            )
        
        if context:
            args.update(context)
        
        for hook in self._pre_hooks:
            try:
                hook(command_name, args)
            except Exception:
                logger.debug(f"忽略异常: hook(command_name, args)", exc_info=True)
                pass
        
        result = command.execute(args)
        
        duration_ms = (time.time() - start_time) * 1000
        result.duration_ms = duration_ms
        
        for hook in self._post_hooks:
            try:
                hook(command_name, args, result)
            except Exception:
                logger.debug(f"忽略异常: hook(command_name, args, result)", exc_info=True)
                pass
        
        self._add_history(command_line, args, result)
        
        return result
    
    def dispatch_parsed(
        self,
        command_name: str,
        args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> CommandResult:
        """使用已解析的参数调度命令"""
        import time
        
        start_time = time.time()
        
        command = self.get_command(command_name)
        if not command:
            return CommandResult(
                success=False,
                error=f"未知命令: {command_name}",
                status=CommandStatus.FAILED
            )
        
        valid, error_msg = command.validate(args)
        if not valid:
            return CommandResult(
                success=False,
                error=error_msg,
                status=CommandStatus.FAILED
            )
        
        if context:
            args = {**args, **context}
        
        for hook in self._pre_hooks:
            try:
                hook(command_name, args)
            except Exception:
                logger.debug(f"忽略异常: hook(command_name, args)", exc_info=True)
                pass
        
        result = command.execute(args)
        
        duration_ms = (time.time() - start_time) * 1000
        result.duration_ms = duration_ms
        
        for hook in self._post_hooks:
            try:
                hook(command_name, args, result)
            except Exception:
                logger.debug(f"忽略异常: hook(command_name, args, result)", exc_info=True)
                pass
        
        return result
    
    def add_pre_hook(self, hook: Callable[[str, Dict], None]) -> None:
        """添加前置钩子"""
        self._pre_hooks.append(hook)
    
    def add_post_hook(self, hook: Callable[[str, Dict, CommandResult], None]) -> None:
        """添加后置钩子"""
        self._post_hooks.append(hook)
    
    def _add_history(self, command: str, args: Dict, result: CommandResult) -> None:
        """添加历史记录"""
        with self._lock:
            history = CommandHistory(
                command=command,
                args=args,
                result=result
            )
            self._history.append(history)
            
            while len(self._history) > self.history_size:
                self._history.pop(0)
            
            self._save_history()
    
    def _load_history(self) -> None:
        """加载历史记录"""
        if not self.history_file or not self.history_file.exists():
            return
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for item in data:
                history = CommandHistory(
                    command=item.get("command", ""),
                    args=item.get("args", {}),
                    result=CommandResult(
                        success=item.get("result", {}).get("success", False),
                        output=item.get("result", {}).get("output"),
                        error=item.get("result", {}).get("error"),
                        status=CommandStatus(item.get("result", {}).get("status", "success"))
                    ),
                    timestamp=datetime.fromisoformat(item.get("timestamp", datetime.now().isoformat()))
                )
                self._history.append(history)
        except Exception:
            logger.debug(f"忽略异常: ", exc_info=True)
            pass
    
    def _save_history(self) -> None:
        """保存历史记录"""
        if not self.history_file:
            return
        
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = [h.to_dict() for h in self._history[-self.history_size:]]
            
            temp_file = self.history_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            if self.history_file.exists():
                self.history_file.unlink()
            temp_file.rename(self.history_file)
        except Exception:
            logger.debug(f"忽略异常: ", exc_info=True)
            pass
    
    def get_history(self, limit: int = 10) -> List[CommandHistory]:
        """获取历史记录"""
        with self._lock:
            return self._history[-limit:]
    
    def clear_history(self) -> None:
        """清空历史记录"""
        with self._lock:
            self._history.clear()
            if self.history_file and self.history_file.exists():
                self.history_file.unlink()
    
    def list_commands(self, group: Optional[str] = None) -> List[str]:
        """列出所有命令"""
        if group:
            target_group = self._groups.get(group)
            return target_group.list_commands() if target_group else []
        return self._root_group.list_commands()
    
    def list_groups(self) -> List[str]:
        """列出所有命令组"""
        return list(self._groups.keys())
    
    def get_help(self, command_name: Optional[str] = None) -> str:
        """获取帮助信息"""
        if command_name:
            command = self.get_command(command_name)
            return command.get_help() if command else f"未知命令: {command_name}"
        
        lines = [f"{self.name} - {self.description}", "", "可用命令:"]
        
        for name in sorted(self.list_commands()):
            command = self.get_command(name)
            if command:
                lines.append(f"  {name:20s} {command.description}")
        
        return "\n".join(lines)


def command(
    name: str,
    description: str = "",
    category: CommandCategory = CommandCategory.CUSTOM,
    aliases: Optional[List[str]] = None,
    arguments: Optional[List[CommandArgument]] = None,
    options: Optional[List[CommandOption]] = None
):
    """
    命令装饰器
    
    用于将函数转换为命令
    """
    def decorator(func: Callable) -> type:
        class FunctionCommand(Command):
            def execute(self, args: Dict[str, Any]) -> CommandResult:
                try:
                    result = func(**args)
                    if isinstance(result, CommandResult):
                        return result
                    return CommandResult(success=True, output=result)
                except Exception as e:
                    return CommandResult(success=False, error=str(e), status=CommandStatus.FAILED)
        
        FunctionCommand.name = name
        FunctionCommand.description = description
        FunctionCommand.category = category
        FunctionCommand.aliases = aliases or []
        FunctionCommand.arguments = arguments or []
        FunctionCommand.options = options or []
        
        return FunctionCommand
    
    return decorator
