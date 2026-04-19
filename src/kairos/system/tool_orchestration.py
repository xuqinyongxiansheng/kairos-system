"""
工具编排系统 - 分区执行策略

设计理念来源:
- cc-haha-main/src/services/tools/toolOrchestration.ts
- 只读工具并行执行，写入工具串行执行

核心特性:
1. 工具分区：只读 vs 写入
2. 并发控制：最多10个并发
3. 依赖解析：工具间依赖关系
4. 超时处理：工具执行超时
5. 重试机制：失败自动重试
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, Generic, List, Optional, Tuple, TypeVar

T = TypeVar('T')
R = TypeVar('R')


class ToolCategory(Enum):
    """工具分类"""
    READ_ONLY = "read_only"
    WRITE = "write"
    NETWORK = "network"
    SYSTEM = "system"
    CUSTOM = "custom"


class ExecutionMode(Enum):
    """执行模式"""
    PARALLEL = "parallel"
    SERIAL = "serial"
    CONDITIONAL = "conditional"


class ToolStatus(Enum):
    """工具状态"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    category: ToolCategory = ToolCategory.READ_ONLY
    execution_mode: ExecutionMode = ExecutionMode.PARALLEL
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    dependencies: List[str] = field(default_factory=list)
    schema: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_read_only(self) -> bool:
        return self.category == ToolCategory.READ_ONLY
    
    def is_concurrency_safe(self) -> bool:
        return self.execution_mode == ExecutionMode.PARALLEL


@dataclass
class ToolCallRequest:
    """工具调用请求"""
    id: str
    tool_name: str
    arguments: Dict[str, Any]
    priority: int = 0
    timeout: Optional[float] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "priority": self.priority,
            "timeout": self.timeout
        }


@dataclass
class ToolCallResult:
    """工具调用结果"""
    request_id: str
    tool_name: str
    status: ToolStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    duration: float = 0.0
    retry_count: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "tool_name": self.tool_name,
            "status": self.status.value,
            "result": str(self.result)[:500] if self.result else None,
            "error": self.error,
            "duration": self.duration,
            "retry_count": self.retry_count,
            "timestamp": self.timestamp.isoformat()
        }
    
    @property
    def success(self) -> bool:
        return self.status == ToolStatus.SUCCESS


@dataclass
class ExecutionBatch:
    """执行批次"""
    is_concurrency_safe: bool
    requests: List[ToolCallRequest]
    results: List[ToolCallResult] = field(default_factory=list)


class ToolExecutor(ABC):
    """工具执行器基类"""
    
    @abstractmethod
    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Any:
        """执行工具"""
        pass


class DefaultToolExecutor(ToolExecutor):
    """默认工具执行器"""
    
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
    
    def register_handler(
        self, 
        tool_name: str, 
        handler: Callable
    ) -> None:
        """注册工具处理器"""
        self._handlers[tool_name] = handler
    
    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Any:
        """执行工具"""
        handler = self._handlers.get(tool_name)
        if handler:
            if asyncio.iscoroutinefunction(handler):
                return await handler(arguments, context)
            else:
                return handler(arguments, context)
        raise ValueError(f"未找到工具处理器: {tool_name}")


class DependencyResolver:
    """
    依赖解析器
    
    解析工具间的依赖关系，确定执行顺序
    """
    
    def __init__(self):
        self._dependencies: Dict[str, List[str]] = {}
    
    def add_dependency(
        self, 
        tool_name: str, 
        depends_on: str
    ) -> None:
        """添加依赖关系"""
        if tool_name not in self._dependencies:
            self._dependencies[tool_name] = []
        self._dependencies[tool_name].append(depends_on)
    
    def get_execution_order(
        self, 
        requests: List[ToolCallRequest]
    ) -> List[List[ToolCallRequest]]:
        """
        获取执行顺序
        
        返回分层执行计划，每层可并行执行
        """
        if not requests:
            return []
        
        request_map = {r.tool_name: r for r in requests}
        in_degree = {r.tool_name: 0 for r in requests}
        
        for r in requests:
            deps = self._dependencies.get(r.tool_name, [])
            for dep in deps:
                if dep in request_map:
                    in_degree[r.tool_name] += 1
        
        result = []
        remaining = set(r.tool_name for r in requests)
        
        while remaining:
            ready = [
                request_map[name] 
                for name in remaining 
                if in_degree[name] == 0
            ]
            
            if not ready:
                break
            
            result.append(ready)
            
            for r in ready:
                remaining.remove(r.tool_name)
                
                for other_name in remaining:
                    if r.tool_name in self._dependencies.get(other_name, []):
                        in_degree[other_name] -= 1
        
        return result
    
    def detect_cycle(
        self, 
        requests: List[ToolCallRequest]
    ) -> Optional[List[str]]:
        """检测循环依赖"""
        visited = set()
        rec_stack = set()
        cycle_path = []
        
        def dfs(tool_name: str, path: List[str]) -> bool:
            visited.add(tool_name)
            rec_stack.add(tool_name)
            path.append(tool_name)
            
            for dep in self._dependencies.get(tool_name, []):
                if dep not in visited:
                    if dfs(dep, path):
                        return True
                elif dep in rec_stack:
                    cycle_path.extend(path)
                    cycle_path.append(dep)
                    return True
            
            path.pop()
            rec_stack.remove(tool_name)
            return False
        
        for r in requests:
            if r.tool_name not in visited:
                if dfs(r.tool_name, []):
                    return cycle_path
        
        return None


class ToolOrchestrator:
    """
    工具编排器
    
    核心功能:
    1. 工具分区：只读 vs 写入
    2. 并发控制：最多N个并发
    3. 依赖解析：确定执行顺序
    4. 超时处理：工具执行超时
    5. 重试机制：失败自动重试
    """
    
    def __init__(
        self,
        tool_definitions: Optional[Dict[str, ToolDefinition]] = None,
        executor: Optional[ToolExecutor] = None,
        max_concurrency: int = 10,
        default_timeout: float = 30.0
    ):
        self.definitions = tool_definitions or {}
        self.executor = executor or DefaultToolExecutor()
        self.max_concurrency = max_concurrency
        self.default_timeout = default_timeout
        self.dependency_resolver = DependencyResolver()
        
        self._execution_stats = {
            "total_calls": 0,
            "successful": 0,
            "failed": 0,
            "retries": 0,
            "timeouts": 0
        }
    
    def register_tool(self, definition: ToolDefinition) -> None:
        """注册工具"""
        self.definitions[definition.name] = definition
        
        for dep in definition.dependencies:
            self.dependency_resolver.add_dependency(definition.name, dep)
    
    def partition_tool_calls(
        self,
        requests: List[ToolCallRequest]
    ) -> List[ExecutionBatch]:
        """
        分区工具调用
        
        将工具调用分为多个批次：
        1. 只读工具批次（可并行）
        2. 写入工具批次（串行）
        """
        if not requests:
            return []
        
        batches: List[ExecutionBatch] = []
        current_safe_batch: List[ToolCallRequest] = []
        current_unsafe_batch: List[ToolCallRequest] = []
        
        for request in requests:
            definition = self.definitions.get(request.tool_name)
            
            is_safe = True
            if definition:
                is_safe = definition.is_concurrency_safe()
            
            if is_safe:
                if current_unsafe_batch:
                    batches.append(ExecutionBatch(
                        is_concurrency_safe=False,
                        requests=current_unsafe_batch
                    ))
                    current_unsafe_batch = []
                current_safe_batch.append(request)
            else:
                if current_safe_batch:
                    batches.append(ExecutionBatch(
                        is_concurrency_safe=True,
                        requests=current_safe_batch
                    ))
                    current_safe_batch = []
                current_unsafe_batch.append(request)
        
        if current_safe_batch:
            batches.append(ExecutionBatch(
                is_concurrency_safe=True,
                requests=current_safe_batch
            ))
        
        if current_unsafe_batch:
            batches.append(ExecutionBatch(
                is_concurrency_safe=False,
                requests=current_unsafe_batch
            ))
        
        return batches
    
    async def run_tools(
        self,
        requests: List[ToolCallRequest],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[ToolCallResult, None]:
        """
        运行工具调用
        
        按分区策略执行工具
        """
        context = context or {}
        
        cycle = self.dependency_resolver.detect_cycle(requests)
        if cycle:
            yield ToolCallResult(
                request_id="cycle_detection",
                tool_name="dependency_resolver",
                status=ToolStatus.FAILED,
                error=f"检测到循环依赖: {' -> '.join(cycle)}"
            )
            return
        
        batches = self.partition_tool_calls(requests)
        
        for batch in batches:
            if batch.is_concurrency_safe:
                async for result in self._run_concurrently(batch.requests, context):
                    batch.results.append(result)
                    yield result
            else:
                async for result in self._run_serially(batch.requests, context):
                    batch.results.append(result)
                    yield result
    
    async def _run_concurrently(
        self,
        requests: List[ToolCallRequest],
        context: Dict[str, Any]
    ) -> AsyncGenerator[ToolCallResult, None]:
        """并行执行工具"""
        semaphore = asyncio.Semaphore(self.max_concurrency)
        
        async def execute_with_semaphore(
            request: ToolCallRequest
        ) -> ToolCallResult:
            async with semaphore:
                return await self._execute_single(request, context)
        
        tasks = [
            asyncio.create_task(execute_with_semaphore(r))
            for r in requests
        ]
        
        for task in asyncio.as_completed(tasks):
            result = await task
            yield result
    
    async def _run_serially(
        self,
        requests: List[ToolCallRequest],
        context: Dict[str, Any]
    ) -> AsyncGenerator[ToolCallResult, None]:
        """串行执行工具"""
        for request in requests:
            result = await self._execute_single(request, context)
            yield result
    
    async def _execute_single(
        self,
        request: ToolCallRequest,
        context: Dict[str, Any]
    ) -> ToolCallResult:
        """执行单个工具"""
        definition = self.definitions.get(request.tool_name)
        timeout = request.timeout or (definition.timeout if definition else self.default_timeout)
        max_retries = definition.max_retries if definition else 3
        retry_delay = definition.retry_delay if definition else 1.0
        
        self._execution_stats["total_calls"] += 1
        
        for attempt in range(max_retries):
            start_time = time.time()
            
            try:
                result = await asyncio.wait_for(
                    self.executor.execute(
                        request.tool_name,
                        request.arguments,
                        {**context, **request.context}
                    ),
                    timeout=timeout
                )
                
                duration = time.time() - start_time
                
                self._execution_stats["successful"] += 1
                
                return ToolCallResult(
                    request_id=request.id,
                    tool_name=request.tool_name,
                    status=ToolStatus.SUCCESS,
                    result=result,
                    duration=duration,
                    retry_count=attempt
                )
                
            except asyncio.TimeoutError:
                duration = time.time() - start_time
                self._execution_stats["timeouts"] += 1
                
                if attempt < max_retries - 1:
                    self._execution_stats["retries"] += 1
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
                
                return ToolCallResult(
                    request_id=request.id,
                    tool_name=request.tool_name,
                    status=ToolStatus.TIMEOUT,
                    error=f"工具执行超时 ({timeout}s)",
                    duration=duration,
                    retry_count=attempt
                )
                
            except Exception as e:
                duration = time.time() - start_time
                
                if attempt < max_retries - 1:
                    self._execution_stats["retries"] += 1
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
                
                self._execution_stats["failed"] += 1
                
                return ToolCallResult(
                    request_id=request.id,
                    tool_name=request.tool_name,
                    status=ToolStatus.FAILED,
                    error=str(e),
                    duration=duration,
                    retry_count=attempt
                )
        
        return ToolCallResult(
            request_id=request.id,
            tool_name=request.tool_name,
            status=ToolStatus.FAILED,
            error="超过最大重试次数"
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        return {
            **self._execution_stats,
            "success_rate": (
                self._execution_stats["successful"] / 
                max(1, self._execution_stats["total_calls"])
            )
        }
    
    def reset_stats(self) -> None:
        """重置统计"""
        self._execution_stats = {
            "total_calls": 0,
            "successful": 0,
            "failed": 0,
            "retries": 0,
            "timeouts": 0
        }


class ToolCallBuilder:
    """工具调用构建器"""
    
    def __init__(self):
        self._counter = 0
    
    def build(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        priority: int = 0,
        timeout: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ToolCallRequest:
        """构建工具调用请求"""
        self._counter += 1
        
        return ToolCallRequest(
            id=self._generate_id(tool_name),
            tool_name=tool_name,
            arguments=arguments,
            priority=priority,
            timeout=timeout,
            context=context or {}
        )
    
    def build_batch(
        self,
        calls: List[Tuple[str, Dict[str, Any]]]
    ) -> List[ToolCallRequest]:
        """批量构建工具调用请求"""
        return [self.build(name, args) for name, args in calls]
    
    def _generate_id(self, tool_name: str) -> str:
        """生成请求ID"""
        content = f"{tool_name}:{time.time()}:{self._counter}"
        return f"{tool_name}_{hashlib.md5(content.encode()).hexdigest()[:8]}"


def create_default_tools() -> Dict[str, ToolDefinition]:
    """创建默认工具定义"""
    return {
        "read": ToolDefinition(
            name="read",
            description="读取文件内容",
            category=ToolCategory.READ_ONLY,
            execution_mode=ExecutionMode.PARALLEL,
            timeout=10.0
        ),
        "write": ToolDefinition(
            name="write",
            description="写入文件内容",
            category=ToolCategory.WRITE,
            execution_mode=ExecutionMode.SERIAL,
            timeout=30.0
        ),
        "edit": ToolDefinition(
            name="edit",
            description="编辑文件内容",
            category=ToolCategory.WRITE,
            execution_mode=ExecutionMode.SERIAL,
            timeout=30.0
        ),
        "bash": ToolDefinition(
            name="bash",
            description="执行Shell命令",
            category=ToolCategory.SYSTEM,
            execution_mode=ExecutionMode.SERIAL,
            timeout=60.0
        ),
        "grep": ToolDefinition(
            name="grep",
            description="搜索文件内容",
            category=ToolCategory.READ_ONLY,
            execution_mode=ExecutionMode.PARALLEL,
            timeout=30.0
        ),
        "glob": ToolDefinition(
            name="glob",
            description="匹配文件路径",
            category=ToolCategory.READ_ONLY,
            execution_mode=ExecutionMode.PARALLEL,
            timeout=10.0
        ),
        "web_fetch": ToolDefinition(
            name="web_fetch",
            description="获取网页内容",
            category=ToolCategory.NETWORK,
            execution_mode=ExecutionMode.PARALLEL,
            timeout=60.0
        ),
        "web_search": ToolDefinition(
            name="web_search",
            description="搜索网络内容",
            category=ToolCategory.NETWORK,
            execution_mode=ExecutionMode.PARALLEL,
            timeout=30.0
        )
    }
