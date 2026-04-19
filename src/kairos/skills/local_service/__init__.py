#!/usr/bin/env python3
"""
本地大模型服务模块
将三种技能适配到 Ollama 本地模型
"""

from .service import (
    LocalSkillService,
    OllamaClient,
    SkillType,
    get_local_skill_service
)

__all__ = [
    "LocalSkillService",
    "OllamaClient",
    "SkillType",
    "get_local_skill_service"
]
