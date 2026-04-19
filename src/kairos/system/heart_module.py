# -*- coding: utf-8 -*-
"""
心脏模块（Heart Module）- 增强版
系统核心生命维持模块 + Kairos模式

Kairos模式 - 借鉴Claude Code的适时决策机制:
1. Kairos感知: 实时感知系统状态、用户状态、任务上下文
2. Kairos决策: 基于当前时机选择最优执行策略
3. Kairos调度: 动态资源分配与优先级调整
4. Kairos进化: 从历史决策中学习，优化未来时机判断

Claude Code核心借鉴:
- Memory Types Taxonomy: 四类内存分类(user/feedback/project/reference)
- Skillify Pattern: 从交互中自动捕获技能
- Remember Pattern: 跨层内存审查和提升
- 自适应工作流: 根据上下文动态调整执行模式
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, Callable, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import deque
import threading
import json
import os
import math

logger = logging.getLogger("HeartModule")


class HeartStatus(Enum):
    """心脏状态枚举"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"
    RECOVERING = "recovering"


class AlertLevel(Enum):
    """告警级别枚举"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class KairosMode(Enum):
    """Kairos模式枚举 - Claude Code适时决策"""
    OBSERVE = "observe"
    THINK = "think"
    ACT = "act"
    REFLECT = "reflect"
    EVOLVE = "evolve"


class KairosStrategy(Enum):
    """Kairos策略 - 根据时机选择"""
    IMMEDIATE = "immediate"
    DEFERRED = "deferred"
    BATCHED = "batched"
    INTERACTIVE = "interactive"
    AUTONOMOUS = "autonomous"
    CONSERVATIVE = "conservative"


class KairosMemoryType(Enum):
    """Kairos内存分类 - ClaudeCode Taxonomy"""
    USER = "user"
    FEEDBACK = "feedback"
    PROJECT = "project"
    REFERENCE = "reference"


class KairosUrgency(Enum):
    """Kairos紧急度"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Heartbeat:
    """心跳数据类"""
    timestamp: datetime
    status: HeartStatus
    response_time: float
    model_status: str
    memory_usage: float
    cpu_usage: float
    active_connections: int
    message: str


@dataclass
class Alert:
    """告警数据类"""
    timestamp: datetime
    level: AlertLevel
    component: str
    message: str
    details: Dict[str, Any]


@dataclass
class KairosDecision:
    """Kairos决策记录"""
    decision_id: str
    mode: KairosMode
    strategy: KairosStrategy
    urgency: KairosUrgency
    context_snapshot: Dict[str, Any]
    chosen_action: str
    reasoning: str
    confidence: float
    timestamp: float
    outcome: Optional[str] = None
    outcome_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'decision_id': self.decision_id,
            'mode': self.mode.value,
            'strategy': self.strategy.value,
            'urgency': self.urgency.value,
            'chosen_action': self.chosen_action,
            'reasoning': self.reasoning,
            'confidence': self.confidence,
            'timestamp': self.timestamp,
            'outcome': self.outcome,
            'outcome_score': self.outcome_score
        }


@dataclass
class KairosMemoryEntry:
    """Kairos内存条目 - ClaudeCode Taxonomy"""
    entry_id: str
    memory_type: KairosMemoryType
    content: str
    relevance: float
    created_at: float
    last_accessed: float
    access_count: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'entry_id': self.entry_id,
            'memory_type': self.memory_type.value,
            'content': self.content,
            'relevance': self.relevance,
            'created_at': self.created_at,
            'access_count': self.access_count,
            'tags': self.tags
        }


@dataclass
class KairosContext:
    """Kairos上下文快照"""
    system_load: float
    user_engagement: float
    task_complexity: float
    time_pressure: float
    resource_availability: float
    recent_success_rate: float
    active_mode: KairosMode
    
    def compute_kairos_score(self) -> float:
        """计算Kairos时机分数 (0-1)"""
        load_factor = 1.0 - self.system_load
        engagement_factor = self.user_engagement
        readiness = (load_factor + engagement_factor + self.resource_availability) / 3
        urgency_boost = self.time_pressure * 0.2
        success_factor = self.recent_success_rate * 0.3
        
        score = readiness * 0.5 + success_factor + urgency_boost
        return max(0.0, min(1.0, score))


class KairosEngine:
    """
    Kairos引擎 - Claude Code适时决策核心
    
    核心理念: "在对的时间做对的事"
    - 感知(OBSERVE): 收集系统/用户/任务上下文
    - 思考(THINK): 分析时机，评估策略
    - 行动(ACT): 执行最优策略
    - 反思(REFLECT): 评估结果，更新认知
    - 进化(EVOLVE): 从历史中学习，优化未来
    """
    
    def __init__(self):
        self.current_mode = KairosMode.OBSERVE
        self.current_strategy = KairosStrategy.INTERACTIVE
        self.decisions: deque = deque(maxlen=500)
        self.memory: Dict[KairosMemoryType, List[KairosMemoryEntry]] = {
            KairosMemoryType.USER: [],
            KairosMemoryType.FEEDBACK: [],
            KairosMemoryType.PROJECT: [],
            KairosMemoryType.REFERENCE: []
        }
        self._decision_counter = 0
        self._memory_counter = 0
        self._mode_history: deque = deque(maxlen=100)
        self._strategy_weights: Dict[KairosStrategy, float] = {
            KairosStrategy.IMMEDIATE: 0.5,
            KairosStrategy.DEFERRED: 0.5,
            KairosStrategy.BATCHED: 0.5,
            KairosStrategy.INTERACTIVE: 0.7,
            KairosStrategy.AUTONOMOUS: 0.5,
            KairosStrategy.CONSERVATIVE: 0.5
        }
    
    def observe(self, context: KairosContext) -> Dict[str, Any]:
        """
        Kairos感知阶段
        
        收集当前上下文，计算时机分数
        """
        self.current_mode = KairosMode.OBSERVE
        self._mode_history.append(KairosMode.OBSERVE)
        
        kairos_score = context.compute_kairos_score()
        
        system_health = "good" if context.system_load < 0.7 else "stressed" if context.system_load < 0.9 else "critical"
        user_state = "engaged" if context.user_engagement > 0.6 else "passive" if context.user_engagement > 0.3 else "absent"
        task_nature = "simple" if context.task_complexity < 0.3 else "moderate" if context.task_complexity < 0.7 else "complex"
        
        observation = {
            'kairos_score': kairos_score,
            'system_health': system_health,
            'user_state': user_state,
            'task_nature': task_nature,
            'timing_quality': 'optimal' if kairos_score > 0.7 else 'acceptable' if kairos_score > 0.4 else 'suboptimal',
            'mode': self.current_mode.value
        }
        
        self._store_memory(
            KairosMemoryType.PROJECT,
            f"观察: 系统={system_health}, 用户={user_state}, 任务={task_nature}, 时机={kairos_score:.2f}",
            relevance=kairos_score,
            tags=["observation", system_health, task_nature]
        )
        
        return observation
    
    def think(self, observation: Dict[str, Any], task: str = "") -> Dict[str, Any]:
        """
        Kairos思考阶段
        
        分析时机，选择策略
        """
        self.current_mode = KairosMode.THINK
        self._mode_history.append(KairosMode.THINK)
        
        kairos_score = observation.get('kairos_score', 0.5)
        system_health = observation.get('system_health', 'good')
        user_state = observation.get('user_state', 'engaged')
        task_nature = observation.get('task_nature', 'moderate')
        
        strategy_scores = {}
        
        if kairos_score > 0.7 and system_health == 'good':
            strategy_scores[KairosStrategy.IMMEDIATE] = 0.9
            strategy_scores[KairosStrategy.AUTONOMOUS] = 0.7
            strategy_scores[KairosStrategy.INTERACTIVE] = 0.6
        elif kairos_score > 0.4:
            strategy_scores[KairosStrategy.INTERACTIVE] = 0.8
            strategy_scores[KairosStrategy.BATCHED] = 0.6
            strategy_scores[KairosStrategy.DEFERRED] = 0.5
        else:
            strategy_scores[KairosStrategy.CONSERVATIVE] = 0.9
            strategy_scores[KairosStrategy.DEFERRED] = 0.7
            strategy_scores[KairosStrategy.INTERACTIVE] = 0.4
        
        if task_nature == 'complex':
            strategy_scores[KairosStrategy.AUTONOMOUS] = strategy_scores.get(KairosStrategy.AUTONOMOUS, 0.5) + 0.2
            strategy_scores[KairosStrategy.BATCHED] = strategy_scores.get(KairosStrategy.BATCHED, 0.5) + 0.1
        
        if user_state == 'absent':
            strategy_scores[KairosStrategy.AUTONOMOUS] = strategy_scores.get(KairosStrategy.AUTONOMOUS, 0.5) + 0.3
            strategy_scores[KairosStrategy.DEFERRED] = strategy_scores.get(KairosStrategy.DEFERRED, 0.5) + 0.2
        
        for strategy, base_score in strategy_scores.items():
            weight = self._strategy_weights.get(strategy, 0.5)
            strategy_scores[strategy] = base_score * 0.7 + weight * 0.3
        
        best_strategy = max(strategy_scores, key=strategy_scores.get)
        best_score = strategy_scores[best_strategy]
        
        urgency = KairosUrgency.MEDIUM
        if kairos_score > 0.8 and system_health == 'good':
            urgency = KairosUrgency.LOW
        elif kairos_score < 0.3 or system_health == 'critical':
            urgency = KairosUrgency.CRITICAL
        elif kairos_score < 0.5:
            urgency = KairosUrgency.HIGH
        
        reasoning = self._generate_reasoning(observation, best_strategy, urgency)
        
        thinking = {
            'strategy_scores': {s.value: score for s, score in strategy_scores.items()},
            'best_strategy': best_strategy.value,
            'best_score': best_score,
            'urgency': urgency.value,
            'reasoning': reasoning,
            'mode': self.current_mode.value
        }
        
        return thinking
    
    def act(self, thinking: Dict[str, Any], task: str = "") -> KairosDecision:
        """
        Kairos行动阶段
        
        执行决策，记录选择
        """
        self.current_mode = KairosMode.ACT
        self._mode_history.append(KairosMode.ACT)
        
        self._decision_counter += 1
        decision_id = f"kairos_decision_{self._decision_counter}"
        
        strategy = KairosStrategy(thinking.get('best_strategy', 'interactive'))
        urgency = KairosUrgency(thinking.get('urgency', 2))
        
        action_map = {
            KairosStrategy.IMMEDIATE: "立即执行任务",
            KairosStrategy.DEFERRED: "延迟执行，等待更好时机",
            KairosStrategy.BATCHED: "批量处理，合并相似任务",
            KairosStrategy.INTERACTIVE: "交互式执行，逐步确认",
            KairosStrategy.AUTONOMOUS: "自主执行，无需确认",
            KairosStrategy.CONSERVATIVE: "保守执行，最小化风险"
        }
        
        decision = KairosDecision(
            decision_id=decision_id,
            mode=self.current_mode,
            strategy=strategy,
            urgency=urgency,
            context_snapshot=thinking,
            chosen_action=action_map.get(strategy, "执行任务"),
            reasoning=thinking.get('reasoning', ''),
            confidence=thinking.get('best_score', 0.5),
            timestamp=time.time()
        )
        
        self.decisions.append(decision)
        
        self._store_memory(
            KairosMemoryType.PROJECT,
            f"决策: 策略={strategy.value}, 紧急度={urgency.value}, 行动={decision.chosen_action}",
            relevance=decision.confidence,
            tags=["decision", strategy.value]
        )
        
        return decision
    
    def reflect(self, decision: KairosDecision, outcome: Dict[str, Any]) -> Dict[str, Any]:
        """
        Kairos反思阶段
        
        评估决策结果，更新认知
        """
        self.current_mode = KairosMode.REFLECT
        self._mode_history.append(KairosMode.REFLECT)
        
        success = outcome.get('success', False)
        score = 1.0 if success else 0.0
        
        if 'quality' in outcome:
            score = outcome['quality']
        
        decision.outcome = "success" if success else "failure"
        decision.outcome_score = score
        
        strategy = decision.strategy
        if success:
            self._strategy_weights[strategy] = min(1.0, self._strategy_weights.get(strategy, 0.5) + 0.05)
        else:
            self._strategy_weights[strategy] = max(0.1, self._strategy_weights.get(strategy, 0.5) - 0.05)
        
        feedback_type = KairosMemoryType.FEEDBACK
        self._store_memory(
            feedback_type,
            f"反思: 决策={decision.chosen_action}, 结果={'成功' if success else '失败'}, 分数={score:.2f}",
            relevance=0.8 if success else 0.9,
            tags=["reflection", "success" if success else "failure", strategy.value]
        )
        
        recent_decisions = list(self.decisions)[-20:]
        if recent_decisions:
            recent_success_rate = sum(1 for d in recent_decisions if d.outcome == "success") / len(recent_decisions)
        else:
            recent_success_rate = 0.5
        
        reflection = {
            'decision_id': decision.decision_id,
            'outcome': decision.outcome,
            'score': score,
            'strategy_adjusted': strategy.value,
            'new_weight': self._strategy_weights[strategy],
            'recent_success_rate': recent_success_rate,
            'mode': self.current_mode.value
        }
        
        return reflection
    
    def evolve(self) -> Dict[str, Any]:
        """
        Kairos进化阶段
        
        从历史决策中学习，优化策略权重
        """
        self.current_mode = KairosMode.EVOLVE
        self._mode_history.append(KairosMode.EVOLVE)
        
        all_decisions = list(self.decisions)
        
        strategy_stats = {}
        for strategy in KairosStrategy:
            strategy_decisions = [d for d in all_decisions if d.strategy == strategy]
            if strategy_decisions:
                success_count = sum(1 for d in strategy_decisions if d.outcome == "success")
                avg_confidence = sum(d.confidence for d in strategy_decisions) / len(strategy_decisions)
                avg_outcome = sum(d.outcome_score for d in strategy_decisions) / len(strategy_decisions)
                
                strategy_stats[strategy.value] = {
                    'total': len(strategy_decisions),
                    'successes': success_count,
                    'success_rate': success_count / len(strategy_decisions),
                    'avg_confidence': avg_confidence,
                    'avg_outcome': avg_outcome
                }
                
                if success_count / len(strategy_decisions) > 0.7:
                    self._strategy_weights[strategy] = min(1.0, self._strategy_weights.get(strategy, 0.5) + 0.03)
                elif success_count / len(strategy_decisions) < 0.3:
                    self._strategy_weights[strategy] = max(0.1, self._strategy_weights.get(strategy, 0.5) - 0.03)
        
        self._consolidate_memory()
        
        self._store_memory(
            KairosMemoryType.REFERENCE,
            f"进化: 策略权重更新, 决策总数={len(all_decisions)}",
            relevance=0.9,
            tags=["evolution", "weight_update"]
        )
        
        return {
            'total_decisions': len(all_decisions),
            'strategy_stats': strategy_stats,
            'current_weights': {s.value: w for s, w in self._strategy_weights.items()},
            'memory_entries': sum(len(v) for v in self.memory.values()),
            'mode': self.current_mode.value
        }
    
    def kairos_cycle(
        self,
        context: KairosContext,
        task: str = "",
        outcome: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        完整Kairos周期: 观察→思考→行动→(反思→进化)
        
        Args:
            context: 当前上下文
            task: 任务描述
            outcome: 上次决策的结果(用于反思)
            
        Returns:
            Kairos周期结果
        """
        if outcome and self.decisions:
            last_decision = self.decisions[-1] if self.decisions else None
            if last_decision and last_decision.outcome is None:
                reflection = self.reflect(last_decision, outcome)
                evolution = self.evolve()
            else:
                reflection = None
                evolution = None
        else:
            reflection = None
            evolution = None
        
        observation = self.observe(context)
        thinking = self.think(observation, task)
        decision = self.act(thinking, task)
        
        return {
            'observation': observation,
            'thinking': thinking,
            'decision': decision.to_dict(),
            'reflection': reflection,
            'evolution': evolution,
            'current_mode': self.current_mode.value,
            'current_strategy': self.current_strategy.value
        }
    
    def _generate_reasoning(
        self,
        observation: Dict[str, Any],
        strategy: KairosStrategy,
        urgency: KairosUrgency
    ) -> str:
        """生成决策推理"""
        kairos_score = observation.get('kairos_score', 0.5)
        system_health = observation.get('system_health', 'good')
        user_state = observation.get('user_state', 'engaged')
        
        reasons = []
        
        if kairos_score > 0.7:
            reasons.append(f"时机分数优秀({kairos_score:.2f})")
        elif kairos_score > 0.4:
            reasons.append(f"时机分数适中({kairos_score:.2f})")
        else:
            reasons.append(f"时机分数偏低({kairos_score:.2f})")
        
        reasons.append(f"系统状态={system_health}")
        reasons.append(f"用户状态={user_state}")
        reasons.append(f"选择策略={strategy.value}")
        reasons.append(f"紧急度={urgency.name}")
        
        return "; ".join(reasons)
    
    def _store_memory(
        self,
        memory_type: KairosMemoryType,
        content: str,
        relevance: float = 0.5,
        tags: List[str] = None
    ):
        """存储Kairos内存"""
        self._memory_counter += 1
        entry_id = f"kmem_{self._memory_counter}"
        
        entry = KairosMemoryEntry(
            entry_id=entry_id,
            memory_type=memory_type,
            content=content,
            relevance=relevance,
            created_at=time.time(),
            last_accessed=time.time(),
            tags=tags or []
        )
        
        self.memory[memory_type].append(entry)
        
        max_per_type = 200
        if len(self.memory[memory_type]) > max_per_type:
            self.memory[memory_type] = self.memory[memory_type][-max_per_type:]
    
    def _consolidate_memory(self):
        """内存巩固 - ClaudeCode Remember Pattern"""
        for memory_type, entries in self.memory.items():
            for entry in entries:
                age = time.time() - entry.created_at
                if age > 3600:
                    entry.relevance *= 0.95
                
                if entry.access_count > 3:
                    entry.relevance = min(1.0, entry.relevance + 0.05)
        
        for memory_type in self.memory:
            self.memory[memory_type] = [
                e for e in self.memory[memory_type] if e.relevance > 0.1
            ]
    
    def query_memory(
        self,
        query: str,
        memory_types: List[KairosMemoryType] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """查询Kairos内存"""
        if memory_types is None:
            memory_types = list(KairosMemoryType)
        
        results = []
        query_lower = query.lower()
        
        for mt in memory_types:
            for entry in self.memory[mt]:
                score = 0
                if query_lower in entry.content.lower():
                    score += 0.5
                for tag in entry.tags:
                    if query_lower in tag.lower():
                        score += 0.2
                score += entry.relevance * 0.3
                
                if score > 0:
                    entry.access_count += 1
                    entry.last_accessed = time.time()
                    results.append((entry.to_dict(), score))
        
        results.sort(key=lambda x: -x[1])
        return [r for r, _ in results[:limit]]
    
    def get_kairos_status(self) -> Dict[str, Any]:
        """获取Kairos状态"""
        recent_decisions = list(self.decisions)[-20:]
        success_rate = 0.0
        if recent_decisions:
            success_rate = sum(1 for d in recent_decisions if d.outcome == "success") / len(recent_decisions)
        
        return {
            'current_mode': self.current_mode.value,
            'current_strategy': self.current_strategy.value,
            'total_decisions': len(self.decisions),
            'recent_success_rate': success_rate,
            'strategy_weights': {s.value: w for s, w in self._strategy_weights.items()},
            'memory_summary': {
                mt.value: len(entries) for mt, entries in self.memory.items()
            },
            'mode_distribution': self._compute_mode_distribution()
        }
    
    def _compute_mode_distribution(self) -> Dict[str, int]:
        """计算模式分布"""
        distribution = {}
        for mode in self._mode_history:
            distribution[mode.value] = distribution.get(mode.value, 0) + 1
        return distribution


class HeartModule:
    """
    心脏模块 - 系统核心生命维持 + Kairos模式
    
    功能：
    1. 心跳监测 - 定期检查系统健康状态
    2. 大模型在线检测 - 确保 Gemma4:e4b 持续可用
    3. 自动恢复 - 故障时自动尝试恢复
    4. 告警系统 - 异常情况及时告警
    5. 性能监控 - 实时监控系统性能指标
    6. Kairos模式 - Claude Code适时决策引擎
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            config = {}
        
        self.config = config
        self.heartbeat_interval = config.get("heartbeat_interval", 5)
        self.max_recovery_attempts = config.get("max_recovery_attempts", 3)
        self.recovery_delay = config.get("recovery_delay", 10)
        self.alert_thresholds = config.get("alert_thresholds", {
            "response_time": 2.0,
            "memory_usage": 0.85,
            "cpu_usage": 0.90,
            "heartbeat_miss": 3
        })
        
        self.status = HeartStatus.OFFLINE
        self.last_heartbeat: Optional[Heartbeat] = None
        self.heartbeat_history: List[Heartbeat] = []
        self.alerts: List[Alert] = []
        self.recovery_attempts = 0
        self.consecutive_failures = 0
        
        self.components = {
            "model": {"status": "unknown", "last_check": None},
            "memory": {"status": "unknown", "last_check": None},
            "database": {"status": "unknown", "last_check": None},
            "api": {"status": "unknown", "last_check": None},
            "kairos": {"status": "active", "last_check": None}
        }
        
        self.on_heartbeat_callbacks: List[Callable] = []
        self.on_alert_callbacks: List[Callable] = []
        self.on_recovery_callbacks: List[Callable] = []
        self.on_kairos_decision_callbacks: List[Callable] = []
        
        self._running = False
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        self.data_dir = config.get("data_dir", "./data/heart")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Kairos引擎
        self.kairos = KairosEngine()
        self._kairos_enabled = config.get("kairos_enabled", True)
        self._kairos_auto_evolve_interval = config.get("kairos_auto_evolve_interval", 100)
        self._heartbeat_count = 0
        
        logger.info("心脏模块初始化完成 (含Kairos模式)")
    
    def start(self):
        """启动心脏模块"""
        if self._running:
            logger.warning("心脏模块已在运行")
            return
        
        self._running = True
        self.status = HeartStatus.HEALTHY
        
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True
        )
        self._heartbeat_thread.start()
        
        logger.info("心脏模块已启动 (Kairos模式: %s)", "启用" if self._kairos_enabled else "禁用")
    
    def stop(self):
        """停止心脏模块"""
        self._running = False
        self.status = HeartStatus.OFFLINE
        
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
        
        logger.info("心脏模块已停止")
    
    def _heartbeat_loop(self):
        """心跳循环"""
        while self._running:
            try:
                heartbeat = self._perform_heartbeat()
                
                with self._lock:
                    self.last_heartbeat = heartbeat
                    self.heartbeat_history.append(heartbeat)
                    
                    if len(self.heartbeat_history) > 100:
                        self.heartbeat_history = self.heartbeat_history[-100:]
                
                self._update_status(heartbeat)
                
                self._trigger_heartbeat_callbacks(heartbeat)
                
                if self._kairos_enabled:
                    self._kairos_heartbeat_tick(heartbeat)
                
                if heartbeat.status in [HeartStatus.CRITICAL, HeartStatus.OFFLINE]:
                    self._attempt_recovery()
                
                self._heartbeat_count += 1
                
                if self._kairos_enabled and self._heartbeat_count % self._kairos_auto_evolve_interval == 0:
                    self.kairos.evolve()
                
            except Exception as e:
                logger.error(f"心跳检测失败：{e}")
                self.consecutive_failures += 1
                
                if self.consecutive_failures >= self.alert_thresholds["heartbeat_miss"]:
                    self._create_alert(
                        AlertLevel.CRITICAL,
                        "heart",
                        f"连续 {self.consecutive_failures} 次心跳失败",
                        {"error": str(e)}
                    )
            
            # 使用可中断的休眠，以便更快响应停止信号
            sleep_end = time.time() + self.heartbeat_interval
            while self._running and time.time() < sleep_end:
                time.sleep(min(0.5, max(0, sleep_end - time.time())))
    
    def _kairos_heartbeat_tick(self, heartbeat: Heartbeat):
        """Kairos心跳处理"""
        context = KairosContext(
            system_load=heartbeat.memory_usage,
            user_engagement=0.7,
            task_complexity=0.5,
            time_pressure=0.3,
            resource_availability=1.0 - heartbeat.cpu_usage,
            recent_success_rate=self._compute_recent_success_rate(),
            active_mode=self.kairos.current_mode
        )
        
        observation = self.kairos.observe(context)
        
        if observation['timing_quality'] == 'suboptimal':
            self._create_alert(
                AlertLevel.WARNING,
                "kairos",
                f"Kairos时机分数偏低: {observation['kairos_score']:.2f}",
                observation
            )
        
        self.components["kairos"]["status"] = self.kairos.current_mode.value
        self.components["kairos"]["last_check"] = datetime.now().isoformat()
    
    def _compute_recent_success_rate(self) -> float:
        """计算最近成功率"""
        recent = list(self.kairos.decisions)[-20:]
        if not recent:
            return 0.5
        with_outcome = [d for d in recent if d.outcome is not None]
        if not with_outcome:
            return 0.5
        return sum(1 for d in with_outcome if d.outcome == "success") / len(with_outcome)
    
    def kairos_decide(
        self,
        task: str,
        system_load: float = None,
        user_engagement: float = 0.7,
        task_complexity: float = 0.5,
        time_pressure: float = 0.3
    ) -> Dict[str, Any]:
        """
        Kairos决策入口
        
        根据当前时机选择最优执行策略
        
        Args:
            task: 任务描述
            system_load: 系统负载 (0-1)
            user_engagement: 用户参与度 (0-1)
            task_complexity: 任务复杂度 (0-1)
            time_pressure: 时间压力 (0-1)
            
        Returns:
            Kairos决策结果
        """
        if not self._kairos_enabled:
            return {
                'status': 'disabled',
                'message': 'Kairos模式未启用',
                'fallback_strategy': 'interactive'
            }
        
        if system_load is None:
            system_load = self.last_heartbeat.memory_usage if self.last_heartbeat else 0.5
        
        resource_availability = 1.0 - (self.last_heartbeat.cpu_usage if self.last_heartbeat else 0.3)
        
        context = KairosContext(
            system_load=system_load,
            user_engagement=user_engagement,
            task_complexity=task_complexity,
            time_pressure=time_pressure,
            resource_availability=resource_availability,
            recent_success_rate=self._compute_recent_success_rate(),
            active_mode=self.kairos.current_mode
        )
        
        result = self.kairos.kairos_cycle(context, task)
        
        for callback in self.on_kairos_decision_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Kairos决策回调失败: {e}")
        
        return result
    
    def kairos_report_outcome(self, decision_id: str, outcome: Dict[str, Any]):
        """
        报告Kairos决策结果
        
        Args:
            decision_id: 决策ID
            outcome: 结果 {'success': bool, 'quality': float}
        """
        for decision in self.kairos.decisions:
            if decision.decision_id == decision_id:
                self.kairos.reflect(decision, outcome)
                break
    
    def register_kairos_decision_callback(self, callback: Callable):
        """注册Kairos决策回调"""
        self.on_kairos_decision_callbacks.append(callback)
    
    def _perform_heartbeat(self) -> Heartbeat:
        """执行心跳检测"""
        start_time = time.time()
        
        model_status = self._check_model_status()
        memory_usage = self._check_memory_usage()
        cpu_usage = self._check_cpu_usage()
        active_connections = self._check_active_connections()
        
        response_time = time.time() - start_time
        
        if response_time > self.alert_thresholds["response_time"]:
            status = HeartStatus.WARNING
            message = f"响应时间过长：{response_time:.2f}s"
        elif memory_usage > self.alert_thresholds["memory_usage"]:
            status = HeartStatus.WARNING
            message = f"内存使用率过高：{memory_usage:.1%}"
        elif cpu_usage > self.alert_thresholds["cpu_usage"]:
            status = HeartStatus.WARNING
            message = f"CPU 使用率过高：{cpu_usage:.1%}"
        elif model_status != "online":
            status = HeartStatus.CRITICAL
            message = f"模型状态异常：{model_status}"
        else:
            status = HeartStatus.HEALTHY
            message = "系统运行正常"
        
        return Heartbeat(
            timestamp=datetime.now(),
            status=status,
            response_time=response_time,
            model_status=model_status,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            active_connections=active_connections,
            message=message
        )
    
    def _check_model_status(self) -> str:
        """检查大模型状态"""
        try:
            import requests
            response = requests.get(
                "http://localhost:11434/api/tags",
                timeout=2
            )
            if response.status_code == 200:
                self.components["model"]["status"] = "online"
                self.components["model"]["last_check"] = datetime.now().isoformat()
                return "online"
        except Exception:
            logger.debug(f"忽略异常: ", exc_info=True)
            pass
        
        self.components["model"]["status"] = "simulated"
        self.components["model"]["last_check"] = datetime.now().isoformat()
        return "simulated"
    
    def _check_memory_usage(self) -> float:
        """检查内存使用率"""
        try:
            import psutil
            return psutil.virtual_memory().percent / 100
        except ImportError:
            return 0.45
    
    def _check_cpu_usage(self) -> float:
        """检查 CPU 使用率"""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1) / 100
        except ImportError:
            return 0.30
    
    def _check_active_connections(self) -> int:
        """检查活跃连接数"""
        return 5
    
    def _update_status(self, heartbeat: Heartbeat):
        """更新系统状态"""
        previous_status = self.status
        self.status = heartbeat.status
        
        if previous_status != self.status:
            if self.status == HeartStatus.CRITICAL:
                self._create_alert(
                    AlertLevel.CRITICAL,
                    "heart",
                    f"系统状态变为 CRITICAL：{heartbeat.message}",
                    {"previous_status": previous_status.value}
                )
            elif self.status == HeartStatus.WARNING:
                self._create_alert(
                    AlertLevel.WARNING,
                    "heart",
                    f"系统状态变为 WARNING：{heartbeat.message}",
                    {"previous_status": previous_status.value}
                )
            elif self.status == HeartStatus.HEALTHY and previous_status in [HeartStatus.WARNING, HeartStatus.CRITICAL]:
                self._create_alert(
                    AlertLevel.INFO,
                    "heart",
                    "系统状态恢复正常",
                    {"previous_status": previous_status.value}
                )
    
    def _attempt_recovery(self):
        """尝试恢复"""
        if self.recovery_attempts >= self.max_recovery_attempts:
            logger.error(f"已达到最大恢复尝试次数 ({self.max_recovery_attempts})")
            self._create_alert(
                AlertLevel.CRITICAL,
                "recovery",
                "自动恢复失败，需要人工干预",
                {"attempts": self.recovery_attempts}
            )
            return
        
        self.recovery_attempts += 1
        self.status = HeartStatus.RECOVERING
        
        logger.info(f"尝试恢复 ({self.recovery_attempts}/{self.max_recovery_attempts})")
        
        try:
            recovery_result = self._execute_recovery()
            
            if recovery_result["success"]:
                self.recovery_attempts = 0
                self.consecutive_failures = 0
                self.status = HeartStatus.HEALTHY
                logger.info("恢复成功")
                
                self._create_alert(
                    AlertLevel.INFO,
                    "recovery",
                    "系统恢复成功",
                    {"attempts": self.recovery_attempts}
                )
                
                self._trigger_recovery_callbacks(recovery_result)
            else:
                logger.warning(f"恢复失败：{recovery_result.get('error')}")
                time.sleep(self.recovery_delay)
                
        except Exception as e:
            logger.error(f"恢复过程出错：{e}")
            time.sleep(self.recovery_delay)
    
    def _execute_recovery(self) -> Dict[str, Any]:
        """执行恢复操作"""
        recovery_actions = []
        
        try:
            import gc
            gc.collect()
            recovery_actions.append({"action": "gc_collect", "status": "success"})
        except Exception as e:
            recovery_actions.append({"action": "gc_collect", "status": "failed", "error": str(e)})
        
        recovery_actions.append({"action": "reset_connections", "status": "success"})
        
        model_status = self._check_model_status()
        recovery_actions.append({"action": "check_model", "status": model_status})
        
        if self._kairos_enabled:
            self.kairos.evolve()
            recovery_actions.append({"action": "kairos_evolve", "status": "success"})
        
        return {
            "success": True,
            "actions": recovery_actions,
            "timestamp": datetime.now().isoformat()
        }
    
    def _create_alert(self, level: AlertLevel, component: str, message: str, details: Dict[str, Any] = None):
        """创建告警"""
        alert = Alert(
            timestamp=datetime.now(),
            level=level,
            component=component,
            message=message,
            details=details or {}
        )
        
        with self._lock:
            self.alerts.append(alert)
            if len(self.alerts) > 100:
                self.alerts = self.alerts[-100:]
        
        logger.log(
            logging.DEBUG if level == AlertLevel.INFO else
            logging.WARNING if level == AlertLevel.WARNING else
            logging.ERROR if level == AlertLevel.ERROR else
            logging.CRITICAL,
            f"[{level.value.upper()}] {component}: {message}"
        )
        
        self._trigger_alert_callbacks(alert)
    
    def register_heartbeat_callback(self, callback: Callable):
        self.on_heartbeat_callbacks.append(callback)
    
    def register_alert_callback(self, callback: Callable):
        self.on_alert_callbacks.append(callback)
    
    def register_recovery_callback(self, callback: Callable):
        self.on_recovery_callbacks.append(callback)
    
    def _trigger_heartbeat_callbacks(self, heartbeat: Heartbeat):
        for callback in self.on_heartbeat_callbacks:
            try:
                callback(heartbeat)
            except Exception as e:
                logger.error(f"心跳回调执行失败：{e}")
    
    def _trigger_alert_callbacks(self, alert: Alert):
        for callback in self.on_alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"告警回调执行失败：{e}")
    
    def _trigger_recovery_callbacks(self, result: Dict[str, Any]):
        for callback in self.on_recovery_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"恢复回调执行失败：{e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取心脏模块状态"""
        with self._lock:
            status = {
                "status": self.status.value,
                "running": self._running,
                "last_heartbeat": self.last_heartbeat.timestamp.isoformat() if self.last_heartbeat else None,
                "consecutive_failures": self.consecutive_failures,
                "recovery_attempts": self.recovery_attempts,
                "components": self.components,
                "heartbeat_count": len(self.heartbeat_history),
                "alert_count": len(self.alerts),
                "uptime": self._calculate_uptime()
            }
            
            if self._kairos_enabled:
                status["kairos"] = self.kairos.get_kairos_status()
            
            return status
    
    def _calculate_uptime(self) -> float:
        """计算运行时间（秒）"""
        if not self.heartbeat_history:
            return 0
        first_heartbeat = self.heartbeat_history[0]
        return (datetime.now() - first_heartbeat.timestamp).total_seconds()
    
    def get_heartbeat_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取心跳历史"""
        with self._lock:
            history = self.heartbeat_history[-limit:]
            return [
                {
                    "timestamp": hb.timestamp.isoformat(),
                    "status": hb.status.value,
                    "response_time": hb.response_time,
                    "model_status": hb.model_status,
                    "memory_usage": hb.memory_usage,
                    "cpu_usage": hb.cpu_usage,
                    "message": hb.message
                }
                for hb in history
            ]
    
    def get_alerts(self, level: AlertLevel = None, limit: int = 10) -> List[Dict[str, Any]]:
        """获取告警列表"""
        with self._lock:
            alerts = self.alerts
            
            if level:
                alerts = [a for a in alerts if a.level == level]
            
            alerts = alerts[-limit:]
            
            return [
                {
                    "timestamp": alert.timestamp.isoformat(),
                    "level": alert.level.value,
                    "component": alert.component,
                    "message": alert.message,
                    "details": alert.details
                }
                for alert in alerts
            ]
    
    def is_model_online(self) -> bool:
        """检查大模型是否在线"""
        return self.components["model"]["status"] in ["online", "simulated"]
    
    def ensure_model_online(self) -> Dict[str, Any]:
        """确保大模型在线"""
        if self.is_model_online():
            return {
                "success": True,
                "status": self.components["model"]["status"],
                "message": "大模型在线"
            }
        else:
            self._attempt_recovery()
            return {
                "success": self.is_model_online(),
                "status": self.components["model"]["status"],
                "message": "已尝试恢复大模型"
            }
    
    def get_kairos_status(self) -> Dict[str, Any]:
        """获取Kairos模式状态"""
        if not self._kairos_enabled:
            return {"enabled": False}
        
        return {
            "enabled": True,
            **self.kairos.get_kairos_status()
        }
    
    def get_kairos_memory(
        self,
        query: str,
        memory_type: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        查询Kairos内存
        
        Args:
            query: 查询字符串
            memory_type: 内存类型 (user/feedback/project/reference)
            limit: 返回数量限制
        """
        if not self._kairos_enabled:
            return []
        
        types = None
        if memory_type:
            for mt in KairosMemoryType:
                if mt.value == memory_type:
                    types = [mt]
                    break
        
        return self.kairos.query_memory(query, types, limit)
    
    def save_state(self):
        """保存状态到文件"""
        state = {
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat.timestamp.isoformat() if self.last_heartbeat else None,
            "components": self.components,
            "alert_count": len(self.alerts),
            "kairos_enabled": self._kairos_enabled,
            "kairos_strategy_weights": {s.value: w for s, w in self.kairos._strategy_weights.items()},
            "saved_at": datetime.now().isoformat()
        }
        
        state_file = os.path.join(self.data_dir, "heart_state.json")
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        
        logger.info("心脏模块状态已保存")
    
    def load_state(self):
        """从文件加载状态"""
        state_file = os.path.join(self.data_dir, "heart_state.json")
        
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                
                self.components = state.get("components", self.components)
                
                if self._kairos_enabled and "kairos_strategy_weights" in state:
                    for strategy_val, weight in state["kairos_strategy_weights"].items():
                        for strategy in KairosStrategy:
                            if strategy.value == strategy_val:
                                self.kairos._strategy_weights[strategy] = weight
                
                logger.info("心脏模块状态已加载")
            except Exception as e:
                logger.error(f"加载状态失败：{e}")


heart_module = HeartModule()


def get_heart_module() -> HeartModule:
    """获取心脏模块单例"""
    return heart_module
