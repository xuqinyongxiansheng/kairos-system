#!/usr/bin/env python3
"""
CrewAI 协调器
"""

from .base_agent import BaseCrewAIAgent
from crewai import Crew, Process
from typing import List, Optional


class CrewCoordinator:
    """CrewAI 协调器"""
    
    def __init__(self):
        self.agents = []
    
    def add_agent(self, agent):
        """添加代理"""
        self.agents.append(agent)
    
    def create_crew(self, task, process=Process.sequential):
        """创建代理团队"""
        crew_agents = [agent.create_agent() for agent in self.agents]
        
        from crewai import Task
        crew_task = Task(
            description=task,
            expected_output="A comprehensive solution to the task",
            agents=crew_agents
        )
        
        return Crew(
            agents=crew_agents,
            tasks=[crew_task],
            process=process,
            verbose=2
        )
    
    def run_task(self, task, process=Process.sequential):
        """运行任务"""
        crew = self.create_crew(task, process)
        return crew.kickoff()
    
    def get_agent_info(self):
        """获取代理信息"""
        return [agent.get_info() for agent in self.agents]