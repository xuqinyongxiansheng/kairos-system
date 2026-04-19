"""
权限系统
实现权限管理和访问控制
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class Permission(Enum):
    """权限枚举"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class AccessLevel(Enum):
    """访问级别"""
    NONE = 0
    READ = 1
    WRITE = 2
    EXECUTE = 3
    ADMIN = 4


class PermissionManager:
    """权限管理器"""
    
    def __init__(self):
        self.permissions = {}
        self.role_permissions = {
            'user': [Permission.READ],
            'developer': [Permission.READ, Permission.WRITE],
            'admin': [Permission.READ, Permission.WRITE, Permission.EXECUTE, Permission.ADMIN]
        }
        self.access_history = []
    
    async def grant_permission(self, role: str, permission: Permission) -> Dict[str, Any]:
        """授予权限"""
        if role not in self.role_permissions:
            self.role_permissions[role] = []
        
        if permission not in self.role_permissions[role]:
            self.role_permissions[role].append(permission)
            logger.info(f"权限已授予：{role} - {permission.value}")
        
        return {
            'status': 'success',
            'role': role,
            'permission': permission.value
        }
    
    async def revoke_permission(self, role: str, permission: Permission) -> Dict[str, Any]:
        """撤销权限"""
        if role in self.role_permissions and permission in self.role_permissions[role]:
            self.role_permissions[role].remove(permission)
            logger.info(f"权限已撤销：{role} - {permission.value}")
        
        return {
            'status': 'success',
            'role': role,
            'permission': permission.value
        }
    
    async def check_permission(self, role: str, permission: Permission) -> Dict[str, Any]:
        """检查权限"""
        has_permission = False
        
        if role in self.role_permissions:
            has_permission = permission in self.role_permissions[role] or \
                           Permission.ADMIN in self.role_permissions[role]
        
        self._log_access(role, permission, has_permission)
        
        return {
            'status': 'success',
            'has_permission': has_permission,
            'role': role,
            'permission': permission.value
        }
    
    def _log_access(self, role: str, permission: Permission, granted: bool):
        """记录访问日志"""
        self.access_history.append({
            'timestamp': datetime.now().isoformat(),
            'role': role,
            'permission': permission.value,
            'granted': granted
        })
    
    async def get_access_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取访问历史"""
        return self.access_history[-limit:]
    
    async def get_permission_summary(self) -> Dict[str, Any]:
        """获取权限摘要"""
        return {
            'status': 'success',
            'roles': list(self.role_permissions.keys()),
            'total_permissions': sum(len(perms) for perms in self.role_permissions.values())
        }
