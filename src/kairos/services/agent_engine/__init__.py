"""
代理引擎 - 系统心脏
借鉴 cc-haha-main 的三大核心架构：
1. Agentic Loop（代理循环）：用户输入→API调用→工具执行→结果回传→继续循环
2. Tool Orchestration（工具编排）：分区策略（并发安全工具并行、写操作串行）
3. Hook System（钩子系统）：PreToolUse/PostToolUse/Stop 钩子

完全重写实现，适配本地 Ollama 大模型服务场景
"""

import os
import json
import time
import logging
import asyncio
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Awaitable, AsyncGenerator
from dataclasses import dataclass, field

logger = logging.getLogger("AgentEngine")


class LoopState(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING_TOOLS = "executing_tools"
    COMPACTING = "compacting"
    STOPPED = "stopped"
    ERROR = "error"


class HookEvent(str, Enum):
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    POST_TOOL_USE_FAILURE = "PostToolUseFailure"
    STOP = "Stop"
    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"


@dataclass
class HookResult:
    outcome: str = "success"
    message: str = ""
    permission_behavior: str = ""
    updated_input: Optional[Dict[str, Any]] = None
    prevent_continuation: bool = False
    additional_context: str = ""


HookCallback = Callable[[Dict[str, Any]], Awaitable[HookResult]]


@dataclass
class HookDef:
    event: HookEvent
    tool_name: str = ""
    callback: Optional[HookCallback] = None
    timeout: int = 30


@dataclass
class ToolCall:
    id: str
    name: str
    input: Dict[str, Any]
    is_concurrency_safe: bool = False
    is_read_only: bool = False


@dataclass
class ToolCallResult:
    tool_call_id: str
    tool_name: str
    success: bool
    output: str = ""
    error: str = ""
    duration_ms: float = 0.0


@dataclass
class LoopIteration:
    turn: int = 0
    state: LoopState = LoopState.IDLE
    model_response: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_results: List[ToolCallResult] = field(default_factory=list)
    tokens_used: int = 0
    duration_ms: float = 0.0


class HookManager:
    """钩子管理器"""

    def __init__(self):
        self._hooks: Dict[HookEvent, List[HookDef]] = {}
        for event in HookEvent:
            self._hooks[event] = []

    def register(self, hook: HookDef):
        self._hooks[hook.event].append(hook)

    def unregister(self, event: HookEvent, tool_name: str = ""):
        self._hooks[event] = [
            h for h in self._hooks[event]
            if not (tool_name and h.tool_name == tool_name)
        ]

    async def fire(self, event: HookEvent, context: Dict[str, Any]) -> HookResult:
        hooks = self._hooks.get(event, [])
        if not hooks:
            return HookResult()

        combined = HookResult()
        for hook in hooks:
            if hook.tool_name and hook.tool_name != context.get("tool_name", ""):
                continue
            try:
                result = await asyncio.wait_for(
                    hook.callback(context),
                    timeout=hook.timeout
                )
                if result.prevent_continuation:
                    combined.prevent_continuation = True
                    break
                if result.permission_behavior == "deny":
                    combined.permission_behavior = "deny"
                    break
                if result.permission_behavior == "allow":
                    combined.permission_behavior = "allow"
                if result.updated_input:
                    combined.updated_input = result.updated_input
                if result.additional_context:
                    combined.additional_context += result.additional_context + "\n"
            except asyncio.TimeoutError:
                logger.warning(f"钩子超时: {event.value} - {hook.tool_name}")
            except Exception as e:
                logger.error(f"钩子执行异常: {e}")

        return combined

    def list_hooks(self) -> List[Dict[str, Any]]:
        result = []
        for event, hooks in self._hooks.items():
            for h in hooks:
                result.append({
                    "event": event.value,
                    "tool_name": h.tool_name,
                    "timeout": h.timeout,
                })
        return result


class ToolOrchestrator:
    """工具编排器 - 分区策略"""

    def __init__(self, tool_registry=None, permission_checker=None, hook_manager=None):
        self._tool_registry = tool_registry
        self._permission_checker = permission_checker
        self._hook_manager = hook_manager
        self._max_concurrency = 10

    def partition_tool_calls(self, calls: List[ToolCall]) -> List[List[ToolCall]]:
        """将工具调用分区：连续的并发安全工具归为一批，非安全的单独一批"""
        if not calls:
            return []

        batches = []
        current_batch = [calls[0]]
        current_safe = calls[0].is_concurrency_safe

        for call in calls[1:]:
            if call.is_concurrency_safe == current_safe:
                current_batch.append(call)
            else:
                batches.append(current_batch)
                current_batch = [call]
                current_safe = call.is_concurrency_safe

        if current_batch:
            batches.append(current_batch)

        return batches

    async def execute_batch(self, calls: List[ToolCall],
                            context: Dict[str, Any] = None) -> List[ToolCallResult]:
        """执行一批工具调用"""
        context = context or {}

        if not calls:
            return []

        if len(calls) == 1 or not calls[0].is_concurrency_safe:
            return await self._execute_serially(calls, context)
        else:
            return await self._execute_concurrently(calls, context)

    async def _execute_serially(self, calls: List[ToolCall],
                                context: Dict[str, Any]) -> List[ToolCallResult]:
        results = []
        for call in calls:
            result = await self._execute_single(call, context)
            results.append(result)
        return results

    async def _execute_concurrently(self, calls: List[ToolCall],
                                     context: Dict[str, Any]) -> List[ToolCallResult]:
        semaphore = asyncio.Semaphore(self._max_concurrency)

        async def limited_execute(call):
            async with semaphore:
                return await self._execute_single(call, context)

        tasks = [limited_execute(call) for call in calls]
        return await asyncio.gather(*tasks)

    async def _execute_single(self, call: ToolCall,
                              context: Dict[str, Any]) -> ToolCallResult:
        """执行单个工具调用"""
        if self._hook_manager:
            hook_result = await self._hook_manager.fire(HookEvent.PRE_TOOL_USE, {
                "tool_name": call.name,
                "tool_input": call.input,
                "tool_call_id": call.id,
            })
            if hook_result.permission_behavior == "deny":
                return ToolCallResult(
                    tool_call_id=call.id,
                    tool_name=call.name,
                    success=False,
                    error=f"钩子拒绝执行: {hook_result.message}",
                )
            if hook_result.prevent_continuation:
                return ToolCallResult(
                    tool_call_id=call.id,
                    tool_name=call.name,
                    success=False,
                    error="钩子阻止继续执行",
                )
            if hook_result.updated_input:
                call.input = {**call.input, **hook_result.updated_input}

        if self._permission_checker:
            perm_result = self._permission_checker.check_permission(
                call.name, is_read_only=call.is_read_only
            )
            if not perm_result.allowed:
                return ToolCallResult(
                    tool_call_id=call.id,
                    tool_name=call.name,
                    success=False,
                    error=f"权限不足: {perm_result.reason}",
                )

        start = time.time()
        try:
            if self._tool_registry:
                tool_result = await self._tool_registry.execute(call.name, call.input, context)
                result = ToolCallResult(
                    tool_call_id=call.id,
                    tool_name=call.name,
                    success=tool_result.success,
                    output=tool_result.output,
                    error=tool_result.error,
                    duration_ms=(time.time() - start) * 1000,
                )
            else:
                result = ToolCallResult(
                    tool_call_id=call.id,
                    tool_name=call.name,
                    success=False,
                    error="工具注册中心未配置",
                    duration_ms=(time.time() - start) * 1000,
                )
        except Exception as e:
            result = ToolCallResult(
                tool_call_id=call.id,
                tool_name=call.name,
                success=False,
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

        if self._hook_manager:
            event = HookEvent.POST_TOOL_USE if result.success else HookEvent.POST_TOOL_USE_FAILURE
            await self._hook_manager.fire(event, {
                "tool_name": call.name,
                "tool_result": result.output,
                "tool_error": result.error,
                "success": result.success,
                "tool_call_id": call.id,
            })

        return result


class AgentEngine:
    """
    代理引擎 - 系统心脏
    实现 Agentic Loop：用户输入→LLM调用→工具执行→结果回传→继续循环
    """

    def __init__(self, ollama_client=None, tool_registry=None,
                 permission_checker=None, compact_service=None,
                 session_manager=None):
        self._ollama = ollama_client
        self._tool_registry = tool_registry
        self._permission_checker = permission_checker
        self._compact_service = compact_service
        self._session_manager = session_manager
        self._hook_manager = HookManager()
        self._orchestrator = ToolOrchestrator(
            tool_registry=tool_registry,
            permission_checker=permission_checker,
            hook_manager=self._hook_manager,
        )

        self._state = LoopState.IDLE
        self._messages: List[Dict[str, Any]] = []
        self._turn_count = 0
        self._max_turns = 50
        self._system_prompt = ""
        self._model = "gemma4:e4b"
        self._context_window = 8192
        self._max_output_tokens = 4096
        self._auto_compact_enabled = True
        self._auto_compact_buffer = 13000
        self._total_tokens = 0
        self._history: List[LoopIteration] = []

    @property
    def state(self) -> LoopState:
        return self._state

    @property
    def turn_count(self) -> int:
        return self._turn_count

    @property
    def hook_manager(self) -> HookManager:
        return self._hook_manager

    def configure(self, system_prompt: str = "", model: str = "",
                  context_window: int = 0, max_turns: int = 0,
                  auto_compact: bool = None):
        if system_prompt:
            self._system_prompt = system_prompt
        if model:
            self._model = model
        if context_window:
            self._context_window = context_window
        if max_turns:
            self._max_turns = max_turns
        if auto_compact is not None:
            self._auto_compact_enabled = auto_compact

    def set_messages(self, messages: List[Dict[str, Any]]):
        self._messages = list(messages)

    def get_messages(self) -> List[Dict[str, Any]]:
        return list(self._messages)

    async def run(self, user_input: str,
                  on_token: Callable[[str], Awaitable[None]] = None,
                  on_tool_call: Callable[[ToolCall], Awaitable[None]] = None,
                  on_tool_result: Callable[[ToolCallResult], Awaitable[None]] = None,
                  on_iteration: Callable[[LoopIteration], Awaitable[None]] = None) -> str:
        """
        运行代理循环
        核心流程：用户输入→LLM调用→工具执行→结果回传→继续循环
        """
        self._state = LoopState.THINKING
        self._messages.append({"role": "user", "content": user_input})

        if self._session_manager:
            try:
                self._session_manager.add_message("user", user_input)
            except Exception:
                pass

        final_response = ""

        try:
            while self._turn_count < self._max_turns:
                self._turn_count += 1
                iteration = LoopIteration(turn=self._turn_count)
                iter_start = time.time()

                if self._auto_compact_enabled:
                    await self._check_and_compact()

                self._state = LoopState.THINKING
                llm_result = await self._call_llm(on_token)

                if not llm_result:
                    break

                iteration.model_response = llm_result
                self._messages.append({"role": "assistant", "content": llm_result})

                tool_calls = self._extract_tool_calls(llm_result)
                iteration.tool_calls = tool_calls

                if not tool_calls:
                    final_response = llm_result
                    self._state = LoopState.IDLE
                    iteration.state = LoopState.IDLE
                    iteration.duration_ms = (time.time() - iter_start) * 1000
                    self._history.append(iteration)
                    break

                self._state = LoopState.EXECUTING_TOOLS
                for tc in tool_calls:
                    if on_tool_call:
                        await on_tool_call(tc)

                batches = self._orchestrator.partition_tool_calls(tool_calls)
                all_results = []
                for batch in batches:
                    results = await self._orchestrator.execute_batch(batch)
                    all_results.extend(results)

                iteration.tool_results = all_results

                for tr in all_results:
                    if on_tool_result:
                        await on_tool_result(tr)
                    self._messages.append({
                        "role": "tool_result",
                        "content": tr.output if tr.success else f"错误: {tr.error}",
                        "tool_call_id": tr.tool_call_id,
                        "tool_name": tr.tool_name,
                    })

                iteration.duration_ms = (time.time() - iter_start) * 1000
                self._history.append(iteration)

                if on_iteration:
                    await on_iteration(iteration)

                stop = await self._check_stop_hooks()
                if stop:
                    break

            if not final_response and self._messages:
                for msg in reversed(self._messages):
                    if msg.get("role") == "assistant":
                        final_response = msg.get("content", "")
                        break

        except Exception as e:
            self._state = LoopState.ERROR
            logger.error(f"代理循环异常: {e}")
            final_response = f"代理循环异常: {str(e)}"
        finally:
            if self._state != LoopState.ERROR:
                self._state = LoopState.IDLE

        if self._session_manager and final_response:
            try:
                self._session_manager.add_message("assistant", final_response)
            except Exception:
                pass

        return final_response

    async def _call_llm(self, on_token: Callable = None) -> str:
        """调用 LLM（异步包装，不阻塞事件循环）"""
        try:
            import ollama
            messages = []
            if self._system_prompt:
                messages.append({"role": "system", "content": self._system_prompt})

            from kairos.services.pipeline import normalize_messages
            normalized = normalize_messages(self._messages)
            messages.extend(normalized)

            loop = asyncio.get_event_loop()

            if on_token:
                try:
                    stream = await loop.run_in_executor(
                        None,
                        lambda: ollama.chat(
                            model=self._model,
                            messages=messages,
                            stream=True,
                        )
                    )
                    full_content = ""
                    for chunk in stream:
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            full_content += content
                            await on_token(content)
                    return full_content
                except Exception as e:
                    logger.warning(f"流式 LLM 调用失败，回退非流式: {e}")

            response = await loop.run_in_executor(
                None,
                lambda: ollama.chat(model=self._model, messages=messages)
            )

            try:
                from kairos.services.token_tracker import get_token_tracker
                from kairos.services.cost_tracker import get_cost_tracker
                tt = get_token_tracker()
                ct = get_cost_tracker()
                prompt_eval = response.get('prompt_eval_count', 0) or 0
                eval_count = response.get('eval_count', 0) or 0
                if prompt_eval or eval_count:
                    tt.record_usage(self._model, prompt_eval, eval_count)
                    ct.record_usage(self._model, prompt_eval, eval_count)
            except Exception:
                pass

            return response.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return f"[LLM 调用失败: {str(e)}]"

    def _extract_tool_calls(self, response, raw_response: Dict = None) -> List[ToolCall]:
        """从 LLM 响应中提取工具调用（优先 Ollama 原生格式，回退 XML 解析）"""
        calls = []

        if raw_response:
            native_calls = raw_response.get("message", {}).get("tool_calls", [])
            if native_calls:
                for i, tc in enumerate(native_calls):
                    func = tc.get("function", tc)
                    name = func.get("name", "")
                    input_data = func.get("arguments", func.get("parameters", {}))
                    if isinstance(input_data, str):
                        try:
                            input_data = json.loads(input_data)
                        except json.JSONDecodeError:
                            input_data = {"raw_input": input_data}

                    tool_def = None
                    if self._tool_registry:
                        tool_def = self._tool_registry.get(name)

                    calls.append(ToolCall(
                        id=f"tc_{i}",
                        name=name,
                        input_data=input_data,
                        is_concurrency_safe=getattr(tool_def, 'is_concurrency_safe', False) if tool_def else False,
                        is_read_only=getattr(tool_def, 'is_read_only', False) if tool_def else False,
                    ))
                return calls

        if isinstance(response, str):
            try:
                import re
                pattern = r'<tool_call\s+name="([^"]+)"\s*>(.*?)</tool_call'
                matches = re.findall(pattern, response, re.DOTALL)
                for i, (name, input_str) in enumerate(matches):
                    try:
                        input_data = json.loads(input_str.strip())
                    except json.JSONDecodeError:
                        input_data = {"raw_input": input_str.strip()}

                    tool_def = None
                    if self._tool_registry:
                        tool_def = self._tool_registry.get(name)

                    calls.append(ToolCall(
                        id=f"tc_{i}_{int(time.time()*1000)}",
                        name=name,
                        input_data=input_data,
                        is_concurrency_safe=getattr(tool_def, 'is_concurrency_safe', False) if tool_def else False,
                        is_read_only=getattr(tool_def, 'is_read_only', False) if tool_def else False,
                    ))
            except Exception as e:
                logger.debug(f"工具调用提取异常: {e}")

        return calls

    async def _check_and_compact(self):
        """检查并执行自动压缩"""
        if not self._compact_service:
            return

        try:
            if self._compact_service.should_compact(self._messages):
                self._state = LoopState.COMPACTING
                result = await self._compact_service.compact(self._messages)
                if result.get("messages"):
                    self._messages = result["messages"]
                logger.info(f"自动压缩完成: {result.get('level', 'unknown')}")
        except Exception as e:
            logger.error(f"自动压缩失败: {e}")

    async def _check_stop_hooks(self) -> bool:
        """检查停止钩子"""
        result = await self._hook_manager.fire(HookEvent.STOP, {
            "turn_count": self._turn_count,
            "messages": self._messages,
        })
        return result.prevent_continuation

    def get_stats(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "turn_count": self._turn_count,
            "max_turns": self._max_turns,
            "message_count": len(self._messages),
            "total_tokens": self._total_tokens,
            "model": self._model,
            "auto_compact": self._auto_compact_enabled,
            "history_count": len(self._history),
            "hooks": self._hook_manager.list_hooks(),
        }


_agent_engine: Optional[AgentEngine] = None


def get_agent_engine() -> AgentEngine:
    global _agent_engine
    if _agent_engine is None:
        try:
            from kairos.services.tools import get_tool_registry
            from kairos.services.compact import get_compact_service
            from kairos.services.permission import get_permission_checker
            from kairos.services.session import get_session_manager
            _agent_engine = AgentEngine(
                tool_registry=get_tool_registry(),
                permission_checker=get_permission_checker(),
                compact_service=get_compact_service(),
                session_manager=get_session_manager(),
            )
        except Exception as e:
            logger.error(f"代理引擎初始化失败: {e}")
            _agent_engine = AgentEngine()
    return _agent_engine
