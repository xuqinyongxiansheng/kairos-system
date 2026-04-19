#!/usr/bin/env python3
"""
任务调度器
实现智能任务调度算法
"""

import asyncio
import logging
import queue
import threading
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class TaskPriority:
    """任务优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class TaskState:
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduledTask:
    """调度任务"""
    
    def __init__(self, task_id: str, function: callable, 
                 args: tuple = (), kwargs: dict = None, 
                 priority: int = TaskPriority.NORMAL, 
                 timeout: Optional[float] = None):
        self.task_id = task_id
        self.function = function
        self.args = args
        self.kwargs = kwargs or {}
        self.priority = priority
        self.timeout = timeout
        self.state = TaskState.PENDING
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.error = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "state": self.state,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error
        }


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, max_workers: int = 4, min_workers: int = 2, max_queue_size: int = 1000):
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.task_queue = queue.PriorityQueue(maxsize=max_queue_size)
        self.active_tasks: Dict[str, ScheduledTask] = {}
        self.completed_tasks: Dict[str, ScheduledTask] = {}
        self.pending_tasks: Dict[str, ScheduledTask] = {}  # 待处理任务（有依赖）
        self.task_dependencies: Dict[str, List[str]] = {}  # 任务依赖关系
        self.running = False
        self.worker_threads = []
        self.lock = threading.Lock()
        self.worker_adjust_interval = 60  # 工作线程调整间隔（秒）
        self.last_worker_adjust = time.time()
        self.queue_size_history = []  # 队列大小历史，用于动态调整工作线程
    
    def start(self):
        """启动调度器"""
        if self.running:
            return
        
        self.running = True
        
        # 启动工作线程（初始为最小线程数）
        for i in range(self.min_workers):
            thread = threading.Thread(target=self._worker, daemon=True)
            thread.start()
            self.worker_threads.append(thread)
        
        logger.info(f"任务调度器已启动，工作线程数: {self.min_workers}")
    
    def stop(self):
        """停止调度器"""
        self.running = False
        
        # 等待工作线程结束
        for thread in self.worker_threads:
            thread.join(timeout=5)
        
        logger.info("任务调度器已停止")
    
    def _worker(self):
        """工作线程"""
        while self.running:
            try:
                # 动态调整工作线程数
                self._adjust_workers()
                
                # 处理有依赖的任务
                self._process_pending_tasks()
                
                # 从队列获取任务
                _, task = self.task_queue.get(block=True, timeout=1)
                
                if not self.running:
                    break
                
                # 执行任务
                self._execute_task(task)
                
                # 标记任务完成
                self.task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"工作线程错误: {e}")
    
    def _adjust_workers(self):
        """动态调整工作线程数"""
        current_time = time.time()
        
        # 检查是否需要调整
        if current_time - self.last_worker_adjust < self.worker_adjust_interval:
            return
        
        # 更新调整时间
        self.last_worker_adjust = current_time
        
        # 记录当前队列大小
        queue_size = self.task_queue.qsize()
        self.queue_size_history.append(queue_size)
        
        # 只保留最近10次记录
        if len(self.queue_size_history) > 10:
            self.queue_size_history = self.queue_size_history[-10:]
        
        # 计算平均队列大小
        if len(self.queue_size_history) > 0:
            avg_queue_size = sum(self.queue_size_history) / len(self.queue_size_history)
            
            # 当前工作线程数
            current_workers = len(self.worker_threads)
            
            # 基于队列大小调整线程数
            if avg_queue_size > 10 and current_workers < self.max_workers:
                # 队列积压，增加线程
                new_workers = min(current_workers + 2, self.max_workers)
                for i in range(current_workers, new_workers):
                    thread = threading.Thread(target=self._worker, daemon=True)
                    thread.start()
                    self.worker_threads.append(thread)
                logger.info(f"增加工作线程数: {current_workers} -> {new_workers}")
            elif avg_queue_size < 5 and current_workers > self.min_workers:
                # 队列空闲，减少线程
                new_workers = max(current_workers - 1, self.min_workers)
                # 这里简化处理，实际应用中可能需要更复杂的线程管理
                logger.info(f"减少工作线程数: {current_workers} -> {new_workers}")
    
    def _process_pending_tasks(self):
        """处理有依赖的任务"""
        with self.lock:
            # 找出所有依赖已完成的任务
            ready_tasks = []
            for task_id, task in self.pending_tasks.items():
                dependencies = self.task_dependencies.get(task_id, [])
                # 检查所有依赖是否都已完成
                all_completed = all(dep_id in self.completed_tasks for dep_id in dependencies)
                if all_completed:
                    ready_tasks.append(task_id)
            
            # 将就绪的任务加入队列
            for task_id in ready_tasks:
                task = self.pending_tasks.pop(task_id)
                # 放入队列
                self.task_queue.put((-task.priority, task))
                logger.info(f"任务依赖已满足，加入队列: {task_id}")
                # 清理依赖关系
                if task_id in self.task_dependencies:
                    del self.task_dependencies[task_id]
    
    def _execute_task(self, task: ScheduledTask):
        """执行任务"""
        task.state = TaskState.RUNNING
        task.started_at = datetime.now()
        
        with self.lock:
            self.active_tasks[task.task_id] = task
        
        try:
            # 执行任务
            if asyncio.iscoroutinefunction(task.function):
                # 异步函数
                loop = asyncio.new_event_loop()
                task.result = loop.run_until_complete(task.function(*task.args, **task.kwargs))
                loop.close()
            else:
                # 同步函数
                task.result = task.function(*task.args, **task.kwargs)
            
            task.state = TaskState.COMPLETED
            task.completed_at = datetime.now()
            logger.info(f"任务执行完成: {task.task_id}")
        except Exception as e:
            task.state = TaskState.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            logger.error(f"任务执行失败: {task.task_id}, 错误: {e}")
        finally:
            with self.lock:
                if task.task_id in self.active_tasks:
                    del self.active_tasks[task.task_id]
                self.completed_tasks[task.task_id] = task
    
    def schedule_task(self, function: callable, args: tuple = (), 
                     kwargs: dict = None, priority: int = TaskPriority.NORMAL, 
                     timeout: Optional[float] = None, dependencies: List[str] = None) -> str:
        """调度任务"""
        task_id = f"task_{int(time.time() * 1000)}"
        task = ScheduledTask(
            task_id=task_id,
            function=function,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout
        )
        
        # 处理依赖关系
        if dependencies:
            # 检查依赖是否存在
            valid_dependencies = []
            for dep_id in dependencies:
                if dep_id in self.completed_tasks or dep_id in self.active_tasks or dep_id in self.pending_tasks:
                    valid_dependencies.append(dep_id)
                else:
                    logger.warning(f"依赖任务不存在: {dep_id}")
            
            if valid_dependencies:
                # 有依赖，放入待处理队列
                with self.lock:
                    self.pending_tasks[task_id] = task
                    self.task_dependencies[task_id] = valid_dependencies
                logger.info(f"任务已调度（有依赖）: {task_id}, 依赖: {valid_dependencies}")
                return task_id
        
        # 无依赖，直接放入队列
        # 使用负优先级，因为PriorityQueue是最小堆
        self.task_queue.put((-priority, task))
        logger.info(f"任务已调度: {task_id}, 优先级: {priority}")
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        with self.lock:
            if task_id in self.active_tasks:
                return self.active_tasks[task_id].to_dict()
            elif task_id in self.completed_tasks:
                return self.completed_tasks[task_id].to_dict()
            elif task_id in self.pending_tasks:
                task_dict = self.pending_tasks[task_id].to_dict()
                task_dict["dependencies"] = self.task_dependencies.get(task_id, [])
                return task_dict
        return None
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        return self.task_queue.qsize()
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """获取活跃任务"""
        with self.lock:
            return [task.to_dict() for task in self.active_tasks.values()]
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """获取待处理任务"""
        with self.lock:
            pending = []
            for task_id, task in self.pending_tasks.items():
                task_dict = task.to_dict()
                task_dict["dependencies"] = self.task_dependencies.get(task_id, [])
                pending.append(task_dict)
            return pending
    
    def get_completed_tasks(self) -> List[Dict[str, Any]]:
        """获取已完成任务"""
        with self.lock:
            return [task.to_dict() for task in self.completed_tasks.values()]
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self.lock:
            # 取消待处理任务
            if task_id in self.pending_tasks:
                del self.pending_tasks[task_id]
                if task_id in self.task_dependencies:
                    del self.task_dependencies[task_id]
                logger.info(f"任务已取消: {task_id}")
                return True
            # 注意：正在执行的任务无法取消
        return False
    
    def cleanup_completed(self, max_keep: int = 1000):
        """清理已完成的任务"""
        with self.lock:
            if len(self.completed_tasks) > max_keep:
                # 按完成时间排序，保留最新的
                sorted_tasks = sorted(
                    self.completed_tasks.values(),
                    key=lambda x: x.completed_at or x.created_at,
                    reverse=True
                )
                
                # 删除旧任务
                for task in sorted_tasks[max_keep:]:
                    del self.completed_tasks[task.task_id]
                
                logger.info(f"清理了 {len(sorted_tasks) - max_keep} 个已完成任务")
    
    def optimize_scheduler(self):
        """优化调度器"""
        # 清理过期任务
        self.cleanup_completed()
        
        # 动态调整工作线程数
        self._adjust_workers()
        
        logger.info("调度器优化完成")
        return True


# 全局任务调度器实例
_task_scheduler = None

def get_task_scheduler() -> TaskScheduler:
    """获取任务调度器实例"""
    global _task_scheduler
    if _task_scheduler is None:
        _task_scheduler = TaskScheduler()
        _task_scheduler.start()
    return _task_scheduler


if __name__ == "__main__":
    # 测试
    import time
    
    def test_function(name, delay):
        print(f"开始执行任务: {name}")
        time.sleep(delay)
        print(f"完成任务: {name}")
        return f"结果: {name}"
    
    async def test_async_function(name, delay):
        print(f"开始执行异步任务: {name}")
        await asyncio.sleep(delay)
        print(f"完成异步任务: {name}")
        return f"异步结果: {name}"
    
    scheduler = get_task_scheduler()
    
    # 调度任务
    task1 = scheduler.schedule_task(test_function, args=("任务1", 2), priority=TaskPriority.LOW)
    task2 = scheduler.schedule_task(test_function, args=("任务2", 1), priority=TaskPriority.HIGH)
    task3 = scheduler.schedule_task(test_async_function, args=("异步任务1", 1.5), priority=TaskPriority.NORMAL)
    
    print(f"调度的任务: {task1}, {task2}, {task3}")
    
    # 等待任务完成
    time.sleep(5)
    
    # 获取任务状态
    print(f"任务1状态: {scheduler.get_task_status(task1)}")
    print(f"任务2状态: {scheduler.get_task_status(task2)}")
    print(f"任务3状态: {scheduler.get_task_status(task3)}")
    
    # 获取队列大小
    print(f"队列大小: {scheduler.get_queue_size()}")
    
    # 清理任务
    scheduler.cleanup_completed()
    
    # 停止调度器
    scheduler.stop()