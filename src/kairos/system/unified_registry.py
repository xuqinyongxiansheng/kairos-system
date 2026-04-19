"""
统一注册表系统 - 整合CLI-Anything的注册表和缓存模式

设计模式来源:
- cli_hub/registry.py: TTL缓存注册表
- cli_hub/installer.py: 安装状态管理

核心特性:
1. 远程数据获取与本地缓存
2. TTL过期机制
3. 搜索和过滤功能
4. 分类管理
5. 离线模式支持
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

T = TypeVar('T')


class CacheStrategy(Enum):
    """缓存策略枚举"""
    TTL = "ttl"
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"


class RegistrySource(Enum):
    """注册表数据源"""
    LOCAL = "local"
    REMOTE = "remote"
    HYBRID = "hybrid"


@dataclass
class CacheEntry(Generic[T]):
    """缓存条目"""
    data: T
    cached_at: float
    expires_at: float
    hit_count: int = 0
    size: int = 0
    etag: Optional[str] = None
    
    def is_expired(self) -> bool:
        return time.time() > self.expires_at
    
    def touch(self) -> None:
        self.hit_count += 1


@dataclass
class RegistryConfig:
    """注册表配置"""
    cache_dir: str = ""
    cache_ttl: int = 3600
    max_cache_size: int = 1000
    cache_strategy: CacheStrategy = CacheStrategy.TTL
    source: RegistrySource = RegistrySource.HYBRID
    remote_url: str = ""
    enable_offline_mode: bool = True
    auto_refresh: bool = True
    refresh_interval: int = 1800


@dataclass
class RegistryItem:
    """注册表条目"""
    id: str
    name: str
    version: str
    description: str = ""
    category: str = "uncategorized"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def matches_query(self, query: str) -> bool:
        """检查是否匹配查询"""
        query_lower = query.lower()
        return (
            query_lower in self.name.lower() or
            query_lower in self.description.lower() or
            query_lower in self.category.lower() or
            any(query_lower in tag.lower() for tag in self.tags)
        )


class UnifiedCache(Generic[T]):
    """
    统一缓存系统
    
    支持多种缓存策略: TTL, LRU, LFU, FIFO
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 3600,
        strategy: CacheStrategy = CacheStrategy.TTL
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.strategy = strategy
        self._cache: Dict[str, CacheEntry[T]] = {}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[T]:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            
            if self.strategy == CacheStrategy.TTL and entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None
            
            entry.touch()
            self._hits += 1
            return entry.data
    
    def set(
        self,
        key: str,
        value: T,
        ttl: Optional[int] = None,
        etag: Optional[str] = None
    ) -> None:
        """设置缓存值"""
        with self._lock:
            now = time.time()
            ttl = ttl or self.default_ttl
            
            size = len(json.dumps(value, default=str)) if isinstance(value, (dict, list)) else 1
            
            entry = CacheEntry(
                data=value,
                cached_at=now,
                expires_at=now + ttl,
                size=size,
                etag=etag
            )
            
            if len(self._cache) >= self.max_size:
                self._evict()
            
            self._cache[key] = entry
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
    
    def _evict(self) -> None:
        """根据策略淘汰缓存"""
        if not self._cache:
            return
        
        if self.strategy == CacheStrategy.LRU:
            key = min(self._cache.keys(), key=lambda k: self._cache[k].hit_count)
        elif self.strategy == CacheStrategy.LFU:
            key = min(self._cache.keys(), key=lambda k: self._cache[k].hit_count)
        elif self.strategy == CacheStrategy.FIFO:
            key = min(self._cache.keys(), key=lambda k: self._cache[k].cached_at)
        else:
            key = min(self._cache.keys(), key=lambda k: self._cache[k].expires_at)
        
        del self._cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0
            
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "strategy": self.strategy.value
            }


class UnifiedRegistry(Generic[T]):
    """
    统一注册表系统
    
    整合了CLI-Anything中的注册表模式:
    - 远程数据获取与本地缓存
    - TTL过期机制
    - 搜索和过滤功能
    - 分类管理
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[RegistryConfig] = None,
        fetcher: Optional[Callable[[], T]] = None
    ):
        self.name = name
        self.config = config or RegistryConfig()
        self._fetcher = fetcher
        self._cache = UnifiedCache(
            max_size=self.config.max_cache_size,
            default_ttl=self.config.cache_ttl,
            strategy=self.config.cache_strategy
        )
        self._items: Dict[str, RegistryItem] = {}
        self._categories: Dict[str, List[str]] = {}
        self._lock = threading.RLock()
        self._last_fetch: Optional[float] = None
        self._etag: Optional[str] = None
        
        if self.config.cache_dir:
            self._cache_dir = Path(self.config.cache_dir)
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            self._cache_dir = None
        
        self._load_from_local()
    
    def _get_cache_path(self) -> Optional[Path]:
        """获取缓存文件路径"""
        if not self._cache_dir:
            return None
        return self._cache_dir / f"{self.name}_registry.json"
    
    def _compute_etag(self, data: Any) -> str:
        """计算数据ETag"""
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(content.encode()).hexdigest()
    
    def _load_from_local(self) -> bool:
        """从本地加载缓存"""
        cache_path = self._get_cache_path()
        if not cache_path or not cache_path.exists():
            return False
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            
            cached_at = cached.get("_cached_at", 0)
            if time.time() - cached_at > self.config.cache_ttl:
                return False
            
            self._etag = cached.get("_etag")
            self._last_fetch = cached_at
            
            items_data = cached.get("items", {})
            for item_id, item_data in items_data.items():
                self._items[item_id] = self._parse_item(item_data)
            
            self._rebuild_categories()
            return True
            
        except (json.JSONDecodeError, IOError):
            return False
    
    def _save_to_local(self) -> bool:
        """保存到本地缓存"""
        cache_path = self._get_cache_path()
        if not cache_path:
            return False
        
        try:
            items_data = {
                item_id: self._serialize_item(item)
                for item_id, item in self._items.items()
            }
            
            cached = {
                "_cached_at": time.time(),
                "_etag": self._etag,
                "items": items_data
            }
            
            temp_path = cache_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(cached, f, indent=2, ensure_ascii=False)
            
            if cache_path.exists():
                cache_path.unlink()
            temp_path.rename(cache_path)
            
            return True
            
        except (IOError, json.JSONEncodeError):
            return False
    
    def _parse_item(self, data: Dict[str, Any]) -> RegistryItem:
        """解析条目数据"""
        return RegistryItem(
            id=data.get("id", ""),
            name=data.get("name", ""),
            version=data.get("version", ""),
            description=data.get("description", ""),
            category=data.get("category", "uncategorized"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None
        )
    
    def _serialize_item(self, item: RegistryItem) -> Dict[str, Any]:
        """序列化条目"""
        return {
            "id": item.id,
            "name": item.name,
            "version": item.version,
            "description": item.description,
            "category": item.category,
            "tags": item.tags,
            "metadata": item.metadata,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None
        }
    
    def _rebuild_categories(self) -> None:
        """重建分类索引"""
        self._categories.clear()
        for item in self._items.values():
            if item.category not in self._categories:
                self._categories[item.category] = []
            self._categories[item.category].append(item.id)
    
    def fetch(self, force_refresh: bool = False) -> bool:
        """
        获取注册表数据
        
        Args:
            force_refresh: 是否强制刷新
            
        Returns:
            是否成功获取
        """
        if not force_refresh and self._last_fetch:
            if time.time() - self._last_fetch < self.config.cache_ttl:
                return True
        
        if not self._fetcher:
            return self._load_from_local()
        
        try:
            data = self._fetcher()
            
            new_etag = self._compute_etag(data)
            if new_etag == self._etag and not force_refresh:
                return True
            
            self._etag = new_etag
            self._last_fetch = time.time()
            
            if isinstance(data, dict):
                items_data = data.get("items", data)
            elif isinstance(data, list):
                items_data = {item.get("id", str(i)): item for i, item in enumerate(data)}
            else:
                return False
            
            self._items.clear()
            for item_id, item_data in items_data.items():
                if isinstance(item_data, dict):
                    item_data["id"] = item_data.get("id", item_id)
                    self._items[item_id] = self._parse_item(item_data)
            
            self._rebuild_categories()
            self._save_to_local()
            
            return True
            
        except Exception:
            if self.config.enable_offline_mode:
                return self._load_from_local()
            return False
    
    def get(self, item_id: str) -> Optional[RegistryItem]:
        """获取单个条目"""
        with self._lock:
            return self._items.get(item_id)
    
    def get_by_name(self, name: str) -> Optional[RegistryItem]:
        """按名称获取条目"""
        with self._lock:
            for item in self._items.values():
                if item.name == name:
                    return item
            return None
    
    def list_all(self) -> List[RegistryItem]:
        """列出所有条目"""
        with self._lock:
            return list(self._items.values())
    
    def list_by_category(self, category: str) -> List[RegistryItem]:
        """按分类列出条目"""
        with self._lock:
            ids = self._categories.get(category, [])
            return [self._items[id_] for id_ in ids if id_ in self._items]
    
    def get_categories(self) -> List[str]:
        """获取所有分类"""
        with self._lock:
            return list(self._categories.keys())
    
    def search(self, query: str) -> List[RegistryItem]:
        """搜索条目"""
        with self._lock:
            return [
                item for item in self._items.values()
                if item.matches_query(query)
            ]
    
    def filter(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        version: Optional[str] = None
    ) -> List[RegistryItem]:
        """过滤条目"""
        with self._lock:
            results = list(self._items.values())
            
            if category:
                results = [r for r in results if r.category == category]
            
            if tags:
                results = [
                    r for r in results
                    if any(tag in r.tags for tag in tags)
                ]
            
            if version:
                results = [r for r in results if r.version == version]
            
            return results
    
    def add(self, item: RegistryItem) -> bool:
        """添加条目"""
        with self._lock:
            if item.id in self._items:
                return False
            
            self._items[item.id] = item
            
            if item.category not in self._categories:
                self._categories[item.category] = []
            self._categories[item.category].append(item.id)
            
            self._save_to_local()
            return True
    
    def update(self, item: RegistryItem) -> bool:
        """更新条目"""
        with self._lock:
            if item.id not in self._items:
                return False
            
            old_item = self._items[item.id]
            if old_item.category != item.category:
                if old_item.category in self._categories:
                    self._categories[old_item.category].remove(item.id)
                if item.category not in self._categories:
                    self._categories[item.category] = []
                self._categories[item.category].append(item.id)
            
            item.updated_at = datetime.now(timezone.utc)
            self._items[item.id] = item
            
            self._save_to_local()
            return True
    
    def remove(self, item_id: str) -> bool:
        """移除条目"""
        with self._lock:
            if item_id not in self._items:
                return False
            
            item = self._items.pop(item_id)
            if item.category in self._categories:
                self._categories[item.category].remove(item_id)
            
            self._save_to_local()
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "name": self.name,
                "total_items": len(self._items),
                "total_categories": len(self._categories),
                "categories": {
                    cat: len(ids) for cat, ids in self._categories.items()
                },
                "last_fetch": self._last_fetch,
                "etag": self._etag,
                "cache_stats": self._cache.get_stats()
            }


class RegistryFactory:
    """
    注册表工厂
    
    用于创建和管理多个注册表实例
    """
    
    _registries: Dict[str, UnifiedRegistry] = {}
    _lock = threading.Lock()
    
    @classmethod
    def create(
        cls,
        name: str,
        config: Optional[RegistryConfig] = None,
        fetcher: Optional[Callable] = None
    ) -> UnifiedRegistry:
        """创建注册表"""
        with cls._lock:
            if name in cls._registries:
                return cls._registries[name]
            
            registry = UnifiedRegistry(name, config, fetcher)
            cls._registries[name] = registry
            return registry
    
    @classmethod
    def get(cls, name: str) -> Optional[UnifiedRegistry]:
        """获取注册表"""
        return cls._registries.get(name)
    
    @classmethod
    def remove(cls, name: str) -> bool:
        """移除注册表"""
        with cls._lock:
            if name in cls._registries:
                del cls._registries[name]
                return True
            return False
    
    @classmethod
    def list_all(cls) -> List[str]:
        """列出所有注册表"""
        return list(cls._registries.keys())
