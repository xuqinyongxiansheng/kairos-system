#!/usr/bin/env python3
"""
速率限制中间件
从main.py拆分，基于IP的滑动窗口速率限制
"""

import time
import threading
from collections import defaultdict
from typing import Tuple


class RateLimiter:
    """基于IP的滑动窗口速率限制器"""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: defaultdict = defaultdict(list)
        self._lock = threading.Lock()
        self._last_cleanup: float = time.time()
        self._cleanup_interval: int = 60

    def is_allowed(self, client_id: str) -> Tuple[bool, int]:
        """检查请求是否被允许

        Args:
            client_id: 客户端标识（通常为IP地址）

        Returns:
            (是否允许, 重试等待秒数)
        """
        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            self._requests[client_id] = [
                t for t in self._requests[client_id] if t > window_start
            ]

            if len(self._requests[client_id]) >= self.max_requests:
                retry_after = int(self._requests[client_id][0] - window_start) + 1
                return False, retry_after

            self._requests[client_id].append(now)

            if now - self._last_cleanup > self._cleanup_interval:
                self._cleanup(window_start)
                self._last_cleanup = now

            return True, 0

    def _cleanup(self, window_start: float):
        """清理过期记录"""
        expired_keys = []
        for client_id in list(self._requests.keys()):
            self._requests[client_id] = [
                t for t in self._requests[client_id] if t > window_start
            ]
            if not self._requests[client_id]:
                expired_keys.append(client_id)
        for k in expired_keys:
            del self._requests[k]
