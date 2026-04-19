"""
会话管理服务
借鉴 cc-haha-main 的会话持久化与恢复架构：
- JSONL 格式持久化
- 会话创建、恢复、列表
- 消息链（parentUuid）
- 会话元数据

完全重写实现，适配本地大模型服务场景
"""

import os
import json
import time
import uuid
import threading
import logging
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger("SessionService")

SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sessions")


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    TOOL_RESULT = "tool_result"


@dataclass
class Message:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    role: str = "user"
    content: str = ""
    parent_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "parent_id": self.parent_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            role=data.get("role", "user"),
            content=data.get("content", ""),
            parent_id=data.get("parent_id"),
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Session:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    title: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    messages: List[Message] = field(default_factory=list)
    model: str = "gemma4:e4b"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [m.to_dict() for m in self.messages],
            "model": self.model,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        messages = [Message.from_dict(m) for m in data.get("messages", [])]
        return cls(
            id=data.get("id", str(uuid.uuid4())[:12]),
            title=data.get("title", ""),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            messages=messages,
            model=data.get("model", "gemma4:e4b"),
            metadata=data.get("metadata", {}),
        )


class SessionManager:
    """会话管理器"""

    def __init__(self, sessions_dir: str = None):
        self.sessions_dir = sessions_dir or SESSIONS_DIR
        os.makedirs(self.sessions_dir, exist_ok=True)
        self._active_sessions: Dict[str, Session] = {}
        self._current_session_id: Optional[str] = None
        self._lock = threading.Lock()

    def create_session(self, title: str = "", model: str = "gemma4:e4b") -> Session:
        session = Session(title=title or f"会话 {time.strftime('%H:%M')}", model=model)
        self._active_sessions[session.id] = session
        self._current_session_id = session.id
        self._save_session(session)
        logger.info(f"创建会话: {session.id} - {session.title}")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]
        session = self._load_session(session_id)
        if session:
            self._active_sessions[session_id] = session
        return session

    def get_current_session(self) -> Optional[Session]:
        if self._current_session_id:
            return self.get_session(self._current_session_id)
        return None

    def set_current_session(self, session_id: str) -> bool:
        session = self.get_session(session_id)
        if session:
            self._current_session_id = session_id
            return True
        return False

    def add_message(self, role: str, content: str, session_id: str = None,
                    metadata: Dict[str, Any] = None) -> Message:
        sid = session_id or self._current_session_id
        if not sid:
            session = self.create_session()
            sid = session.id

        session = self.get_session(sid)
        if not session:
            raise ValueError(f"会话不存在: {sid}")

        parent_id = session.messages[-1].id if session.messages else None
        msg = Message(
            role=role,
            content=content,
            parent_id=parent_id,
            metadata=metadata or {},
        )
        session.messages.append(msg)
        session.updated_at = time.time()

        if not session.title and role == "user" and len(session.messages) <= 2:
            session.title = content[:30] + ("..." if len(content) > 30 else "")

        self._save_session(session)
        return msg

    def get_messages(self, session_id: str = None) -> List[Message]:
        sid = session_id or self._current_session_id
        if not sid:
            return []
        session = self.get_session(sid)
        return session.messages if session else []

    def get_chat_history(self, session_id: str = None) -> List[Dict[str, str]]:
        messages = self.get_messages(session_id)
        return [{"role": m.role, "content": m.content} for m in messages
                if m.role in ("user", "assistant", "system")]

    def clear_session(self, session_id: str = None) -> bool:
        sid = session_id or self._current_session_id
        if not sid:
            return False
        session = self.get_session(sid)
        if session:
            session.messages = []
            session.updated_at = time.time()
            self._save_session(session)
            return True
        return False

    def list_sessions(self) -> List[Dict[str, Any]]:
        result = []
        for fname in os.listdir(self.sessions_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(self.sessions_dir, fname), "r", encoding="utf-8") as f:
                        data = json.load(f)
                    result.append({
                        "id": data.get("id", ""),
                        "title": data.get("title", ""),
                        "created_at": data.get("created_at", 0),
                        "updated_at": data.get("updated_at", 0),
                        "message_count": len(data.get("messages", [])),
                        "model": data.get("model", ""),
                    })
                except Exception:
                    pass
        return sorted(result, key=lambda s: s["updated_at"], reverse=True)

    def delete_session(self, session_id: str) -> bool:
        filepath = os.path.join(self.sessions_dir, f"{session_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            self._active_sessions.pop(session_id, None)
            if self._current_session_id == session_id:
                self._current_session_id = None
            return True
        return False

    def _save_session(self, session: Session):
        filepath = os.path.join(self.sessions_dir, f"{session.id}.json")
        try:
            import tempfile
            os.makedirs(self.sessions_dir, exist_ok=True)
            tmp_fd, tmp_path = tempfile.mkstemp(
                dir=self.sessions_dir, suffix=".tmp", prefix=f"sess_{session.id}_"
            )
            try:
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, filepath)
            except Exception:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise
        except Exception as e:
            logger.error(f"保存会话失败 [{session.id}]: {e}")

    def _load_session(self, session_id: str) -> Optional[Session]:
        filepath = os.path.join(self.sessions_dir, f"{session_id}.json")
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Session.from_dict(data)
        except Exception as e:
            logger.error(f"加载会话失败 [{session_id}]: {e}")
            return None


_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
