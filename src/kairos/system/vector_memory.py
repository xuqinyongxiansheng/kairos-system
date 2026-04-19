"""
向量记忆系统
实现语义记忆搜索能力
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib
import json
import os

logger = logging.getLogger(__name__)


class VectorMemory:
    """向量记忆系统 - 实现语义记忆搜索"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.persist_directory = self.config.get("vector_db_path", "./data/vector_memory")
        self.memories = []
        self.memory_index = {}
        
        os.makedirs(self.persist_directory, exist_ok=True)
        
        self._load_memories()
        
        logger.info("VectorMemory initialized")
    
    def _load_memories(self):
        """加载记忆"""
        index_file = os.path.join(self.persist_directory, "memory_index.json")
        
        if os.path.exists(index_file):
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memories = data.get('memories', [])
                    self.memory_index = data.get('index', {})
                logger.info(f"Loaded {len(self.memories)} memories")
            except Exception as e:
                logger.error(f"Failed to load memories: {e}")
    
    def _save_memories(self):
        """保存记忆"""
        index_file = os.path.join(self.persist_directory, "memory_index.json")
        
        try:
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'memories': self.memories,
                    'index': self.memory_index
                }, f, ensure_ascii=False, indent=2)
            logger.info("Memories saved")
        except Exception as e:
            logger.error(f"Failed to save memories: {e}")
    
    def _generate_embedding(self, text: str) -> List[float]:
        """生成简单嵌入向量（模拟）"""
        hash_value = hashlib.md5(text.encode()).hexdigest()
        return [float(int(hash_value[i:i+2], 16)) / 255.0 for i in range(0, 32, 2)]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def add_memory(
        self,
        content: str,
        metadata: Dict[str, Any] = None,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """添加记忆"""
        memory_id = f"mem_{len(self.memories) + 1}"
        
        embedding = self._generate_embedding(content)
        
        memory = {
            'id': memory_id,
            'content': content,
            'embedding': embedding,
            'metadata': metadata or {},
            'tags': tags or [],
            'timestamp': datetime.now().isoformat()
        }
        
        self.memories.append(memory)
        
        for tag in (tags or []):
            if tag not in self.memory_index:
                self.memory_index[tag] = []
            self.memory_index[tag].append(memory_id)
        
        self._save_memories()
        
        logger.info(f"Memory added: {memory_id}")
        
        return {
            'status': 'success',
            'memory_id': memory_id,
            'memory': memory
        }
    
    async def search_memories(
        self,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.5
    ) -> Dict[str, Any]:
        """搜索记忆"""
        query_embedding = self._generate_embedding(query)
        
        results = []
        
        for memory in self.memories:
            similarity = self._cosine_similarity(query_embedding, memory['embedding'])
            
            if similarity >= min_similarity:
                results.append({
                    'memory': memory,
                    'similarity': similarity
                })
        
        results.sort(key=lambda x: x['similarity'], reverse=True)
        results = results[:limit]
        
        logger.info(f"Search found {len(results)} memories")
        
        return {
            'status': 'success',
            'results': results,
            'count': len(results)
        }
    
    async def get_memory(self, memory_id: str) -> Dict[str, Any]:
        """获取记忆"""
        for memory in self.memories:
            if memory['id'] == memory_id:
                return {
                    'status': 'success',
                    'memory': memory
                }
        
        return {
            'status': 'not_found',
            'message': f'Memory not found: {memory_id}'
        }
    
    async def search_by_tags(self, tags: List[str]) -> Dict[str, Any]:
        """按标签搜索"""
        memory_ids = set()
        
        for tag in tags:
            if tag in self.memory_index:
                memory_ids.update(self.memory_index[tag])
        
        results = [
            m for m in self.memories
            if m['id'] in memory_ids
        ]
        
        return {
            'status': 'success',
            'results': results,
            'count': len(results)
        }
    
    async def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """删除记忆"""
        for i, memory in enumerate(self.memories):
            if memory['id'] == memory_id:
                for tag in memory['tags']:
                    if tag in self.memory_index and memory_id in self.memory_index[tag]:
                        self.memory_index[tag].remove(memory_id)
                
                del self.memories[i]
                self._save_memories()
                
                logger.info(f"Memory deleted: {memory_id}")
                
                return {
                    'status': 'success',
                    'message': 'Memory deleted'
                }
        
        return {
            'status': 'not_found',
            'message': f'Memory not found: {memory_id}'
        }
    
    async def get_memory_summary(self) -> Dict[str, Any]:
        """获取记忆摘要"""
        return {
            'status': 'success',
            'total_memories': len(self.memories),
            'total_tags': len(self.memory_index),
            'tags': list(self.memory_index.keys())
        }
