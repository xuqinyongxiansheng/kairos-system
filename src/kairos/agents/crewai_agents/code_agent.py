#!/usr/bin/env python3
"""
CrewAI 代码代理
"""

from .base_agent import BaseCrewAIAgent
from crewai_tools import FileReadTool, FileWriteTool, DirectoryReadTool


class CodeAgent(BaseCrewAIAgent):
    """代码代理"""
    
    def __init__(self):
        super().__init__(
            role="Senior Software Engineer",
            goal="Write high-quality, efficient, and well-documented code",
            backstory="You are a seasoned software engineer with expertise in multiple programming languages and frameworks. You excel at writing clean, maintainable code and solving complex technical problems."
        )
        
        # 添加工具
        self.add_tool(FileReadTool())
        self.add_tool(FileWriteTool())
        self.add_tool(DirectoryReadTool())