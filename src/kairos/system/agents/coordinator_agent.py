# -*- coding: utf-8 -*-
"""
协调Agent (CoordinatorAgent)
协调编排，资源分配/优先级管理
适用于: 多Agent协调、任务分发、资源调度、冲突解决

特征:
- 多Agent编排
- 资源感知调度
- 冲突检测与解决
- 负载均衡
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

from .base_neuron_agent import BaseNeuronAgent, AgentCapability, AgentDecision
from ..core.enums import AgentType, AgentState, MessagePriority
from ..core.synaptic_bus import SynapticMessage, get_synaptic_bus

logger = logging.getLogger("CoordinatorAgent")


@dataclass
class AgentAllocation:
    """Agent分配"""
    agent_id: str
    agent_type: AgentType
    task: str
    priority: MessagePriority
    assigned_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "assigned"


@dataclass
class CoordinationPlan:
    """协调计划"""
    plan_id: str
    task: str
    allocations: List[AgentAllocation] = field(default_factory=list)
    dependencies: List[Dict[str, str]] = field(default_factory=list)
    fallback_plan: Optional[str] = None
    estimated_duration_ms: float = 0.0


class CoordinatorAgent(BaseNeuronAgent):
    """
    协调Agent - 协调编排
    
    触发条件: 多Agent协作、资源分配、优先级管理
    适用场景: 多Agent协调、任务分发、资源调度、冲突解决
    """

    def __init__(self, agent_id: str = "coordinator_agent"):
        capabilities = [
            AgentCapability(
                name="multi_agent_coordination",
                description="多Agent协调",
                confidence_threshold=0.5,
                avg_latency_ms=200.0
            ),
            AgentCapability(
                name="task_distribution",
                description="任务分发",
                confidence_threshold=0.6,
                avg_latency_ms=100.0
            ),
            AgentCapability(
                name="resource_allocation",
                description="资源分配",
                confidence_threshold=0.5,
                avg_latency_ms=150.0
            ),
            AgentCapability(
                name="conflict_resolution",
                description="冲突解决",
                confidence_threshold=0.4,
                avg_latency_ms=300.0
            ),
        ]
        super().__init__(agent_id, AgentType.COORDINATOR, capabilities)

        self._managed_agents: Dict[str, Dict[str, Any]] = {}
        self._active_allocations: Dict[str, AgentAllocation] = {}
        self._coordination_history: List[CoordinationPlan] = []
        self._max_history = 500
        self._max_concurrent_per_agent = 5
        self._load_balance_threshold = 0.8

    def can_handle(self, task: str, confidence: float) -> bool:
        """判断是否需要协调"""
        coord_keywords = ["协调", "分配", "调度", "编排", "统筹",
                         "coordinate", "distribute", "schedule", "orchestrate"]
        if any(kw in task.lower() for kw in coord_keywords):
            return True

        if len(self._managed_agents) > 1:
            return True

        return False

    def register_agent(self, agent_id: str, agent_type: AgentType,
                      capabilities: List[str] = None):
        """
        注册受管Agent
        
        Args:
            agent_id: Agent标识
            agent_type: Agent类型
            capabilities: 能力列表
        """
        self._managed_agents[agent_id] = {
            "type": agent_type,
            "capabilities": capabilities or [],
            "state": AgentState.IDLE,
            "current_load": 0,
            "total_tasks": 0,
            "successful_tasks": 0
        }
        logger.info(f"协调器注册Agent: {agent_id} (类型: {agent_type.value})")

    def unregister_agent(self, agent_id: str):
        """注销Agent"""
        self._managed_agents.pop(agent_id, None)

    async def process(self, content: Dict[str, Any]) -> AgentDecision:
        """协调处理"""
        task = content.get("task", "")
        context = content.get("context", {})
        action = content.get("action", "coordinate")

        if action == "coordinate":
            return await self._coordinate(task, context)
        elif action == "distribute":
            return await self._distribute(task, context)
        elif action == "resolve_conflict":
            return await self._resolve_conflict(task, context)
        elif action == "get_allocation":
            return await self._get_allocation_status(content)
        else:
            return await self._coordinate(task, context)

    async def _coordinate(self, task: str, context: Dict[str, Any]) -> AgentDecision:
        """协调多Agent"""
        import uuid

        plan = CoordinationPlan(
            plan_id=f"plan_{uuid.uuid4().hex[:12]}",
            task=task
        )

        complexity = context.get("complexity", 0.5)
        urgency = context.get("urgency", 0.3)

        if urgency > 0.8:
            suitable_agents = self._find_agents_by_type(AgentType.REFLEX)
            if not suitable_agents:
                suitable_agents = self._find_available_agents()
        elif complexity > 0.7:
            suitable_agents = self._find_agents_by_type(AgentType.DELIBERATIVE)
            if not suitable_agents:
                suitable_agents = self._find_available_agents()
        else:
            suitable_agents = self._find_available_agents()

        if not suitable_agents:
            return AgentDecision(
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                action="no_available_agents",
                confidence=0.1,
                reasoning="无可用Agent"
            )

        selected = self._select_best_agent(suitable_agents, task, context)

        allocation = AgentAllocation(
            agent_id=selected,
            agent_type=self._managed_agents[selected]["type"],
            task=task,
            priority=MessagePriority.HIGH if urgency > 0.7 else MessagePriority.NORMAL
        )

        plan.allocations.append(allocation)
        self._active_allocations[allocation.agent_id] = allocation

        self._managed_agents[selected]["current_load"] += 1
        self._managed_agents[selected]["state"] = AgentState.PROCESSING

        self._coordination_history.append(plan)
        if len(self._coordination_history) > self._max_history:
            self._coordination_history = self._coordination_history[-self._max_history:]

        try:
            bus = get_synaptic_bus()
            message = SynapticMessage(
                sender=self.agent_id,
                recipients=[selected],
                content={"action": "decide", "task": task, "context": context},
                confidence=context.get("confidence", 0.5),
                priority=allocation.priority,
                metadata={"plan_id": plan.plan_id}
            )
            receipts = await bus.send(message)

            delivery_success = all(
                r.status.value in ["delivered", "acknowledged"]
                for r in receipts
            )
        except Exception as e:
            logger.error(f"协调消息发送失败: {e}")
            delivery_success = False

        return AgentDecision(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            action=f"coordinated_to_{selected}",
            confidence=0.8 if delivery_success else 0.3,
            reasoning=f"协调计划 {plan.plan_id}: 任务分配至 {selected} (类型: {allocation.agent_type.value})",
            evidence=[
                {"source": "coordination_plan", "plan_id": plan.plan_id},
                {"source": "agent_selection", "agent_id": selected,
                 "type": allocation.agent_type.value},
                {"source": "delivery", "success": delivery_success}
            ],
            alternatives=[
                {"agent_id": aid, "type": self._managed_agents[aid]["type"].value}
                for aid in suitable_agents if aid != selected
            ],
            metadata={"plan_id": plan.plan_id, "selected_agent": selected}
        )

    async def _distribute(self, task: str, context: Dict[str, Any]) -> AgentDecision:
        """分发任务到多个Agent"""
        import uuid

        sub_tasks = context.get("sub_tasks", [task])
        available = self._find_available_agents()

        if not available:
            return AgentDecision(
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                action="no_available_agents",
                confidence=0.1,
                reasoning="无可用Agent进行分发"
            )

        allocations = []
        for i, sub_task in enumerate(sub_tasks):
            agent_id = available[i % len(available)]
            allocation = AgentAllocation(
                agent_id=agent_id,
                agent_type=self._managed_agents[agent_id]["type"],
                task=sub_task,
                priority=MessagePriority.NORMAL
            )
            allocations.append(allocation)
            self._active_allocations[f"{agent_id}_{i}"] = allocation

        return AgentDecision(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            action="distributed",
            confidence=0.75,
            reasoning=f"任务分发至 {len(allocations)} 个Agent",
            evidence=[
                {"source": "distribution",
                 "allocations": [{"agent": a.agent_id, "task": a.task[:30]} for a in allocations]}
            ]
        )

    async def _resolve_conflict(self, task: str, context: Dict[str, Any]) -> AgentDecision:
        """解决冲突"""
        conflicting_agents = context.get("conflicting_agents", [])
        conflict_type = context.get("conflict_type", "resource")

        resolution = "sequential"
        if conflict_type == "resource":
            resolution = "priority_based"
        elif conflict_type == "opinion":
            resolution = "consensus"
        elif conflict_type == "timing":
            resolution = "scheduling"

        return AgentDecision(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            action=f"conflict_resolved_{resolution}",
            confidence=0.7,
            reasoning=f"冲突解决: 类型={conflict_type}, 策略={resolution}",
            evidence=[
                {"source": "conflict", "type": conflict_type,
                 "agents": conflicting_agents},
                {"source": "resolution", "strategy": resolution}
            ]
        )

    async def _get_allocation_status(self, content: Dict[str, Any]) -> AgentDecision:
        """获取分配状态"""
        return AgentDecision(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            action="allocation_status",
            confidence=0.95,
            reasoning="当前分配状态",
            evidence=[
                {"source": "active_allocations", "count": len(self._active_allocations)},
                {"source": "managed_agents", "count": len(self._managed_agents)}
            ],
            metadata={
                "active_allocations": len(self._active_allocations),
                "managed_agents": len(self._managed_agents)
            }
        )

    def _find_available_agents(self) -> List[str]:
        """查找可用Agent"""
        available = []
        for agent_id, info in self._managed_agents.items():
            if info["current_load"] < self._max_concurrent_per_agent:
                available.append(agent_id)
        return available

    def _find_agents_by_type(self, agent_type: AgentType) -> List[str]:
        """按类型查找Agent"""
        return [
            aid for aid, info in self._managed_agents.items()
            if info["type"] == agent_type and info["current_load"] < self._max_concurrent_per_agent
        ]

    def _select_best_agent(self, candidates: List[str], task: str,
                           context: Dict[str, Any]) -> str:
        """选择最佳Agent"""
        if len(candidates) == 1:
            return candidates[0]

        scores = {}
        for agent_id in candidates:
            info = self._managed_agents[agent_id]
            score = 1.0 - (info["current_load"] / self._max_concurrent_per_agent)

            success_rate = info["successful_tasks"] / max(info["total_tasks"], 1)
            score += success_rate * 0.5

            agent_caps = info.get("capabilities", [])
            task_lower = task.lower()
            for cap in agent_caps:
                if cap.lower() in task_lower:
                    score += 0.3

            scores[agent_id] = score

        return max(scores, key=scores.get)

    def release_agent(self, agent_id: str, success: bool = True):
        """释放Agent"""
        if agent_id in self._managed_agents:
            info = self._managed_agents[agent_id]
            info["current_load"] = max(0, info["current_load"] - 1)
            info["total_tasks"] += 1
            if success:
                info["successful_tasks"] += 1
            if info["current_load"] == 0:
                info["state"] = AgentState.IDLE

        self._active_allocations.pop(agent_id, None)

    def get_coordination_stats(self) -> Dict[str, Any]:
        """获取协调统计"""
        return {
            "managed_agents": len(self._managed_agents),
            "active_allocations": len(self._active_allocations),
            "coordination_history": len(self._coordination_history),
            "agents": {
                aid: {
                    "type": info["type"].value,
                    "load": info["current_load"],
                    "total_tasks": info["total_tasks"],
                    "success_rate": info["successful_tasks"] / max(info["total_tasks"], 1)
                }
                for aid, info in self._managed_agents.items()
            }
        }
