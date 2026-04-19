#!/usr/bin/env python3
"""
健康检查中间件
从main.py拆分，系统健康状态检测
支持同步/异步检查、依赖注册、存活/就绪探针
"""

import time
import logging
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)


class HealthChecker:
    """系统健康检查器"""

    def __init__(self):
        self._start_time: float = time.time()
        self._shutdown_requested: bool = False
        self._dependencies: Dict[str, Dict[str, Any]] = {}

    def register_dependency(self, name: str, check_func: Callable[[], bool]):
        """注册健康检查依赖项

        Args:
            name: 依赖项名称
            check_func: 检查函数（返回bool）
        """
        self._dependencies[name] = {
            "func": check_func,
            "last_status": None,
            "last_check": 0
        }

    def register_check(self, name: str, check_func: Callable, critical: bool = True):
        """注册健康检查项（兼容接口）

        Args:
            name: 检查项名称
            check_func: 检查函数（返回bool）
            critical: 是否为关键检查项
        """
        self._dependencies[name] = {
            "func": check_func,
            "critical": critical,
            "last_status": None,
            "last_check": 0
        }

    def check_all(self) -> Dict[str, Any]:
        """执行所有健康检查（同步）

        Returns:
            健康状态报告
        """
        results = {}
        all_healthy = True

        for name, dep_info in self._dependencies.items():
            try:
                check_func = dep_info["func"]
                healthy = bool(check_func())
                dep_info["last_status"] = healthy
                dep_info["last_check"] = time.time()
                results[name] = {"status": "healthy" if healthy else "unhealthy"}
                critical = dep_info.get("critical", True)
                if not healthy and critical:
                    all_healthy = False
            except Exception as e:
                results[name] = {"status": "error", "message": str(e)}
                dep_info["last_status"] = False
                dep_info["last_check"] = time.time()
                critical = dep_info.get("critical", True)
                if critical:
                    all_healthy = False

        return {
            "status": "healthy" if all_healthy else "degraded",
            "dependencies": results,
            "uptime_seconds": int(time.time() - self._start_time),
            "timestamp": time.time()
        }

    async def async_check_all(self) -> Dict[str, Any]:
        """执行所有健康检查（异步兼容）

        Returns:
            健康状态报告
        """
        return self.check_all()

    def check_live(self) -> bool:
        """存活探针检查

        Returns:
            是否存活
        """
        return not self._shutdown_requested

    def check_ready(self) -> tuple:
        """就绪探针检查

        Returns:
            (是否就绪, 原因说明)
        """
        if self._shutdown_requested:
            return False, "shutdown in progress"

        for name, dep_info in self._dependencies.items():
            try:
                check_func = dep_info["func"]
                if not check_func():
                    return False, f"{name} not ready"
            except Exception:
                return False, f"{name} check failed"

        return True, "ready"

    def request_shutdown(self):
        """请求关闭"""
        self._shutdown_requested = True
