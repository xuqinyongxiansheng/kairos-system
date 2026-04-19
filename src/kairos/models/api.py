"""
API 响应模型
定义所有 API 端点的请求和响应模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# 认证相关模型
class AuthRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    api_key: str = Field(..., min_length=1)

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

# 聊天相关模型
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1024

class ChatResponse(BaseModel):
    response: str
    model: str
    tokens: Dict[str, int]
    duration: float

# 健康检查相关模型
class HealthResponse(BaseModel):
    status: str
    services: Dict[str, bool]
    timestamp: float

# 系统核心相关模型
class SystemCoreResponse(BaseModel):
    name: str
    version: str
    architecture: str
    default_model: str
    status: str

# 通用响应模型
class ErrorResponse(BaseModel):
    error: str
    error_id: Optional[str] = None
    detail: Optional[str] = None

class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: float
