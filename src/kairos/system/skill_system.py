"""
技能系统兼容层

已迁移到 system/unified_skill_system.py
此文件保留以维持向后兼容性，所有调用自动委托到统一技能系统

使用方式（不变）：
    from kairos.system.skill_system import SkillSystem, SkillCategory
    system = SkillSystem()
    system.register_skill(name="test", function=fn, category=SkillCategory.AI)
"""

from kairos.system.unified_skill_system import (
    UnifiedSkillSystem,
    SkillCategory as UnifiedSkillCategory,
    SkillStatus,
    SkillMetadata as UnifiedSkillMetadata,
    get_unified_skill_system,
)

import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime

logger = logging.getLogger(__name__)

logger.info("skill_system.py 已委托到 unified_skill_system.py，向后兼容")


class SkillCategory:
    """技能分类（兼容旧版6类）"""
    GENERAL = "general"
    VOICE = "voice"
    WEB = "web"
    SYSTEM = "system"
    AI = "ai"
    TOOL = "tool"

    @staticmethod
    def to_unified(category: str) -> str:
        mapping = {
            "general": UnifiedSkillCategory.GENERAL.value,
            "voice": UnifiedSkillCategory.VOICE.value,
            "web": UnifiedSkillCategory.WEB.value,
            "system": UnifiedSkillCategory.SYSTEM.value,
            "ai": UnifiedSkillCategory.AI.value,
            "tool": UnifiedSkillCategory.AUTOMATION.value,
        }
        return mapping.get(category, UnifiedSkillCategory.GENERAL.value)


class SkillMetadata:
    """技能元数据（兼容旧版）"""

    def __init__(self, name: str, function: Callable, description: str = "",
                 category: str = SkillCategory.GENERAL, version: str = "1.0.0",
                 author: str = "", dependencies: list = None, permissions: List[str] = None,
                 security_level: str = "low", tags: List[str] = None,
                 timeout: int = 30, rate_limit: int = 100):
        self.name = name
        self.function = function
        self.description = description
        self.category = category
        self.version = version
        self.author = author
        self.dependencies = dependencies or []
        self.permissions = permissions or []
        self.security_level = security_level
        self.tags = tags or []
        self.timeout = timeout
        self.rate_limit = rate_limit
        self.created_at = datetime.now()
        self.last_used = None
        self.usage_count = 0


class SkillSystem:
    """技能系统兼容层 - 委托到统一技能系统"""

    def __init__(self):
        self._unified = get_unified_skill_system()

    def register_skill(self, name: str, function: Callable, description: str = "",
                       category: str = SkillCategory.GENERAL, version: str = "1.0.0",
                       **kwargs) -> bool:
        unified_category = SkillCategory.to_unified(category)
        try:
            self._unified.register_skill(
                name=name,
                function=function,
                description=description,
                category=unified_category,
                version=version,
                **kwargs,
            )
            return True
        except Exception as e:
            logger.warning("技能注册失败(兼容层): %s - %s", name, e)
            return False

    async def execute_skill(self, name: str, **kwargs) -> Any:
        return await self._unified.execute_skill(name, **kwargs)

    def get_skill(self, name: str) -> Optional[SkillMetadata]:
        unified_meta = self._unified.get_skill(name)
        if unified_meta:
            return SkillMetadata(
                name=unified_meta.name,
                function=unified_meta.function,
                description=unified_meta.description,
                category=unified_meta.category.value if hasattr(unified_meta.category, 'value') else str(unified_meta.category),
                version=unified_meta.version,
            )
        return None

    def list_skills(self, category: str = None) -> Dict[str, Any]:
        if category:
            unified_category = SkillCategory.to_unified(category)
            return self._unified.list_skills(category=unified_category)
        return self._unified.list_skills()

    def get_all_skills(self) -> Dict[str, SkillMetadata]:
        result = {}
        skills = self._unified.list_skills()
        if isinstance(skills, dict) and "skills" in skills:
            for name, meta in skills["skills"].items():
                if isinstance(meta, dict):
                    result[name] = SkillMetadata(name=name, function=lambda: None, description=meta.get("description", ""))
                elif hasattr(meta, "name"):
                    result[name] = SkillMetadata(name=meta.name, function=meta.function, description=meta.description)
        return result

    def unregister_skill(self, name: str) -> bool:
        try:
            self._unified.unregister_skill(name)
            return True
        except Exception:
            return False

    def get_skill_info(self, name: str) -> Optional[Dict[str, Any]]:
        return self._unified.get_skill_info(name)
