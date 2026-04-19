#!/usr/bin/env python3
"""
系统指标
定义系统关键指标
"""

from typing import Dict, Any, List
from datetime import datetime


class MetricType:
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class Metric:
    """指标"""
    
    def __init__(self, name: str, metric_type: str, 
                 description: str = "", labels: Dict[str, str] = None):
        self.name = name
        self.metric_type = metric_type
        self.description = description
        self.labels = labels or {}
        self.value = 0
        self.timestamp = datetime.now()
        self.samples = []
    
    def set(self, value: float):
        """设置指标值"""
        self.value = value
        self.timestamp = datetime.now()
        if self.metric_type == MetricType.HISTOGRAM:
            self.samples.append(value)
    
    def increment(self, value: float = 1.0):
        """增加指标值"""
        if self.metric_type == MetricType.COUNTER:
            self.value += value
            self.timestamp = datetime.now()
    
    def get(self) -> float:
        """获取指标值"""
        return self.value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "type": self.metric_type,
            "description": self.description,
            "labels": self.labels,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "samples": self.samples if self.metric_type == MetricType.HISTOGRAM else None
        }


class MetricsRegistry:
    """指标注册表"""
    
    def __init__(self):
        self.metrics: Dict[str, Metric] = {}
    
    def register(self, metric: Metric):
        """注册指标"""
        key = f"{metric.name}_{'_'.join(f'{k}={v}' for k, v in metric.labels.items())}"
        self.metrics[key] = metric
    
    def get(self, name: str, labels: Dict[str, str] = None) -> Metric:
        """获取指标"""
        labels = labels or {}
        key = f"{name}_{'_'.join(f'{k}={v}' for k, v in labels.items())}"
        if key not in self.metrics:
            # 创建默认指标
            metric = Metric(name, MetricType.GAUGE, labels=labels)
            self.register(metric)
        return self.metrics[key]
    
    def list(self) -> List[Metric]:
        """列出所有指标"""
        return list(self.metrics.values())
    
    def clear(self):
        """清空指标"""
        self.metrics.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            metric.name: metric.to_dict()
            for metric in self.metrics.values()
        }


# 预定义指标
def get_default_metrics() -> List[Metric]:
    """获取默认指标"""
    return [
        # 系统指标
        Metric("system_cpu_usage", MetricType.GAUGE, "CPU使用率"),
        Metric("system_memory_usage", MetricType.GAUGE, "内存使用率"),
        Metric("system_disk_usage", MetricType.GAUGE, "磁盘使用率"),
        
        # 模型指标
        Metric("model_inference_time", MetricType.HISTOGRAM, "模型推理时间"),
        Metric("model_requests_total", MetricType.COUNTER, "模型请求总数"),
        Metric("model_requests_failed", MetricType.COUNTER, "模型失败请求数"),
        
        # Agent指标
        Metric("agent_tasks_total", MetricType.COUNTER, "Agent任务总数"),
        Metric("agent_tasks_completed", MetricType.COUNTER, "Agent完成任务数"),
        Metric("agent_tasks_failed", MetricType.COUNTER, "Agent失败任务数"),
        
        # 缓存指标
        Metric("cache_hits_total", MetricType.COUNTER, "缓存命中数"),
        Metric("cache_misses_total", MetricType.COUNTER, "缓存未命中数"),
        Metric("cache_size", MetricType.GAUGE, "缓存大小"),
        
        # 任务调度指标
        Metric("tasks_scheduled_total", MetricType.COUNTER, "调度任务总数"),
        Metric("tasks_completed_total", MetricType.COUNTER, "完成任务总数"),
        Metric("tasks_failed_total", MetricType.COUNTER, "失败任务总数"),
        Metric("queue_size", MetricType.GAUGE, "队列大小"),
        
        # 系统指标
        Metric("system_uptime", MetricType.GAUGE, "系统运行时间"),
        Metric("system_requests_total", MetricType.COUNTER, "系统请求总数"),
        Metric("system_errors_total", MetricType.COUNTER, "系统错误总数")
    ]


# 全局指标注册表实例
_metrics_registry = None

def get_metrics_registry() -> MetricsRegistry:
    """获取指标注册表实例"""
    global _metrics_registry
    if _metrics_registry is None:
        _metrics_registry = MetricsRegistry()
        # 注册默认指标
        for metric in get_default_metrics():
            _metrics_registry.register(metric)
    return _metrics_registry


if __name__ == "__main__":
    # 测试
    registry = get_metrics_registry()
    
    # 获取指标
    cpu_metric = registry.get("system_cpu_usage")
    memory_metric = registry.get("system_memory_usage")
    
    # 设置指标值
    cpu_metric.set(45.5)
    memory_metric.set(60.2)
    
    # 增加计数器
    requests_metric = registry.get("model_requests_total")
    requests_metric.increment()
    requests_metric.increment()
    
    # 列出所有指标
    metrics = registry.list()
    for metric in metrics:
        print(f"{metric.name}: {metric.get()}")