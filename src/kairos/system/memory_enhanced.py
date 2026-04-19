"""
增强记忆系统
提供高级记忆存储和检索功能
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    timestamp: str
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class EnhancedMemorySystem:
    """增强记忆系统"""
    
    def __init__(self):
        self.memories = {}
        self.memory_index = {}
        self.next_id = 1
        self.access_history = []
    
    async def add_memory(self, content: str, tags: List[str] = None,
                        metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """添加记忆"""
        memory_id = f"mem_{self.next_id}"
        self.next_id += 1
        
        if tags is None:
            tags = []
        if metadata is None:
            metadata = {}
        
        memory = MemoryEntry(
            id=memory_id,
            content=content,
            timestamp=datetime.now().isoformat(),
            tags=tags,
            metadata=metadata
        )
        
        self.memories[memory_id] = memory
        
        for tag in tags:
            if tag not in self.memory_index:
                self.memory_index[tag] = []
            self.memory_index[tag].append(memory_id)
        
        logger.info(f"记忆已添加：{memory_id}")
        
        return {
            'status': 'success',
            'memory_id': memory_id,
            'memory': memory.to_dict()
        }
    
    async def get_memory(self, memory_id: str) -> Dict[str, Any]:
        """获取记忆"""
        if memory_id not in self.memories:
            return {
                'status': 'not_found',
                'message': f'记忆不存在：{memory_id}'
            }
        
        memory = self.memories[memory_id]
        self._log_access(memory_id)
        
        return {
            'status': 'success',
            'memory': memory.to_dict()
        }
    
    async def search_memories(self, query: str, tags: List[str] = None) -> Dict[str, Any]:
        """搜索记忆"""
        results = []
        
        for memory_id, memory in self.memories.items():
            match = False
            
            if query.lower() in memory.content.lower():
                match = True
            
            if tags:
                if any(tag in memory.tags for tag in tags):
                    match = True
            
            if match:
                results.append(memory.to_dict())
        
        return {
            'status': 'success',
            'results': results,
            'count': len(results)
        }
    
    async def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """删除记忆"""
        if memory_id not in self.memories:
            return {
                'status': 'not_found',
                'message': f'记忆不存在：{memory_id}'
            }
        
        memory = self.memories[memory_id]
        
        for tag in memory.tags:
            if tag in self.memory_index and memory_id in self.memory_index[tag]:
                self.memory_index[tag].remove(memory_id)
        
        del self.memories[memory_id]
        logger.info(f"记忆已删除：{memory_id}")
        
        return {
            'status': 'success',
            'message': '记忆已删除'
        }
    
    def _log_access(self, memory_id: str):
        """记录访问日志"""
        self.access_history.append({
            'memory_id': memory_id,
            'timestamp': datetime.now().isoformat()
        })
    
    async def get_memories_by_tag(self, tag: str) -> Dict[str, Any]:
        """按标签获取记忆"""
        if tag not in self.memory_index:
            return {
                'status': 'success',
                'memories': [],
                'count': 0
            }
        
        memories = [
            self.memories[mid].to_dict()
            for mid in self.memory_index[tag]
            if mid in self.memories
        ]
        
        return {
            'status': 'success',
            'memories': memories,
            'count': len(memories)
        }
    
    async def get_memory_summary(self) -> Dict[str, Any]:
        """获取记忆摘要"""
        return {
            'status': 'success',
            'total_memories': len(self.memories),
            'total_tags': len(self.memory_index),
            'total_accesses': len(self.access_history)
        }
