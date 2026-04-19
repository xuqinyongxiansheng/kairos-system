#!/usr/bin/env python3
"""
Agent 集成模块
"""

from .agency_agents import get_agency_agent_adapter
from .minimax_skills import get_minimax_skill_adapter
from .claude_mem import get_claude_mem_adapter
from .speech_recognition import get_speech_recognition_adapter
from .vision_volo import get_vision_volo_adapter
from .clawbot_adapter import get_clawbot_adapter, get_clawbot_bridge

__all__ = [
    "get_agency_agent_adapter",
    "get_minimax_skill_adapter",
    "get_claude_mem_adapter",
    "get_speech_recognition_adapter",
    "get_vision_volo_adapter",
    "get_clawbot_adapter",
    "get_clawbot_bridge",
]
