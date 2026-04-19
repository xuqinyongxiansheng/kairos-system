#!/usr/bin/env python3
"""
分布式缓存
实现基于Redis的分布式缓存系统
"""

import json
import time
from typing import Dict, Any, Optional, List


class DistributedCache:
    """分布式缓存"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, password: Optional[str] = None):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """连接Redis"""
        try:
            import redis
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password
            )
            # 测试连接
            self.redis_client.ping()
        except Exception as e:
            print(f"连接Redis失败: {e}")
            self.redis_client = None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        if not self.redis_client:
            return False
        
        try:
            # 序列化值
            serialized_value = json.dumps(value, ensure_ascii=False)
            if ttl:
                return self.redis_client.setex(key, ttl, serialized_value)
            else:
                return self.redis_client.set(key, serialized_value)
        except Exception:
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self.redis_client:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except Exception:
            return False
    
    def clear(self) -> bool:
        """清空缓存"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.flushdb())
        except Exception:
            return False
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.exists(key))
        except Exception:
            return False
    
    def keys(self, pattern: str = "*") -> List[str]:
        """获取键列表"""
        if not self.redis_client:
            return []
        
        try:
            return self.redis_client.keys(pattern)
        except Exception:
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        if not self.redis_client:
            return {"connected": False}
        
        try:
            info = self.redis_client.info()
            return {
                "connected": True,
                "keys": info.get("db0", {}).get("keys", 0),
                "memory_used": info.get("used_memory_human", "N/A"),
                "uptime": info.get("uptime_in_seconds", 0)
            }
        except Exception:
            return {"connected": False}


class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.local_cache = None
        self.distributed_cache = None
        self._init_caches()
    
    def _init_caches(self):
        """初始化缓存"""
        # 导入本地缓存
        from .local_cache import get_local_cache
        self.local_cache = get_local_cache()
        
        # 尝试初始化分布式缓存
        try:
            self.distributed_cache = DistributedCache()
        except Exception:
            self.distributed_cache = None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, use_distributed: bool = False) -> bool:
        """设置缓存"""
        # 先设置本地缓存
        self.local_cache.set(key, value, ttl)
        
        # 如果需要分布式缓存且可用，则设置
        if use_distributed and self.distributed_cache:
            return self.distributed_cache.set(key, value, ttl)
        
        return True
    
    def get(self, key: str, use_distributed: bool = False) -> Optional[Any]:
        """获取缓存"""
        # 先从本地缓存获取
        value = self.local_cache.get(key)
        if value is not None:
            return value
        
        # 如果需要分布式缓存且可用，则从分布式缓存获取
        if use_distributed and self.distributed_cache:
            value = self.distributed_cache.get(key)
            if value is not None:
                # 将分布式缓存的值同步到本地缓存
                self.local_cache.set(key, value)
            return value
        
        return None
    
    def delete(self, key: str, use_distributed: bool = False) -> bool:
        """删除缓存"""
        # 删除本地缓存
        self.local_cache.delete(key)
        
        # 如果需要分布式缓存且可用，则删除
        if use_distributed and self.distributed_cache:
            return self.distributed_cache.delete(key)
        
        return True
    
    def clear(self, use_distributed: bool = False) -> bool:
        """清空缓存"""
        # 清空本地缓存
        self.local_cache.clear()
        
        # 如果需要分布式缓存且可用，则清空
        if use_distributed and self.distributed_cache:
            return self.distributed_cache.clear()
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        stats = {
            "local": self.local_cache.get_stats()
        }
        
        if self.distributed_cache:
            stats["distributed"] = self.distributed_cache.get_stats()
        else:
            stats["distributed"] = {"connected": False}
        
        return stats
    
    def prewarm(self, key: str, value: Any, ttl: Optional[int] = None, use_distributed: bool = False) -> bool:
        """缓存预热"""
        # 预热本地缓存
        self.local_cache.prewarm(key, value, ttl)
        
        # 如果需要分布式缓存且可用，则预热分布式缓存
        if use_distributed and self.distributed_cache:
            return self.distributed_cache.set(key, value, ttl)
        
        return True
    
    def batch_prewarm(self, items: List[Dict[str, Any]], use_distributed: bool = False) -> int:
        """批量缓存预热"""
        # 预热本地缓存
        local_count = self.local_cache.batch_prewarm(items)
        
        # 如果需要分布式缓存且可用，则预热分布式缓存
        if use_distributed and self.distributed_cache:
            distributed_count = 0
            for item in items:
                key = item.get("key")
                value = item.get("value")
                ttl = item.get("ttl")
                if key and value is not None:
                    if self.distributed_cache.set(key, value, ttl):
                        distributed_count += 1
            return max(local_count, distributed_count)
        
        return local_count
    
    def optimize_cache(self):
        """优化缓存"""
        # 清理过期缓存
        self.clear(use_distributed=False)  # 只清理本地缓存
        
        # 可以添加其他优化策略，如缓存项优先级调整等
        return True


# 全局缓存管理器实例
_cache_manager = None

def get_cache_manager() -> CacheManager:
    """获取缓存管理器实例"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


if __name__ == "__main__":
    # 测试缓存管理器
    cache_manager = get_cache_manager()
    
    # 设置缓存
    cache_manager.set("test_key", "test_value")
    
    # 获取缓存
    value = cache_manager.get("test_key")
    print(f"缓存值: {value}")
    
    # 获取统计信息
    stats = cache_manager.get_stats()
    print(f"缓存统计: {stats}")