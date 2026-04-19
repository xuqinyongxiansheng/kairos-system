#!/usr/bin/env python3
"""
CrewAI 基础代理
"""

from crewai import Agent
from typing import List, Optional, Dict, Any
from config.crewai_config import get_crewai_config


class BaseCrewAIAgent:
    """CrewAI 基础代理"""
    
    def __init__(self, role: str, goal: str, backstory: str):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.tools = []
        self.config = get_crewai_config()
    
    def add_tool(self, tool):
        """添加工具"""
        self.tools.append(tool)
    
    def create_agent(self) -> Agent:
        """创建代理"""
        return Agent(
            role=self.role,
            goal=self.goal,
            backstory=self.backstory,
            tools=self.tools,
            verbose=True,
            allow_delegation=True,
            # 使用本地模型
            llm=self._get_local_llm()
        )
    
    def _get_local_llm(self):
        """获取本地LLM"""
        try:
            from langchain_ollama import OllamaLLM
            return OllamaLLM(
                model=self.config.default_model,
                base_url=self.config.local_model_endpoint
            )
        except ImportError:
            # 回退到OpenAI
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model="gpt-4o-mini",
                temperature=self.config.temperature
            )
    
    def get_info(self) -> Dict[str, Any]:
        """获取代理信息"""
        return {
            "role": self.role,
            "goal": self.goal,
            "backstory": self.backstory,
            "tool_count": len(self.tools)
        }