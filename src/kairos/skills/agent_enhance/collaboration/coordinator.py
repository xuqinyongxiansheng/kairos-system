#!/usr/bin/env python3
"""
协作协调器
管理多个Agent协同工作
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel

from ..professional_agents import get_agent_registry, ProfessionalAgent
from ..communication import get_communication_manager, CommunicationProtocol

logger = logging.getLogger(__name__)


class TaskAssignment(BaseModel):
    """任务分配"""
    task_id: str
    agent_id: str
    task_description: str
    context: Dict[str, Any] = {}
    priority: int = 1
    deadline: Optional[datetime] = None
    status: str = "pending"  # pending, in_progress, completed, failed


class CollaborationResult(BaseModel):
    """协作结果"""
    collaboration_id: str
    tasks: List[TaskAssignment]
    overall_status: str
    results: Dict[str, Any]
    total_time: float
    timestamp: datetime = datetime.now()


class CollaborationCoordinator:
    """协作协调器"""
    
    def __init__(self):
        self.agent_registry = get_agent_registry()
        self.communication_manager = get_communication_manager()
        self.active_collaborations: Dict[str, Dict[str, Any]] = {}
    
    async def initiate_collaboration(self, task: str, agent_ids: List[str], 
                                   context: Optional[Dict[str, Any]] = None) -> str:
        """启动协作"""
        collaboration_id = str(uuid.uuid4())
        
        # 验证Agent是否存在
        valid_agents = []
        for agent_id in agent_ids:
            agent = self.agent_registry.get_agent(agent_id)
            if agent:
                valid_agents.append(agent_id)
            else:
                logger.warning(f"Agent {agent_id} 不存在")
        
        if not valid_agents:
            raise ValueError("没有有效的Agent")
        
        # 分配任务
        tasks = []
        for i, agent_id in enumerate(valid_agents):
            task_id = str(uuid.uuid4())
            task_assignment = TaskAssignment(
                task_id=task_id,
                agent_id=agent_id,
                task_description=f"{task} (子任务 {i+1})",
                context=context or {},
                priority=len(valid_agents) - i
            )
            tasks.append(task_assignment)
        
        # 保存协作信息
        self.active_collaborations[collaboration_id] = {
            "tasks": tasks,
            "start_time": datetime.now(),
            "status": "in_progress",
            "results": {}
        }
        
        logger.info(f"启动协作: {collaboration_id}, 任务: {task}, Agent数量: {len(valid_agents)}")
        
        # 开始执行任务
        asyncio.create_task(self._execute_collaboration(collaboration_id))
        
        return collaboration_id
    
    async def _execute_collaboration(self, collaboration_id: str):
        """执行协作"""
        collaboration = self.active_collaborations.get(collaboration_id)
        if not collaboration:
            return
        
        tasks = collaboration['tasks']
        results = {}
        
        # 顺序执行任务
        for task_assignment in tasks:
            # 更新任务状态
            task_assignment.status = "in_progress"
            
            try:
                # 获取Agent
                agent = self.agent_registry.get_agent(task_assignment.agent_id)
                if not agent:
                    task_assignment.status = "failed"
                    results[task_assignment.task_id] = {
                        "status": "error",
                        "error": f"Agent {task_assignment.agent_id} 不存在"
                    }
                    continue
                
                # 执行任务
                result = await agent.process_task(
                    task_assignment.task_description,
                    task_assignment.context
                )
                
                # 更新任务状态
                if result.get("status") == "success":
                    task_assignment.status = "completed"
                    results[task_assignment.task_id] = result
                else:
                    task_assignment.status = "failed"
                    results[task_assignment.task_id] = result
                
                # 将结果传递给下一个任务
                if task_assignment != tasks[-1]:
                    tasks[tasks.index(task_assignment) + 1].context["previous_result"] = result
                
            except Exception as e:
                task_assignment.status = "failed"
                results[task_assignment.task_id] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # 计算总时间
        total_time = (datetime.now() - collaboration['start_time']).total_seconds()
        
        # 确定整体状态
        all_completed = all(task.status == "completed" for task in tasks)
        any_failed = any(task.status == "failed" for task in tasks)
        
        if all_completed:
            overall_status = "completed"
        elif any_failed:
            overall_status = "partially_completed"
        else:
            overall_status = "in_progress"
        
        # 更新协作信息
        collaboration['status'] = overall_status
        collaboration['results'] = results
        collaboration['total_time'] = total_time
        collaboration['end_time'] = datetime.now()
        
        logger.info(f"协作完成: {collaboration_id}, 状态: {overall_status}, 耗时: {total_time:.2f}秒")
    
    def get_collaboration_status(self, collaboration_id: str) -> Optional[Dict[str, Any]]:
        """获取协作状态"""
        return self.active_collaborations.get(collaboration_id)
    
    def list_collaborations(self) -> List[Dict[str, Any]]:
        """列出所有协作"""
        return list(self.active_collaborations.values())
    
    def cancel_collaboration(self, collaboration_id: str) -> bool:
        """取消协作"""
        if collaboration_id in self.active_collaborations:
            self.active_collaborations[collaboration_id]['status'] = "cancelled"
            logger.info(f"取消协作: {collaboration_id}")
            return True
        return False
    
    def cleanup_completed(self) -> int:
        """清理已完成的协作"""
        completed = []
        for collaboration_id, collaboration in self.active_collaborations.items():
            if collaboration['status'] in ["completed", "partially_completed", "cancelled"]:
                completed.append(collaboration_id)
        
        for collaboration_id in completed:
            del self.active_collaborations[collaboration_id]
        
        logger.info(f"清理了 {len(completed)} 个已完成的协作")
        return len(completed)


# 全局协作协调器实例
_collaboration_coordinator = None

def get_collaboration_coordinator() -> CollaborationCoordinator:
    """获取协作协调器实例"""
    global _collaboration_coordinator
    if _collaboration_coordinator is None:
        _collaboration_coordinator = CollaborationCoordinator()
    return _collaboration_coordinator


if __name__ == "__main__":
    # 测试
    import asyncio
    from ..professional_agents import get_code_agent, get_data_agent
    
    async def test_collaboration():
        coordinator = get_collaboration_coordinator()
        
        # 注册Agent
        code_agent = get_code_agent()
        data_agent = get_data_agent()
        
        agent_registry = get_agent_registry()
        agent_registry.register_agent(code_agent)
        agent_registry.register_agent(data_agent)
        
        # 启动协作
        collaboration_id = await coordinator.initiate_collaboration(
            task="分析销售数据并生成报告",
            agent_ids=["code_agent", "data_agent"],
            context={"data": [{"product": "A", "sales": 100}, {"product": "B", "sales": 200}]}
        )
        
        print(f"协作ID: {collaboration_id}")
        
        # 等待协作完成
        await asyncio.sleep(5)
        
        # 获取协作状态
        status = coordinator.get_collaboration_status(collaboration_id)
        if status:
            print(f"协作状态: {status['status']}")
            print(f"总耗时: {status.get('total_time', 0):.2f}秒")
            print(f"任务结果: {status.get('results', {})}")
    
    asyncio.run(test_collaboration())