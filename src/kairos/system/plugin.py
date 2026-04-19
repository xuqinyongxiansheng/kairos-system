"""
插件系统
管理插件的加载和执行
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    description: str
    author: str = ""
    status: str = "inactive"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self.plugins = {}
        self.plugin_history = []
        self.plugin_dir = "./plugins"
    
    async def register_plugin(self, plugin_info: Dict[str, Any]) -> Dict[str, Any]:
        """注册插件"""
        name = plugin_info.get('name', '')
        
        if not name:
            return {
                'status': 'error',
                'error': '插件名称不能为空'
            }
        
        info = PluginInfo(
            name=name,
            version=plugin_info.get('version', '1.0.0'),
            description=plugin_info.get('description', ''),
            author=plugin_info.get('author', '')
        )
        
        self.plugins[name] = info
        
        logger.info(f"插件注册：{name}")
        
        self.plugin_history.append({
            'action': 'register',
            'plugin': name,
            'timestamp': datetime.now().isoformat()
        })
        
        return {
            'status': 'success',
            'plugin': info.to_dict()
        }
    
    async def activate_plugin(self, name: str) -> Dict[str, Any]:
        """激活插件"""
        if name not in self.plugins:
            return {
                'status': 'not_found',
                'message': f'插件不存在：{name}'
            }
        
        self.plugins[name].status = 'active'
        
        logger.info(f"插件激活：{name}")
        
        self.plugin_history.append({
            'action': 'activate',
            'plugin': name,
            'timestamp': datetime.now().isoformat()
        })
        
        return {
            'status': 'success',
            'plugin': name
        }
    
    async def deactivate_plugin(self, name: str) -> Dict[str, Any]:
        """停用插件"""
        if name not in self.plugins:
            return {
                'status': 'not_found',
                'message': f'插件不存在：{name}'
            }
        
        self.plugins[name].status = 'inactive'
        
        logger.info(f"插件停用：{name}")
        
        self.plugin_history.append({
            'action': 'deactivate',
            'plugin': name,
            'timestamp': datetime.now().isoformat()
        })
        
        return {
            'status': 'success',
            'plugin': name
        }
    
    async def unregister_plugin(self, name: str) -> Dict[str, Any]:
        """注销插件"""
        if name not in self.plugins:
            return {
                'status': 'not_found',
                'message': f'插件不存在：{name}'
            }
        
        del self.plugins[name]
        
        logger.info(f"插件注销：{name}")
        
        self.plugin_history.append({
            'action': 'unregister',
            'plugin': name,
            'timestamp': datetime.now().isoformat()
        })
        
        return {
            'status': 'success',
            'plugin': name
        }
    
    async def list_plugins(self) -> Dict[str, Any]:
        """列出插件"""
        return {
            'status': 'success',
            'plugins': [p.to_dict() for p in self.plugins.values()],
            'count': len(self.plugins)
        }
    
    async def get_plugin_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取插件历史"""
        return self.plugin_history[-limit:]
    
    async def get_plugin_summary(self) -> Dict[str, Any]:
        """获取插件摘要"""
        active = sum(1 for p in self.plugins.values() if p.status == 'active')
        
        return {
            'status': 'success',
            'total_plugins': len(self.plugins),
            'active_plugins': active,
            'inactive_plugins': len(self.plugins) - active
        }
