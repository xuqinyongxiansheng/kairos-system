#!/usr/bin/env python3
"""
输入验证中间件
验证用户输入，防止注入攻击
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable

from kairos.system.security import get_security_manager


class InputValidationMiddleware(BaseHTTPMiddleware):
    """输入验证中间件"""
    
    def __init__(self, app):
        super().__init__(app)
        self.security_manager = get_security_manager()
    
    async def dispatch(self, request: Request, call_next: Callable):
        """验证输入"""
        # 验证请求方法
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                # 读取请求体
                body = await request.json()
                
                # 验证输入
                if not self._validate_input(body):
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid input: potentially dangerous content detected"
                    )
                
            except Exception as e:
                # 如果不是JSON请求，继续处理
                pass
        
        # 验证查询参数
        for key, value in request.query_params.items():
            if isinstance(value, str) and not self.security_manager.validate_input(value):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid input in parameter '{key}'"
                )
        
        # 处理请求
        response = await call_next(request)
        return response
    
    def _validate_input(self, data) -> bool:
        """递归验证输入数据"""
        if isinstance(data, str):
            return self.security_manager.validate_input(data)
        elif isinstance(data, dict):
            for key, value in data.items():
                if not self._validate_input(key) or not self._validate_input(value):
                    return False
        elif isinstance(data, list):
            for item in data:
                if not self._validate_input(item):
                    return False
        return True