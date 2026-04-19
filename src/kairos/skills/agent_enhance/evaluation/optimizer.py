#!/usr/bin/env python3
"""
能力评估与优化
评估Agent能力并提供优化建议
"""

import asyncio
import logging
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel

from .metrics import EvaluationMetrics, EvaluationMetric
from ..professional_agents import get_agent_registry, ProfessionalAgent

logger = logging.getLogger(__name__)


class EvaluationResult(BaseModel):
    """评估结果"""
    agent_id: str
    agent_name: str
    overall_score: float
    metrics: Dict[str, float]
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str]
    timestamp: datetime = datetime.now()


class AgentEvaluator:
    """Agent评估器"""
    
    def __init__(self, storage_path: str = "data/agent_evaluations"):
        self.storage_path = storage_path
        self.agent_registry = get_agent_registry()
        self.evaluations: List[EvaluationResult] = []
        self._load_evaluations()
    
    def _load_evaluations(self):
        """加载评估结果"""
        try:
            if os.path.exists(self.storage_path):
                for filename in os.listdir(self.storage_path):
                    if filename.endswith(".json"):
                        with open(os.path.join(self.storage_path, filename), 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if 'timestamp' in data:
                                data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                            result = EvaluationResult(**data)
                            self.evaluations.append(result)
        except Exception as e:
            logger.error(f"加载评估结果失败: {e}")
    
    def _save_evaluation(self, result: EvaluationResult):
        """保存评估结果"""
        try:
            os.makedirs(self.storage_path, exist_ok=True)
            filename = f"{result.agent_id}_{result.timestamp.strftime('%Y%m%d%H%M%S')}.json"
            with open(os.path.join(self.storage_path, filename), 'w', encoding='utf-8') as f:
                json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存评估结果失败: {e}")
    
    async def evaluate_agent(self, agent_id: str) -> Optional[EvaluationResult]:
        """评估Agent"""
        agent = self.agent_registry.get_agent(agent_id)
        if not agent:
            logger.error(f"Agent {agent_id} 不存在")
            return None
        
        # 根据Agent类型选择评估指标
        if agent_id == "code_agent":
            metrics = EvaluationMetrics.get_code_agent_metrics()
        elif agent_id == "data_agent":
            metrics = EvaluationMetrics.get_data_agent_metrics()
        elif agent_id == "content_agent":
            metrics = EvaluationMetrics.get_content_agent_metrics()
        else:
            metrics = EvaluationMetrics.get_default_metrics()
        
        # 执行评估测试
        metric_scores = {}
        for metric in metrics:
            score = await self._evaluate_metric(agent, metric)
            metric_scores[metric.name] = score
        
        # 计算总分
        total_weight = sum(metric.weight for metric in metrics)
        overall_score = sum(metric_scores[metric.name] * metric.weight for metric in metrics) / total_weight
        
        # 分析优势和劣势
        strengths = []
        weaknesses = []
        for metric in metrics:
            score = metric_scores[metric.name]
            if score >= 0.8:
                strengths.append(f"{metric.name}: {score:.2f}")
            elif score <= 0.5:
                weaknesses.append(f"{metric.name}: {score:.2f}")
        
        # 生成优化建议
        suggestions = self._generate_suggestions(agent, metric_scores, metrics)
        
        # 创建评估结果
        result = EvaluationResult(
            agent_id=agent.agent_id,
            agent_name=agent.name,
            overall_score=overall_score,
            metrics=metric_scores,
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions
        )
        
        # 保存评估结果
        self.evaluations.append(result)
        self._save_evaluation(result)
        
        logger.info(f"评估完成: {agent.name}, 得分: {overall_score:.2f}")
        return result
    
    async def _evaluate_metric(self, agent: ProfessionalAgent, metric: EvaluationMetric) -> float:
        """评估单个指标"""
        # 这里应该实现具体的评估逻辑
        # 简化示例，返回随机分数
        import random
        return random.uniform(metric.min_score, metric.max_score)
    
    def _generate_suggestions(self, agent: ProfessionalAgent, 
                            metric_scores: Dict[str, float],
                            metrics: List[EvaluationMetric]) -> List[str]:
        """生成优化建议"""
        suggestions = []
        
        # 根据得分生成建议
        for metric in metrics:
            score = metric_scores[metric.name]
            if score < 0.6:
                if metric.name == "code_quality":
                    suggestions.append("提高代码质量，注重代码规范和可读性")
                elif metric.name == "data_accuracy":
                    suggestions.append("加强数据验证，提高数据处理的准确性")
                elif metric.name == "content_quality":
                    suggestions.append("提升内容质量，注重内容的深度和广度")
                elif metric.name == "speed":
                    suggestions.append("优化响应速度，减少处理时间")
                elif metric.name == "creativity":
                    suggestions.append("增强创造力，提供更多创新的解决方案")
        
        # 通用建议
        if not suggestions:
            suggestions.append("继续保持良好的表现")
            suggestions.append("尝试处理更复杂的任务以进一步提升能力")
        
        return suggestions
    
    def get_evaluation_history(self, agent_id: str) -> List[EvaluationResult]:
        """获取评估历史"""
        return [eval for eval in self.evaluations if eval.agent_id == agent_id]
    
    def get_latest_evaluation(self, agent_id: str) -> Optional[EvaluationResult]:
        """获取最新评估"""
        history = self.get_evaluation_history(agent_id)
        if history:
            history.sort(key=lambda x: x.timestamp, reverse=True)
            return history[0]
        return None
    
    def get_agent_performance_trend(self, agent_id: str) -> Dict[str, Any]:
        """获取Agent性能趋势"""
        history = self.get_evaluation_history(agent_id)
        if not history:
            return {}
        
        # 按时间排序
        history.sort(key=lambda x: x.timestamp)
        
        # 提取数据
        timestamps = [eval.timestamp.isoformat() for eval in history]
        scores = [eval.overall_score for eval in history]
        
        return {
            "timestamps": timestamps,
            "scores": scores,
            "improvement": scores[-1] - scores[0] if len(scores) > 1 else 0
        }
    
    def batch_evaluate(self) -> List[EvaluationResult]:
        """批量评估所有Agent"""
        agents = self.agent_registry.list_agents()
        results = []
        
        for agent in agents:
            result = asyncio.run(self.evaluate_agent(agent.agent_id))
            if result:
                results.append(result)
        
        return results


# 全局Agent评估器实例
_agent_evaluator = None

def get_agent_evaluator() -> AgentEvaluator:
    """获取Agent评估器实例"""
    global _agent_evaluator
    if _agent_evaluator is None:
        _agent_evaluator = AgentEvaluator()
    return _agent_evaluator


if __name__ == "__main__":
    # 测试
    import asyncio
    from ..professional_agents import get_code_agent, get_data_agent, get_content_agent
    
    async def test_evaluation():
        evaluator = get_agent_evaluator()
        
        # 注册Agent
        code_agent = get_code_agent()
        data_agent = get_data_agent()
        content_agent = get_content_agent()
        
        agent_registry = get_agent_registry()
        agent_registry.register_agent(code_agent)
        agent_registry.register_agent(data_agent)
        agent_registry.register_agent(content_agent)
        
        # 评估Agent
        code_result = await evaluator.evaluate_agent("code_agent")
        data_result = await evaluator.evaluate_agent("data_agent")
        content_result = await evaluator.evaluate_agent("content_agent")
        
        # 打印结果
        if code_result:
            print(f"代码Agent评估结果: {code_result.overall_score:.2f}")
            print(f"优势: {code_result.strengths}")
            print(f"劣势: {code_result.weaknesses}")
            print(f"建议: {code_result.suggestions}")
        
        if data_result:
            print(f"\n数据Agent评估结果: {data_result.overall_score:.2f}")
        
        if content_result:
            print(f"\n内容Agent评估结果: {content_result.overall_score:.2f}")
    
    asyncio.run(test_evaluation())