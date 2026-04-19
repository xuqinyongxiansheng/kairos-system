#!/usr/bin/env python3
"""
专业Agent基类
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AgentMessage(BaseModel):
    """Agent消息"""
    sender: str
    receiver: str
    content: str
    message_type: str = "text"
    metadata: Dict[str, Any] = {}


class ProfessionalAgent:
    """专业Agent基类"""
    
    def __init__(self, agent_id: str, name: str, description: str):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.skills: List[str] = []
        self.capabilities: List[str] = []
        self.communication_channel = None
    
    def add_skill(self, skill: str):
        """添加技能"""
        if skill not in self.skills:
            self.skills.append(skill)
    
    def add_capability(self, capability: str):
        """添加能力"""
        if capability not in self.capabilities:
            self.capabilities.append(capability)
    
    async def process_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理任务"""
        raise NotImplementedError("子类必须实现process_task方法")
    
    async def send_message(self, receiver: str, content: str, message_type: str = "text", 
                          metadata: Optional[Dict[str, Any]] = None):
        """发送消息"""
        if self.communication_channel:
            message = AgentMessage(
                sender=self.agent_id,
                receiver=receiver,
                content=content,
                message_type=message_type,
                metadata=metadata or {}
            )
            await self.communication_channel.send_message(message)
    
    async def receive_message(self, message: AgentMessage):
        """接收消息"""
        logger.info(f"{self.name} 收到来自 {message.sender} 的消息: {message.content}")
    
    def get_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "skills": self.skills,
            "capabilities": self.capabilities
        }
    
    def set_communication_channel(self, channel):
        """设置通信通道"""
        self.communication_channel = channel


class AgentRegistry:
    """Agent注册表"""
    
    def __init__(self):
        self.agents: Dict[str, ProfessionalAgent] = {}
    
    def register_agent(self, agent: ProfessionalAgent):
        """注册Agent"""
        self.agents[agent.agent_id] = agent
    
    def get_agent(self, agent_id: str) -> Optional[ProfessionalAgent]:
        """获取Agent"""
        return self.agents.get(agent_id)
    
    def list_agents(self) -> List[ProfessionalAgent]:
        """列出所有Agent"""
        return list(self.agents.values())
    
    def get_agents_by_skill(self, skill: str) -> List[ProfessionalAgent]:
        """根据技能获取Agent"""
        return [agent for agent in self.agents.values() if skill in agent.skills]
    
    def get_agents_by_capability(self, capability: str) -> List[ProfessionalAgent]:
        """根据能力获取Agent"""
        return [agent for agent in self.agents.values() if capability in agent.capabilities]


# 全局Agent注册表实例
_agent_registry = None

def get_agent_registry() -> AgentRegistry:
    """获取Agent注册表实例"""
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = AgentRegistry()
    return _agent_registry