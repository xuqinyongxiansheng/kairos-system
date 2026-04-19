"""
执行层
负责执行具体任务
"""

import logging
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ExecutionLayer:
    """执行层 - 执行具体任务"""
    
    def __init__(self):
        self.executors = {}
        self.execution_history = []
        self.active_executions = {}
    
    async def register_executor(self, name: str, executor_func: Callable):
        """
        注册执行器
        
        Args:
            name: 执行器名称
            executor_func: 执行函数
        """
        self.executors[name] = {
            'func': executor_func,
            'registered_at': datetime.now().isoformat(),
            'call_count': 0
        }
        logger.info(f"执行器注册成功：{name}")
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行任务
        
        Args:
            task: 任务数据
            
        Returns:
            执行结果
        """
        try:
            logger.info(f"开始执行任务：{task.get('type', 'unknown')}")
            
            executor_name = task.get('executor', 'default')
            
            if executor_name not in self.executors:
                logger.warning(f"执行器不存在：{executor_name}，使用默认执行器")
                result = await self._default_execute(task)
            else:
                executor = self.executors[executor_name]['func']
                result = await executor(task)
            
            execution_record = {
                'timestamp': datetime.now().isoformat(),
                'task_type': task.get('type', 'unknown'),
                'executor': executor_name,
                'result_status': result.get('status', 'unknown')
            }
            
            self.execution_history.append(execution_record)
            
            if executor_name in self.executors:
                self.executors[executor_name]['call_count'] += 1
            
            logger.info(f"任务执行完成：{result.get('status', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"执行层处理失败：{e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def _default_execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """默认执行逻辑"""
        logger.info(f"执行默认任务：{task.get('type', 'unknown')}")
        
        return {
            'status': 'success',
            'message': '任务已执行',
            'timestamp': datetime.now().isoformat()
        }
    
    async def execute_batch(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量执行任务"""
        logger.info(f"批量执行 {len(tasks)} 个任务")
        
        results = []
        success_count = 0
        error_count = 0
        
        for task in tasks:
            result = await self.execute(task)
            results.append(result)
            
            if result.get('status') == 'success':
                success_count += 1
            else:
                error_count += 1
        
        return {
            'status': 'success',
            'total': len(tasks),
            'success': success_count,
            'error': error_count,
            'results': results
        }
    
    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """获取执行状态"""
        if execution_id in self.active_executions:
            return {
                'status': 'success',
                'execution': self.active_executions[execution_id]
            }
        else:
            return {
                'status': 'not_found',
                'message': f'执行 ID 不存在：{execution_id}'
            }
    
    async def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        total_executions = len(self.execution_history)
        total_executors = len(self.executors)
        
        executor_stats = {}
        for name, executor in self.executors.items():
            executor_stats[name] = executor['call_count']
        
        return {
            'status': 'success',
            'total_executions': total_executions,
            'total_executors': total_executors,
            'executor_stats': executor_stats
        }
