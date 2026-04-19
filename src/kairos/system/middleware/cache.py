#!/usr/bin/env python3
"""
响应缓存和模型缓存中间件
从main.py拆分
"""

import time
import asyncio
import threading
import logging
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)


class ResponseCache:
    """API响应缓存"""

    def __init__(self, ttl: int = 300, enabled: bool = True, max_size: int = 1000):
        self.ttl = ttl
        self.enabled = enabled
        self.max_size = max_size
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self.enabled:
            return None

        with self._lock:
            if key in self._cache:
                data, expire = self._cache[key]
                if time.time() < expire:
                    return data
                del self._cache[key]
        return None

    def set(self, key: str, value: Any):
        """设置缓存"""
        if not self.enabled:
            return

        with self._lock:
            if len(self._cache) >= self.max_size:
                now = time.time()
                expired_keys = [k for k, (_, exp) in self._cache.items() if exp <= now]
                if expired_keys:
                    for k in expired_keys:
                        del self._cache[k]
                else:
                    oldest = min(self._cache.items(), key=lambda x: x[1][1])
                    del self._cache[oldest[0]]
            self._cache[key] = (value, time.time() + self.ttl)

    def delete(self, key: str):
        """删除缓存"""
        with self._lock:
            self._cache.pop(key, None)

    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()

    def generate_key(self, request) -> str:
        """生成缓存键"""
        return f"{request.method}:{request.url.path}:{request.query_params}"


class ModelCache:
    """Ollama模型列表缓存"""

    def __init__(self, ttl: int = 300):
        self._models: Optional[List[str]] = None
        self._last_update: float = 0
        self._ttl = ttl
        self._lock = asyncio.Lock()

    async def get_models(self) -> List[str]:
        """获取模型列表（带缓存）"""
        async with self._lock:
            now = time.time()
            if self._models is None or (now - self._last_update) > self._ttl:
                try:
                    import ollama
                    models = ollama.list()
                    self._models = []
                    if models and 'models' in models:
                        for m in models['models']:
                            if isinstance(m, dict):
                                self._models.append(m.get('name', 'unknown'))
                    self._last_update = now
                except Exception as e:
                    logger.warning("获取模型列表失败: %s", e)
                    if self._models is None:
                        self._models = []
        return self._models or []

    async def refresh(self) -> List[str]:
        """强制刷新模型列表"""
        async with self._lock:
            try:
                import ollama
                models = ollama.list()
                self._models = []
                if models and 'models' in models:
                    for m in models['models']:
                        if isinstance(m, dict):
                            self._models.append(m.get('name', 'unknown'))
                self._last_update = time.time()
            except Exception as e:
                logger.warning("刷新模型列表失败: %s", e)
        return self._models or []
