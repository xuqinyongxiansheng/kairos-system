#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一记忆系统架构
整合短期记忆、长期记忆、向量存储、语义搜索功能
参照人类神经学中的强化神经元系统原理设计

核心功能：
1. 多层记忆架构（工作记忆/短期记忆/长期记忆/语义记忆）
2. 向量语义搜索（ChromaDB集成）
3. 强化学习机制（记忆权重动态调整）
4. 记忆衰减与巩固（模拟人类遗忘曲线）
5. 统一API接口（兼容所有现有模块）
"""

import json
import time
import os
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger("UnifiedMemorySystem")


class MemoryType(Enum):
    """记忆类型枚举"""
    WORKING = "working"           # 工作记忆（当前任务相关）
    SHORT_TERM = "short_term"     # 短期记忆（临时信息）
    LONG_TERM = "long_term"       # 长期记忆（重要信息）
    SEMANTIC = "semantic"         # 语义记忆（知识库）
    EPISODIC = "episodic"         # 情景记忆（事件经历）
    PROCEDURAL = "procedural"     # 程序记忆（技能方法）


class MemoryPriority(Enum):
    """记忆优先级"""
    CRITICAL = 0    # 关键记忆，永不遗忘
    HIGH = 1        # 高优先级，长期保留
    MEDIUM = 2      # 中等优先级，正常保留
    LOW = 3         # 低优先级，可能遗忘
    TEMPORARY = 4   # 临时记忆，快速遗忘


@dataclass
class MemoryNode:
    """记忆节点 - 模拟神经元"""
    id: str
    content: str
    memory_type: str
    embedding: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    priority: int = 2
    weight: float = 1.0              # 记忆权重（强化学习）
    access_count: int = 0            # 访问次数
    created_at: str = ""
    last_accessed: str = ""
    last_reinforced: str = ""        # 最后强化时间
    decay_rate: float = 0.1          # 衰减率
    connections: List[str] = field(default_factory=list)  # 关联记忆ID
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_accessed:
            self.last_accessed = self.created_at
        if not self.last_reinforced:
            self.last_reinforced = self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def access(self):
        """访问记忆 - 强化连接"""
        self.access_count += 1
        self.last_accessed = datetime.now().isoformat()
        self.weight = min(self.weight * 1.1, 10.0)  # 权重增加，上限10
    
    def reinforce(self, strength: float = 0.5):
        """强化记忆 - 模拟神经元强化"""
        self.weight = min(self.weight + strength, 10.0)
        self.last_reinforced = datetime.now().isoformat()
        self.decay_rate = max(self.decay_rate * 0.9, 0.01)  # 降低衰减率
    
    def decay(self):
        """记忆衰减 - 模拟遗忘曲线"""
        days_since_reinforced = (datetime.now() - datetime.fromisoformat(self.last_reinforced)).days
        decay_factor = self.decay_rate * days_since_reinforced
        self.weight = max(self.weight * (1 - decay_factor), 0.1)
        
        if self.weight < 0.3 and self.priority > MemoryPriority.HIGH.value:
            return True  # 标记为可遗忘
        return False


class MemoryBackend(ABC):
    """记忆存储后端抽象类"""
    
    @abstractmethod
    async def store(self, memory: MemoryNode) -> bool:
        pass
    
    @abstractmethod
    async def retrieve(self, memory_id: str) -> Optional[MemoryNode]:
        pass
    
    @abstractmethod
    async def search(self, query: str, limit: int) -> List[MemoryNode]:
        pass
    
    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        pass


class FileBackend(MemoryBackend):
    """文件存储后端"""
    
    def __init__(self, storage_path: str = "./data/unified_memory"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        self.index_file = os.path.join(storage_path, "memory_index.json")
        self.memories: Dict[str, MemoryNode] = {}
        self._load_index()
    
    def _load_index(self):
        """加载记忆索引"""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for mem_id, mem_data in data.items():
                        self.memories[mem_id] = MemoryNode(**mem_data)
                logger.info(f"加载 {len(self.memories)} 条记忆")
            except Exception as e:
                logger.error(f"加载记忆索引失败: {e}")
    
    def _save_index(self):
        """保存记忆索引"""
        try:
            data = {mem_id: mem.to_dict() for mem_id, mem in self.memories.items()}
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存记忆索引失败: {e}")
    
    async def store(self, memory: MemoryNode) -> bool:
        """存储记忆"""
        self.memories[memory.id] = memory
        self._save_index()
        return True
    
    async def retrieve(self, memory_id: str) -> Optional[MemoryNode]:
        """检索记忆"""
        memory = self.memories.get(memory_id)
        if memory:
            memory.access()
        return memory
    
    async def search(self, query: str, limit: int) -> List[MemoryNode]:
        """搜索记忆（简单关键词匹配）"""
        results = []
        query_lower = query.lower()
        
        for memory in self.memories.values():
            if query_lower in memory.content.lower():
                results.append(memory)
            elif any(query_lower in tag.lower() for tag in memory.tags):
                results.append(memory)
        
        results.sort(key=lambda x: x.weight, reverse=True)
        return results[:limit]
    
    async def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        if memory_id in self.memories:
            del self.memories[memory_id]
            self._save_index()
            return True
        return False


class ChromaDBBackend(MemoryBackend):
    """ChromaDB向量存储后端"""
    
    def __init__(self, storage_path: str = "./data/chromadb_unified"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        
        try:
            import chromadb
            from chromadb.config import Settings
            
            self.client = chromadb.PersistentClient(
                path=storage_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            self.collection = self.client.get_or_create_collection(
                name="unified_memory",
                metadata={"description": "统一记忆系统向量存储"}
            )
            
            self.available = True
            logger.info(f"ChromaDB后端初始化成功: {storage_path}")
            
        except ImportError:
            self.available = False
            logger.warning("ChromaDB未安装，向量搜索功能不可用")
    
    async def store(self, memory: MemoryNode) -> bool:
        """存储记忆到向量数据库"""
        if not self.available:
            return False
        
        try:
            self.collection.add(
                documents=[memory.content],
                metadatas=[{
                    "memory_type": memory.memory_type,
                    "priority": memory.priority,
                    "weight": memory.weight,
                    "tags": json.dumps(memory.tags),
                    "created_at": memory.created_at
                }],
                ids=[memory.id]
            )
            return True
        except Exception as e:
            logger.error(f"ChromaDB存储失败: {e}")
            return False
    
    async def retrieve(self, memory_id: str) -> Optional[MemoryNode]:
        """从向量数据库检索记忆"""
        if not self.available:
            return None
        
        try:
            result = self.collection.get(ids=[memory_id])
            if result["ids"]:
                return MemoryNode(
                    id=result["ids"][0],
                    content=result["documents"][0],
                    memory_type=result["metadatas"][0].get("memory_type", "short_term"),
                    metadata=result["metadatas"][0],
                    tags=json.loads(result["metadatas"][0].get("tags", "[]"))
                )
        except Exception as e:
            logger.error(f"ChromaDB检索失败: {e}")
        return None
    
    async def search(self, query: str, limit: int) -> List[MemoryNode]:
        """语义搜索记忆"""
        if not self.available:
            return []
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            
            memories = []
            for i in range(len(results["ids"][0])):
                memory = MemoryNode(
                    id=results["ids"][0][i],
                    content=results["documents"][0][i],
                    memory_type=results["metadatas"][0][i].get("memory_type", "short_term"),
                    metadata=results["metadatas"][0][i],
                    tags=json.loads(results["metadatas"][0][i].get("tags", "[]"))
                )
                memories.append(memory)
            
            return memories
        except Exception as e:
            logger.error(f"ChromaDB搜索失败: {e}")
            return []
    
    async def delete(self, memory_id: str) -> bool:
        """从向量数据库删除记忆"""
        if not self.available:
            return False
        
        try:
            self.collection.delete(ids=[memory_id])
            return True
        except Exception as e:
            logger.error(f"ChromaDB删除失败: {e}")
            return False


class UnifiedMemorySystem:
    """
    统一记忆系统
    整合多层记忆架构，提供统一的记忆管理接口
    """
    
    def __init__(self, config: Dict = None):
        """初始化统一记忆系统"""
        self.config = config or {}
        
        # 存储后端
        self.file_backend = FileBackend(
            self.config.get("file_storage_path", "./data/unified_memory")
        )
        self.vector_backend = ChromaDBBackend(
            self.config.get("vector_storage_path", "./data/chromadb_unified")
        )
        
        # 记忆层级容量
        self.capacity = {
            MemoryType.WORKING.value: 7,          # 工作记忆容量（模拟人类7±2）
            MemoryType.SHORT_TERM.value: 100,     # 短期记忆容量
            MemoryType.LONG_TERM.value: 10000,    # 长期记忆容量
            MemoryType.SEMANTIC.value: 50000,     # 语义记忆容量
            MemoryType.EPISODIC.value: 5000,      # 情景记忆容量
            MemoryType.PROCEDURAL.value: 1000     # 程序记忆容量
        }
        
        # 记忆索引
        self.type_index: Dict[str, List[str]] = {t.value: [] for t in MemoryType}
        self.tag_index: Dict[str, List[str]] = {}
        self.connection_graph: Dict[str, List[str]] = {}  # 记忆关联图
        
        # 统计信息
        self.stats = {
            "total_memories": 0,
            "total_accesses": 0,
            "total_reinforcements": 0,
            "total_forgettings": 0
        }
        
        self._rebuild_index()
        logger.info("统一记忆系统初始化完成")
    
    def _rebuild_index(self):
        """重建记忆索引"""
        for memory_id, memory in self.file_backend.memories.items():
            self.type_index[memory.memory_type].append(memory_id)
            for tag in memory.tags:
                if tag not in self.tag_index:
                    self.tag_index[tag] = []
                self.tag_index[tag].append(memory_id)
            if memory.connections:
                self.connection_graph[memory_id] = memory.connections
        
        self.stats["total_memories"] = len(self.file_backend.memories)
    
    def _generate_id(self, content: str) -> str:
        """生成记忆ID"""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(f"{content}_{timestamp}".encode()).hexdigest()[:16]
    
    def _generate_embedding(self, text: str) -> List[float]:
        """生成简单嵌入向量"""
        hash_value = hashlib.md5(text.encode()).hexdigest()
        return [float(int(hash_value[i:i+2], 16)) / 255.0 for i in range(0, 32, 2)]
    
    async def add_memory(
        self,
        content: str,
        memory_type: str = "short_term",
        tags: List[str] = None,
        metadata: Dict = None,
        priority: int = 2,
        connections: List[str] = None
    ) -> Dict[str, Any]:
        """
        添加记忆
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型
            tags: 标签列表
            metadata: 元数据
            priority: 优先级
            connections: 关联记忆ID列表
        
        Returns:
            添加结果
        """
        try:
            memory_id = self._generate_id(content)
            
            memory = MemoryNode(
                id=memory_id,
                content=content,
                memory_type=memory_type,
                embedding=self._generate_embedding(content),
                metadata=metadata or {},
                tags=tags or [],
                priority=priority,
                connections=connections or []
            )
            
            # 存储到文件后端
            await self.file_backend.store(memory)
            
            # 存储到向量后端
            await self.vector_backend.store(memory)
            
            # 更新索引
            self.type_index[memory_type].append(memory_id)
            for tag in (tags or []):
                if tag not in self.tag_index:
                    self.tag_index[tag] = []
                self.tag_index[tag].append(memory_id)
            
            if connections:
                self.connection_graph[memory_id] = connections
                # 建立双向连接
                for conn_id in connections:
                    if conn_id not in self.connection_graph:
                        self.connection_graph[conn_id] = []
                    if memory_id not in self.connection_graph[conn_id]:
                        self.connection_graph[conn_id].append(memory_id)
            
            self.stats["total_memories"] += 1
            
            logger.info(f"记忆已添加: {memory_id} ({memory_type})")
            
            return {
                "success": True,
                "memory_id": memory_id,
                "memory_type": memory_type
            }
            
        except Exception as e:
            logger.error(f"添加记忆失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """获取记忆"""
        memory = await self.file_backend.retrieve(memory_id)
        if memory:
            self.stats["total_accesses"] += 1
            return memory.to_dict()
        return None
    
    async def search_memories(
        self,
        query: str,
        memory_type: str = None,
        tags: List[str] = None,
        limit: int = 10,
        use_semantic: bool = True
    ) -> List[Dict[str, Any]]:
        """
        搜索记忆
        
        Args:
            query: 搜索查询
            memory_type: 记忆类型过滤
            tags: 标签过滤
            limit: 返回数量限制
            use_semantic: 是否使用语义搜索
        
        Returns:
            记忆列表
        """
        results = []
        
        # 语义搜索（优先）
        if use_semantic and self.vector_backend.available:
            semantic_results = await self.vector_backend.search(query, limit * 2)
            for memory in semantic_results:
                if memory_type and memory.memory_type != memory_type:
                    continue
                if tags and not any(tag in memory.tags for tag in tags):
                    continue
                results.append(memory)
        
        # 关键词搜索（补充）
        if len(results) < limit:
            keyword_results = await self.file_backend.search(query, limit)
            for memory in keyword_results:
                if memory.id not in [r.id for r in results]:
                    if memory_type and memory.memory_type != memory_type:
                        continue
                    if tags and not any(tag in memory.tags for tag in tags):
                        continue
                    results.append(memory)
        
        # 按权重排序
        results.sort(key=lambda x: x.weight, reverse=True)
        
        return [r.to_dict() for r in results[:limit]]
    
    async def reinforce_memory(self, memory_id: str, strength: float = 0.5) -> bool:
        """强化记忆"""
        memory = await self.file_backend.retrieve(memory_id)
        if memory:
            memory.reinforce(strength)
            await self.file_backend.store(memory)
            self.stats["total_reinforcements"] += 1
            logger.info(f"记忆已强化: {memory_id}, 新权重: {memory.weight}")
            return True
        return False
    
    async def connect_memories(self, memory_id1: str, memory_id2: str) -> bool:
        """建立记忆关联"""
        memory1 = await self.file_backend.retrieve(memory_id1)
        memory2 = await self.file_backend.retrieve(memory_id2)
        
        if memory1 and memory2:
            if memory_id2 not in memory1.connections:
                memory1.connections.append(memory_id2)
            if memory_id1 not in memory2.connections:
                memory2.connections.append(memory_id1)
            
            await self.file_backend.store(memory1)
            await self.file_backend.store(memory2)
            
            # 更新关联图
            if memory_id1 not in self.connection_graph:
                self.connection_graph[memory_id1] = []
            if memory_id2 not in self.connection_graph[memory_id1]:
                self.connection_graph[memory_id1].append(memory_id2)
            
            if memory_id2 not in self.connection_graph:
                self.connection_graph[memory_id2] = []
            if memory_id1 not in self.connection_graph[memory_id2]:
                self.connection_graph[memory_id2].append(memory_id1)
            
            logger.info(f"记忆关联已建立: {memory_id1} <-> {memory_id2}")
            return True
        return False
    
    async def get_related_memories(self, memory_id: str, depth: int = 1) -> List[Dict[str, Any]]:
        """获取关联记忆"""
        related_ids = set()
        current_level = {memory_id}
        
        for _ in range(depth):
            next_level = set()
            for mid in current_level:
                if mid in self.connection_graph:
                    for conn_id in self.connection_graph[mid]:
                        if conn_id not in related_ids and conn_id != memory_id:
                            related_ids.add(conn_id)
                            next_level.add(conn_id)
            current_level = next_level
        
        related_memories = []
        for rid in related_ids:
            memory = await self.file_backend.retrieve(rid)
            if memory:
                related_memories.append(memory.to_dict())
        
        return related_memories
    
    async def decay_memories(self, force: bool = False) -> int:
        """
        执行记忆衰减（遗忘）
        
        Args:
            force: 是否强制执行衰减
        
        Returns:
            遗忘的记忆数量
        """
        forgotten_count = 0
        to_forget = []
        
        for memory_id, memory in self.file_backend.memories.items():
            if force or (datetime.now() - datetime.fromisoformat(memory.last_accessed)).days > 7:
                should_forget = memory.decay()
                if should_forget:
                    to_forget.append(memory_id)
        
        for memory_id in to_forget:
            await self.file_backend.delete(memory_id)
            await self.vector_backend.delete(memory_id)
            forgotten_count += 1
        
        self.stats["total_forgettings"] += forgotten_count
        logger.info(f"记忆衰减完成，遗忘 {forgotten_count} 条记忆")
        
        return forgotten_count
    
    async def consolidate_memories(self) -> int:
        """
        记忆巩固 - 将高频访问的短期记忆转为长期记忆
        模拟人类睡眠时的记忆巩固过程
        """
        consolidated_count = 0
        
        short_term_ids = self.type_index[MemoryType.SHORT_TERM.value].copy()
        
        for memory_id in short_term_ids:
            memory = await self.file_backend.retrieve(memory_id)
            if memory and memory.access_count >= 3 and memory.weight >= 2.0:
                memory.memory_type = MemoryType.LONG_TERM.value
                memory.priority = max(memory.priority - 1, 0)
                memory.decay_rate = memory.decay_rate * 0.5
                
                await self.file_backend.store(memory)
                
                self.type_index[MemoryType.SHORT_TERM.value].remove(memory_id)
                self.type_index[MemoryType.LONG_TERM.value].append(memory_id)
                
                consolidated_count += 1
        
        logger.info(f"记忆巩固完成，转化 {consolidated_count} 条短期记忆为长期记忆")
        return consolidated_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        type_counts = {t: len(ids) for t, ids in self.type_index.items()}
        
        return {
            "total_memories": self.stats["total_memories"],
            "by_type": type_counts,
            "total_tags": len(self.tag_index),
            "total_connections": len(self.connection_graph),
            "total_accesses": self.stats["total_accesses"],
            "total_reinforcements": self.stats["total_reinforcements"],
            "total_forgettings": self.stats["total_forgettings"],
            "vector_backend_available": self.vector_backend.available
        }
    
    async def export_memories(self, output_path: str) -> bool:
        """导出记忆到文件"""
        try:
            data = {
                "memories": {mid: m.to_dict() for mid, m in self.file_backend.memories.items()},
                "connection_graph": self.connection_graph,
                "stats": self.stats,
                "exported_at": datetime.now().isoformat()
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"记忆已导出到: {output_path}")
            return True
        except Exception as e:
            logger.error(f"导出记忆失败: {e}")
            return False
    
    async def import_memories(self, input_path: str) -> int:
        """从文件导入记忆"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            imported_count = 0
            for memory_id, memory_data in data.get("memories", {}).items():
                if memory_id not in self.file_backend.memories:
                    memory = MemoryNode(**memory_data)
                    await self.file_backend.store(memory)
                    await self.vector_backend.store(memory)
                    imported_count += 1
            
            self._rebuild_index()
            logger.info(f"成功导入 {imported_count} 条记忆")
            return imported_count
            
        except Exception as e:
            logger.error(f"导入记忆失败: {e}")
            return 0


# 全局实例
_unified_memory_system = None


def get_unified_memory_system(config: Dict = None) -> UnifiedMemorySystem:
    """获取统一记忆系统实例"""
    global _unified_memory_system
    
    if _unified_memory_system is None:
        _unified_memory_system = UnifiedMemorySystem(config)
    
    return _unified_memory_system
