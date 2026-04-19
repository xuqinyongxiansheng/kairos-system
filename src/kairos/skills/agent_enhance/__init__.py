#!/usr/bin/env python3
"""
Agent能力增强模块
"""

from .professional_agents import (
    ProfessionalAgent,
    AgentMessage,
    AgentRegistry,
    get_agent_registry,
    CodeAgent,
    get_code_agent,
    DataAgent,
    get_data_agent,
    ContentAgent,
    get_content_agent
)
from .integrations import (
    get_agency_agent_adapter,
    get_minimax_skill_adapter,
    get_claude_mem_adapter
)
from .communication import (
    MessageType,
    MessagePriority,
    AgentMessage as CommAgentMessage,
    CommunicationProtocol,
    MessageValidator,
    CommunicationManager,
    get_communication_manager
)
from .collaboration import (
    TaskAssignment,
    CollaborationResult,
    CollaborationCoordinator,
    get_collaboration_coordinator,
    WorkflowNode,
    Workflow,
    WorkflowInstance,
    WorkflowEngine,
    get_workflow_engine
)
from .evaluation import (
    EvaluationMetrics,
    EvaluationMetric,
    EvaluationResult,
    AgentEvaluator,
    get_agent_evaluator
)

__all__ = [
    # Professional Agents
    'ProfessionalAgent',
    'AgentMessage',
    'AgentRegistry',
    'get_agent_registry',
    'CodeAgent',
    'get_code_agent',
    'DataAgent',
    'get_data_agent',
    'ContentAgent',
    'get_content_agent',
    # Communication
    'MessageType',
    'MessagePriority',
    'CommAgentMessage',
    'CommunicationProtocol',
    'MessageValidator',
    'CommunicationManager',
    'get_communication_manager',
    # Collaboration
    'TaskAssignment',
    'CollaborationResult',
    'CollaborationCoordinator',
    'get_collaboration_coordinator',
    'WorkflowNode',
    'Workflow',
    'WorkflowInstance',
    'WorkflowEngine',
    'get_workflow_engine',
    # Evaluation
    'EvaluationMetrics',
    'EvaluationMetric',
    'EvaluationResult',
    'AgentEvaluator',
    'get_agent_evaluator',
    # Integrations
    'get_agency_agent_adapter',
    'get_minimax_skill_adapter',
    'get_claude_mem_adapter'
]