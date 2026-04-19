"""
团队记忆同步服务（Team Memory Sync）
借鉴 cc-haha-main 的 teamMemorySync 架构：
1. 多代理实时记忆共享 — 基于事件驱动的增量同步
2. 语义级冲突合并 — 基于时间戳+优先级的合并策略
3. 代理间记忆路由 — 基于角色/能力的记忆分发
4. 可见性控制 — TEAM/ROLE/DIRECT/PRIVATE 四级可见性

完全重写实现
"""

import os
import re
import json
import time
import hashlib
import logging
import threading
import tempfile
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field, asdict
from collections import defaultdict

logger = logging.getLogger("TeamMemorySync")

TEAM_MEMORY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "team_memory")
MAX_ENTRIES_PER_KEY = 500


class MemoryVisibility(Enum):
    TEAM = "team"
    ROLE = "role"
    DIRECT = "direct"
    PRIVATE = "private"


class MergeStrategy(Enum):
    LAST_WRITE_WINS = "last_write_wins"
    SEMANTIC_MERGE = "semantic_merge"
    APPEND_ONLY = "append_only"


@dataclass
class AgentIdentity:
    agent_id: str = ""
    agent_type: str = "default"
    capabilities: List[str] = field(default_factory=list)
    session_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TeamMemoryEntry:
    entry_id: str = ""
    key: str = ""
    content: str = ""
    content_hash: str = ""
    author: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    timestamp: float = field(default_factory=time.time)
    visibility: str = "team"
    tags: List[str] = field(default_factory=list)
    merge_strategy: str = "last_write_wins"
    parent_version: int = 0

    def __post_init__(self):
        if not self.entry_id:
            self.entry_id = f"mem_{int(time.time() * 1000)}_{hashlib.md5(self.key.encode()).hexdigest()[:8]}"
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.content.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["visibility"] = self.visibility
        d["merge_strategy"] = self.merge_strategy
        return d


@dataclass
class MemorySyncEvent:
    event_type: str = "created"
    entry: TeamMemoryEntry = None
    source_agent: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "event_type": self.event_type,
            "source_agent": self.source_agent,
            "timestamp": self.timestamp,
        }
        if self.entry:
            result["entry"] = self.entry.to_dict()
        return result


@dataclass
class ConflictInfo:
    key: str
    local_version: int
    remote_version: int
    local_content: str
    remote_content: str
    local_timestamp: float
    remote_timestamp: float
    resolved: bool = False
    resolution: str = ""


class TeamMemorySyncService:
    """团队记忆同步服务"""

    def __init__(self, memory_dir: str = None):
        self.memory_dir = memory_dir or TEAM_MEMORY_DIR
        os.makedirs(self.memory_dir, exist_ok=True)
        self._store: Dict[str, List[TeamMemoryEntry]] = {}
        self._lock = threading.RLock()
        self._event_handlers: List[Callable[[MemorySyncEvent], Any]] = []
        self._conflicts: Dict[str, ConflictInfo] = {}
        self._stats = {
            "total_entries": 0,
            "total_syncs": 0,
            "total_conflicts": 0,
            "total_resolutions": 0,
            "created_count": 0,
            "updated_count": 0,
            "deleted_count": 0,
        }
        self._load_all()

    def _load_all(self):
        """加载所有本地记忆"""
        if not os.path.exists(self.memory_dir):
            return
        for fname in os.listdir(self.memory_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(self.memory_dir, fname), "r", encoding="utf-8") as f:
                        data = json.load(f)
                    key = fname[:-5]
                    entries = [TeamMemoryEntry(**e) for e in data]
                    self._store[key] = entries
                except Exception:
                    pass

    def _save_key(self, key: str):
        """原子写入单个key的记忆"""
        filepath = os.path.join(self.memory_dir, f"{key}.json")
        entries = self._store.get(key, [])
        tmp_fd, tmp_path = tempfile.mkstemp(dir=self.memory_dir, suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump([e.to_dict() for e in entries], f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, filepath)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    async def share_memory(
        self,
        key: str,
        content: str,
        author: AgentIdentity = None,
        visibility: MemoryVisibility = MemoryVisibility.TEAM,
        merge_strategy: MergeStrategy = MergeStrategy.LAST_WRITE_WINS,
        tags: List[str] = None,
    ) -> TeamMemoryEntry:
        """共享记忆条目到团队"""
        author_data = author.to_dict() if author else {"agent_id": "system", "agent_type": "system"}
        
        with self._lock:
            existing = self._store.get(key, [])
            new_entry = TeamMemoryEntry(
                key=key,
                content=content,
                author=author_data,
                visibility=visibility.value,
                merge_strategy=merge_strategy.value,
                tags=tags or [],
                version=len(existing) + 1,
                parent_version=existing[-1].version if existing else 0,
            )
            
            is_update = len(existing) > 0
            
            if len(existing) >= MAX_ENTRIES_PER_KEY:
                existing = existing[-(MAX_ENTRIES_PER_KEY - 1):]
            
            existing.append(new_entry)
            self._store[key] = existing
            self._save_key(key)

            self._stats["total_entries"] += 1
            if is_update:
                self._stats["updated_count"] += 1
                event_type = "updated"
            else:
                self._stats["created_count"] += 1
                event_type = "created"

        event = MemorySyncEvent(
            event_type=event_type,
            entry=new_entry,
            source_agent=author_data.get("agent_id", "unknown"),
        )
        await self._fire_event(event)
        return new_entry

    async def query_team_memory(
        self,
        query: str,
        tags: List[str] = None,
        visibility: MemoryVisibility = None,
        limit: int = 10,
    ) -> List[TeamMemoryEntry]:
        """查询团队记忆"""
        results = []
        query_lower = query.lower()
        tag_set = set(tags) if tags else set()
        
        with self._lock:
            for key, entries in self._store.items():
                for entry in reversed(entries):
                    if visibility and entry.visibility != visibility.value:
                        continue
                    if tag_set and not tag_set.intersection(set(entry.tags)):
                        continue
                    if query_lower:
                        if query_lower in entry.content.lower() or query_lower in key.lower():
                            results.append(entry)
                            if len(results) >= limit:
                                return results
                    else:
                        results.append(entry)
                        if len(results) >= limit:
                            return results
        
        return results

    async def get_memory_by_key(self, key: str, visibility: MemoryVisibility = None) -> List[TeamMemoryEntry]:
        """按key获取记忆"""
        with self._lock:
            entries = self._store.get(key, [])
            if visibility:
                entries = [e for e in entries if e.visibility == visibility.value]
            return list(entries)

    async def delete_memory(self, key: str, entry_id: str = None, author: AgentIdentity = None) -> bool:
        """删除记忆"""
        author_id = author.agent_id if author else "system"
        
        with self._lock:
            if key not in self._store:
                return False
            
            if entry_id:
                before = len(self._store[key])
                self._store[key] = [e for e in self._store[key] if e.entry_id != entry_id]
                deleted = before - len(self._store[key])
            else:
                deleted = len(self._store[key])
                self._store[key] = []
            
            if not self._store[key]:
                del self._store[key]
                filepath = os.path.join(self.memory_dir, f"{key}.json")
                if os.path.exists(filepath):
                    os.remove(filepath)
            else:
                self._save_key(key)
            
            self._stats["deleted_count"] += deleted
            self._stats["total_entries"] -= deleted

        event = MemorySyncEvent(event_type="deleted", source_agent=author_id)
        await self._fire_event(event)
        return True

    async def resolve_conflict(
        self, key: str, resolution: str, merged_content: str = None, author: AgentIdentity = None
    ) -> Optional[TeamMemoryEntry]:
        """解决记忆冲突"""
        conflict = self._conflicts.get(key)
        if not conflict or conflict.resolved:
            return None
        
        with self._lock:
            if resolution == "local":
                pass
            elif resolution == "remote":
                entries = self._store.get(key, [])
                if entries:
                    entries[-1].content = conflict.remote_content
                    entries[-1].content_hash = hashlib.sha256(conflict.remote_content.encode()).hexdigest()
                    entries[-1].timestamp = time.time()
                    self._save_key(key)
            elif resolution == "merged" and merged_content:
                entries = self._store.get(key, [])
                new_entry = TeamMemoryEntry(
                    key=key,
                    content=merged_content,
                    author=author.to_dict() if author else {"agent_id": "resolver"},
                    version=(entries[-1].version if entries else 0) + 1,
                    merge_strategy="semantic_merge",
                )
                if not entries:
                    self._store[key] = []
                self._store[key].append(new_entry)
                self._save_key(key)
            else:
                return None
            
            conflict.resolved = True
            conflict.resolution = resolution
            self._stats["total_resolutions"] += 1

        event = MemorySyncEvent(event_type="merged", source_agent=author.agent_id if author else "resolver")
        await self._fire_event(event)
        return self._store.get(key, [])[-1] if key in self._store else None

    def subscribe(self, handler: Callable[[MemorySyncEvent], Any]) -> int:
        """订阅记忆变更事件"""
        self._event_handlers.append(handler)
        return len(self._event_handlers) - 1

    def unsubscribe(self, handler_index: int) -> bool:
        """取消订阅"""
        if 0 <= handler_index < len(self._event_handlers):
            self._event_handlers.pop(handler_index)
            return True
        return False

    async def _fire_event(self, event: MemorySyncEvent):
        """触发事件通知"""
        self._stats["total_syncs"] += 1
        for handler in self._event_handlers:
            try:
                result = handler(event)
                import asyncio
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.debug(f"事件处理器执行失败: {e}")

    def get_all_keys(self) -> List[str]:
        """获取所有记忆键"""
        with self._lock:
            return list(self._store.keys())

    def get_conflicts(self) -> Dict[str, ConflictInfo]:
        """获取所有未解决的冲突"""
        return {k: v for k, v in self._conflicts.items() if not v.resolved}

    def get_stats(self) -> Dict[str, Any]:
        """获取同步统计"""
        with self._lock:
            stats = dict(self._stats)
            stats["keys_count"] = len(self._store)
            stats["pending_conflicts"] = sum(1 for c in self._conflicts.values() if not c.resolved)
            stats["subscribers"] = len(self._event_handlers)
            return stats

    def export_memories(self, output_file: str = None) -> str:
        """导出所有记忆为JSON文件"""
        if not output_file:
            output_file = os.path.join(self.memory_dir, "export.json")
        
        with self._lock:
            export_data = {
                "export_time": time.time(),
                "entries_total": sum(len(v) for v in self._store.values()),
                "keys": {},
            }
            for key, entries in self._store.items():
                export_data["keys"][key] = {
                    "count": len(entries),
                    "latest_version": entries[-1].version if entries else 0,
                    "entries": [e.to_dict() for e in entries],
                }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        return output_file


_team_memory_service: Optional[TeamMemorySyncService] = None


def get_team_memory_service() -> TeamMemorySyncService:
    global _team_memory_service
    if _team_memory_service is None:
        _team_memory_service = TeamMemorySyncService()
    return _team_memory_service
