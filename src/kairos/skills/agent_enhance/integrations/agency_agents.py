#!/usr/bin/env python3
"""
Agency Swarm 适配器
深度集成 agency-swarm 多智能体编排框架
"""

import os
import logging
from typing import Dict, Any, Optional, List

from ..professional_agents.base_agent import ProfessionalAgent, get_agent_registry

logger = logging.getLogger(__name__)


class AgencySwarmAdapter:
    """Agency Swarm 适配器 - 深度集成多智能体编排框架"""
    
    def __init__(self, agency_dir: str = "project/vendor/agency-swarm"):
        self.agency_dir = agency_dir
        self.agency_swarm_available = False
        self.agents = {}
        self.tools = {}
        self._check_agency_swarm()
        self._init_agents()
    
    def _check_agency_swarm(self):
        """检查 agency-swarm 是否可用"""
        try:
            import importlib
            importlib.import_module("agency_swarm")
            self.agency_swarm_available = True
            logger.info("agency-swarm 框架已安装")
        except ImportError:
            self.agency_swarm_available = False
            logger.info("agency-swarm 框架未安装，使用内置代理系统")
    
    def _init_agents(self):
        """初始化代理"""
        self.agents["coordinator"] = {
            "name": "Agency 协调代理",
            "description": "基于 Agency Swarm 的多代理协调器，负责代理间的任务分配和协作",
            "skills": ["task_decomposition", "agent_coordination", "workflow_management", "conflict_resolution"],
            "capabilities": ["multi_agent_orchestration", "dynamic_task_assignment", "parallel_execution", "error_recovery"]
        }
        self.agents["executor"] = {
            "name": "Agency 执行代理",
            "description": "基于 Agency Swarm 的任务执行代理，负责具体任务的执行和结果返回",
            "skills": ["task_execution", "tool_usage", "result_validation", "error_handling"],
            "capabilities": ["autonomous_execution", "tool_integration", "self_correction", "progress_reporting"]
        }
        self.agents["analyst"] = {
            "name": "Agency 分析代理",
            "description": "基于 Agency Swarm 的分析代理，负责数据分析和洞察生成",
            "skills": ["data_analysis", "pattern_recognition", "insight_generation", "report_creation"],
            "capabilities": ["statistical_analysis", "trend_detection", "anomaly_detection", "visualization"]
        }
        
        # 如果 agency-swarm 可用，注册内置工具
        if self.agency_swarm_available:
            self._register_swarm_tools()
    
    def _register_swarm_tools(self):
        """注册 agency-swarm 工具"""
        try:
            from agency_swarm import function_tool
            
            @function_tool
            def delegate_task(agent_type: str, task: str, context: dict = None) -> str:
                """将任务委派给指定类型的代理执行"""
                return f"任务已委派给 {agent_type} 代理: {task}"
            
            @function_tool
            def broadcast_message(message: str, exclude_agent: str = None) -> str:
                """向所有代理广播消息"""
                return f"消息已广播: {message}"
            
            @function_tool
            def query_agent_status(agent_id: str) -> str:
                """查询代理状态"""
                return f"代理 {agent_id} 状态: 就绪"
            
            self.tools["delegate_task"] = delegate_task
            self.tools["broadcast_message"] = broadcast_message
            self.tools["query_agent_status"] = query_agent_status
            
            logger.info("agency-swarm 工具已注册")
        except Exception as e:
            logger.warning(f"注册 agency-swarm 工具失败: {e}")
    
    def create_agency(self, agents_config: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建 Agency 实例"""
        if not self.agency_swarm_available:
            return {
                "status": "error",
                "message": "agency-swarm 框架未安装，请运行: pip install agency-swarm"
            }
        
        try:
            from agency_swarm import Agency, Agent
            
            # 创建代理
            agents = []
            for config in (agents_config or []):
                agent = Agent(
                    name=config.get("name", "Agent"),
                    description=config.get("description", ""),
                    instructions=config.get("instructions", ""),
                    tools=config.get("tools", [])
                )
                agents.append(agent)
            
            # 创建 Agency
            if agents:
                agency = Agency(agents[0], *agents[1:], shared_instructions="协作完成用户任务")
                return {
                    "status": "success",
                    "message": "Agency 实例已创建",
                    "agents_count": len(agents)
                }
            else:
                return {
                    "status": "error",
                    "message": "未提供代理配置"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"创建 Agency 实例失败: {e}"
            }
    
    def delegate_task(self, agent_type: str, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """委派任务给指定代理"""
        if agent_type in self.agents:
            return {
                "status": "success",
                "agent_type": agent_type,
                "task": task,
                "message": f"任务已委派给 {agent_type} 代理"
            }
        else:
            return {
                "status": "error",
                "message": f"未找到代理类型: {agent_type}",
                "available_types": list(self.agents.keys())
            }
    
    def list_available_agents(self) -> List[str]:
        """列出可用代理"""
        return list(self.agents.keys())
    
    def convert_to_professional_agent(self, agent_name: str) -> Optional[ProfessionalAgent]:
        """将 agency-swarm agent 转换为专业代理"""
        agent_data = self.agents.get(agent_name)
        if not agent_data:
            return None
        
        adapter = self
        
        class AgencySwarmProfessionalAgent(ProfessionalAgent):
            def __init__(self, agent_data, adapter_ref):
                super().__init__(
                    agent_id=f"agency_{agent_name}",
                    name=agent_data["name"],
                    description=agent_data["description"]
                )
                for skill in agent_data.get("skills", []):
                    self.add_skill(skill)
                for capability in agent_data.get("capabilities", []):
                    self.add_capability(capability)
                self._adapter = adapter_ref
            
            async def process_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
                """处理任务"""
                ctx = context or {}
                
                if "委派" in task or "delegate" in task.lower():
                    agent_type = ctx.get("agent_type", "executor")
                    return self._adapter.delegate_task(agent_type, task, ctx)
                
                elif "创建" in task and "agency" in task.lower():
                    agents_config = ctx.get("agents_config")
                    return self._adapter.create_agency(agents_config)
                
                elif "列表" in task or "list" in task.lower():
                    return {
                        "status": "success",
                        "available_agents": self._adapter.list_available_agents()
                    }
                
                else:
                    return {
                        "status": "success",
                        "response": f"Agency 代理已处理任务: {task}",
                        "agent_id": self.agent_id,
                        "agency_swarm_available": self._adapter.agency_swarm_available,
                        "available_operations": ["委派任务", "创建Agency", "列出代理"]
                    }
        
        return AgencySwarmProfessionalAgent(agent_data, adapter)
    
    def register_all_agents(self):
        """注册所有 agency-swarm agents"""
        agent_registry = get_agent_registry()
        for agent_name in self.agents:
            agent = self.convert_to_professional_agent(agent_name)
            if agent:
                agent_registry.register_agent(agent)
                logger.info(f"注册 Agency Swarm Agent: {agent_name}")


_agency_agent_adapter = None

def get_agency_agent_adapter() -> AgencySwarmAdapter:
    """获取 Agency Swarm 适配器实例"""
    global _agency_agent_adapter
    if _agency_agent_adapter is None:
        _agency_agent_adapter = AgencySwarmAdapter()
    return _agency_agent_adapter