"""
统一错误处理系统 - 整合CLI-Anything的错误处理模式

设计模式来源:
- renderdoc/utils/errors.py: 统一错误处理
- ollama_backend.py: HTTP错误处理
- 多个模块的异常处理模式

核心特性:
1. 统一错误类型定义
2. 错误上下文收集
3. 错误恢复策略
4. 错误报告生成
5. 错误统计与分析
"""

from __future__ import annotations

import json
import logging
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union

logger = logging.getLogger("unified_error")


class ErrorSeverity(Enum):
    """错误严重程度"""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4
    FATAL = 5


class ErrorCategory(Enum):
    """错误分类"""
    SYSTEM = "system"
    NETWORK = "network"
    DATABASE = "database"
    FILE = "file"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    RUNTIME = "runtime"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """恢复策略"""
    IGNORE = "ignore"
    RETRY = "retry"
    FALLBACK = "fallback"
    ABORT = "abort"
    ESCALATE = "escalate"
    CUSTOM = "custom"


@dataclass
class ErrorContext:
    """错误上下文"""
    function_name: str = ""
    file_name: str = ""
    line_number: int = 0
    module_name: str = ""
    thread_id: int = 0
    process_id: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    local_variables: Dict[str, Any] = field(default_factory=dict)
    call_stack: List[str] = field(default_factory=list)
    additional_info: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def capture(cls, depth: int = 1) -> 'ErrorContext':
        """捕获当前上下文"""
        frame = sys._getframe(depth + 1)
        
        local_vars = {}
        try:
            for key, value in frame.f_locals.items():
                try:
                    json.dumps({key: str(value)})
                    local_vars[key] = str(value)[:200]
                except Exception:
                    local_vars[key] = "<无法序列化>"
        except Exception:
            logger.debug(f"忽略异常: json.dumps({key: str(value)})", exc_info=True)
            pass
        
        call_stack = []
        for line in traceback.format_stack(frame, limit=10):
            call_stack.append(line.strip())
        
        return cls(
            function_name=frame.f_code.co_name,
            file_name=frame.f_code.co_filename,
            line_number=frame.f_lineno,
            module_name=frame.f_globals.get("__name__", ""),
            thread_id=threading.get_ident(),
            process_id=os.getpid() if hasattr(os, 'getpid') else 0,
            local_variables=local_vars,
            call_stack=call_stack
        )


@dataclass
class ErrorRecord:
    """错误记录"""
    error_id: str
    error_type: str
    message: str
    severity: ErrorSeverity
    category: ErrorCategory
    context: ErrorContext
    traceback_str: str = ""
    cause: Optional['ErrorRecord'] = None
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.ABORT
    recovery_attempts: int = 0
    recovered: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "error_type": self.error_type,
            "message": self.message,
            "severity": self.severity.value,
            "category": self.category.value,
            "context": {
                "function_name": self.context.function_name,
                "file_name": self.context.file_name,
                "line_number": self.context.line_number,
                "module_name": self.context.module_name,
                "thread_id": self.context.thread_id,
                "process_id": self.context.process_id,
                "timestamp": self.context.timestamp.isoformat()
            },
            "traceback": self.traceback_str,
            "recovery_strategy": self.recovery_strategy.value,
            "recovery_attempts": self.recovery_attempts,
            "recovered": self.recovered,
            "metadata": self.metadata
        }


class UnifiedError(Exception):
    """
    统一错误基类
    
    所有自定义错误都应继承此类
    """
    
    error_type: str = "unified_error"
    default_message: str = "发生未知错误"
    default_severity: ErrorSeverity = ErrorSeverity.ERROR
    default_category: ErrorCategory = ErrorCategory.UNKNOWN
    default_recovery: RecoveryStrategy = RecoveryStrategy.ABORT
    
    def __init__(
        self,
        message: Optional[str] = None,
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None,
        recovery: Optional[RecoveryStrategy] = None,
        cause: Optional[Exception] = None,
        **metadata
    ):
        self.message = message or self.default_message
        self.severity = severity or self.default_severity
        self.category = category or self.default_category
        self.recovery_strategy = recovery or self.default_recovery
        self.cause = cause
        self.metadata = metadata
        self.context = ErrorContext.capture(depth=2)
        self.error_id = self._generate_error_id()
        self.traceback_str = traceback.format_exc() if cause else ""
        
        super().__init__(self.message)
    
    def _generate_error_id(self) -> str:
        import hashlib
        content = f"{self.error_type}:{self.message}:{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def to_record(self) -> ErrorRecord:
        """转换为错误记录"""
        cause_record = None
        if self.cause and isinstance(self.cause, UnifiedError):
            cause_record = self.cause.to_record()
        
        return ErrorRecord(
            error_id=self.error_id,
            error_type=self.error_type,
            message=self.message,
            severity=self.severity,
            category=self.category,
            context=self.context,
            traceback_str=self.traceback_str,
            cause=cause_record,
            recovery_strategy=self.recovery_strategy,
            metadata=self.metadata
        )


class NetworkError(UnifiedError):
    """网络错误"""
    error_type = "network_error"
    default_message = "网络连接失败"
    default_category = ErrorCategory.NETWORK
    default_recovery = RecoveryStrategy.RETRY


class TimeoutError(UnifiedError):
    """超时错误"""
    error_type = "timeout_error"
    default_message = "操作超时"
    default_category = ErrorCategory.TIMEOUT
    default_recovery = RecoveryStrategy.RETRY


class ValidationError(UnifiedError):
    """验证错误"""
    error_type = "validation_error"
    default_message = "数据验证失败"
    default_category = ErrorCategory.VALIDATION
    default_recovery = RecoveryStrategy.ABORT


class AuthenticationError(UnifiedError):
    """认证错误"""
    error_type = "authentication_error"
    default_message = "认证失败"
    default_category = ErrorCategory.AUTHENTICATION
    default_recovery = RecoveryStrategy.ABORT


class PermissionError(UnifiedError):
    """权限错误"""
    error_type = "permission_error"
    default_message = "权限不足"
    default_category = ErrorCategory.PERMISSION
    default_recovery = RecoveryStrategy.ABORT


class ResourceError(UnifiedError):
    """资源错误"""
    error_type = "resource_error"
    default_message = "资源不可用"
    default_category = ErrorCategory.RESOURCE
    default_recovery = RecoveryStrategy.FALLBACK


class ConfigurationError(UnifiedError):
    """配置错误"""
    error_type = "configuration_error"
    default_message = "配置错误"
    default_category = ErrorCategory.CONFIGURATION
    default_recovery = RecoveryStrategy.ABORT


class DatabaseError(UnifiedError):
    """数据库错误"""
    error_type = "database_error"
    default_message = "数据库操作失败"
    default_category = ErrorCategory.DATABASE
    default_recovery = RecoveryStrategy.RETRY


class FileError(UnifiedError):
    """文件错误"""
    error_type = "file_error"
    default_message = "文件操作失败"
    default_category = ErrorCategory.FILE
    default_recovery = RecoveryStrategy.RETRY


class ErrorHandler:
    """
    错误处理器
    
    提供统一的错误处理、恢复和报告功能
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        log_file: Optional[str] = None,
        on_error: Optional[Callable[[ErrorRecord], None]] = None
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.log_file = Path(log_file) if log_file else None
        self.on_error = on_error
        
        self._error_history: List[ErrorRecord] = []
        self._error_counts: Dict[str, int] = {}
        self._recovery_handlers: Dict[ErrorCategory, Callable] = {}
        self._lock = threading.RLock()
    
    def handle(
        self,
        error: Union[Exception, ErrorRecord],
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorRecord:
        """
        处理错误
        
        Args:
            error: 错误对象或错误记录
            context: 额外上下文
            
        Returns:
            错误记录
        """
        if isinstance(error, ErrorRecord):
            record = error
        elif isinstance(error, UnifiedError):
            record = error.to_record()
        else:
            record = self._wrap_exception(error)
        
        if context:
            record.metadata.update(context)
        
        with self._lock:
            self._error_history.append(record)
            error_key = f"{record.error_type}:{record.category.value}"
            self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1
        
        self._log_error(record)
        
        if self.on_error:
            try:
                self.on_error(record)
            except Exception:
                logger.debug(f"忽略异常: self.on_error(record)", exc_info=True)
                pass
        
        return record
    
    def _wrap_exception(self, error: Exception) -> ErrorRecord:
        """将标准异常包装为错误记录"""
        error_type = type(error).__name__
        
        category = ErrorCategory.UNKNOWN
        if isinstance(error, (ConnectionError, ConnectionRefusedError, ConnectionResetError)):
            category = ErrorCategory.NETWORK
        elif isinstance(error, TimeoutError):
            category = ErrorCategory.TIMEOUT
        elif isinstance(error, PermissionError):
            category = ErrorCategory.PERMISSION
        elif isinstance(error, FileNotFoundError):
            category = ErrorCategory.FILE
        elif isinstance(error, ValueError):
            category = ErrorCategory.VALIDATION
        
        return ErrorRecord(
            error_id=self._generate_id(),
            error_type=error_type,
            message=str(error),
            severity=ErrorSeverity.ERROR,
            category=category,
            context=ErrorContext.capture(depth=2),
            traceback_str=traceback.format_exc()
        )
    
    def _generate_id(self) -> str:
        import hashlib
        content = f"error:{time.time()}:{threading.get_ident()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _log_error(self, record: ErrorRecord) -> None:
        """记录错误到日志"""
        log_entry = json.dumps(record.to_dict(), ensure_ascii=False)
        
        if self.log_file:
            try:
                self.log_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry + "\n")
            except Exception:
                logger.debug(f"忽略异常: ", exc_info=True)
                pass
    
    def register_recovery_handler(
        self,
        category: ErrorCategory,
        handler: Callable[[ErrorRecord], bool]
    ) -> None:
        """注册恢复处理器"""
        self._recovery_handlers[category] = handler
    
    def attempt_recovery(self, record: ErrorRecord) -> bool:
        """
        尝试恢复
        
        Args:
            record: 错误记录
            
        Returns:
            是否成功恢复
        """
        if record.recovery_strategy == RecoveryStrategy.IGNORE:
            record.recovered = True
            return True
        
        if record.recovery_strategy == RecoveryStrategy.ABORT:
            return False
        
        handler = self._recovery_handlers.get(record.category)
        if handler:
            try:
                record.recovery_attempts += 1
                success = handler(record)
                record.recovered = success
                return success
            except Exception:
                return False
        
        return False
    
    def get_error_history(
        self,
        limit: int = 100,
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None
    ) -> List[ErrorRecord]:
        """获取错误历史"""
        with self._lock:
            records = self._error_history
            
            if severity:
                records = [r for r in records if r.severity == severity]
            if category:
                records = [r for r in records if r.category == category]
            
            return records[-limit:]
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        with self._lock:
            total = len(self._error_history)
            by_severity = {}
            by_category = {}
            
            for record in self._error_history:
                sev = record.severity.value
                by_severity[sev] = by_severity.get(sev, 0) + 1
                
                cat = record.category.value
                by_category[cat] = by_category.get(cat, 0) + 1
            
            recovered = sum(1 for r in self._error_history if r.recovered)
            
            return {
                "total_errors": total,
                "recovered": recovered,
                "recovery_rate": recovered / total if total > 0 else 0,
                "by_severity": by_severity,
                "by_category": by_category,
                "error_counts": dict(self._error_counts)
            }
    
    def clear_history(self) -> None:
        """清空错误历史"""
        with self._lock:
            self._error_history.clear()
            self._error_counts.clear()


def handle_error(
    error: Exception,
    debug: bool = False,
    handler: Optional[ErrorHandler] = None
) -> Dict[str, Any]:
    """
    处理错误的便捷函数
    
    Args:
        error: 异常对象
        debug: 是否包含调试信息
        handler: 错误处理器
        
    Returns:
        错误信息字典
    """
    if handler:
        record = handler.handle(error)
    elif isinstance(error, UnifiedError):
        record = error.to_record()
    else:
        record = ErrorRecord(
            error_id="unknown",
            error_type=type(error).__name__,
            message=str(error),
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.UNKNOWN,
            context=ErrorContext.capture(depth=1),
            traceback_str=traceback.format_exc() if debug else ""
        )
    
    result = {
        "error": record.message,
        "type": record.error_type,
        "severity": record.severity.value,
        "category": record.category.value
    }
    
    if debug:
        result["traceback"] = record.traceback_str
        result["context"] = {
            "function": record.context.function_name,
            "file": record.context.file_name,
            "line": record.context.line_number
        }
    
    return result


def die(message: str, code: int = 1) -> None:
    """
    打印错误消息并退出
    
    Args:
        message: 错误消息
        code: 退出码
    """
    sys.stderr.write(f"错误: {message}\n")
    sys.exit(code)


def safe_execute(
    func: Callable,
    *args,
    default: Any = None,
    handler: Optional[ErrorHandler] = None,
    **kwargs
) -> Any:
    """
    安全执行函数
    
    Args:
        func: 要执行的函数
        default: 发生错误时的默认返回值
        handler: 错误处理器
        args: 位置参数
        kwargs: 关键字参数
        
    Returns:
        函数返回值或默认值
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if handler:
            handler.handle(e)
        return default


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 重试延迟
        exceptions: 要捕获的异常类型
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
            raise last_error
        return wrapper
    return decorator


import os
