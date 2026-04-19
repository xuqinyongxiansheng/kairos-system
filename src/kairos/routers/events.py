"""
事件路由模块
处理事件系统的 API 端点
"""

from fastapi import APIRouter
from typing import Dict, Any
import time

from kairos.system.event_system import get_event_system, EventType

router = APIRouter(prefix="/api/events", tags=["事件系统"])

@router.get("")
async def get_events(limit: int = 100):
    """获取事件历史"""
    event_system = get_event_system()
    events = event_system.get_event_history(limit)
    return {
        "events": events,
        "count": len(events),
        "timestamp": time.time()
    }

@router.get("/stats")
async def get_event_stats():
    """获取事件统计"""
    event_system = get_event_system()
    stats = event_system.get_statistics()
    return {
        "stats": stats,
        "timestamp": time.time()
    }

@router.get("/types")
async def get_event_types():
    """获取事件类型"""
    event_system = get_event_system()
    event_types = [e.value for e in EventType]
    registered = event_system.get_registered_events()
    return {
        "event_types": event_types,
        "registered_events": registered,
        "timestamp": time.time()
    }

@router.get("/health")
async def event_system_health():
    """事件系统健康检查"""
    event_system = get_event_system()
    status = event_system.get_status()
    return {
        "status": status,
        "timestamp": time.time()
    }

@router.post("/test")
async def test_event_system():
    """测试事件系统"""
    event_system = get_event_system()
    await event_system.emit(EventType.SYSTEM_WARNING.value, {"message": "Test event", "level": "info"})
    return {
        "message": "Test event emitted",
        "timestamp": time.time()
    }
