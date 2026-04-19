"""
记忆 Agent
负责记忆管理和检索
"""

import logging
from typing import Dict, Any, List
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class MemoryAgent(BaseAgent):
    """记忆 Agent - 管理和检索记忆"""
    
    def __init__(self):
        super().__init__("MemoryAgent", "记忆管理和检索")
        self.short_term_memory = []
        self.long_term_memory = {}
        self.memory_index = {}
    
    async def initialize(self):
        """初始化记忆 Agent"""
        logger.info("初始化记忆 Agent")
        return {'status': 'success', 'message': '记忆 Agent 初始化完成'}
    
    async def store(self, memory_data: Dict[str, Any], 
                   memory_type: str = 'short') -> Dict[str, Any]:
        """
        存储记忆
        
        Args:
            memory_data: 记忆数据
            memory_type: 记忆类型 (short/long)
            
        Returns:
            存储结果
        """
        try:
            logger.info(f"存储记忆：{memory_type}")
            
            timestamp = self._get_timestamp()
            memory_id = len(self.short_term_memory) + len(self.long_term_memory)
            
            memory = {
                'id': memory_id,
                'timestamp': timestamp,
                'content': memory_data.get('content', ''),
                'type': memory_data.get('type', 'general'),
                'importance': memory_data.get('importance', 0.5)
            }
            
            if memory_type == 'long':
                self.long_term_memory[memory_id] = memory
            else:
                self.short_term_memory.append(memory)
            
            return {
                'status': 'success',
                'memory_id': memory_id,
                'type': memory_type
            }
            
        except Exception as e:
            logger.error(f"存储记忆失败：{e}")
            return {'status': 'error', 'error': str(e)}
    
    async def retrieve(self, memory_id: int, 
                      memory_type: str = 'short') -> Dict[str, Any]:
        """检索记忆"""
        if memory_type == 'long':
            if memory_id in self.long_term_memory:
                return {
                    'status': 'success',
                    'memory': self.long_term_memory[memory_id]
                }
        else:
            for memory in self.short_term_memory:
                if memory['id'] == memory_id:
                    return {
                        'status': 'success',
                        'memory': memory
                    }
        
        return {
            'status': 'not_found',
            'message': f'记忆不存在：{memory_id}'
        }
    
    async def search(self, keywords: List[str]) -> Dict[str, Any]:
        """搜索记忆"""
        results = []
        
        all_memories = list(self.long_term_memory.values()) + self.short_term_memory
        
        for memory in all_memories:
            content = str(memory.get('content', '')).lower()
            if any(kw.lower() in content for kw in keywords):
                results.append(memory)
        
        return {
            'status': 'success',
            'results': results,
            'count': len(results)
        }
    
    async def get_memory_summary(self) -> Dict[str, Any]:
        """获取记忆摘要"""
        return {
            'status': 'success',
            'short_term_count': len(self.short_term_memory),
            'long_term_count': len(self.long_term_memory)
        }
