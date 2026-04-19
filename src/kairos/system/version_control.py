"""
版本控制系统
管理项目设定的版本追踪和变更管理
"""

import json
import os
import hashlib
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging

def _get_version() -> str:
    try:
        from kairos.version import VERSION
        return VERSION
    except ImportError:
        return "4.0.0"

logger = logging.getLogger("VersionControl")


class ChangeType(Enum):
    """变更类型枚举"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ROLLBACK = "rollback"


class ChangeStatus(Enum):
    """变更状态枚举"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


@dataclass
class ChangeRecord:
    """变更记录数据类"""
    change_id: str
    change_type: str
    component: str
    description: str
    old_value: Any
    new_value: Any
    status: str
    created_at: str
    approved_at: Optional[str]
    approved_by: Optional[str]
    rollback_id: Optional[str]


class VersionControl:
    """版本控制系统"""
    
    def __init__(self, data_dir: str = "./data/version_control"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        self.changes_file = os.path.join(data_dir, "changes.json")
        self.snapshots_dir = os.path.join(data_dir, "snapshots")
        os.makedirs(self.snapshots_dir, exist_ok=True)
        
        self.changes: List[ChangeRecord] = []
        self.current_version = _get_version()
        
        self._load_changes()
        logger.info("版本控制系统初始化完成")
    
    def _load_changes(self):
        """加载变更记录"""
        if os.path.exists(self.changes_file):
            try:
                with open(self.changes_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.changes = [ChangeRecord(**change) for change in data.get("changes", [])]
                    self.current_version = data.get("current_version", self.current_version)
            except Exception as e:
                logger.error(f"加载变更记录失败：{e}")
    
    def _save_changes(self):
        """保存变更记录"""
        try:
            data = {
                "current_version": self.current_version,
                "changes": [
                    {
                        "change_id": c.change_id,
                        "change_type": c.change_type,
                        "component": c.component,
                        "description": c.description,
                        "old_value": c.old_value,
                        "new_value": c.new_value,
                        "status": c.status,
                        "created_at": c.created_at,
                        "approved_at": c.approved_at,
                        "approved_by": c.approved_by,
                        "rollback_id": c.rollback_id
                    }
                    for c in self.changes
                ]
            }
            
            with open(self.changes_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存变更记录失败：{e}")
    
    def create_change(self, change_type: ChangeType, component: str,
                     description: str, old_value: Any, new_value: Any) -> str:
        """创建变更记录"""
        change_id = hashlib.md5(
            f"{component}{description}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        change = ChangeRecord(
            change_id=change_id,
            change_type=change_type.value,
            component=component,
            description=description,
            old_value=old_value,
            new_value=new_value,
            status=ChangeStatus.PENDING.value,
            created_at=datetime.now().isoformat(),
            approved_at=None,
            approved_by=None,
            rollback_id=None
        )
        
        self.changes.append(change)
        self._save_changes()
        
        logger.info(f"创建变更记录：{change_id} - {description}")
        return change_id
    
    def approve_change(self, change_id: str, approved_by: str = "system") -> bool:
        """批准变更"""
        for change in self.changes:
            if change.change_id == change_id:
                change.status = ChangeStatus.APPROVED.value
                change.approved_at = datetime.now().isoformat()
                change.approved_by = approved_by
                self._save_changes()
                logger.info(f"变更已批准：{change_id}")
                return True
        return False
    
    def reject_change(self, change_id: str, reason: str = "") -> bool:
        """拒绝变更"""
        for change in self.changes:
            if change.change_id == change_id:
                change.status = ChangeStatus.REJECTED.value
                self._save_changes()
                logger.info(f"变更已拒绝：{change_id} - {reason}")
                return True
        return False
    
    def rollback_change(self, change_id: str) -> Optional[str]:
        """回滚变更"""
        original_change = None
        for change in self.changes:
            if change.change_id == change_id:
                original_change = change
                break
        
        if not original_change:
            return None
        
        # 创建回滚变更
        rollback_id = self.create_change(
            change_type=ChangeType.ROLLBACK,
            component=original_change.component,
            description=f"回滚变更 {change_id}",
            old_value=original_change.new_value,
            new_value=original_change.old_value
        )
        
        # 更新原始变更状态
        original_change.status = ChangeStatus.ROLLED_BACK.value
        original_change.rollback_id = rollback_id
        
        self._save_changes()
        logger.info(f"变更已回滚：{change_id} -> {rollback_id}")
        
        return rollback_id
    
    def create_snapshot(self, name: str, config_data: Dict[str, Any]) -> str:
        """创建配置快照"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_id = f"{name}_{timestamp}"
        
        snapshot_file = os.path.join(self.snapshots_dir, f"{snapshot_id}.json")
        
        snapshot_data = {
            "snapshot_id": snapshot_id,
            "name": name,
            "created_at": datetime.now().isoformat(),
            "version": self.current_version,
            "config": config_data
        }
        
        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"创建配置快照：{snapshot_id}")
        return snapshot_id
    
    def load_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """加载配置快照"""
        snapshot_file = os.path.join(self.snapshots_dir, f"{snapshot_id}.json")
        
        if os.path.exists(snapshot_file):
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return None
    
    def list_snapshots(self) -> List[Dict[str, Any]]:
        """列出所有快照"""
        snapshots = []
        
        for filename in os.listdir(self.snapshots_dir):
            if filename.endswith('.json'):
                snapshot_file = os.path.join(self.snapshots_dir, filename)
                try:
                    with open(snapshot_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        snapshots.append({
                            "snapshot_id": data.get("snapshot_id"),
                            "name": data.get("name"),
                            "created_at": data.get("created_at"),
                            "version": data.get("version")
                        })
                except Exception:
                    logger.debug(f"忽略异常: ", exc_info=True)
                    pass
        
        return sorted(snapshots, key=lambda x: x["created_at"], reverse=True)
    
    def get_change_history(self, component: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """获取变更历史"""
        changes = self.changes
        
        if component:
            changes = [c for c in changes if c.component == component]
        
        changes = sorted(changes, key=lambda x: x.created_at, reverse=True)[:limit]
        
        return [
            {
                "change_id": c.change_id,
                "change_type": c.change_type,
                "component": c.component,
                "description": c.description,
                "status": c.status,
                "created_at": c.created_at,
                "approved_at": c.approved_at
            }
            for c in changes
        ]
    
    def get_pending_changes(self) -> List[Dict[str, Any]]:
        """获取待审核变更"""
        pending = [c for c in self.changes if c.status == ChangeStatus.PENDING.value]
        
        return [
            {
                "change_id": c.change_id,
                "change_type": c.change_type,
                "component": c.component,
                "description": c.description,
                "created_at": c.created_at
            }
            for c in pending
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        status_counts = {}
        for status in ChangeStatus:
            status_counts[status.value] = len([c for c in self.changes if c.status == status.value])
        
        type_counts = {}
        for change_type in ChangeType:
            type_counts[change_type.value] = len([c for c in self.changes if c.change_type == change_type.value])
        
        return {
            "current_version": self.current_version,
            "total_changes": len(self.changes),
            "status_distribution": status_counts,
            "type_distribution": type_counts,
            "snapshot_count": len(self.list_snapshots())
        }


version_control = VersionControl()


def get_version_control() -> VersionControl:
    """获取版本控制单例"""
    return version_control
