#!/usr/bin/env python3
"""
CrewAI 服务集成
"""

import asyncio
import json
import os
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from kairos.agents.crewai_agents import CodeAgent, ResearchAgent, CrewCoordinator
from kairos.agents.model_expert import get_model_expert_system


class CrewAIService:
    """CrewAI 服务"""
    
    def __init__(self):
        self.tasks = {}
        self.expert_system = get_model_expert_system()
    
    def create_crew(self, task_description: str, agent_configs: Optional[list] = None):
        """创建代理团队"""
        coordinator = CrewCoordinator()
        
        # 添加默认代理
        if not agent_configs:
            coordinator.add_agent(ResearchAgent())
            coordinator.add_agent(CodeAgent())
        else:
            # 根据配置添加代理
            for config in agent_configs:
                if config.get("role") == "code":
                    coordinator.add_agent(CodeAgent())
                elif config.get("role") == "research":
                    coordinator.add_agent(ResearchAgent())
        
        return coordinator
    
    async def run_task(self, task_description: str, agent_configs: Optional[list] = None):
        """运行任务"""
        task_id = str(uuid.uuid4())
        
        # 创建任务记录
        self.tasks[task_id] = {
            "id": task_id,
            "description": task_description,
            "status": "running",
            "created_at": datetime.now().isoformat(),
            "result": None
        }
        
        try:
            # 创建代理团队
            coordinator = self.create_crew(task_description, agent_configs)
            
            # 运行任务
            result = await asyncio.to_thread(
                coordinator.run_task, 
                task_description
            )
            
            # 更新任务状态
            self.tasks[task_id].update({
                "status": "completed",
                "result": str(result),
                "completed_at": datetime.now().isoformat()
            })
            
            return {
                "task_id": task_id,
                "status": "completed",
                "result": str(result)
            }
            
        except Exception as e:
            # 更新任务状态
            self.tasks[task_id].update({
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            })
            
            return {
                "task_id": task_id,
                "status": "failed",
                "error": str(e)
            }
    
    def get_task_status(self, task_id: str):
        """获取任务状态"""
        if task_id in self.tasks:
            return self.tasks[task_id]
        return None
    
    def cancel_task(self, task_id: str):
        """取消任务"""
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = "cancelled"
            return True
        return False
    
    def get_model_recommendation(self, task_type: str):
        """获取模型推荐"""
        recommendation = self.expert_system.get_recommendation(task_type)
        return {
            "model": recommendation.model_name,
            "score": recommendation.score,
            "reasoning": recommendation.reasoning
        }
    
    def list_tasks(self):
        """列出任务"""
        return list(self.tasks.values())
    
    def clean_up_tasks(self):
        """清理任务"""
        # 清理24小时前的任务
        cutoff_time = datetime.now().timestamp() - (24 * 3600)
        tasks_to_remove = []
        
        for task_id, task in self.tasks.items():
            created_at = datetime.fromisoformat(task["created_at"]).timestamp()
            if created_at < cutoff_time:
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
        
        return len(tasks_to_remove)


# 全局 CrewAI 服务实例
_crewai_service = None

def get_crewai_service() -> CrewAIService:
    """获取 CrewAI 服务实例"""
    global _crewai_service
    if _crewai_service is None:
        _crewai_service = CrewAIService()
    return _crewai_service


if __name__ == "__main__":
    # 测试
    service = get_crewai_service()
    
    # 运行任务
    import asyncio
    
    async def test_task():
        result = await service.run_task(
            "Write a Python function to calculate Fibonacci sequence"
        )
        print(f"任务结果: {result}")
        
        # 获取任务状态
        task_id = result["task_id"]
        status = service.get_task_status(task_id)
        print(f"任务状态: {status}")
        
        # 获取模型推荐
        recommendation = service.get_model_recommendation("coding")
        print(f"模型推荐: {recommendation}")
    
    asyncio.run(test_task())