#!/usr/bin/env python3
"""
skills系统主入口
"""

import logging
from typing import Dict, Any

from .model_manager import (
    get_model_registry,
    get_version_control,
    get_update_manager,
    get_compatibility_checker
)
from .agent_enhance import (
    get_agent_registry,
    get_communication_manager,
    get_collaboration_coordinator,
    get_workflow_engine,
    get_agent_evaluator,
    get_agency_agent_adapter,
    get_minimax_skill_adapter,
    get_claude_mem_adapter
)
from .performance import (
    get_cache_manager,
    get_task_scheduler,
    get_performance_monitor,
    get_resource_manager
)
from .extensions import (
    get_i18n_manager,
    get_workflow_editor,
    get_plugin_manager,
    get_claw_skill_adapter
)
from .monitoring import (
    get_metrics_registry,
    get_monitoring_panel,
    get_performance_analyzer,
    get_alert_manager
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class SkillsSystem:
    """skills系统"""
    
    def __init__(self):
        self.initialized = False
        self.components = {}
    
    def initialize(self, config: Dict[str, Any] = None):
        """初始化系统"""
        if self.initialized:
            return
        
        logger.info("开始初始化skills系统...")
        
        # 初始化各组件
        components = {
            "model_registry": get_model_registry(),
            "version_control": get_version_control(),
            "update_manager": get_update_manager(),
            "compatibility_checker": get_compatibility_checker(),
            "agent_registry": get_agent_registry(),
            "communication_manager": get_communication_manager(),
            "collaboration_coordinator": get_collaboration_coordinator(),
            "workflow_engine": get_workflow_engine(),
            "agent_evaluator": get_agent_evaluator(),
            "cache_manager": get_cache_manager(),
            "task_scheduler": get_task_scheduler(),
            "performance_monitor": get_performance_monitor(),
            "resource_manager": get_resource_manager(),
            "i18n_manager": get_i18n_manager(),
            "workflow_editor": get_workflow_editor(),
            "plugin_manager": get_plugin_manager(),
            "claw_skill_adapter": get_claw_skill_adapter(),
            "metrics_registry": get_metrics_registry(),
            "monitoring_panel": get_monitoring_panel(),
            "performance_analyzer": get_performance_analyzer(),
            "alert_manager": get_alert_manager()
        }
        
        self.components = components
        
        # 启动需要运行的组件
        self.components["task_scheduler"].start()
        self.components["monitoring_panel"].start()
        
        # 加载插件
        self.components["plugin_manager"].set_context(self.components)
        
        # 加载claw技能
        self.components["claw_skill_adapter"].register_all_skills()
        
        # 注册集成的代理
        print("注册集成的代理...")
        get_agency_agent_adapter().register_all_agents()
        get_minimax_skill_adapter().register_all_agents()
        get_claude_mem_adapter().register_all_agents()
        
        logger.info("skills系统初始化完成")
        self.initialized = True
    
    def shutdown(self):
        """关闭系统"""
        if not self.initialized:
            return
        
        logger.info("开始关闭skills系统...")
        
        # 停止运行的组件
        if "task_scheduler" in self.components:
            self.components["task_scheduler"].stop()
        if "monitoring_panel" in self.components:
            self.components["monitoring_panel"].stop()
        if "resource_manager" in self.components:
            self.components["resource_manager"].stop()
        
        # 卸载插件
        if "plugin_manager" in self.components:
            for plugin_name in self.components["plugin_manager"].list_plugins():
                self.components["plugin_manager"].unload_plugin(plugin_name)
        
        logger.info("skills系统已关闭")
        self.initialized = False
    
    def get_component(self, name: str) -> Any:
        """获取组件"""
        return self.components.get(name)
    
    def get_model_registry(self):
        """获取模型注册表"""
        return self.components.get("model_registry")
    
    def get_agent_registry(self):
        """获取Agent注册表"""
        return self.components.get("agent_registry")
    
    def get_cache_manager(self):
        """获取缓存管理器"""
        return self.components.get("cache_manager")
    
    def get_task_scheduler(self):
        """获取任务调度器"""
        return self.components.get("task_scheduler")
    
    def get_monitoring_panel(self):
        """获取监控面板"""
        return self.components.get("monitoring_panel")
    
    def get_workflow_editor(self):
        """获取工作流编辑器"""
        return self.components.get("workflow_editor")
    
    def get_plugin_manager(self):
        """获取插件管理器"""
        return self.components.get("plugin_manager")
    
    def get_i18n_manager(self):
        """获取国际化管理器"""
        return self.components.get("i18n_manager")
    
    def get_resource_manager(self):
        """获取资源管理器"""
        return self.components.get("resource_manager")


# 全局skills系统实例
_skills_system = None

def get_skills_system() -> SkillsSystem:
    """获取skills系统实例"""
    global _skills_system
    if _skills_system is None:
        _skills_system = SkillsSystem()
    return _skills_system


# 便捷函数
def initialize_skills(config: Dict[str, Any] = None):
    """初始化skills系统"""
    system = get_skills_system()
    system.initialize(config)


def shutdown_skills():
    """关闭skills系统"""
    system = get_skills_system()
    system.shutdown()


if __name__ == "__main__":
    # 测试
    import time
    
    # 初始化系统
    initialize_skills()
    
    # 获取系统实例
    system = get_skills_system()
    
    # 测试各组件
    print("系统初始化完成，组件列表:")
    for name, component in system.components.items():
        print(f"  - {name}")
    
    # 测试模型注册表
    model_registry = system.get_model_registry()
    print(f"\n模型注册表: {model_registry}")
    
    # 测试Agent注册表
    agent_registry = system.get_agent_registry()
    print(f"Agent注册表: {agent_registry}")
    
    # 测试监控面板
    monitoring_panel = system.get_monitoring_panel()
    time.sleep(2)
    metrics = monitoring_panel.get_metrics()
    print(f"\n系统指标: {metrics}")
    
    # 关闭系统
    shutdown_skills()
    print("\n系统已关闭")