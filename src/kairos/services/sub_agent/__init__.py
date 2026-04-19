"""
子代理系统
借鉴 cc-haha-main 的 AgentTool + runAgent 架构：
- 子代理创建与执行
- 同步/异步执行模式
- 独立工具池和权限上下文
- 代理任务追踪

完全重写实现，适配本地 Ollama 大模型服务场景
"""

import os
import json
import time
import uuid
import logging
import asyncio
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger("SubAgent")


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


@dataclass
class AgentTask:
    id: str = field(default_factory=lambda: f"a{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""
    status: AgentStatus = AgentStatus.PENDING
    prompt: str = ""
    model: str = "gemma4:e4b"
    parent_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    result: str = ""
    error: str = ""
    allowed_tools: List[str] = field(default_factory=list)
    max_turns: int = 10

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "model": self.model,
            "parent_id": self.parent_id,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result[:500] if self.result else "",
            "error": self.error,
            "allowed_tools": self.allowed_tools,
            "max_turns": self.max_turns,
        }


class SubAgentRunner:
    """子代理运行器"""

    MAX_RECURSION_DEPTH = 2

    def __init__(self):
        self._tasks: Dict[str, AgentTask] = {}
        self._results: Dict[str, Any] = {}
        self._recursion_depth = 0
        self._max_tasks = 20
        self._background_tasks: Dict[str, asyncio.Task] = {}

    def create_task(self, prompt: str, name: str = "", description: str = "",
                    model: str = "gemma4:e4b", parent_id: str = None,
                    allowed_tools: List[str] = None, max_turns: int = 10) -> AgentTask:
        """创建子代理任务"""
        if len(self._tasks) >= self._max_tasks:
            oldest = min(self._tasks.values(), key=lambda t: t.created_at)
            self._tasks.pop(oldest.id, None)

        task = AgentTask(
            name=name or f"子代理_{uuid.uuid4().hex[:4]}",
            description=description or prompt[:100],
            prompt=prompt,
            model=model,
            parent_id=parent_id,
            allowed_tools=allowed_tools or [],
            max_turns=max_turns,
        )
        self._tasks[task.id] = task
        logger.info(f"创建子代理任务: {task.id} - {task.name}")
        return task

    async def run_sync(self, task: AgentTask) -> AgentTask:
        """同步执行子代理任务"""
        if self._recursion_depth >= self.MAX_RECURSION_DEPTH:
            task.status = AgentStatus.FAILED
            task.error = f"递归深度超限 ({self._recursion_depth}/{self.MAX_RECURSION_DEPTH})"
            logger.warning(f"子代理递归深度超限: {task.id}")
            return task

        task.status = AgentStatus.RUNNING
        task.started_at = time.time()
        self._recursion_depth += 1

        try:
            from kairos.services.agent_engine import get_agent_engine
            engine = get_agent_engine()
            engine._system_prompt = f"你是子代理 '{task.name}'。{task.description}"
            engine._model = task.model
            engine._max_turns = min(task.max_turns, 50)

            result = await engine.run(task.prompt)
            task.result = result
            task.status = AgentStatus.COMPLETED
        except Exception as e:
            task.error = str(e)
            task.status = AgentStatus.FAILED
            logger.error(f"子代理任务失败 [{task.id}]: {e}")
        finally:
            self._recursion_depth -= 1
            task.completed_at = time.time()

        return task

    async def run_async(self, task: AgentTask) -> AgentTask:
        """异步执行子代理任务（后台运行）"""
        async def _run():
            await self.run_sync(task)

        bg_task = asyncio.create_task(_run())
        self._background_tasks[task.id] = bg_task
        return task

    async def wait_for_task(self, task_id: str, timeout: float = 300) -> AgentTask:
        """等待异步任务完成"""
        bg_task = self._background_tasks.get(task_id)
        if not bg_task:
            return self._tasks.get(task_id, AgentTask())

        try:
            await asyncio.wait_for(asyncio.shield(bg_task), timeout=timeout)
        except asyncio.TimeoutError:
            task = self._tasks.get(task_id)
            if task:
                task.status = AgentStatus.FAILED
                task.error = "任务超时"

        return self._tasks.get(task_id, AgentTask())

    def kill_task(self, task_id: str) -> bool:
        """终止任务"""
        task = self._tasks.get(task_id)
        if not task:
            return False

        bg_task = self._background_tasks.get(task_id)
        if bg_task and not bg_task.done():
            bg_task.cancel()

        task.status = AgentStatus.KILLED
        task.completed_at = time.time()
        return True

    def get_task(self, task_id: str) -> Optional[AgentTask]:
        return self._tasks.get(task_id)

    def list_tasks(self, status: AgentStatus = None) -> List[Dict[str, Any]]:
        tasks = self._tasks.values()
        if status:
            tasks = [t for t in tasks if t.status == status]
        return [t.to_dict() for t in sorted(tasks, key=lambda t: t.created_at, reverse=True)]

    def get_stats(self) -> Dict[str, Any]:
        by_status = {}
        for t in self._tasks.values():
            s = t.status.value
            by_status[s] = by_status.get(s, 0) + 1
        return {
            "total_tasks": len(self._tasks),
            "by_status": by_status,
            "background_running": sum(1 for t in self._background_tasks.values() if not t.done()),
        }


_sub_agent_runner: Optional[SubAgentRunner] = None


def get_sub_agent_runner() -> SubAgentRunner:
    global _sub_agent_runner
    if _sub_agent_runner is None:
        _sub_agent_runner = SubAgentRunner()
    return _sub_agent_runner
