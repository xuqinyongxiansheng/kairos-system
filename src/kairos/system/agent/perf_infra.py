# -*- coding: utf-8 -*-
"""
零序列化进程内缓存 + 双检锁模型缓存 + 分布式锁 + 定时GC

整合MaxKB的4项P1性能优化：
1. MemCache: 零序列化进程内缓存，直接存储对象引用
2. ModelCache: 双检锁模型实例缓存（已集成到model_provider.py）
3. DistributedLock: 分布式锁（Redis SET NX + Lua原子释放）
4. MemoryGuard: 定时GC + malloc_trim内存归还

参考: MaxKB MemCache + RedisLock + 内存管理
"""

import gc
import logging
import threading
import time
import ctypes
import os
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class MemCache:
    """
    零序列化进程内缓存。

    与Django的LocMemCache不同，不做pickle序列化，
    直接存储对象引用，避免序列化/反序列化开销。

    特性：
    - 零拷贝：直接存储对象引用
    - TTL过期：支持超时自动清理
    - 按命名空间清除：支持按应用/模块清除
    - 线程安全
    """

    def __init__(self, default_timeout: int = 3600):
        self._cache: Dict[str, tuple] = {}
        self._lock = threading.Lock()
        self._default_timeout = default_timeout
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "evictions": 0}

    def get(self, key: str) -> Any:
        """获取缓存值（零拷贝）"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats["misses"] += 1
                return None
            value, expire_at = entry
            if expire_at and time.time() > expire_at:
                del self._cache[key]
                self._stats["evictions"] += 1
                self._stats["misses"] += 1
                return None
            self._stats["hits"] += 1
            return value

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """设置缓存值（零序列化）"""
        expire_at = None
        t = timeout if timeout is not None else self._default_timeout
        if t and t > 0:
            expire_at = time.time() + t
        with self._lock:
            self._cache[key] = (value, expire_at)
            self._stats["sets"] += 1

    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear_by_prefix(self, prefix: str) -> int:
        """按前缀清除缓存"""
        with self._lock:
            keys = [k for k in self._cache if k.startswith(prefix)]
            for k in keys:
                del self._cache[k]
            return len(keys)

    def clear_expired(self) -> int:
        """清理过期缓存"""
        now = time.time()
        with self._lock:
            expired = [k for k, (_, exp) in self._cache.items()
                       if exp and now > exp]
            for k in expired:
                del self._cache[k]
            self._stats["evictions"] += len(expired)
            return len(expired)

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    def get_statistics(self) -> dict:
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total if total > 0 else 0
            return {
                **self._stats,
                "size": len(self._cache),
                "hit_rate": round(hit_rate, 4),
            }


class DistributedLock:
    """
    分布式锁。

    基于Redis实现：
    - try_lock: SET key value NX EX timeout
    - un_lock: Lua脚本原子删除（仅删除自己加的锁）
    - 支持装饰器模式
    - 支持非Redis降级（线程锁）

    Lua脚本保证原子性：
    if redis.call('get', KEYS[1]) == ARGV[1] then
        return redis.call('del', KEYS[1])
    else
        return 0
    end
    """

    _LUA_UNLOCK = """
    if redis.call('get', KEYS[1]) == ARGV[1] then
        return redis.call('del', KEYS[1])
    else
        return 0
    end
    """

    def __init__(self, redis_client=None, key_prefix: str = "hmyxlock:",
                 max_local_locks: int = 1000):
        self._redis = redis_client
        self._key_prefix = key_prefix
        self._local_locks: Dict[str, threading.Lock] = {}
        self._lock_owners: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._stats = {"acquired": 0, "failed": 0, "released": 0}
        self._max_local_locks = max_local_locks
        self._lock_order: List[str] = []  # LRU顺序追踪

    def try_lock(self, name: str, timeout: int = 30,
                 owner: Optional[str] = None) -> bool:
        """尝试获取锁"""
        import uuid
        if owner is None:
            owner = str(uuid.uuid4())[:8]

        key = f"{self._key_prefix}{name}"

        if self._redis is not None:
            try:
                result = self._redis.set(key, owner, nx=True, ex=timeout)
                if result:
                    with self._lock:
                        self._lock_owners[name] = owner
                    self._stats["acquired"] += 1
                    return True
                self._stats["failed"] += 1
                return False
            except Exception as e:
                logger.warning("Redis锁异常，降级到本地锁: %s", e)

        return self._try_local_lock(name, owner, timeout)

    def _try_local_lock(self, name: str, owner: str, timeout: int) -> bool:
        """本地锁降级（死锁安全版本：在全局锁外获取本地锁）"""
        with self._lock:
            if name not in self._local_locks:
                if len(self._local_locks) >= self._max_local_locks:
                    oldest = self._lock_order.pop(0)
                    self._local_locks.pop(oldest, None)
                self._local_locks[name] = threading.Lock()
            self._update_lru(name)
            lock = self._local_locks[name]

        acquired = lock.acquire(timeout=timeout)
        if acquired:
            with self._lock:
                self._lock_owners[name] = owner
            self._stats["acquired"] += 1
            return True
        self._stats["failed"] += 1
        return False

    def _update_lru(self, name: str):
        """更新LRU顺序"""
        if name in self._lock_order:
            self._lock_order.remove(name)
        self._lock_order.append(name)

    def un_lock(self, name: str, owner: Optional[str] = None) -> bool:
        """释放锁"""
        key = f"{self._key_prefix}{name}"

        with self._lock:
            current_owner = self._lock_owners.get(name)
            if owner and current_owner != owner:
                return False
            owner = current_owner or owner or ""

        if self._redis is not None:
            try:
                result = self._redis.eval(
                    self._LUA_UNLOCK, 1, key, owner
                )
                if result:
                    with self._lock:
                        self._lock_owners.pop(name, None)
                        local_lock = self._local_locks.get(name)
                        if local_lock:
                            local_lock.release()
                    self._stats["released"] += 1
                    return True
                return False
            except Exception as e:
                logger.warning("Redis解锁异常，降级到本地解锁: %s", e)

        with self._lock:
            local_lock = self._local_locks.get(name)
            if local_lock:
                try:
                    local_lock.release()
                except RuntimeError:
                    pass
            self._lock_owners.pop(name, None)
            self._stats["released"] += 1
            return True

    def lock(self, name: str, timeout: int = 30):
        """锁装饰器"""
        def decorator(fn: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                import uuid
                owner = str(uuid.uuid4())[:8]
                if self.try_lock(name, timeout, owner):
                    try:
                        return fn(*args, **kwargs)
                    finally:
                        self.un_lock(name, owner)
                else:
                    raise TimeoutError(f"获取锁 {name} 超时")
            return wrapper
        return decorator

    def get_statistics(self) -> dict:
        with self._lock:
            return dict(self._stats)


class MemoryGuard:
    """
    内存守护器。

    定时强制GC + malloc_trim归还内存给OS，
    防止长时间运行导致的内存泄漏和膨胀。

    参考: MaxKB mem.py + 定时GC策略
    """

    def __init__(self, gc_interval_s: int = 3600,
                 trim_interval_s: int = 1800,
                 warning_mb: float = 512.0):
        self._gc_interval = gc_interval_s
        self._trim_interval = trim_interval_s
        self._warning_mb = warning_mb
        self._running = False
        self._timer: Optional[threading.Timer] = None
        self._stats = {
            "gc_runs": 0,
            "trim_runs": 0,
            "warnings": 0,
            "last_gc": None,
            "last_trim": None,
        }
        self._lock = threading.Lock()

    def start(self) -> None:
        """启动内存守护"""
        if self._running:
            return
        self._running = True
        self._schedule_gc()
        logger.info("内存守护器已启动，GC间隔=%ds，Trim间隔=%ds",
                     self._gc_interval, self._trim_interval)

    def stop(self) -> None:
        """停止内存守护"""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def force_gc(self) -> Dict:
        """强制GC"""
        import psutil
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024 / 1024

        gc.collect(2)

        mem_after = process.memory_info().rss / 1024 / 1024

        with self._lock:
            self._stats["gc_runs"] += 1
            self._stats["last_gc"] = datetime.now().isoformat()

        return {
            "mem_before_mb": round(mem_before, 2),
            "mem_after_mb": round(mem_after, 2),
            "freed_mb": round(mem_before - mem_after, 2),
        }

    def force_trim(self) -> bool:
        """尝试malloc_trim归还内存给OS"""
        try:
            if os.name != 'nt':
                libc = ctypes.CDLL("libc.so.6")
                result = libc.malloc_trim(0)
                with self._lock:
                    self._stats["trim_runs"] += 1
                    self._stats["last_trim"] = datetime.now().isoformat()
                return result == 1
            return False
        except Exception as e:
            logger.debug("malloc_trim不可用: %s", e)
            return False

    def check_memory(self) -> Dict:
        """检查内存状态"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            rss_mb = process.memory_info().rss / 1024 / 1024

            is_warning = rss_mb > self._warning_mb
            if is_warning:
                with self._lock:
                    self._stats["warnings"] += 1

            return {
                "rss_mb": round(rss_mb, 2),
                "warning_threshold_mb": self._warning_mb,
                "is_warning": is_warning,
            }
        except ImportError:
            return {"rss_mb": -1, "warning_threshold_mb": self._warning_mb, "is_warning": False}

    def _schedule_gc(self) -> None:
        """调度GC"""
        if not self._running:
            return

        self.force_gc()
        self.force_trim()

        interval = min(self._gc_interval, self._trim_interval)
        self._timer = threading.Timer(interval, self._schedule_gc)
        self._timer.daemon = True
        self._timer.start()

    def get_statistics(self) -> dict:
        with self._lock:
            return dict(self._stats)


_mem_cache: Optional[MemCache] = None
_distributed_lock: Optional[DistributedLock] = None
_memory_guard: Optional[MemoryGuard] = None


def get_mem_cache() -> MemCache:
    """获取零序列化缓存单例"""
    global _mem_cache
    if _mem_cache is None:
        _mem_cache = MemCache()
    return _mem_cache


def get_distributed_lock() -> DistributedLock:
    """获取分布式锁单例"""
    global _distributed_lock
    if _distributed_lock is None:
        _distributed_lock = DistributedLock()
    return _distributed_lock


def get_memory_guard() -> MemoryGuard:
    """获取内存守护器单例"""
    global _memory_guard
    if _memory_guard is None:
        _memory_guard = MemoryGuard()
    return _memory_guard
