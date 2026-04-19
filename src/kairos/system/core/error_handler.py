"""
统一错误处理框架（线程安全版）
提供异常分类、重试机制、降级处理、错误上报
所有共享状态受RLock保护，错误历史使用有界deque
"""

import asyncio
import functools
import logging
import re
import threading
import traceback
from collections import deque
from typing import Dict, Any, List, Optional, Callable, Type, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json
import os

logger = logging.getLogger("ErrorHandler")

_SENSITIVE_PATTERNS = [
    re.compile(r'api_key\s*[:=]\s*["\']?\w+', re.IGNORECASE),
    re.compile(r'password\s*[:=]\s*\S+', re.IGNORECASE),
    re.compile(r'secret\s*[:=]\s*\S+', re.IGNORECASE),
    re.compile(r'token\s*[:=]\s*\S+', re.IGNORECASE),
]


class ErrorSeverity(Enum):
    """错误严重程度（IntEnum确保数值比较正确）"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def level(self) -> int:
        return _SEVERITY_LEVELS[self.value]


_SEVERITY_LEVELS = {"low": 1, "medium": 2, "high": 3, "critical": 4}


class ErrorCategory(Enum):
    """错误类别"""
    NETWORK = "network"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    LLM = "llm"
    TOOL = "tool"
    VALIDATION = "validation"
    PERMISSION = "permission"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """恢复策略"""
    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    ABORT = "abort"
    ESCALATE = "escalate"


@dataclass
class ErrorContext:
    """错误上下文"""
    error_id: str
    error_type: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: str
    source: str
    traceback: str
    context: Dict[str, Any]
    recovery_attempted: bool = False
    recovery_strategy: Optional[RecoveryStrategy] = None
    recovery_result: Optional[str] = None


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: List[Type[Exception]] = field(default_factory=lambda: [Exception])


class HMYXException(Exception):
    """鸿蒙小雨基础异常"""

    def __init__(self, message: str,
                 category: ErrorCategory = ErrorCategory.UNKNOWN,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 context: Dict[str, Any] = None):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.timestamp = datetime.now().isoformat()


class ToolExecutionError(HMYXException):
    def __init__(self, message: str, tool_name: str = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.TOOL)
        super().__init__(message, **kwargs)
        self.tool_name = tool_name


class LLMError(HMYXException):
    def __init__(self, message: str, model: str = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.LLM)
        super().__init__(message, **kwargs)
        self.model = model


class ValidationError(HMYXException):
    def __init__(self, message: str, field: str = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.VALIDATION)
        kwargs.setdefault('severity', ErrorSeverity.LOW)
        super().__init__(message, **kwargs)
        self.field = field


class HMYXTimeoutError(HMYXException):
    """超时错误（避免与内置TimeoutError冲突）"""
    def __init__(self, message: str, timeout: float = None, **kwargs):
        kwargs.setdefault('category', ErrorCategory.TIMEOUT)
        super().__init__(message, **kwargs)
        self.timeout = timeout


class ErrorHandler:
    """
    统一错误处理器（线程安全版）

    改进:
    - 所有共享状态通过 RLock 保护
    - error_history 使用有界deque防内存泄漏
    - traceback 输出脱敏处理（过滤API密钥/密码等）
    - TimeoutError 重命名为 HMYXTimeoutError 避免覆盖内置异常
    """

    def __init__(self, log_path: str = None, max_history: int = 1000):
        self._lock = threading.RLock()
        self.log_path = log_path or "./logs/errors.log"
        self.error_history: deque = deque(maxlen=max_history)
        self.max_history = max_history
        self.handlers: Dict[ErrorCategory, Callable] = {}
        self.fallback_handlers: Dict[str, Callable] = {}
        self.error_counts: Dict[str, int] = {}
        # 增量统计计数器（避免get_error_stats()全量遍历deque）
        self._category_counts: Dict[str, int] = {cat.value: 0 for cat in ErrorCategory}
        self._severity_counts: Dict[str, int] = {sev.value: 0 for sev in ErrorSeverity}

        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

        self._register_default_handlers()
        logger.info(f"错误处理器初始化(线程安全版+增量统计, max_history={max_history})")

    def _register_default_handlers(self):
        self.handlers = {
            ErrorCategory.NETWORK: self._handle_network_error,
            ErrorCategory.TIMEOUT: self._handle_timeout_error,
            ErrorCategory.LLM: self._handle_llm_error,
            ErrorCategory.TOOL: self._handle_tool_error,
            ErrorCategory.VALIDATION: self._handle_validation_error,
        }

    def handle(self, error: Exception, context: Dict[str, Any] = None,
               source: str = "unknown") -> ErrorContext:
        if isinstance(error, HMYXException):
            category = error.category
            severity = error.severity
            error_context = error.context
        else:
            category = self._classify_error(error)
            severity = self._assess_severity(error)
            error_context = {}

        tb_lines = traceback.format_exception(type(error), error, error.__traceback__)
        safe_traceback = self._sanitize_traceback(
            "".join(tb_lines) if tb_lines else f"{type(error).__name__}: {error}"
        )

        error_ctx = ErrorContext(
            error_id=f"err_{int(datetime.now().timestamp() * 1000)}",
            error_type=type(error).__name__,
            message=str(error)[:500],
            category=category,
            severity=severity,
            timestamp=datetime.now().isoformat(),
            source=source,
            traceback=safe_traceback,
            context={**error_context, **(context or {})}
        )

        with self._lock:
            self.error_history.append(error_ctx)
            # 增量更新统计计数器
            cat_val = error_ctx.category.value
            sev_val = error_ctx.severity.value
            self._category_counts[cat_val] = self._category_counts.get(cat_val, 0) + 1
            self._severity_counts[sev_val] = self._severity_counts.get(sev_val, 0) + 1

        if category in self.handlers:
            try:
                recovery = self.handlers[category](error, error_ctx)
                error_ctx.recovery_attempted = True
                error_ctx.recovery_strategy = recovery.get("strategy")
                error_ctx.recovery_result = recovery.get("result")
            except Exception as e:
                logger.error(f"错误处理器异常: {e}")

        with self._lock:
            key = f"{error_ctx.category.value}:{error_ctx.error_type}"
            self.error_counts[key] = self.error_counts.get(key, 0) + 1

        return error_ctx

    @staticmethod
    def _sanitize_traceback(tb: str) -> str:
        """脱敏traceback中的敏感信息"""
        result = tb
        for pattern in _SENSITIVE_PATTERNS:
            result = pattern.sub('[REDACTED]', result)
        return result

    def _classify_error(self, error: Exception) -> ErrorCategory:
        error_name = type(error).__name__.lower()
        error_message = str(error).lower()

        if type(error).__name__ in ("ValueError", "TypeError", "KeyError", "AttributeError",
                                    "AssertionError", "ValidationError"):
            return ErrorCategory.VALIDATION

        network_keywords = ["connection", "network", "socket", "http", "dns"]
        if any(kw in error_name or kw in error_message for kw in network_keywords):
            return ErrorCategory.NETWORK

        file_keywords = ["file", "directory", "path", "permission", "access"]
        if any(kw in error_name or kw in error_message for kw in file_keywords):
            return ErrorCategory.FILE_SYSTEM

        db_keywords = ["database", "sql", "query", "table", "column"]
        if any(kw in error_name or kw in error_message for kw in db_keywords):
            return ErrorCategory.DATABASE

        if "timeout" in error_name or "timeout" in error_message:
            return ErrorCategory.TIMEOUT

        return ErrorCategory.UNKNOWN

    def _assess_severity(self, error: Exception) -> ErrorSeverity:
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            return ErrorSeverity.CRITICAL

        error_name = type(error).__name__
        critical_errors = ["MemoryError", "SystemExit"]
        if error_name in critical_errors:
            return ErrorSeverity.CRITICAL

        high_errors = ["PermissionError", "OSError", "ConnectionError"]
        if error_name in high_errors:
            return ErrorSeverity.HIGH

        low_errors = ["ValueError", "TypeError", "KeyError"]
        if error_name in low_errors:
            return ErrorSeverity.LOW

        return ErrorSeverity.MEDIUM

    def _handle_network_error(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        return {"strategy": RecoveryStrategy.RETRY, "result": "建议重试或检查网络连接"}

    def _handle_timeout_error(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        return {"strategy": RecoveryStrategy.RETRY, "result": "建议增加超时时间或重试"}

    def _handle_llm_error(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        return {"strategy": RecoveryStrategy.FALLBACK, "result": "建议使用备用模型或降级处理"}

    def _handle_tool_error(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        return {"strategy": RecoveryStrategy.FALLBACK, "result": "建议使用替代工具或跳过"}

    def _handle_validation_error(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        return {"strategy": RecoveryStrategy.SKIP, "result": "输入验证失败，请检查参数"}

    def register_handler(self, category: ErrorCategory, handler: Callable):
        with self._lock:
            self.handlers[category] = handler

    def register_fallback(self, operation: str, handler: Callable):
        with self._lock:
            self.fallback_handlers[operation] = handler

    def get_error_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self.error_history)
            # 使用增量计数器替代O(n)全量遍历
            by_category = dict(self._category_counts)
            by_severity = dict(self._severity_counts)
            top_errors = sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        return {
            "total_errors": total,
            "by_category": by_category,
            "by_severity": by_severity,
            "top_errors": top_errors,
            "max_capacity": self.max_history,
            "current_size": len(self.error_history),
        }

    def get_recent_errors(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            recent = list(self.error_history)[-limit:]
        return [
            {
                "error_id": e.error_id,
                "error_type": e.error_type,
                "message": e.message[:100],
                "category": e.category.value,
                "severity": e.severity.value,
                "timestamp": e.timestamp,
                "source": e.source
            }
            for e in recent
        ]


def retry(config: RetryConfig = None):
    config = config or RetryConfig()

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if not any(isinstance(e, exc) for exc in config.retryable_exceptions):
                        raise
                    if attempt < config.max_retries:
                        delay = min(config.base_delay * (config.exponential_base ** attempt), config.max_delay)
                        if config.jitter:
                            import random as _r
                            delay *= (0.5 + _r.random())
                        logger.warning(f"重试 {attempt + 1}/{config.max_retries}: {e}, 等待 {delay:.2f}s")
                        await asyncio.sleep(delay)
            raise last_error

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if not any(isinstance(e, exc) for exc in config.retryable_exceptions):
                        raise
                    if attempt < config.max_retries:
                        delay = min(config.base_delay * (config.exponential_base ** attempt), config.max_delay)
                        if config.jitter:
                            import random as _r
                            delay *= (0.5 + _r.random())
                        import time as _t
                        _t.sleep(delay)
            raise last_error

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def safe_execute(default: Any = None, log_error: bool = True):
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.error(f"安全执行捕获异常: {e}")
                return default

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.error(f"安全执行捕获异常: {e}")
                return default

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


_error_handler_lock = threading.Lock()
_error_handler_instance: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器（DCLP）"""
    global _error_handler_instance
    if _error_handler_instance is not None:
        return _error_handler_instance
    with _error_handler_lock:
        if _error_handler_instance is None:
            _error_handler_instance = ErrorHandler()
    return _error_handler_instance
