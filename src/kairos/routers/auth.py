"""
认证路由模块
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any
import time

from kairos.system.security import SecurityManager
from kairos.system.config import settings
from kairos.models.api import AuthResponse

router = APIRouter(prefix="/api/auth", tags=["认证"])
security = HTTPBearer()

@router.post("/token", response_model=AuthResponse)
async def create_token():
    """创建认证令牌"""
    security_manager = SecurityManager()
    token = security_manager.create_token()
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": time.time() + 3600 * 24 * 7
    }

@router.get("/verify")
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """验证令牌"""
    security_manager = SecurityManager()
    try:
        payload = security_manager.verify_token(credentials.credentials)
        return {
            "valid": True,
            "payload": payload,
            "message": "Token is valid"
        }
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials"
        )
