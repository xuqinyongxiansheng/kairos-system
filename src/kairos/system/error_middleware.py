#!/usr/bin/env python3
"""
统一错误处理中间件 v4.1
提供全局异常捕获、标准化错误响应、请求追踪

使用方式（在main.py中注册）:
    from kairos.system.error_middleware import register_error_handlers
    app = FastAPI()
    register_error_handlers(app)
"""

import traceback
import uuid
import logging
import time
from typing import Optional, Dict, Any, List

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException, RequestValidationError
from pydantic import ValidationError

logger = logging.getLogger("ErrorHandler")


class AppError(Exception):
    """应用层错误基类"""

    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = 500,
        details: Optional[Dict] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class NotFoundError(AppError):
    """资源未找到"""

    def __init__(self, message: str = "资源未找到"):
        super().__init__(message, "NOT_FOUND", 404)


class ValidationError(AppError):
    """参数校验失败"""

    def __init__(self, message: str = "参数校验失败", details: Optional[Dict] = None):
        super().__init__(message, "VALIDATION_ERROR", 422, details)


class RateLimitError(AppError):
    """速率限制"""

    def __init__(self, message: str = "请求过于频繁，请稍后重试"):
        super().__init__(message, "RATE_LIMITED", 429)


class ServiceUnavailableError(AppError):
    """服务不可用"""

    def __init__(self, message: str = "服务暂时不可用"):
        super().__init__(message, "SERVICE_UNAVAILABLE", 503)


def _build_error_response(
    request: Request,
    code: str,
    message: str,
    status_code: int,
    details: Optional[Dict] = None,
    trace_id: Optional[str] = None
) -> JSONResponse:
    """构建标准错误响应"""
    trace_id = trace_id or getattr(request.state, 'trace_id', uuid.uuid4().hex[:12])

    body: Dict[str, Any] = {
        "code": status_code,
        "message": message,
        "error": code,
        "traceId": trace_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    if details:
        body["details"] = details

    # 开发环境显示完整堆栈
    try:
        from kairos.system.config import settings
        if settings.server.debug and status_code >= 500:
            body["stack"] = traceback.format_exc()[-500:]
    except Exception:
        pass

    return JSONResponse(
        status_code=status_code,
        content=body,
        headers={"X-Trace-ID": trace_id}
    )


async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    """处理应用层自定义错误"""
    logger.warning(
        "[%s] 应用错误 [%s] %s | %s %s",
        getattr(request.state, 'trace_id', '?'),
        exc.code,
        exc.message,
        request.method,
        request.url.path
    )
    return _build_error_response(
        request, exc.code, exc.message, exc.status_code, exc.details
    )


async def _handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    """处理FastAPI内置HTTP异常"""
    logger.warning(
        "[%s] HTTP %d: %s | %s %s",
        getattr(request.state, 'trace_id', '?'),
        exc.status_code,
        exc.detail,
        request.method,
        request.url.path
    )
    return _build_error_response(
        request,
        f"HTTP_{exc.status_code}",
        str(exc.detail),
        exc.status_code
    )


async def _handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """处理请求参数校验错误"""
    errors: List[Dict[str, Any]] = []
    for err in exc.errors():
        loc = " → ".join(str(l) for l in err.get("loc", []))
        errors.append({
            "field": loc,
            "message": err.get("msg", ""),
            "type": err.get("type", "")
        })

    logger.warning(
        "[%s] 校验失败 (%d个字段) | %s %s",
        getattr(request.state, 'trace_id', '?'),
        len(errors),
        request.method,
        request.url.path
    )
    return _build_error_response(
        request,
        "VALIDATION_ERROR",
        "请求参数校验失败",
        422,
        {"fields": errors}
    )


async def _handle_unhandled(request: Request, exc: Exception) -> JSONResponse:
    """兜底：处理未预期的异常"""
    trace_id = getattr(request.state, 'trace_id', uuid.uuid4().hex[:12])
    logger.error(
        "[%s] 未处理异常: %s | %s %s\n%s",
        trace_id,
        repr(exc),
        request.method,
        request.url.path,
        traceback.format_exc()
    )
    return _build_error_response(
        request,
        "INTERNAL_ERROR",
        "服务器内部错误，请稍后重试",
        500,
        trace_id=trace_id
    )


def register_error_handlers(app):
    """注册全局错误处理器到FastAPI应用

    Args:
        app: FastAPI应用实例
    """
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(HTTPException, _handle_http_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)

    # 兜底处理器（必须最后注册）
    @app.exception_handler(Exception)
    async def catch_all(request: Request, exc: Exception):
        return await _handle_unhandled(request, exc)

    logger.info("统一错误处理中间件已注册")
