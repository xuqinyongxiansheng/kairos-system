#!/usr/bin/env python3
"""
监控面板
实现实时监控面板，跟踪系统关键指标
"""

import json
import os
import threading
import time
from typing import Dict, Any, List
from datetime import datetime

from .metrics import get_metrics_registry, Metric


class MonitoringPanel:
    """监控面板"""
    
    def __init__(self, data_dir: str = "data/monitoring"):
        self.data_dir = data_dir
        self.metrics_registry = get_metrics_registry()
        self.history: Dict[str, List[Dict[str, Any]]] = {}
        self.max_history = 1000
        self.running = False
        self.thread = None
        self.anomalies: List[Dict[str, Any]] = []
        self.max_anomalies = 100
        self.thresholds = {
            "system_cpu_usage": 80,  # CPU使用率阈值
            "system_memory_usage": 90,  # 内存使用率阈值
            "system_disk_usage": 90,  # 磁盘使用率阈值
            "model_inference_time": 5000,  # 模型推理时间阈值（毫秒）
            "cache_hit_rate": 50  # 缓存命中率阈值（%）
        }
        os.makedirs(self.data_dir, exist_ok=True)
        self._init_metrics()
    
    def _init_metrics(self):
        """初始化指标"""
        # 系统指标
        self.metrics_registry.register("system_cpu_usage", "gauge", "CPU使用率")
        self.metrics_registry.register("system_memory_usage", "gauge", "内存使用率")
        self.metrics_registry.register("system_disk_usage", "gauge", "磁盘使用率")
        self.metrics_registry.register("system_network_sent", "counter", "网络发送字节数")
        self.metrics_registry.register("system_network_recv", "counter", "网络接收字节数")
        self.metrics_registry.register("system_process_count", "gauge", "进程数量")
        
        # 缓存指标
        self.metrics_registry.register("cache_hit_count", "counter", "缓存命中次数")
        self.metrics_registry.register("cache_miss_count", "counter", "缓存未命中次数")
        self.metrics_registry.register("cache_hit_rate", "gauge", "缓存命中率")
        
        # 任务调度指标
        self.metrics_registry.register("task_queue_size", "gauge", "任务队列大小")
        self.metrics_registry.register("task_execution_time", "gauge", "任务执行时间")
        self.metrics_registry.register("task_success_rate", "gauge", "任务成功率")
        
        # 模型指标
        self.metrics_registry.register("model_inference_time", "gauge", "模型推理时间")
        self.metrics_registry.register("model_requests_total", "counter", "模型请求总数")
        
        # Agent指标
        self.metrics_registry.register("agent_tasks_total", "counter", "Agent任务总数")
        self.metrics_registry.register("agent_tasks_completed", "counter", "Agent完成任务数")
    
    def start(self):
        """启动监控"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._collect_metrics, daemon=True)
        self.thread.start()
        print("监控面板已启动")
    
    def stop(self):
        """停止监控"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("监控面板已停止")
    
    def _collect_metrics(self):
        """收集指标"""
        while self.running:
            # 收集系统指标
            self._collect_system_metrics()
            
            # 收集所有指标
            metrics = self.metrics_registry.list()
            current_metrics = {}
            
            for metric in metrics:
                value = metric.get()
                metric_data = {
                    "value": value,
                    "timestamp": datetime.now().isoformat()
                }
                
                # 存储当前指标值用于异常检测
                current_metrics[metric.name] = value
                
                if metric.name not in self.history:
                    self.history[metric.name] = []
                
                self.history[metric.name].append(metric_data)
                
                # 限制历史数据大小
                if len(self.history[metric.name]) > self.max_history:
                    self.history[metric.name] = self.history[metric.name][-self.max_history:]
            
            # 检测异常
            self._detect_anomalies(current_metrics)
            
            # 保存历史数据
            self._save_history()
            
            # 休眠
            time.sleep(1)
    
    def _detect_anomalies(self, current_metrics: Dict[str, Any]):
        """检测异常"""
        for metric_name, value in current_metrics.items():
            # 检查阈值异常
            if metric_name in self.thresholds:
                threshold = self.thresholds[metric_name]
                if value > threshold:
                    anomaly = {
                        "metric": metric_name,
                        "value": value,
                        "threshold": threshold,
                        "type": "threshold",
                        "timestamp": datetime.now().isoformat(),
                        "message": f"指标 {metric_name} 超过阈值 {threshold}"
                    }
                    self._add_anomaly(anomaly)
            
            # 检查趋势异常（简单实现：与历史平均值比较）
            if metric_name in self.history and len(self.history[metric_name]) >= 10:
                # 计算历史平均值
                history_values = [item["value"] for item in self.history[metric_name][-10:]]
                avg_value = sum(history_values) / len(history_values)
                
                # 如果当前值与平均值相差超过50%，则视为异常
                if avg_value > 0 and abs(value - avg_value) / avg_value > 0.5:
                    anomaly = {
                        "metric": metric_name,
                        "value": value,
                        "average": avg_value,
                        "type": "trend",
                        "timestamp": datetime.now().isoformat(),
                        "message": f"指标 {metric_name} 与历史平均值偏差较大"
                    }
                    self._add_anomaly(anomaly)
    
    def _add_anomaly(self, anomaly: Dict[str, Any]):
        """添加异常"""
        self.anomalies.append(anomaly)
        # 限制异常数量
        if len(self.anomalies) > self.max_anomalies:
            self.anomalies = self.anomalies[-self.max_anomalies:]
        # 打印异常信息
        print(f"异常检测: {anomaly['message']}")
    
    def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            import psutil
            
            # CPU使用率
            cpu_usage = psutil.cpu_percent()
            cpu_metric = self.metrics_registry.get("system_cpu_usage")
            cpu_metric.set(cpu_usage)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            memory_metric = self.metrics_registry.get("system_memory_usage")
            memory_metric.set(memory_usage)
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            disk_metric = self.metrics_registry.get("system_disk_usage")
            disk_metric.set(disk_usage)
            
            # 网络流量
            net_io = psutil.net_io_counters()
            net_sent_metric = self.metrics_registry.get("system_network_sent")
            net_sent_metric.set(net_io.bytes_sent)
            net_recv_metric = self.metrics_registry.get("system_network_recv")
            net_recv_metric.set(net_io.bytes_recv)
            
            # 进程数量
            process_count = len(psutil.pids())
            process_metric = self.metrics_registry.get("system_process_count")
            process_metric.set(process_count)
            
        except Exception:
            pass
    
    def _save_history(self):
        """保存历史数据"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"metrics_{timestamp}.json"
            file_path = os.path.join(self.data_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史数据失败: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取当前指标"""
        metrics = {}
        for metric in self.metrics_registry.list():
            metrics[metric.name] = {
                "value": metric.get(),
                "type": metric.metric_type,
                "description": metric.description
            }
        return metrics
    
    def get_metric_history(self, metric_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取指标历史"""
        if metric_name in self.history:
            return self.history[metric_name][-limit:]
        return []
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表盘数据"""
        return {
            "current_metrics": self.get_metrics(),
            "system_metrics": {
                "cpu": self.get_metric_history("system_cpu_usage", 60),
                "memory": self.get_metric_history("system_memory_usage", 60),
                "disk": self.get_metric_history("system_disk_usage", 60),
                "network": {
                    "sent": self.get_metric_history("system_network_sent", 60),
                    "recv": self.get_metric_history("system_network_recv", 60)
                },
                "processes": self.get_metric_history("system_process_count", 60)
            },
            "cache_metrics": {
                "hit_rate": self.get_metric_history("cache_hit_rate", 60),
                "hits": self.get_metric_history("cache_hit_count", 60),
                "misses": self.get_metric_history("cache_miss_count", 60)
            },
            "task_metrics": {
                "queue_size": self.get_metric_history("task_queue_size", 60),
                "execution_time": self.get_metric_history("task_execution_time", 60),
                "success_rate": self.get_metric_history("task_success_rate", 60)
            },
            "model_metrics": {
                "inference_time": self.get_metric_history("model_inference_time", 60),
                "requests": self.get_metric_history("model_requests_total", 60)
            },
            "agent_metrics": {
                "tasks": self.get_metric_history("agent_tasks_total", 60),
                "completed": self.get_metric_history("agent_tasks_completed", 60)
            },
            "anomalies": self.get_recent_anomalies(10),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_recent_anomalies(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的异常"""
        return self.anomalies[-limit:]
    
    def clear_anomalies(self):
        """清空异常"""
        self.anomalies.clear()
    
    def optimize_monitoring(self):
        """优化监控"""
        # 清理历史数据
        for metric_name in self.history:
            if len(self.history[metric_name]) > self.max_history:
                self.history[metric_name] = self.history[metric_name][-self.max_history:]
        
        # 清理异常数据
        if len(self.anomalies) > self.max_anomalies:
            self.anomalies = self.anomalies[-self.max_anomalies:]
        
        print("监控面板优化完成")
        return True
    
    def clear_history(self):
        """清空历史数据"""
        self.history.clear()


# 全局监控面板实例
_monitoring_panel = None

def get_monitoring_panel() -> MonitoringPanel:
    """获取监控面板实例"""
    global _monitoring_panel
    if _monitoring_panel is None:
        _monitoring_panel = MonitoringPanel()
        _monitoring_panel.start()
    return _monitoring_panel


if __name__ == "__main__":
    # 测试
    panel = get_monitoring_panel()
    
    # 等待收集一些数据
    time.sleep(5)
    
    # 获取仪表盘数据
    dashboard = panel.get_dashboard_data()
    print(f"仪表盘数据: {json.dumps(dashboard, ensure_ascii=False, indent=2)}")
    
    # 获取CPU历史数据
    cpu_history = panel.get_metric_history("system_cpu_usage")
    print(f"CPU历史数据: {cpu_history}")
    
    # 停止监控
    panel.stop()