# -*- coding: utf-8 -*-
"""
记忆系统兼容层

已迁移到 system/unified_memory_system_v2.py
此文件保留以维持向后兼容性，所有调用自动委托到统一记忆系统

使用方式（不变）：
    from kairos.system.memory_system import MemorySystem, MemoryType
    system = MemorySystem()
    mid = await system.store("内容", MemoryType.WORKING)
"""

from kairos.system.unified_memory_system_v2 import (
    UnifiedMemorySystem,
    MemoryType,
    MemoryPriority,
    MemoryStatus,
    MemoryItem,
    get_unified_memory,
)

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("memory_system")

logger.info("memory_system.py 已委托到 unified_memory_system_v2.py，向后兼容")


class MemorySystem:
    """记忆系统兼容层 - 委托到统一记忆系统"""

    def __init__(self):
        self._unified = get_unified_memory()

    async def store(self, content: str, memory_type: MemoryType = MemoryType.WORKING,
                    priority: MemoryPriority = MemoryPriority.MEDIUM,
                    tags: List[str] = None, metadata: Dict[str, Any] = None) -> str:
        return await self._unified.store(content, memory_type, priority, tags, metadata)

    async def retrieve(self, query: str = None, memory_type: MemoryType = None,
                       memory_id: str = None, tags: List[str] = None,
                       limit: int = 10) -> List[MemoryItem]:
        return await self._unified.retrieve(query, memory_type, memory_id, tags, limit)

    async def search(self, query: str, limit: int = 5, semantic: bool = True) -> List[MemoryItem]:
        return await self._unified.search(query, limit, semantic)

    async def consolidate(self) -> int:
        return await self._unified.consolidate()

    async def forget(self) -> int:
        return await self._unified.forget()

    async def update(self, memory_id: str, **kwargs) -> bool:
        return await self._unified.update(memory_id, **kwargs)

    async def delete(self, memory_id: str) -> bool:
        return await self._unified.delete(memory_id)

    def get_stats(self) -> Dict[str, Any]:
        return self._unified.get_stats()

    def clear(self, memory_type: MemoryType = None):
        self._unified.clear(memory_type)
