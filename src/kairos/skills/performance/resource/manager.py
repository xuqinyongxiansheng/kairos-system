#!/usr/bin/env python3
"""
资源管理模块
实现内存使用监控和自动回收
"""

import gc
import logging
import threading
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ResourceManager:
    """资源管理器"""
    
    def __init__(self, memory_threshold: float = 80.0, check_interval: int = 60):
        """
        初始化资源管理器
        
        Args:
            memory_threshold: 内存使用率阈值，超过此值将触发回收 (默认80%)
            check_interval: 检查间隔 (默认60秒)
        """
        self.memory_threshold = memory_threshold
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        self._init_metrics()
    
    def _init_metrics(self):
        """初始化指标"""
        from ..monitoring.metrics import get_metrics_registry
        self.metrics_registry = get_metrics_registry()
        self.metrics_registry.register("resource_memory_usage", "gauge", "内存使用率")
        self.metrics_registry.register("resource_gc_collections", "counter", "垃圾回收次数")
        self.metrics_registry.register("resource_gc_objects_collected", "counter", "垃圾回收对象数")
    
    def start(self):
        """启动资源管理器"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self.thread.start()
        logger.info("资源管理器已启动")
    
    def stop(self):
        """停止资源管理器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("资源管理器已停止")
    
    def _monitor_resources(self):
        """监控资源使用情况"""
        while self.running:
            try:
                # 检查内存使用情况
                memory_usage = self._get_memory_usage()
                
                # 更新指标
                memory_metric = self.metrics_registry.get("resource_memory_usage")
                memory_metric.set(memory_usage)
                
                # 如果内存使用超过阈值，触发回收
                if memory_usage > self.memory_threshold:
                    logger.warning(f"内存使用率过高: {memory_usage:.2f}%，触发回收")
                    self._recycle_resources()
                
            except Exception as e:
                logger.error(f"监控资源失败: {e}")
            
            # 休眠
            time.sleep(self.check_interval)
    
    def _get_memory_usage(self) -> float:
        """获取内存使用率"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return memory.percent
        except Exception:
            return 0.0
    
    def _recycle_resources(self):
        """回收资源"""
        try:
            # 手动触发垃圾回收
            logger.info("开始回收资源...")
            
            # 记录回收前的对象数
            before = len(gc.get_objects())
            
            # 执行垃圾回收
            collected = gc.collect()
            
            # 记录回收后的对象数
            after = len(gc.get_objects())
            
            # 更新指标
            gc_collections_metric = self.metrics_registry.get("resource_gc_collections")
            gc_collections_metric.set(gc_collections_metric.get() + 1)
            
            gc_objects_collected_metric = self.metrics_registry.get("resource_gc_objects_collected")
            gc_objects_collected_metric.set(gc_objects_collected_metric.get() + collected)
            
            logger.info(f"资源回收完成: 回收了 {collected} 个对象, 内存使用情况: {before} -> {after}")
            
        except Exception as e:
            logger.error(f"回收资源失败: {e}")
    
    def get_resource_status(self) -> Dict[str, Any]:
        """获取资源状态"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return {
                "memory_usage": memory.percent,
                "memory_total": memory.total,
                "memory_available": memory.available,
                "cpu_count": psutil.cpu_count(),
                "cpu_usage": psutil.cpu_percent(),
                "gc_objects": len(gc.get_objects()),
                "gc_collections": self.metrics_registry.get("resource_gc_collections").get()
            }
        except Exception as e:
            return {
                "error": str(e)
            }
    
    def optimize_resources(self):
        """优化资源使用"""
        # 执行垃圾回收
        self._recycle_resources()
        
        # 可以添加其他资源优化策略
        
        logger.info("资源优化完成")
        return True


# 全局资源管理器实例
_resource_manager = None

def get_resource_manager() -> ResourceManager:
    """获取资源管理器实例"""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
        _resource_manager.start()
    return _resource_manager


if __name__ == "__main__":
    # 测试
    resource_manager = get_resource_manager()
    
    # 等待一段时间
    time.sleep(5)
    
    # 获取资源状态
    status = resource_manager.get_resource_status()
    print(f"资源状态: {status}")
    
    # 手动触发资源优化
    resource_manager.optimize_resources()
    
    # 获取资源状态
    status = resource_manager.get_resource_status()
    print(f"优化后资源状态: {status}")
    
    # 停止资源管理器
    resource_manager.stop()
    print("资源管理器已停止")