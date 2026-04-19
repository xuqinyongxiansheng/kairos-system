# -*- coding: utf-8 -*-
"""
Agent工厂
负责创建和管理所有特化Agent实例
提供统一的Agent生命周期管理
"""

import logging
from typing import Dict, Any, List, Optional

from .base_neuron_agent import BaseNeuronAgent
from .reflex_agent import ReflexAgent
from .deliberative_agent import DeliberativeAgent
from .learning_agent import LearningAgent
from .coordinator_agent import CoordinatorAgent
from ..core.enums import AgentType, AgentState

logger = logging.getLogger("AgentFactory")


class AgentFactory:
    """
    Agent工厂
    
    功能:
    - 创建特化Agent实例
    - 管理Agent生命周期
    - 提供Agent发现
    - 统一Agent注册
    """

    def __init__(self):
        self._agents: Dict[str, BaseNeuronAgent] = {}
        self._type_registry: Dict[AgentType, type] = {
            AgentType.REFLEX: ReflexAgent,
            AgentType.DELIBERATIVE: DeliberativeAgent,
            AgentType.LEARNING: LearningAgent,
            AgentType.COORDINATOR: CoordinatorAgent,
        }

        self._create_default_agents()
        logger.info("Agent工厂初始化")

    def _create_default_agents(self):
        """创建默认Agent实例"""
        self._agents["reflex_agent"] = ReflexAgent()
        self._agents["deliberative_agent"] = DeliberativeAgent()
        self._agents["learning_agent"] = LearningAgent()
        self._agents["coordinator_agent"] = CoordinatorAgent()

        coordinator = self._agents["coordinator_agent"]
        if isinstance(coordinator, CoordinatorAgent):
            for agent_id, agent in self._agents.items():
                if agent_id != "coordinator_agent":
                    coordinator.register_agent(
                        agent_id=agent_id,
                        agent_type=agent.agent_type,
                        capabilities=[c.name for c in agent.capabilities]
                    )

    def create_agent(self, agent_type: AgentType, agent_id: str = None,
                    **kwargs) -> BaseNeuronAgent:
        """
        创建Agent
        
        Args:
            agent_type: Agent类型
            agent_id: 自定义ID
            **kwargs: 额外参数
            
        Returns:
            Agent实例
        """
        if agent_type not in self._type_registry:
            raise ValueError(f"未知Agent类型: {agent_type}")

        agent_cls = self._type_registry[agent_type]
        agent_id = agent_id or f"{agent_type.value}_agent_{len(self._agents)}"

        agent = agent_cls(agent_id=agent_id, **kwargs)
        self._agents[agent_id] = agent

        logger.info(f"创建Agent: {agent_id} (类型: {agent_type.value})")
        return agent

    def get_agent(self, agent_id: str) -> Optional[BaseNeuronAgent]:
        """获取Agent"""
        return self._agents.get(agent_id)

    def get_agents_by_type(self, agent_type: AgentType) -> List[BaseNeuronAgent]:
        """按类型获取Agent"""
        return [a for a in self._agents.values() if a.agent_type == agent_type]

    def get_reflex_agent(self) -> ReflexAgent:
        """获取反射Agent"""
        agents = self.get_agents_by_type(AgentType.REFLEX)
        return agents[0] if agents else self.create_agent(AgentType.REFLEX)

    def get_deliberative_agent(self) -> DeliberativeAgent:
        """获取审议Agent"""
        agents = self.get_agents_by_type(AgentType.DELIBERATIVE)
        return agents[0] if agents else self.create_agent(AgentType.DELIBERATIVE)

    def get_learning_agent(self) -> LearningAgent:
        """获取学习Agent"""
        agents = self.get_agents_by_type(AgentType.LEARNING)
        return agents[0] if agents else self.create_agent(AgentType.LEARNING)

    def get_coordinator_agent(self) -> CoordinatorAgent:
        """获取协调Agent"""
        agents = self.get_agents_by_type(AgentType.COORDINATOR)
        return agents[0] if agents else self.create_agent(AgentType.COORDINATOR)

    def select_agent(self, task: str, confidence: float = 0.5) -> BaseNeuronAgent:
        """
        基于置信度自动选择Agent
        
        Args:
            task: 任务描述
            confidence: 置信度
            
        Returns:
            最合适的Agent
        """
        if confidence > 0.8:
            reflex = self.get_reflex_agent()
            if reflex.can_handle(task, confidence):
                return reflex

        if confidence < 0.3:
            deliberative = self.get_deliberative_agent()
            if deliberative.can_handle(task, confidence):
                return deliberative

        learning = self.get_learning_agent()
        if learning.can_handle(task, confidence):
            return learning

        for agent_type in [AgentType.REFLEX, AgentType.DELIBERATIVE, AgentType.LEARNING]:
            agents = self.get_agents_by_type(agent_type)
            for agent in agents:
                if agent.can_handle(task, confidence):
                    return agent

        return self.get_deliberative_agent()

    def remove_agent(self, agent_id: str) -> bool:
        """移除Agent"""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"移除Agent: {agent_id}")
            return True
        return False

    def get_all_agents_info(self) -> Dict[str, Any]:
        """获取所有Agent信息"""
        return {
            "total_agents": len(self._agents),
            "by_type": {
                t.value: len(self.get_agents_by_type(t))
                for t in AgentType
            },
            "agents": {
                aid: agent.get_info()
                for aid, agent in self._agents.items()
            }
        }

    def get_factory_stats(self) -> Dict[str, Any]:
        """获取工厂统计"""
        return {
            "total_agents": len(self._agents),
            "by_type": {
                t.value: len(self.get_agents_by_type(t))
                for t in AgentType
            },
            "by_state": {
                s.value: sum(1 for a in self._agents.values() if a.state == s)
                for s in AgentState
            }
        }


agent_factory = AgentFactory()


def get_agent_factory() -> AgentFactory:
    """获取全局Agent工厂"""
    return agent_factory
