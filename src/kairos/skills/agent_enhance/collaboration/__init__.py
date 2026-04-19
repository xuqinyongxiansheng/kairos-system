#!/usr/bin/env python3
"""
协作模块
"""

from .coordinator import (
    TaskAssignment,
    CollaborationResult,
    CollaborationCoordinator,
    get_collaboration_coordinator
)
from .workflow import (
    WorkflowNode,
    Workflow,
    WorkflowInstance,
    WorkflowEngine,
    get_workflow_engine
)

__all__ = [
    'TaskAssignment',
    'CollaborationResult',
    'CollaborationCoordinator',
    'get_collaboration_coordinator',
    'WorkflowNode',
    'Workflow',
    'WorkflowInstance',
    'WorkflowEngine',
    'get_workflow_engine'
]