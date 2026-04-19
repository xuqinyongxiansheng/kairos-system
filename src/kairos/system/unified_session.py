"""
import logging
统一会话管理系统 - 整合CLI-Anything的会话管理模式
logger = logging.getLogger("unified_session")

设计模式来源:
- browser/session.py: 浏览器会话状态管理
- anygen/session.py: 任务会话管理
- obs_studio/session.py: 项目会话管理

核心特性:
1. 会话状态追踪
2. 历史记录管理 (Undo/Redo)
3. 会话持久化
4. 文件锁定机制
5. 会话生命周期管理
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

T = TypeVar('T')


class SessionState(Enum):
    """会话状态枚举"""
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
    ERROR = "error"


class HistoryAction(Enum):
    """历史动作类型"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MOVE = "move"
    CUSTOM = "custom"


@dataclass
class HistoryEntry(Generic[T]):
    """历史记录条目"""
    action: HistoryAction
    timestamp: datetime
    data: T
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data if not isinstance(self.data, (dict, list)) else self.data,
            "description": self.description,
            "metadata": self.metadata
        }


@dataclass
class SessionConfig:
    """会话配置"""
    session_dir: str = ""
    max_history: int = 100
    auto_save: bool = True
    auto_save_interval: int = 60
    enable_undo_redo: bool = True
    enable_persistence: bool = True
    file_lock_timeout: int = 10


class SessionStorage:
    """
    会话存储管理器
    
    提供文件锁定和原子写入功能
    """
    
    def __init__(self, session_dir: str):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()
    
    def _get_lock(self, key: str) -> threading.Lock:
        """获取文件锁"""
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]
    
    def save(self, key: str, data: Dict[str, Any]) -> bool:
        """
        保存会话数据 (原子写入)
        
        使用临时文件+重命名实现原子写入
        """
        file_path = self.session_dir / f"{key}.json"
        temp_path = self.session_dir / f"{key}.json.tmp"
        lock = self._get_lock(key)
        
        with lock:
            try:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)
                
                if file_path.exists():
                    file_path.unlink()
                
                temp_path.rename(file_path)
                return True
            except Exception as e:
                if temp_path.exists():
                    temp_path.unlink()
                raise e
    
    def load(self, key: str) -> Optional[Dict[str, Any]]:
        """加载会话数据"""
        file_path = self.session_dir / f"{key}.json"
        lock = self._get_lock(key)
        
        with lock:
            if not file_path.exists():
                return None
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
    
    def delete(self, key: str) -> bool:
        """删除会话数据"""
        file_path = self.session_dir / f"{key}.json"
        lock = self._get_lock(key)
        
        with lock:
            if file_path.exists():
                file_path.unlink()
                return True
            return False
    
    def exists(self, key: str) -> bool:
        """检查会话是否存在"""
        return (self.session_dir / f"{key}.json").exists()
    
    def list_sessions(self) -> List[str]:
        """列出所有会话"""
        return [f.stem for f in self.session_dir.glob("*.json")]


class UnifiedSession(Generic[T]):
    """
    统一会话管理
    
    整合了CLI-Anything中多个会话管理模式:
    - 状态追踪
    - 历史记录 (Undo/Redo)
    - 持久化存储
    - 文件锁定
    """
    
    def __init__(
        self,
        session_id: str,
        initial_state: T,
        config: Optional[SessionConfig] = None,
        storage: Optional[SessionStorage] = None
    ):
        self.session_id = session_id
        self._state: T = initial_state
        self.config = config or SessionConfig()
        self._storage = storage
        
        self._state_enum = SessionState.CREATED
        self._history: List[HistoryEntry[T]] = []
        self._redo_stack: List[HistoryEntry[T]] = []
        self._metadata: Dict[str, Any] = {}
        self._created_at = datetime.now(timezone.utc)
        self._updated_at = datetime.now(timezone.utc)
        self._lock = threading.RLock()
        
        self._on_state_change: Optional[Callable[[T, T], None]] = None
        self._on_history_change: Optional[Callable[[HistoryEntry[T]], None]] = None
        
        if self.config.enable_persistence and self._storage:
            self._load_from_storage()
    
    @property
    def state(self) -> T:
        """获取当前状态"""
        with self._lock:
            return self._state
    
    @property
    def session_state(self) -> SessionState:
        """获取会话状态"""
        with self._lock:
            return self._state_enum
    
    def set_state(
        self,
        new_state: T,
        action: HistoryAction = HistoryAction.UPDATE,
        description: str = "",
        record_history: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        设置新状态
        
        Args:
            new_state: 新状态值
            action: 动作类型
            description: 描述
            record_history: 是否记录历史
            metadata: 额外元数据
        """
        with self._lock:
            old_state = self._state
            self._state = new_state
            self._updated_at = datetime.now(timezone.utc)
            
            if record_history and self.config.enable_undo_redo:
                entry = HistoryEntry(
                    action=action,
                    timestamp=self._updated_at,
                    data=old_state,
                    description=description,
                    metadata=metadata or {}
                )
                self._history.append(entry)
                self._redo_stack.clear()
                
                while len(self._history) > self.config.max_history:
                    self._history.pop(0)
                
                if self._on_history_change:
                    self._on_history_change(entry)
            
            if self._on_state_change:
                self._on_state_change(old_state, new_state)
            
            if self.config.auto_save and self._storage:
                self._save_to_storage()
    
    def undo(self) -> Optional[HistoryEntry[T]]:
        """
        撤销操作
        
        Returns:
            被撤销的历史条目
        """
        with self._lock:
            if not self._history:
                return None
            
            entry = self._history.pop()
            self._redo_stack.append(entry)
            
            if self._history:
                self._state = self._history[-1].data
            else:
                pass
            
            self._updated_at = datetime.now(timezone.utc)
            
            if self.config.auto_save and self._storage:
                self._save_to_storage()
            
            return entry
    
    def redo(self) -> Optional[HistoryEntry[T]]:
        """
        重做操作
        
        Returns:
            被重做的历史条目
        """
        with self._lock:
            if not self._redo_stack:
                return None
            
            entry = self._redo_stack.pop()
            self._history.append(entry)
            self._state = entry.data
            
            self._updated_at = datetime.now(timezone.utc)
            
            if self.config.auto_save and self._storage:
                self._save_to_storage()
            
            return entry
    
    def can_undo(self) -> bool:
        """是否可以撤销"""
        return len(self._history) > 0
    
    def can_redo(self) -> bool:
        """是否可以重做"""
        return len(self._redo_stack) > 0
    
    def get_history(self, limit: int = 10) -> List[HistoryEntry[T]]:
        """获取历史记录"""
        with self._lock:
            return self._history[-limit:]
    
    def clear_history(self) -> None:
        """清空历史记录"""
        with self._lock:
            self._history.clear()
            self._redo_stack.clear()
    
    def set_metadata(self, key: str, value: Any) -> None:
        """设置元数据"""
        with self._lock:
            self._metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """获取元数据"""
        with self._lock:
            return self._metadata.get(key, default)
    
    def activate(self) -> None:
        """激活会话"""
        with self._lock:
            self._state_enum = SessionState.ACTIVE
            self._updated_at = datetime.now(timezone.utc)
    
    def pause(self) -> None:
        """暂停会话"""
        with self._lock:
            self._state_enum = SessionState.PAUSED
            self._updated_at = datetime.now(timezone.utc)
    
    def close(self) -> None:
        """关闭会话"""
        with self._lock:
            self._state_enum = SessionState.CLOSED
            self._updated_at = datetime.now(timezone.utc)
            
            if self.config.enable_persistence and self._storage:
                self._save_to_storage()
    
    def on_state_change(self, callback: Callable[[T, T], None]) -> None:
        """设置状态变化回调"""
        self._on_state_change = callback
    
    def on_history_change(self, callback: Callable[[HistoryEntry[T]], None]) -> None:
        """设置历史变化回调"""
        self._on_history_change = callback
    
    def _save_to_storage(self) -> bool:
        """保存到存储"""
        if not self._storage:
            return False
        
        data = {
            "session_id": self.session_id,
            "state": self._state if isinstance(self._state, (dict, list, str, int, float, bool, type(None))) else str(self._state),
            "state_enum": self._state_enum.value,
            "metadata": self._metadata,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
            "history": [h.to_dict() for h in self._history[-self.config.max_history:]]
        }
        
        return self._storage.save(self.session_id, data)
    
    def _load_from_storage(self) -> bool:
        """从存储加载"""
        if not self._storage:
            return False
        
        data = self._storage.load(self.session_id)
        if not data:
            return False
        
        self._state_enum = SessionState(data.get("state_enum", "created"))
        self._metadata = data.get("metadata", {})
        
        if "created_at" in data:
            self._created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            self._updated_at = datetime.fromisoformat(data["updated_at"])
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        with self._lock:
            return {
                "session_id": self.session_id,
                "state": self._state,
                "session_state": self._state_enum.value,
                "metadata": self._metadata,
                "created_at": self._created_at.isoformat(),
                "updated_at": self._updated_at.isoformat(),
                "history_count": len(self._history),
                "redo_count": len(self._redo_stack),
                "can_undo": self.can_undo(),
                "can_redo": self.can_redo()
            }


class SessionManager(Generic[T]):
    """
    会话管理器
    
    管理多个会话实例
    """
    
    def __init__(
        self,
        storage_dir: str = "",
        config: Optional[SessionConfig] = None
    ):
        self.config = config or SessionConfig()
        self._storage = SessionStorage(storage_dir) if storage_dir else None
        self._sessions: Dict[str, UnifiedSession[T]] = {}
        self._lock = threading.RLock()
    
    def create_session(
        self,
        session_id: str,
        initial_state: T,
        config: Optional[SessionConfig] = None
    ) -> UnifiedSession[T]:
        """创建新会话"""
        with self._lock:
            if session_id in self._sessions:
                raise ValueError(f"会话已存在: {session_id}")
            
            session = UnifiedSession(
                session_id=session_id,
                initial_state=initial_state,
                config=config or self.config,
                storage=self._storage
            )
            self._sessions[session_id] = session
            return session
    
    def get_session(self, session_id: str) -> Optional[UnifiedSession[T]]:
        """获取会话"""
        with self._lock:
            return self._sessions.get(session_id)
    
    def remove_session(self, session_id: str) -> bool:
        """移除会话"""
        with self._lock:
            if session_id in self._sessions:
                session = self._sessions.pop(session_id)
                session.close()
                return True
            return False
    
    def list_sessions(self) -> List[str]:
        """列出所有会话"""
        with self._lock:
            return list(self._sessions.keys())
    
    def get_active_sessions(self) -> List[UnifiedSession[T]]:
        """获取所有活跃会话"""
        with self._lock:
            return [
                s for s in self._sessions.values()
                if s.session_state == SessionState.ACTIVE
            ]
    
    def close_all(self) -> None:
        """关闭所有会话"""
        with self._lock:
            for session in self._sessions.values():
                session.close()
            self._sessions.clear()
    
    def restore_from_storage(self) -> int:
        """从存储恢复会话"""
        if not self._storage:
            return 0
        
        restored = 0
        for session_id in self._storage.list_sessions():
            if session_id not in self._sessions:
                try:
                    session = UnifiedSession(
                        session_id=session_id,
                        initial_state=None,
                        config=self.config,
                        storage=self._storage
                    )
                    self._sessions[session_id] = session
                    restored += 1
                except Exception:
                    logger.debug(f"忽略异常: ", exc_info=True)
                    pass
        
        return restored
