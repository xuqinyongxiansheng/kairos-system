"""
异步生成器状态机 - 核心Agent循环引擎

设计理念来源:
- cc-haha-main/src/query.ts: 异步生成器驱动的状态机
- 非ReAct模式，通过状态赋值驱动循环

核心特性:
1. 异步生成器实时产出消息
2. 状态赋值驱动循环（非递归）
3. 五阶段循环：准备→调用→决策→执行→更新
4. 流式工具执行
5. 完善的错误恢复机制
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, Generic, List, Optional, TypeVar, Union

T = TypeVar('T')
R = TypeVar('R')


class TransitionReason(Enum):
    """状态转换原因"""
    NEXT_TURN = "next_turn"
    TOOL_CALL = "tool_call"
    COMPLETE = "complete"
    ERROR = "error"
    COMPACT = "compact"
    RECOVERY = "recovery"
    USER_INTERRUPT = "user_interrupt"


class MessageRole(Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCallStatus(Enum):
    """工具调用状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class Message:
    """消息基类"""
    role: MessageRole = MessageRole.USER
    content: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ToolCall:
    """工具调用"""
    id: str
    name: str
    arguments: Dict[str, Any]
    status: ToolCallStatus = ToolCallStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    duration: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "arguments": self.arguments,
            "status": self.status.value,
            "result": str(self.result)[:500] if self.result else None,
            "error": self.error,
            "duration": self.duration
        }


@dataclass
class AssistantMessage(Message):
    """助手消息"""
    role: MessageRole = MessageRole.ASSISTANT
    tool_calls: List[ToolCall] = field(default_factory=list)
    thinking: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "thinking": self.thinking
        })
        return d


@dataclass
class ToolResultMessage(Message):
    """工具结果消息"""
    role: MessageRole = MessageRole.TOOL
    tool_call_id: str = ""
    tool_name: str = ""
    success: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "success": self.success
        })
        return d


@dataclass
class Transition:
    """状态转换"""
    reason: TransitionReason
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class State(Generic[T]):
    """
    Agent状态
    
    核心设计：通过状态赋值而非递归调用驱动循环
    """
    messages: List[Message] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    turn_count: int = 0
    max_output_tokens_recovery_count: int = 0
    has_attempted_compact: bool = False
    transition: Optional[Transition] = None
    data: Optional[T] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "messages": [m.to_dict() for m in self.messages],
            "context": self.context,
            "turn_count": self.turn_count,
            "max_output_tokens_recovery_count": self.max_output_tokens_recovery_count,
            "has_attempted_compact": self.has_attempted_compact,
            "transition": {
                "reason": self.transition.reason.value,
                "metadata": self.transition.metadata
            } if self.transition else None,
            "metadata": self.metadata
        }


class Tool(ABC):
    """工具基类"""
    
    name: str = ""
    description: str = ""
    is_read_only: bool = True
    
    @abstractmethod
    async def execute(
        self, 
        arguments: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Any:
        """执行工具"""
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具Schema"""
        return {
            "name": self.name,
            "description": self.description,
            "is_read_only": self.is_read_only
        }


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._lock = asyncio.Lock()
    
    def register(self, tool: Tool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[Tool]:
        """列出所有工具"""
        return list(self._tools.values())
    
    def list_read_only_tools(self) -> List[Tool]:
        """列出只读工具"""
        return [t for t in self._tools.values() if t.is_read_only]
    
    def list_write_tools(self) -> List[Tool]:
        """列出写入工具"""
        return [t for t in self._tools.values() if not t.is_read_only]


class StreamingToolExecutor:
    """
    流式工具执行器
    
    在流式传输过程中就开始执行工具
    """
    
    def __init__(self, tool_registry: ToolRegistry):
        self.registry = tool_registry
        self._running_tasks: Dict[str, asyncio.Task] = {}
    
    async def start_execution(
        self,
        tool_call: ToolCall,
        context: Dict[str, Any]
    ) -> asyncio.Task:
        """开始执行工具"""
        tool = self.registry.get(tool_call.name)
        if not tool:
            tool_call.status = ToolCallStatus.FAILED
            tool_call.error = f"未知工具: {tool_call.name}"
            return asyncio.create_task(asyncio.sleep(0))
        
        async def execute():
            tool_call.status = ToolCallStatus.RUNNING
            start_time = time.time()
            
            try:
                result = await tool.execute(tool_call.arguments, context)
                tool_call.result = result
                tool_call.status = ToolCallStatus.SUCCESS
            except Exception as e:
                tool_call.error = str(e)
                tool_call.status = ToolCallStatus.FAILED
            finally:
                tool_call.duration = time.time() - start_time
        
        task = asyncio.create_task(execute())
        self._running_tasks[tool_call.id] = task
        return task
    
    async def wait_for_completion(
        self, 
        tool_call_id: str
    ) -> Optional[ToolCall]:
        """等待工具完成"""
        task = self._running_tasks.get(tool_call_id)
        if task:
            await task
        return None


class ContextCompressor:
    """
    上下文压缩器
    
    四层压缩策略
    """
    
    def __init__(self, max_tokens: int = 200000):
        self.max_tokens = max_tokens
        self.compression_stats = {
            "snip": 0,
            "micro": 0,
            "collapse": 0,
            "auto_compact": 0
        }
    
    def estimate_tokens(self, messages: List[Message]) -> int:
        """估算token数量"""
        total = 0
        for msg in messages:
            total += len(msg.content) // 4
            if isinstance(msg, AssistantMessage):
                for tc in msg.tool_calls:
                    total += len(str(tc.arguments)) // 4
        return total
    
    def snip_compress(
        self, 
        messages: List[Message],
        target_ratio: float = 0.8
    ) -> List[Message]:
        """
        Snip压缩 - 智能删除旧消息中的冗余token
        """
        if len(messages) <= 2:
            return messages
        
        current_tokens = self.estimate_tokens(messages)
        target_tokens = int(current_tokens * target_ratio)
        
        if current_tokens <= target_tokens:
            return messages
        
        compressed = []
        for i, msg in enumerate(messages):
            if i < len(messages) - 2:
                if len(msg.content) > 500:
                    content = msg.content[:500] + "\n...[已压缩]"
                    compressed.append(Message(
                        role=msg.role,
                        content=content,
                        metadata={**msg.metadata, "snipped": True}
                    ))
                else:
                    compressed.append(msg)
            else:
                compressed.append(msg)
        
        self.compression_stats["snip"] += 1
        return compressed
    
    def micro_compress(
        self, 
        messages: List[Message]
    ) -> List[Message]:
        """
        Micro压缩 - 修改已缓存消息的内容
        """
        compressed = []
        for msg in messages:
            if isinstance(msg, AssistantMessage):
                if msg.thinking and len(msg.thinking) > 200:
                    msg.thinking = msg.thinking[:200] + "...[已压缩]"
            compressed.append(msg)
        
        self.compression_stats["micro"] += 1
        return compressed
    
    def context_collapse(
        self, 
        messages: List[Message],
        summary_func: Optional[Callable] = None
    ) -> List[Message]:
        """
        上下文折叠 - 分阶段摘要历史消息
        """
        if len(messages) <= 10:
            return messages
        
        early_messages = messages[:-5]
        recent_messages = messages[-5:]
        
        if summary_func:
            summary = summary_func(early_messages)
        else:
            summary = f"[已折叠 {len(early_messages)} 条早期消息]"
        
        summary_msg = Message(
            role=MessageRole.SYSTEM,
            content=summary,
            metadata={"collapsed": True, "original_count": len(early_messages)}
        )
        
        self.compression_stats["collapse"] += 1
        return [summary_msg] + recent_messages
    
    def auto_compact(
        self, 
        messages: List[Message],
        compact_func: Optional[Callable] = None
    ) -> List[Message]:
        """
        Auto Compact - 通过Claude生成完整摘要
        """
        if compact_func:
            messages = compact_func(messages)
        
        self.compression_stats["auto_compact"] += 1
        return messages
    
    def compress(
        self, 
        messages: List[Message],
        force: bool = False
    ) -> List[Message]:
        """执行压缩"""
        current_tokens = self.estimate_tokens(messages)
        
        if not force and current_tokens < self.max_tokens * 0.8:
            return messages
        
        messages = self.snip_compress(messages)
        
        current_tokens = self.estimate_tokens(messages)
        if current_tokens > self.max_tokens * 0.7:
            messages = self.micro_compress(messages)
        
        current_tokens = self.estimate_tokens(messages)
        if current_tokens > self.max_tokens * 0.6:
            messages = self.context_collapse(messages)
        
        return messages
    
    def get_stats(self) -> Dict[str, int]:
        """获取压缩统计"""
        return self.compression_stats.copy()


class AsyncGeneratorStateMachine(Generic[T, R]):
    """
    异步生成器状态机
    
    核心Agent循环引擎
    
    使用方式:
        machine = AsyncGeneratorStateMachine(config)
        
        async for event in machine.run(initial_state):
            print(event)
    """
    
    def __init__(
        self,
        tool_registry: Optional[ToolRegistry] = None,
        max_iterations: int = 100,
        max_tokens: int = 200000,
        model_caller: Optional[Callable] = None
    ):
        self.tool_registry = tool_registry or ToolRegistry()
        self.max_iterations = max_iterations
        self.max_tokens = max_tokens
        self.model_caller = model_caller
        
        self.compressor = ContextCompressor(max_tokens)
        self.tool_executor = StreamingToolExecutor(self.tool_registry)
        
        self._state: Optional[State[T]] = None
        self._iteration_count = 0
        self._start_time: Optional[float] = None
    
    async def run(
        self, 
        initial_state: State[T],
        callback: Optional[Callable[[str, Any], None]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        运行状态机
        
        五阶段循环：
        1. 消息准备与压缩
        2. 流式API调用
        3. 决策点
        4. 工具编排执行
        5. 状态更新
        """
        self._state = initial_state
        self._start_time = time.time()
        self._iteration_count = 0
        
        yield {
            "type": "start",
            "state": self._state.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        while self._iteration_count < self.max_iterations:
            self._iteration_count += 1
            
            # 阶段1: 消息准备与压缩
            self._state = await self._phase_prepare_messages()
            yield {
                "type": "prepared",
                "turn": self._state.turn_count,
                "message_count": len(self._state.messages)
            }
            
            if callback:
                callback("prepared", {"turn": self._state.turn_count})
            
            # 阶段2: 流式API调用
            async for stream_event in self._phase_call_model():
                yield stream_event
            
            # 阶段3: 决策点
            decision = await self._phase_decision()
            yield {
                "type": "decision",
                "decision": decision
            }
            
            if decision == "stop":
                break
            elif decision == "tool_call":
                # 阶段4: 工具编排执行
                async for tool_event in self._phase_execute_tools():
                    yield tool_event
            
            # 阶段5: 状态更新
            self._state = self._phase_update_state()
            
            yield {
                "type": "turn_complete",
                "turn": self._state.turn_count,
                "transition": self._state.transition.reason.value if self._state.transition else None
            }
        
        yield {
            "type": "complete",
            "iterations": self._iteration_count,
            "duration": time.time() - (self._start_time or 0),
            "state": self._state.to_dict() if self._state else None
        }
    
    async def _phase_prepare_messages(self) -> State[T]:
        """阶段1: 消息准备与压缩"""
        if not self._state:
            return self._state
        
        messages = self._state.messages
        
        messages = self.compressor.compress(messages)
        
        return State(
            messages=messages,
            context=self._state.context,
            turn_count=self._state.turn_count,
            max_output_tokens_recovery_count=self._state.max_output_tokens_recovery_count,
            has_attempted_compact=self._state.has_attempted_compact,
            data=self._state.data,
            metadata=self._state.metadata
        )
    
    async def _phase_call_model(self) -> AsyncGenerator[Dict[str, Any], None]:
        """阶段2: 流式API调用"""
        yield {
            "type": "model_call_start",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if self.model_caller and self._state:
            try:
                async for chunk in self.model_caller(self._state.messages):
                    yield {
                        "type": "model_chunk",
                        "content": chunk
                    }
            except Exception as e:
                yield {
                    "type": "model_error",
                    "error": str(e)
                }
        else:
            yield {
                "type": "model_chunk",
                "content": "[模拟响应]"
            }
        
        yield {
            "type": "model_call_end",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _phase_decision(self) -> str:
        """阶段3: 决策点"""
        if not self._state:
            return "stop"
        
        if self._state.messages:
            last_msg = self._state.messages[-1]
            if isinstance(last_msg, AssistantMessage):
                if last_msg.tool_calls:
                    return "tool_call"
        
        if self._state.turn_count >= self.max_iterations:
            return "stop"
        
        return "stop"
    
    async def _phase_execute_tools(self) -> AsyncGenerator[Dict[str, Any], None]:
        """阶段4: 工具编排执行"""
        if not self._state or not self._state.messages:
            return
        
        last_msg = self._state.messages[-1]
        if not isinstance(last_msg, AssistantMessage):
            return
        
        tool_calls = last_msg.tool_calls
        
        read_only_calls = [tc for tc in tool_calls 
                          if self._is_read_only_tool(tc.name)]
        write_calls = [tc for tc in tool_calls 
                      if not self._is_read_only_tool(tc.name)]
        
        yield {
            "type": "tool_execution_start",
            "read_only_count": len(read_only_calls),
            "write_count": len(write_calls)
        }
        
        for tc in read_only_calls:
            await self.tool_executor.start_execution(
                tc, 
                self._state.context if self._state else {}
            )
        
        for tc in read_only_calls:
            await self.tool_executor.wait_for_completion(tc.id)
            yield {
                "type": "tool_result",
                "tool_call_id": tc.id,
                "tool_name": tc.name,
                "status": tc.status.value,
                "result": str(tc.result)[:500] if tc.result else None,
                "error": tc.error
            }
        
        for tc in write_calls:
            await self.tool_executor.start_execution(
                tc, 
                self._state.context if self._state else {}
            )
            await self.tool_executor.wait_for_completion(tc.id)
            yield {
                "type": "tool_result",
                "tool_call_id": tc.id,
                "tool_name": tc.name,
                "status": tc.status.value,
                "result": str(tc.result)[:500] if tc.result else None,
                "error": tc.error
            }
        
        yield {
            "type": "tool_execution_end"
        }
    
    def _phase_update_state(self) -> State[T]:
        """阶段5: 状态更新"""
        if not self._state:
            return self._state
        
        return State(
            messages=self._state.messages,
            context=self._state.context,
            turn_count=self._state.turn_count + 1,
            max_output_tokens_recovery_count=self._state.max_output_tokens_recovery_count,
            has_attempted_compact=self._state.has_attempted_compact,
            transition=Transition(reason=TransitionReason.NEXT_TURN),
            data=self._state.data,
            metadata=self._state.metadata
        )
    
    def _is_read_only_tool(self, name: str) -> bool:
        """判断是否为只读工具"""
        tool = self.tool_registry.get(name)
        return tool.is_read_only if tool else False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "iterations": self._iteration_count,
            "duration": time.time() - (self._start_time or 0),
            "compression_stats": self.compressor.get_stats(),
            "turn_count": self._state.turn_count if self._state else 0
        }


class AgentLoop:
    """
    Agent循环简化接口
    
    提供更简洁的使用方式
    """
    
    def __init__(
        self,
        tools: Optional[List[Tool]] = None,
        max_iterations: int = 100
    ):
        self.registry = ToolRegistry()
        
        if tools:
            for tool in tools:
                self.registry.register(tool)
        
        self.machine = AsyncGeneratorStateMachine(
            tool_registry=self.registry,
            max_iterations=max_iterations
        )
    
    def register_tool(self, tool: Tool) -> None:
        """注册工具"""
        self.registry.register(tool)
    
    async def run(
        self,
        initial_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """运行Agent循环"""
        initial_state = State(
            messages=[Message(role=MessageRole.USER, content=initial_message)],
            context=context or {}
        )
        
        async for event in self.machine.run(initial_state):
            yield event
    
    async def run_until_complete(
        self,
        initial_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """运行直到完成"""
        final_event = None
        async for event in self.run(initial_message, context):
            final_event = event
        
        return final_event or {"type": "error", "error": "No events generated"}
