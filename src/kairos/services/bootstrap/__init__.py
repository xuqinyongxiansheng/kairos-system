"""
全局状态管理（Bootstrap State）
借鉴 cc-haha-main 的 state.ts（1757行）：
1. 集中式全局状态管理 - 系统基石
2. 会话管理（sessionId、parentSessionId、sessionSwitched）
3. 模式管理（autoMode、planMode、fastMode 状态和转换）
4. 交互时间追踪（lastInteractionTime + flushInteractionTime）
5. Hook 注册表（SDK 回调和插件原生 Hook）
6. Agent 颜色分配（多代理颜色映射）
7. Beta Header Latch（防止模式切换破坏 prompt cache）
"""

import os
import time
import json
import logging
import threading
from enum import Enum
from typing import Dict, Any, Optional, List, Set, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger("BootstrapState")

DATA_DIR = os.environ.get("GEMMA4_DATA_DIR", "data")
STATE_FILE = os.path.join(DATA_DIR, "bootstrap_state.json")


class AgentMode(Enum):
    DEFAULT = "default"
    AUTO = "auto"
    PLAN = "plan"
    FAST = "fast"
    AFK = "afk"


@dataclass
class SessionState:
    session_id: str
    parent_session_id: Optional[str] = None
    created_at: float = 0.0
    last_active: float = 0.0
    message_count: int = 0
    switched: bool = False

    def __post_init__(self):
        now = time.time()
        if self.created_at == 0.0:
            self.created_at = now
        if self.last_active == 0.0:
            self.last_active = now

    def touch(self):
        self.last_active = time.time()
        self.message_count += 1


@dataclass
class ModeLatch:
    """防止模式切换破坏 prompt cache 的锁存器"""
    auto_mode_latched: bool = False
    fast_mode_latched: bool = False
    cache_editing_latched: bool = False
    afk_mode_latched: bool = False

    def can_switch_mode(self, target_mode: AgentMode) -> bool:
        if target_mode == AgentMode.AUTO and self.auto_mode_latched:
            return False
        if target_mode == AgentMode.FAST and self.fast_mode_latched:
            return False
        if target_mode == AgentMode.AFK and self.afk_mode_latched:
            return False
        return True

    def release_all(self):
        self.auto_mode_latched = False
        self.fast_mode_latched = False
        self.cache_editing_latched = False
        self.afk_mode_latched = False


@dataclass
class InteractionTime:
    last_interaction: float = 0.0
    last_flush: float = 0.0
    interaction_count: int = 0
    total_idle_seconds: float = 0.0

    def record_interaction(self):
        now = time.time()
        if self.last_interaction > 0:
            idle = now - self.last_interaction
            if idle > 60:
                self.total_idle_seconds += idle
        self.last_interaction = now
        self.interaction_count += 1

    def should_flush(self, interval: float = 30.0) -> bool:
        if self.last_flush == 0.0:
            return True
        return time.time() - self.last_flush >= interval

    def mark_flushed(self):
        self.last_flush = time.time()


class BootstrapState:
    """全局状态管理 - 系统基石"""

    def __init__(self):
        self._lock = threading.RLock()
        self._session: Optional[SessionState] = None
        self._mode = AgentMode.DEFAULT
        self._mode_latch = ModeLatch()
        self._interaction = InteractionTime()
        self._agent_colors: Dict[str, str] = {}
        self._color_palette = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
            "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F",
            "#BB8FCE", "#85C1E9", "#F0B27A", "#82E0AA",
        ]
        self._color_index = 0
        self._registered_hooks: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._cron_tasks: Dict[str, Dict[str, Any]] = {}
        self._scroll_draining = False
        self._custom_state: Dict[str, Any] = {}
        self._initialized = False
        self._init_time = time.time()

    def initialize(self, session_id: str = None, parent_session_id: str = None):
        """初始化全局状态"""
        with self._lock:
            if session_id is None:
                import uuid
                session_id = str(uuid.uuid4())[:8]
            self._session = SessionState(
                session_id=session_id,
                parent_session_id=parent_session_id,
            )
            self._initialized = True
            logger.info(f"全局状态初始化: session={session_id}")

    @property
    def session(self) -> Optional[SessionState]:
        return self._session

    @property
    def session_id(self) -> Optional[str]:
        return self._session.session_id if self._session else None

    @property
    def mode(self) -> AgentMode:
        return self._mode

    def set_mode(self, mode: AgentMode) -> bool:
        """设置代理模式，受 ModeLatch 约束"""
        with self._lock:
            if not self._mode_latch.can_switch_mode(mode):
                logger.warning(f"模式切换被锁存器阻止: {self._mode.value} → {mode.value}")
                return False
            old_mode = self._mode
            self._mode = mode
            logger.info(f"模式切换: {old_mode.value} → {mode.value}")
            return True

    @property
    def mode_latch(self) -> ModeLatch:
        return self._mode_latch

    @property
    def is_auto_mode(self) -> bool:
        return self._mode == AgentMode.AUTO

    @property
    def is_plan_mode(self) -> bool:
        return self._mode == AgentMode.PLAN

    @property
    def is_fast_mode(self) -> bool:
        return self._mode == AgentMode.FAST

    def get_agent_color(self, agent_id: str) -> str:
        """为代理分配颜色"""
        with self._lock:
            if agent_id not in self._agent_colors:
                color = self._color_palette[self._color_index % len(self._color_palette)]
                self._agent_colors[agent_id] = color
                self._color_index += 1
            return self._agent_colors[agent_id]

    def register_hook(self, event_type: str, hook_config: Dict[str, Any]):
        """注册 Hook"""
        with self._lock:
            self._registered_hooks[event_type].append(hook_config)

    def get_hooks(self, event_type: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """获取已注册的 Hook"""
        with self._lock:
            if event_type:
                return {event_type: self._registered_hooks.get(event_type, [])}
            return dict(self._registered_hooks)

    def register_cron_task(self, task_id: str, config: Dict[str, Any]):
        """注册定时任务"""
        with self._lock:
            self._cron_tasks[task_id] = {
                **config,
                "registered_at": time.time(),
                "last_run": None,
                "run_count": 0,
            }

    def remove_cron_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._cron_tasks:
                del self._cron_tasks[task_id]
                return True
            return False

    def list_cron_tasks(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._cron_tasks)

    def record_interaction(self):
        """记录用户交互"""
        with self._lock:
            self._interaction.record_interaction()
            if self._session:
                self._session.touch()

    @property
    def scroll_draining(self) -> bool:
        return self._scroll_draining

    @scroll_draining.setter
    def scroll_draining(self, value: bool):
        self._scroll_draining = value

    def set_custom(self, key: str, value: Any):
        """设置自定义状态"""
        with self._lock:
            self._custom_state[key] = value

    def get_custom(self, key: str, default: Any = None) -> Any:
        """获取自定义状态"""
        with self._lock:
            return self._custom_state.get(key, default)

    def save_to_disk(self):
        """持久化状态到磁盘"""
        with self._lock:
            try:
                os.makedirs(DATA_DIR, exist_ok=True)
                state_data = {
                    "session_id": self.session_id,
                    "mode": self._mode.value,
                    "interaction": {
                        "count": self._interaction.interaction_count,
                        "total_idle_seconds": self._interaction.total_idle_seconds,
                    },
                    "agent_colors": self._agent_colors,
                    "custom_state": self._custom_state,
                    "saved_at": time.time(),
                }
                with open(STATE_FILE, "w", encoding="utf-8") as f:
                    json.dump(state_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"状态持久化失败: {e}")

    def load_from_disk(self) -> bool:
        """从磁盘恢复状态"""
        with self._lock:
            try:
                if not os.path.exists(STATE_FILE):
                    return False
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state_data = json.load(f)

                session_id = state_data.get("session_id")
                if session_id:
                    self._session = SessionState(session_id=session_id)
                mode_str = state_data.get("mode", "default")
                try:
                    self._mode = AgentMode(mode_str)
                except ValueError:
                    self._mode = AgentMode.DEFAULT
                self._agent_colors = state_data.get("agent_colors", {})
                self._custom_state = state_data.get("custom_state", {})
                logger.info(f"状态从磁盘恢复: session={session_id}")
                return True
            except Exception as e:
                logger.error(f"状态恢复失败: {e}")
                return False

    def get_full_state(self) -> Dict[str, Any]:
        """获取完整状态快照"""
        with self._lock:
            return {
                "initialized": self._initialized,
                "session_id": self.session_id,
                "mode": self._mode.value,
                "mode_latch": {
                    "auto_latched": self._mode_latch.auto_mode_latched,
                    "fast_latched": self._mode_latch.fast_mode_latched,
                    "cache_editing_latched": self._mode_latch.cache_editing_latched,
                    "afk_latched": self._mode_latch.afk_mode_latched,
                },
                "interaction": {
                    "last_interaction": self._interaction.last_interaction,
                    "count": self._interaction.interaction_count,
                    "total_idle_seconds": round(self._interaction.total_idle_seconds, 1),
                },
                "agent_colors": self._agent_colors,
                "registered_hooks": {k: len(v) for k, v in self._registered_hooks.items()},
                "cron_tasks": len(self._cron_tasks),
                "scroll_draining": self._scroll_draining,
                "uptime_seconds": round(time.time() - self._init_time, 1),
                "custom_keys": list(self._custom_state.keys()),
            }


_bootstrap_state: Optional[BootstrapState] = None


def get_bootstrap_state() -> BootstrapState:
    global _bootstrap_state
    if _bootstrap_state is None:
        _bootstrap_state = BootstrapState()
        _bootstrap_state.initialize()
    return _bootstrap_state
