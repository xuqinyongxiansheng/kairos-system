#!/usr/bin/env python3
"""
统一记忆系统 (Unified Memory System)

整合5个记忆实现为统一接口：
1. memory_system.py - 工作记忆/长期记忆/情景记忆
2. unified_memory_system.py - 统一记忆接口
3. vector_memory.py - 向量语义记忆
4. chromadb_memory.py - ChromaDB向量存储
5. forgetting_curve_database.py - 遗忘曲线数据库

统一接口：
- store(content, type, priority) → memory_id
- retrieve(query, type, limit) → List[MemoryItem]
- consolidate() → 巩固记忆
- forget() → 遗忘低价值记忆
- search(query, semantic=True) → 语义搜索
"""

import math
import json
import os
import time
import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
from datetime import datetime

from kairos.system.config import settings

logger = logging.getLogger("UnifiedMemory")


class MemoryType(Enum):
    WORKING = "working"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


class MemoryPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    DISPOSABLE = 5


class MemoryStatus(Enum):
    ACTIVE = "active"
    CONSOLIDATING = "consolidating"
    ARCHIVED = "archived"
    FORGOTTEN = "forgotten"


@dataclass
class MemoryItem:
    memory_id: str
    memory_type: MemoryType
    content: str
    priority: MemoryPriority
    status: MemoryStatus
    created_at: float
    last_accessed: float
    access_count: int = 0
    importance: float = 0.5
    tags: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "importance": self.importance,
            "tags": self.tags,
            "metadata": self.metadata,
        }


class UnifiedMemorySystem:
    """
    统一记忆系统

    整合工作记忆、长期记忆、情景记忆、语义记忆
    支持记忆巩固、遗忘曲线、语义搜索
    """

    def __init__(self):
        self._working_memory: deque = deque(maxlen=settings.memory.working_memory_capacity)
        self._long_term_memory: Dict[str, MemoryItem] = {}
        self._episodic_memory: deque = deque(maxlen=settings.memory.episodic_max)
        self._semantic_index: Dict[str, List[str]] = defaultdict(list)
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)

        self._forgetting_enabled = settings.memory.forgetting_enabled
        self._forgetting_rate = settings.memory.forgetting_rate
        self._consolidation_threshold = 3

        self._stats = {
            "total_stored": 0,
            "total_retrieved": 0,
            "total_consolidated": 0,
            "total_forgotten": 0,
        }

        self._vector_available = False
        self._chromadb_available = False
        self._vector_client = None
        self._chromadb_client = None

        self._init_backends()

        logger.info(
            "统一记忆系统初始化 | 工作记忆:%d | 情景记忆:%d | 遗忘:%s",
            settings.memory.working_memory_capacity,
            settings.memory.episodic_max,
            "启用" if self._forgetting_enabled else "禁用",
        )

    def _init_backends(self):
        try:
            from kairos.system.vector_memory import VectorMemory
            self._vector_client = VectorMemory()
            self._vector_available = True
            logger.info("向量记忆后端已加载")
        except Exception as e:
            logger.info("向量记忆后端不可用: %s", e)

        try:
            from kairos.system.chromadb_memory import ChromaDBMemory
            self._chromadb_client = ChromaDBMemory()
            self._chromadb_available = True
            logger.info("ChromaDB记忆后端已加载")
        except Exception as e:
            logger.info("ChromaDB记忆后端不可用: %s", e)

    def _generate_id(self, content: str) -> str:
        return hashlib.md5(f"{content}{time.time()}".encode()).hexdigest()[:12]

    async def store(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.WORKING,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> str:
        memory_id = self._generate_id(content)
        now = time.time()

        item = MemoryItem(
            memory_id=memory_id,
            memory_type=memory_type,
            content=content,
            priority=priority,
            status=MemoryStatus.ACTIVE,
            created_at=now,
            last_accessed=now,
            tags=tags or [],
            metadata=metadata or {},
        )

        if memory_type == MemoryType.WORKING:
            self._working_memory.append(item)
        elif memory_type == MemoryType.LONG_TERM:
            self._long_term_memory[memory_id] = item
        elif memory_type == MemoryType.EPISODIC:
            self._episodic_memory.append(item)
        elif memory_type == MemoryType.SEMANTIC:
            self._long_term_memory[memory_id] = item

        for tag in (tags or []):
            self._tag_index[tag].add(memory_id)

        content_lower = content.lower()
        for word in content_lower.split():
            if len(word) > 2:
                self._semantic_index[word].append(memory_id)

        if self._vector_available and self._vector_client:
            try:
                await self._vector_client.store(memory_id, content, metadata)
            except Exception as e:
                logger.debug("向量存储失败: %s", e)

        if self._chromadb_available and self._chromadb_client:
            try:
                await self._chromadb_client.store(memory_id, content, metadata)
            except Exception as e:
                logger.debug("ChromaDB存储失败: %s", e)

        self._stats["total_stored"] += 1
        logger.debug("记忆存储: %s (%s)", memory_id, memory_type.value)
        return memory_id

    async def retrieve(
        self,
        query: str = None,
        memory_type: MemoryType = None,
        memory_id: str = None,
        tags: List[str] = None,
        limit: int = 10,
    ) -> List[MemoryItem]:
        results = []

        if memory_id:
            for item in self._long_term_memory.values():
                if item.memory_id == memory_id:
                    item.access_count += 1
                    item.last_accessed = time.time()
                    results.append(item)
                    break
            for item in self._working_memory:
                if item.memory_id == memory_id:
                    item.access_count += 1
                    results.append(item)
                    break
            self._stats["total_retrieved"] += len(results)
            return results

        candidates = []

        if memory_type == MemoryType.WORKING or memory_type is None:
            candidates.extend(self._working_memory)
        if memory_type == MemoryType.LONG_TERM or memory_type is None:
            candidates.extend(self._long_term_memory.values())
        if memory_type == MemoryType.EPISODIC or memory_type is None:
            candidates.extend(self._episodic_memory)

        if tags:
            tag_ids = set()
            for tag in tags:
                tag_ids.update(self._tag_index.get(tag, set()))
            candidates = [c for c in candidates if c.memory_id in tag_ids]

        if query:
            scored = []
            query_lower = query.lower()
            query_words = set(query_lower.split())
            for item in candidates:
                if item.status == MemoryStatus.FORGOTTEN:
                    continue
                score = 0.0
                content_lower = item.content.lower()
                for word in query_words:
                    if word in content_lower:
                        score += 1.0
                for word in query_words:
                    if word in self._semantic_index:
                        if item.memory_id in self._semantic_index[word]:
                            score += 0.5
                score += item.importance * 0.3
                score += (1.0 / max(1, item.priority.value)) * 0.2
                if score > 0:
                    scored.append((score, item))
            scored.sort(key=lambda x: x[0], reverse=True)
            results = [item for _, item in scored[:limit]]
        else:
            results = [c for c in candidates if c.status != MemoryStatus.FORGOTTEN][:limit]

        for item in results:
            item.access_count += 1
            item.last_accessed = time.time()

        self._stats["total_retrieved"] += len(results)
        return results

    async def search(self, query: str, limit: int = 5, semantic: bool = True) -> List[MemoryItem]:
        if semantic and self._vector_available and self._vector_client:
            try:
                vector_results = await self._vector_client.search(query, limit=limit)
                if vector_results:
                    memory_ids = [r.get("id") for r in vector_results if r.get("id")]
                    items = []
                    for mid in memory_ids:
                        if mid in self._long_term_memory:
                            items.append(self._long_term_memory[mid])
                    if items:
                        return items
            except Exception as e:
                logger.debug("向量搜索失败，回退到关键词: %s", e)

        if semantic and self._chromadb_available and self._chromadb_client:
            try:
                chroma_results = await self._chromadb_client.search(query, limit=limit)
                if chroma_results:
                    memory_ids = [r.get("id") for r in chroma_results if r.get("id")]
                    items = []
                    for mid in memory_ids:
                        if mid in self._long_term_memory:
                            items.append(self._long_term_memory[mid])
                    if items:
                        return items
            except Exception as e:
                logger.debug("ChromaDB搜索失败，回退到关键词: %s", e)

        return await self.retrieve(query=query, limit=limit)

    async def consolidate(self) -> int:
        consolidated = 0
        working_items = list(self._working_memory)

        for item in working_items:
            if item.access_count >= self._consolidation_threshold or item.priority.value <= 2:
                lt_item = MemoryItem(
                    memory_id=item.memory_id,
                    memory_type=MemoryType.LONG_TERM,
                    content=item.content,
                    priority=item.priority,
                    status=MemoryStatus.ACTIVE,
                    created_at=item.created_at,
                    last_accessed=item.last_accessed,
                    access_count=item.access_count,
                    importance=min(1.0, item.importance + 0.2),
                    tags=item.tags,
                    metadata=item.metadata,
                )
                self._long_term_memory[item.memory_id] = lt_item
                consolidated += 1

        self._stats["total_consolidated"] += consolidated
        if consolidated > 0:
            logger.info("记忆巩固完成: %d条工作记忆→长期记忆", consolidated)
        return consolidated

    async def forget(self) -> int:
        if not self._forgetting_enabled:
            return 0

        forgotten = 0
        now = time.time()

        to_remove = []
        for mid, item in self._long_term_memory.items():
            if item.status == MemoryStatus.FORGOTTEN:
                continue
            elapsed = now - item.last_accessed
            retention = math.exp(-self._forgetting_rate * elapsed / 86400)
            if item.access_count > 0:
                retention *= min(1.0, item.access_count * 0.1)
            if retention < 0.1 and item.priority.value >= 4:
                item.status = MemoryStatus.FORGOTTEN
                to_remove.append(mid)
                forgotten += 1

        for mid in to_remove:
            self._long_term_memory.pop(mid, None)

        self._stats["total_forgotten"] += forgotten
        if forgotten > 0:
            logger.info("遗忘处理完成: %d条低价值记忆", forgotten)
        return forgotten

    async def update(self, memory_id: str, **kwargs) -> bool:
        item = self._long_term_memory.get(memory_id)
        if not item:
            for wm in self._working_memory:
                if wm.memory_id == memory_id:
                    item = wm
                    break
        if not item:
            return False

        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)
        item.last_accessed = time.time()
        return True

    async def delete(self, memory_id: str) -> bool:
        if memory_id in self._long_term_memory:
            del self._long_term_memory[memory_id]
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "working_memory_count": len(self._working_memory),
            "long_term_memory_count": len(self._long_term_memory),
            "episodic_memory_count": len(self._episodic_memory),
            "vector_available": self._vector_available,
            "chromadb_available": self._chromadb_available,
            **self._stats,
        }

    def clear(self, memory_type: MemoryType = None):
        if memory_type == MemoryType.WORKING or memory_type is None:
            self._working_memory.clear()
        if memory_type == MemoryType.LONG_TERM or memory_type is None:
            self._long_term_memory.clear()
        if memory_type == MemoryType.EPISODIC or memory_type is None:
            self._episodic_memory.clear()


_unified_memory: Optional[UnifiedMemorySystem] = None


def get_unified_memory() -> UnifiedMemorySystem:
    global _unified_memory
    if _unified_memory is None:
        _unified_memory = UnifiedMemorySystem()
    return _unified_memory
