#!/usr/bin/env python3
"""
执行输出层 - 行成
负责执行任务和操作，协调各组件工作
"""

import logging
import asyncio
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class Coordinator:
    """任务协调器"""
    
    def __init__(self):
        self.tasks = []
        self.running_tasks = []
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务"""
        task_id = f"task_{len(self.tasks) + 1}"
        task_info = {
            "id": task_id,
            "task": task,
            "status": "running",
            "start_time": datetime.now().isoformat()
        }
        
        self.tasks.append(task_info)
        self.running_tasks.append(task_id)
        
        try:
            result = await self._execute_task_impl(task)
            task_info["status"] = "completed"
            task_info["result"] = result
            task_info["end_time"] = datetime.now().isoformat()
        except Exception as e:
            task_info["status"] = "failed"
            task_info["error"] = str(e)
            task_info["end_time"] = datetime.now().isoformat()
        
        self.running_tasks.remove(task_id)
        return task_info
    
    async def _execute_task_impl(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务实现"""
        task_type = task.get("type", "general")
        
        if task_type == "command":
            return await self._execute_command(task)
        elif task_type == "python":
            return await self._execute_python(task)
        elif task_type == "workflow":
            return await self._execute_workflow(task)
        else:
            return await self._execute_general(task)
    
    async def _execute_command(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行命令"""
        command = task.get("command", "")
        timeout = task.get("timeout", 60)
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode("utf-8"),
                "stderr": stderr.decode("utf-8"),
                "returncode": process.returncode
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": "Command timed out"}
    
    async def _execute_python(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Python 代码"""
        code = task.get("code", "")
        timeout = task.get("timeout", 30)
        
        try:
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            try:
                process = await asyncio.create_subprocess_shell(
                    f"python {temp_file}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                return {
                    "success": process.returncode == 0,
                    "stdout": stdout.decode("utf-8"),
                    "stderr": stderr.decode("utf-8"),
                    "returncode": process.returncode
                }
            finally:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行工作流"""
        workflow_steps = task.get("steps", [])
        results = []
        
        for step in workflow_steps:
            result = await self.execute_task(step)
            results.append(result)
            
            if not result.get("success", False):
                break
        
        return {"results": results}
    
    async def _execute_general(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行通用任务"""
        return {
            "success": True,
            "message": "General task executed",
            "task": task
        }
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        for task in self.tasks:
            if task["id"] == task_id:
                return task
        return None
    
    def get_all_tasks(self) -> list:
        """获取所有任务"""
        return self.tasks


class ModelCallOptimizer:
    """模型调用优化器"""
    
    def __init__(self):
        self.call_history = []
    
    def optimize_call(self, model_name: str, prompt: str, parameters: dict = None) -> Dict[str, Any]:
        """优化模型调用"""
        call_info = {
            "model": model_name,
            "prompt_length": len(prompt),
            "parameters": parameters,
            "timestamp": datetime.now().isoformat()
        }
        
        self.call_history.append(call_info)
        optimized_params = self._optimize_parameters(model_name, parameters)
        
        return {
            "model": model_name,
            "prompt": prompt,
            "parameters": optimized_params,
            "optimized": optimized_params != parameters
        }
    
    def _optimize_parameters(self, model_name: str, parameters: dict = None) -> dict:
        """优化参数 - 适配 i5-7500/16GB"""
        if parameters is None:
            parameters = {}
        
        if model_name == "qwen2.5:3b-instruct-q4_K_M":
            parameters.setdefault("temperature", 0.6)
            parameters.setdefault("max_tokens", 1024)
            parameters.setdefault("num_ctx", 4096)
            parameters.setdefault("top_p", 0.85)
        
        return parameters
    
    def get_call_statistics(self) -> Dict[str, Any]:
        """获取调用统计"""
        stats = {}
        for call in self.call_history:
            model = call["model"]
            if model not in stats:
                stats[model] = {"count": 0, "total_prompt_length": 0}
            stats[model]["count"] += 1
            stats[model]["total_prompt_length"] += call["prompt_length"]
        
        return stats


class ExecutionLayer_XingCheng:
    """
    执行输出层 - 行成
    角色：任务执行者和协调员
    工作流程：接收决策 → 任务分解 → 资源分配 → 执行协调 → 输出结果
    """
    
    def __init__(self):
        self.name = "行成"
        self.role = "执行输出层"
        self.coordinator = Coordinator()
        self.model_optimizer = ModelCallOptimizer()
        self.execution_history = []
    
    async def execute_decisions(self, decision_result: Dict[str, Any]) -> Dict[str, Any]:
        """执行决策"""
        decisions = decision_result.get("decisions", [])
        execution_results = []
        
        for decision in decisions:
            task = self._decision_to_task(decision)
            result = await self.coordinator.execute_task(task)
            execution_results.append({
                "decision": decision,
                "task": task,
                "result": result
            })
        
        self._record_execution(decision_result, execution_results)
        
        all_completed = all(
            r["result"].get("status") == "completed"
            for r in execution_results
        )
        
        logger.info(f"行成执行完成：{len(execution_results)} 个任务")
        
        return {
            "status": "success",
            "type": "execution",
            "status_summary": "completed" if all_completed else "partial",
            "decisions": decisions,
            "execution_results": execution_results,
            "processed_by": self.name,
            "timestamp": datetime.now().isoformat()
        }
    
    def _decision_to_task(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """将决策转换为任务"""
        action = decision.get("action", "")
        target = decision.get("target", "")
        
        if action == "紧急执行":
            return {
                "type": "command",
                "command": f"echo '紧急执行任务：{target}'",
                "priority": "high",
                "timeout": 30
            }
        elif action == "优先执行":
            return {
                "type": "python",
                "code": f"print('优先执行任务：{target}')",
                "priority": "medium",
                "timeout": 60
            }
        else:
            return {
                "type": "general",
                "action": action,
                "target": target,
                "priority": "low"
            }
    
    def optimize_model_call(self, model_name: str, prompt: str, parameters: dict = None) -> Dict[str, Any]:
        """优化模型调用"""
        return self.model_optimizer.optimize_call(model_name, prompt, parameters)
    
    async def get_execution_history(self, limit: int = 10) -> list:
        """获取执行历史"""
        return self.execution_history[-limit:]
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return self.coordinator.get_task_status(task_id)
    
    async def get_all_tasks(self) -> list:
        """获取所有任务"""
        return self.coordinator.get_all_tasks()
    
    async def get_model_call_statistics(self) -> Dict[str, Any]:
        """获取模型调用统计"""
        return self.model_optimizer.get_call_statistics()
    
    def _record_execution(self, decision_result: Dict[str, Any], execution_results: list):
        """记录执行历史"""
        self.execution_history.append({
            "decision_result": decision_result,
            "execution_results": execution_results,
            "timestamp": datetime.now().isoformat()
        })
    
    async def get_agent_info(self) -> Dict[str, Any]:
        """获取 Agent 信息"""
        return {
            "name": self.name,
            "role": self.role,
            "components": ["Coordinator", "ModelCallOptimizer"],
            "description": "负责执行任务和操作，协调各组件工作"
        }
