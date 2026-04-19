#!/usr/bin/env python3
"""
模型评估器
评估模型在不同任务上的性能
"""

import time
import json
import os
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime


class EvaluationResult(BaseModel):
    """评估结果"""
    model_name: str
    task_type: str
    accuracy: float
    response_time: float
    cost: float
    reliability: float
    overall_score: float
    timestamp: datetime = datetime.now()
    details: Optional[Dict[str, Any]] = None


class ModelEvaluator:
    """模型评估器"""
    
    def __init__(self, evaluation_storage: str = "data/model_evaluations.json"):
        self.evaluation_storage = evaluation_storage
        self.evaluations: List[EvaluationResult] = []
        self._load_evaluations()
    
    def _load_evaluations(self):
        """加载历史评估结果"""
        try:
            if os.path.exists(self.evaluation_storage):
                with open(self.evaluation_storage, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for eval_data in data:
                        if 'timestamp' in eval_data:
                            eval_data['timestamp'] = datetime.fromisoformat(eval_data['timestamp'])
                        self.evaluations.append(EvaluationResult(**eval_data))
        except Exception as e:
            print(f"加载评估结果失败: {e}")
    
    def _save_evaluations(self):
        """保存评估结果"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.evaluation_storage), exist_ok=True)
            
            # 转换为可序列化的格式
            data = []
            for eval_result in self.evaluations:
                eval_dict = eval_result.model_dump()
                eval_dict['timestamp'] = eval_dict['timestamp'].isoformat()
                data.append(eval_dict)
            
            with open(self.evaluation_storage, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存评估结果失败: {e}")
    
    async def evaluate_model(self, model_name: str, task_type: str, test_data: str) -> EvaluationResult:
        """评估模型"""
        # 模拟评估过程
        # 实际实现中，这里应该调用模型API进行真实评估
        
        # 模拟响应时间
        start_time = time.time()
        time.sleep(0.5)  # 模拟处理时间
        response_time = time.time() - start_time
        
        # 基于模型名称和任务类型模拟性能数据
        performance_data = self._get_simulation_data(model_name, task_type)
        
        # 计算综合得分
        overall_score = (
            performance_data['accuracy'] * 0.4 +
            (1.0 / response_time) * 0.3 * 10  # 响应时间越短得分越高
            + performance_data['reliability'] * 0.2 +
            (1.0 - performance_data['cost']) * 0.1  # 成本越低得分越高
        )
        overall_score = min(1.0, max(0.0, overall_score))
        
        result = EvaluationResult(
            model_name=model_name,
            task_type=task_type,
            accuracy=performance_data['accuracy'],
            response_time=response_time,
            cost=performance_data['cost'],
            reliability=performance_data['reliability'],
            overall_score=overall_score,
            details={
                'test_data_length': len(test_data),
                'task_complexity': self._estimate_task_complexity(task_type),
                'simulation': True
            }
        )
        
        # 保存评估结果
        self.evaluations.append(result)
        self._save_evaluations()
        
        return result
    
    def _get_simulation_data(self, model_name: str, task_type: str) -> Dict[str, float]:
        """获取模拟性能数据"""
        # 基于模型和任务类型的模拟数据
        base_data = {
            'gemma4:e4b': {
                'text_generation': {'accuracy': 0.85, 'cost': 0.1, 'reliability': 0.9},
                'conversation': {'accuracy': 0.88, 'cost': 0.15, 'reliability': 0.92},
                'coding': {'accuracy': 0.82, 'cost': 0.2, 'reliability': 0.88},
                'reasoning': {'accuracy': 0.80, 'cost': 0.25, 'reliability': 0.85}
            },
            'gemma:latest': {
                'text_generation': {'accuracy': 0.80, 'cost': 0.05, 'reliability': 0.85},
                'conversation': {'accuracy': 0.82, 'cost': 0.1, 'reliability': 0.88},
                'coding': {'accuracy': 0.75, 'cost': 0.15, 'reliability': 0.80},
                'reasoning': {'accuracy': 0.72, 'cost': 0.2, 'reliability': 0.78}
            },
            'gemma4:latest': {
                'text_generation': {'accuracy': 0.90, 'cost': 0.2, 'reliability': 0.95},
                'conversation': {'accuracy': 0.92, 'cost': 0.25, 'reliability': 0.96},
                'coding': {'accuracy': 0.88, 'cost': 0.3, 'reliability': 0.92},
                'reasoning': {'accuracy': 0.86, 'cost': 0.35, 'reliability': 0.90}
            }
        }
        
        model_data = base_data.get(model_name, base_data['gemma:latest'])
        task_data = model_data.get(task_type, model_data['text_generation'])
        
        return task_data
    
    def _estimate_task_complexity(self, task_type: str) -> str:
        """估计任务复杂度"""
        complexity_map = {
            'text_generation': 'medium',
            'conversation': 'medium',
            'coding': 'high',
            'reasoning': 'high',
            'summarization': 'medium',
            'translation': 'medium',
            'classification': 'low',
            'qa': 'medium'
        }
        return complexity_map.get(task_type, 'medium')
    
    def get_evaluation_history(self, model_name: Optional[str] = None, 
                             task_type: Optional[str] = None) -> List[EvaluationResult]:
        """获取评估历史"""
        results = self.evaluations
        
        if model_name:
            results = [r for r in results if r.model_name == model_name]
        if task_type:
            results = [r for r in results if r.task_type == task_type]
        
        # 按时间排序
        results.sort(key=lambda x: x.timestamp, reverse=True)
        
        return results
    
    def get_best_model(self, task_type: str) -> Optional[EvaluationResult]:
        """获取特定任务的最佳模型"""
        task_evaluations = [r for r in self.evaluations if r.task_type == task_type]
        if not task_evaluations:
            return None
        
        # 按综合得分排序
        task_evaluations.sort(key=lambda x: x.overall_score, reverse=True)
        return task_evaluations[0]
    
    def get_model_performance(self, model_name: str) -> Dict[str, Any]:
        """获取模型整体性能"""
        model_evaluations = [r for r in self.evaluations if r.model_name == model_name]
        if not model_evaluations:
            return {}
        
        # 计算平均性能
        avg_accuracy = sum(r.accuracy for r in model_evaluations) / len(model_evaluations)
        avg_response_time = sum(r.response_time for r in model_evaluations) / len(model_evaluations)
        avg_cost = sum(r.cost for r in model_evaluations) / len(model_evaluations)
        avg_reliability = sum(r.reliability for r in model_evaluations) / len(model_evaluations)
        avg_overall = sum(r.overall_score for r in model_evaluations) / len(model_evaluations)
        
        return {
            'model_name': model_name,
            'evaluation_count': len(model_evaluations),
            'average_accuracy': avg_accuracy,
            'average_response_time': avg_response_time,
            'average_cost': avg_cost,
            'average_reliability': avg_reliability,
            'average_overall_score': avg_overall,
            'last_evaluation': max(r.timestamp for r in model_evaluations)
        }


# 全局模型评估器实例
_model_evaluator = None

def get_model_evaluator() -> ModelEvaluator:
    """获取模型评估器实例"""
    global _model_evaluator
    if _model_evaluator is None:
        _model_evaluator = ModelEvaluator()
    return _model_evaluator


if __name__ == "__main__":
    # 测试
    evaluator = get_model_evaluator()
    
    # 评估模型
    import asyncio
    
    async def test_evaluation():
        result = await evaluator.evaluate_model(
            model_name="gemma4:e4b",
            task_type="coding",
            test_data="Write a Python function to calculate factorial"
        )
        print(f"评估结果: {result.model_dump()}")
        
        # 获取最佳模型
        best_model = evaluator.get_best_model("coding")
        if best_model:
            print(f"最佳编码模型: {best_model.model_name} (得分: {best_model.overall_score:.2f})")
        
        # 获取模型性能
        performance = evaluator.get_model_performance("gemma4:e4b")
        print(f"模型性能: {performance}")
    
    asyncio.run(test_evaluation())