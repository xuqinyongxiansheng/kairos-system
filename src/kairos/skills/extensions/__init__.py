#!/usr/bin/env python3
"""
功能扩展模块
"""

from .i18n import I18nManager, get_i18n_manager, _
from .workflow import WorkflowNodeType, WorkflowNode, Workflow, WorkflowEditor, get_workflow_editor
from .plugins import Plugin, PluginManager, get_plugin_manager
from .claw import ClawSkillAdapter, get_claw_skill_adapter

__all__ = [
    # I18n
    'I18nManager',
    'get_i18n_manager',
    '_',
    # Workflow
    'WorkflowNodeType',
    'WorkflowNode',
    'Workflow',
    'WorkflowEditor',
    'get_workflow_editor',
    # Plugins
    'Plugin',
    'PluginManager',
    'get_plugin_manager',
    # Claw
    'ClawSkillAdapter',
    'get_claw_skill_adapter'
]