#!/usr/bin/env python3
"""
性能监控模块
负责监控系统性能指标，如CPU使用率、内存使用率、磁盘使用率等
"""

import os
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger("PerformanceMonitor")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not installed. Performance monitoring will be limited.")


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        """初始化性能监控器"""
        self.logger = logging.getLogger(__name__)
        self.history = []
        self.max_history = 100
        
        self.logger.info("性能监控器初始化完成")
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统性能统计信息"""
        try:
            if not PSUTIL_AVAILABLE:
                return self._get_mock_stats()
            
            cpu_percent = psutil.cpu_percent(interval=1)
            
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used / (1024 * 1024 * 1024)
            memory_total = memory.total / (1024 * 1024 * 1024)
            
            try:
                disk = psutil.disk_usage('/')
                disk_percent = disk.percent
                disk_used = disk.used / (1024 * 1024 * 1024)
                disk_total = disk.total / (1024 * 1024 * 1024)
            except Exception:
                disk_percent = 0
                disk_used = 0
                disk_total = 0
            
            net_io = psutil.net_io_counters()
            net_sent = net_io.bytes_sent / (1024 * 1024)
            net_recv = net_io.bytes_recv / (1024 * 1024)
            
            process_count = len(psutil.pids())
            
            stats = {
                "timestamp": datetime.now().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "percent": memory_percent,
                    "used_gb": round(memory_used, 2),
                    "total_gb": round(memory_total, 2)
                },
                "disk": {
                    "percent": disk_percent,
                    "used_gb": round(disk_used, 2),
                    "total_gb": round(disk_total, 2)
                },
                "network": {
                    "sent_mb": round(net_sent, 2),
                    "recv_mb": round(net_recv, 2)
                },
                "process": {
                    "count": process_count
                },
                "resource_usage": {
                    "cpu": cpu_percent,
                    "memory": memory_percent,
                    "disk": disk_percent
                }
            }
            
            self._add_to_history(stats)
            
            return stats
        except Exception as e:
            self.logger.error(f"获取系统性能统计信息失败: {e}")
            return self._get_mock_stats()
    
    def _get_mock_stats(self) -> Dict[str, Any]:
        """获取模拟统计数据"""
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": {"percent": 25.0, "count": 8},
            "memory": {"percent": 50.0, "used_gb": 8.0, "total_gb": 16.0},
            "disk": {"percent": 40.0, "used_gb": 200.0, "total_gb": 500.0},
            "network": {"sent_mb": 100.0, "recv_mb": 500.0},
            "process": {"count": 150},
            "resource_usage": {"cpu": 25.0, "memory": 50.0, "disk": 40.0}
        }
    
    def get_process_stats(self, process_id: int = None) -> Dict[str, Any]:
        """获取进程性能统计信息"""
        try:
            if not PSUTIL_AVAILABLE:
                return {"error": "psutil not available"}
            
            if process_id is None:
                process_id = os.getpid()
            
            process = psutil.Process(process_id)
            
            cpu_percent = process.cpu_percent(interval=1)
            
            memory_info = process.memory_info()
            memory_used = memory_info.rss / (1024 * 1024)
            
            io_counters = process.io_counters()
            read_bytes = io_counters.read_bytes / (1024 * 1024)
            write_bytes = io_counters.write_bytes / (1024 * 1024)
            
            stats = {
                "timestamp": datetime.now().isoformat(),
                "process_id": process_id,
                "name": process.name(),
                "cpu": {"percent": cpu_percent},
                "memory": {"used_mb": round(memory_used, 2)},
                "disk": {"read_mb": round(read_bytes, 2), "write_mb": round(write_bytes, 2)},
                "status": process.status()
            }
            
            return stats
        except Exception as e:
            self.logger.error(f"获取进程性能统计信息失败: {e}")
            return {"timestamp": datetime.now().isoformat(), "error": str(e)}
    
    def get_history(self) -> List[Dict[str, Any]]:
        """获取历史性能数据"""
        return self.history
    
    def get_average_stats(self, minutes: int = 5) -> Dict[str, Any]:
        """获取平均性能统计信息"""
        try:
            cutoff_time = datetime.now().timestamp() - (minutes * 60)
            
            recent_history = [h for h in self.history if datetime.fromisoformat(h['timestamp']).timestamp() >= cutoff_time]
            
            if not recent_history:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "error": "No recent data available"
                }
            
            cpu_sum = sum(h['cpu']['percent'] for h in recent_history)
            memory_sum = sum(h['memory']['percent'] for h in recent_history)
            disk_sum = sum(h['disk']['percent'] for h in recent_history)
            
            count = len(recent_history)
            
            return {
                "timestamp": datetime.now().isoformat(),
                "average": {
                    "cpu_percent": round(cpu_sum / count, 2),
                    "memory_percent": round(memory_sum / count, 2),
                    "disk_percent": round(disk_sum / count, 2)
                },
                "sample_count": count,
                "time_range_minutes": minutes
            }
        except Exception as e:
            self.logger.error(f"获取平均性能统计信息失败: {e}")
            return {"timestamp": datetime.now().isoformat(), "error": str(e)}
    
    def _add_to_history(self, stats: Dict[str, Any]):
        """添加统计信息到历史记录"""
        self.history.append(stats)
        
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def is_overloaded(self, cpu_threshold: float = 80.0, memory_threshold: float = 85.0, disk_threshold: float = 90.0) -> bool:
        """检查系统是否过载"""
        stats = self.get_system_stats()
        
        if "error" in stats:
            return False
        
        resource_usage = stats.get("resource_usage", {})
        
        cpu_usage = resource_usage.get("cpu", 0.0)
        memory_usage = resource_usage.get("memory", 0.0)
        disk_usage = resource_usage.get("disk", 0.0)
        
        return cpu_usage > cpu_threshold or memory_usage > memory_threshold or disk_usage > disk_threshold
    
    def get_status(self) -> Dict[str, Any]:
        """获取监控器状态"""
        return {
            "status": "active",
            "psutil_available": PSUTIL_AVAILABLE,
            "history_count": len(self.history),
            "max_history": self.max_history
        }


_performance_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控器实例"""
    global _performance_monitor
    
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    
    return _performance_monitor
