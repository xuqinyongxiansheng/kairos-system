"""
缓存系统
提供性能优化
"""

import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """缓存策略"""
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float
    expires_at: Optional[float] = None
    access_count: int = 0
    last_accessed: float = None
    
    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class CacheBackend:
    """缓存后端"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None
            
            entry = self.cache[key]
            
            if entry.is_expired():
                self._delete(key)
                self.misses += 1
                return None
            
            entry.access_count += 1
            entry.last_accessed = time.time()
            self.hits += 1
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        with self.lock:
            if ttl is None:
                ttl = self.default_ttl
            
            expires_at = time.time() + ttl if ttl > 0 else None
            
            if key in self.cache:
                self.cache[key].value = value
                self.cache[key].expires_at = expires_at
                self.cache[key].last_accessed = time.time()
            else:
                if len(self.cache) >= self.max_size:
                    self._evict()
                
                self.cache[key] = CacheEntry(
                    key=key,
                    value=value,
                    created_at=time.time(),
                    expires_at=expires_at
                )
            
            return True
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        with self.lock:
            return self._delete(key)
    
    def _delete(self, key: str) -> bool:
        """内部删除方法"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def _evict(self):
        """驱逐缓存"""
        if not self.cache:
            return
        
        lru_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k].last_accessed
        )
        
        self._delete(lru_key)
        self.evictions += 1
        
        logger.debug(f"Evicted cache entry: {lru_key}")
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        with self.lock:
            return key in self.cache and not self.cache[key].is_expired()
    
    def clear(self) -> bool:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            logger.info("Cache cleared")
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'evictions': self.evictions,
                'hit_rate': f"{hit_rate:.2f}%"
            }
    
    def get_size(self) -> int:
        """获取缓存大小"""
        with self.lock:
            return len(self.cache)
    
    def batch_get(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取"""
        with self.lock:
            return {
                key: self.get(key)
                for key in keys
            }
    
    def batch_set(self, items: Dict[str, Any], ttl: Optional[int] = None) -> Dict[str, bool]:
        """批量设置"""
        with self.lock:
            return {
                key: self.set(key, value, ttl)
                for key, value in items.items()
            }


class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.caches: Dict[str, CacheBackend] = {}
        self.default_cache = CacheBackend()
    
    def get_cache(self, name: str = "default") -> CacheBackend:
        """获取缓存"""
        if name not in self.caches:
            self.caches[name] = CacheBackend()
        return self.caches[name]
    
    def configure_cache(self, name: str, max_size: int = 1000, default_ttl: int = 3600):
        """配置缓存"""
        self.caches[name] = CacheBackend(max_size=max_size, default_ttl=default_ttl)
        logger.info(f"Cache configured: {name}")
    
    async def get(self, key: str, cache_name: str = "default") -> Dict[str, Any]:
        """获取缓存"""
        cache = self.get_cache(cache_name)
        value = cache.get(key)
        
        if value is not None:
            return {
                'status': 'success',
                'value': value,
                'cached': True
            }
        else:
            return {
                'status': 'not_found',
                'cached': False
            }
    
    async def set(
        self,
        key: str,
        value: Any,
        cache_name: str = "default",
        ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        """设置缓存"""
        cache = self.get_cache(cache_name)
        success = cache.set(key, value, ttl)
        
        return {
            'status': 'success' if success else 'error',
            'key': key,
            'cached': success
        }
    
    async def delete(self, key: str, cache_name: str = "default") -> Dict[str, Any]:
        """删除缓存"""
        cache = self.get_cache(cache_name)
        success = cache.delete(key)
        
        return {
            'status': 'success' if success else 'not_found',
            'key': key
        }
    
    async def get_cache_stats(self, cache_name: str = "default") -> Dict[str, Any]:
        """获取缓存统计"""
        cache = self.get_cache(cache_name)
        stats = cache.get_stats()
        
        return {
            'status': 'success',
            'cache_name': cache_name,
            'stats': stats
        }
    
    async def get_all_stats(self) -> Dict[str, Any]:
        """获取所有缓存统计"""
        stats = {}
        
        for name, cache in self.caches.items():
            stats[name] = cache.get_stats()
        
        stats['default'] = self.default_cache.get_stats()
        
        return {
            'status': 'success',
            'caches': stats,
            'total_caches': len(self.caches) + 1
        }
