# -*- coding: utf-8 -*-
"""
中止控制器层级 + 活动管理器

AbortController: 父子层级中止控制器，父级中止时自动传播到子级。
子级中止不影响父级。使用弱引用防止内存泄漏。

ActivityManager: 双通道活动追踪器，分别追踪用户活动和CLI活动。
自动去重重叠活动，提供独立的用户/CLI活跃时间指标。

参考: Claude Code abortController.ts + activityManager.ts
"""

import threading
import logging
import weakref
import time
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class AbortState(Enum):
    ACTIVE = "active"
    ABORTED = "aborted"


@dataclass
class AbortInfo:
    controller_id: str
    parent_id: Optional[str]
    state: AbortState
    reason: Optional[str]
    child_count: int
    created_at: str


class AbortController:
    """
    中止控制器，支持父子层级传播。

    核心设计：
    - 父级中止时自动传播到所有子级
    - 子级中止不影响父级
    - 弱引用持有子级，防止内存泄漏
    - 线程安全
    """

    _id_counter = 0
    _id_lock = threading.Lock()

    def __init__(self, controller_id: Optional[str] = None,
                 parent: Optional['AbortController'] = None):
        with AbortController._id_lock:
            if controller_id is None:
                AbortController._id_counter += 1
                self._id = f"abort_{AbortController._id_counter}"
            else:
                self._id = controller_id

        self._state = AbortState.ACTIVE
        self._reason: Optional[str] = None
        self._lock = threading.Lock()
        self._listeners: List[Callable[[Optional[str]], None]] = []
        self._children: List[weakref.ref] = []
        self._parent = parent

        if parent is not None:
            parent._add_child(self)

    @property
    def id(self) -> str:
        return self._id

    @property
    def is_aborted(self) -> bool:
        with self._lock:
            return self._state == AbortState.ABORTED

    @property
    def reason(self) -> Optional[str]:
        with self._lock:
            return self._reason

    def abort(self, reason: Optional[str] = None) -> None:
        """中止此控制器及所有子控制器"""
        with self._lock:
            if self._state == AbortState.ABORTED:
                return
            self._state = AbortState.ABORTED
            self._reason = reason
            listeners = list(self._listeners)
            children = list(self._children)

        for listener in listeners:
            try:
                listener(reason)
            except Exception as e:
                logger.warning("中止监听器异常: %s", e)

        for child_ref in children:
            child = child_ref()
            if child is not None and not child.is_aborted:
                child.abort(reason or "父级控制器中止")

    def on_abort(self, listener: Callable[[Optional[str]], None]) -> None:
        """注册中止监听器"""
        with self._lock:
            if self._state == AbortState.ABORTED:
                listener(self._reason)
                return
            self._listeners.append(listener)

    def create_child(self, child_id: Optional[str] = None) -> 'AbortController':
        """创建子控制器"""
        return AbortController(controller_id=child_id, parent=self)

    def _add_child(self, child: 'AbortController') -> None:
        """添加子控制器（弱引用）"""
        with self._lock:
            if self._state == AbortState.ABORTED:
                child.abort(self.reason or "父级控制器已中止")
                return
            self._children.append(weakref.ref(child, self._cleanup_child))

    def _cleanup_child(self, ref: weakref.ref) -> None:
        """弱引用回调，子级被GC时清理"""
        with self._lock:
            try:
                self._children.remove(ref)
            except ValueError:
                pass

    def get_info(self) -> AbortInfo:
        """获取控制器信息"""
        with self._lock:
            alive_children = sum(1 for ref in self._children if ref() is not None)
            return AbortInfo(
                controller_id=self._id,
                parent_id=self._parent._id if self._parent else None,
                state=self._state,
                reason=self._reason,
                child_count=alive_children,
                created_at=datetime.now().isoformat(),
            )


class AbortControllerManager:
    """
    中止控制器管理器，管理所有控制器的生命周期。

    提供：
    - 创建根控制器和子控制器
    - 批量中止
    - 统计与监控
    """

    def __init__(self):
        self._controllers: Dict[str, AbortController] = {}
        self._lock = threading.Lock()

    def create(self, controller_id: Optional[str] = None,
               parent_id: Optional[str] = None) -> AbortController:
        """创建控制器"""
        with self._lock:
            parent = None
            if parent_id:
                parent = self._controllers.get(parent_id)

            ctrl = AbortController(controller_id=controller_id, parent=parent)
            self._controllers[ctrl.id] = ctrl
            return ctrl

    def abort(self, controller_id: str, reason: Optional[str] = None) -> bool:
        """中止控制器"""
        with self._lock:
            ctrl = self._controllers.get(controller_id)
        if ctrl is None:
            return False
        ctrl.abort(reason)
        return True

    def get(self, controller_id: str) -> Optional[AbortController]:
        """获取控制器"""
        with self._lock:
            return self._controllers.get(controller_id)

    def list_active(self) -> List[AbortInfo]:
        """列出所有活跃控制器"""
        with self._lock:
            return [
                ctrl.get_info()
                for ctrl in self._controllers.values()
                if not ctrl.is_aborted
            ]

    def abort_all(self, reason: str = "批量中止") -> int:
        """中止所有活跃控制器"""
        count = 0
        with self._lock:
            for ctrl in self._controllers.values():
                if not ctrl.is_aborted:
                    ctrl.abort(reason)
                    count += 1
        return count

    def cleanup_aborted(self) -> int:
        """清理已中止的控制器"""
        count = 0
        with self._lock:
            to_remove = [
                cid for cid, ctrl in self._controllers.items()
                if ctrl.is_aborted
            ]
            for cid in to_remove:
                del self._controllers[cid]
                count += 1
        return count

    def get_statistics(self) -> dict:
        """获取统计"""
        with self._lock:
            total = len(self._controllers)
            active = sum(1 for c in self._controllers.values() if not c.is_aborted)
            aborted = total - active
            return {
                "total": total,
                "active": active,
                "aborted": aborted,
            }


_abort_manager: Optional[AbortControllerManager] = None


def get_abort_manager() -> AbortControllerManager:
    """获取中止控制器管理器单例"""
    global _abort_manager
    if _abort_manager is None:
        _abort_manager = AbortControllerManager()
    return _abort_manager


class ActivityType(Enum):
    USER = "user"
    CLI = "cli"


@dataclass
class ActivityState:
    is_user_active: bool
    is_cli_active: bool
    active_operation_count: int
    user_idle_seconds: float
    cli_active_seconds: float


class ActivityManager:
    """
    双通道活动追踪器。

    分别追踪用户活动（输入、命令等）和CLI活动（工具执行、AI响应等）。
    自动去重重叠活动，CLI活动优先于用户活动计时。

    特性：
    - 双通道独立追踪
    - CLI活动自动去重（相同操作ID）
    - 用户活动超时衰减（5秒无活动视为不活跃）
    - 操作追踪（开始/结束配对）
    """

    USER_ACTIVITY_TIMEOUT_S = 5.0

    def __init__(self, get_now: Optional[Callable[[], float]] = None):
        self._get_now = get_now or time.time
        self._active_operations: Set[str] = set()
        self._last_user_activity: float = 0.0
        self._last_cli_recorded: float = self._get_now()
        self._is_cli_active: bool = False
        self._user_active_time: float = 0.0
        self._cli_active_time: float = 0.0
        self._lock = threading.Lock()
        self._stats = {
            "user_activities": 0,
            "cli_starts": 0,
            "cli_ends": 0,
            "total_user_time_s": 0.0,
            "total_cli_time_s": 0.0,
        }

    def record_user_activity(self) -> None:
        """记录用户活动"""
        now = self._get_now()
        with self._lock:
            if not self._is_cli_active and self._last_user_activity > 0:
                elapsed = now - self._last_user_activity
                if 0 < elapsed < self.USER_ACTIVITY_TIMEOUT_S:
                    self._user_active_time += elapsed
                    self._stats["total_user_time_s"] += elapsed

            self._last_user_activity = now
            self._stats["user_activities"] += 1

    def start_cli_activity(self, operation_id: str) -> None:
        """开始追踪CLI活动"""
        now = self._get_now()
        with self._lock:
            if operation_id in self._active_operations:
                self._end_cli_activity_unlocked(operation_id)

            was_empty = len(self._active_operations) == 0
            self._active_operations.add(operation_id)

            if was_empty:
                self._is_cli_active = True
                self._last_cli_recorded = now

            self._stats["cli_starts"] += 1

    def end_cli_activity(self, operation_id: str) -> None:
        """停止追踪CLI活动"""
        with self._lock:
            self._end_cli_activity_unlocked(operation_id)

    def _end_cli_activity_unlocked(self, operation_id: str) -> None:
        """内部方法：停止追踪CLI活动（不加锁）"""
        self._active_operations.discard(operation_id)

        if len(self._active_operations) == 0:
            now = self._get_now()
            elapsed = now - self._last_cli_recorded
            if elapsed > 0:
                self._cli_active_time += elapsed
                self._stats["total_cli_time_s"] += elapsed
            self._last_cli_recorded = now
            self._is_cli_active = False

        self._stats["cli_ends"] += 1

    def track_operation(self, operation_id: str, fn: Callable) -> Any:
        """便捷方法：自动追踪操作"""
        self.start_cli_activity(operation_id)
        try:
            return fn()
        finally:
            self.end_cli_activity(operation_id)

    def get_state(self) -> ActivityState:
        """获取当前活动状态"""
        now = self._get_now()
        with self._lock:
            user_idle = now - self._last_user_activity if self._last_user_activity > 0 else float('inf')
            is_user_active = user_idle < self.USER_ACTIVITY_TIMEOUT_S

            return ActivityState(
                is_user_active=is_user_active,
                is_cli_active=self._is_cli_active,
                active_operation_count=len(self._active_operations),
                user_idle_seconds=round(user_idle, 2) if self._last_user_activity > 0 else 0,
                cli_active_seconds=round(self._cli_active_time, 2),
            )

    def get_statistics(self) -> dict:
        """获取统计"""
        with self._lock:
            return {
                **self._stats,
                "current_state": {
                    "is_user_active": self._last_user_activity > 0 and
                    (self._get_now() - self._last_user_activity) < self.USER_ACTIVITY_TIMEOUT_S,
                    "is_cli_active": self._is_cli_active,
                    "active_operations": len(self._active_operations),
                },
                "user_active_time_s": round(self._user_active_time, 2),
                "cli_active_time_s": round(self._cli_active_time, 2),
            }

    def reset(self) -> None:
        """重置（仅用于测试）"""
        with self._lock:
            self._active_operations.clear()
            self._last_user_activity = 0.0
            self._last_cli_recorded = self._get_now()
            self._is_cli_active = False
            self._user_active_time = 0.0
            self._cli_active_time = 0.0


_activity_manager: Optional[ActivityManager] = None


def get_activity_manager() -> ActivityManager:
    """获取活动管理器单例"""
    global _activity_manager
    if _activity_manager is None:
        _activity_manager = ActivityManager()
    return _activity_manager
