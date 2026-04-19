#!/usr/bin/env python3
"""
缓存模块
"""

from .local_cache import LocalCache, FileCache, get_local_cache, get_file_cache
from .distributed_cache import DistributedCache, CacheManager, get_cache_manager

__all__ = [
    'LocalCache',
    'FileCache',
    'get_local_cache',
    'get_file_cache',
    'DistributedCache',
    'CacheManager',
    'get_cache_manager'
]