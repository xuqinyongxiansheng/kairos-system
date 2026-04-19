"""
核心路由模块
处理系统核心功能的 API 端点
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import time
import psutil

from kairos.system.config import settings
from kairos.version import VERSION as SYSTEM_CORE_VERSION, SYSTEM_NAME as SYSTEM_CORE_NAME, SYSTEM_CODENAME
from kairos.system.llm_client import get_llm_client
from kairos.system.response import ApiResponse

router = APIRouter(prefix="/api", tags=["核心"])

@router.get("/core")
async def core_info():
    """核心系统信息"""
    data = {
        "version": SYSTEM_CORE_VERSION,
        "name": SYSTEM_CORE_NAME,
        "codename": SYSTEM_CODENAME,
        "env": settings.server.env,
        "debug": settings.server.debug,
        "timestamp": time.time()
    }
    return ApiResponse.success(data=data, message="获取核心信息成功")

@router.get("/performance")
async def performance_metrics():
    """系统性能指标"""
    try:
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)
        disk = psutil.disk_usage('/')
        
        data = {
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used_percent": memory.percent
            },
            "cpu": {
                "usage_percent": cpu
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "used_percent": disk.percent
            },
            "timestamp": time.time()
        }
        return ApiResponse.success(data=data, message="获取性能指标成功")
    except Exception as e:
        return ApiResponse.server_error(message=f"获取性能指标失败: {str(e)}")

@router.post("/refresh-models")
async def refresh_models():
    """刷新模型列表"""
    try:
        client = get_llm_client()
        models = await client.list()
        data = {
            "models": models,
            "count": len(models) if models else 0,
            "timestamp": time.time()
        }
        return ApiResponse.success(data=data, message="刷新模型列表成功")
    except Exception as e:
        return ApiResponse.server_error(message=f"刷新模型失败: {str(e)}")

@router.get("/versions")
async def versions():
    """版本信息"""
    data = {
        "system": {
            "version": SYSTEM_CORE_VERSION,
            "name": SYSTEM_CORE_NAME,
            "codename": SYSTEM_CODENAME
        },
        "components": {
            "fastapi": "0.104.1",
            "python": "3.11+"
        },
        "timestamp": time.time()
    }
    return ApiResponse.success(data=data, message="获取版本信息成功")
