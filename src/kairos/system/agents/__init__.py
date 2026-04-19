# -*- coding: utf-8 -*-
"""
Agent类型系统模块
受Neuron AI Framework启发，实现四种特化Agent类型:
- ReflexAgent: 快速模式匹配，高置信度触发
- DeliberativeAgent: 深度推理，低置信度触发
- LearningAgent: 学习适应，模式识别/策略进化
- CoordinatorAgent: 协调编排，资源分配/优先级管理
"""

from .base_neuron_agent import (
    BaseNeuronAgent,
    AgentCapability,
    AgentDecision
)
from .reflex_agent import ReflexAgent
from .deliberative_agent import DeliberativeAgent
from .learning_agent import LearningAgent
from .coordinator_agent import CoordinatorAgent
from .agent_factory import AgentFactory, agent_factory

__all__ = [
    'BaseNeuronAgent',
    'AgentCapability',
    'AgentDecision',
    'ReflexAgent',
    'DeliberativeAgent',
    'LearningAgent',
    'CoordinatorAgent',
    'AgentFactory',
    'agent_factory'
]
