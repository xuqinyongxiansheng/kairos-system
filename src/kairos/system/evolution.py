"""
进化系统
追踪和管理系统进化
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型"""
    CAPABILITY_IMPROVEMENT = "capability_improvement"
    SKILL_ACQUIRED = "skill_acquired"
    KNOWLEDGE_ADDED = "knowledge_added"
    MILESTONE_REACHED = "milestone_reached"


@dataclass
class EvolutionEvent:
    """进化事件"""
    id: str
    event_type: str
    title: str
    description: str
    timestamp: str
    metrics: Dict[str, float] = None
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class EvolutionMilestone:
    """进化里程碑"""
    id: str
    name: str
    description: str
    target_value: float
    current_value: float
    status: str = "pending"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class EvolutionTracker:
    """进化追踪器"""
    
    def __init__(self):
        self.events = []
        self.milestones = {}
        self.capabilities = {}
        self.next_id = 1
    
    async def record_event(self, event_type: EventType, title: str,
                          description: str, metrics: Dict[str, float] = None) -> Dict[str, Any]:
        """记录进化事件"""
        event_id = f"event_{self.next_id}"
        self.next_id += 1
        
        event = EvolutionEvent(
            id=event_id,
            event_type=event_type.value,
            title=title,
            description=description,
            timestamp=datetime.now().isoformat(),
            metrics=metrics or {}
        )
        
        self.events.append(event)
        
        if metrics:
            for key, value in metrics.items():
                if key not in self.capabilities:
                    self.capabilities[key] = []
                self.capabilities[key].append({
                    'value': value,
                    'timestamp': event.timestamp
                })
        
        logger.info(f"进化事件记录：{title}")
        
        return {
            'status': 'success',
            'event_id': event_id,
            'event': event.to_dict()
        }
    
    async def add_milestone(self, name: str, description: str,
                           target_value: float) -> Dict[str, Any]:
        """添加里程碑"""
        milestone_id = f"milestone_{len(self.milestones) + 1}"
        
        milestone = EvolutionMilestone(
            id=milestone_id,
            name=name,
            description=description,
            target_value=target_value,
            current_value=0
        )
        
        self.milestones[milestone_id] = milestone
        
        logger.info(f"里程碑添加：{name}")
        
        return {
            'status': 'success',
            'milestone_id': milestone_id,
            'milestone': milestone.to_dict()
        }
    
    async def update_milestone_progress(self, milestone_id: str,
                                       current_value: float) -> Dict[str, Any]:
        """更新里程碑进度"""
        if milestone_id not in self.milestones:
            return {
                'status': 'not_found',
                'message': f'里程碑不存在：{milestone_id}'
            }
        
        milestone = self.milestones[milestone_id]
        milestone.current_value = current_value
        
        if current_value >= milestone.target_value:
            milestone.status = "achieved"
        
        logger.info(f"里程碑进度更新：{milestone.name} - {current_value}/{milestone.target_value}")
        
        return {
            'status': 'success',
            'milestone': milestone.to_dict()
        }
    
    async def get_evolution_events(self, limit: int = 10) -> Dict[str, Any]:
        """获取进化事件"""
        return {
            'status': 'success',
            'events': [e.to_dict() for e in self.events[-limit:]],
            'count': len(self.events)
        }
    
    async def get_milestones(self) -> Dict[str, Any]:
        """获取里程碑"""
        return {
            'status': 'success',
            'milestones': [m.to_dict() for m in self.milestones.values()],
            'count': len(self.milestones)
        }
    
    async def get_capability_trend(self, capability: str) -> Dict[str, Any]:
        """获取能力趋势"""
        if capability not in self.capabilities:
            return {
                'status': 'not_found',
                'message': f'能力不存在：{capability}'
            }
        
        return {
            'status': 'success',
            'capability': capability,
            'trend': self.capabilities[capability]
        }
    
    async def get_evolution_summary(self) -> Dict[str, Any]:
        """获取进化摘要"""
        achieved_milestones = sum(
            1 for m in self.milestones.values() if m.status == 'achieved'
        )
        
        return {
            'status': 'success',
            'total_events': len(self.events),
            'total_milestones': len(self.milestones),
            'achieved_milestones': achieved_milestones,
            'capabilities_tracked': len(self.capabilities)
        }


# ============================================================
# 自进化引擎扩展（增强型设计开发.md 需求）
# 新增：经验提取、知识蒸馏、策略优化
# ============================================================

import time
import json
from collections import defaultdict


class SelfEvolutionEngine:
    """自进化引擎：持续学习、经验沉淀、策略优化

    核心能力：
    1. 经验提取：从任务执行结果中提取经验教训
    2. 知识蒸馏：将高频经验压缩为规则
    3. 策略优化：根据历史表现调整决策参数
    4. 能力评估：量化评估各维度能力水平
    """

    def __init__(self, tracker: EvolutionTracker = None, memory_system=None):
        self.tracker = tracker or EvolutionTracker()
        self.memory = memory_system
        self._experience_pool: List[Dict[str, Any]] = []
        self._distilled_rules: Dict[str, Dict[str, Any]] = {}
        self._strategy_params: Dict[str, float] = {
            "exploration_rate": 0.3,
            "learning_rate": 0.1,
            "forgetting_rate": 0.01,
            "consolidation_threshold": 3
        }
        self._capability_scores: Dict[str, List[float]] = defaultdict(list)
        self._stats = {
            "experiences_processed": 0,
            "rules_distilled": 0,
            "strategies_optimized": 0
        }

    async def learn_from_experience(
        self,
        task: str,
        result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """从经验中学习

        Args:
            task: 任务描述
            result: 执行结果
            context: 上下文

        Returns:
            学习结果
        """
        success = result.get("success", result.get("status") == "completed")
        lessons = result.get("lessons", [])

        experience = {
            "id": f"exp_{int(time.time() * 1000)}",
            "task": task,
            "success": success,
            "lessons": lessons,
            "context": context or {},
            "timestamp": time.time()
        }

        self._experience_pool.append(experience)
        self._stats["experiences_processed"] += 1

        # 更新能力评分
        domain = self._classify_domain(task)
        score = 1.0 if success else 0.0
        self._capability_scores[domain].append(score)

        # 记录进化事件
        if self.tracker:
            event_type = EventType.SKILL_ACQUIRED if success else EventType.CAPABILITY_IMPROVEMENT
            await self.tracker.record_event(
                event_type=event_type,
                title=f"{'成功' if success else '失败'}经验: {task[:40]}",
                description=f"经验教训: {'; '.join(lessons[:3])}" if lessons else "无特殊教训",
                metrics={domain: score}
            )

        # 检查是否需要知识蒸馏
        if len(self._experience_pool) >= self._strategy_params["consolidation_threshold"] * 5:
            await self._distill_knowledge()

        # 存储到记忆系统
        if self.memory:
            try:
                if hasattr(self.memory, 'store'):
                    self.memory.store(
                        content=json.dumps(experience, ensure_ascii=False),
                        layer="long_term",
                        tags=["experience", domain, "success" if success else "failure"]
                    )
            except Exception:
                pass

        return {
            "experience_id": experience["id"],
            "domain": domain,
            "learned": True,
            "total_experiences": len(self._experience_pool)
        }

    async def _distill_knowledge(self):
        """知识蒸馏：将高频经验压缩为规则"""
        domain_experiences = defaultdict(list)
        for exp in self._experience_pool:
            domain = self._classify_domain(exp["task"])
            domain_experiences[domain].append(exp)

        new_rules = 0
        for domain, experiences in domain_experiences.items():
            success_rate = sum(1 for e in experiences if e["success"]) / max(len(experiences), 1)

            if len(experiences) >= self._strategy_params["consolidation_threshold"]:
                all_lessons = []
                for e in experiences:
                    all_lessons.extend(e.get("lessons", []))

                lesson_freq = defaultdict(int)
                for lesson in all_lessons:
                    lesson_freq[lesson] += 1

                top_lessons = sorted(lesson_freq.items(), key=lambda x: -x[1])[:5]

                rule_id = f"rule_{domain}_{len(self._distilled_rules)}"
                self._distilled_rules[rule_id] = {
                    "domain": domain,
                    "success_rate": round(success_rate, 2),
                    "sample_count": len(experiences),
                    "top_lessons": [l[0] for l in top_lessons],
                    "created_at": time.time()
                }
                new_rules += 1

        self._stats["rules_distilled"] += new_rules
        if new_rules > 0:
            logger.info("知识蒸馏完成，新增 %d 条规则", new_rules)

    async def optimize_strategy(self) -> Dict[str, Any]:
        """策略优化：根据历史表现调整参数"""
        optimizations = {}

        for domain, scores in self._capability_scores.items():
            if len(scores) < 3:
                continue

            recent_avg = sum(scores[-5:]) / len(scores[-5:])
            overall_avg = sum(scores) / len(scores)

            if recent_avg > overall_avg:
                optimizations[domain] = {
                    "trend": "improving",
                    "recent_avg": round(recent_avg, 2),
                    "overall_avg": round(overall_avg, 2),
                    "action": "维持当前策略"
                }
            else:
                optimizations[domain] = {
                    "trend": "declining",
                    "recent_avg": round(recent_avg, 2),
                    "overall_avg": round(overall_avg, 2),
                    "action": "增加探索率"
                }
                self._strategy_params["exploration_rate"] = min(
                    0.5, self._strategy_params["exploration_rate"] + 0.05
                )

        self._stats["strategies_optimized"] += 1

        return {
            "optimizations": optimizations,
            "current_params": dict(self._strategy_params)
        }

    def _classify_domain(self, task: str) -> str:
        """任务领域分类"""
        domain_keywords = {
            "coding": ["代码", "编程", "函数", "bug", "debug", "code"],
            "reasoning": ["推理", "分析", "逻辑", "思考", "判断"],
            "knowledge": ["知识", "查询", "搜索", "检索", "查找"],
            "planning": ["规划", "计划", "任务", "安排", "调度"],
            "communication": ["对话", "交流", "沟通", "回答", "提问"],
            "creation": ["生成", "创作", "设计", "写", "创建"]
        }

        task_lower = task.lower()
        for domain, keywords in domain_keywords.items():
            if any(kw in task_lower for kw in keywords):
                return domain
        return "general"

    def get_capability_report(self) -> Dict[str, Any]:
        """获取能力评估报告"""
        report = {}
        for domain, scores in self._capability_scores.items():
            if not scores:
                continue
            report[domain] = {
                "current_score": round(scores[-1], 2),
                "avg_score": round(sum(scores) / len(scores), 2),
                "trend": "improving" if len(scores) >= 2 and scores[-1] > scores[0] else "stable",
                "sample_count": len(scores)
            }
        return report

    def get_evolution_summary(self) -> Dict[str, Any]:
        """获取自进化摘要"""
        return {
            "stats": dict(self._stats),
            "strategy_params": dict(self._strategy_params),
            "distilled_rules_count": len(self._distilled_rules),
            "experience_pool_size": len(self._experience_pool),
            "capability_domains": list(self._capability_scores.keys())
        }

    def get_distilled_rules(self, domain: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """获取蒸馏规则"""
        rules = list(self._distilled_rules.values())
        if domain:
            rules = [r for r in rules if r.get("domain") == domain]
        return rules[:limit]


_evolution_engine_instance: Optional[SelfEvolutionEngine] = None


def get_evolution_engine() -> SelfEvolutionEngine:
    """获取自进化引擎单例"""
    global _evolution_engine_instance
    if _evolution_engine_instance is None:
        _evolution_engine_instance = SelfEvolutionEngine()
    return _evolution_engine_instance
