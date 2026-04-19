"""
import logging
统一事件追踪系统 - 整合CLI-Anything的分析追踪模式
logger = logging.getLogger("unified_event_tracker")

设计模式来源:
- cli_hub/analytics.py: 非阻塞事件追踪
- 环境检测和Agent识别

核心特性:
1. 非阻塞异步事件发送
2. 线程池管理
3. 环境检测
4. 批量事件处理
5. 离线队列支持
"""

from __future__ import annotations

import atexit
import json
import os
import platform
import queue
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class EventType(Enum):
    """事件类型枚举"""
    PAGE_VIEW = "page_view"
    CLICK = "click"
    SEARCH = "search"
    INSTALL = "install"
    UNINSTALL = "uninstall"
    ERROR = "error"
    PERFORMANCE = "performance"
    CUSTOM = "custom"
    VISIT_HUMAN = "visit_human"
    VISIT_AGENT = "visit_agent"
    FIRST_RUN = "first_run"


class EventPriority(Enum):
    """事件优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Event:
    """事件数据结构"""
    name: str
    event_type: EventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: Dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    url: str = "/"
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "priority": self.priority.value,
            "url": self.url,
            "session_id": self.session_id,
            "user_id": self.user_id
        }


@dataclass
class TrackerConfig:
    """追踪器配置"""
    endpoint: str = ""
    website_id: str = ""
    hostname: str = "localhost"
    enabled: bool = True
    batch_size: int = 10
    flush_interval: int = 30
    max_queue_size: int = 1000
    timeout: int = 5
    retry_count: int = 3
    retry_delay: float = 1.0
    offline_storage: bool = True
    storage_dir: str = ""
    user_agent: str = ""


class EventQueue:
    """
    事件队列
    
    线程安全的事件队列，支持优先级排序
    """
    
    def __init__(self, max_size: int = 1000):
        self._queue: List[Event] = []
        self._lock = threading.Lock()
        self._max_size = max_size
    
    def put(self, event: Event) -> bool:
        """添加事件"""
        with self._lock:
            if len(self._queue) >= self._max_size:
                self._queue.pop(0)
            self._queue.append(event)
            return True
    
    def get_batch(self, size: int) -> List[Event]:
        """获取一批事件"""
        with self._lock:
            batch = self._queue[:size]
            self._queue = self._queue[size:]
            return batch
    
    def peek(self, size: int = 10) -> List[Event]:
        """查看事件但不移除"""
        with self._lock:
            return self._queue[:size]
    
    def size(self) -> int:
        """获取队列大小"""
        with self._lock:
            return len(self._queue)
    
    def clear(self) -> None:
        """清空队列"""
        with self._lock:
            self._queue.clear()


class OfflineStorage:
    """
    离线存储
    
    在网络不可用时存储事件
    """
    
    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
    
    def save(self, events: List[Event]) -> bool:
        """保存事件到离线存储"""
        if not events:
            return True
        
        with self._lock:
            try:
                filename = f"events_{int(time.time() * 1000)}.json"
                filepath = self.storage_dir / filename
                
                data = [e.to_dict() for e in events]
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                return True
            except Exception:
                return False
    
    def load_pending(self) -> List[Event]:
        """加载待发送事件"""
        events = []
        
        with self._lock:
            for filepath in sorted(self.storage_dir.glob("events_*.json")):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    for item in data:
                        event = Event(
                            name=item.get("name", ""),
                            event_type=EventType(item.get("type", "custom")),
                            data=item.get("data", {}),
                            priority=EventPriority(item.get("priority", 2)),
                            url=item.get("url", "/")
                        )
                        events.append(event)
                    
                    filepath.unlink()
                except Exception:
                    logger.debug(f"忽略异常: ", exc_info=True)
                    pass
        
        return events
    
    def clear(self) -> None:
        """清空离线存储"""
        with self._lock:
            for filepath in self.storage_dir.glob("events_*.json"):
                filepath.unlink()


class EnvironmentDetector:
    """
    环境检测器
    
    检测运行环境和Agent类型
    """
    
    AGENT_INDICATORS = [
        "CLAUDE_CODE",
        "CODEX",
        "CURSOR_SESSION",
        "CLINE_SESSION",
        "COPILOT",
        "AIDER",
        "CONTINUE_SESSION",
        "GPT_ENGINEER",
        "SMOL_DEVELOPER",
        "DEVIN_SESSION",
    ]
    
    @classmethod
    def is_agent(cls) -> bool:
        """检测是否在Agent环境中运行"""
        for var in cls.AGENT_INDICATORS:
            if os.environ.get(var):
                return True
        
        import sys
        if not sys.stdin.isatty():
            return True
        
        return False
    
    @classmethod
    def get_platform_info(cls) -> Dict[str, str]:
        """获取平台信息"""
        return {
            "system": platform.system().lower(),
            "machine": platform.machine().lower(),
            "python_version": platform.python_version(),
            "is_agent": str(cls.is_agent()).lower()
        }
    
    @classmethod
    def get_environment_vars(cls) -> Dict[str, bool]:
        """获取环境变量状态"""
        return {
            var: bool(os.environ.get(var))
            for var in cls.AGENT_INDICATORS
        }


class UnifiedEventTracker:
    """
    统一事件追踪系统
    
    整合了CLI-Anything中的分析追踪模式:
    - 非阻塞异步事件发送
    - 线程池管理
    - 环境检测
    - 批量事件处理
    - 离线队列支持
    """
    
    _instance: Optional['UnifiedEventTracker'] = None
    _lock = threading.Lock()
    
    def __new__(cls, config: Optional[TrackerConfig] = None):
        """单例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, config: Optional[TrackerConfig] = None):
        if self._initialized:
            return
        
        self.config = config or TrackerConfig()
        self._event_queue = EventQueue(max_size=self.config.max_queue_size)
        self._offline_storage: Optional[OfflineStorage] = None
        
        if self.config.offline_storage and self.config.storage_dir:
            self._offline_storage = OfflineStorage(self.config.storage_dir)
        
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._flush_event = threading.Event()
        self._pending_threads: List[threading.Thread] = []
        self._threads_lock = threading.Lock()
        
        self._event_count = 0
        self._success_count = 0
        self._error_count = 0
        
        self._session_id: Optional[str] = None
        self._user_id: Optional[str] = None
        
        self._initialized = True
        
        atexit.register(self._flush_on_exit)
        
        if self.config.enabled:
            self._start_worker()
    
    def _start_worker(self) -> None:
        """启动工作线程"""
        if self._worker_thread and self._worker_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True
        )
        self._worker_thread.start()
    
    def _worker_loop(self) -> None:
        """工作线程循环"""
        while not self._stop_event.is_set():
            if self._event_queue.size() >= self.config.batch_size:
                self._flush()
            elif self._flush_event.wait(timeout=self.config.flush_interval):
                self._flush_event.clear()
                if self._event_queue.size() > 0:
                    self._flush()
    
    def _flush(self) -> None:
        """刷新事件队列"""
        if not REQUESTS_AVAILABLE:
            return
        
        batch = self._event_queue.get_batch(self.config.batch_size)
        if not batch:
            return
        
        if self._offline_storage:
            pending = self._offline_storage.load_pending()
            if pending:
                batch = pending + batch
        
        success = self._send_batch(batch)
        
        if not success and self._offline_storage:
            self._offline_storage.save(batch)
    
    def _send_batch(self, events: List[Event]) -> bool:
        """发送一批事件"""
        if not self.config.endpoint or not REQUESTS_AVAILABLE:
            return False
        
        payload = {
            "type": "batch",
            "payload": {
                "website": self.config.website_id,
                "hostname": self.config.hostname,
                "events": [e.to_dict() for e in events]
            }
        }
        
        headers = {
            "User-Agent": self.config.user_agent,
            "Content-Type": "application/json"
        }
        
        for attempt in range(self.config.retry_count):
            try:
                response = requests.post(
                    self.config.endpoint,
                    json=payload,
                    headers=headers,
                    timeout=self.config.timeout
                )
                
                if response.status_code < 400:
                    self._success_count += len(events)
                    return True
                
            except Exception:
                logger.debug(f"忽略异常: ", exc_info=True)
                pass
            
            if attempt < self.config.retry_count - 1:
                time.sleep(self.config.retry_delay * (attempt + 1))
        
        self._error_count += len(events)
        return False
    
    def _flush_on_exit(self) -> None:
        """退出时刷新"""
        self._stop_event.set()
        
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5)
        
        with self._threads_lock:
            threads = list(self._pending_threads)
        for t in threads:
            t.join(timeout=3)
        
        if self._event_queue.size() > 0:
            batch = self._event_queue.get_batch(self._event_queue.size())
            if batch:
                if self._offline_storage:
                    self._offline_storage.save(batch)
    
    def track(
        self,
        name: str,
        event_type: EventType = EventType.CUSTOM,
        data: Optional[Dict[str, Any]] = None,
        priority: EventPriority = EventPriority.NORMAL,
        url: str = "/"
    ) -> bool:
        """
        追踪事件
        
        Args:
            name: 事件名称
            event_type: 事件类型
            data: 事件数据
            priority: 优先级
            url: 关联URL
            
        Returns:
            是否成功加入队列
        """
        if not self.config.enabled:
            return False
        
        event = Event(
            name=name,
            event_type=event_type,
            data=data or {},
            priority=priority,
            url=url,
            session_id=self._session_id,
            user_id=self._user_id
        )
        
        event.data.update(EnvironmentDetector.get_platform_info())
        
        self._event_count += 1
        return self._event_queue.put(event)
    
    def track_visit(self, is_agent: Optional[bool] = None) -> None:
        """追踪访问"""
        if is_agent is None:
            is_agent = EnvironmentDetector.is_agent()
        
        event_type = EventType.VISIT_AGENT if is_agent else EventType.VISIT_HUMAN
        self.track(
            name=f"visit-{'agent' if is_agent else 'human'}",
            event_type=event_type,
            data=EnvironmentDetector.get_platform_info()
        )
    
    def track_install(self, item_name: str, version: str = "unknown") -> None:
        """追踪安装事件"""
        self.track(
            name=f"install:{item_name}",
            event_type=EventType.INSTALL,
            data={
                "item": item_name,
                "version": version,
                **EnvironmentDetector.get_platform_info()
            }
        )
    
    def track_uninstall(self, item_name: str) -> None:
        """追踪卸载事件"""
        self.track(
            name=f"uninstall:{item_name}",
            event_type=EventType.UNINSTALL,
            data={
                "item": item_name,
                **EnvironmentDetector.get_platform_info()
            }
        )
    
    def track_error(
        self,
        error_message: str,
        error_type: str = "unknown",
        stack_trace: Optional[str] = None
    ) -> None:
        """追踪错误事件"""
        data = {
            "error_message": error_message,
            "error_type": error_type,
            **EnvironmentDetector.get_platform_info()
        }
        if stack_trace:
            data["stack_trace"] = stack_trace[:1000]
        
        self.track(
            name=f"error:{error_type}",
            event_type=EventType.ERROR,
            data=data,
            priority=EventPriority.HIGH
        )
    
    def track_performance(
        self,
        operation: str,
        duration_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """追踪性能事件"""
        self.track(
            name=f"perf:{operation}",
            event_type=EventType.PERFORMANCE,
            data={
                "operation": operation,
                "duration_ms": duration_ms,
                **(metadata or {}),
                **EnvironmentDetector.get_platform_info()
            }
        )
    
    def track_search(self, query: str, results_count: int = 0) -> None:
        """追踪搜索事件"""
        self.track(
            name=f"search:{query[:50]}",
            event_type=EventType.SEARCH,
            data={
                "query": query,
                "results_count": results_count
            }
        )
    
    def set_session_id(self, session_id: str) -> None:
        """设置会话ID"""
        self._session_id = session_id
    
    def set_user_id(self, user_id: str) -> None:
        """设置用户ID"""
        self._user_id = user_id
    
    def flush(self) -> None:
        """手动刷新队列"""
        self._flush_event.set()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "enabled": self.config.enabled,
            "event_count": self._event_count,
            "success_count": self._success_count,
            "error_count": self._error_count,
            "queue_size": self._event_queue.size(),
            "is_agent": EnvironmentDetector.is_agent()
        }
    
    def enable(self) -> None:
        """启用追踪"""
        self.config.enabled = True
        self._start_worker()
    
    def disable(self) -> None:
        """禁用追踪"""
        self.config.enabled = False
        self._stop_event.set()
    
    @classmethod
    def get_instance(cls) -> 'UnifiedEventTracker':
        """获取单例实例"""
        return cls()


def create_tracker(
    endpoint: str,
    website_id: str,
    hostname: str = "localhost",
    **kwargs
) -> UnifiedEventTracker:
    """创建事件追踪器"""
    config = TrackerConfig(
        endpoint=endpoint,
        website_id=website_id,
        hostname=hostname,
        **kwargs
    )
    return UnifiedEventTracker(config)
