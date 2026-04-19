"""
健康检查路由
提供存活、就绪、详细三级健康检查
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import time

from kairos.system.degradation import get_degradation_manager, ServiceLevel

router = APIRouter(prefix="/api", tags=["健康检查"])

_health_checker = None
_model_cache = None

async def check_ollama_connection():
    """检查 Ollama 连接"""
    try:
        from kairos.system.llm_client import get_llm_client
        client = get_llm_client()
        models = await client.list()
        return models is not None
    except Exception:
        return False

def init_health_deps(health_checker, model_cache):
    global _health_checker, _model_cache
    _health_checker = health_checker
    _model_cache = model_cache

@router.get("/health")
async def health():
    """基础健康检查"""
    models = []
    cache_age = None
    if _model_cache:
        try:
            models = await _model_cache.get_models()
            cache_age = time.time() - _model_cache._last_update if _model_cache._last_update > 0 else None
        except Exception:
            pass
    
    # 集成降级管理
    degradation_manager = get_degradation_manager()
    service_level = await degradation_manager.evaluate_service_level()
    ollama_healthy = await check_ollama_connection()
    
    return {
        "status": "ok" if service_level == ServiceLevel.FULL else "degraded",
        "service_level": service_level.name,
        "ollama_healthy": ollama_healthy,
        "models": models,
        "default_model": _model_cache._models[0] if _model_cache and _model_cache._models else "gemma4:e4b",
        "cache_age": cache_age,
        "degradation_status": degradation_manager.get_status(),
        "timestamp": time.time()
    }

@router.get("/health/detailed")
async def health_detailed():
    """详细健康检查"""
    if _health_checker:
        result = _health_checker.check_all()
        # 添加降级状态
        degradation_manager = get_degradation_manager()
        service_level = await degradation_manager.evaluate_service_level()
        result["service_level"] = service_level.name
        result["degradation_status"] = degradation_manager.get_status()
        return result
    return {"status": "ok", "detail": "健康检查器未初始化"}

@router.get("/ready")
async def readiness():
    """就绪检查"""
    if _health_checker:
        ready, message = _health_checker.check_ready()
        if ready:
            return {"status": "ready", "message": message}
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "message": message}
        )
    return {"status": "ready", "message": "默认就绪"}

@router.get("/live")
async def liveness():
    """存活检查"""
    if _health_checker:
        if _health_checker.check_live():
            return {"status": "alive"}
        return JSONResponse(
            status_code=503,
            content={"status": "terminating"}
        )
    return {"status": "alive"}

@router.get("/degradation/status")
async def degradation_status():
    """降级状态检查"""
    degradation_manager = get_degradation_manager()
    service_level = await degradation_manager.evaluate_service_level()
    status = degradation_manager.get_status()
    ollama_healthy = await check_ollama_connection()
    
    return {
        "service_level": status["current_level"],
        "ollama_healthy": ollama_healthy,
        "degradation_details": status,
        "timestamp": time.time()
    }
