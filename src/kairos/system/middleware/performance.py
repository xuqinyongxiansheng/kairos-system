#!/usr/bin/env python3
"""
性能追踪中间件
从main.py拆分，API请求性能追踪与统计
支持百分位统计、慢请求检测、端点级过滤
"""

import time
import threading
from collections import defaultdict
from typing import Dict, Any, Optional


class PerformanceTracker:
    """API请求性能追踪器"""

    def __init__(
        self,
        max_entries: int = 10000,
        slow_threshold: float = 1.0,
        max_endpoints: int = 200,
        max_per_endpoint: int = 500
    ):
        self._requests: defaultdict = defaultdict(list)
        self._lock = threading.Lock()
        self._max_entries = max_entries
        self._slow_threshold = slow_threshold
        self._max_endpoints = max_endpoints
        self._max_per_endpoint = max_per_endpoint

    def record(self, path: str, duration: float, status_code: int):
        """记录请求性能数据

        Args:
            path: 请求路径
            duration: 请求耗时（秒）
            status_code: HTTP状态码
        """
        with self._lock:
            if len(self._requests) >= self._max_endpoints and path not in self._requests:
                oldest_ep = min(
                    self._requests.items(),
                    key=lambda x: x[1][0]["timestamp"] if x[1] else 0
                )
                del self._requests[oldest_ep[0]]

            self._requests[path].append({
                "duration": duration,
                "status_code": status_code,
                "timestamp": time.time()
            })

            if len(self._requests[path]) > self._max_per_endpoint * 2:
                self._requests[path] = self._requests[path][-self._max_per_endpoint:]

    def get_stats(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """获取性能统计

        Args:
            endpoint: 可选，指定端点路径；为None时返回全局统计

        Returns:
            性能统计数据
        """
        with self._lock:
            if endpoint:
                requests = self._requests.get(endpoint, [])
            else:
                requests = []
                for reqs in self._requests.values():
                    requests.extend(reqs)

            if not requests:
                return {"count": 0}

            durations = [r["duration"] for r in requests]
            sorted_durations = sorted(durations)

            return {
                "count": len(requests),
                "avg_duration": sum(durations) / len(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "p50": sorted_durations[len(sorted_durations) // 2],
                "p95": sorted_durations[int(len(sorted_durations) * 0.95)] if len(sorted_durations) > 20 else max(durations),
                "slow_requests": len([d for d in durations if d > self._slow_threshold]),
                "path_details": self._get_path_details() if endpoint is None else None
            }

    def _get_path_details(self) -> Dict[str, Dict[str, Any]]:
        """获取各端点的详细统计"""
        path_stats = {}
        for path, entries in self._requests.items():
            if not entries:
                continue
            durations = [e["duration"] for e in entries]
            avg = sum(durations) / len(durations)
            path_stats[path] = {
                "count": len(entries),
                "avg_ms": round(avg * 1000, 2),
                "max_ms": round(max(durations) * 1000, 2),
                "min_ms": round(min(durations) * 1000, 2),
            }
        return path_stats
