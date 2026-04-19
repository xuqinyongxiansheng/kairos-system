#!/usr/bin/env python3
"""
插件系统
实现插件系统，支持第三方功能扩展
"""

import importlib
import os
import sys
import inspect
from typing import Dict, Any, List, Optional


class Plugin:
    """插件基类"""
    
    def __init__(self):
        self.name = ""
        self.version = ""
        self.description = ""
        self.author = ""
    
    def initialize(self, context: Dict[str, Any]) -> bool:
        """初始化插件"""
        return True
    
    def shutdown(self) -> bool:
        """关闭插件"""
        return True
    
    def get_commands(self) -> Dict[str, callable]:
        """获取插件命令"""
        return {}
    
    def get_hooks(self) -> Dict[str, callable]:
        """获取插件钩子"""
        return {}


class PluginManager:
    """插件管理器"""
    
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = plugins_dir
        self.plugins: Dict[str, Plugin] = {}
        self.context: Dict[str, Any] = {}
        self._load_plugins()
        os.makedirs(self.plugins_dir, exist_ok=True)
    
    def _load_plugins(self):
        """加载插件"""
        try:
            # 添加插件目录到Python路径
            if self.plugins_dir not in sys.path:
                sys.path.insert(0, self.plugins_dir)
            
            # 遍历插件目录
            if os.path.exists(self.plugins_dir):
                for item in os.listdir(self.plugins_dir):
                    item_path = os.path.join(self.plugins_dir, item)
                    if os.path.isdir(item_path) and not item.startswith('.'):
                        # 检查是否有__init__.py文件
                        init_file = os.path.join(item_path, "__init__.py")
                        if os.path.exists(init_file):
                            try:
                                # 导入插件模块
                                module_name = item
                                module = importlib.import_module(module_name)
                                
                                # 查找Plugin子类
                                for name, obj in inspect.getmembers(module):
                                    if inspect.isclass(obj) and issubclass(obj, Plugin) and obj != Plugin:
                                        # 创建插件实例
                                        plugin = obj()
                                        # 初始化插件
                                        if plugin.initialize(self.context):
                                            self.plugins[plugin.name or module_name] = plugin
                                            print(f"加载插件: {plugin.name or module_name}")
                                        break
                            except Exception as e:
                                print(f"加载插件 {item} 失败: {e}")
        except Exception as e:
            print(f"加载插件失败: {e}")
    
    def set_context(self, context: Dict[str, Any]):
        """设置上下文"""
        self.context.update(context)
        # 更新所有已加载插件的上下文
        for plugin in self.plugins.values():
            plugin.initialize(self.context)
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """获取插件"""
        return self.plugins.get(name)
    
    def list_plugins(self) -> List[str]:
        """列出插件"""
        return list(self.plugins.keys())
    
    def load_plugin(self, plugin_path: str) -> bool:
        """加载插件"""
        try:
            # 检查插件路径
            if not os.path.exists(plugin_path):
                return False
            
            # 复制到插件目录
            plugin_name = os.path.basename(plugin_path)
            dest_path = os.path.join(self.plugins_dir, plugin_name)
            
            if os.path.isdir(plugin_path):
                # 复制目录
                import shutil
                shutil.copytree(plugin_path, dest_path)
            else:
                # 复制文件
                os.makedirs(self.plugins_dir, exist_ok=True)
                import shutil
                shutil.copy(plugin_path, dest_path)
            
            # 重新加载插件
            self._load_plugins()
            return True
        except Exception as e:
            print(f"加载插件失败: {e}")
            return False
    
    def unload_plugin(self, name: str) -> bool:
        """卸载插件"""
        if name not in self.plugins:
            return False
        
        try:
            plugin = self.plugins[name]
            # 关闭插件
            plugin.shutdown()
            # 删除插件
            del self.plugins[name]
            print(f"卸载插件: {name}")
            return True
        except Exception as e:
            print(f"卸载插件失败: {e}")
            return False
    
    def reload_plugin(self, name: str) -> bool:
        """重新加载插件"""
        # 先卸载
        if not self.unload_plugin(name):
            return False
        
        # 重新加载所有插件
        self._load_plugins()
        return name in self.plugins
    
    def get_commands(self) -> Dict[str, callable]:
        """获取所有插件命令"""
        commands = {}
        for plugin in self.plugins.values():
            plugin_commands = plugin.get_commands()
            commands.update(plugin_commands)
        return commands
    
    def get_hooks(self) -> Dict[str, List[callable]]:
        """获取所有插件钩子"""
        hooks = {}
        for plugin in self.plugins.values():
            plugin_hooks = plugin.get_hooks()
            for hook_name, hook_func in plugin_hooks.items():
                if hook_name not in hooks:
                    hooks[hook_name] = []
                hooks[hook_name].append(hook_func)
        return hooks
    
    def execute_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """执行钩子"""
        results = []
        hooks = self.get_hooks()
        if hook_name in hooks:
            for hook_func in hooks[hook_name]:
                try:
                    result = hook_func(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    print(f"执行钩子 {hook_name} 失败: {e}")
        return results


# 全局插件管理器实例
_plugin_manager = None

def get_plugin_manager() -> PluginManager:
    """获取插件管理器实例"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


if __name__ == "__main__":
    # 测试
    manager = get_plugin_manager()
    
    # 列出插件
    plugins = manager.list_plugins()
    print(f"已加载插件: {plugins}")
    
    # 执行钩子
    results = manager.execute_hook("on_startup")
    print(f"执行启动钩子结果: {results}")