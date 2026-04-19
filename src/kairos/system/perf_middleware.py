#!/usr/bin/env python3
"""
请求性能监控中间件 v4.1
自动记录每个请求的耗时、状态码、追踪ID
支持Prometheus指标导出

使用方式:
    from kairos.system.perf_middleware import add_perf_middleware
    add_perf_middleware(app)
"""

import time
import uuid
import logging
from typing import Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("PerfMiddleware")

# 排除健康检查端点（避免噪音）
_SKIP_PATHS = {"/api/health", "/api/v1/health", "/api/v2/health", "/api/ready", "/api/live", "/metrics"}


class PerformanceMiddleware(BaseHTTPMiddleware):
    """请求性能监控中间件"""

    def __init__(self, app, slow_threshold_ms: float = 1000.0):
        super().__init__(app)
        self.slow_threshold = slow_threshold_ms

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 跳过静态文件和健康检查
        if request.url.path in _SKIP_PATHS or request.url.path.startswith("/static"):
            return await call_next(request)

        # 注入追踪ID
        trace_id = request.headers.get("X-Trace-ID") or uuid.uuid4().hex[:12]
        request.state.trace_id = trace_id
        start_time = time.perf_counter()

        # 记录请求开始
        logger.debug(
            "[%s] → %s %s",
            trace_id,
            request.method,
            request.url.path
        )

        try:
            response = await call_next(request)

            # 计算耗时
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            status = response.status_code

            # 添加响应头
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"

            # 日志级别根据状态码选择
            if status >= 500:
                log_fn = logger.error
            elif status >= 400:
                log_fn = logger.warning
            elif elapsed_ms > self.slow_threshold:
                log_fn = logger.warning
            else:
                log_fn = logger.info

            log_fn(
                "[%s] ← %s %d (%.1fms)",
                trace_id,
                request.url.path,
                status,
                elapsed_ms
            )

            # Prometheus指标（如果可用）
            self._record_metrics(request.method, request.url.path, status, elapsed_ms)

            return response

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "[%s] ✗ %s %s 异常 (%.1fms): %s",
                trace_id,
                request.method,
                request.url.path,
                elapsed_ms,
                e
            )
            raise

    @staticmethod
    def _record_metrics(method: str, path: str, status: int, elapsed_ms: float):
        """记录Prometheus指标"""
        try:
            from main import REQUEST_COUNT, REQUEST_LATENCY, ACTIVE_REQUESTS
            if REQUEST_COUNT is not None:
                labels = [method, path.split("?")[0], str(status)]
                REQUEST_COUNT.labels(*labels).inc()
                REQUEST_LATENCY.labels(method, path.split("?")[0]).observe(elapsed_ms / 1000)
        except Exception:
            pass


def add_perf_middleware(app, slow_threshold_ms: float = 1000.0):
    """注册性能监控中间件到FastAPI应用

    Args:
        app: FastAPI实例
        slow_threshold_ms: 慢请求阈值(毫秒)，超过此值会warning日志
    """
    app.add_middleware(PerformanceMiddleware, slow_threshold_ms=slow_threshold_ms)
    logger.info("性能监控中间件已注册 (慢请求阈值: %.0fms)", slow_threshold_ms)
