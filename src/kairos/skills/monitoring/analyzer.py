#!/usr/bin/env python3
"""
性能分析工具
开发性能分析工具，生成详细性能报告
"""

import json
import os
import time
import cProfile
import pstats
from typing import Dict, Any, List
from datetime import datetime


class PerformanceAnalyzer:
    """性能分析器"""
    
    def __init__(self, output_dir: str = "data/performance"):
        self.output_dir = output_dir
        self.profiles: Dict[str, Dict[str, Any]] = {}
        os.makedirs(self.output_dir, exist_ok=True)
    
    def profile_function(self, func: callable, name: str = None, *args, **kwargs) -> Dict[str, Any]:
        """分析函数性能"""
        if name is None:
            name = func.__name__
        
        # 开始时间
        start_time = time.time()
        
        # 使用cProfile分析
        profile = cProfile.Profile()
        profile.enable()
        
        # 执行函数
        result = func(*args, **kwargs)
        
        # 停止分析
        profile.disable()
        
        # 结束时间
        end_time = time.time()
        duration = end_time - start_time
        
        # 生成统计信息
        stats = pstats.Stats(profile)
        stats.sort_stats('cumulative')
        
        # 提取统计信息
        stats_data = []
        for func_info in stats.stats.items():
            func_name = func_info[0][2]
            filename = func_info[0][0]
            line_no = func_info[0][1]
            cc, nn, tt, ct, callers = func_info[1]
            
            stats_data.append({
                "function": func_name,
                "filename": filename,
                "line": line_no,
                "calls": cc,
                "time_per_call": tt / cc if cc > 0 else 0,
                "cumulative_time": ct
            })
        
        # 生成报告
        report = {
            "name": name,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            "statistics": stats_data[:20],  # 只取前20个
            "result": str(result)
        }
        
        # 保存报告
        self.profiles[name] = report
        self._save_report(name, report)
        
        return report
    
    def _save_report(self, name: str, report: Dict[str, Any]):
        """保存报告"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"profile_{name}_{timestamp}.json"
            file_path = os.path.join(self.output_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存性能报告失败: {e}")
    
    def get_report(self, name: str) -> Dict[str, Any]:
        """获取报告"""
        return self.profiles.get(name, {})
    
    def list_reports(self) -> List[str]:
        """列出报告"""
        return list(self.profiles.keys())
    
    def generate_summary(self) -> Dict[str, Any]:
        """生成性能摘要"""
        if not self.profiles:
            return {}
        
        summaries = []
        for name, report in self.profiles.items():
            summaries.append({
                "name": name,
                "duration": report["duration"],
                "timestamp": report["timestamp"]
            })
        
        # 按执行时间排序
        summaries.sort(key=lambda x: x["duration"], reverse=True)
        
        return {
            "total_profiles": len(self.profiles),
            "summaries": summaries,
            "timestamp": datetime.now().isoformat()
        }


class AnomalyDetector:
    """异常检测器"""
    
    def __init__(self):
        self.thresholds = {
            "system_cpu_usage": 90.0,  # CPU使用率阈值
            "system_memory_usage": 95.0,  # 内存使用率阈值
            "system_disk_usage": 90.0,  # 磁盘使用率阈值
            "model_inference_time": 5.0,  # 模型推理时间阈值（秒）
            "queue_size": 100  # 队列大小阈值
        }
        self.anomalies: List[Dict[str, Any]] = []
    
    def set_threshold(self, metric_name: str, threshold: float):
        """设置阈值"""
        self.thresholds[metric_name] = threshold
    
    def detect(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检测异常"""
        current_anomalies = []
        
        for metric_name, metric_data in metrics.items():
            if metric_name in self.thresholds:
                threshold = self.thresholds[metric_name]
                value = metric_data.get("value", 0)
                
                if value > threshold:
                    anomaly = {
                        "metric": metric_name,
                        "value": value,
                        "threshold": threshold,
                        "timestamp": datetime.now().isoformat(),
                        "message": f"{metric_name} 超过阈值: {value} > {threshold}"
                    }
                    current_anomalies.append(anomaly)
                    self.anomalies.append(anomaly)
        
        return current_anomalies
    
    def get_anomalies(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取异常"""
        return self.anomalies[-limit:]
    
    def clear_anomalies(self):
        """清空异常"""
        self.anomalies.clear()


class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.anomaly_detector = AnomalyDetector()
        self.alerts: List[Dict[str, Any]] = []
    
    def check_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查告警"""
        anomalies = self.anomaly_detector.detect(metrics)
        
        for anomaly in anomalies:
            alert = {
                "id": f"alert_{int(time.time() * 1000)}",
                "level": "warning" if anomaly["value"] < anomaly["threshold"] * 1.5 else "critical",
                "message": anomaly["message"],
                "timestamp": anomaly["timestamp"],
                "metric": anomaly["metric"],
                "value": anomaly["value"],
                "threshold": anomaly["threshold"]
            }
            self.alerts.append(alert)
        
        return anomalies
    
    def get_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取告警"""
        return self.alerts[-limit:]
    
    def clear_alerts(self):
        """清空告警"""
        self.alerts.clear()
    
    def set_threshold(self, metric_name: str, threshold: float):
        """设置阈值"""
        self.anomaly_detector.set_threshold(metric_name, threshold)


# 全局性能分析器实例
_performance_analyzer = None

def get_performance_analyzer() -> PerformanceAnalyzer:
    """获取性能分析器实例"""
    global _performance_analyzer
    if _performance_analyzer is None:
        _performance_analyzer = PerformanceAnalyzer()
    return _performance_analyzer


# 全局告警管理器实例
_alert_manager = None

def get_alert_manager() -> AlertManager:
    """获取告警管理器实例"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


if __name__ == "__main__":
    # 测试性能分析器
    def test_function():
        time.sleep(0.1)
        for i in range(100000):
            pass
    
    analyzer = get_performance_analyzer()
    report = analyzer.profile_function(test_function, "test_function")
    print(f"性能报告: {json.dumps(report, ensure_ascii=False, indent=2)}")
    
    # 测试告警管理器
    alert_manager = get_alert_manager()
    metrics = {
        "system_cpu_usage": 95.0,
        "system_memory_usage": 80.0,
        "model_inference_time": 6.0
    }
    alerts = alert_manager.check_alerts(metrics)
    print(f"检测到的告警: {alerts}")