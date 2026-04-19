"""
系统核心配置文件
定义项目的核心设定、人物设定、Agent 角色设定
确保大模型调用的准确性和一致性

核心定义来源: system/core_definition.yaml (声明式)
加载器: system/unified_initializer.py (SSOT)
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import os
import logging

def _get_version() -> str:
    try:
        from kairos.version import VERSION
        return VERSION
    except ImportError:
        return "4.0.0"
from datetime import datetime

logger = logging.getLogger("CoreConfig")


class SystemRole(Enum):
    """系统角色枚举"""
    ASSISTANT = "assistant"
    DEVELOPER = "developer"
    ANALYST = "analyst"
    LEARNER = "learner"
    COMPANION = "companion"


class ModelType(Enum):
    """模型类型枚举"""
    QWEN25_3B = "qwen2.5:3b-instruct-q4_K_M"
    GEMMA4_4B = "gemma4:4b"
    GEMMA4_12B = "gemma4:12b"
    GEMMA4_E4B = "gemma4:e4b"


@dataclass
class CharacterSetting:
    """人物设定数据类"""
    name: str
    role: str
    personality: List[str]
    background: str
    abilities: List[str]
    limitations: List[str]
    speaking_style: str
    values: List[str]


@dataclass
class AgentRoleConfig:
    """Agent 角色配置数据类"""
    agent_name: str
    agent_type: str
    description: str
    responsibilities: List[str]
    capabilities: List[str]
    limitations: List[str]
    priority: int
    dependencies: List[str] = field(default_factory=list)


@dataclass
class SystemConfig:
    """系统配置数据类"""
    version: str
    model_name: str
    model_type: str
    system_name: str
    system_role: str
    created_at: str
    updated_at: str


def _load_characters_from_yaml() -> Dict[str, CharacterSetting]:
    """从统一加载器加载人物设定"""
    try:
        from kairos.system.unified_initializer import get_all_characters
        characters = get_all_characters()
        result = {}
        for name, char in characters.items():
            personality = char.personality if isinstance(char.personality, list) else [char.personality]
            result[name] = CharacterSetting(
                name=char.displayName or char.name,
                role=char.role,
                personality=personality,
                background=char.background,
                abilities=char.abilities,
                limitations=char.limitations,
                speaking_style=char.speakingStyle,
                values=char.values
            )
        return result
    except Exception as e:
        logger.warning(f"从统一加载器加载人物设定失败: {e}")
        return {}


def _load_agents_from_yaml() -> Dict[str, AgentRoleConfig]:
    """从统一加载器加载Agent配置"""
    try:
        from kairos.system.unified_initializer import get_all_agents
        agents = get_all_agents()
        result = {}
        for name, agent in agents.items():
            result[name] = AgentRoleConfig(
                agent_name=agent.name,
                agent_type=agent.type,
                description=agent.description,
                responsibilities=agent.responsibilities,
                capabilities=agent.capabilities,
                limitations=[],
                priority=agent.priority,
                dependencies=agent.dependencies
            )
        return result
    except Exception as e:
        logger.warning(f"从统一加载器加载Agent配置失败: {e}")
        return {}


def _load_system_config_from_yaml() -> SystemConfig:
    """从统一加载器加载系统配置"""
    try:
        from kairos.system.unified_initializer import get_system_identity
        identity = get_system_identity()
        return SystemConfig(
            version=identity.version,
            model_name="Gemma4",
            model_type=ModelType.GEMMA4_E4B.value,
            system_name=identity.fullName or identity.name,
            system_role=SystemRole.ASSISTANT.value,
            created_at="2024-01-01T00:00:00",
            updated_at=datetime.now().isoformat()
        )
    except Exception as e:
        logger.warning(f"从统一加载器加载系统配置失败: {e}")
        return SystemConfig(
            version=_get_version(),
            model_name="Gemma4",
            model_type=ModelType.GEMMA4_E4B.value,
            system_name="鸿蒙小雨",
            system_role=SystemRole.ASSISTANT.value,
            created_at="2024-01-01T00:00:00",
            updated_at=datetime.now().isoformat()
        )


SYSTEM_CONFIG = _load_system_config_from_yaml()

CHARACTER_SETTINGS = _load_characters_from_yaml()

AGENT_ROLE_CONFIGS = _load_agents_from_yaml()

VALIDATION_RULES = {
    "character": {
        "required_fields": ["name", "role", "personality", "background"],
        "personality_min_count": 3,
        "abilities_max_count": 10
    },
    "agent": {
        "required_fields": ["agent_name", "agent_type", "description", "responsibilities"],
        "responsibilities_min_count": 1,
        "priority_range": (1, 10)
    },
    "system": {
        "required_fields": ["version", "model_name", "system_name"],
        "version_format": r"^\d+\.\d+\.\d+$"
    }
}

CONFLICT_RULES = {
    "agent_overlap": {
        "description": "检测 Agent 职责重叠",
        "threshold": 0.3
    },
    "priority_conflict": {
        "description": "检测优先级冲突",
        "same_priority_warning": True
    },
    "dependency_cycle": {
        "description": "检测依赖循环",
        "enabled": True
    },
    "capability_conflict": {
        "description": "检测能力冲突",
        "check_enabled": True
    }
}


def get_character_setting(role: str) -> CharacterSetting:
    """获取人物设定"""
    return CHARACTER_SETTINGS.get(role, CHARACTER_SETTINGS["main_assistant"])


def get_agent_config(agent_name: str) -> AgentRoleConfig:
    """获取 Agent 配置"""
    return AGENT_ROLE_CONFIGS.get(agent_name)


def get_system_config() -> SystemConfig:
    """获取系统配置"""
    return SYSTEM_CONFIG


def validate_character_setting(character: CharacterSetting) -> Dict[str, Any]:
    """验证人物设定"""
    errors = []
    warnings = []
    
    rules = VALIDATION_RULES["character"]
    
    # 检查必填字段
    for field in rules["required_fields"]:
        if not getattr(character, field, None):
            errors.append(f"缺少必填字段: {field}")
    
    # 检查性格特征数量
    if len(character.personality) < rules["personality_min_count"]:
        warnings.append(f"性格特征数量不足 ({len(character.personality)} < {rules['personality_min_count']})")
    
    # 检查能力数量
    if len(character.abilities) > rules["abilities_max_count"]:
        warnings.append(f"能力数量过多 ({len(character.abilities)} > {rules['abilities_max_count']})")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_agent_config(agent: AgentRoleConfig) -> Dict[str, Any]:
    """验证 Agent 配置"""
    errors = []
    warnings = []
    
    rules = VALIDATION_RULES["agent"]
    
    # 检查必填字段
    for field in rules["required_fields"]:
        if not getattr(agent, field, None):
            errors.append(f"缺少必填字段: {field}")
    
    # 检查职责数量
    if len(agent.responsibilities) < rules["responsibilities_min_count"]:
        errors.append(f"职责数量不足 ({len(agent.responsibilities)} < {rules['responsibilities_min_count']})")
    
    # 检查优先级范围
    min_pri, max_pri = rules["priority_range"]
    if not (min_pri <= agent.priority <= max_pri):
        errors.append(f"优先级超出范围 ({agent.priority} 不在 [{min_pri}, {max_pri}])")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def detect_agent_conflicts() -> List[Dict[str, Any]]:
    """检测 Agent 冲突"""
    conflicts = []
    
    # 检测优先级冲突
    priority_map = {}
    for name, config in AGENT_ROLE_CONFIGS.items():
        pri = config.priority
        if pri in priority_map:
            conflicts.append({
                "type": "priority_conflict",
                "agents": [priority_map[pri], name],
                "message": f"优先级冲突: {priority_map[pri]} 和 {name} 都有优先级 {pri}"
            })
        else:
            priority_map[pri] = name
    
    # 检测依赖循环
    def has_cycle(agent_name, visited=None):
        if visited is None:
            visited = set()
        
        if agent_name in visited:
            return True
        
        visited.add(agent_name)
        config = AGENT_ROLE_CONFIGS.get(agent_name)
        
        if config:
            for dep in config.dependencies:
                if has_cycle(dep, visited.copy()):
                    return True
        
        return False
    
    for name in AGENT_ROLE_CONFIGS:
        if has_cycle(name):
            conflicts.append({
                "type": "dependency_cycle",
                "agent": name,
                "message": f"检测到依赖循环: {name}"
            })
    
    return conflicts


def export_config(output_path: str):
    """导出配置到文件"""
    config_data = {
        "system": {
            "version": SYSTEM_CONFIG.version,
            "model_name": SYSTEM_CONFIG.model_name,
            "model_type": SYSTEM_CONFIG.model_type,
            "system_name": SYSTEM_CONFIG.system_name,
            "system_role": SYSTEM_CONFIG.system_role,
            "exported_at": datetime.now().isoformat()
        },
        "characters": {
            name: {
                "name": char.name,
                "role": char.role,
                "personality": char.personality,
                "background": char.background,
                "abilities": char.abilities,
                "limitations": char.limitations,
                "speaking_style": char.speaking_style,
                "values": char.values
            }
            for name, char in CHARACTER_SETTINGS.items()
        },
        "agents": {
            name: {
                "agent_name": agent.agent_name,
                "agent_type": agent.agent_type,
                "description": agent.description,
                "responsibilities": agent.responsibilities,
                "capabilities": agent.capabilities,
                "limitations": agent.limitations,
                "priority": agent.priority,
                "dependencies": agent.dependencies
            }
            for name, agent in AGENT_ROLE_CONFIGS.items()
        }
    }
    
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)
    
    return output_path
