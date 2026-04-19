# -*- coding: utf-8 -*-
"""
插件化架构 (Plugin Architecture)
源自Hermes Agent插件系统设计

核心设计:
- ABC抽象基类定义接口契约
- 注册表模式管理插件实例
- 配置驱动选择活跃插件
- 三种发现源: 用户目录/项目目录/pip入口点
- 单选插件: 记忆提供者/上下文引擎同时只能激活一个
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type
from dataclasses import dataclass, field

logger = logging.getLogger("PluginArchitecture")


class PluginType:
    MEMORY_PROVIDER = "memory_provider"
    CONTEXT_ENGINE = "context_engine"
    TOOL = "tool"
    HOOK = "hook"
    SKILL = "skill"


class BasePlugin(ABC):
    """插件基类"""

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def get_type(self) -> str:
        pass

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def shutdown(self):
        pass

    def get_description(self) -> str:
        return ""

    def get_version(self) -> str:
        return "1.0.0"


class MemoryProviderPlugin(BasePlugin):
    """记忆提供者插件接口"""

    @abstractmethod
    def prefetch(self, query: str, session_id: str = "") -> str:
        pass

    @abstractmethod
    def sync_turn(self, user_content: str, assistant_content: str, session_id: str = ""):
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_context(self, session_id: str = "") -> str:
        pass


class ContextEnginePlugin(BasePlugin):
    """上下文引擎插件接口"""

    @abstractmethod
    def should_compress(self, messages: List[Dict[str, Any]],
                        context_length: int) -> bool:
        pass

    @abstractmethod
    def compress(self, messages: List[Dict[str, Any]],
                 context_length: int) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_summary(self, messages: List[Dict[str, Any]]) -> str:
        pass


class PluginRegistry:
    """
    插件注册表
    
    用法:
    1. register_plugin_class() 注册插件类
    2. activate_plugin() 激活插件实例
    3. get_active() 获取活跃插件
    4. list_available() 列出可用插件
    """

    SINGLE_SELECT_TYPES = {PluginType.MEMORY_PROVIDER, PluginType.CONTEXT_ENGINE}

    def __init__(self):
        self._classes: Dict[str, Dict[str, Type[BasePlugin]]] = {}
        self._instances: Dict[str, Dict[str, BasePlugin]] = {}
        self._active: Dict[str, Optional[str]] = {}

    def register_plugin_class(self, plugin_type: str, name: str,
                              plugin_class: Type[BasePlugin]):
        if plugin_type not in self._classes:
            self._classes[plugin_type] = {}
        self._classes[plugin_type][name] = plugin_class
        logger.info("插件类已注册: %s/%s", plugin_type, name)

    def activate_plugin(self, plugin_type: str, name: str,
                        config: Dict[str, Any] = None) -> bool:
        if plugin_type not in self._classes or name not in self._classes[plugin_type]:
            logger.error("插件未注册: %s/%s", plugin_type, name)
            return False

        if plugin_type in self.SINGLE_SELECT_TYPES:
            if plugin_type in self._active and self._active[plugin_type]:
                old_name = self._active[plugin_type]
                if old_name in self._instances.get(plugin_type, {}):
                    try:
                        self._instances[plugin_type][old_name].shutdown()
                    except Exception:
                        pass

        cls = self._classes[plugin_type][name]
        instance = cls()

        try:
            if not instance.initialize(config or {}):
                logger.error("插件初始化失败: %s/%s", plugin_type, name)
                return False
        except Exception as e:
            logger.error("插件初始化异常: %s/%s - %s", plugin_type, name, e)
            return False

        if plugin_type not in self._instances:
            self._instances[plugin_type] = {}
        self._instances[plugin_type][name] = instance
        self._active[plugin_type] = name

        logger.info("插件已激活: %s/%s", plugin_type, name)
        return True

    def deactivate_plugin(self, plugin_type: str, name: str = None):
        target = name or self._active.get(plugin_type)
        if not target:
            return

        if plugin_type in self._instances and target in self._instances[plugin_type]:
            try:
                self._instances[plugin_type][target].shutdown()
            except Exception:
                pass
            del self._instances[plugin_type][target]

        if self._active.get(plugin_type) == target:
            self._active[plugin_type] = None

    def get_active(self, plugin_type: str) -> Optional[BasePlugin]:
        name = self._active.get(plugin_type)
        if not name:
            return None
        return self._instances.get(plugin_type, {}).get(name)

    def get_active_name(self, plugin_type: str) -> Optional[str]:
        return self._active.get(plugin_type)

    def list_available(self, plugin_type: str = None) -> Dict[str, List[str]]:
        if plugin_type:
            return {plugin_type: list(self._classes.get(plugin_type, {}).keys())}
        return {pt: list(classes.keys()) for pt, classes in self._classes.items()}

    def list_active(self) -> Dict[str, Optional[str]]:
        return dict(self._active)

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "registered_types": list(self._classes.keys()),
            "registered_count": sum(len(v) for v in self._classes.values()),
            "active_plugins": dict(self._active),
            "single_select_types": list(self.SINGLE_SELECT_TYPES)
        }


_registry: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


def register_plugin(plugin_type: str):
    """装饰器: 注册插件类"""
    def decorator(cls):
        name = cls.__name__
        get_plugin_registry().register_plugin_class(plugin_type, name, cls)
        return cls
    return decorator
