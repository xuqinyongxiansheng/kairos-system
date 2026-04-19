# -*- coding: utf-8 -*-
"""
神经元Agent基类
为所有特化Agent提供统一接口和基础功能
集成突触总线通信、可观测性追踪、资源管理
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..core.enums import AgentType, AgentState, MessagePriority
from ..core.synaptic_bus import SynapticMessage, get_synaptic_bus

logger = logging.getLogger("BaseNeuronAgent")


@dataclass
class AgentCapability:
    """Agent能力描述"""
    name: str
    description: str
    confidence_threshold: float = 0.5
    avg_latency_ms: float = 0.0
    success_rate: float = 0.0
    invocation_count: int = 0


@dataclass
class AgentDecision:
    """Agent决策结果"""
    agent_id: str
    agent_type: AgentType
    action: str
    confidence: float
    reasoning: str
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    decision_id: str = field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:12]}")
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "decision_id": self.decision_id,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "action": self.action,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "alternatives": self.alternatives,
            "evidence": self.evidence,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "latency_ms": self.latency_ms
        }


class BaseNeuronAgent:
    """
    神经元Agent基类
    
    所有特化Agent继承此基类，提供:
    - 统一的消息处理接口
    - 突触总线集成
    - 能力注册与发现
    - 决策追踪
    - 性能统计
    """

    def __init__(self, agent_id: str, agent_type: AgentType,
                 capabilities: List[AgentCapability] = None):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.state = AgentState.IDLE
        self.capabilities = capabilities or []
        self._decision_history: List[AgentDecision] = []
        self._max_history = 1000
        self._stats = {
            "total_decisions": 0,
            "successful_decisions": 0,
            "failed_decisions": 0,
            "avg_confidence": 0.0,
            "avg_latency_ms": 0.0,
            "by_action": {}
        }
        self._pattern_cache: Dict[str, Any] = {}
        self._message_handlers: Dict[str, Callable] = {}

        self._register_with_bus()
        logger.info(f"Agent初始化: {agent_id} (类型: {agent_type.value})")

    def _register_with_bus(self):
        """注册到突触总线"""
        try:
            bus = get_synaptic_bus()
            bus.register_endpoint(
                endpoint_id=self.agent_id,
                handler=self.handle_message,
                agent_type=self.agent_type
            )
        except Exception as e:
            logger.warning(f"注册突触总线失败: {e}")

    async def handle_message(self, message: SynapticMessage) -> Any:
        """
        处理突触消息 (统一入口)
        
        Args:
            message: 突触消息
            
        Returns:
            处理结果
        """
        action = message.content.get("action", "process")
        handler = self._message_handlers.get(action, self.process)

        try:
            self.state = AgentState.PROCESSING
            result = await handler(message.content) if asyncio.iscoroutinefunction(handler) else handler(message.content)
            self.state = AgentState.IDLE
            return result
        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(f"Agent {self.agent_id} 处理消息失败: {e}")
            raise

    async def process(self, content: Dict[str, Any]) -> AgentDecision:
        """
        处理内容 (子类必须实现)
        
        Args:
            content: 消息内容
            
        Returns:
            决策结果
        """
        raise NotImplementedError("子类必须实现 process 方法")

    async def decide(self, task: str, context: Dict[str, Any] = None,
                    confidence: float = 0.5) -> AgentDecision:
        """
        做出决策
        
        Args:
            task: 任务描述
            context: 上下文
            confidence: 初始置信度
            
        Returns:
            决策结果
        """
        start_time = time.time()
        self.state = AgentState.PROCESSING

        try:
            content = {
                "action": "decide",
                "task": task,
                "context": context or {},
                "confidence": confidence
            }

            decision = await self.process(content)

            if not isinstance(decision, AgentDecision):
                decision = AgentDecision(
                    agent_id=self.agent_id,
                    agent_type=self.agent_type,
                    action=str(decision),
                    confidence=confidence,
                    reasoning="默认决策"
                )

            decision.latency_ms = (time.time() - start_time) * 1000
            self._record_decision(decision)
            self.state = AgentState.IDLE

            return decision

        except Exception as e:
            self.state = AgentState.ERROR
            decision = AgentDecision(
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                action="error",
                confidence=0.0,
                reasoning=f"决策失败: {e}"
            )
            decision.latency_ms = (time.time() - start_time) * 1000
            self._record_decision(decision)
            return decision

    def can_handle(self, task: str, confidence: float) -> bool:
        """
        判断是否能处理此任务
        
        Args:
            task: 任务描述
            confidence: 置信度
            
        Returns:
            是否能处理
        """
        return True

    def register_handler(self, action: str, handler: Callable):
        """注册消息处理器"""
        self._message_handlers[action] = handler

    def add_capability(self, capability: AgentCapability):
        """添加能力"""
        self.capabilities.append(capability)

    def _record_decision(self, decision: AgentDecision):
        """记录决策"""
        self._decision_history.append(decision)
        if len(self._decision_history) > self._max_history:
            self._decision_history = self._decision_history[-self._max_history:]

        self._stats["total_decisions"] += 1
        if decision.confidence > 0.5:
            self._stats["successful_decisions"] += 1
        else:
            self._stats["failed_decisions"] += 1

        total = self._stats["total_decisions"]
        self._stats["avg_confidence"] = (
            self._stats["avg_confidence"] * (total - 1) + decision.confidence
        ) / total
        self._stats["avg_latency_ms"] = (
            self._stats["avg_latency_ms"] * (total - 1) + decision.latency_ms
        ) / total

        action_key = decision.action[:30]
        self._stats["by_action"][action_key] = self._stats["by_action"].get(action_key, 0) + 1

    def get_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "state": self.state.value,
            "capabilities": [
                {
                    "name": c.name,
                    "description": c.description,
                    "confidence_threshold": c.confidence_threshold,
                    "success_rate": c.success_rate
                }
                for c in self.capabilities
            ],
            "stats": self.get_stats()
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_decisions": self._stats["total_decisions"],
            "successful_decisions": self._stats["successful_decisions"],
            "failed_decisions": self._stats["failed_decisions"],
            "avg_confidence": round(self._stats["avg_confidence"], 3),
            "avg_latency_ms": round(self._stats["avg_latency_ms"], 2),
            "by_action": dict(self._stats["by_action"])
        }

    def get_decision_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取决策历史"""
        return [d.to_dict() for d in self._decision_history[-limit:]]
