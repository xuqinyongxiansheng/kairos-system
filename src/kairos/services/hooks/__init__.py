"""
Hook 生命周期系统
借鉴 cc-haha-main 的 AsyncHookRegistry + hookEvents + hooksConfigManager：
1. 26 种 Hook 事件类型（工具/会话/用户/子代理/压缩/任务/配置/文件/初始化）
2. 四种 Hook 类型（command/prompt/agent/http）
3. 异步 Hook 注册表（进度监控、超时控制）
4. 优先级排序（userSettings > projectSettings > localSettings > pluginHook）
5. FunctionHook（内存回调，不可持久化）
"""

import os
import time
import json
import logging
import asyncio
import subprocess
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger("HookSystem")


class HookEvent(Enum):
    PreToolUse = "PreToolUse"
    PostToolUse = "PostToolUse"
    PostToolUseFailure = "PostToolUseFailure"
    PermissionRequest = "PermissionRequest"
    PermissionDenied = "PermissionDenied"
    SessionStart = "SessionStart"
    SessionEnd = "SessionEnd"
    Stop = "Stop"
    StopFailure = "StopFailure"
    UserPromptSubmit = "UserPromptSubmit"
    Notification = "Notification"
    SubagentStart = "SubagentStart"
    SubagentStop = "SubagentStop"
    PreCompact = "PreCompact"
    PostCompact = "PostCompact"
    TaskCreated = "TaskCreated"
    TaskCompleted = "TaskCompleted"
    ConfigChange = "ConfigChange"
    InstructionsLoaded = "InstructionsLoaded"
    CwdChanged = "CwdChanged"
    FileChanged = "FileChanged"
    Setup = "Setup"


class HookType(Enum):
    COMMAND = "command"
    PROMPT = "prompt"
    AGENT = "agent"
    HTTP = "http"
    FUNCTION = "function"


class HookSource(Enum):
    USER_SETTINGS = "user_settings"
    PROJECT_SETTINGS = "project_settings"
    LOCAL_SETTINGS = "local_settings"
    PLUGIN = "plugin"
    BUILTIN = "builtin"
    SESSION = "session"


SOURCE_PRIORITY = {
    HookSource.USER_SETTINGS: 100,
    HookSource.PROJECT_SETTINGS: 80,
    HookSource.LOCAL_SETTINGS: 60,
    HookSource.PLUGIN: 40,
    HookSource.BUILTIN: 20,
    HookSource.SESSION: 10,
}


@dataclass
class HookResult:
    allowed: bool = True
    reason: str = ""
    modified_input: Optional[Dict[str, Any]] = None
    modified_output: Optional[Any] = None
    error: Optional[str] = None
    source_hook: str = ""


@dataclass
class HookDefinition:
    name: str
    event: HookEvent
    hook_type: HookType
    source: HookSource = HookSource.BUILTIN
    matcher: str = ""
    command: str = ""
    prompt_text: str = ""
    url: str = ""
    function: Optional[Callable] = None
    timeout: float = 30.0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def priority(self) -> int:
        return SOURCE_PRIORITY.get(self.source, 0)


class AsyncHookRegistry:
    """异步 Hook 注册表"""

    def __init__(self):
        self._hooks: Dict[HookEvent, List[HookDefinition]] = defaultdict(list)
        self._running_hooks: Dict[str, Dict[str, Any]] = {}
        self._hook_counter = 0

    def register(self, hook: HookDefinition):
        """注册 Hook"""
        self._hooks[hook.event].append(hook)
        self._hooks[hook.event].sort(key=lambda h: h.priority, reverse=True)
        logger.debug(f"Hook 注册: {hook.name} [{hook.event.value}] from {hook.source.value}")

    def unregister(self, name: str) -> bool:
        """取消注册 Hook"""
        for event, hooks in self._hooks.items():
            for i, hook in enumerate(hooks):
                if hook.name == name:
                    hooks.pop(i)
                    return True
        return False

    def get_hooks(self, event: HookEvent, matcher: str = "") -> List[HookDefinition]:
        """获取匹配的 Hook"""
        hooks = [h for h in self._hooks.get(event, []) if h.enabled]
        if matcher:
            hooks = [h for h in hooks if not h.matcher or h.matcher == matcher]
        return hooks

    async def fire(self, event: HookEvent, context: Dict[str, Any],
                   matcher: str = "") -> HookResult:
        """触发 Hook 事件"""
        hooks = self.get_hooks(event, matcher)

        for hook in hooks:
            if not hook.enabled:
                continue

            hook_id = f"{hook.name}_{self._hook_counter}"
            self._hook_counter += 1
            self._running_hooks[hook_id] = {
                "hook": hook.name,
                "event": event.value,
                "started_at": time.time(),
                "status": "running",
            }

            try:
                result = await self._execute_hook(hook, context)
                self._running_hooks[hook_id]["status"] = "completed"

                if not result.allowed:
                    result.source_hook = hook.name
                    return result

                if result.modified_input:
                    context.update(result.modified_input)

            except asyncio.TimeoutError:
                self._running_hooks[hook_id]["status"] = "timeout"
                logger.warning(f"Hook 超时: {hook.name}")
            except Exception as e:
                self._running_hooks[hook_id]["status"] = "error"
                logger.error(f"Hook 执行失败: {hook.name} - {e}")
            finally:
                if hook_id in self._running_hooks:
                    del self._running_hooks[hook_id]

        return HookResult(allowed=True)

    async def _execute_hook(self, hook: HookDefinition,
                            context: Dict[str, Any]) -> HookResult:
        """执行单个 Hook"""
        if hook.hook_type == HookType.FUNCTION:
            return await self._execute_function_hook(hook, context)
        elif hook.hook_type == HookType.COMMAND:
            return await self._execute_command_hook(hook, context)
        elif hook.hook_type == HookType.PROMPT:
            return await self._execute_prompt_hook(hook, context)
        elif hook.hook_type == HookType.HTTP:
            return await self._execute_http_hook(hook, context)
        elif hook.hook_type == HookType.AGENT:
            return await self._execute_agent_hook(hook, context)
        return HookResult(allowed=True)

    async def _execute_function_hook(self, hook: HookDefinition,
                                      context: Dict[str, Any]) -> HookResult:
        """执行函数 Hook"""
        if not hook.function:
            return HookResult(allowed=True)

        try:
            if asyncio.iscoroutinefunction(hook.function):
                result = await asyncio.wait_for(
                    hook.function(context), timeout=hook.timeout
                )
            else:
                result = hook.function(context)

            if isinstance(result, HookResult):
                return result
            if isinstance(result, bool):
                return HookResult(allowed=result)
            if isinstance(result, dict):
                return HookResult(
                    allowed=result.get("allowed", True),
                    reason=result.get("reason", ""),
                    modified_input=result.get("modified_input"),
                )
            return HookResult(allowed=True)
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            return HookResult(allowed=True, error=str(e))

    async def _execute_command_hook(self, hook: HookDefinition,
                                     context: Dict[str, Any]) -> HookResult:
        """执行命令 Hook"""
        try:
            env = os.environ.copy()
            env["HOOK_EVENT"] = hook.event.value
            env["HOOK_CONTEXT"] = json.dumps(context, ensure_ascii=False, default=str)[:4000]

            proc = await asyncio.create_subprocess_exec(
                *hook.command.split(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=hook.timeout
            )

            exit_code = proc.returncode
            if exit_code == 2:
                return HookResult(
                    allowed=False,
                    reason=f"Hook '{hook.name}' 阻止操作 (exit code 2)",
                    source_hook=hook.name,
                )
            elif exit_code == 0:
                return HookResult(allowed=True)
            else:
                return HookResult(
                    allowed=True,
                    reason=f"Hook '{hook.name}' 返回非零退出码 {exit_code}",
                )
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            return HookResult(allowed=True, error=str(e))

    async def _execute_prompt_hook(self, hook: HookDefinition,
                                    context: Dict[str, Any]) -> HookResult:
        """执行 Prompt Hook（注入文本到上下文）"""
        try:
            rendered = hook.prompt_text
            for key, value in context.items():
                rendered = rendered.replace(f"{{{key}}}", str(value))

            return HookResult(
                allowed=True,
                modified_input={"_injected_prompt": rendered},
            )
        except Exception as e:
            return HookResult(allowed=True, error=str(e))

    async def _execute_http_hook(self, hook: HookDefinition,
                                  context: Dict[str, Any]) -> HookResult:
        """执行 HTTP Hook"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=hook.timeout) as client:
                resp = await client.post(
                    hook.url,
                    json={"event": hook.event.value, "context": context},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return HookResult(
                        allowed=data.get("allowed", True),
                        reason=data.get("reason", ""),
                        modified_input=data.get("modified_input"),
                    )
                return HookResult(allowed=True)
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            return HookResult(allowed=True, error=str(e))

    async def _execute_agent_hook(self, hook: HookDefinition,
                                   context: Dict[str, Any]) -> HookResult:
        """执行 Agent Hook（启动多轮 LLM 查询）"""
        try:
            from kairos.services.agent_engine import AgentEngine
            engine = AgentEngine(max_turns=5)
            engine._system_prompt = f"你是 Hook 代理 '{hook.name}'。分析以下事件并决定是否允许操作。"
            prompt = f"事件: {hook.event.value}\n上下文: {json.dumps(context, ensure_ascii=False, default=str)[:2000]}"
            result = await asyncio.wait_for(
                engine.run(prompt), timeout=hook.timeout
            )

            if "拒绝" in result or "DENY" in result.upper():
                return HookResult(allowed=False, reason=result[:500])
            return HookResult(allowed=True)
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            return HookResult(allowed=True, error=str(e))

    def get_running_hooks(self) -> List[Dict[str, Any]]:
        """获取正在运行的 Hook"""
        return list(self._running_hooks.values())

    def list_all_hooks(self) -> Dict[str, List[Dict[str, Any]]]:
        """列出所有已注册的 Hook"""
        result = {}
        for event, hooks in self._hooks.items():
            result[event.value] = [
                {
                    "name": h.name,
                    "type": h.hook_type.value,
                    "source": h.source.value,
                    "matcher": h.matcher,
                    "enabled": h.enabled,
                    "priority": h.priority,
                }
                for h in hooks
            ]
        return result


class HookConfigManager:
    """Hook 配置管理器"""

    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir or os.environ.get(
            "GEMMA4_HOOK_CONFIG_DIR",
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "hooks")
        )
        self._loaded_configs: Dict[str, float] = {}

    def load_hooks_from_dir(self, registry: AsyncHookRegistry,
                            source: HookSource = HookSource.PROJECT_SETTINGS) -> int:
        """从目录加载 Hook 配置"""
        count = 0
        if not os.path.exists(self.config_dir):
            return count

        for fname in os.listdir(self.config_dir):
            if not fname.endswith(".json"):
                continue
            filepath = os.path.join(self.config_dir, fname)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    config = json.load(f)

                hooks = config.get("hooks", [])
                for hook_config in hooks:
                    try:
                        hook = HookDefinition(
                            name=hook_config.get("name", fname),
                            event=HookEvent(hook_config.get("event", "")),
                            hook_type=HookType(hook_config.get("type", "command")),
                            source=source,
                            matcher=hook_config.get("matcher", ""),
                            command=hook_config.get("command", ""),
                            prompt_text=hook_config.get("prompt", ""),
                            url=hook_config.get("url", ""),
                            timeout=hook_config.get("timeout", 30.0),
                            enabled=hook_config.get("enabled", True),
                        )
                        registry.register(hook)
                        count += 1
                    except (ValueError, KeyError) as e:
                        logger.warning(f"跳过无效 Hook 配置: {e}")

                self._loaded_configs[filepath] = time.time()
            except Exception as e:
                logger.error(f"加载 Hook 配置失败 {filepath}: {e}")

        return count

    def save_hook_config(self, hooks: List[HookDefinition], filepath: str):
        """保存 Hook 配置"""
        config = {
            "hooks": [
                {
                    "name": h.name,
                    "event": h.event.value,
                    "type": h.hook_type.value,
                    "matcher": h.matcher,
                    "command": h.command,
                    "prompt": h.prompt_text,
                    "url": h.url,
                    "timeout": h.timeout,
                    "enabled": h.enabled,
                }
                for h in hooks
            ]
        }
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)


_hook_registry: Optional[AsyncHookRegistry] = None
_hook_config_manager: Optional[HookConfigManager] = None


def get_hook_registry() -> AsyncHookRegistry:
    global _hook_registry
    if _hook_registry is None:
        _hook_registry = AsyncHookRegistry()
    return _hook_registry


def get_hook_config_manager() -> HookConfigManager:
    global _hook_config_manager
    if _hook_config_manager is None:
        _hook_config_manager = HookConfigManager()
    return _hook_config_manager
