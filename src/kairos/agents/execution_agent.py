"""
执行 Agent
负责执行具体任务
"""

import logging
from typing import Dict, Any, List, Callable
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ExecutionAgent(BaseAgent):
    """执行 Agent - 执行具体任务"""
    
    def __init__(self):
        super().__init__("ExecutionAgent", "执行具体任务")
        self.executors = {}
        self.execution_history = []
    
    async def initialize(self):
        """初始化执行 Agent"""
        logger.info("初始化执行 Agent")
        return {'status': 'success', 'message': '执行 Agent 初始化完成'}
    
    async def register_executor(self, name: str, executor_func: Callable):
        """注册执行器"""
        self.executors[name] = executor_func
        logger.info(f"执行器注册：{name}")
        return {'status': 'success', 'executor': name}
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行任务
        
        Args:
            task: 任务数据
            
        Returns:
            执行结果
        """
        try:
            logger.info(f"执行任务：{task.get('type', 'unknown')}")
            
            executor_name = task.get('executor', 'default')
            
            if executor_name in self.executors:
                executor = self.executors[executor_name]
                result = await executor(task)
            else:
                result = await self._default_execute(task)
            
            execution_record = {
                'timestamp': self._get_timestamp(),
                'task_type': task.get('type', 'unknown'),
                'executor': executor_name,
                'result': result
            }
            
            self.execution_history.append(execution_record)
            
            return result
            
        except Exception as e:
            logger.error(f"执行失败：{e}")
            return {'status': 'error', 'error': str(e)}
    
    async def _default_execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """默认执行逻辑"""
        return {
            'status': 'success',
            'message': '任务已执行',
            'timestamp': self._get_timestamp()
        }
    
    async def execute_batch(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量执行"""
        results = []
        success_count = 0
        
        for task in tasks:
            result = await self.execute(task)
            results.append(result)
            if result.get('status') == 'success':
                success_count += 1
        
        return {
            'status': 'success',
            'total': len(tasks),
            'success': success_count,
            'results': results
        }
    
    async def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        return {
            'status': 'success',
            'total_executions': len(self.execution_history),
            'executors': list(self.executors.keys())
        }
