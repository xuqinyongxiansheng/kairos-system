"""
通信 Agent
负责对外通信和交互
"""

import logging
from typing import Dict, Any, List
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class CommunicationAgent(BaseAgent):
    """通信 Agent - 管理对外通信"""
    
    def __init__(self):
        super().__init__("CommunicationAgent", "对外通信和交互")
        self.channels = {}
        self.message_history = []
    
    async def initialize(self):
        """初始化通信 Agent"""
        logger.info("初始化通信 Agent")
        return {'status': 'success', 'message': '通信 Agent 初始化完成'}
    
    async def send(self, message: Dict[str, Any], 
                  channel: str = 'default') -> Dict[str, Any]:
        """
        发送消息
        
        Args:
            message: 消息内容
            channel: 通信渠道
            
        Returns:
            发送结果
        """
        try:
            logger.info(f"发送消息：{channel}")
            
            message_record = {
                'id': len(self.message_history) + 1,
                'timestamp': self._get_timestamp(),
                'direction': 'outbound',
                'channel': channel,
                'content': message.get('content', ''),
                'status': 'sent'
            }
            
            self.message_history.append(message_record)
            
            return {
                'status': 'success',
                'message_id': message_record['id'],
                'channel': channel
            }
            
        except Exception as e:
            logger.error(f"发送消息失败：{e}")
            return {'status': 'error', 'error': str(e)}
    
    async def receive(self, message: Dict[str, Any], 
                     channel: str = 'default') -> Dict[str, Any]:
        """接收消息"""
        try:
            logger.info(f"接收消息：{channel}")
            
            message_record = {
                'id': len(self.message_history) + 1,
                'timestamp': self._get_timestamp(),
                'direction': 'inbound',
                'channel': channel,
                'content': message.get('content', '')
            }
            
            self.message_history.append(message_record)
            
            return {
                'status': 'success',
                'message': message_record
            }
            
        except Exception as e:
            logger.error(f"接收消息失败：{e}")
            return {'status': 'error', 'error': str(e)}
    
    async def register_channel(self, name: str, config: Dict[str, Any]):
        """注册通信渠道"""
        self.channels[name] = {
            'config': config,
            'active': True
        }
        logger.info(f"通信渠道注册：{name}")
        return {'status': 'success', 'channel': name}
    
    async def get_message_summary(self) -> Dict[str, Any]:
        """获取消息摘要"""
        outbound = sum(1 for m in self.message_history if m['direction'] == 'outbound')
        inbound = sum(1 for m in self.message_history if m['direction'] == 'inbound')
        
        return {
            'status': 'success',
            'total_messages': len(self.message_history),
            'outbound': outbound,
            'inbound': inbound,
            'channels': list(self.channels.keys())
        }
