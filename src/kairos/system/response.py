"""
统一响应格式模块
提供标准化的 API 响应格式
"""

from typing import Any, Optional, Dict, Generic, TypeVar
from pydantic import BaseModel
import time

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应格式"""
    success: bool
    message: str
    data: Optional[T] = None
    error: Optional[Dict[str, Any]] = None
    timestamp: float
    request_id: Optional[str] = None
    
    @classmethod
    def success(cls, data: Optional[T] = None, message: str = "操作成功") -> 'ApiResponse[T]':
        """成功响应"""
        return cls(
            success=True,
            message=message,
            data=data,
            error=None,
            timestamp=time.time()
        )
    
    @classmethod
    def error(cls, message: str, error: Optional[Dict[str, Any]] = None) -> 'ApiResponse[None]':
        """错误响应"""
        return cls(
            success=False,
            message=message,
            data=None,
            error=error or {"message": message},
            timestamp=time.time()
        )
    
    @classmethod
    def validation_error(cls, message: str, errors: Optional[Dict[str, Any]] = None) -> 'ApiResponse[None]':
        """验证错误响应"""
        return cls(
            success=False,
            message=message,
            data=None,
            error={"type": "validation_error", "errors": errors or {}}, 
            timestamp=time.time()
        )
    
    @classmethod
    def server_error(cls, message: str = "服务器内部错误", error: Optional[Dict[str, Any]] = None) -> 'ApiResponse[None]':
        """服务器错误响应"""
        return cls(
            success=False,
            message=message,
            data=None,
            error=error or {"type": "server_error"},
            timestamp=time.time()
        )
    
    @classmethod
    def not_found(cls, message: str = "资源不存在") -> 'ApiResponse[None]':
        """资源不存在响应"""
        return cls(
            success=False,
            message=message,
            data=None,
            error={"type": "not_found"},
            timestamp=time.time()
        )
    
    @classmethod
    def unauthorized(cls, message: str = "未授权访问") -> 'ApiResponse[None]':
        """未授权响应"""
        return cls(
            success=False,
            message=message,
            data=None,
            error={"type": "unauthorized"},
            timestamp=time.time()
        )
    
    @classmethod
    def forbidden(cls, message: str = "访问被禁止") -> 'ApiResponse[None]':
        """禁止访问响应"""
        return cls(
            success=False,
            message=message,
            data=None,
            error={"type": "forbidden"},
            timestamp=time.time()
        )

def create_response(
    success: bool,
    data: Optional[Any] = None,
    message: str = "",
    error: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """创建标准响应字典（兼容旧接口）"""
    return {
        "success": success,
        "message": message,
        "data": data,
        "error": error,
        "timestamp": time.time()
    }
