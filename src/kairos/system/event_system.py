#!/usr/bin/env python3
"""
事件驱动系统模块 - 提供完整的事件处理机制
"""

import asyncio
import logging
from typing import Dict, Any, Callable, List, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger("EventSystem")


class EventType(Enum):
    """事件类型枚举"""
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"
    
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    
    COMPONENT_REGISTERED = "component.registered"
    COMPONENT_UNREGISTERED = "component.unregistered"
    COMPONENT_HEALTH_CHECK = "component.health_check"
    
    DATA_CREATED = "data.created"
    DATA_UPDATED = "data.updated"
    DATA_DELETED = "data.deleted"
    DATA_SYNCED = "data.synced"
    
    USER_LOGIN = "security.user_login"
    USER_LOGOUT = "security.user_logout"
    PERMISSION_DENIED = "security.permission_denied"
    SECURITY_ALERT = "security.alert"
    
    RESOURCE_USAGE_HIGH = "monitoring.resource_high"
    PERFORMANCE_DEGRADED = "monitoring.performance_degraded"
    HEALTH_CHECK_FAILED = "monitoring.health_failed"
    
    CUSTOM_EVENT = "custom.event"


class Event:
    """事件基类"""
    
    def __init__(self, event_type: str, data: Dict[str, Any], source: str = "system", priority: int = 0):
        """初始化事件"""
        self.event_type = event_type
        self.data = data
        self.source = source
        self.priority = priority
        self.timestamp = datetime.now().isoformat()
        self.event_id = f"{event_type}.{int(datetime.now().timestamp() * 1000)}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "data": self.data,
            "source": self.source,
            "priority": self.priority,
            "timestamp": self.timestamp
        }
    
    def __str__(self):
        """字符串表示"""
        return f"Event({self.event_type}, source={self.source}, priority={self.priority})"


class EventBus:
    """事件总线"""
    
    def __init__(self, max_queue_size: int = 1000):
        """初始化事件总线"""
        self._handlers: Dict[str, List[Callable]] = {}
        self._event_queue = asyncio.Queue(maxsize=max_queue_size)
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._event_history: List[Dict[str, Any]] = []
        self._max_history = 1000
        
    async def start(self):
        """启动事件总线"""
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._process_events())
            logger.info("EventBus started")
    
    async def stop(self):
        """停止事件总线"""
        if self._running:
            self._running = False
            if self._worker_task:
                self._worker_task.cancel()
                try:
                    await self._worker_task
                except asyncio.CancelledError:
                    pass
            logger.info("EventBus stopped")
    
    def register_handler(self, event_type: str, handler: Callable[[Dict[str, Any]], Any]):
        """注册事件处理器"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Registered handler for event type: {event_type}")
    
    def unregister_handler(self, event_type: str, handler: Callable[[Dict[str, Any]], Any]):
        """注销事件处理器"""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                if not self._handlers[event_type]:
                    del self._handlers[event_type]
                logger.debug(f"Unregistered handler for event type: {event_type}")
            except ValueError:
                logger.warning(f"Handler not found for event type: {event_type}")
    
    async def publish(self, event: Event):
        """发布事件"""
        if not self._running:
            logger.warning("EventBus is not running")
            return
        
        event_dict = event.to_dict()
        
        self._event_history.append(event_dict)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        try:
            await self._event_queue.put(event_dict)
            logger.debug(f"Published event: {event.event_type}")
        except asyncio.QueueFull:
            logger.warning(f"Event queue is full, dropping event: {event.event_type}")
    
    async def publish_event(self, event_type: str, data: Dict[str, Any], source: str = "system", priority: int = 0):
        """便捷方法：发布事件"""
        event = Event(event_type, data, source, priority)
        await self.publish(event)
    
    async def _process_events(self):
        """处理事件队列"""
        while self._running:
            try:
                event = await self._event_queue.get()
                await self._dispatch_event(event)
                self._event_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")
    
    async def _dispatch_event(self, event: Dict[str, Any]):
        """分发事件到处理器"""
        event_type = event["event_type"]
        
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")
        
        if "*" in self._handlers:
            for handler in self._handlers["*"]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Error in wildcard event handler: {e}")
    
    def get_event_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取事件历史"""
        return self._event_history[-limit:]
    
    def get_active_event_types(self) -> List[str]:
        """获取活跃的事件类型"""
        return list(self._handlers.keys())
    
    def get_handler_count(self, event_type: str) -> int:
        """获取事件处理器数量"""
        return len(self._handlers.get(event_type, []))


class EventSystem:
    """事件系统"""
    
    def __init__(self):
        """初始化事件系统"""
        self.event_bus = EventBus()
        self._event_registry: Dict[str, Any] = {}
        self._subscribers: Dict[str, List[Callable]] = {}
        
    async def start(self):
        """启动事件系统"""
        await self.event_bus.start()
        logger.info("EventSystem started")
    
    async def stop(self):
        """停止事件系统"""
        await self.event_bus.stop()
        logger.info("EventSystem stopped")
    
    def register_event_type(self, event_name: str, event_schema: Optional[Dict[str, Any]] = None):
        """注册事件类型"""
        self._event_registry[event_name] = {
            "schema": event_schema,
            "registered_at": datetime.now().isoformat()
        }
        logger.info(f"Registered event type: {event_name}")
    
    def register_subscriber(self, event_type: str, subscriber: Callable[[Dict[str, Any]], Any]):
        """注册订阅者"""
        self.event_bus.register_handler(event_type, subscriber)
    
    def unregister_subscriber(self, event_type: str, subscriber: Callable[[Dict[str, Any]], Any]):
        """注销订阅者"""
        self.event_bus.unregister_handler(event_type, subscriber)
    
    async def emit(self, event_type: str, data: Dict[str, Any], source: str = "system", priority: int = 0):
        """触发事件"""
        await self.event_bus.publish_event(event_type, data, source, priority)
    
    async def emit_system_event(self, event_type: str, data: Dict[str, Any], priority: int = 10):
        """触发系统事件"""
        await self.emit(f"system.{event_type}", data, "system", priority)
    
    async def emit_task_event(self, task_id: str, event_type: str, data: Dict[str, Any], priority: int = 5):
        """触发任务事件"""
        event_data = {"task_id": task_id, **data}
        await self.emit(f"task.{event_type}", event_data, "task_system", priority)
    
    async def emit_component_event(self, component_id: str, event_type: str, data: Dict[str, Any], priority: int = 3):
        """触发组件事件"""
        event_data = {"component_id": component_id, **data}
        await self.emit(f"component.{event_type}", event_data, component_id, priority)
    
    def get_registered_events(self) -> Dict[str, Any]:
        """获取已注册的事件类型"""
        return self._event_registry.copy()
    
    def get_event_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取事件历史"""
        return self.event_bus.get_event_history(limit)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取事件系统统计信息"""
        history = self.event_bus.get_event_history()
        active_types = self.event_bus.get_active_event_types()
        
        event_counts = {}
        for event in history:
            event_type = event["event_type"]
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        return {
            "registered_events": len(self._event_registry),
            "active_event_types": len(active_types),
            "total_events_processed": len(history),
            "event_counts": event_counts,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "status": "active",
            "registered_events": len(self._event_registry),
            "active_handlers": len(self.event_bus.get_active_event_types())
        }


_global_event_system = None


def get_event_system() -> EventSystem:
    """获取全局事件系统实例"""
    global _global_event_system
    
    if _global_event_system is None:
        _global_event_system = EventSystem()
    
    return _global_event_system


async def initialize_event_system():
    """初始化事件系统"""
    event_system = get_event_system()
    await event_system.start()
    return event_system


async def shutdown_event_system():
    """关闭事件系统"""
    global _global_event_system
    
    if _global_event_system:
        await _global_event_system.stop()
        _global_event_system = None


event_system = get_event_system()


def get_events(limit: int = 100) -> List[Dict[str, Any]]:
    """获取事件列表（兼容旧接口）"""
    return event_system.get_event_history(limit)


def get_events_by_type(event_type: str, limit: int = 100) -> List[Dict[str, Any]]:
    """根据类型获取事件（兼容旧接口）"""
    events = event_system.get_event_history(limit)
    return [event for event in events if event["event_type"] == event_type]
