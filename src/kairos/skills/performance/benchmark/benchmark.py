#!/usr/bin/env python3
"""
性能基准测试
实现性能基准测试和持续优化机制
"""

import time
import json
import os
import statistics
from typing import Dict, Any, List, Callable
from datetime import datetime


class BenchmarkResult:
    """基准测试结果"""
    
    def __init__(self, test_name: str, duration: float, success: bool = True, error: str = None):
        self.test_name = test_name
        self.duration = duration
        self.success = success
        self.error = error
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "test_name": self.test_name,
            "duration": self.duration,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp.isoformat()
        }


class BenchmarkSuite:
    """基准测试套件"""
    
    def __init__(self, suite_name: str, storage_path: str = "data/benchmarks"):
        self.suite_name = suite_name
        self.storage_path = storage_path
        self.tests: List[Dict[str, Any]] = []
        self.results: List[BenchmarkResult] = []
        os.makedirs(self.storage_path, exist_ok=True)
    
    def add_test(self, name: str, test_function: Callable, iterations: int = 1):
        """添加测试"""
        self.tests.append({
            "name": name,
            "function": test_function,
            "iterations": iterations
        })
    
    def run(self) -> List[BenchmarkResult]:
        """运行测试"""
        results = []
        
        for test in self.tests:
            test_name = test["name"]
            test_function = test["function"]
            iterations = test["iterations"]
            
            durations = []
            success = True
            error = None
            
            for i in range(iterations):
                start_time = time.time()
                try:
                    test_function()
                    duration = time.time() - start_time
                    durations.append(duration)
                except Exception as e:
                    success = False
                    error = str(e)
                    break
            
            if durations:
                # 计算平均时间
                avg_duration = statistics.mean(durations)
                result = BenchmarkResult(
                    test_name=test_name,
                    duration=avg_duration,
                    success=success,
                    error=error
                )
            else:
                result = BenchmarkResult(
                    test_name=test_name,
                    duration=0,
                    success=success,
                    error=error
                )
            
            results.append(result)
            self.results.append(result)
            
            print(f"测试 {test_name}: {avg_duration:.4f}s {'✓' if success else '✗'}")
        
        # 保存结果
        self._save_results(results)
        return results
    
    def _save_results(self, results: List[BenchmarkResult]):
        """保存结果"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.suite_name}_{timestamp}.json"
            file_path = os.path.join(self.storage_path, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(
                    [result.to_dict() for result in results],
                    f,
                    ensure_ascii=False,
                    indent=2
                )
        except Exception as e:
            print(f"保存测试结果失败: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """获取测试摘要"""
        if not self.results:
            return {}
        
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        
        if successful:
            avg_duration = statistics.mean([r.duration for r in successful])
            min_duration = min([r.duration for r in successful])
            max_duration = max([r.duration for r in successful])
        else:
            avg_duration = 0
            min_duration = 0
            max_duration = 0
        
        return {
            "suite_name": self.suite_name,
            "total_tests": len(self.results),
            "successful_tests": len(successful),
            "failed_tests": len(failed),
            "average_duration": avg_duration,
            "min_duration": min_duration,
            "max_duration": max_duration
        }
    
    def compare_with(self, other_results: List[BenchmarkResult]) -> Dict[str, Any]:
        """与其他结果比较"""
        comparison = {}
        
        # 构建结果映射
        current_results = {r.test_name: r for r in self.results}
        other_results_map = {r.test_name: r for r in other_results}
        
        for test_name, current_result in current_results.items():
            if test_name in other_results_map:
                other_result = other_results_map[test_name]
                if current_result.success and other_result.success:
                    improvement = (other_result.duration - current_result.duration) / other_result.duration * 100
                    comparison[test_name] = {
                        "current_duration": current_result.duration,
                        "previous_duration": other_result.duration,
                        "improvement": improvement,
                        "status": "improved" if improvement > 0 else "regressed" if improvement < 0 else "same"
                    }
        
        return comparison


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.start_times: Dict[str, float] = {}
    
    def start_timer(self, metric_name: str):
        """开始计时"""
        self.start_times[metric_name] = time.time()
    
    def stop_timer(self, metric_name: str):
        """停止计时"""
        if metric_name in self.start_times:
            duration = time.time() - self.start_times[metric_name]
            if metric_name not in self.metrics:
                self.metrics[metric_name] = []
            self.metrics[metric_name].append(duration)
            del self.start_times[metric_name]
            return duration
        return 0
    
    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """获取指标"""
        result = {}
        for metric_name, values in self.metrics.items():
            if values:
                result[metric_name] = {
                    "count": len(values),
                    "average": statistics.mean(values),
                    "min": min(values),
                    "max": max(values),
                    "stddev": statistics.stdev(values) if len(values) > 1 else 0
                }
        return result
    
    def clear(self):
        """清空指标"""
        self.metrics.clear()
        self.start_times.clear()


# 全局性能监控器实例
_performance_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控器实例"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


# 装饰器用于性能监控
def monitor_performance(metric_name: str):
    """性能监控装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            monitor.start_timer(metric_name)
            try:
                return func(*args, **kwargs)
            finally:
                monitor.stop_timer(metric_name)
        return wrapper
    return decorator


if __name__ == "__main__":
    # 测试
    import time
    
    # 测试函数
    def test_function1():
        time.sleep(0.1)
    
    def test_function2():
        time.sleep(0.2)
    
    # 创建测试套件
    suite = BenchmarkSuite("test_suite")
    suite.add_test("test1", test_function1, iterations=5)
    suite.add_test("test2", test_function2, iterations=3)
    
    # 运行测试
    results = suite.run()
    
    # 获取摘要
    summary = suite.get_summary()
    print(f"测试摘要: {summary}")
    
    # 测试性能监控器
    monitor = get_performance_monitor()
    
    # 使用装饰器
    @monitor_performance("test_decorator")
    def decorated_function():
        time.sleep(0.1)
    
    # 调用函数
    for i in range(3):
        decorated_function()
    
    # 获取指标
    metrics = monitor.get_metrics()
    print(f"性能指标: {metrics}")