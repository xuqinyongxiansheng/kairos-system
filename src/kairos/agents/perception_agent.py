"""
感知 Agent
负责感知和接收外部信息
"""

import logging
from typing import Dict, Any, List
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class PerceptionAgent(BaseAgent):
    """感知 Agent - 接收和处理外部输入"""
    
    def __init__(self):
        super().__init__("PerceptionAgent", "感知外部输入")
        self.input_channels = {}
        self.perception_buffer = []
    
    async def initialize(self):
        """初始化感知 Agent"""
        logger.info("初始化感知 Agent")
        self.input_channels['default'] = {
            'type': 'text',
            'active': True
        }
        return {'status': 'success', 'message': '感知 Agent 初始化完成'}
    
    async def perceive(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        感知输入
        
        Args:
            input_data: 输入数据
            
        Returns:
            感知结果
        """
        try:
            logger.info(f"感知输入：{input_data.get('type', 'unknown')}")
            
            perception = {
                'status': 'success',
                'timestamp': self._get_timestamp(),
                'input_type': input_data.get('type', 'unknown'),
                'content': input_data.get('content', ''),
                'source': input_data.get('source', 'unknown'),
                'confidence': 0.9
            }
            
            self.perception_buffer.append(perception)
            
            return perception
            
        except Exception as e:
            logger.error(f"感知失败：{e}")
            return {'status': 'error', 'error': str(e)}
    
    async def register_channel(self, name: str, config: Dict[str, Any]):
        """注册输入通道"""
        self.input_channels[name] = {
            'config': config,
            'active': True
        }
        logger.info(f"输入通道注册：{name}")
        return {'status': 'success', 'channel': name}
    
    async def get_buffer_status(self) -> Dict[str, Any]:
        """获取缓冲区状态"""
        return {
            'status': 'success',
            'buffer_size': len(self.perception_buffer),
            'channels': list(self.input_channels.keys())
        }
