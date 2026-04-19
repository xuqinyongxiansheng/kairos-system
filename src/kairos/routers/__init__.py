"""
路由模块包
统一管理所有 API 路由
"""

from .agent import router as agent_router
from .chat import router as chat_router
from .enhanced import router as enhanced_router
from .health import router as health_router
from .services import router as services_router
from .wiki import router as wiki_router
from .auth import router as auth_router
from .core import router as core_router
from .events import router as events_router

__all__ = [
    "agent_router",
    "chat_router",
    "enhanced_router",
    "health_router",
    "services_router",
    "wiki_router",
    "auth_router",
    "core_router",
    "events_router"
]
