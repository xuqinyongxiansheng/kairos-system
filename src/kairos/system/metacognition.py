#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
元认知与自我监控层模块

核心功能：
1. 自我认知模块：系统状态监测、能力评估模型、知识边界识别
2. 反思系统：决策过程记录、错误分析算法、改进策略生成
3. 元学习模块：学习策略优化、认知偏差修正、思维模式调整
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import os
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger("MetaCognition")


class SelfAssessmentType(Enum):
    """自我评估类型"""
    CAPABILITY = "capability"
    KNOWLEDGE = "knowledge"
    PERFORMANCE = "performance"
    LIMITATIONS = "limitations"


class ReflectionType(Enum):
    """反思类型"""
    DECISION = "decision"
    ERROR = "error"
    SUCCESS = "success"
    IMPROVEMENT = "improvement"


class LearningStrategy(Enum):
    """学习策略类型"""
    SPACED_REPETITION = "spaced_repetition"
    ACTIVE_RECALL = "active_recall"
    FEEDBACK_LOOP = "feedback_loop"
    METACOGNITIVE_MONITORING = "metacognitive_monitoring"


class CognitiveBias(Enum):
    """认知偏差类型"""
    CONFIRMATION_BIAS = "confirmation_bias"
    ANCHORING_EFFECT = "anchoring_effect"
    AVAILABILITY_HEURISTIC = "availability_heuristic"
    OVERCONFIDENCE = "overconfidence"
    HINDSIGHT_BIAS = "hindsight_bias"


@dataclass
class SelfAssessment:
    """自我评估数据类"""
    id: str
    assessment_type: SelfAssessmentType
    title: str
    description: str
    timestamp: str
    metrics: Dict[str, float]
    limitations: List[str] = None
    strengths: List[str] = None
    
    def __post_init__(self):
        if self.limitations is None:
            self.limitations = []
        if self.strengths is None:
            self.strengths = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "assessment_type": self.assessment_type.value,
            "title": self.title,
            "description": self.description,
            "timestamp": self.timestamp,
            "metrics": self.metrics,
            "limitations": self.limitations,
            "strengths": self.strengths
        }


@dataclass
class Reflection:
    """反思记录数据类"""
    id: str
    reflection_type: ReflectionType
    content: str
    context: Dict[str, Any]
    timestamp: str
    insights: List[str] = None
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.insights is None:
            self.insights = []
        if self.recommendations is None:
            self.recommendations = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "reflection_type": self.reflection_type.value,
            "content": self.content,
            "context": self.context,
            "timestamp": self.timestamp,
            "insights": self.insights,
            "recommendations": self.recommendations
        }


@dataclass
class LearningStrategyConfig:
    """学习策略配置数据类"""
    strategy_type: LearningStrategy
    parameters: Dict[str, Any]
    effectiveness_score: float = 0.0
    last_updated: str = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "strategy_type": self.strategy_type.value,
            "parameters": self.parameters,
            "effectiveness_score": self.effectiveness_score,
            "last_updated": self.last_updated
        }


class MetaCognition:
    """元认知与自我监控层模块"""
    
    def __init__(self, config: Dict = None, agent = None):
        """初始化元认知与自我监控层模块"""
        self.config = config or {}
        self.agent = agent
        
        self.self_assessments: Dict[str, SelfAssessment] = {}
        self.reflections: Dict[str, Reflection] = {}
        self.learning_strategies: Dict[str, LearningStrategyConfig] = {}
        
        data_dir = self.config.get("data_dir", "./data/metacognition")
        self.assessments_file = os.path.join(data_dir, "self_assessments.json")
        self.reflections_file = os.path.join(data_dir, "reflections.json")
        self.strategies_file = os.path.join(data_dir, "learning_strategies.json")
        
        self._load_data()
        self._initialize_default_strategies()
        
        logger.info("元认知与自我监控层模块初始化完成")
    
    def _load_data(self):
        """加载数据"""
        try:
            if os.path.exists(self.assessments_file):
                with open(self.assessments_file, "r", encoding="utf-8") as f:
                    assessments_data = json.load(f)
                    for assessment_id, assessment_data in assessments_data.items():
                        self.self_assessments[assessment_id] = SelfAssessment(
                            id=assessment_data["id"],
                            assessment_type=SelfAssessmentType(assessment_data["assessment_type"]),
                            title=assessment_data["title"],
                            description=assessment_data["description"],
                            timestamp=assessment_data["timestamp"],
                            metrics=assessment_data["metrics"],
                            limitations=assessment_data["limitations"],
                            strengths=assessment_data["strengths"]
                        )
            
            if os.path.exists(self.reflections_file):
                with open(self.reflections_file, "r", encoding="utf-8") as f:
                    reflections_data = json.load(f)
                    for reflection_id, reflection_data in reflections_data.items():
                        self.reflections[reflection_id] = Reflection(
                            id=reflection_data["id"],
                            reflection_type=ReflectionType(reflection_data["reflection_type"]),
                            content=reflection_data["content"],
                            context=reflection_data["context"],
                            timestamp=reflection_data["timestamp"],
                            insights=reflection_data["insights"],
                            recommendations=reflection_data["recommendations"]
                        )
            
            if os.path.exists(self.strategies_file):
                with open(self.strategies_file, "r", encoding="utf-8") as f:
                    strategies_data = json.load(f)
                    for strategy_type, strategy_data in strategies_data.items():
                        self.learning_strategies[strategy_type] = LearningStrategyConfig(
                            strategy_type=LearningStrategy(strategy_data["strategy_type"]),
                            parameters=strategy_data["parameters"],
                            effectiveness_score=strategy_data["effectiveness_score"],
                            last_updated=strategy_data["last_updated"]
                        )
        
        except Exception as e:
            logger.error(f"加载元认知数据失败: {e}")
    
    def _save_data(self):
        """保存数据"""
        try:
            os.makedirs(os.path.dirname(self.assessments_file), exist_ok=True)
            
            assessments_data = {aid: assessment.to_dict() for aid, assessment in self.self_assessments.items()}
            with open(self.assessments_file, "w", encoding="utf-8") as f:
                json.dump(assessments_data, f, ensure_ascii=False, indent=2)
            
            reflections_data = {rid: reflection.to_dict() for rid, reflection in self.reflections.items()}
            with open(self.reflections_file, "w", encoding="utf-8") as f:
                json.dump(reflections_data, f, ensure_ascii=False, indent=2)
            
            strategies_data = {s.strategy_type.value: s.to_dict() for s in self.learning_strategies.values()}
            with open(self.strategies_file, "w", encoding="utf-8") as f:
                json.dump(strategies_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"保存元认知数据失败: {e}")
    
    def _initialize_default_strategies(self):
        """初始化默认学习策略"""
        default_strategies = [
            LearningStrategyConfig(
                strategy_type=LearningStrategy.SPACED_REPETITION,
                parameters={
                    "initial_interval": 1,
                    "multiplier": 2,
                    "max_interval": 30,
                    "min_interval": 1
                },
                effectiveness_score=0.85
            ),
            LearningStrategyConfig(
                strategy_type=LearningStrategy.ACTIVE_RECALL,
                parameters={
                    "recall_frequency": "daily",
                    "question_generation": "auto",
                    "difficulty_adjustment": True
                },
                effectiveness_score=0.82
            ),
            LearningStrategyConfig(
                strategy_type=LearningStrategy.FEEDBACK_LOOP,
                parameters={
                    "feedback_frequency": "continuous",
                    "adjustment_threshold": 0.7,
                    "optimization_cycles": 5
                },
                effectiveness_score=0.78
            ),
            LearningStrategyConfig(
                strategy_type=LearningStrategy.METACOGNITIVE_MONITORING,
                parameters={
                    "monitoring_frequency": "session",
                    "reflection_triggers": ["failure", "success", "threshold"],
                    "self_assessment_period": "weekly"
                },
                effectiveness_score=0.80
            )
        ]
        
        for strategy in default_strategies:
            if strategy.strategy_type.value not in self.learning_strategies:
                self.learning_strategies[strategy.strategy_type.value] = strategy
        
        self._save_data()
    
    async def perform_self_assessment(self, assessment_data: Dict[str, Any]) -> SelfAssessment:
        """执行自我评估"""
        try:
            assessment_id = f"assessment_{int(datetime.now().timestamp())}"
            
            assessment = SelfAssessment(
                id=assessment_id,
                assessment_type=SelfAssessmentType(assessment_data.get("assessment_type", SelfAssessmentType.CAPABILITY.value)),
                title=assessment_data.get("title", "自我评估"),
                description=assessment_data.get("description", ""),
                timestamp=datetime.now().isoformat(),
                metrics=assessment_data.get("metrics", {}),
                limitations=assessment_data.get("limitations", []),
                strengths=assessment_data.get("strengths", [])
            )
            
            await self._identify_limitations(assessment)
            
            self.self_assessments[assessment_id] = assessment
            self._save_data()
            
            return assessment
            
        except Exception as e:
            logger.error(f"执行自我评估失败: {e}")
            raise
    
    async def _identify_limitations(self, assessment: SelfAssessment):
        """识别知识边界和能力限制"""
        for metric_name, value in assessment.metrics.items():
            if value < 0.5:
                limitation = f"{metric_name} 能力不足 (当前水平: {value})"
                if limitation not in assessment.limitations:
                    assessment.limitations.append(limitation)
            
            if value > 0.8:
                strength = f"{metric_name} 能力优势 (当前水平: {value})"
                if strength not in assessment.strengths:
                    assessment.strengths.append(strength)
    
    async def record_reflection(self, reflection_data: Dict[str, Any]) -> Reflection:
        """记录反思"""
        try:
            reflection_id = f"reflection_{int(datetime.now().timestamp())}"
            
            reflection = Reflection(
                id=reflection_id,
                reflection_type=ReflectionType(reflection_data.get("reflection_type", ReflectionType.DECISION.value)),
                content=reflection_data.get("content", ""),
                context=reflection_data.get("context", {}),
                timestamp=datetime.now().isoformat(),
                insights=reflection_data.get("insights", []),
                recommendations=reflection_data.get("recommendations", [])
            )
            
            await self._generate_insights(reflection)
            
            self.reflections[reflection_id] = reflection
            self._save_data()
            
            return reflection
            
        except Exception as e:
            logger.error(f"记录反思失败: {e}")
            raise
    
    async def _generate_insights(self, reflection: Reflection):
        """生成反思洞察和建议"""
        if reflection.reflection_type == ReflectionType.ERROR:
            error_patterns = self._analyze_error_patterns(reflection.content)
            reflection.insights.extend(error_patterns)
            
            improvements = self._generate_improvement_recommendations(error_patterns)
            reflection.recommendations.extend(improvements)
            
        elif reflection.reflection_type == ReflectionType.SUCCESS:
            success_factors = self._analyze_success_factors(reflection.content)
            reflection.insights.extend(success_factors)
            
        elif reflection.reflection_type == ReflectionType.DECISION:
            decision_insights = self._analyze_decision_process(reflection.content)
            reflection.insights.extend(decision_insights)
    
    def _analyze_error_patterns(self, content: str) -> List[str]:
        """分析错误模式"""
        patterns = []
        content_lower = content.lower()
        
        if "confusion" in content_lower or "uncertain" in content_lower:
            patterns.append("识别到认知混淆模式，可能存在知识理解不清晰的问题")
        
        if "rushed" in content_lower or "hasty" in content_lower:
            patterns.append("识别到决策仓促模式，可能需要更多思考时间")
        
        if "overlooked" in content_lower or "missed" in content_lower:
            patterns.append("识别到信息遗漏模式，需要改进信息收集流程")
        
        return patterns
    
    def _generate_improvement_recommendations(self, error_patterns: List[str]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        for pattern in error_patterns:
            if "认知混淆" in pattern:
                recommendations.append("建议增加概念复习和理解验证环节")
            elif "决策仓促" in pattern:
                recommendations.append("建议实施决策延迟机制，增加思考时间")
            elif "信息遗漏" in pattern:
                recommendations.append("建议建立信息核对清单，确保信息完整性")
        
        return recommendations
    
    def _analyze_success_factors(self, content: str) -> List[str]:
        """分析成功因素"""
        factors = []
        content_lower = content.lower()
        
        if "planning" in content_lower or "preparation" in content_lower:
            factors.append("识别到充分准备因素，准备工作做得很好")
        
        if "analysis" in content_lower or "evaluation" in content_lower:
            factors.append("识别到深入分析因素，分析过程很全面")
        
        return factors
    
    def _analyze_decision_process(self, content: str) -> List[str]:
        """分析决策过程"""
        insights = []
        content_lower = content.lower()
        
        if "data" in content_lower or "evidence" in content_lower:
            insights.append("决策基于数据和证据，决策质量较高")
        else:
            insights.append("决策可能缺乏数据支持，建议增加数据收集")
        
        return insights
    
    async def detect_cognitive_biases(self, content: str) -> List[Dict[str, Any]]:
        """检测认知偏差"""
        detected_biases = []
        content_lower = content.lower()
        
        if "only" in content_lower and "supports" in content_lower:
            detected_biases.append({
                "bias_type": CognitiveBias.CONFIRMATION_BIAS.value,
                "description": "确认偏差：只关注支持自己观点的信息",
                "severity": "medium",
                "suggestion": "尝试寻找反证和不同观点"
            })
        
        if "definitely" in content_lower or "certain" in content_lower:
            detected_biases.append({
                "bias_type": CognitiveBias.OVERCONFIDENCE.value,
                "description": "过度自信：对判断过于确定",
                "severity": "high",
                "suggestion": "保持适度的不确定性，考虑多种可能性"
            })
        
        return detected_biases
    
    async def optimize_learning_strategy(self, strategy_type: LearningStrategy, 
                                     performance_metrics: Dict[str, float]) -> Dict[str, Any]:
        """优化学习策略"""
        strategy_key = strategy_type.value
        
        if strategy_key not in self.learning_strategies:
            return {"error": "学习策略不存在"}
        
        strategy = self.learning_strategies[strategy_key]
        
        if strategy_type == LearningStrategy.SPACED_REPETITION:
            recall_accuracy = performance_metrics.get("recall_accuracy", 0.5)
            
            if recall_accuracy > 0.8:
                strategy.parameters["initial_interval"] = min(
                    strategy.parameters["initial_interval"] * 1.5,
                    strategy.parameters["max_interval"]
                )
            elif recall_accuracy < 0.4:
                strategy.parameters["initial_interval"] = max(
                    strategy.parameters["initial_interval"] * 0.5,
                    strategy.parameters["min_interval"]
                )
        
        strategy.effectiveness_score = self._calculate_strategy_effectiveness(strategy, performance_metrics)
        strategy.last_updated = datetime.now().isoformat()
        
        self._save_data()
        
        return {
            "strategy_type": strategy_type.value,
            "updated_parameters": strategy.parameters,
            "effectiveness_score": strategy.effectiveness_score
        }
    
    def _calculate_strategy_effectiveness(self, strategy: LearningStrategyConfig, 
                                       performance_metrics: Dict[str, float]) -> float:
        """计算策略有效性"""
        weights = {
            "accuracy": 0.3,
            "efficiency": 0.3,
            "retention": 0.2,
            "satisfaction": 0.2
        }
        
        effectiveness = 0.0
        for metric_name, weight in weights.items():
            if metric_name in performance_metrics:
                effectiveness += performance_metrics[metric_name] * weight
        
        return max(0, min(1, effectiveness))
    
    async def get_metacognitive_dashboard(self) -> Dict[str, Any]:
        """获取元认知仪表盘"""
        recent_assessments = sorted(
            self.self_assessments.values(),
            key=lambda x: x.timestamp,
            reverse=True
        )[:5]
        
        reflection_stats = {}
        for reflection in self.reflections.values():
            rtype = reflection.reflection_type.value
            reflection_stats[rtype] = reflection_stats.get(rtype, 0) + 1
        
        strategy_effectiveness = {
            strategy.strategy_type.value: strategy.effectiveness_score
            for strategy in self.learning_strategies.values()
        }
        
        return {
            "recent_assessments": [a.to_dict() for a in recent_assessments],
            "reflection_statistics": reflection_stats,
            "learning_strategy_effectiveness": strategy_effectiveness,
            "total_assessments": len(self.self_assessments),
            "total_reflections": len(self.reflections),
            "knowledge_gaps": self._identify_knowledge_gaps()
        }
    
    def _identify_knowledge_gaps(self) -> List[str]:
        """识别知识差距"""
        gaps = []
        
        for assessment in self.self_assessments.values():
            gaps.extend(assessment.limitations)
        
        gap_counts = {}
        for gap in gaps:
            gap_counts[gap] = gap_counts.get(gap, 0) + 1
        
        return [gap for gap, count in sorted(gap_counts.items(), key=lambda x: x[1], reverse=True)][:10]
    
    async def generate_metacognitive_report(self) -> Dict[str, Any]:
        """生成元认知报告"""
        dashboard = await self.get_metacognitive_dashboard()
        
        cognitive_patterns = await self._analyze_cognitive_patterns()
        
        recommendations = await self._generate_metacognitive_recommendations(cognitive_patterns)
        
        return {
            "report_time": datetime.now().isoformat(),
            "dashboard": dashboard,
            "cognitive_patterns": cognitive_patterns,
            "recommendations": recommendations
        }
    
    async def _analyze_cognitive_patterns(self) -> Dict[str, Any]:
        """分析认知模式"""
        patterns = {
            "bias_frequency": {},
            "reflection_trends": {},
            "learning_effectiveness": {}
        }
        
        for reflection in self.reflections.values():
            biases = await self.detect_cognitive_biases(reflection.content)
            for bias in biases:
                bias_type = bias["bias_type"]
                patterns["bias_frequency"][bias_type] = patterns["bias_frequency"].get(bias_type, 0) + 1
        
        for reflection in self.reflections.values():
            rtype = reflection.reflection_type.value
            patterns["reflection_trends"][rtype] = patterns["reflection_trends"].get(rtype, 0) + 1
        
        for strategy_type, strategy in self.learning_strategies.items():
            patterns["learning_effectiveness"][strategy_type] = strategy.effectiveness_score
        
        return patterns
    
    async def _generate_metacognitive_recommendations(self, cognitive_patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成元认知改进建议"""
        recommendations = []
        
        for bias_type, count in cognitive_patterns["bias_frequency"].items():
            if count > 2:
                recommendations.append({
                    "type": "bias_mitigation",
                    "priority": "high",
                    "message": f"检测到频繁的{bias_type}，建议实施针对性的认知修正策略"
                })
        
        reflection_counts = cognitive_patterns["reflection_trends"]
        if reflection_counts.get("error", 0) > reflection_counts.get("success", 0):
            recommendations.append({
                "type": "reflection_balance",
                "priority": "medium",
                "message": "反思过于关注错误，建议增加对成功经验的总结"
            })
        
        for strategy_type, effectiveness in cognitive_patterns["learning_effectiveness"].items():
            if effectiveness < 0.6:
                recommendations.append({
                    "type": "strategy_improvement",
                    "priority": "high",
                    "message": f"学习策略 {strategy_type} 效果不佳，建议优化或更换策略"
                })
        
        return recommendations


_metacognition_instance = None


def get_metacognition(config: Dict = None, agent = None) -> MetaCognition:
    """获取元认知模块实例"""
    global _metacognition_instance
    
    if _metacognition_instance is None:
        _metacognition_instance = MetaCognition(config=config, agent=agent)
    
    return _metacognition_instance
