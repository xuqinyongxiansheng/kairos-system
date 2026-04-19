"""
事件总线（线程安全版）
实现模块间松耦合通信，所有共享状态受RLock保护
支持同步/异步事件处理、优先级调度、错误隔离、有界历史
"""

import asyncio
import logging
import threading
from collections import deque
from typing import Dict, Any, List, Callable, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json
import os

logger = logging.getLogger("EventBus")


class EventType(Enum):
    """事件类型枚举"""
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_PAUSED = "task_paused"
    TASK_RESUMED = "task_resumed"
    SKILL_CREATED = "skill_created"
    SKILL_EXECUTED = "skill_executed"
    SKILL_IMPROVED = "skill_improved"
    SKILL_DEPRECATED = "skill_deprecated"
    KNOWLEDGE_ADDED = "knowledge_added"
    LEARNING_STARTED = "learning_started"
    LEARNING_COMPLETED = "learning_completed"
    EVOLUTION_EVENT = "evolution_event"
    MILESTONE_REACHED = "milestone_reached"
    CAPABILITY_IMPROVED = "capability_improved"
    USER_INTERACTION = "user_interaction"
    USER_FEEDBACK = "user_feedback"
    USER_CORRECTION = "user_correction"
    METACOGNITION_TRIGGERED = "metacognition_triggered"
    SELF_ASSESSMENT = "self_assessment"
    REFLECTION_COMPLETED = "reflection_completed"
    SYSTEM_STARTED = "system_started"
    SYSTEM_STOPPED = "system_stopped"
    ERROR_OCCURRED = "error_occurred"
    WARNING_RAISED = "warning_raised"
    TOOL_CALLED = "tool_called"
    TOOL_COMPLETED = "tool_completed"
    TOOL_FAILED = "tool_failed"
    BROWSER_NAVIGATED = "browser_navigated"
    BROWSER_ACTION = "browser_action"
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"


@dataclass
class Event:
    """事件数据类"""
    type: EventType
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = "system"
    priority: int = 0
    id: str = field(default_factory=lambda: f"evt_{int(datetime.now().timestamp() * 1000)}")
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value if isinstance(self.type, EventType) else self.type,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source,
            "priority": self.priority,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class Subscription:
    """订阅信息"""
    handler: Callable
    priority: int = 0
    once: bool = False
    filter_func: Optional[Callable[[Event], bool]] = None
    id: str = field(default_factory=lambda: f"sub_{int(datetime.now().timestamp() * 1000)}")


class EventBus:
    """
    事件总线（线程安全版）

    所有共享状态通过 RLock 保护：
    - _handlers: 订阅者字典
    - _event_history: 事件历史（有界deque）
    - _middleware: 中间件列表
    - _error_handlers: 错误处理器列表
    """

    def __init__(self, max_history: int = 1000, persistence_path: str = None):
        self._lock = threading.RLock()
        self._handlers: Dict[Union[EventType, str], List[Subscription]] = {}
        self._event_history: deque = deque(maxlen=max_history)
        self._max_history = max_history
        self._persistence_path = persistence_path
        self._middleware: List[Callable] = []
        self._error_handlers: List[Callable] = []

        if persistence_path:
            os.makedirs(os.path.dirname(persistence_path), exist_ok=True)

        logger.info(f"事件总线初始化(线程安全版, max_history={max_history})")

    def subscribe(self, event_type: Union[EventType, str],
                 handler: Callable,
                 priority: int = 0,
                 once: bool = False,
                 filter_func: Callable[[Event], bool] = None) -> str:
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []

            subscription = Subscription(
                handler=handler, priority=priority,
                once=once, filter_func=filter_func
            )
            self._handlers[event_type].append(subscription)
            self._handlers[event_type].sort(key=lambda s: s.priority, reverse=True)

        logger.debug(f"订阅事件: {event_type} -> {handler.__name__}")
        return subscription.id

    def subscribe_once(self, event_type: Union[EventType, str],
                      handler: Callable,
                      priority: int = 0) -> str:
        return self.subscribe(event_type, handler, priority, once=True)

    def unsubscribe(self, subscription_id: str) -> bool:
        with self._lock:
            for event_type, subscriptions in self._handlers.items():
                for i, sub in enumerate(subscriptions):
                    if sub.id == subscription_id:
                        subscriptions.pop(i)
                        logger.debug(f"取消订阅: {subscription_id}")
                        return True
        return False

    def unsubscribe_all(self, event_type: Union[EventType, str] = None):
        with self._lock:
            if event_type:
                self._handlers[event_type] = []
            else:
                self._handlers.clear()
        logger.debug("取消所有订阅")

    async def publish(self, event_type: Union[EventType, str],
                     data: Dict[str, Any],
                     source: str = "system",
                     priority: int = 0,
                     correlation_id: str = None,
                     metadata: Dict[str, Any] = None) -> str:
        event = Event(
            type=event_type if isinstance(event_type, EventType)
                  else EventType(event_type) if event_type in [e.value for e in EventType]
                  else event_type,
            data=data, source=source, priority=priority,
            correlation_id=correlation_id, metadata=metadata or {},
        )

        with self._lock:
            middleware_snapshot = list(self._middleware)
        for middleware in middleware_snapshot:
            try:
                event = await middleware(event) if asyncio.iscoroutinefunction(middleware) else middleware(event)
                if event is None:
                    return None
            except Exception as e:
                logger.error(f"中间件错误: {e}")

        with self._lock:
            self._event_history.append(event)

        if self._persistence_path:
            await self._persist_event(event)

        await self._dispatch(event)

        logger.debug(f"发布事件: {event_type} (id={event.id})")
        return event.id

    def publish_sync(self, event_type: Union[EventType, str],
                    data: Dict[str, Any],
                    source: str = "system",
                    priority: int = 0) -> str:
        event = Event(
            type=event_type if isinstance(event_type, EventType) else event_type,
            data=data, source=source, priority=priority
        )
        with self._lock:
            middleware_snapshot = list(self._middleware)
        for middleware in middleware_snapshot:
            try:
                event = middleware(event) if not asyncio.iscoroutinefunction(middleware) else event
                if event is None:
                    return None
            except Exception as e:
                logger.error(f"中间件错误(同步): {e}")

        with self._lock:
            self._event_history.append(event)
        self._dispatch_sync(event)
        return event.id

    async def _dispatch(self, event: Event):
        event_type = event.type if isinstance(event.type, EventType) else event.type

        with self._lock:
            handlers = self._handlers.get(event_type)
            if handlers is None:
                return
            if len(handlers) <= 1:
                handlers_snapshot = handlers if handlers else []
            else:
                handlers_snapshot = list(handlers)

        to_remove = []
        for subscription in handlers_snapshot:
            if subscription.filter_func and not subscription.filter_func(event):
                continue
            try:
                if asyncio.iscoroutinefunction(subscription.handler):
                    await subscription.handler(event)
                else:
                    subscription.handler(event)
                if subscription.once:
                    to_remove.append(subscription.id)
            except Exception as e:
                logger.error(f"事件处理器错误: {e}")
                await self._handle_error(event, e)

        for sub_id in to_remove:
            self.unsubscribe(sub_id)

    def _dispatch_sync(self, event: Event):
        event_type = event.type if isinstance(event.type, EventType) else event.type
        with self._lock:
            handlers = self._handlers.get(event_type)
            if handlers is None:
                return
            if len(handlers) <= 1:
                handlers_snapshot = handlers if handlers else []
            else:
                handlers_snapshot = list(handlers)
        for subscription in handlers_snapshot:
            try:
                subscription.handler(event)
            except Exception as e:
                logger.error(f"事件处理器错误: {e}")

    async def _handle_error(self, event: Event, error: Exception):
        with self._lock:
            error_handlers_snapshot = list(self._error_handlers)
        for error_handler in error_handlers_snapshot:
            try:
                if asyncio.iscoroutinefunction(error_handler):
                    await error_handler(event, error)
                else:
                    error_handler(event, error)
            except Exception as e:
                logger.error(f"错误处理器异常: {e}")

    async def _persist_event(self, event: Event):
        if not self._persistence_path:
            return
        try:
            with open(self._persistence_path, 'a', encoding='utf-8') as f:
                f.write(event.to_json() + '\n')
        except Exception as e:
            logger.error(f"事件持久化失败: {e}")

    async def publish_batch(self, events: List[Dict[str, Any]],
                           source: str = "batch") -> List[str]:
        """批量发布事件（减少锁竞争，适合高频场景）"""
        event_objs = []
        with self._lock:
            middleware_snapshot = list(self._middleware)

        for ev in events:
            event = Event(
                type=ev.get("type", "system"),
                data=ev.get("data", {}),
                source=source,
                priority=ev.get("priority", 0),
                correlation_id=ev.get("correlation_id"),
                metadata=ev.get("metadata", {}),
            )
            for middleware in middleware_snapshot:
                try:
                    if not asyncio.iscoroutinefunction(middleware):
                        event = middleware(event)
                        if event is None:
                            break
                except Exception as e:
                    logger.warning(f"批量中间件错误: {e}")
            if event is not None:
                event_objs.append(event)

        with self._lock:
            for event in event_objs:
                self._event_history.append(event)
                await self._persist_event(event)

        for event in event_objs:
            await self._dispatch(event)

        return [e.id for e in event_objs]

    def publish_batch_sync(self, events: List[Dict[str, Any]],
                            source: str = "batch") -> List[str]:
        """同步批量发布事件"""
        event_objs = []
        with self._lock:
            middleware_snapshot = list(self._middleware)

        for ev in events:
            event = Event(
                type=ev.get("type", "system"),
                data=ev.get("data", {}),
                source=source,
                priority=ev.get("priority", 0),
                correlation_id=ev.get("correlation_id"),
                metadata=ev.get("metadata", {}),
            )
            for middleware in middleware_snapshot:
                try:
                    event = middleware(event)
                    if event is None:
                        break
                except Exception as e:
                    logger.warning(f"批量中间件错误(同步): {e}")
            if event is not None:
                event_objs.append(event)

        with self._lock:
            for event in event_objs:
                self._event_history.append(event)

        for event in event_objs:
            self._dispatch_sync(event)

        return [e.id for e in event_objs]

    def add_middleware(self, middleware: Callable):
        with self._lock:
            self._middleware.append(middleware)

    def add_error_handler(self, handler: Callable):
        with self._lock:
            self._error_handlers.append(handler)

    def get_history(self, event_type: Union[EventType, str] = None,
                   limit: int = 100,
                   source: str = None) -> List[Event]:
        with self._lock:
            events = list(self._event_history)

        if event_type:
            events = [e for e in events if e.type == event_type or
                     (isinstance(e.type, EventType) and e.type.value == event_type)]
        if source:
            events = [e for e in events if e.source == source]

        return events[-limit:]

    def get_event(self, event_id: str) -> Optional[Event]:
        with self._lock:
            for event in self._event_history:
                if event.id == event_id:
                    return event
        return None

    def get_subscriptions(self, event_type: Union[EventType, str] = None) -> Dict[str, Any]:
        with self._lock:
            if event_type:
                if event_type in self._handlers:
                    return {
                        "event_type": event_type.value if isinstance(event_type, EventType) else event_type,
                        "subscriptions": [
                            {"id": sub.id, "handler": sub.handler.__name__,
                             "priority": sub.priority, "once": sub.once}
                            for sub in self._handlers[event_type]
                        ]
                    }
                return {}
            return {
                "event_types": list(self._handlers.keys()),
                "total_subscriptions": sum(len(subs) for subs in self._handlers.values())
            }

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_events = len(self._event_history)
            event_types = {
                et.value if isinstance(et, EventType) else et: len(subs)
                for et, subs in self._handlers.items()
            }
            total_subs = sum(len(subs) for subs in self._handlers.values())
            mid_count = len(self._middleware)
            err_count = len(self._error_handlers)
        return {
            "total_events": total_events,
            "event_types": event_types,
            "total_subscriptions": total_subs,
            "middleware_count": mid_count,
            "error_handlers_count": err_count
        }

    def clear_history(self):
        with self._lock:
            self._event_history.clear()
        logger.info("事件历史已清除")


_event_bus_lock = threading.Lock()
_event_bus_instance: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """获取全局事件总线（DCLP）"""
    global _event_bus_instance
    if _event_bus_instance is not None:
        return _event_bus_instance
    with _event_bus_lock:
        if _event_bus_instance is None:
            _event_bus_instance = EventBus()
    return _event_bus_instance


def on_event(event_type: Union[EventType, str], priority: int = 0):
    """事件订阅装饰器"""
    def decorator(func):
        get_event_bus().subscribe(event_type, func, priority)
        return func
    return decorator
