#!/usr/bin/env python3
"""
Agent 协调器 - 协调所有 Agent 的工作
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from .base_agent import BaseAgent
from .brain_agent import BrainAgent, get_brain_agent

logger = logging.getLogger("AgentCoordinator")


class AgentCoordinator:
    """Agent 协调器 - 管理和协调所有 Agent"""
    
    def __init__(self):
        """初始化协调器"""
        self.brain = get_brain_agent()
        self.agents: Dict[str, BaseAgent] = {}
        self.task_history = []
        
        logger.info("Agent 协调器初始化完成")
    
    def register_agent(self, name: str, agent: BaseAgent):
        """
        注册 Agent
        
        Args:
            name: Agent 名称
            agent: Agent 实例
        """
        self.agents[name] = agent
        self.brain.register_sub_agent(name, agent)
        logger.info(f"注册 Agent: {name}")
    
    def unregister_agent(self, name: str):
        """
        注销 Agent
        
        Args:
            name: Agent 名称
        """
        if name in self.agents:
            del self.agents[name]
            self.brain.unregister_sub_agent(name)
            logger.info(f"注销 Agent: {name}")
    
    def get_agent(self, name: str) -> BaseAgent:
        """
        获取 Agent
        
        Args:
            name: Agent 名称
            
        Returns:
            Agent 实例
        """
        if name not in self.agents:
            raise ValueError(f"Agent 不存在：{name}")
        return self.agents[name]
    
    def list_agents(self) -> List[str]:
        """
        列出所有 Agent
        
        Returns:
            Agent 名称列表
        """
        return list(self.agents.keys())
    
    async def execute_task(self, task: str, agent_name: str = None, **kwargs) -> Dict[str, Any]:
        """
        执行任务
        
        Args:
            task: 任务描述
            agent_name: 指定 Agent 名称 (可选)
            **kwargs: 任务参数
            
        Returns:
            执行结果
        """
        try:
            logger.info(f"执行任务：{task[:50]}...")
            
            # 如果指定了 Agent，直接调用
            if agent_name:
                agent = self.get_agent(agent_name)
                result = await agent.execute(task, **kwargs)
            else:
                # 否则交给大脑 Agent 协调
                result = await self.brain.execute_task(task, **kwargs)
            
            # 记录任务历史
            self.task_history.append({
                "task": task,
                "agent": agent_name or "auto",
                "timestamp": datetime.now().isoformat(),
                "result": result
            })
            
            return result
            
        except Exception as e:
            logger.error(f"任务执行失败：{e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取协调器状态
        
        Returns:
            状态信息
        """
        return {
            "coordinator": "AgentCoordinator",
            "brain_status": self.brain.get_status(),
            "agents_count": len(self.agents),
            "agents": list(self.agents.keys()),
            "task_history_size": len(self.task_history),
            "timestamp": datetime.now().isoformat()
        }


# 单例模式
_coordinator_instance = None


def get_coordinator() -> AgentCoordinator:
    """获取协调器单例"""
    global _coordinator_instance
    if _coordinator_instance is None:
        _coordinator_instance = AgentCoordinator()
    return _coordinator_instance
