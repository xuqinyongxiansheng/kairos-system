#!/usr/bin/env python3
"""
评估指标
定义Agent能力评估的指标体系
"""

from typing import Dict, Any, List
from pydantic import BaseModel


class EvaluationMetric(BaseModel):
    """评估指标"""
    name: str
    description: str
    weight: float = 1.0
    min_score: float = 0.0
    max_score: float = 1.0


class EvaluationMetrics:
    """评估指标体系"""
    
    @staticmethod
    def get_default_metrics() -> List[EvaluationMetric]:
        """获取默认评估指标"""
        return [
            EvaluationMetric(
                name="task_completion",
                description="任务完成度",
                weight=0.3
            ),
            EvaluationMetric(
                name="accuracy",
                description="结果准确性",
                weight=0.25
            ),
            EvaluationMetric(
                name="speed",
                description="响应速度",
                weight=0.15
            ),
            EvaluationMetric(
                name="creativity",
                description="创造力",
                weight=0.1
            ),
            EvaluationMetric(
                name="adaptability",
                description="适应性",
                weight=0.1
            ),
            EvaluationMetric(
                name="communication",
                description="沟通能力",
                weight=0.1
            )
        ]
    
    @staticmethod
    def get_code_agent_metrics() -> List[EvaluationMetric]:
        """获取代码Agent评估指标"""
        return [
            EvaluationMetric(
                name="code_quality",
                description="代码质量",
                weight=0.3
            ),
            EvaluationMetric(
                name="bug_free",
                description="代码无错误",
                weight=0.25
            ),
            EvaluationMetric(
                name="performance",
                description="代码性能",
                weight=0.2
            ),
            EvaluationMetric(
                name="documentation",
                description="代码文档",
                weight=0.15
            ),
            EvaluationMetric(
                name="best_practices",
                description="最佳实践",
                weight=0.1
            )
        ]
    
    @staticmethod
    def get_data_agent_metrics() -> List[EvaluationMetric]:
        """获取数据Agent评估指标"""
        return [
            EvaluationMetric(
                name="data_accuracy",
                description="数据准确性",
                weight=0.3
            ),
            EvaluationMetric(
                name="analysis_depth",
                description="分析深度",
                weight=0.25
            ),
            EvaluationMetric(
                name="visualization_quality",
                description="可视化质量",
                weight=0.2
            ),
            EvaluationMetric(
                name="insights",
                description="洞察能力",
                weight=0.2
            ),
            EvaluationMetric(
                name="data_cleaning",
                description="数据清洗能力",
                weight=0.05
            )
        ]
    
    @staticmethod
    def get_content_agent_metrics() -> List[EvaluationMetric]:
        """获取内容Agent评估指标"""
        return [
            EvaluationMetric(
                name="content_quality",
                description="内容质量",
                weight=0.3
            ),
            EvaluationMetric(
                name="creativity",
                description="创造力",
                weight=0.25
            ),
            EvaluationMetric(
                name="relevance",
                description="内容相关性",
                weight=0.2
            ),
            EvaluationMetric(
                name="structure",
                description="结构清晰度",
                weight=0.15
            ),
            EvaluationMetric(
                name="engagement",
                description="内容吸引力",
                weight=0.1
            )
        ]