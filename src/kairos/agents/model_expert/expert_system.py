#!/usr/bin/env python3
"""
模型专家系统
基于用户需求推荐合适的模型
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from .model_registry import get_model_registry, ModelInfo
from .evaluation import get_model_evaluator, EvaluationResult


class ModelRecommendation(BaseModel):
    """模型推荐"""
    model_name: str
    score: float
    reasoning: str
    details: Optional[Dict[str, Any]] = None


class ModelExpertSystem:
    """模型专家系统"""
    
    def __init__(self):
        self.registry = get_model_registry()
        self.evaluator = get_model_evaluator()
    
    def get_recommendation(self, task_type: str, 
                          requirements: Optional[Dict[str, float]] = None) -> ModelRecommendation:
        """获取模型推荐"""
        # 获取可用模型
        available_models = self.registry.get_available_models()
        if not available_models:
            return ModelRecommendation(
                model_name="gemma4:e4b",
                score=0.5,
                reasoning="无可用模型，返回默认模型",
                details={"default": True}
            )
        
        # 计算每个模型的推荐分数
        recommendations = []
        for model in available_models:
            # 检查模型是否支持该任务
            if task_type not in model.capabilities:
                continue
            
            # 计算基础分数
            base_score = self._calculate_base_score(model, task_type)
            
            # 应用用户需求权重
            final_score = self._apply_requirements(base_score, model, requirements)
            
            recommendations.append({
                "model": model,
                "score": final_score
            })
        
        # 排序并返回最佳推荐
        if recommendations:
            recommendations.sort(key=lambda x: x["score"], reverse=True)
            best = recommendations[0]
            
            # 生成推荐理由
            reasoning = self._generate_reasoning(best["model"], task_type, requirements)
            
            return ModelRecommendation(
                model_name=best["model"].name,
                score=best["score"],
                reasoning=reasoning,
                details={
                    "capabilities": best["model"].capabilities,
                    "performance": best["model"].performance,
                    "cost": best["model"].cost
                }
            )
        else:
            # 返回默认模型
            return ModelRecommendation(
                model_name="gemma4:e4b",
                score=0.5,
                reasoning="无匹配模型，返回默认模型",
                details={"default": True}
            )
    
    def _calculate_base_score(self, model: ModelInfo, task_type: str) -> float:
        """计算基础分数"""
        # 基于模型性能计算基础分数
        performance = model.performance
        
        # 任务复杂度权重
        task_weights = {
            "text_generation": {"accuracy": 0.4, "speed": 0.3, "cost_efficiency": 0.3},
            "conversation": {"accuracy": 0.3, "speed": 0.4, "cost_efficiency": 0.3},
            "coding": {"accuracy": 0.5, "speed": 0.2, "cost_efficiency": 0.3},
            "reasoning": {"accuracy": 0.5, "speed": 0.2, "cost_efficiency": 0.3},
            "summarization": {"accuracy": 0.4, "speed": 0.3, "cost_efficiency": 0.3},
            "translation": {"accuracy": 0.4, "speed": 0.3, "cost_efficiency": 0.3},
            "classification": {"accuracy": 0.5, "speed": 0.3, "cost_efficiency": 0.2},
            "qa": {"accuracy": 0.4, "speed": 0.3, "cost_efficiency": 0.3}
        }
        
        weights = task_weights.get(task_type, task_weights["text_generation"])
        
        score = (
            performance.get("accuracy", 0.5) * weights["accuracy"] +
            performance.get("speed", 0.5) * weights["speed"] +
            performance.get("cost_efficiency", 0.5) * weights["cost_efficiency"]
        )
        
        # 成本调整
        score = score * (1 - model.cost * 0.1)  # 成本越高，分数越低
        
        return score
    
    def _apply_requirements(self, base_score: float, model: ModelInfo, 
                          requirements: Optional[Dict[str, float]]) -> float:
        """应用用户需求权重"""
        if not requirements:
            return base_score
        
        # 需求权重映射
        requirement_mapping = {
            "accuracy": "accuracy",
            "speed": "speed",
            "cost": "cost_efficiency",
            "reliability": "reliability"
        }
        
        adjusted_score = base_score
        
        for req_key, req_value in requirements.items():
            if req_key in requirement_mapping:
                perf_key = requirement_mapping[req_key]
                if perf_key in model.performance:
                    # 根据用户需求调整分数
                    performance_value = model.performance[perf_key]
                    # 如果用户要求高，而模型性能也高，则加分
                    if req_value > 0.7 and performance_value > 0.7:
                        adjusted_score += (performance_value - 0.7) * 0.2
                    # 如果用户要求高，但模型性能低，则减分
                    elif req_value > 0.7 and performance_value < 0.5:
                        adjusted_score -= (0.5 - performance_value) * 0.2
        
        return min(1.0, max(0.0, adjusted_score))
    
    def _generate_reasoning(self, model: ModelInfo, task_type: str, 
                          requirements: Optional[Dict[str, float]]) -> str:
        """生成推荐理由"""
        reasoning_parts = []
        
        # 基础能力
        reasoning_parts.append(f"{model.name} 支持 {task_type} 任务")
        
        # 性能优势
        performance = model.performance
        if performance.get("accuracy", 0) > 0.8:
            reasoning_parts.append(f"准确率高 ({performance['accuracy']:.2f})")
        if performance.get("speed", 0) > 0.8:
            reasoning_parts.append(f"响应速度快 ({performance['speed']:.2f})")
        if performance.get("cost_efficiency", 0) > 0.8:
            reasoning_parts.append(f"成本效益高 ({performance['cost_efficiency']:.2f})")
        
        # 成本考虑
        if model.cost < 0.1:
            reasoning_parts.append("运行成本低")
        
        # 用户需求匹配
        if requirements:
            if requirements.get("accuracy", 0) > 0.7 and performance.get("accuracy", 0) > 0.8:
                reasoning_parts.append("满足高准确率需求")
            if requirements.get("speed", 0) > 0.7 and performance.get("speed", 0) > 0.8:
                reasoning_parts.append("满足高速度需求")
            if requirements.get("cost", 0) < 0.3 and model.cost < 0.1:
                reasoning_parts.append("满足低成本需求")
        
        return "，".join(reasoning_parts)
    
    async def evaluate_model(self, model_name: str, task_type: str, 
                           test_data: str) -> EvaluationResult:
        """评估模型"""
        return await self.evaluator.evaluate_model(model_name, task_type, test_data)
    
    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """获取模型信息"""
        return self.registry.get_model(model_name)
    
    def list_models(self, capability: Optional[str] = None) -> List[ModelInfo]:
        """列出模型"""
        return self.registry.list_models(capability)
    
    def get_evaluation_history(self, model_name: Optional[str] = None, 
                             task_type: Optional[str] = None) -> List[EvaluationResult]:
        """获取评估历史"""
        return self.evaluator.get_evaluation_history(model_name, task_type)
    
    def get_model_performance(self, model_name: str) -> Dict[str, Any]:
        """获取模型性能"""
        return self.evaluator.get_model_performance(model_name)
    
    def suggest_model_improvements(self, model_name: str) -> List[str]:
        """建议模型改进"""
        model = self.registry.get_model(model_name)
        if not model:
            return ["模型不存在"]
        
        improvements = []
        performance = model.performance
        
        if performance.get("accuracy", 0) < 0.8:
            improvements.append("提高模型准确率")
        if performance.get("speed", 0) < 0.7:
            improvements.append("优化模型响应速度")
        if performance.get("cost_efficiency", 0) < 0.7:
            improvements.append("降低运行成本")
        if model.cost > 0.2:
            improvements.append("减少模型使用成本")
        
        if not improvements:
            improvements.append("模型性能良好，无需改进")
        
        return improvements


# 全局模型专家系统实例
_model_expert_system = None

def get_model_expert_system() -> ModelExpertSystem:
    """获取模型专家系统实例"""
    global _model_expert_system
    if _model_expert_system is None:
        _model_expert_system = ModelExpertSystem()
    return _model_expert_system


if __name__ == "__main__":
    # 测试
    expert = get_model_expert_system()
    
    # 获取推荐
    recommendation = expert.get_recommendation(
        task_type="coding",
        requirements={"accuracy": 0.9, "speed": 0.7}
    )
    print(f"推荐模型: {recommendation.model_name}")
    print(f"推荐分数: {recommendation.score:.2f}")
    print(f"推荐理由: {recommendation.reasoning}")
    
    # 评估模型
    import asyncio
    
    async def test_evaluation():
        result = await expert.evaluate_model(
            model_name="gemma4:e4b",
            task_type="coding",
            test_data="Write a Python function to calculate factorial"
        )
        print(f"\n评估结果: {result.model_name}")
        print(f"综合得分: {result.overall_score:.2f}")
        print(f"准确率: {result.accuracy:.2f}")
        print(f"响应时间: {result.response_time:.2f}s")
    
    asyncio.run(test_evaluation())
    
    # 模型改进建议
    improvements = expert.suggest_model_improvements("gemma:latest")
    print(f"\n模型改进建议:")
    for improvement in improvements:
        print(f"- {improvement}")