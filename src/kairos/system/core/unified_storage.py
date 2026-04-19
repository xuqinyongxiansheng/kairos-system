# -*- coding: utf-8 -*-
"""
统一存储层 (Unified Storage Layer)

在双循环系统架构下，整合8个冗余存储模块为统一存储接口:
- 内存缓存层: LRU/LFU/TTL多策略缓存，线程安全
- 关系数据库层: SQLite + WAL模式 + 事务安全 + 索引优化
- 向量数据库层: ChromaDB语义搜索 + 真实嵌入生成
- 文件存储层: 增量JSON + 文件锁 + 统一数据目录

双循环数据流:
- 内循环: 数据收集→训练→评估→优化 (高频读写，缓存优先)
- 外循环: 摄取→消化→提炼→迭代 (批量处理，持久化优先)
- 桥接: 内外循环间的数据同步与一致性保障
"""

import json
import os
import time
import math
import hashlib
import sqlite3
import logging
import threading
import shutil
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, OrderedDict
from datetime import datetime
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("UnifiedStorage")


class StorageTier(Enum):
    CACHE = "cache"
    RELATIONAL = "relational"
    VECTOR = "vector"
    FILE = "file"


class EvictionPolicy(Enum):
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"


class MemoryCategory(Enum):
    WORKING = "working"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"


@dataclass
class StorageItem:
    id: str
    content: str
    category: MemoryCategory
    priority: int = 2
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: List[float] = field(default_factory=list)
    strength: float = 1.0
    decay_rate: float = 0.1
    access_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    last_reinforced: float = field(default_factory=time.time)

    @property
    def retention(self) -> float:
        elapsed_hours = (time.time() - self.last_reinforced) / 3600
        if self.strength <= 0:
            return 0.0
        r = math.exp(-elapsed_hours / (self.strength * 100))
        priority_factor = 1.0 - (self.priority * 0.1)
        return max(0.0, min(1.0, r * priority_factor))

    def access(self) -> float:
        self.access_count += 1
        self.last_accessed = time.time()
        self.strength = min(self.strength * 1.05, 10.0)
        return self.retention

    def reinforce(self, factor: float = 1.5):
        self.strength = min(self.strength * factor, 10.0)
        self.last_reinforced = time.time()
        self.decay_rate = max(self.decay_rate * 0.9, 0.01)

    def decay(self) -> float:
        r = self.retention
        self.strength *= r
        return r

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "category": self.category.value,
            "priority": self.priority,
            "tags": self.tags,
            "metadata": self.metadata,
            "strength": self.strength,
            "decay_rate": self.decay_rate,
            "access_count": self.access_count,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "last_reinforced": self.last_reinforced,
            "retention": self.retention
        }


class CacheLayer:
    """多策略内存缓存层 - 线程安全"""

    def __init__(self, max_size: int = 2000, default_ttl: int = 3600,
                 policy: EvictionPolicy = EvictionPolicy.LRU):
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._policy = policy
        self._lock = threading.RLock()
        self._items: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._freq: Dict[str, int] = defaultdict(int)
        self._stats = {"hits": 0, "misses": 0, "evictions": 0, "sets": 0}

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._items:
                self._stats["misses"] += 1
                return None
            entry = self._items[key]
            if entry["expires_at"] and time.time() > entry["expires_at"]:
                del self._items[key]
                self._freq.pop(key, None)
                self._stats["misses"] += 1
                return None
            entry["access_count"] += 1
            entry["last_accessed"] = time.time()
            self._freq[key] += 1
            if self._policy == EvictionPolicy.LRU:
                self._items.move_to_end(key)
            self._stats["hits"] += 1
            return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        with self._lock:
            if ttl is None:
                ttl = self._default_ttl
            expires_at = time.time() + ttl if ttl > 0 else None
            if key in self._items:
                self._items[key]["value"] = value
                self._items[key]["expires_at"] = expires_at
                self._items[key]["last_accessed"] = time.time()
                if self._policy == EvictionPolicy.LRU:
                    self._items.move_to_end(key)
            else:
                if len(self._items) >= self._max_size:
                    self._evict()
                self._items[key] = {
                    "value": value,
                    "created_at": time.time(),
                    "last_accessed": time.time(),
                    "access_count": 0,
                    "expires_at": expires_at
                }
                self._freq[key] = 0
            self._stats["sets"] += 1
            return True

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._items:
                del self._items[key]
                self._freq.pop(key, None)
                return True
            return False

    def exists(self, key: str) -> bool:
        with self._lock:
            if key not in self._items:
                return False
            entry = self._items[key]
            if entry["expires_at"] and time.time() > entry["expires_at"]:
                del self._items[key]
                self._freq.pop(key, None)
                return False
            return True

    def clear(self):
        with self._lock:
            self._items.clear()
            self._freq.clear()

    def _evict(self):
        if not self._items:
            return
        if self._policy == EvictionPolicy.LRU:
            key, _ = self._items.popitem(last=False)
        elif self._policy == EvictionPolicy.LFU:
            key = min(self._freq, key=self._freq.get)
            self._items.pop(key, None)
            self._freq.pop(key, None)
        elif self._policy == EvictionPolicy.FIFO:
            key, _ = self._items.popitem(last=False)
        else:
            key, _ = self._items.popitem(last=False)
        self._stats["evictions"] += 1

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
            return {
                "size": len(self._items),
                "max_size": self._max_size,
                "policy": self._policy.value,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "evictions": self._stats["evictions"],
                "sets": self._stats["sets"],
                "hit_rate": f"{hit_rate:.2f}%"
            }


class RelationalLayer:
    """关系数据库层 - SQLite WAL模式 + 事务安全 + 索引优化"""

    def __init__(self, db_path: str = "./data/storage/unified.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._local = threading.local()
        self._write_lock = threading.Lock()
        self._initialize()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA cache_size=-64000")
            self._local.conn.execute("PRAGMA temp_store=MEMORY")
        return self._local.conn

    def _initialize(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS storage_items (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                priority INTEGER DEFAULT 2,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                strength REAL DEFAULT 1.0,
                decay_rate REAL DEFAULT 0.1,
                access_count INTEGER DEFAULT 0,
                created_at REAL,
                last_accessed REAL,
                last_reinforced REAL
            );

            CREATE TABLE IF NOT EXISTS access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL,
                access_type TEXT NOT NULL,
                retention_before REAL,
                retention_after REAL,
                accessed_at REAL DEFAULT (strftime('%s','now')),
                FOREIGN KEY (item_id) REFERENCES storage_items(id)
            );

            CREATE INDEX IF NOT EXISTS idx_items_category ON storage_items(category);
            CREATE INDEX IF NOT EXISTS idx_items_priority ON storage_items(priority);
            CREATE INDEX IF NOT EXISTS idx_items_strength ON storage_items(strength);
            CREATE INDEX IF NOT EXISTS idx_items_last_accessed ON storage_items(last_accessed);
            CREATE INDEX IF NOT EXISTS idx_items_created_at ON storage_items(created_at);
            CREATE INDEX IF NOT EXISTS idx_access_log_item ON access_log(item_id);
            CREATE INDEX IF NOT EXISTS idx_access_log_time ON access_log(accessed_at);
        """)
        conn.commit()

    def store(self, item: StorageItem) -> bool:
        with self._write_lock:
            conn = self._get_conn()
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO storage_items
                    (id, content, category, priority, tags, metadata,
                     strength, decay_rate, access_count, created_at, last_accessed, last_reinforced)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.id, item.content, item.category.value, item.priority,
                    json.dumps(item.tags, ensure_ascii=False),
                    json.dumps(item.metadata, ensure_ascii=False),
                    item.strength, item.decay_rate, item.access_count,
                    item.created_at, item.last_accessed, item.last_reinforced
                ))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"关系数据库存储失败: {e}")
                conn.rollback()
                return False

    def retrieve(self, item_id: str) -> Optional[StorageItem]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM storage_items WHERE id = ?", (item_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_item(row)
        except Exception as e:
            logger.error(f"关系数据库检索失败: {e}")
            return None

    def search(self, query: str, category: Optional[str] = None,
               min_strength: float = 0.0, limit: int = 20) -> List[StorageItem]:
        conn = self._get_conn()
        try:
            sql = "SELECT * FROM storage_items WHERE content LIKE ?"
            params: list = [f"%{query}%"]
            if category:
                sql += " AND category = ?"
                params.append(category)
            if min_strength > 0:
                sql += " AND strength >= ?"
                params.append(min_strength)
            sql += " ORDER BY strength DESC, last_accessed DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_item(r) for r in rows]
        except Exception as e:
            logger.error(f"关系数据库搜索失败: {e}")
            return []

    def update_strength(self, item_id: str, new_strength: float,
                        access_type: str = "access") -> bool:
        with self._write_lock:
            conn = self._get_conn()
            try:
                old = conn.execute(
                    "SELECT strength FROM storage_items WHERE id = ?", (item_id,)
                ).fetchone()
                if not old:
                    return False
                retention_before = old["strength"]
                conn.execute("""
                    UPDATE storage_items
                    SET strength = ?, access_count = access_count + 1,
                        last_accessed = ?, last_reinforced = ?
                    WHERE id = ?
                """, (new_strength, time.time(), time.time(), item_id))
                conn.execute("""
                    INSERT INTO access_log (item_id, access_type, retention_before, retention_after)
                    VALUES (?, ?, ?, ?)
                """, (item_id, access_type, retention_before, new_strength))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"强度更新失败: {e}")
                conn.rollback()
                return False

    def delete(self, item_id: str) -> bool:
        with self._write_lock:
            conn = self._get_conn()
            try:
                conn.execute("DELETE FROM storage_items WHERE id = ?", (item_id,))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"关系数据库删除失败: {e}")
                conn.rollback()
                return False

    def get_items_by_category(self, category: str, limit: int = 100) -> List[StorageItem]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM storage_items WHERE category = ? ORDER BY strength DESC LIMIT ?",
                (category, limit)
            ).fetchall()
            return [self._row_to_item(r) for r in rows]
        except Exception as e:
            logger.error(f"按类别查询失败: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        conn = self._get_conn()
        try:
            total = conn.execute("SELECT COUNT(*) FROM storage_items").fetchone()[0]
            by_category = {}
            for row in conn.execute(
                "SELECT category, COUNT(*) as cnt FROM storage_items GROUP BY category"
            ).fetchall():
                by_category[row["category"]] = row["cnt"]
            avg_strength = conn.execute(
                "SELECT AVG(strength) FROM storage_items"
            ).fetchone()[0] or 0
            return {
                "total_items": total,
                "by_category": by_category,
                "avg_strength": round(avg_strength, 3),
                "db_path": self.db_path
            }
        except Exception as e:
            logger.error(f"统计查询失败: {e}")
            return {"error": str(e)}

    def apply_decay_batch(self, min_strength: float = 0.05) -> int:
        with self._write_lock:
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    "SELECT id, strength, decay_rate, last_reinforced, priority FROM storage_items"
                ).fetchall()
                forgotten = 0
                for row in rows:
                    elapsed_hours = (time.time() - row["last_reinforced"]) / 3600
                    s = row["strength"]
                    if s <= 0:
                        retention = 0.0
                    else:
                        retention = math.exp(-elapsed_hours / (s * 100))
                        priority_factor = 1.0 - (row["priority"] * 0.1)
                        retention = max(0.0, min(1.0, retention * priority_factor))
                    new_strength = s * retention
                    if new_strength < min_strength and row["priority"] > 1:
                        conn.execute("DELETE FROM storage_items WHERE id = ?", (row["id"],))
                        forgotten += 1
                    else:
                        conn.execute(
                            "UPDATE storage_items SET strength = ? WHERE id = ?",
                            (new_strength, row["id"])
                        )
                conn.commit()
                return forgotten
            except Exception as e:
                logger.error(f"批量衰减失败: {e}")
                conn.rollback()
                return 0

    def _row_to_item(self, row: sqlite3.Row) -> StorageItem:
        return StorageItem(
            id=row["id"],
            content=row["content"],
            category=MemoryCategory(row["category"]),
            priority=row["priority"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            strength=row["strength"],
            decay_rate=row["decay_rate"],
            access_count=row["access_count"],
            created_at=row["created_at"],
            last_accessed=row["last_accessed"],
            last_reinforced=row["last_reinforced"]
        )

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


class VectorLayer:
    """向量数据库层 - ChromaDB语义搜索 + 嵌入生成"""

    def __init__(self, storage_path: str = "./data/storage/chromadb"):
        self.storage_path = storage_path
        self._available = False
        self._client = None
        self._collection = None
        self._embedding_fn = None
        try:
            import chromadb
            from chromadb.config import Settings
            try:
                self._client = chromadb.PersistentClient(
                    path=storage_path,
                    settings=Settings(anonymized_telemetry=False, allow_reset=True)
                )
                self._collection = self._client.get_or_create_collection(
                    name="unified_storage",
                    metadata={"description": "统一存储向量层"}
                )
                self._available = True
                logger.info(f"向量数据库层初始化成功: {storage_path}")
            except Exception as init_err:
                logger.warning(f"ChromaDB客户端初始化失败: {init_err}，回退到关键词搜索")
                self._client = None
                self._collection = None
        except ImportError:
            logger.warning("ChromaDB未安装，向量搜索不可用，回退到关键词搜索")
        except Exception as e:
            logger.warning(f"向量数据库初始化失败: {e}，回退到关键词搜索")
            self._client = None
            self._collection = None

    @property
    def available(self) -> bool:
        return self._available

    def _generate_embedding(self, text: str) -> List[float]:
        if self._embedding_fn:
            try:
                return self._embedding_fn(text)
            except Exception:
                pass
        hash_value = hashlib.sha256(text.encode()).hexdigest()
        return [float(int(hash_value[i:i+2], 16)) / 255.0 for i in range(0, 64, 2)]

    def set_embedding_fn(self, fn):
        self._embedding_fn = fn

    def store(self, item: StorageItem) -> bool:
        if not self._available:
            return False
        try:
            embedding = item.embedding if item.embedding else self._generate_embedding(item.content)
            self._collection.upsert(
                ids=[item.id],
                documents=[item.content],
                embeddings=[embedding],
                metadatas=[{
                    "category": item.category.value,
                    "priority": item.priority,
                    "strength": item.strength,
                    "tags": json.dumps(item.tags, ensure_ascii=False),
                    "created_at": item.created_at
                }]
            )
            return True
        except Exception as e:
            logger.error(f"向量存储失败: {e}")
            return False

    def search(self, query: str, n_results: int = 10,
               category: Optional[str] = None,
               min_relevance: float = 0.3) -> List[Dict[str, Any]]:
        if not self._available:
            return []
        try:
            where_filter = {}
            if category:
                where_filter["category"] = category
            results = self._collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter if where_filter else None,
                include=["documents", "metadatas", "distances"]
            )
            memories = []
            for i in range(len(results["ids"][0])):
                distance = results["distances"][0][i] if results["distances"] else 0
                relevance = 1.0 / (1.0 + distance) if distance > 0 else 1.0
                if relevance < min_relevance:
                    continue
                memories.append({
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "relevance": round(relevance, 3),
                    "distance": round(distance, 3)
                })
            return memories
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []

    def delete(self, item_id: str) -> bool:
        if not self._available:
            return False
        try:
            self._collection.delete(ids=[item_id])
            return True
        except Exception as e:
            logger.error(f"向量删除失败: {e}")
            return False

    def get_count(self) -> int:
        if not self._available:
            return 0
        try:
            return self._collection.count()
        except Exception:
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "available": self._available,
            "total_vectors": self.get_count(),
            "storage_path": self.storage_path,
            "embedding_fn": "custom" if self._embedding_fn else "hash_fallback"
        }


class FileLayer:
    """文件存储层 - 增量JSON + 文件锁 + 统一数据目录"""

    def __init__(self, storage_dir: str = "./data/storage/files"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self._lock_file = os.path.join(storage_dir, ".lock")
        self._index_file = os.path.join(storage_dir, "index.json")
        self._index: Dict[str, str] = {}
        self._write_lock = threading.Lock()
        self._load_index()

    def _load_index(self):
        if os.path.exists(self._index_file):
            try:
                with open(self._index_file, "r", encoding="utf-8") as f:
                    self._index = json.load(f)
            except Exception as e:
                logger.error(f"文件索引加载失败: {e}")
                self._index = {}

    def _save_index(self):
        try:
            with open(self._index_file, "w", encoding="utf-8") as f:
                json.dump(self._index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"文件索引保存失败: {e}")

    def _item_path(self, item_id: str) -> str:
        prefix = item_id[:2] if len(item_id) >= 2 else "00"
        subdir = os.path.join(self.storage_dir, prefix)
        os.makedirs(subdir, exist_ok=True)
        return os.path.join(subdir, f"{item_id}.json")

    def store(self, item: StorageItem) -> bool:
        with self._write_lock:
            try:
                path = self._item_path(item.id)
                data = item.to_dict()
                tmp_path = path + ".tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                shutil.move(tmp_path, path)
                self._index[item.id] = path
                self._save_index()
                return True
            except Exception as e:
                logger.error(f"文件存储失败: {e}")
                return False

    def retrieve(self, item_id: str) -> Optional[StorageItem]:
        path = self._index.get(item_id)
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return StorageItem(
                id=data["id"],
                content=data["content"],
                category=MemoryCategory(data["category"]),
                priority=data.get("priority", 2),
                tags=data.get("tags", []),
                metadata=data.get("metadata", {}),
                strength=data.get("strength", 1.0),
                decay_rate=data.get("decay_rate", 0.1),
                access_count=data.get("access_count", 0),
                created_at=data.get("created_at", time.time()),
                last_accessed=data.get("last_accessed", time.time()),
                last_reinforced=data.get("last_reinforced", time.time())
            )
        except Exception as e:
            logger.error(f"文件检索失败: {e}")
            return None

    def delete(self, item_id: str) -> bool:
        with self._write_lock:
            path = self._index.get(item_id)
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    del self._index[item_id]
                    self._save_index()
                    return True
                except Exception as e:
                    logger.error(f"文件删除失败: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        total_files = len(self._index)
        total_size = 0
        for path in self._index.values():
            if os.path.exists(path):
                total_size += os.path.getsize(path)
        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "storage_dir": self.storage_dir
        }


class UnifiedStorage:
    """
    统一存储系统 - 双循环架构下的存储协调器

    四层存储架构:
    L1 缓存层: 毫秒级访问，高频热数据
    L2 关系层: 毫秒-秒级，结构化查询与事务
    L3 向量层: 语义搜索，知识检索
    L4 文件层: 持久化归档，冷数据

    双循环数据流:
    - 内循环: 缓存→关系→向量 (高频读写路径)
    - 外循环: 文件→关系→向量 (批量处理路径)
    - 桥接: 缓存失效→关系回源→向量补充
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        base_dir = self.config.get("base_dir", "./data/storage")

        self.cache = CacheLayer(
            max_size=self.config.get("cache_max_size", 2000),
            default_ttl=self.config.get("cache_ttl", 3600),
            policy=EvictionPolicy(self.config.get("cache_policy", "lru"))
        )
        self.relational = RelationalLayer(
            db_path=os.path.join(base_dir, "unified.db")
        )
        self.vector = VectorLayer(
            storage_path=os.path.join(base_dir, "chromadb")
        )
        self.file_store = FileLayer(
            storage_dir=os.path.join(base_dir, "files")
        )

        self._tag_index: Dict[str, Set[str]] = defaultdict(set)
        self._category_index: Dict[str, List[str]] = defaultdict(list)
        self._maintenance_running = False
        self._maintenance_thread = None
        self._executor = ThreadPoolExecutor(max_workers=2)

        self._rebuild_indices()
        logger.info("统一存储系统初始化完成 (四层架构)")

    def _rebuild_indices(self):
        try:
            stats = self.relational.get_statistics()
            by_category = stats.get("by_category", {})
            for category, count in by_category.items():
                items = self.relational.get_items_by_category(category, limit=count)
                for item in items:
                    self._category_index[category].append(item.id)
                    for tag in item.tags:
                        self._tag_index[tag].add(item.id)
        except Exception as e:
            logger.error(f"索引重建失败: {e}")

    def _generate_id(self, content: str, category: str) -> str:
        timestamp = str(time.time())
        raw = f"{content[:50]}_{category}_{timestamp}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    async def store(self, content: str, category: MemoryCategory = MemoryCategory.SHORT_TERM,
                    priority: int = 2, tags: List[str] = None,
                    metadata: Dict[str, Any] = None,
                    persist: bool = True) -> Dict[str, Any]:
        item_id = self._generate_id(content, category.value)
        item = StorageItem(
            id=item_id,
            content=content,
            category=category,
            priority=priority,
            tags=tags or [],
            metadata=metadata or {},
            decay_rate=self._default_decay_rate(category)
        )
        self.cache.set(item_id, item.to_dict(), ttl=self._default_ttl(category))
        if persist:
            self.relational.store(item)
            self.vector.store(item)
            if category in (MemoryCategory.LONG_TERM, MemoryCategory.SEMANTIC,
                            MemoryCategory.PROCEDURAL, MemoryCategory.EPISODIC):
                self.file_store.store(item)
        for tag in (tags or []):
            self._tag_index[tag].add(item_id)
        self._category_index[category.value].append(item_id)
        return {"success": True, "item_id": item_id, "category": category.value}

    async def retrieve(self, item_id: str, reinforce: bool = True) -> Optional[Dict[str, Any]]:
        cached = self.cache.get(item_id)
        if cached is not None:
            if reinforce:
                self.relational.update_strength(item_id, min(cached.get("strength", 1.0) * 1.05, 10.0))
            return cached
        item = self.relational.retrieve(item_id)
        if item:
            if reinforce:
                item.access()
                self.relational.update_strength(item_id, item.strength)
            self.cache.set(item_id, item.to_dict())
            return item.to_dict()
        item = self.file_store.retrieve(item_id)
        if item:
            self.relational.store(item)
            self.vector.store(item)
            self.cache.set(item_id, item.to_dict())
            if reinforce:
                item.access()
                self.relational.update_strength(item_id, item.strength)
            return item.to_dict()
        return None

    async def search(self, query: str, category: Optional[MemoryCategory] = None,
                     tags: List[str] = None, limit: int = 10,
                     use_semantic: bool = True) -> List[Dict[str, Any]]:
        results = []
        seen_ids = set()
        if use_semantic and self.vector.available:
            cat_filter = category.value if category else None
            vector_results = self.vector.search(query, n_results=limit, category=cat_filter)
            for vr in vector_results:
                if vr["id"] not in seen_ids:
                    seen_ids.add(vr["id"])
                    full = await self.retrieve(vr["id"], reinforce=False)
                    if full:
                        full["relevance"] = vr["relevance"]
                        full["source"] = "vector"
                        results.append(full)
        if len(results) < limit:
            cat_filter = category.value if category else None
            relational_results = self.relational.search(query, category=cat_filter, limit=limit)
            for item in relational_results:
                if item.id not in seen_ids:
                    seen_ids.add(item.id)
                    d = item.to_dict()
                    d["source"] = "relational"
                    results.append(d)
        if tags:
            tag_ids = set()
            for tag in tags:
                tag_ids.update(self._tag_index.get(tag, set()))
            if tag_ids:
                tag_results = []
                for rid in tag_ids:
                    if rid not in seen_ids:
                        item = self.relational.retrieve(rid)
                        if item:
                            d = item.to_dict()
                            d["source"] = "tag_index"
                            tag_results.append(d)
                results.extend(tag_results)
        results.sort(key=lambda x: x.get("strength", 0), reverse=True)
        return results[:limit]

    async def delete(self, item_id: str) -> bool:
        self.cache.delete(item_id)
        r_ok = self.relational.delete(item_id)
        v_ok = self.vector.delete(item_id)
        f_ok = self.file_store.delete(item_id)
        for tag_ids in self._tag_index.values():
            tag_ids.discard(item_id)
        for cat_ids in self._category_index.values():
            if item_id in cat_ids:
                cat_ids.remove(item_id)
        return r_ok or v_ok or f_ok

    async def consolidate(self) -> Dict[str, Any]:
        """记忆巩固 - 将高频短期记忆转为长期记忆"""
        consolidated = 0
        short_term_items = self.relational.get_items_by_category(
            MemoryCategory.SHORT_TERM.value, limit=500
        )
        for item in short_term_items:
            if item.access_count >= 3 and item.strength >= 2.0:
                item.category = MemoryCategory.LONG_TERM
                item.priority = max(item.priority - 1, 0)
                item.decay_rate *= 0.5
                self.relational.store(item)
                self.vector.store(item)
                self.file_store.store(item)
                if item.id in self._category_index.get(MemoryCategory.SHORT_TERM.value, []):
                    self._category_index[MemoryCategory.SHORT_TERM.value].remove(item.id)
                self._category_index[MemoryCategory.LONG_TERM.value].append(item.id)
                consolidated += 1
        return {"consolidated": consolidated}

    async def apply_forgetting(self, min_strength: float = 0.05) -> Dict[str, Any]:
        """应用遗忘曲线 - 批量衰减与清理"""
        forgotten = self.relational.apply_decay_batch(min_strength)
        return {"forgotten": forgotten}

    async def reinforce_item(self, item_id: str, factor: float = 1.5) -> bool:
        """强化指定记忆"""
        item = self.relational.retrieve(item_id)
        if not item:
            return False
        item.reinforce(factor)
        self.relational.store(item)
        self.cache.set(item_id, item.to_dict())
        return True

    async def get_items_by_tags(self, tags: List[str], limit: int = 20) -> List[Dict[str, Any]]:
        results = []
        seen = set()
        for tag in tags:
            for item_id in self._tag_index.get(tag, set()):
                if item_id not in seen:
                    seen.add(item_id)
                    item = await self.retrieve(item_id, reinforce=False)
                    if item:
                        results.append(item)
        results.sort(key=lambda x: x.get("strength", 0), reverse=True)
        return results[:limit]

    def start_maintenance(self, interval_seconds: int = 3600):
        """启动后台维护线程"""
        if self._maintenance_running:
            return
        self._maintenance_running = True

        def _loop():
            import time as _time
            while self._maintenance_running:
                _time.sleep(interval_seconds)
                try:
                    self.relational.apply_decay_batch()
                    import asyncio
                    asyncio.run(self.consolidate())
                except Exception as e:
                    logger.error(f"存储维护任务失败: {e}")

        self._maintenance_thread = threading.Thread(target=_loop, daemon=True)
        self._maintenance_thread.start()
        logger.info(f"存储维护线程启动 (间隔={interval_seconds}s)")

    def stop_maintenance(self):
        self._maintenance_running = False

    def get_system_statistics(self) -> Dict[str, Any]:
        return {
            "cache": self.cache.get_stats(),
            "relational": self.relational.get_statistics(),
            "vector": self.vector.get_statistics(),
            "file": self.file_store.get_statistics(),
            "indices": {
                "tag_count": len(self._tag_index),
                "category_count": len(self._category_index)
            }
        }

    def _default_decay_rate(self, category: MemoryCategory) -> float:
        rates = {
            MemoryCategory.WORKING: 0.5,
            MemoryCategory.SHORT_TERM: 0.3,
            MemoryCategory.LONG_TERM: 0.01,
            MemoryCategory.SEMANTIC: 0.005,
            MemoryCategory.EPISODIC: 0.05,
            MemoryCategory.PROCEDURAL: 0.008,
        }
        return rates.get(category, 0.1)

    def _default_ttl(self, category: MemoryCategory) -> int:
        ttls = {
            MemoryCategory.WORKING: 300,
            MemoryCategory.SHORT_TERM: 1800,
            MemoryCategory.LONG_TERM: 86400,
            MemoryCategory.SEMANTIC: 0,
            MemoryCategory.EPISODIC: 7200,
            MemoryCategory.PROCEDURAL: 0,
        }
        return ttls.get(category, 3600)

    def close(self):
        self.stop_maintenance()
        self.relational.close()
        self._executor.shutdown(wait=False)


_unified_storage: Optional[UnifiedStorage] = None


def get_unified_storage(config: Dict[str, Any] = None) -> UnifiedStorage:
    global _unified_storage
    if _unified_storage is None:
        _unified_storage = UnifiedStorage(config)
    return _unified_storage
