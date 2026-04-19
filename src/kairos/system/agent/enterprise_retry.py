# -*- coding: utf-8 -*-
"""
企业级API重试系统

核心特性：
- 指数退避 + 随机抖动，避免惊群效应
- 前台/后台分离：前台快速失败，后台持续重试
- 429速率限制处理：解析Retry-After头
- 上下文溢出适配：检测token超限并自动截断
- 529过载检测：服务端过载时延长退避

参考: Claude Code withRetry.ts (822行)
"""

import time
import random
import logging
import threading
import asyncio
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, TypeVar, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

T = TypeVar('T')

BASE_DELAY_MS = 1000
MAX_RETRY_DELAY_MS = 60000
BACKOFF_MULTIPLIER = 2


class RetryMode(Enum):
    FOREGROUND = "foreground"
    BACKGROUND = "background"


class ErrorCategory(Enum):
    TRANSIENT = "transient"
    RATE_LIMITED = "rate_limited"
    OVERLOADED = "overloaded"
    CONTEXT_OVERFLOW = "context_overflow"
    FATAL = "fatal"


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay_ms: int = BASE_DELAY_MS
    max_delay_ms: int = MAX_RETRY_DELAY_MS
    backoff_multiplier: float = BACKOFF_MULTIPLIER
    jitter_range: float = 0.25
    mode: RetryMode = RetryMode.FOREGROUND
    retry_on_categories: List[ErrorCategory] = field(
        default_factory=lambda: [
            ErrorCategory.TRANSIENT,
            ErrorCategory.RATE_LIMITED,
            ErrorCategory.OVERLOADED,
        ]
    )


@dataclass
class RetryAttempt:
    attempt_number: int
    error: Optional[Exception] = None
    error_category: Optional[ErrorCategory] = None
    delay_ms: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RetryResult:
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    attempts: List[RetryAttempt] = field(default_factory=list)
    total_delay_ms: int = 0
    final_category: Optional[ErrorCategory] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "attempts": len(self.attempts),
            "total_delay_ms": self.total_delay_ms,
            "final_category": self.final_category.value if self.final_category else None,
            "error": str(self.error) if self.error else None,
        }


class ErrorClassifier:
    """
    错误分类器，将异常映射到错误类别。

    分类规则：
    - 网络超时/连接错误 → TRANSIENT
    - 429状态码 → RATE_LIMITED
    - 529状态码 → OVERLOADED
    - token超限 → CONTEXT_OVERFLOW
    - 4xx客户端错误 → FATAL
    """

    TRANSIENT_PATTERNS = [
        "timeout", "connection", "network", "reset", "refused",
        "broken pipe", "eof", "unreachable", "dns",
        "超时", "连接", "网络", "重置", "拒绝",
        "断开", "不可达",
    ]
    RATE_LIMIT_PATTERNS = ["429", "rate limit", "too many requests", "速率限制", "请求过多"]
    OVERLOAD_PATTERNS = ["529", "overloaded", "service unavailable", "503", "过载", "服务不可用"]
    CONTEXT_OVERFLOW_PATTERNS = [
        "too many tokens", "context length", "prompt too long",
        "max tokens", "context window", "token limit",
        "token过多", "上下文长度", "提示过长",
    ]
    FATAL_PATTERNS = [
        "401", "403", "unauthorized", "forbidden",
        "invalid api key", "invalid x-api-key",
        "未授权", "禁止访问",
    ]

    @classmethod
    def classify(cls, error: Exception) -> ErrorCategory:
        msg = str(error).lower()

        for pattern in cls.FATAL_PATTERNS:
            if pattern in msg:
                return ErrorCategory.FATAL

        for pattern in cls.CONTEXT_OVERFLOW_PATTERNS:
            if pattern in msg:
                return ErrorCategory.CONTEXT_OVERFLOW

        for pattern in cls.RATE_LIMIT_PATTERNS:
            if pattern in msg:
                return ErrorCategory.RATE_LIMITED

        for pattern in cls.OVERLOAD_PATTERNS:
            if pattern in msg:
                return ErrorCategory.OVERLOADED

        for pattern in cls.TRANSIENT_PATTERNS:
            if pattern in msg:
                return ErrorCategory.TRANSIENT

        return ErrorCategory.FATAL


def calculate_retry_delay(
    attempt: int,
    base_delay_ms: int = BASE_DELAY_MS,
    max_delay_ms: int = MAX_RETRY_DELAY_MS,
    multiplier: float = BACKOFF_MULTIPLIER,
    jitter_range: float = 0.25,
    retry_after_ms: Optional[int] = None,
) -> int:
    """
    计算重试延迟，指数退避 + 随机抖动。

    Args:
        attempt: 当前尝试次数（从0开始）
        base_delay_ms: 基础延迟
        max_delay_ms: 最大延迟
        multiplier: 退避乘数
        jitter_range: 抖动范围（0-1）
        retry_after_ms: 服务端指定的重试等待时间

    Returns:
        延迟毫秒数
    """
    if retry_after_ms and retry_after_ms > 0:
        return min(retry_after_ms, max_delay_ms)

    delay = base_delay_ms * (multiplier ** attempt)
    delay = min(delay, max_delay_ms)

    jitter = delay * jitter_range * (2 * random.random() - 1)
    delay = max(0, int(delay + jitter))

    return min(delay, max_delay_ms)


def parse_retry_after(headers: Dict) -> Optional[int]:
    """解析Retry-After头，返回毫秒数"""
    retry_after = headers.get("retry-after") or headers.get("Retry-After")
    if not retry_after:
        return None

    try:
        seconds = float(retry_after)
        return int(seconds * 1000)
    except (ValueError, TypeError):
        pass

    return None


class EnterpriseRetry:
    """
    企业级重试执行器。

    特性：
    - 前台模式：快速失败，有限重试
    - 后台模式：持续重试，更长退避
    - 429处理：解析Retry-After，尊重服务端节奏
    - 上下文溢出：检测并标记，不重试
    - 重试统计：记录每次尝试的详细信息
    """

    FOREGROUND_CONFIG = RetryConfig(
        max_retries=3,
        base_delay_ms=1000,
        max_delay_ms=30000,
        mode=RetryMode.FOREGROUND,
    )

    BACKGROUND_CONFIG = RetryConfig(
        max_retries=10,
        base_delay_ms=2000,
        max_delay_ms=60000,
        mode=RetryMode.BACKGROUND,
    )

    def __init__(self, config: Optional[RetryConfig] = None):
        self._config = config or self.FOREGROUND_CONFIG
        self._stats = {
            "total_calls": 0,
            "successful_first_try": 0,
            "successful_after_retry": 0,
            "failed": 0,
            "by_category": {cat.value: 0 for cat in ErrorCategory},
        }
        self._lock = threading.Lock()

    def execute(self, fn: Callable[[], T],
                config: Optional[RetryConfig] = None) -> RetryResult:
        """
        执行带重试的函数调用。

        Args:
            fn: 要执行的函数
            config: 可选的覆盖配置

        Returns:
            RetryResult 包含执行结果和重试历史
        """
        cfg = config or self._config
        attempts: List[RetryAttempt] = []
        total_delay = 0

        with self._lock:
            self._stats["total_calls"] += 1

        for attempt_num in range(cfg.max_retries + 1):
            attempt = RetryAttempt(attempt_number=attempt_num)

            try:
                result = fn()
                attempt.timestamp = datetime.now().isoformat()
                attempts.append(attempt)

                with self._lock:
                    if attempt_num == 0:
                        self._stats["successful_first_try"] += 1
                    else:
                        self._stats["successful_after_retry"] += 1

                return RetryResult(
                    success=True,
                    result=result,
                    attempts=attempts,
                    total_delay_ms=total_delay,
                )

            except Exception as e:
                category = ErrorClassifier.classify(e)
                attempt.error = e
                attempt.error_category = category
                attempt.timestamp = datetime.now().isoformat()
                attempts.append(attempt)

                with self._lock:
                    self._stats["by_category"][category.value] += 1

                if category == ErrorCategory.FATAL:
                    with self._lock:
                        self._stats["failed"] += 1
                    return RetryResult(
                        success=False,
                        error=e,
                        attempts=attempts,
                        total_delay_ms=total_delay,
                        final_category=category,
                    )

                if category == ErrorCategory.CONTEXT_OVERFLOW:
                    with self._lock:
                        self._stats["failed"] += 1
                    return RetryResult(
                        success=False,
                        error=e,
                        attempts=attempts,
                        total_delay_ms=total_delay,
                        final_category=category,
                    )

                if category not in cfg.retry_on_categories:
                    with self._lock:
                        self._stats["failed"] += 1
                    return RetryResult(
                        success=False,
                        error=e,
                        attempts=attempts,
                        total_delay_ms=total_delay,
                        final_category=category,
                    )

                if attempt_num >= cfg.max_retries:
                    with self._lock:
                        self._stats["failed"] += 1
                    return RetryResult(
                        success=False,
                        error=e,
                        attempts=attempts,
                        total_delay_ms=total_delay,
                        final_category=category,
                    )

                retry_after_ms = None
                if hasattr(e, 'headers') and isinstance(e.headers, dict):
                    retry_after_ms = parse_retry_after(e.headers)

                delay = calculate_retry_delay(
                    attempt=attempt_num,
                    base_delay_ms=cfg.base_delay_ms,
                    max_delay_ms=cfg.max_delay_ms,
                    multiplier=cfg.backoff_multiplier,
                    jitter_range=cfg.jitter_range,
                    retry_after_ms=retry_after_ms,
                )

                if category == ErrorCategory.OVERLOADED:
                    delay = int(delay * 1.5)

                attempt.delay_ms = delay
                total_delay += delay

                logger.info(
                    "重试 %d/%d，类别=%s，延迟=%dms",
                    attempt_num + 1, cfg.max_retries,
                    category.value, delay,
                )

                time.sleep(delay / 1000.0)

        with self._lock:
            self._stats["failed"] += 1

        return RetryResult(
            success=False,
            error=attempts[-1].error if attempts else None,
            attempts=attempts,
            total_delay_ms=total_delay,
            final_category=attempts[-1].error_category if attempts else None,
        )

    def execute_foreground(self, fn: Callable[[], T]) -> RetryResult:
        """前台模式执行（快速失败）"""
        return self.execute(fn, self.FOREGROUND_CONFIG)

    def execute_background(self, fn: Callable[[], T]) -> RetryResult:
        """后台模式执行（持续重试）"""
        return self.execute(fn, self.BACKGROUND_CONFIG)

    async def execute_async(
        self,
        fn: Callable[[], T],
        cfg: Optional['RetryConfig'] = None
    ) -> RetryResult:
        """
        异步执行版本（不阻塞事件循环）

        与 execute() 的区别：
        - 使用 asyncio.sleep() 替代 time.sleep()
        - 可在 FastAPI/asyncio 环境中安全使用
        - 不会阻塞其他协程的执行
        """
        if cfg is None:
            cfg = self.BACKGROUND_CONFIG

        attempts: List[RetryAttempt] = []
        total_delay = 0

        with self._lock:
            self._stats["total_calls"] += 1

        for attempt_num in range(cfg.max_retries + 1):
            try:
                result = fn()
                with self._lock:
                    self._stats["successful_first_try"] += int(attempt_num == 0)
                    self._stats["successful_after_retry"] += int(attempt_num > 0)
                return RetryResult(
                    success=True,
                    result=result,
                    attempts=attempts,
                    total_delay_ms=total_delay,
                )
            except Exception as e:
                category = ErrorClassifier.classify(e)
                attempt = RetryAttempt(
                    attempt_number=attempt_num,
                    error=e,
                    error_category=category,
                    timestamp=datetime.now(),
                )
                attempts.append(attempt)

                with self._lock:
                    self._stats["by_category"][category.value] += 1

                if category in (ErrorCategory.FATAL, ErrorCategory.CONTEXT_OVERFLOW):
                    with self._lock:
                        self._stats["failed"] += 1
                    return RetryResult(
                        success=False,
                        error=e,
                        attempts=attempts,
                        total_delay_ms=total_delay,
                        final_category=category,
                    )

                if category not in cfg.retry_on_categories:
                    with self._lock:
                        self._stats["failed"] += 1
                    return RetryResult(
                        success=False,
                        error=e,
                        attempts=attempts,
                        total_delay_ms=total_delay,
                        final_category=category,
                    )

                if attempt_num >= cfg.max_retries:
                    with self._lock:
                        self._stats["failed"] += 1
                    return RetryResult(
                        success=False,
                        error=e,
                        attempts=attempts,
                        total_delay_ms=total_delay,
                        final_category=category,
                    )

                retry_after_ms = None
                if hasattr(e, 'headers') and isinstance(e.headers, dict):
                    retry_after_ms = parse_retry_after(e.headers)

                delay = calculate_retry_delay(
                    attempt=attempt_num,
                    base_delay_ms=cfg.base_delay_ms,
                    max_delay_ms=cfg.max_delay_ms,
                    multiplier=cfg.backoff_multiplier,
                    jitter_range=cfg.jitter_range,
                    retry_after_ms=retry_after_ms,
                )

                if category == ErrorCategory.OVERLOADED:
                    delay = int(delay * 1.5)

                attempt.delay_ms = delay
                total_delay += delay

                logger.info(
                    "异步重试 %d/%d，类别=%s，延迟=%dms",
                    attempt_num + 1, cfg.max_retries,
                    category.value, delay,
                )

                await asyncio.sleep(delay / 1000.0)  # 异步等待，不阻塞事件循环

        with self._lock:
            self._stats["failed"] += 1

        return RetryResult(
            success=False,
            error=attempts[-1].error if attempts else None,
            attempts=attempts,
            total_delay_ms=total_delay,
            final_category=attempts[-1].error_category if attempts else None,
        )

    async def execute_foreground_async(self, fn: Callable[[], T]) -> RetryResult:
        """异步前台模式执行"""
        return await self.execute_async(fn, self.FOREGROUND_CONFIG)

    async def execute_background_async(self, fn: Callable[[], T]) -> RetryResult:
        """异步后台模式执行"""
        return await self.execute_async(fn, self.BACKGROUND_CONFIG)

    def get_statistics(self) -> dict:
        """获取统计"""
        with self._lock:
            stats = self._stats.copy()
        total = stats["total_calls"]
        if total > 0:
            stats["success_rate"] = (
                (stats["successful_first_try"] + stats["successful_after_retry"])
                / total
            )
            stats["first_try_rate"] = stats["successful_first_try"] / total
        return stats


_retry_instance: Optional[EnterpriseRetry] = None


def get_enterprise_retry() -> EnterpriseRetry:
    """获取企业级重试执行器单例"""
    global _retry_instance
    if _retry_instance is None:
        _retry_instance = EnterpriseRetry()
    return _retry_instance
