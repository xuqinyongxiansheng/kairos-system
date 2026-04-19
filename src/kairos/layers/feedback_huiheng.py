#!/usr/bin/env python3
"""
反馈调控层 - 回衡
负责收集反馈并调整系统，优化系统性能和行为
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ModelPreloader:
    """模型预加载器"""
    
    def __init__(self):
        self.preloaded_models = {}
        self.preload_queue = []
        self.is_preloading = False
    
    async def preload_model(self, model_name: str) -> Dict[str, Any]:
        """预加载模型"""
        if model_name in self.preloaded_models:
            return {"success": True, "message": f"Model {model_name} already preloaded"}
        
        self.preload_queue.append(model_name)
        
        if not self.is_preloading:
            await self._process_preload_queue()
        
        return {"success": True, "message": f"Model {model_name} queued for preloading"}
    
    async def _process_preload_queue(self):
        """处理预加载队列"""
        self.is_preloading = True
        
        while self.preload_queue:
            model_name = self.preload_queue.pop(0)
            
            try:
                await asyncio.sleep(2)
                self.preloaded_models[model_name] = {
                    "loaded_at": datetime.now().isoformat(),
                    "status": "ready"
                }
                logger.info(f"Model {model_name} preloaded successfully")
            except Exception as e:
                logger.error(f"Failed to preload model {model_name}: {e}")
        
        self.is_preloading = False
    
    def get_preloaded_models(self) -> Dict[str, Any]:
        """获取已预加载的模型"""
        return self.preloaded_models
    
    def remove_model(self, model_name: str) -> bool:
        """移除预加载的模型"""
        if model_name in self.preloaded_models:
            del self.preloaded_models[model_name]
            return True
        return False


class FeedbackMemory:
    """反馈记忆系统"""
    
    def __init__(self):
        self.feedback_history = []
        self.performance_metrics = []
    
    def add_feedback(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """添加反馈"""
        feedback_entry = {
            "feedback": feedback,
            "timestamp": datetime.now().isoformat(),
            "type": feedback.get("type", "general")
        }
        self.feedback_history.append(feedback_entry)
        return feedback_entry
    
    def add_performance_metric(self, metric: Dict[str, Any]) -> Dict[str, Any]:
        """添加性能指标"""
        metric_entry = {
            "metric": metric,
            "timestamp": datetime.now().isoformat()
        }
        self.performance_metrics.append(metric_entry)
        return metric_entry
    
    def get_feedback_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取反馈历史"""
        return self.feedback_history[-limit:]
    
    def get_performance_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取性能指标"""
        return self.performance_metrics[-limit:]
    
    def analyze_feedback(self) -> Dict[str, Any]:
        """分析反馈"""
        if not self.feedback_history:
            return {"total": 0, "types": {}}
        
        feedback_types = {}
        for feedback in self.feedback_history:
            feedback_type = feedback.get("type", "general")
            feedback_types[feedback_type] = feedback_types.get(feedback_type, 0) + 1
        
        return {
            "total": len(self.feedback_history),
            "types": feedback_types,
            "latest": self.feedback_history[-1] if self.feedback_history else None
        }


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = []
        self.monitoring_interval = 10
    
    async def start_monitoring(self):
        """开始监控"""
        while True:
            metrics = self._collect_metrics()
            self.metrics.append(metrics)
            await asyncio.sleep(self.monitoring_interval)
    
    def _collect_metrics(self) -> Dict[str, Any]:
        """收集性能指标"""
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                },
                "process": {
                    "cpu_percent": psutil.Process().cpu_percent(),
                    "memory_percent": psutil.Process().memory_percent()
                }
            }
        except Exception as e:
            logger.error(f"性能指标收集失败：{e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": 0,
                "memory": {"percent": 0},
                "disk": {"percent": 0},
                "process": {"cpu_percent": 0, "memory_percent": 0}
            }
    
    def get_latest_metrics(self) -> Dict[str, Any]:
        """获取最新指标"""
        return self.metrics[-1] if self.metrics else None
    
    def get_metrics_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取指标历史"""
        return self.metrics[-limit:]
    
    def analyze_performance(self) -> Dict[str, Any]:
        """分析性能"""
        if len(self.metrics) < 2:
            return {"status": "insufficient_data"}
        
        latest = self.metrics[-1]
        previous = self.metrics[-2]
        
        cpu_change = latest["cpu_percent"] - previous["cpu_percent"]
        memory_change = latest["memory"]["percent"] - previous["memory"]["percent"]
        
        status = "normal"
        if latest["cpu_percent"] > 80:
            status = "high_cpu"
        elif latest["memory"]["percent"] > 85:
            status = "high_memory"
        
        return {
            "status": status,
            "cpu_change": cpu_change,
            "memory_change": memory_change,
            "current": latest
        }


class FeedbackLayer_HuiHeng:
    """
    反馈调控层 - 回衡
    角色：反馈收集者和系统调控者
    工作流程：接收执行结果 → 收集反馈 → 性能监控 → 系统调整 → 回流优化
    """
    
    def __init__(self):
        self.name = "回衡"
        self.role = "反馈调控层"
        self.model_preloader = ModelPreloader()
        self.feedback_memory = FeedbackMemory()
        self.performance_monitor = PerformanceMonitor()
        self.optimization_history = []
        self.monitoring_task = None
    
    async def start_monitoring(self) -> Dict[str, Any]:
        """启动监控"""
        if self.monitoring_task is None:
            self.monitoring_task = asyncio.create_task(
                self.performance_monitor.start_monitoring()
            )
            return {"success": True, "message": "Monitoring started"}
        return {"success": False, "message": "Monitoring already running"}
    
    async def stop_monitoring(self) -> Dict[str, Any]:
        """停止监控"""
        if self.monitoring_task is not None:
            self.monitoring_task.cancel()
            self.monitoring_task = None
            return {"success": True, "message": "Monitoring stopped"}
        return {"success": False, "message": "Monitoring not running"}
    
    async def process_execution_result(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """处理执行结果"""
        feedback = self._collect_feedback(execution_result)
        self.feedback_memory.add_feedback(feedback)
        
        performance_metric = self._collect_performance_metric()
        self.feedback_memory.add_performance_metric(performance_metric)
        
        analysis = self._analyze_feedback_and_performance()
        optimization = self._generate_optimization(analysis)
        
        self._record_optimization(optimization)
        
        logger.info(f"回衡处理反馈：{len(optimization)} 个优化建议")
        
        return {
            "status": "success",
            "type": "feedback",
            "feedback": feedback,
            "performance": performance_metric,
            "analysis": analysis,
            "optimization": optimization,
            "processed_by": self.name,
            "timestamp": datetime.now().isoformat()
        }
    
    def _collect_feedback(self, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """收集反馈"""
        decisions = execution_result.get("decisions", [])
        execution_results = execution_result.get("execution_results", [])
        
        success_count = sum(
            1 for r in execution_results
            if r["result"].get("status") == "completed"
        )
        total_count = len(execution_results) if execution_results else 0
        
        return {
            "type": "execution_feedback",
            "success_rate": success_count / total_count if total_count > 0 else 0,
            "decision_count": len(decisions),
            "execution_count": total_count,
            "success_count": success_count,
            "failed_count": total_count - success_count
        }
    
    def _collect_performance_metric(self) -> Dict[str, Any]:
        """收集性能指标"""
        latest_metrics = self.performance_monitor.get_latest_metrics()
        
        if latest_metrics:
            return {
                "type": "performance",
                "cpu_percent": latest_metrics["cpu_percent"],
                "memory_percent": latest_metrics["memory"]["percent"],
                "disk_percent": latest_metrics["disk"]["percent"]
            }
        else:
            return {
                "type": "performance",
                "cpu_percent": 0,
                "memory_percent": 0,
                "disk_percent": 0
            }
    
    def _analyze_feedback_and_performance(self) -> Dict[str, Any]:
        """分析反馈和性能"""
        feedback_analysis = self.feedback_memory.analyze_feedback()
        performance_analysis = self.performance_monitor.analyze_performance()
        
        issues = []
        
        if feedback_analysis.get("total", 0) > 0:
            success_rate = sum(
                1 for f in self.feedback_memory.get_feedback_history()
                if f["feedback"].get("success_rate", 0) < 0.8
            ) / feedback_analysis["total"]
            
            if success_rate > 0.3:
                issues.append("Low execution success rate")
        
        if performance_analysis["status"] == "high_cpu":
            issues.append("High CPU usage")
        elif performance_analysis["status"] == "high_memory":
            issues.append("High memory usage")
        
        return {
            "feedback_analysis": feedback_analysis,
            "performance_analysis": performance_analysis,
            "issues": issues,
            "overall_health": "good" if not issues else "needs_attention"
        }
    
    def _generate_optimization(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成优化建议"""
        optimizations = []
        issues = analysis.get("issues", [])
        
        for issue in issues:
            if issue == "Low execution success rate":
                optimizations.append({
                    "type": "optimization",
                    "target": "execution",
                    "action": "Review decision making process",
                    "priority": "high"
                })
            elif issue == "High CPU usage":
                optimizations.append({
                    "type": "optimization",
                    "target": "performance",
                    "action": "Reduce model complexity or optimize code",
                    "priority": "medium"
                })
            elif issue == "High memory usage":
                optimizations.append({
                    "type": "optimization",
                    "target": "memory",
                    "action": "Release unused models or optimize memory usage",
                    "priority": "medium"
                })
        
        optimizations.append({
            "type": "optimization",
            "target": "preloading",
            "action": "Preload frequently used models",
            "priority": "low"
        })
        
        return optimizations
    
    def _record_optimization(self, optimization: List[Dict[str, Any]]):
        """记录优化历史"""
        self.optimization_history.append({
            "optimization": optimization,
            "timestamp": datetime.now().isoformat()
        })
    
    async def apply_optimization(self, optimization: Dict[str, Any]) -> Dict[str, Any]:
        """应用优化"""
        target = optimization.get("target")
        action = optimization.get("action")
        
        if target == "preloading":
            await self.model_preloader.preload_model("qwen2.5:3b-instruct-q4_K_M")
            return {"success": True, "message": f"Applied optimization: {action}"}
        elif target == "memory":
            for model in list(self.model_preloader.get_preloaded_models().keys()):
                self.model_preloader.remove_model(model)
            return {"success": True, "message": "Released memory by removing preloaded models"}
        else:
            return {"success": True, "message": f"Optimization noted: {action}"}
    
    async def get_feedback_statistics(self) -> Dict[str, Any]:
        """获取反馈统计"""
        return self.feedback_memory.analyze_feedback()
    
    async def get_performance_statistics(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.performance_monitor.analyze_performance()
    
    async def get_optimization_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取优化历史"""
        return self.optimization_history[-limit:]
    
    async def get_agent_info(self) -> Dict[str, Any]:
        """获取 Agent 信息"""
        return {
            "name": self.name,
            "role": self.role,
            "components": ["ModelPreloader", "FeedbackMemory", "PerformanceMonitor"],
            "description": "负责收集反馈并调整系统，优化系统性能和行为"
        }
