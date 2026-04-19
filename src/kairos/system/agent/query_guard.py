# -*- coding: utf-8 -*-
"""
查询守卫状态机

三状态查询生命周期管理，防止并发查询重入：
  idle        → 无查询，安全出队处理
  dispatching → 已出队，异步链尚未到达查询执行
  running     → 查询正在执行

状态转换：
  idle → dispatching  (reserve)
  dispatching → running  (try_start)
  idle → running  (try_start，直接用户提交)
  running → idle  (end / force_end)
  dispatching → idle  (cancel_reservation)

代数计数器确保过期查询的清理逻辑不会干扰新查询。

参考: Claude Code QueryGuard.ts
"""

import threading
import logging
from enum import Enum
from typing import Callable, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class QueryState(Enum):
    IDLE = "idle"
    DISPATCHING = "dispatching"
    RUNNING = "running"


@dataclass
class QueryGuardSnapshot:
    state: QueryState
    generation: int
    is_active: bool


class QueryGuard:
    """
    同步状态机，管理查询生命周期。

    核心设计：
    - 三状态模型确保异步间隙不会导致重入
    - 代数计数器区分当前查询与过期查询
    - 线程安全，所有状态变更加锁
    - 支持订阅机制，状态变更时通知监听者
    """

    def __init__(self):
        self._state = QueryState.IDLE
        self._generation = 0
        self._lock = threading.RLock()  # RLock允许重入，防止_notify中的回调死锁
        self._listeners: List[Callable[[QueryGuardSnapshot], None]] = []

    def reserve(self) -> bool:
        """
        预留守卫用于队列处理。idle → dispatching。
        如果非空闲则返回False（另一个查询或调度正在进行）。
        """
        with self._lock:
            if self._state != QueryState.IDLE:
                return False
            self._state = QueryState.DISPATCHING
            self._notify()
            return True

    def cancel_reservation(self) -> bool:
        """
        取消预留，当队列处理无内容时调用。dispatching → idle。
        返回是否成功取消。
        """
        with self._lock:
            if self._state != QueryState.DISPATCHING:
                return False
            self._state = QueryState.IDLE
            self._notify()
            return True

    def try_start(self) -> Optional[int]:
        """
        启动查询。成功返回代数编号，失败返回None。
        接受 idle（直接用户提交）和 dispatching（队列处理器路径）两种转换。
        """
        with self._lock:
            if self._state == QueryState.RUNNING:
                return None
            self._state = QueryState.RUNNING
            self._generation += 1
            gen = self._generation
            self._notify()
            return gen

    def end(self, generation: int) -> bool:
        """
        结束查询。如果代数匹配且状态为running返回True（调用者应执行清理）。
        如果代数不匹配返回False（过期查询的finally块）。
        """
        with self._lock:
            if self._generation != generation:
                return False
            if self._state != QueryState.RUNNING:
                return False
            self._state = QueryState.IDLE
            self._notify()
            return True

    def force_end(self) -> bool:
        """
        强制结束当前查询，无论代数。
        用于取消操作。递增代数使过期查询的finally块跳过清理。
        返回是否确实执行了强制结束。
        """
        with self._lock:
            if self._state == QueryState.IDLE:
                return False
            self._state = QueryState.IDLE
            self._generation += 1
            self._notify()
            return True

    @property
    def is_active(self) -> bool:
        """守卫是否活跃（dispatching或running）"""
        with self._lock:
            return self._state != QueryState.IDLE

    @property
    def state(self) -> QueryState:
        """当前状态"""
        with self._lock:
            return self._state

    @property
    def generation(self) -> int:
        """当前代数"""
        with self._lock:
            return self._generation

    def get_snapshot(self) -> QueryGuardSnapshot:
        """获取当前快照"""
        with self._lock:
            return QueryGuardSnapshot(
                state=self._state,
                generation=self._generation,
                is_active=self._state != QueryState.IDLE,
            )

    def subscribe(self, listener: Callable[[QueryGuardSnapshot], None]) -> None:
        """订阅状态变更"""
        with self._lock:
            self._listeners.append(listener)

    def unsubscribe(self, listener: Callable[[QueryGuardSnapshot], None]) -> None:
        """取消订阅"""
        with self._lock:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

    def _notify(self) -> None:
        snapshot = QueryGuardSnapshot(
            state=self._state,
            generation=self._generation,
            is_active=self._state != QueryState.IDLE,
        )
        for listener in self._listeners:
            try:
                listener(snapshot)
            except Exception as e:
                logger.warning("查询守卫监听器异常: %s", e)

    def reset(self) -> None:
        """重置守卫状态（仅用于测试）"""
        with self._lock:
            self._state = QueryState.IDLE
            self._generation = 0


class QueryGuardManager:
    """
    查询守卫管理器，为多个查询通道提供独立的守卫实例。

    每个通道（如聊天、搜索、记忆检索等）拥有独立的守卫，
    防止不同通道间的查询互相阻塞。
    """

    def __init__(self):
        self._guards: dict = {}
        self._lock = threading.Lock()

    def get_guard(self, channel: str) -> QueryGuard:
        """获取指定通道的守卫，不存在则创建"""
        with self._lock:
            if channel not in self._guards:
                self._guards[channel] = QueryGuard()
            return self._guards[channel]

    def list_channels(self) -> List[str]:
        """列出所有通道"""
        with self._lock:
            return list(self._guards.keys())

    def get_all_snapshots(self) -> dict:
        """获取所有通道的快照"""
        with self._lock:
            return {ch: guard.get_snapshot() for ch, guard in self._guards.items()}

    def force_end_all(self) -> int:
        """强制结束所有活跃查询，返回结束数量"""
        count = 0
        with self._lock:
            for guard in self._guards.values():
                if guard.force_end():
                    count += 1
        return count


_guard_manager: Optional[QueryGuardManager] = None


def get_query_guard_manager() -> QueryGuardManager:
    """获取查询守卫管理器单例"""
    global _guard_manager
    if _guard_manager is None:
        _guard_manager = QueryGuardManager()
    return _guard_manager
