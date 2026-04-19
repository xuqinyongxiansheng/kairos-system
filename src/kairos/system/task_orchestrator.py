#!/usr/bin/env python3
"""
任务协调器 - 神将元系统
负责协调多个Agent完成任务
"""

import sys
import os
import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional

logger = logging.getLogger("TaskOrchestrator")


class PlannerAgent:
    """规划Agent"""
    
    def __init__(self):
        self.name = "PlannerAgent"
        logger.info("规划Agent初始化完成")
    
    async def analyze_task(self, task: Dict) -> Dict[str, Any]:
        """分析任务"""
        return {
            "task_type": task.get("type", "unknown"),
            "complexity": "medium",
            "required_skills": ["analysis", "planning"],
            "estimated_time": 30
        }
    
    async def create_plan(self, task_analysis: Dict) -> Dict[str, Any]:
        """创建计划"""
        return {
            "plan_id": str(uuid.uuid4()),
            "steps": [
                {"step": 1, "action": "analyze", "status": "pending"},
                {"step": 2, "action": "execute", "status": "pending"},
                {"step": 3, "action": "verify", "status": "pending"}
            ],
            "created_at": asyncio.get_event_loop().time()
        }
    
    async def adjust_plan(self, plan: Dict, evaluation: Dict) -> Dict[str, Any]:
        """调整计划"""
        adjusted_plan = plan.copy()
        adjusted_plan["adjusted"] = True
        adjusted_plan["adjustment_reason"] = evaluation.get("error", "需要优化")
        return adjusted_plan


class GeneratorAgent:
    """生成Agent"""
    
    def __init__(self):
        self.name = "GeneratorAgent"
        logger.info("生成Agent初始化完成")
    
    async def execute_plan(self, plan: Dict) -> Dict[str, Any]:
        """执行计划"""
        results = []
        for step in plan.get("steps", []):
            results.append({
                "step": step["step"],
                "action": step["action"],
                "result": "completed",
                "timestamp": asyncio.get_event_loop().time()
            })
        
        return {
            "plan_id": plan.get("plan_id"),
            "results": results,
            "status": "completed"
        }


class EvaluatorAgent:
    """评估Agent"""
    
    def __init__(self):
        self.name = "EvaluatorAgent"
        logger.info("评估Agent初始化完成")
    
    async def evaluate_result(self, result: Dict, task: Dict) -> Dict[str, Any]:
        """评估结果"""
        success = result.get("status") == "completed"
        
        return {
            "success": success,
            "score": 0.85 if success else 0.3,
            "feedback": "任务执行成功" if success else "任务执行失败",
            "improvements": [] if success else ["需要优化执行流程"]
        }


class TaskOrchestrator:
    """任务协调器 - 神将元系统"""
    
    def __init__(self):
        """初始化任务协调器"""
        self.planner = PlannerAgent()
        self.generator = GeneratorAgent()
        self.evaluator = EvaluatorAgent()
        self.tasks = {}
        self.logger = logging.getLogger(__name__)
        self.logger.info("任务协调器初始化完成")
    
    async def process_task(self, task: Dict) -> Dict:
        """处理用户任务"""
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            "status": "processing",
            "task": task,
            "start_time": asyncio.get_event_loop().time()
        }
        
        try:
            self.logger.info(f"处理任务 {task_id}: {task.get('content')}")
            task_analysis = await self.planner.analyze_task(task)
            
            plan = await self.planner.create_plan(task_analysis)
            self.tasks[task_id]["plan"] = plan
            
            result = await self.generator.execute_plan(plan)
            self.tasks[task_id]["result"] = result
            
            evaluation = await self.evaluator.evaluate_result(result, task)
            self.tasks[task_id]["evaluation"] = evaluation
            
            if not evaluation.get('success'):
                self.logger.info(f"任务 {task_id} 失败，调整计划")
                adjusted_plan = await self.planner.adjust_plan(plan, evaluation)
                self.tasks[task_id]["adjusted_plan"] = adjusted_plan
                
                result = await self.generator.execute_plan(adjusted_plan)
                self.tasks[task_id]["result"] = result
                
                evaluation = await self.evaluator.evaluate_result(result, task)
                self.tasks[task_id]["evaluation"] = evaluation
            
            self.tasks[task_id]["status"] = "completed"
            self.tasks[task_id]["end_time"] = asyncio.get_event_loop().time()
            
            return {
                "task_id": task_id,
                "success": evaluation.get('success'),
                "result": result,
                "evaluation": evaluation,
                "status": "completed"
            }
        except Exception as e:
            self.logger.error(f"处理任务 {task_id} 时出错: {e}")
            self.tasks[task_id]["status"] = "failed"
            self.tasks[task_id]["error"] = str(e)
            
            return {
                "task_id": task_id,
                "success": False,
                "error": str(e),
                "status": "failed"
            }
    
    async def get_task_status(self, task_id: str) -> Dict:
        """获取任务状态"""
        task = self.tasks.get(task_id)
        if not task:
            return {
                "success": False,
                "error": "任务未找到"
            }
        
        return {
            "success": True,
            "task": task
        }
    
    async def cancel_task(self, task_id: str) -> Dict:
        """取消任务"""
        task = self.tasks.get(task_id)
        if not task:
            return {
                "success": False,
                "error": "任务未找到"
            }
        
        if task.get("status") == "processing":
            task["status"] = "cancelled"
            return {
                "success": True,
                "message": "任务已取消"
            }
        else:
            return {
                "success": False,
                "error": f"任务已经是 {task.get('status')} 状态"
            }
    
    async def get_all_tasks(self) -> Dict:
        """获取所有任务"""
        return {
            "success": True,
            "tasks": self.tasks
        }
    
    async def clear_completed_tasks(self) -> Dict:
        """清除已完成的任务"""
        completed_tasks = [task_id for task_id, task in self.tasks.items() if task.get("status") in ["completed", "failed", "cancelled"]]
        for task_id in completed_tasks:
            del self.tasks[task_id]
        
        return {
            "success": True,
            "message": f"已清除 {len(completed_tasks)} 个任务"
        }


class ShenJiangYuanSystem:
    """神将元系统 - 连接大脑和四肢的中间层"""
    
    def __init__(self):
        """初始化神将元系统"""
        self.orchestrator = TaskOrchestrator()
        self.logger = logging.getLogger(__name__)
        self.logger.info("神将元系统初始化完成")
    
    async def process_user_task(self, task: Dict) -> Dict:
        """处理用户任务"""
        self.logger.info(f"接收到用户任务: {task.get('content')}")
        
        result = await self.orchestrator.process_task(task)
        
        return result
    
    async def get_system_status(self) -> Dict:
        """获取系统状态"""
        tasks = await self.orchestrator.get_all_tasks()
        
        return {
            "success": True,
            "task_orchestrator": {
                "tasks_count": len(tasks.get("tasks", {})),
                "status": "running"
            }
        }


_task_orchestrator = None
_shen_jiang_yuan_system = None


def get_task_orchestrator() -> TaskOrchestrator:
    """获取任务协调器实例"""
    global _task_orchestrator
    
    if _task_orchestrator is None:
        _task_orchestrator = TaskOrchestrator()
    
    return _task_orchestrator


def get_shen_jiang_yuan_system() -> ShenJiangYuanSystem:
    """获取神将元系统实例"""
    global _shen_jiang_yuan_system
    
    if _shen_jiang_yuan_system is None:
        _shen_jiang_yuan_system = ShenJiangYuanSystem()
    
    return _shen_jiang_yuan_system
