# -*- coding: utf-8 -*-
"""
自我进化模块 (Self-Evolution Engine)
Kairos 3.0 4b核心特性

特点:
- 能力自评估
- 策略自适应
- 知识自动积累
- 性能持续优化
- 进化轨迹追踪
"""

import math
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import time


class EvolutionPhase(Enum):
    """进化阶段"""
    ASSESSMENT = "assessment"
    PLANNING = "planning"
    ADAPTATION = "adaptation"
    VALIDATION = "validation"
    INTEGRATION = "integration"


class SkillLevel(Enum):
    """技能等级"""
    NOVICE = 1
    BEGINNER = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5


class AdaptationType(Enum):
    """适应类型"""
    PARAMETER_TUNING = "parameter_tuning"
    STRATEGY_SWITCH = "strategy_switch"
    KNOWLEDGE_ACQUISITION = "knowledge_acquisition"
    SKILL_IMPROVEMENT = "skill_improvement"
    ARCHITECTURE_CHANGE = "architecture_change"


@dataclass
class SkillProfile:
    """技能档案"""
    skill_name: str
    level: SkillLevel
    experience_points: int
    success_rate: float
    usage_count: int
    last_used: float
    improvement_areas: List[str] = field(default_factory=list)
    
    def add_experience(self, success: bool):
        """添加经验"""
        self.usage_count += 1
        self.experience_points += 10 if success else 2
        self.last_used = time.time()
        
        if success:
            self.success_rate = (self.success_rate * (self.usage_count - 1) + 1.0) / self.usage_count
        else:
            self.success_rate = (self.success_rate * (self.usage_count - 1)) / self.usage_count
        
        new_level = self._compute_level()
        if new_level.value > self.level.value:
            self.level = new_level
    
    def _compute_level(self) -> SkillLevel:
        """计算等级"""
        if self.experience_points >= 1000:
            return SkillLevel.EXPERT
        elif self.experience_points >= 500:
            return SkillLevel.ADVANCED
        elif self.experience_points >= 200:
            return SkillLevel.INTERMEDIATE
        elif self.experience_points >= 50:
            return SkillLevel.BEGINNER
        else:
            return SkillLevel.NOVICE
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'skill_name': self.skill_name,
            'level': self.level.value,
            'level_name': self.level.name,
            'experience_points': self.experience_points,
            'success_rate': self.success_rate,
            'usage_count': self.usage_count,
            'last_used': self.last_used,
            'improvement_areas': self.improvement_areas
        }


@dataclass
class AdaptationRecord:
    """适应记录"""
    adaptation_id: str
    adaptation_type: AdaptationType
    description: str
    before_state: Dict[str, Any]
    after_state: Dict[str, Any]
    improvement_score: float
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'adaptation_id': self.adaptation_id,
            'adaptation_type': self.adaptation_type.value,
            'description': self.description,
            'before_state': self.before_state,
            'after_state': self.after_state,
            'improvement_score': self.improvement_score,
            'timestamp': self.timestamp
        }


@dataclass
class EvolutionCheckpoint:
    """进化检查点"""
    checkpoint_id: str
    timestamp: float
    skill_profiles: Dict[str, Dict[str, Any]]
    performance_metrics: Dict[str, float]
    adaptations_count: int
    phase: EvolutionPhase
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'checkpoint_id': self.checkpoint_id,
            'timestamp': self.timestamp,
            'skill_profiles': self.skill_profiles,
            'performance_metrics': self.performance_metrics,
            'adaptations_count': self.adaptations_count,
            'phase': self.phase.value
        }


class SelfEvolutionEngine:
    """
    自我进化引擎
    
    核心功能:
    - 能力自评估
    - 策略自适应
    - 知识自动积累
    - 性能持续优化
    - 进化轨迹追踪
    """
    
    def __init__(self):
        self.skills: Dict[str, SkillProfile] = {}
        self.adaptations: List[AdaptationRecord] = []
        self.checkpoints: List[EvolutionCheckpoint] = []
        self.performance_history: deque = deque(maxlen=1000)
        
        self._current_phase = EvolutionPhase.ASSESSMENT
        self._adaptation_counter = 0
        self._checkpoint_counter = 0
        
        self._parameter_store: Dict[str, Any] = {}
        self._strategy_store: Dict[str, Callable] = {}
        self._knowledge_store: Dict[str, Dict[str, Any]] = {}
    
    def register_skill(
        self,
        skill_name: str,
        initial_level: SkillLevel = SkillLevel.NOVICE
    ):
        """注册技能"""
        self.skills[skill_name] = SkillProfile(
            skill_name=skill_name,
            level=initial_level,
            experience_points=0,
            success_rate=0.5,
            usage_count=0,
            last_used=time.time()
        )
    
    def record_performance(
        self,
        skill_name: str,
        success: bool,
        execution_time_ms: float = 0,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        记录性能
        
        Args:
            skill_name: 技能名称
            success: 是否成功
            execution_time_ms: 执行时间
            context: 上下文
            
        Returns:
            记录结果
        """
        if skill_name not in self.skills:
            self.register_skill(skill_name)
        
        skill = self.skills[skill_name]
        old_level = skill.level
        skill.add_experience(success)
        
        self.performance_history.append({
            'skill': skill_name,
            'success': success,
            'execution_time_ms': execution_time_ms,
            'timestamp': time.time(),
            'context': context or {}
        })
        
        result = {
            'skill': skill_name,
            'success': success,
            'level_before': old_level.name,
            'level_after': skill.level.name,
            'level_up': skill.level.value > old_level.value,
            'success_rate': skill.success_rate,
            'experience_points': skill.experience_points
        }
        
        if skill.level.value > old_level.value:
            self._on_level_up(skill_name, old_level, skill.level)
        
        return result
    
    def _on_level_up(self, skill_name: str, old_level: SkillLevel, new_level: SkillLevel):
        """等级提升处理"""
        self._adaptation_counter += 1
        
        adaptation = AdaptationRecord(
            adaptation_id=f"adapt_{self._adaptation_counter}",
            adaptation_type=AdaptationType.SKILL_IMPROVEMENT,
            description=f"技能 {skill_name} 从 {old_level.name} 提升到 {new_level.name}",
            before_state={'level': old_level.value},
            after_state={'level': new_level.value},
            improvement_score=new_level.value - old_level.value,
            timestamp=time.time()
        )
        
        self.adaptations.append(adaptation)
    
    def assess_capabilities(self) -> Dict[str, Any]:
        """
        评估当前能力
        
        Returns:
            能力评估结果
        """
        self._current_phase = EvolutionPhase.ASSESSMENT
        
        assessment = {
            'total_skills': len(self.skills),
            'skill_levels': {},
            'weak_areas': [],
            'strong_areas': [],
            'overall_score': 0.0
        }
        
        total_score = 0
        for name, skill in self.skills.items():
            assessment['skill_levels'][name] = skill.to_dict()
            
            score = skill.level.value * 0.4 + skill.success_rate * 0.6
            total_score += score
            
            if skill.success_rate < 0.5:
                assessment['weak_areas'].append({
                    'skill': name,
                    'success_rate': skill.success_rate,
                    'level': skill.level.name
                })
            elif skill.success_rate > 0.8 and skill.level.value >= SkillLevel.INTERMEDIATE.value:
                assessment['strong_areas'].append({
                    'skill': name,
                    'success_rate': skill.success_rate,
                    'level': skill.level.name
                })
        
        assessment['overall_score'] = total_score / len(self.skills) if self.skills else 0
        
        return assessment
    
    def plan_adaptation(self, assessment: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        规划适应策略
        
        Args:
            assessment: 能力评估结果
            
        Returns:
            适应计划
        """
        self._current_phase = EvolutionPhase.PLANNING
        
        if assessment is None:
            assessment = self.assess_capabilities()
        
        plan = {
            'adaptations': [],
            'priority': 'medium',
            'estimated_improvement': 0.0
        }
        
        for weak_area in assessment.get('weak_areas', []):
            skill_name = weak_area['skill']
            skill = self.skills.get(skill_name)
            
            if not skill:
                continue
            
            if skill.success_rate < 0.3:
                adaptation = {
                    'type': AdaptationType.STRATEGY_SWITCH.value,
                    'skill': skill_name,
                    'action': f"切换 {skill_name} 的执行策略",
                    'priority': 'high'
                }
            else:
                adaptation = {
                    'type': AdaptationType.PARAMETER_TUNING.value,
                    'skill': skill_name,
                    'action': f"调整 {skill_name} 的参数",
                    'priority': 'medium'
                }
            
            plan['adaptations'].append(adaptation)
        
        if not assessment.get('weak_areas'):
            for strong_area in assessment.get('strong_areas', []):
                adaptation = {
                    'type': AdaptationType.KNOWLEDGE_ACQUISITION.value,
                    'skill': strong_area['skill'],
                    'action': f"扩展 {strong_area['skill']} 的知识范围",
                    'priority': 'low'
                }
                plan['adaptations'].append(adaptation)
        
        total_improvement = sum(0.1 for _ in plan['adaptations'])
        plan['estimated_improvement'] = min(1.0, total_improvement)
        
        if any(a['priority'] == 'high' for a in plan['adaptations']):
            plan['priority'] = 'high'
        elif any(a['priority'] == 'medium' for a in plan['adaptations']):
            plan['priority'] = 'medium'
        else:
            plan['priority'] = 'low'
        
        return plan
    
    def execute_adaptation(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行适应
        
        Args:
            plan: 适应计划
            
        Returns:
            执行结果
        """
        self._current_phase = EvolutionPhase.ADAPTATION
        
        results = []
        
        for adaptation in plan.get('adaptations', []):
            self._adaptation_counter += 1
            
            adaptation_type = AdaptationType(adaptation['type'])
            
            before_state = self._get_current_state(adaptation['skill'])
            
            improvement = self._apply_adaptation(adaptation)
            
            after_state = self._get_current_state(adaptation['skill'])
            
            record = AdaptationRecord(
                adaptation_id=f"adapt_{self._adaptation_counter}",
                adaptation_type=adaptation_type,
                description=adaptation['action'],
                before_state=before_state,
                after_state=after_state,
                improvement_score=improvement,
                timestamp=time.time()
            )
            
            self.adaptations.append(record)
            
            results.append({
                'adaptation_id': record.adaptation_id,
                'type': adaptation_type.value,
                'improvement': improvement,
                'success': improvement > 0
            })
        
        return {
            'total_adaptations': len(results),
            'successful': sum(1 for r in results if r['success']),
            'total_improvement': sum(r['improvement'] for r in results),
            'results': results
        }
    
    def _get_current_state(self, skill_name: str) -> Dict[str, Any]:
        """获取当前状态"""
        skill = self.skills.get(skill_name)
        if skill:
            return skill.to_dict()
        return {'skill': skill_name, 'status': 'unregistered'}
    
    def _apply_adaptation(self, adaptation: Dict[str, Any]) -> float:
        """应用适应"""
        skill_name = adaptation['skill']
        adaptation_type = AdaptationType(adaptation['type'])
        
        skill = self.skills.get(skill_name)
        if not skill:
            return 0.0
        
        improvement = 0.0
        
        if adaptation_type == AdaptationType.PARAMETER_TUNING:
            skill.success_rate = min(1.0, skill.success_rate + 0.05)
            improvement = 0.05
        
        elif adaptation_type == AdaptationType.STRATEGY_SWITCH:
            skill.success_rate = min(1.0, skill.success_rate + 0.1)
            improvement = 0.1
        
        elif adaptation_type == AdaptationType.KNOWLEDGE_ACQUISITION:
            skill.experience_points += 20
            improvement = 0.03
        
        elif adaptation_type == AdaptationType.SKILL_IMPROVEMENT:
            skill.experience_points += 50
            skill.success_rate = min(1.0, skill.success_rate + 0.08)
            improvement = 0.08
        
        return improvement
    
    def create_checkpoint(self) -> str:
        """
        创建进化检查点
        
        Returns:
            检查点ID
        """
        self._checkpoint_counter += 1
        checkpoint_id = f"checkpoint_{self._checkpoint_counter}"
        
        skill_profiles = {
            name: skill.to_dict() for name, skill in self.skills.items()
        }
        
        performance_metrics = self._compute_performance_metrics()
        
        checkpoint = EvolutionCheckpoint(
            checkpoint_id=checkpoint_id,
            timestamp=time.time(),
            skill_profiles=skill_profiles,
            performance_metrics=performance_metrics,
            adaptations_count=len(self.adaptations),
            phase=self._current_phase
        )
        
        self.checkpoints.append(checkpoint)
        
        return checkpoint_id
    
    def _compute_performance_metrics(self) -> Dict[str, float]:
        """计算性能指标"""
        if not self.performance_history:
            return {'avg_success_rate': 0, 'total_operations': 0}
        
        recent = list(self.performance_history)[-100:]
        
        success_rate = sum(1 for p in recent if p['success']) / len(recent)
        avg_time = sum(p['execution_time_ms'] for p in recent) / len(recent)
        
        return {
            'avg_success_rate': success_rate,
            'avg_execution_time_ms': avg_time,
            'total_operations': len(self.performance_history)
        }
    
    def get_evolution_trajectory(self) -> Dict[str, Any]:
        """
        获取进化轨迹
        
        Returns:
            进化轨迹
        """
        if not self.checkpoints:
            return {'trajectory': [], 'total_checkpoints': 0}
        
        trajectory = []
        for i, checkpoint in enumerate(self.checkpoints):
            trajectory.append({
                'checkpoint_id': checkpoint.checkpoint_id,
                'timestamp': checkpoint.timestamp,
                'overall_score': checkpoint.performance_metrics.get('avg_success_rate', 0),
                'skills_count': len(checkpoint.skill_profiles),
                'adaptations_count': checkpoint.adaptations_count,
                'phase': checkpoint.phase.value
            })
        
        improvement = 0
        if len(trajectory) >= 2:
            first_score = trajectory[0]['overall_score']
            last_score = trajectory[-1]['overall_score']
            improvement = last_score - first_score
        
        return {
            'trajectory': trajectory,
            'total_checkpoints': len(self.checkpoints),
            'total_adaptations': len(self.adaptations),
            'overall_improvement': improvement,
            'current_phase': self._current_phase.value
        }
    
    def get_evolution_statistics(self) -> Dict[str, Any]:
        """获取进化统计"""
        return {
            'total_skills': len(self.skills),
            'total_adaptations': len(self.adaptations),
            'total_checkpoints': len(self.checkpoints),
            'current_phase': self._current_phase.value,
            'performance_metrics': self._compute_performance_metrics(),
            'skill_summary': {
                name: {
                    'level': skill.level.name,
                    'success_rate': skill.success_rate,
                    'experience': skill.experience_points
                }
                for name, skill in self.skills.items()
            }
        }
    
    def auto_evolve(self) -> Dict[str, Any]:
        """
        自动进化一轮
        
        Returns:
            进化结果
        """
        assessment = self.assess_capabilities()
        plan = self.plan_adaptation(assessment)
        result = self.execute_adaptation(plan)
        checkpoint_id = self.create_checkpoint()
        
        return {
            'assessment': assessment,
            'plan': plan,
            'execution_result': result,
            'checkpoint_id': checkpoint_id,
            'phase': self._current_phase.value
        }
    
    def reset(self):
        """重置进化引擎"""
        self.skills.clear()
        self.adaptations.clear()
        self.checkpoints.clear()
        self.performance_history.clear()
        self._current_phase = EvolutionPhase.ASSESSMENT
        self._parameter_store.clear()
        self._strategy_store.clear()
        self._knowledge_store.clear()


def create_evolution_engine() -> SelfEvolutionEngine:
    """创建自我进化引擎实例"""
    return SelfEvolutionEngine()
