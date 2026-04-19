#!/usr/bin/env python3
"""
核心决策层 - 明策
负责制定决策和策略，管理模型和资源
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class LocalModelManager:
    """本地模型管理器"""
    
    def __init__(self):
        self.models = {
            "qwen2.5:3b-instruct-q4_K_M": {
                "name": "qwen2.5:3b-instruct-q4_K_M",
                "type": "llm",
                "status": "available",
                "memory_usage": "2.0GB",
                "priority": "primary"
            }
        }
    
    def get_model(self, model_name: str = None) -> Optional[Dict[str, Any]]:
        """获取模型"""
        if model_name:
            return self.models.get(model_name)
        for model in self.models.values():
            if model['priority'] == 'primary':
                return model
        return None
    
    def get_available_models(self) -> list:
        """获取可用模型"""
        return [model for model in self.models.values() if model['status'] == 'available']
    
    def update_model_status(self, model_name: str, status: str) -> bool:
        """更新模型状态"""
        if model_name in self.models:
            self.models[model_name]['status'] = status
            return True
        return False


class ModelResourceManager:
    """模型资源管理器 - 适配 i5-7500/16GB"""
    
    def __init__(self):
        self.total_memory = 16
        self.used_memory = 0
        self.cpu_cores = 4
        self.used_cpu = 0
        self.max_concurrent_models = 1
    
    def allocate_resources(self, model: Dict[str, Any]) -> bool:
        """分配资源"""
        memory_needed = float(model['memory_usage'].replace('GB', ''))
        
        if self.used_memory + memory_needed <= self.total_memory:
            self.used_memory += memory_needed
            self.used_cpu += 2
            return True
        return False
    
    def release_resources(self, model: Dict[str, Any]) -> bool:
        """释放资源"""
        memory_used = float(model['memory_usage'].replace('GB', ''))
        self.used_memory -= memory_used
        self.used_cpu -= 2
        return True
    
    def get_resource_status(self) -> Dict[str, Any]:
        """获取资源状态"""
        return {
            "total_memory": self.total_memory,
            "used_memory": self.used_memory,
            "available_memory": self.total_memory - self.used_memory,
            "total_cpu": self.cpu_cores,
            "used_cpu": self.used_cpu,
            "available_cpu": self.cpu_cores - self.used_cpu
        }


class DecisionLayer_MingCe:
    """
    核心决策层 - 明策
    角色：决策制定者和资源管理者
    工作流程：接收评估结果 → 资源检查 → 模型选择 → 决策制定 → 输出决策结果
    """
    
    def __init__(self):
        self.name = "明策"
        self.role = "核心决策层"
        self.models = {
            "primary": "qwen2.5:3b-instruct-q4_K_M"
        }
        self.model_manager = LocalModelManager()
        self.resource_manager = ModelResourceManager()
        self.decision_history = []
    
    async def make_decision(self, evaluation_report: Dict[str, Any]) -> Dict[str, Any]:
        """制定决策"""
        try:
            resource_status = self._check_resources()
            selected_model = self._select_model(evaluation_report, resource_status)
            
            if not selected_model:
                return {
                    "status": "error",
                    "message": "No available models or insufficient resources",
                    "processed_by": self.name,
                    "timestamp": datetime.now().isoformat()
                }
            
            if not self.resource_manager.allocate_resources(selected_model):
                return {
                    "status": "error",
                    "message": "Failed to allocate resources",
                    "processed_by": self.name,
                    "timestamp": datetime.now().isoformat()
                }
            
            decision = self._generate_decision(evaluation_report, selected_model)
            self._record_decision(decision, selected_model)
            
            logger.info(f"明策制定决策：{len(decision.get('decisions', []))} 个决策")
            return decision
            
        except Exception as e:
            logger.error(f"明策决策失败：{e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _check_resources(self) -> Dict[str, Any]:
        """检查资源状态"""
        return self.resource_manager.get_resource_status()
    
    def _select_model(self, evaluation_report: Dict[str, Any], resource_status: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """选择合适的模型"""
        value_score = evaluation_report.get('value_scores', {}).get('overall', 0.5)
        available_models = self.model_manager.get_available_models()
        
        if value_score >= 0.8:
            for model in available_models:
                if model['priority'] == 'primary':
                    return model
        elif value_score >= 0.5:
            for model in available_models:
                if model['priority'] == 'secondary':
                    return model
        
        return available_models[0] if available_models else None
    
    def _generate_decision(self, evaluation_report: Dict[str, Any], selected_model: Dict[str, Any]) -> Dict[str, Any]:
        """生成决策"""
        recommendations = evaluation_report.get('recommendations', [])
        prioritized_info = evaluation_report.get('prioritized_info', [])
        
        decisions = []
        
        for item in prioritized_info[:2]:
            priority_level = item['priority_level']
            
            if priority_level == 'critical':
                decisions.append({
                    "action": "紧急执行",
                    "target": item['item']['type'],
                    "confidence": 0.95,
                    "model_used": selected_model['name']
                })
            elif priority_level == 'high':
                decisions.append({
                    "action": "优先执行",
                    "target": item['item']['type'],
                    "confidence": 0.85,
                    "model_used": selected_model['name']
                })
        
        for recommendation in recommendations:
            decisions.append({
                "action": recommendation['action'],
                "reason": recommendation['reason'],
                "priority": recommendation['priority'],
                "model_used": selected_model['name']
            })
        
        return {
            "status": "success",
            "type": "decision",
            "model_used": selected_model['name'],
            "resource_status": self.resource_manager.get_resource_status(),
            "decisions": decisions,
            "confidence": self._calculate_confidence(decisions),
            "processed_by": self.name,
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_confidence(self, decisions: list) -> float:
        """计算决策置信度"""
        if not decisions:
            return 0.0
        
        total_confidence = sum(d.get('confidence', 0.7) for d in decisions)
        return total_confidence / len(decisions)
    
    def _record_decision(self, decision: Dict[str, Any], model: Dict[str, Any]):
        """记录决策历史"""
        self.decision_history.append({
            "decision": decision,
            "model_used": model['name'],
            "timestamp": datetime.now().isoformat()
        })
    
    async def release_resources(self, model_name: str) -> bool:
        """释放模型资源"""
        model = self.model_manager.get_model(model_name)
        if model:
            return self.resource_manager.release_resources(model)
        return False
    
    async def get_decision_history(self, limit: int = 10) -> list:
        """获取决策历史"""
        return self.decision_history[-limit:]
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "models": self.model_manager.models,
            "resources": self.resource_manager.get_resource_status(),
            "decision_count": len(self.decision_history)
        }
    
    async def get_agent_info(self) -> Dict[str, Any]:
        """获取 Agent 信息"""
        return {
            "name": self.name,
            "role": self.role,
            "models": self.models,
            "description": "负责制定决策和策略，管理模型和资源"
        }
