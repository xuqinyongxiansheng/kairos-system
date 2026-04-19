#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鸿蒙小雨核心定义统一加载器
Single Source of Truth (SSOT) - 所有核心定义的唯一来源

功能：
1. 从YAML文件加载声明式核心定义
2. 提供统一的人物角色系统
3. 管理所有初始化配置
4. 验证核心定义的完整性

警告：
禁止在其他文件中硬编码核心定义！
所有角色、配置必须通过此类加载。
"""

import os
import yaml
import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from threading import Lock

logger = logging.getLogger("CoreDefinition")


@dataclass
class CharacterDefinition:
    """人物定义"""
    name: str
    displayName: str
    role: str
    personality: List[str] = field(default_factory=list)
    background: str = ""
    abilities: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    speakingStyle: str = ""
    values: List[str] = field(default_factory=list)
    default: bool = False


@dataclass
class AgentDefinition:
    """Agent定义"""
    name: str
    type: str
    description: str
    priority: int = 5
    responsibilities: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class SystemIdentity:
    """系统身份"""
    name: str
    shortName: str
    version: str
    description: str
    fullName: str = ""
    archetype: str = ""
    origin: str = ""
    purpose: str = ""
    personality: Dict[str, Any] = field(default_factory=dict)
    coreDirectives: List[str] = field(default_factory=list)
    behavioralPrinciples: List[str] = field(default_factory=list)
    creator: Dict[str, str] = field(default_factory=dict)
    emotionalBaseline: str = ""


class CoreDefinitionLoader:
    """
    核心定义统一加载器

    设计原则：
    1. SSOT - 单一真相来源
    2. 声明式配置 - YAML格式
    3. 延迟加载 - 优化启动性能
    4. 线程安全 - 多线程环境安全
    """

    _instance: Optional['CoreDefinitionLoader'] = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._yaml_path = self._find_yaml_path()
        self._raw_config: Dict[str, Any] = {}
        self._system_identity: Optional[SystemIdentity] = None
        self._characters: Dict[str, CharacterDefinition] = {}
        self._agents: Dict[str, AgentDefinition] = {}
        self._last_modified: float = 0
        self._loaded: bool = False
        self._initialized = True

        logger.info(f"核心定义加载器初始化完成，配置路径: {self._yaml_path}")

    def _find_yaml_path(self) -> str:
        """查找YAML配置文件"""
        search_paths = [
            os.path.join(os.path.dirname(__file__), "core_definition.yaml"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "system", "core_definition.yaml"),
            os.path.join(os.getcwd(), "system", "core_definition.yaml"),
        ]

        for path in search_paths:
            if os.path.exists(path):
                logger.info(f"找到核心定义文件: {path}")
                return path

        logger.warning("未找到核心定义文件，使用默认配置")
        return search_paths[0]

    def load(self, force_reload: bool = False) -> bool:
        """
        加载核心定义

        Args:
            force_reload: 是否强制重新加载

        Returns:
            加载是否成功
        """
        if not force_reload and self._raw_config:
            return True

        try:
            yaml_path = Path(self._yaml_path)
            if not yaml_path.exists():
                logger.error(f"核心定义文件不存在: {self._yaml_path}")
                return False

            current_mtime = os.path.getmtime(self._yaml_path)
            if not force_reload and current_mtime == self._last_modified:
                return True

            with open(self._yaml_path, 'r', encoding='utf-8') as f:
                content = f.read()

            documents = list(yaml.safe_load_all(content))
            self._raw_config = self._merge_documents(documents)
            self._parse_definitions()
            self._last_modified = current_mtime
            self._loaded = True

            logger.info(f"核心定义加载成功，共 {len(self._characters)} 个人物，{len(self._agents)} 个Agent")
            return True

        except Exception as e:
            logger.error(f"加载核心定义失败: {e}")
            self._loaded = False
            return False
    
    @property
    def loaded(self) -> bool:
        """返回是否已加载"""
        return self._loaded

    def _merge_documents(self, documents: List[Dict]) -> Dict[str, Any]:
        """合并多个YAML文档"""
        merged = {
            "metadata": {},
            "characters": {},
            "agents": {},
            "identity": {}
        }

        for doc in documents:
            if not doc:
                continue

            kind = doc.get('kind', '')
            spec = doc.get('spec', {})
            metadata = doc.get('metadata', {})

            if kind == 'SystemDefinition':
                merged["metadata"] = metadata

            elif kind == 'Identity':
                merged["identity"] = spec

            elif kind == 'CharacterDefinition':
                for char in spec.get('characters', []):
                    char_name = char.get('name', '')
                    if char_name:
                        merged["characters"][char_name] = char

            elif kind == 'AgentDefinition':
                for agent in spec.get('agents', []):
                    agent_name = agent.get('name', '')
                    if agent_name:
                        merged["agents"][agent_name] = agent

        return merged

    def _parse_definitions(self):
        """解析定义到数据结构"""
        identity_spec = self._raw_config.get('identity', {})

        self._system_identity = SystemIdentity(
            name=identity_spec.get('name', '鸿蒙小雨'),
            shortName=identity_spec.get('shortName', 'HMYX'),
            version=identity_spec.get('version', '2.0.0'),
            description=identity_spec.get('description', ''),
            fullName=identity_spec.get('fullName', ''),
            archetype=identity_spec.get('archetype', ''),
            origin=identity_spec.get('origin', ''),
            purpose=identity_spec.get('purpose', ''),
            personality=identity_spec.get('personality', {}),
            coreDirectives=identity_spec.get('coreDirectives', []),
            behavioralPrinciples=identity_spec.get('behavioralPrinciples', []),
            creator=identity_spec.get('creator', {}),
            emotionalBaseline=identity_spec.get('emotionalBaseline', '') or identity_spec.get('personality', {}).get('emotionalBaseline', '')
        )

        self._characters.clear()
        for char_name, char_data in self._raw_config.get('characters', {}).items():
            self._characters[char_name] = CharacterDefinition(
                name=char_data.get('name', char_name),
                displayName=char_data.get('displayName', ''),
                role=char_data.get('role', ''),
                personality=char_data.get('personality', []),
                background=char_data.get('background', ''),
                abilities=char_data.get('abilities', []),
                limitations=char_data.get('limitations', []),
                speakingStyle=char_data.get('speakingStyle', ''),
                values=char_data.get('values', []),
                default=char_data.get('default', False)
            )

        self._agents.clear()
        for agent_name, agent_data in self._raw_config.get('agents', {}).items():
            self._agents[agent_name] = AgentDefinition(
                name=agent_data.get('name', agent_name),
                type=agent_data.get('type', ''),
                description=agent_data.get('description', ''),
                priority=agent_data.get('priority', 5),
                responsibilities=agent_data.get('responsibilities', []),
                capabilities=agent_data.get('capabilities', []),
                dependencies=agent_data.get('dependencies', []),
                enabled=agent_data.get('enabled', True)
            )

    def get_system_identity(self) -> SystemIdentity:
        """获取系统身份"""
        if not self._raw_config:
            self.load()
        return self._system_identity

    def get_character(self, name: str) -> Optional[CharacterDefinition]:
        """获取人物定义"""
        if not self._raw_config:
            self.load()
        return self._characters.get(name)

    def get_default_character(self) -> Optional[CharacterDefinition]:
        """获取默认人物"""
        if not self._raw_config:
            self.load()
        for char in self._characters.values():
            if char.default:
                return char
        return None

    def get_all_characters(self) -> Dict[str, CharacterDefinition]:
        """获取所有人物"""
        if not self._raw_config:
            self.load()
        return dict(self._characters)

    def get_agent(self, name: str) -> Optional[AgentDefinition]:
        """获取Agent定义"""
        if not self._raw_config:
            self.load()
        return self._agents.get(name)

    def get_all_agents(self) -> Dict[str, AgentDefinition]:
        """获取所有Agent"""
        if not self._raw_config:
            self.load()
        return dict(self._agents)

    def get_agents_by_priority(self, min_priority: int = 1) -> List[AgentDefinition]:
        """按优先级获取Agent"""
        if not self._raw_config:
            self.load()
        return [a for a in self._agents.values() if a.priority <= min_priority and a.enabled]

    def validate(self) -> List[str]:
        """验证核心定义的完整性"""
        errors = []

        if not self._system_identity:
            errors.append("系统身份未定义")
        else:
            if not self._system_identity.name:
                errors.append("系统名称为空")
            if not self._system_identity.version:
                errors.append("系统版本为空")

        if not self._characters:
            errors.append("未定义任何人物")
        else:
            has_default = any(c.default for c in self._characters.values())
            if not has_default:
                errors.append("没有默认人物")

        if not self._agents:
            errors.append("未定义任何Agent")

        for agent in self._agents.values():
            for dep in agent.dependencies:
                if dep not in self._agents:
                    errors.append(f"Agent {agent.name} 依赖 {dep} 不存在")

        if errors:
            logger.error(f"核心定义验证失败: {errors}")

        return errors

    def get_initialization_status(self) -> Dict[str, Any]:
        """获取初始化状态"""
        return {
            "yaml_path": self._yaml_path,
            "yaml_exists": os.path.exists(self._yaml_path),
            "loaded": bool(self._raw_config),
            "character_count": len(self._characters),
            "agent_count": len(self._agents),
            "validation_errors": self.validate(),
            "system_identity": {
                "name": self._system_identity.name if self._system_identity else None,
                "version": self._system_identity.version if self._system_identity else None
            } if self._system_identity else None,
            "default_character": self.get_default_character().name if self.get_default_character() else None
        }

    def reload(self):
        """重新加载配置"""
        self._raw_config = {}
        self.load(force_reload=True)


_loader: Optional[CoreDefinitionLoader] = None


def get_core_loader() -> CoreDefinitionLoader:
    """获取核心定义加载器单例"""
    global _loader
    if _loader is None:
        _loader = CoreDefinitionLoader()
        _loader.load()
    return _loader


def get_system_identity() -> SystemIdentity:
    """获取系统身份便捷函数"""
    return get_core_loader().get_system_identity()


def get_character(name: str) -> Optional[CharacterDefinition]:
    """获取人物便捷函数"""
    return get_core_loader().get_character(name)


def get_default_character() -> Optional[CharacterDefinition]:
    """获取默认人物便捷函数"""
    return get_core_loader().get_default_character()


def get_all_characters() -> Dict[str, CharacterDefinition]:
    """获取所有人物便捷函数"""
    return get_core_loader().get_all_characters()


def get_agent(name: str) -> Optional[AgentDefinition]:
    """获取Agent便捷函数"""
    return get_core_loader().get_agent(name)


def get_all_agents() -> Dict[str, AgentDefinition]:
    """获取所有Agent便捷函数"""
    return get_core_loader().get_all_agents()


def get_initialization_status() -> Dict[str, Any]:
    """获取初始化状态便捷函数"""
    return get_core_loader().get_initialization_status()


def validate_core_definitions() -> List[str]:
    """验证核心定义"""
    return get_core_loader().validate()
