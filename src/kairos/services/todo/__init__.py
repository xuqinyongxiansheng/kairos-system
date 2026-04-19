"""
待办系统
借鉴 cc-haha-main 的 TodoWriteTool 架构：
- 任务列表管理
- 状态追踪（pending/in_progress/completed）
- 验证推动（verification nudge）
- 按会话/代理隔离

完全重写实现
"""

import os
import json
import time
import logging
import threading
import tempfile
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("TodoSystem")

TODO_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "todos")


class TodoStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass
class TodoItem:
    id: str = ""
    content: str = ""
    status: TodoStatus = TodoStatus.PENDING
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class TodoManager:
    """待办管理器"""

    def __init__(self, todo_dir: str = None):
        self.todo_dir = todo_dir or TODO_DIR
        os.makedirs(self.todo_dir, exist_ok=True)
        self._lists: Dict[str, List[TodoItem]] = {}
        self._lock = threading.Lock()
        self._load_all()

    def _load_all(self):
        if not os.path.exists(self.todo_dir):
            return
        for fname in os.listdir(self.todo_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(self.todo_dir, fname), "r", encoding="utf-8") as f:
                        data = json.load(f)
                    key = fname[:-5]
                    self._lists[key] = [TodoItem(**item) for item in data]
                except Exception:
                    pass

    def _save(self, key: str):
        items = self._lists.get(key, [])
        filepath = os.path.join(self.todo_dir, f"{key}.json")
        try:
            tmp_fd, tmp_path = tempfile.mkstemp(
                dir=self.todo_dir, suffix=".tmp", prefix=f"todo_{key}_"
            )
            try:
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    json.dump([i.to_dict() for i in items], f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, filepath)
            except Exception:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise
        except Exception as e:
            logger.error(f"保存待办列表失败: {e}")

    def update_todos(self, key: str, todos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """更新待办列表"""
        old_items = self._lists.get(key, [])
        new_items = []
        for i, todo_data in enumerate(todos):
            item = TodoItem(
                id=todo_data.get("id", f"todo_{i}"),
                content=todo_data.get("content", ""),
                status=TodoStatus(todo_data.get("status", "pending")),
                priority=todo_data.get("priority", 0),
            )
            new_items.append(item)

        self._lists[key] = new_items
        self._save(key)

        all_done = all(i.status == TodoStatus.COMPLETED for i in new_items) if new_items else False
        verification_nudge = False
        if all_done and len(new_items) >= 3:
            has_verification = any("验证" in i.content or "测试" in i.content for i in new_items)
            if not has_verification:
                verification_nudge = True

        return {
            "success": True,
            "old_count": len(old_items),
            "new_count": len(new_items),
            "all_done": all_done,
            "verification_nudge": verification_nudge,
        }

    def get_todos(self, key: str) -> List[Dict[str, Any]]:
        return [i.to_dict() for i in self._lists.get(key, [])]

    def add_todo(self, key: str, content: str, priority: int = 0) -> Dict[str, Any]:
        if key not in self._lists:
            self._lists[key] = []
        item = TodoItem(
            id=f"todo_{len(self._lists[key])}_{int(time.time())}",
            content=content,
            priority=priority,
        )
        self._lists[key].append(item)
        self._save(key)
        return {"success": True, "id": item.id}

    def update_status(self, key: str, todo_id: str, status: str) -> Dict[str, Any]:
        items = self._lists.get(key, [])
        for item in items:
            if item.id == todo_id:
                item.status = TodoStatus(status)
                item.updated_at = time.time()
                self._save(key)
                return {"success": True, "id": todo_id, "status": status}
        return {"success": False, "error": f"待办项不存在: {todo_id}"}

    def clear_completed(self, key: str) -> int:
        items = self._lists.get(key, [])
        before = len(items)
        self._lists[key] = [i for i in items if i.status != TodoStatus.COMPLETED]
        self._save(key)
        return before - len(self._lists[key])

    def get_stats(self, key: str = None) -> Dict[str, Any]:
        if key:
            items = self._lists.get(key, [])
            by_status = {}
            for i in items:
                s = i.status.value
                by_status[s] = by_status.get(s, 0) + 1
            return {"key": key, "total": len(items), "by_status": by_status}

        total = sum(len(items) for items in self._lists.values())
        return {"lists": len(self._lists), "total_items": total}


_todo_manager: Optional[TodoManager] = None


def get_todo_manager() -> TodoManager:
    global _todo_manager
    if _todo_manager is None:
        _todo_manager = TodoManager()
    return _todo_manager
