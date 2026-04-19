#!/usr/bin/env python3
"""
本地缓存
实现本地缓存系统
"""

import json
import os
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta


class LocalCache:
    """本地缓存"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.eviction_policy = "lru"  # lru, fifo, lfu
        self.access_patterns: Dict[str, List[float]] = {}  # 存储访问时间模式
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        # 检查缓存大小
        if len(self.cache) >= self.max_size:
            self._evict()
        
        # 动态调整TTL
        ttl = self._dynamic_ttl(key, ttl)
        
        # 设置缓存
        self.cache[key] = {
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl,
            "access_count": 0,
            "last_access": time.time()
        }
        
        # 初始化访问模式
        if key not in self.access_patterns:
            self.access_patterns[key] = []
        
        return True
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key not in self.cache:
            return None
        
        # 检查是否过期
        item = self.cache[key]
        if time.time() > item["timestamp"] + item["ttl"]:
            del self.cache[key]
            if key in self.access_patterns:
                del self.access_patterns[key]
            return None
        
        # 更新访问计数和时间戳
        item["access_count"] += 1
        item["last_access"] = time.time()
        
        # 记录访问模式
        if key in self.access_patterns:
            self.access_patterns[key].append(time.time())
            # 只保留最近10次访问记录
            if len(self.access_patterns[key]) > 10:
                self.access_patterns[key] = self.access_patterns[key][-10:]
        
        return item["value"]
    
    def _dynamic_ttl(self, key: str, ttl: Optional[int] = None) -> int:
        """动态调整TTL"""
        if ttl is not None:
            return ttl
        
        # 默认TTL
        default_ttl = self.default_ttl
        
        # 根据访问模式调整TTL
        if key in self.access_patterns and len(self.access_patterns[key]) >= 2:
            # 计算平均访问间隔
            access_times = self.access_patterns[key]
            intervals = [access_times[i] - access_times[i-1] for i in range(1, len(access_times))]
            avg_interval = sum(intervals) / len(intervals)
            
            # 根据访问间隔调整TTL
            if avg_interval < 60:  # 频繁访问（小于1分钟）
                return int(avg_interval * 2)  # TTL为平均间隔的2倍
            elif avg_interval < 3600:  # 中等频率（小于1小时）
                return int(avg_interval * 1.5)  # TTL为平均间隔的1.5倍
            else:  # 低频访问
                return min(int(avg_interval), default_ttl * 2)  # 最大不超过默认TTL的2倍
        
        return default_ttl
    
    def prewarm(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """缓存预热"""
        return self.set(key, value, ttl)
    
    def batch_prewarm(self, items: List[Dict[str, Any]]) -> int:
        """批量缓存预热"""
        count = 0
        for item in items:
            key = item.get("key")
            value = item.get("value")
            ttl = item.get("ttl")
            if key and value is not None:
                if self.prewarm(key, value, ttl):
                    count += 1
        return count
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self) -> bool:
        """清空缓存"""
        self.cache.clear()
        return True
    
    def size(self) -> int:
        """获取缓存大小"""
        self._clean_expired()
        return len(self.cache)
    
    def _evict(self):
        """驱逐缓存"""
        if not self.cache:
            return
        
        if self.eviction_policy == "lru":
            # 最少最近使用
            lru_key = min(self.cache, key=lambda k: self.cache[k]["timestamp"])
        elif self.eviction_policy == "fifo":
            # 先进先出
            fifo_key = min(self.cache, key=lambda k: self.cache[k]["timestamp"])
        elif self.eviction_policy == "lfu":
            # 最少使用频率
            lfu_key = min(self.cache, key=lambda k: self.cache[k]["access_count"])
        else:
            # 默认LRU
            lru_key = min(self.cache, key=lambda k: self.cache[k]["timestamp"])
        
        del self.cache[lru_key]
    
    def _clean_expired(self):
        """清理过期缓存"""
        expired_keys = []
        current_time = time.time()
        
        for key, item in self.cache.items():
            if current_time > item["timestamp"] + item["ttl"]:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        self._clean_expired()
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "items": [{
                "key": key,
                "age": time.time() - item["timestamp"],
                "ttl": item["ttl"],
                "access_count": item["access_count"]
            } for key, item in self.cache.items()]
        }


class FileCache:
    """文件缓存"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_file_path(self, key: str) -> str:
        """获取文件路径"""
        import hashlib
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{key_hash}.json")
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        try:
            file_path = self._get_file_path(key)
            data = {
                "value": value,
                "timestamp": time.time(),
                "ttl": ttl
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            file_path = self._get_file_path(key)
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查是否过期
            if data.get("ttl") and time.time() > data["timestamp"] + data["ttl"]:
                os.remove(file_path)
                return None
            
            return data["value"]
        except Exception:
            return None
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            file_path = self._get_file_path(key)
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False
    
    def clear(self) -> bool:
        """清空缓存"""
        try:
            for file in os.listdir(self.cache_dir):
                if file.endswith(".json"):
                    os.remove(os.path.join(self.cache_dir, file))
            return True
        except Exception:
            return False
    
    def size(self) -> int:
        """获取缓存大小"""
        try:
            files = [f for f in os.listdir(self.cache_dir) if f.endswith(".json")]
            return len(files)
        except Exception:
            return 0


# 全局本地缓存实例
_local_cache = None

def get_local_cache() -> LocalCache:
    """获取本地缓存实例"""
    global _local_cache
    if _local_cache is None:
        _local_cache = LocalCache()
    return _local_cache


# 全局文件缓存实例
_file_cache = None

def get_file_cache() -> FileCache:
    """获取文件缓存实例"""
    global _file_cache
    if _file_cache is None:
        _file_cache = FileCache()
    return _file_cache


if __name__ == "__main__":
    # 测试本地缓存
    local_cache = get_local_cache()
    
    # 设置缓存
    local_cache.set("key1", "value1")
    local_cache.set("key2", "value2", ttl=5)
    
    # 获取缓存
    print(f"key1: {local_cache.get('key1')}")
    print(f"key2: {local_cache.get('key2')}")
    
    # 等待过期
    time.sleep(6)
    print(f"key2 after expiration: {local_cache.get('key2')}")
    
    # 测试文件缓存
    file_cache = get_file_cache()
    file_cache.set("file_key", "file_value")
    print(f"file_key: {file_cache.get('file_key')}")