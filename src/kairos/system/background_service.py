"""
后台服务模块
提供持续运行、定时任务、任务队列等功能
"""

import asyncio
import logging
import os
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """服务状态"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    URGENT = 20


@dataclass
class ScheduledTask:
    """定时任务"""
    id: str
    name: str
    cron_expression: str
    handler: str
    parameters: Dict[str, Any]
    last_run: Optional[str]
    next_run: Optional[str]
    status: str
    enabled: bool


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    status: str
    result: Any
    error: Optional[str]
    started_at: str
    completed_at: str
    duration_ms: int


class BackgroundService:
    """后台服务"""
    
    def __init__(self, service_name: str = "鸿蒙小雨后台服务"):
        self.service_name = service_name
        self.status = ServiceStatus.STOPPED
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.task_results: List[TaskResult] = []
        self.task_handlers: Dict[str, Callable] = {}
        self.task_queue: asyncio.Queue = None
        self.worker_task = None
        self.scheduler_task = None
        self._running = False
        self._lock = threading.Lock()
        
        self._register_default_handlers()
        logger.info(f"后台服务初始化: {service_name}")
    
    def _register_default_handlers(self):
        """注册默认处理器"""
        self.task_handlers = {
            "health_check": self._health_check_handler,
            "cleanup": self._cleanup_handler,
            "report": self._report_handler,
            "sync": self._sync_handler
        }
    
    async def _health_check_handler(self, **kwargs) -> Dict[str, Any]:
        """健康检查处理器"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "tasks_count": len(self.scheduled_tasks),
            "results_count": len(self.task_results)
        }
    
    async def _cleanup_handler(self, **kwargs) -> Dict[str, Any]:
        """清理处理器"""
        max_results = kwargs.get("max_results", 1000)
        if len(self.task_results) > max_results:
            self.task_results = self.task_results[-max_results:]
        return {"cleaned": True, "remaining": len(self.task_results)}
    
    async def _report_handler(self, **kwargs) -> Dict[str, Any]:
        """报告处理器"""
        return {
            "report_time": datetime.now().isoformat(),
            "scheduled_tasks": len(self.scheduled_tasks),
            "total_executions": len(self.task_results)
        }
    
    async def _sync_handler(self, **kwargs) -> Dict[str, Any]:
        """同步处理器"""
        return {"synced": True, "timestamp": datetime.now().isoformat()}
    
    def register_handler(self, name: str, handler: Callable):
        """注册任务处理器"""
        self.task_handlers[name] = handler
        logger.info(f"任务处理器注册: {name}")
    
    def schedule_task(self, name: str, cron_expression: str, handler: str,
                     parameters: Dict[str, Any] = None, enabled: bool = True) -> Dict[str, Any]:
        """创建定时任务"""
        task_id = f"task_{int(datetime.now().timestamp())}_{name}"
        
        # 解析cron表达式计算下次运行时间
        next_run = self._calculate_next_run(cron_expression)
        
        task = ScheduledTask(
            id=task_id,
            name=name,
            cron_expression=cron_expression,
            handler=handler,
            parameters=parameters or {},
            last_run=None,
            next_run=next_run,
            status="scheduled",
            enabled=enabled
        )
        
        self.scheduled_tasks[task_id] = task
        logger.info(f"定时任务创建: {name} (cron: {cron_expression})")
        
        return {
            "status": "success",
            "task_id": task_id,
            "next_run": next_run
        }
    
    def _calculate_next_run(self, cron_expression: str) -> str:
        """计算下次运行时间"""
        # 简化版cron解析
        now = datetime.now()
        
        try:
            parts = cron_expression.split()
            if len(parts) == 5:
                minute, hour, day, month, weekday = parts
                
                # 简单处理：每分钟/每小时
                if minute == "*":
                    return (now + timedelta(minutes=1)).isoformat()
                elif hour == "*":
                    return (now + timedelta(hours=1)).isoformat()
                else:
                    # 指定时间
                    next_run = now.replace(minute=int(minute), second=0, microsecond=0)
                    if next_run <= now:
                        next_run += timedelta(hours=1)
                    return next_run.isoformat()
        except Exception:
            logger.debug(f"忽略异常: ", exc_info=True)
            pass
        
        # 默认1分钟后
        return (now + timedelta(minutes=1)).isoformat()
    
    async def execute_task(self, task_id: str) -> Dict[str, Any]:
        """执行任务"""
        if task_id not in self.scheduled_tasks:
            return {"status": "error", "error": f"任务不存在: {task_id}"}
        
        task = self.scheduled_tasks[task_id]
        
        if task.handler not in self.task_handlers:
            return {"status": "error", "error": f"处理器不存在: {task.handler}"}
        
        started_at = datetime.now()
        
        try:
            handler = self.task_handlers[task.handler]
            
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**task.parameters)
            else:
                result = handler(**task.parameters)
            
            task.last_run = started_at.isoformat()
            task.next_run = self._calculate_next_run(task.cron_expression)
            task.status = "completed"
            
            task_result = TaskResult(
                task_id=task_id,
                status="success",
                result=result,
                error=None,
                started_at=started_at.isoformat(),
                completed_at=datetime.now().isoformat(),
                duration_ms=int((datetime.now() - started_at).total_seconds() * 1000)
            )
            
            self.task_results.append(task_result)
            
            logger.info(f"任务执行成功: {task.name}")
            return {"status": "success", "result": result}
            
        except Exception as e:
            task.status = "failed"
            
            task_result = TaskResult(
                task_id=task_id,
                status="error",
                result=None,
                error=str(e),
                started_at=started_at.isoformat(),
                completed_at=datetime.now().isoformat(),
                duration_ms=int((datetime.now() - started_at).total_seconds() * 1000)
            )
            
            self.task_results.append(task_result)
            
            logger.error(f"任务执行失败: {task.name} - {e}")
            return {"status": "error", "error": str(e)}
    
    async def _scheduler_loop(self):
        """调度循环"""
        while self._running:
            try:
                now = datetime.now()
                
                for task_id, task in self.scheduled_tasks.items():
                    if not task.enabled:
                        continue
                    
                    if task.next_run:
                        next_run = datetime.fromisoformat(task.next_run)
                        if now >= next_run:
                            logger.info(f"触发定时任务: {task.name}")
                            await self.execute_task(task_id)
                
                await asyncio.sleep(10)  # 每10秒检查一次
                
            except Exception as e:
                logger.error(f"调度循环错误: {e}")
                await asyncio.sleep(5)
    
    async def start(self) -> Dict[str, Any]:
        """启动服务"""
        if self.status == ServiceStatus.RUNNING:
            return {"status": "error", "error": "服务已在运行"}
        
        self.status = ServiceStatus.STARTING
        logger.info(f"启动后台服务: {self.service_name}")
        
        self._running = True
        
        # 启动调度器
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        self.status = ServiceStatus.RUNNING
        logger.info("后台服务已启动")
        
        return {
            "status": "success",
            "service_name": self.service_name,
            "started_at": datetime.now().isoformat()
        }
    
    async def stop(self) -> Dict[str, Any]:
        """停止服务"""
        if self.status != ServiceStatus.RUNNING:
            return {"status": "error", "error": "服务未在运行"}
        
        self.status = ServiceStatus.STOPPING
        logger.info("停止后台服务...")
        
        self._running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        self.status = ServiceStatus.STOPPED
        logger.info("后台服务已停止")
        
        return {
            "status": "success",
            "service_name": self.service_name,
            "stopped_at": datetime.now().isoformat()
        }
    
    async def pause(self) -> Dict[str, Any]:
        """暂停服务"""
        if self.status != ServiceStatus.RUNNING:
            return {"status": "error", "error": "服务未在运行"}
        
        self._running = False
        self.status = ServiceStatus.PAUSED
        logger.info("后台服务已暂停")
        
        return {"status": "success", "message": "服务已暂停"}
    
    async def resume(self) -> Dict[str, Any]:
        """恢复服务"""
        if self.status != ServiceStatus.PAUSED:
            return {"status": "error", "error": "服务未暂停"}
        
        self._running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        self.status = ServiceStatus.RUNNING
        logger.info("后台服务已恢复")
        
        return {"status": "success", "message": "服务已恢复"}
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "status": "success",
            "service": {
                "name": self.service_name,
                "status": self.status.value,
                "running": self._running,
                "scheduled_tasks": len(self.scheduled_tasks),
                "total_executions": len(self.task_results),
                "handlers": list(self.task_handlers.keys())
            }
        }
    
    def get_scheduled_tasks(self) -> Dict[str, Any]:
        """获取定时任务列表"""
        return {
            "status": "success",
            "tasks": [
                {
                    "id": task.id,
                    "name": task.name,
                    "cron": task.cron_expression,
                    "handler": task.handler,
                    "enabled": task.enabled,
                    "last_run": task.last_run,
                    "next_run": task.next_run,
                    "status": task.status
                }
                for task in self.scheduled_tasks.values()
            ],
            "count": len(self.scheduled_tasks)
        }
    
    def get_task_results(self, limit: int = 50) -> Dict[str, Any]:
        """获取任务执行结果"""
        return {
            "status": "success",
            "results": [
                {
                    "task_id": r.task_id,
                    "status": r.status,
                    "error": r.error,
                    "started_at": r.started_at,
                    "completed_at": r.completed_at,
                    "duration_ms": r.duration_ms
                }
                for r in self.task_results[-limit:]
            ],
            "total": len(self.task_results)
        }
    
    def remove_task(self, task_id: str) -> Dict[str, Any]:
        """移除定时任务"""
        if task_id not in self.scheduled_tasks:
            return {"status": "error", "error": f"任务不存在: {task_id}"}
        
        del self.scheduled_tasks[task_id]
        logger.info(f"定时任务已移除: {task_id}")
        
        return {"status": "success", "message": f"任务已移除: {task_id}"}
    
    def enable_task(self, task_id: str) -> Dict[str, Any]:
        """启用任务"""
        if task_id not in self.scheduled_tasks:
            return {"status": "error", "error": f"任务不存在: {task_id}"}
        
        self.scheduled_tasks[task_id].enabled = True
        return {"status": "success", "message": f"任务已启用: {task_id}"}
    
    def disable_task(self, task_id: str) -> Dict[str, Any]:
        """禁用任务"""
        if task_id not in self.scheduled_tasks:
            return {"status": "error", "error": f"任务不存在: {task_id}"}
        
        self.scheduled_tasks[task_id].enabled = False
        return {"status": "success", "message": f"任务已禁用: {task_id}"}


background_service = BackgroundService()
