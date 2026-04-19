"""
import logging
自我提示系统 - 主动知识持久化与自我进化机制
logger = logging.getLogger("self_nudge_system")

设计理念来源:
- Hermes Agent: Nudge系统
- ClaudeCode: 持久化项目记忆
- KEPA系统: 自我进化能力

核心特性:
1. 定期自我提示: 主动触发知识管理
2. 知识持久化: 将临时知识转为持久存储
3. 技能触发: 自动触发技能创建和改进
4. 记忆整合: 整合分散的记忆片段
5. 用户建模: 深化对用户的理解
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


class NudgeType(Enum):
    """提示类型枚举"""
    KNOWLEDGE_PERSIST = "knowledge_persist"
    SKILL_CREATE = "skill_create"
    SKILL_IMPROVE = "skill_improve"
    MEMORY_CONSOLIDATE = "memory_consolidate"
    CONTEXT_SUMMARIZE = "context_summarize"
    USER_MODEL_UPDATE = "user_model_update"
    PERFORMANCE_REVIEW = "performance_review"
    LEARNING_REFLECTION = "learning_reflection"
    GOAL_CHECK = "goal_check"
    CLEANUP = "cleanup"


class NudgePriority(Enum):
    """提示优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class NudgeStatus(Enum):
    """提示状态"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Nudge:
    """自我提示数据结构"""
    id: str
    type: NudgeType
    priority: NudgePriority
    context: Dict[str, Any]
    scheduled_at: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: NudgeStatus = NudgeStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "priority": self.priority.value,
            "context": self.context,
            "scheduled_at": self.scheduled_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "metadata": self.metadata
        }


@dataclass
class KnowledgeItem:
    """知识条目"""
    id: str
    content: str
    source: str
    confidence: float
    importance: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserProfile:
    """用户画像"""
    user_id: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    patterns: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    interaction_history: List[Dict[str, Any]] = field(default_factory=list)
    skill_preferences: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class NudgeScheduler:
    """
    自我提示调度器
    
    核心功能:
    1. 定时调度: 按计划执行提示
    2. 优先级队列: 按优先级处理
    3. 重试机制: 失败自动重试
    4. 并发控制: 控制并发执行数
    """
    
    def __init__(
        self,
        interval_seconds: int = 60,
        max_concurrent: int = 3,
        storage_dir: str = ""
    ):
        self.interval = interval_seconds
        self.max_concurrent = max_concurrent
        self.storage_dir = Path(storage_dir) if storage_dir else None
        
        self._pending_queue: List[Nudge] = []
        self._running: Dict[str, Nudge] = {}
        self._history: List[Nudge] = []
        self._callbacks: Dict[NudgeType, Callable] = {}
        
        self._running_flag = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        self._stats = {
            "total_scheduled": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_retries": 0
        }
    
    def register_callback(
        self, 
        nudge_type: NudgeType, 
        callback: Callable[[Dict[str, Any]], str]
    ):
        """注册回调函数"""
        self._callbacks[nudge_type] = callback
    
    def schedule(
        self, 
        nudge: Nudge
    ) -> bool:
        """调度提示"""
        with self._lock:
            if nudge.status != NudgeStatus.PENDING:
                return False
            
            nudge.status = NudgeStatus.SCHEDULED
            self._pending_queue.append(nudge)
            self._pending_queue.sort(
                key=lambda n: (n.priority.value, n.scheduled_at),
                reverse=True
            )
            
            self._stats["total_scheduled"] += 1
            return True
    
    def schedule_immediate(
        self,
        nudge_type: NudgeType,
        priority: NudgePriority = NudgePriority.NORMAL,
        context: Optional[Dict[str, Any]] = None
    ) -> Nudge:
        """立即调度提示"""
        nudge = Nudge(
            id=self._generate_id(),
            type=nudge_type,
            priority=priority,
            context=context or {},
            scheduled_at=datetime.now(timezone.utc)
        )
        self.schedule(nudge)
        return nudge
    
    def schedule_delayed(
        self,
        nudge_type: NudgeType,
        delay_seconds: int,
        priority: NudgePriority = NudgePriority.NORMAL,
        context: Optional[Dict[str, Any]] = None
    ) -> Nudge:
        """延迟调度提示"""
        scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        
        nudge = Nudge(
            id=self._generate_id(),
            type=nudge_type,
            priority=priority,
            context=context or {},
            scheduled_at=scheduled_at
        )
        self.schedule(nudge)
        return nudge
    
    def start(self):
        """启动调度器"""
        if self._running_flag:
            return
        
        self._running_flag = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """停止调度器"""
        self._running_flag = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
    
    def _run_loop(self):
        """主循环"""
        while self._running_flag:
            try:
                self._process_pending()
                self._auto_schedule()
            except Exception:
                logger.debug(f"忽略异常: self._process_pending()", exc_info=True)
                pass
            
            time.sleep(self.interval)
    
    def _process_pending(self):
        """处理待执行提示"""
        now = datetime.now(timezone.utc)
        
        with self._lock:
            to_process = [
                n for n in self._pending_queue
                if n.scheduled_at <= now and n.status == NudgeStatus.SCHEDULED
            ]
        
        for nudge in to_process:
            if len(self._running) >= self.max_concurrent:
                break
            
            self._execute_nudge(nudge)
    
    def _execute_nudge(self, nudge: Nudge):
        """执行提示"""
        with self._lock:
            if nudge.id in self._running:
                return
            
            nudge.status = NudgeStatus.RUNNING
            nudge.started_at = datetime.now(timezone.utc)
            self._running[nudge.id] = nudge
            
            if nudge in self._pending_queue:
                self._pending_queue.remove(nudge)
        
        callback = self._callbacks.get(nudge.type)
        
        try:
            if callback:
                result = callback(nudge.context)
                nudge.result = result
                nudge.status = NudgeStatus.COMPLETED
                self._stats["total_completed"] += 1
            else:
                nudge.result = "No callback registered"
                nudge.status = NudgeStatus.COMPLETED
        except Exception as e:
            nudge.error = str(e)
            nudge.retry_count += 1
            self._stats["total_retries"] += 1
            
            if nudge.retry_count < nudge.max_retries:
                nudge.status = NudgeStatus.SCHEDULED
                nudge.scheduled_at = datetime.now(timezone.utc) + timedelta(
                    seconds=30 * nudge.retry_count
                )
                with self._lock:
                    self._pending_queue.append(nudge)
            else:
                nudge.status = NudgeStatus.FAILED
                self._stats["total_failed"] += 1
        
        finally:
            nudge.completed_at = datetime.now(timezone.utc)
            
            with self._lock:
                self._running.pop(nudge.id, None)
                self._history.append(nudge)
                
                if self.storage_dir:
                    self._save_nudge_history(nudge)
    
    def _auto_schedule(self):
        """自动调度常规提示"""
        now = datetime.now(timezone.utc)
        
        has_knowledge_persist = any(
            n.type == NudgeType.KNOWLEDGE_PERSIST 
            for n in self._pending_queue
        )
        if not has_knowledge_persist:
            self.schedule_delayed(
                NudgeType.KNOWLEDGE_PERSIST,
                delay_seconds=300,
                priority=NudgePriority.LOW
            )
        
        has_memory_consolidate = any(
            n.type == NudgeType.MEMORY_CONSOLIDATE 
            for n in self._pending_queue
        )
        if not has_memory_consolidate:
            self.schedule_delayed(
                NudgeType.MEMORY_CONSOLIDATE,
                delay_seconds=1800,
                priority=NudgePriority.LOW
            )
        
        has_learning_reflection = any(
            n.type == NudgeType.LEARNING_REFLECTION 
            for n in self._pending_queue
        )
        if not has_learning_reflection:
            self.schedule_delayed(
                NudgeType.LEARNING_REFLECTION,
                delay_seconds=3600,
                priority=NudgePriority.NORMAL
            )
    
    def cancel(self, nudge_id: str) -> bool:
        """取消提示"""
        with self._lock:
            for nudge in self._pending_queue:
                if nudge.id == nudge_id:
                    nudge.status = NudgeStatus.CANCELLED
                    self._pending_queue.remove(nudge)
                    self._history.append(nudge)
                    return True
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        with self._lock:
            return {
                "running": self._running_flag,
                "pending_count": len(self._pending_queue),
                "running_count": len(self._running),
                "history_count": len(self._history),
                "stats": self._stats.copy()
            }
    
    def get_pending(self) -> List[Dict[str, Any]]:
        """获取待执行列表"""
        with self._lock:
            return [n.to_dict() for n in self._pending_queue[:10]]
    
    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取历史"""
        with self._lock:
            return [n.to_dict() for n in self._history[-limit:]]
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        content = f"nudge:{time.time()}:{threading.get_ident()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _save_nudge_history(self, nudge: Nudge):
        """保存提示历史"""
        if not self.storage_dir:
            return
        
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        filepath = self.storage_dir / f"nudge_{nudge.id}.json"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(nudge.to_dict(), f, indent=2, ensure_ascii=False)


class KnowledgeManager:
    """
    知识管理器
    
    核心功能:
    1. 知识收集: 收集临时知识
    2. 知识评估: 评估知识重要性
    3. 知识持久化: 转为持久存储
    4. 知识检索: 检索相关知识
    """
    
    def __init__(
        self,
        memory_system: Optional[Any] = None,
        storage_dir: str = ""
    ):
        self.memory_system = memory_system
        self.storage_dir = Path(storage_dir) if storage_dir else None
        
        self._temporary_knowledge: Dict[str, KnowledgeItem] = {}
        self._persistent_knowledge: Dict[str, KnowledgeItem] = {}
        self._lock = threading.Lock()
    
    def add_knowledge(
        self,
        content: str,
        source: str = "interaction",
        confidence: float = 0.5,
        importance: float = 0.5,
        tags: Optional[List[str]] = None
    ) -> KnowledgeItem:
        """添加临时知识"""
        item = KnowledgeItem(
            id=self._generate_id(),
            content=content,
            source=source,
            confidence=confidence,
            importance=importance,
            tags=tags or []
        )
        
        with self._lock:
            self._temporary_knowledge[item.id] = item
        
        return item
    
    def persist_knowledge(
        self,
        min_importance: float = 0.3,
        min_confidence: float = 0.3
    ) -> int:
        """持久化知识"""
        persisted_count = 0
        
        with self._lock:
            to_persist = [
                item for item in self._temporary_knowledge.values()
                if item.importance >= min_importance 
                and item.confidence >= min_confidence
            ]
            
            for item in to_persist:
                if self.memory_system:
                    try:
                        self.memory_system.store(
                            content=item.content,
                            memory_type="long_term",
                            metadata={
                                "source": item.source,
                                "confidence": item.confidence,
                                "importance": item.importance,
                                "tags": item.tags
                            }
                        )
                    except Exception:
                        continue
                
                self._persistent_knowledge[item.id] = item
                del self._temporary_knowledge[item.id]
                persisted_count += 1
        
        return persisted_count
    
    def get_recent_knowledge(
        self,
        limit: int = 10,
        min_importance: float = 0.0
    ) -> List[KnowledgeItem]:
        """获取最近知识"""
        with self._lock:
            all_knowledge = list(self._temporary_knowledge.values())
            
            if min_importance > 0:
                all_knowledge = [
                    k for k in all_knowledge 
                    if k.importance >= min_importance
                ]
            
            all_knowledge.sort(key=lambda k: k.created_at, reverse=True)
            return all_knowledge[:limit]
    
    def search_knowledge(
        self,
        query: str,
        limit: int = 10
    ) -> List[KnowledgeItem]:
        """搜索知识"""
        results = []
        query_lower = query.lower()
        
        with self._lock:
            for item in self._persistent_knowledge.values():
                if query_lower in item.content.lower():
                    results.append(item)
                elif any(query_lower in tag.lower() for tag in item.tags):
                    results.append(item)
        
        results.sort(key=lambda k: k.importance, reverse=True)
        return results[:limit]
    
    def consolidate_memory(self) -> Dict[str, int]:
        """整合记忆"""
        stats = {
            "merged": 0,
            "summarized": 0,
            "archived": 0
        }
        
        with self._lock:
            groups = self._group_similar_knowledge()
            
            for key, items in groups.items():
                if len(items) > 1:
                    merged = self._merge_knowledge(items)
                    for item in items:
                        if item.id in self._temporary_knowledge:
                            del self._temporary_knowledge[item.id]
                    self._temporary_knowledge[merged.id] = merged
                    stats["merged"] += len(items) - 1
        
        return stats
    
    def _group_similar_knowledge(
        self
    ) -> Dict[str, List[KnowledgeItem]]:
        """分组相似知识"""
        groups: Dict[str, List[KnowledgeItem]] = {}
        
        for item in self._temporary_knowledge.values():
            key = self._get_similarity_key(item)
            if key not in groups:
                groups[key] = []
            groups[key].append(item)
        
        return groups
    
    def _get_similarity_key(self, item: KnowledgeItem) -> str:
        """获取相似性键"""
        words = item.content.lower().split()[:5]
        return "_".join(words)
    
    def _merge_knowledge(
        self, 
        items: List[KnowledgeItem]
    ) -> KnowledgeItem:
        """合并知识"""
        best = max(items, key=lambda k: k.confidence * k.importance)
        
        merged = KnowledgeItem(
            id=self._generate_id(),
            content=best.content,
            source="merged",
            confidence=sum(k.confidence for k in items) / len(items),
            importance=max(k.importance for k in items),
            tags=list(set(tag for k in items for tag in k.tags)),
            metadata={"merged_from": [k.id for k in items]}
        )
        
        return merged
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        content = f"knowledge:{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计"""
        with self._lock:
            return {
                "temporary_count": len(self._temporary_knowledge),
                "persistent_count": len(self._persistent_knowledge),
                "total_count": len(self._temporary_knowledge) + 
                              len(self._persistent_knowledge)
            }


class UserModeling:
    """
    用户建模系统
    
    核心功能:
    1. 偏好学习: 学习用户偏好
    2. 模式识别: 识别用户行为模式
    3. 目标追踪: 追踪用户目标
    4. 个性化适配: 适配用户需求
    """
    
    def __init__(self, storage_dir: str = ""):
        self.storage_dir = Path(storage_dir) if storage_dir else None
        self._profiles: Dict[str, UserProfile] = {}
        self._current_user: Optional[str] = None
        self._lock = threading.Lock()
    
    def get_or_create_profile(
        self, 
        user_id: str
    ) -> UserProfile:
        """获取或创建用户画像"""
        with self._lock:
            if user_id not in self._profiles:
                self._profiles[user_id] = UserProfile(user_id=user_id)
            return self._profiles[user_id]
    
    def set_current_user(self, user_id: str):
        """设置当前用户"""
        self._current_user = user_id
        self.get_or_create_profile(user_id)
    
    def record_interaction(
        self,
        interaction_type: str,
        content: str,
        feedback: Optional[str] = None
    ):
        """记录交互"""
        if not self._current_user:
            return
        
        with self._lock:
            profile = self._profiles.get(self._current_user)
            if not profile:
                return
            
            profile.interaction_history.append({
                "type": interaction_type,
                "content": content[:200],
                "feedback": feedback,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            profile.updated_at = datetime.now(timezone.utc)
            
            self._update_preferences(profile, interaction_type, feedback)
    
    def _update_preferences(
        self,
        profile: UserProfile,
        interaction_type: str,
        feedback: Optional[str]
    ):
        """更新偏好"""
        if not feedback:
            return
        
        if feedback.lower() in ["good", "positive", "helpful"]:
            current = profile.preferences.get(interaction_type, 0.5)
            profile.preferences[interaction_type] = min(1.0, current + 0.1)
        elif feedback.lower() in ["bad", "negative", "unhelpful"]:
            current = profile.preferences.get(interaction_type, 0.5)
            profile.preferences[interaction_type] = max(0.0, current - 0.1)
    
    def add_goal(self, goal: str):
        """添加目标"""
        if not self._current_user:
            return
        
        with self._lock:
            profile = self._profiles.get(self._current_user)
            if profile and goal not in profile.goals:
                profile.goals.append(goal)
                profile.updated_at = datetime.now(timezone.utc)
    
    def update_skill_preference(
        self,
        skill_name: str,
        preference: float
    ):
        """更新技能偏好"""
        if not self._current_user:
            return
        
        with self._lock:
            profile = self._profiles.get(self._current_user)
            if profile:
                profile.skill_preferences[skill_name] = preference
                profile.updated_at = datetime.now(timezone.utc)
    
    def get_recommendations(self) -> List[Dict[str, Any]]:
        """获取推荐"""
        if not self._current_user:
            return []
        
        with self._lock:
            profile = self._profiles.get(self._current_user)
            if not profile:
                return []
            
            recommendations = []
            
            sorted_skills = sorted(
                profile.skill_preferences.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            for skill, pref in sorted_skills[:5]:
                recommendations.append({
                    "type": "skill",
                    "name": skill,
                    "preference": pref
                })
            
            return recommendations
    
    def get_profile_summary(self) -> Dict[str, Any]:
        """获取画像摘要"""
        if not self._current_user:
            return {}
        
        with self._lock:
            profile = self._profiles.get(self._current_user)
            if not profile:
                return {}
            
            return {
                "user_id": profile.user_id,
                "preferences_count": len(profile.preferences),
                "patterns_count": len(profile.patterns),
                "goals_count": len(profile.goals),
                "interactions_count": len(profile.interaction_history),
                "skill_preferences_count": len(profile.skill_preferences),
                "created_at": profile.created_at.isoformat(),
                "updated_at": profile.updated_at.isoformat()
            }


class SelfNudgeSystem:
    """
    自我提示系统主类
    
    整合调度器、知识管理和用户建模
    
    使用方式:
        system = SelfNudgeSystem(
            memory_system=memory,
            skill_system=skills,
            metacognition=meta
        )
        system.start()
        
        # 触发技能创建
        system.trigger_skill_creation({"context": "..."})
        
        # 触发技能改进
        system.trigger_skill_improvement("skill_id", "feedback")
    """
    
    def __init__(
        self,
        memory_system: Optional[Any] = None,
        skill_system: Optional[Any] = None,
        metacognition: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.memory_system = memory_system
        self.skill_system = skill_system
        self.metacognition = metacognition
        self.config = config or {}
        
        self.scheduler = NudgeScheduler(
            interval_seconds=self.config.get("interval_seconds", 60),
            max_concurrent=self.config.get("max_concurrent", 3),
            storage_dir=self.config.get("storage_dir", "")
        )
        
        self.knowledge_manager = KnowledgeManager(
            memory_system=memory_system,
            storage_dir=self.config.get("storage_dir", "")
        )
        
        self.user_modeling = UserModeling(
            storage_dir=self.config.get("storage_dir", "")
        )
        
        self._setup_callbacks()
        self._running = False
    
    def _setup_callbacks(self):
        """设置回调函数"""
        self.scheduler.register_callback(
            NudgeType.KNOWLEDGE_PERSIST,
            self._persist_knowledge
        )
        self.scheduler.register_callback(
            NudgeType.SKILL_CREATE,
            self._create_skill
        )
        self.scheduler.register_callback(
            NudgeType.SKILL_IMPROVE,
            self._improve_skill
        )
        self.scheduler.register_callback(
            NudgeType.MEMORY_CONSOLIDATE,
            self._consolidate_memory
        )
        self.scheduler.register_callback(
            NudgeType.CONTEXT_SUMMARIZE,
            self._summarize_context
        )
        self.scheduler.register_callback(
            NudgeType.USER_MODEL_UPDATE,
            self._update_user_model
        )
        self.scheduler.register_callback(
            NudgeType.PERFORMANCE_REVIEW,
            self._review_performance
        )
        self.scheduler.register_callback(
            NudgeType.LEARNING_REFLECTION,
            self._reflect_learning
        )
        self.scheduler.register_callback(
            NudgeType.GOAL_CHECK,
            self._check_goals
        )
        self.scheduler.register_callback(
            NudgeType.CLEANUP,
            self._cleanup
        )
    
    def start(self):
        """启动系统"""
        if self._running:
            return
        
        self._running = True
        self.scheduler.start()
    
    def stop(self):
        """停止系统"""
        self._running = False
        self.scheduler.stop()
    
    def trigger_skill_creation(
        self,
        context: Dict[str, Any],
        priority: NudgePriority = NudgePriority.HIGH
    ):
        """触发技能创建"""
        self.scheduler.schedule_immediate(
            NudgeType.SKILL_CREATE,
            priority=priority,
            context=context
        )
    
    def trigger_skill_improvement(
        self,
        skill_id: str,
        feedback: str,
        priority: NudgePriority = NudgePriority.HIGH
    ):
        """触发技能改进"""
        self.scheduler.schedule_immediate(
            NudgeType.SKILL_IMPROVE,
            priority=priority,
            context={"skill_id": skill_id, "feedback": feedback}
        )
    
    def add_knowledge(
        self,
        content: str,
        source: str = "interaction",
        confidence: float = 0.5,
        importance: float = 0.5
    ):
        """添加知识"""
        return self.knowledge_manager.add_knowledge(
            content=content,
            source=source,
            confidence=confidence,
            importance=importance
        )
    
    def record_user_interaction(
        self,
        interaction_type: str,
        content: str,
        feedback: Optional[str] = None
    ):
        """记录用户交互"""
        self.user_modeling.record_interaction(
            interaction_type=interaction_type,
            content=content,
            feedback=feedback
        )
    
    def set_user(self, user_id: str):
        """设置当前用户"""
        self.user_modeling.set_current_user(user_id)
    
    def _persist_knowledge(self, context: Dict[str, Any]) -> str:
        """持久化知识"""
        count = self.knowledge_manager.persist_knowledge()
        return f"持久化 {count} 条知识"
    
    def _create_skill(self, context: Dict[str, Any]) -> str:
        """创建技能"""
        if not self.skill_system:
            return "技能系统不可用"
        
        return "技能创建已触发"
    
    def _improve_skill(self, context: Dict[str, Any]) -> str:
        """改进技能"""
        skill_id = context.get("skill_id")
        feedback = context.get("feedback", "")
        
        if not self.skill_system or not skill_id:
            return "技能系统不可用或缺少技能ID"
        
        return f"技能 {skill_id} 改进已触发"
    
    def _consolidate_memory(self, context: Dict[str, Any]) -> str:
        """整合记忆"""
        stats = self.knowledge_manager.consolidate_memory()
        return f"记忆整合完成: 合并{stats['merged']}条"
    
    def _summarize_context(self, context: Dict[str, Any]) -> str:
        """总结上下文"""
        recent = self.knowledge_manager.get_recent_knowledge(limit=5)
        
        if not recent:
            return "无最近上下文"
        
        summary = "; ".join(k.content[:50] for k in recent)
        return f"上下文摘要: {summary[:200]}"
    
    def _update_user_model(self, context: Dict[str, Any]) -> str:
        """更新用户模型"""
        summary = self.user_modeling.get_profile_summary()
        return f"用户模型已更新: {summary.get('interactions_count', 0)}次交互"
    
    def _review_performance(self, context: Dict[str, Any]) -> str:
        """性能审查"""
        if self.metacognition:
            try:
                stats = self.metacognition.get_performance_stats()
                return f"性能审查: {stats}"
            except Exception:
                logger.debug(f"忽略异常: stats = self.metacognition.get_performance_stats()", exc_info=True)
                pass
        
        return "性能审查完成"
    
    def _reflect_learning(self, context: Dict[str, Any]) -> str:
        """学习反思"""
        knowledge_stats = self.knowledge_manager.get_statistics()
        
        reflection = f"学习反思: 临时知识{knowledge_stats['temporary_count']}条, "
        reflection += f"持久知识{knowledge_stats['persistent_count']}条"
        
        return reflection
    
    def _check_goals(self, context: Dict[str, Any]) -> str:
        """检查目标"""
        recommendations = self.user_modeling.get_recommendations()
        return f"目标检查完成: {len(recommendations)}个推荐"
    
    def _cleanup(self, context: Dict[str, Any]) -> str:
        """清理"""
        return "清理完成"
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "running": self._running,
            "scheduler": self.scheduler.get_status(),
            "knowledge": self.knowledge_manager.get_statistics(),
            "user_profile": self.user_modeling.get_profile_summary()
        }
    
    def get_pending_nudges(self) -> List[Dict[str, Any]]:
        """获取待执行提示"""
        return self.scheduler.get_pending()
    
    def get_nudge_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取提示历史"""
        return self.scheduler.get_history(limit)
