#!/usr/bin/env python3
"""
CrewAI 研究代理
"""

from .base_agent import BaseCrewAIAgent
from crewai_tools import SerperDevTool
from config.crewai_config import get_crewai_config


class ResearchAgent(BaseCrewAIAgent):
    """研究代理"""
    
    def __init__(self):
        super().__init__(
            role="Researcher",
            goal="Gather and analyze information from various sources",
            backstory="You are a professional researcher with expertise in information gathering and analysis. You excel at finding relevant information and synthesizing it into comprehensive insights."
        )
        
        # 添加工具
        config = get_crewai_config()
        if config.serper_api_key:
            self.add_tool(SerperDevTool(api_key=config.serper_api_key))
        else:
            # 没有API key时，使用其他工具
            from crewai_tools import FileReadTool
            self.add_tool(FileReadTool())