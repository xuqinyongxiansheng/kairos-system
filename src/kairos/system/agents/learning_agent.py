# -*- coding: utf-8 -*-
"""
学习Agent (LearningAgent)
学习适应，模式识别/策略进化
适用于: 技能学习、经验积累、策略优化、知识更新

特征:
- 经验驱动
- 模式识别
- 策略进化
- 知识迁移
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .base_neuron_agent import BaseNeuronAgent, AgentCapability, AgentDecision
from ..core.enums import AgentType

logger = logging.getLogger("LearningAgent")


@dataclass
class LearningExperience:
    """学习经验"""
    experience_id: str
    task: str
    approach: str
    outcome: str
    success: bool
    confidence: float
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class LearnedPattern:
    """学习到的模式"""
    pattern_id: str
    pattern_type: str
    description: str
    conditions: List[str]
    action: str
    success_rate: float
    sample_count: int
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


class LearningAgent(BaseNeuronAgent):
    """
    学习Agent - 学习适应
    
    触发条件: 需要学习/适应/优化
    适用场景: 技能学习、经验积累、策略优化、知识更新
    """

    def __init__(self, agent_id: str = "learning_agent"):
        capabilities = [
            AgentCapability(
                name="skill_learning",
                description="技能学习",
                confidence_threshold=0.5,
                avg_latency_ms=300.0
            ),
            AgentCapability(
                name="pattern_recognition",
                description="模式识别",
                confidence_threshold=0.6,
                avg_latency_ms=200.0
            ),
            AgentCapability(
                name="strategy_optimization",
                description="策略优化",
                confidence_threshold=0.4,
                avg_latency_ms=500.0
            ),
            AgentCapability(
                name="knowledge_transfer",
                description="知识迁移",
                confidence_threshold=0.5,
                avg_latency_ms=400.0
            ),
        ]
        super().__init__(agent_id, AgentType.LEARNING, capabilities)

        self._experiences: List[LearningExperience] = []
        self._learned_patterns: Dict[str, LearnedPattern] = {}
        self._strategy_scores: Dict[str, float] = {}
        self._max_experiences = 2000
        self._max_patterns = 500

    def can_handle(self, task: str, confidence: float) -> bool:
        """判断是否需要学习"""
        learn_keywords = ["学习", "优化", "改进", "适应", "训练",
                         "learn", "optimize", "improve", "adapt", "train"]
        if any(kw in task.lower() for kw in learn_keywords):
            return True

        if self._find_similar_experience(task) is not None:
            return True

        return False

    async def process(self, content: Dict[str, Any]) -> AgentDecision:
        """学习处理"""
        task = content.get("task", "")
        context = content.get("context", {})
        action = content.get("action", "learn")

        if action == "learn":
            return await self._learn(task, context)
        elif action == "apply_experience":
            return await self._apply_experience(task, context)
        elif action == "optimize_strategy":
            return await self._optimize_strategy(task, context)
        elif action == "record_outcome":
            return await self._record_outcome(content)
        else:
            return await self._learn(task, context)

    async def _learn(self, task: str, context: Dict[str, Any]) -> AgentDecision:
        """学习新经验"""
        import uuid

        similar = self._find_similar_experience(task)

        if similar:
            approach = f"基于历史经验: {similar.approach}"
            confidence = similar.confidence * 0.9
        else:
            approach = "探索性学习"
            confidence = 0.3

        experience = LearningExperience(
            experience_id=f"exp_{uuid.uuid4().hex[:12]}",
            task=task,
            approach=approach,
            outcome="学习中",
            success=False,
            confidence=confidence,
            context=context
        )
        self._add_experience(experience)

        self._extract_pattern(task, approach, context)

        return AgentDecision(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            action="learn",
            confidence=confidence,
            reasoning=f"学习模式: {approach}" + (f" (相似经验: {similar.experience_id})" if similar else ""),
            evidence=[
                {"source": "experience", "id": experience.experience_id},
                {"source": "similar_experience", "found": similar is not None}
            ],
            metadata={
                "experience_id": experience.experience_id,
                "approach": approach,
                "patterns_learned": len(self._learned_patterns)
            }
        )

    async def _apply_experience(self, task: str, context: Dict[str, Any]) -> AgentDecision:
        """应用历史经验"""
        similar = self._find_similar_experience(task)

        if similar and similar.success:
            return AgentDecision(
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                action=similar.approach,
                confidence=similar.confidence,
                reasoning=f"复用成功经验: {similar.experience_id}",
                evidence=[
                    {"source": "past_experience", "id": similar.experience_id,
                     "success_rate": similar.confidence}
                ]
            )

        return AgentDecision(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            action="no_applicable_experience",
            confidence=0.2,
            reasoning="无适用历史经验，建议探索性学习"
        )

    async def _optimize_strategy(self, task: str, context: Dict[str, Any]) -> AgentDecision:
        """优化策略"""
        strategy_name = context.get("strategy", "default")

        current_score = self._strategy_scores.get(strategy_name, 0.5)

        related_experiences = [
            e for e in self._experiences
            if strategy_name in e.approach or strategy_name in e.task
        ]

        if related_experiences:
            success_rate = sum(1 for e in related_experiences if e.success) / len(related_experiences)
            new_score = current_score * 0.7 + success_rate * 0.3
        else:
            new_score = current_score

        self._strategy_scores[strategy_name] = new_score

        return AgentDecision(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            action="strategy_optimized",
            confidence=new_score,
            reasoning=f"策略 '{strategy_name}' 评分: {current_score:.2f} → {new_score:.2f}",
            evidence=[
                {"source": "strategy_score", "before": current_score, "after": new_score},
                {"source": "related_experiences", "count": len(related_experiences)}
            ]
        )

    async def _record_outcome(self, content: Dict[str, Any]) -> AgentDecision:
        """记录结果"""
        experience_id = content.get("experience_id")
        success = content.get("success", False)
        outcome = content.get("outcome", "")

        for exp in self._experiences:
            if exp.experience_id == experience_id:
                exp.success = success
                exp.outcome = outcome
                if success:
                    exp.confidence = min(exp.confidence + 0.1, 1.0)
                else:
                    exp.confidence = max(exp.confidence - 0.1, 0.0)
                break

        return AgentDecision(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            action="outcome_recorded",
            confidence=0.9,
            reasoning=f"经验 {experience_id} 结果已记录: {'成功' if success else '失败'}"
        )

    def _find_similar_experience(self, task: str) -> Optional[LearningExperience]:
        """查找相似经验"""
        task_lower = task.lower()
        best_match = None
        best_score = 0.0

        for exp in self._experiences:
            if not exp.success:
                continue

            score = 0.0
            exp_lower = exp.task.lower()

            for word in task_lower.split():
                if word in exp_lower:
                    score += 0.3

            common_len = len(set(task_lower) & set(exp_lower))
            total_len = len(set(task_lower) | set(exp_lower))
            if total_len > 0:
                score += (common_len / total_len) * 0.7

            if score > best_score and score > 0.3:
                best_score = score
                best_match = exp

        return best_match

    def _extract_pattern(self, task: str, approach: str, context: Dict[str, Any]):
        """提取模式"""
        import uuid

        conditions = []
        for key in ["task_type", "complexity", "domain"]:
            if key in context:
                conditions.append(f"{key}={context[key]}")

        pattern_key = f"{approach}:{':'.join(conditions)}"

        if pattern_key in self._learned_patterns:
            pattern = self._learned_patterns[pattern_key]
            pattern.sample_count += 1
        else:
            if len(self._learned_patterns) >= self._max_patterns:
                oldest_key = next(iter(self._learned_patterns))
                del self._learned_patterns[oldest_key]

            self._learned_patterns[pattern_key] = LearnedPattern(
                pattern_id=f"pat_{uuid.uuid4().hex[:8]}",
                pattern_type="experience_based",
                description=f"从任务 '{task[:30]}' 提取",
                conditions=conditions,
                action=approach,
                success_rate=0.5,
                sample_count=1
            )

    def _add_experience(self, experience: LearningExperience):
        """添加经验"""
        self._experiences.append(experience)
        if len(self._experiences) > self._max_experiences:
            self._experiences = self._experiences[-self._max_experiences:]

    def get_learning_stats(self) -> Dict[str, Any]:
        """获取学习统计"""
        total = len(self._experiences)
        successful = sum(1 for e in self._experiences if e.success)

        return {
            "total_experiences": total,
            "successful_experiences": successful,
            "success_rate": successful / max(total, 1),
            "learned_patterns": len(self._learned_patterns),
            "strategy_scores": dict(self._strategy_scores),
            "top_patterns": [
                {
                    "id": p.pattern_id,
                    "description": p.description[:50],
                    "success_rate": p.success_rate,
                    "sample_count": p.sample_count
                }
                for p in sorted(
                    self._learned_patterns.values(),
                    key=lambda x: x.sample_count,
                    reverse=True
                )[:10]
            ]
        }
