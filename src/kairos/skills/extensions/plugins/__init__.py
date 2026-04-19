#!/usr/bin/env python3
"""
插件系统模块
"""

from .plugin_manager import Plugin, PluginManager, get_plugin_manager

__all__ = [
    'Plugin',
    'PluginManager',
    'get_plugin_manager'
]