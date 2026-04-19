#!/usr/bin/env python3
"""
消息传递系统
实现Agent之间的消息发送和接收
"""

import asyncio
import logging
import queue
from typing import Dict, Any, Optional, List

from .protocol import AgentMessage, CommunicationProtocol, MessageValidator

logger = logging.getLogger(__name__)


class MessageQueue:
    """消息队列"""
    
    def __init__(self):
        self.queue = queue.PriorityQueue()
    
    def put(self, message: AgentMessage):
        """放入消息"""
        # 使用优先级进行排序
        self.queue.put((-message.priority, message))
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Optional[AgentMessage]:
        """获取消息"""
        try:
            _, message = self.queue.get(block=block, timeout=timeout)
            return message
        except queue.Empty:
            return None
    
    def qsize(self) -> int:
        """获取队列大小"""
        return self.queue.qsize()
    
    def empty(self) -> bool:
        """检查队列是否为空"""
        return self.queue.empty()


class CommunicationChannel:
    """通信通道"""
    
    def __init__(self):
        self.agent_queues: Dict[str, MessageQueue] = {}
        self.message_history: List[AgentMessage] = []
        self.lock = asyncio.Lock()
    
    def register_agent(self, agent_id: str):
        """注册Agent"""
        if agent_id not in self.agent_queues:
            self.agent_queues[agent_id] = MessageQueue()
            logger.info(f"Agent {agent_id} 已注册到通信通道")
    
    def unregister_agent(self, agent_id: str):
        """注销Agent"""
        if agent_id in self.agent_queues:
            del self.agent_queues[agent_id]
            logger.info(f"Agent {agent_id} 已从通信通道注销")
    
    async def send_message(self, message: AgentMessage):
        """发送消息"""
        # 验证消息
        if not MessageValidator.validate_message(message):
            logger.error("无效的消息")
            return False
        
        # 注册发送者和接收者
        self.register_agent(message.sender)
        self.register_agent(message.receiver)
        
        # 放入接收者的队列
        if message.receiver in self.agent_queues:
            self.agent_queues[message.receiver].put(message)
            
            # 记录消息历史
            async with self.lock:
                self.message_history.append(message)
                # 限制历史记录大小
                if len(self.message_history) > 1000:
                    self.message_history = self.message_history[-1000:]
            
            logger.info(f"消息从 {message.sender} 发送到 {message.receiver}")
            return True
        else:
            logger.error(f"接收者 {message.receiver} 不存在")
            return False
    
    async def receive_message(self, agent_id: str, timeout: Optional[float] = None) -> Optional[AgentMessage]:
        """接收消息"""
        if agent_id not in self.agent_queues:
            self.register_agent(agent_id)
        
        # 从队列中获取消息
        message = self.agent_queues[agent_id].get(block=False)
        if message:
            logger.info(f"Agent {agent_id} 收到消息")
            return message
        return None
    
    async def broadcast_message(self, sender: str, content: str, 
                              message_type: str = "text",
                              metadata: Optional[Dict[str, Any]] = None):
        """广播消息"""
        for agent_id in self.agent_queues:
            if agent_id != sender:
                message = CommunicationProtocol.create_message(
                    sender=sender,
                    receiver=agent_id,
                    content=content,
                    message_type=message_type,
                    metadata=metadata
                )
                await self.send_message(message)
    
    def get_message_history(self, agent_id: Optional[str] = None) -> List[AgentMessage]:
        """获取消息历史"""
        if agent_id:
            return [msg for msg in self.message_history 
                   if msg.sender == agent_id or msg.receiver == agent_id]
        return self.message_history
    
    def get_queue_size(self, agent_id: str) -> int:
        """获取Agent的消息队列大小"""
        if agent_id in self.agent_queues:
            return self.agent_queues[agent_id].qsize()
        return 0


class CommunicationManager:
    """通信管理器"""
    
    def __init__(self):
        self.channels: Dict[str, CommunicationChannel] = {}
        self.default_channel = "default"
        self._create_default_channel()
    
    def _create_default_channel(self):
        """创建默认通道"""
        self.channels[self.default_channel] = CommunicationChannel()
    
    def get_channel(self, channel_name: str = None) -> CommunicationChannel:
        """获取通信通道"""
        channel_name = channel_name or self.default_channel
        if channel_name not in self.channels:
            self.channels[channel_name] = CommunicationChannel()
        return self.channels[channel_name]
    
    def create_channel(self, channel_name: str) -> CommunicationChannel:
        """创建通信通道"""
        if channel_name not in self.channels:
            self.channels[channel_name] = CommunicationChannel()
            logger.info(f"创建通信通道: {channel_name}")
        return self.channels[channel_name]
    
    def remove_channel(self, channel_name: str):
        """移除通信通道"""
        if channel_name != self.default_channel and channel_name in self.channels:
            del self.channels[channel_name]
            logger.info(f"移除通信通道: {channel_name}")
    
    async def send_message(self, message: AgentMessage, channel_name: str = None):
        """发送消息"""
        channel = self.get_channel(channel_name)
        return await channel.send_message(message)
    
    async def receive_message(self, agent_id: str, channel_name: str = None, 
                           timeout: Optional[float] = None) -> Optional[AgentMessage]:
        """接收消息"""
        channel = self.get_channel(channel_name)
        return await channel.receive_message(agent_id, timeout)
    
    async def broadcast_message(self, sender: str, content: str, 
                              message_type: str = "text",
                              metadata: Optional[Dict[str, Any]] = None,
                              channel_name: str = None):
        """广播消息"""
        channel = self.get_channel(channel_name)
        await channel.broadcast_message(sender, content, message_type, metadata)
    
    def register_agent(self, agent_id: str, channel_name: str = None):
        """注册Agent到通道"""
        channel = self.get_channel(channel_name)
        channel.register_agent(agent_id)
    
    def unregister_agent(self, agent_id: str, channel_name: str = None):
        """从通道注销Agent"""
        channel = self.get_channel(channel_name)
        channel.unregister_agent(agent_id)


# 全局通信管理器实例
_communication_manager = None

def get_communication_manager() -> CommunicationManager:
    """获取通信管理器实例"""
    global _communication_manager
    if _communication_manager is None:
        _communication_manager = CommunicationManager()
    return _communication_manager


if __name__ == "__main__":
    # 测试
    import asyncio
    
    async def test_communication():
        comm_manager = get_communication_manager()
        
        # 注册Agent
        comm_manager.register_agent("agent1")
        comm_manager.register_agent("agent2")
        
        # 创建消息
        message = CommunicationProtocol.create_message(
            sender="agent1",
            receiver="agent2",
            content="Hello from agent1",
            message_type="text"
        )
        
        # 发送消息
        await comm_manager.send_message(message)
        
        # 接收消息
        received_message = await comm_manager.receive_message("agent2")
        if received_message:
            print(f"接收到消息: {received_message.content}")
        
        # 广播消息
        await comm_manager.broadcast_message(
            sender="agent1",
            content="Broadcast message",
            message_type="system"
        )
    
    asyncio.run(test_communication())