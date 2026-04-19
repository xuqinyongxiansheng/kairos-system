# -*- coding: utf-8 -*-
"""
上下文感知引擎 (Context Awareness Engine)
Kairos 3.0 4b核心组件

特点:
- 多维度上下文感知
- 上下文切换检测
- 上下文相关性计算
- 动态上下文更新
"""

import math
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
from datetime import datetime
import time


class ContextType(Enum):
    """上下文类型"""
    TASK = "task"
    DOMAIN = "domain"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    SOCIAL = "social"
    EMOTIONAL = "emotional"
    TECHNICAL = "technical"
    HISTORICAL = "historical"


class ContextPriority(Enum):
    """上下文优先级"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class ContextElement:
    """上下文元素"""
    context_id: str
    context_type: ContextType
    content: str
    relevance: float
    priority: ContextPriority
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    ttl_seconds: Optional[float] = None
    
    def is_expired(self) -> bool:
        if self.ttl_seconds is None:
            return False
        return time.time() - self.timestamp > self.ttl_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'context_id': self.context_id,
            'context_type': self.context_type.value,
            'content': self.content,
            'relevance': self.relevance,
            'priority': self.priority.value,
            'timestamp': self.timestamp,
            'metadata': self.metadata,
            'ttl_seconds': self.ttl_seconds,
            'is_expired': self.is_expired()
        }


@dataclass
class ContextSnapshot:
    """上下文快照"""
    snapshot_id: str
    timestamp: float
    elements: List[ContextElement]
    dominant_context: Optional[ContextType]
    context_switch_detected: bool
    coherence_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'snapshot_id': self.snapshot_id,
            'timestamp': self.timestamp,
            'elements': [e.to_dict() for e in self.elements],
            'dominant_context': self.dominant_context.value if self.dominant_context else None,
            'context_switch_detected': self.context_switch_detected,
            'coherence_score': self.coherence_score
        }


class ContextAwarenessEngine:
    """
    上下文感知引擎
    
    核心功能:
    - 多维度上下文管理
    - 上下文切换检测
    - 相关性计算
    - 上下文融合
    """
    
    def __init__(self, max_contexts: int = 100):
        self.max_contexts = max_contexts
        self.contexts: Dict[str, ContextElement] = {}
        self.context_history: deque = deque(maxlen=1000)
        self.type_index: Dict[ContextType, Set[str]] = defaultdict(set)
        
        self._context_counter = 0
        self._snapshot_counter = 0
        self._last_dominant_context: Optional[ContextType] = None
        self._context_keywords = self._init_context_keywords()
    
    def _init_context_keywords(self) -> Dict[ContextType, List[str]]:
        """初始化上下文关键词"""
        return {
            ContextType.TASK: ['任务', '工作', '完成', '目标', 'task', 'work', 'goal', '完成'],
            ContextType.DOMAIN: ['代码', '编程', '开发', 'code', 'programming', '开发', '技术'],
            ContextType.TEMPORAL: ['时间', '今天', '现在', '昨天', 'time', 'today', 'now', '昨天'],
            ContextType.SPATIAL: ['位置', '地点', '这里', 'location', 'place', 'here', '位置'],
            ContextType.SOCIAL: ['用户', '团队', '合作', 'user', 'team', 'collaborate', '团队'],
            ContextType.EMOTIONAL: ['感觉', '情绪', '开心', 'feel', 'emotion', 'happy', '情绪'],
            ContextType.TECHNICAL: ['系统', '配置', '错误', 'system', 'config', 'error', '错误'],
            ContextType.HISTORICAL: ['之前', '历史', '记录', 'before', 'history', 'record', '历史']
        }
    
    def add_context(
        self,
        context_type: ContextType,
        content: str,
        relevance: float = 1.0,
        priority: ContextPriority = ContextPriority.MEDIUM,
        metadata: Dict[str, Any] = None,
        ttl_seconds: Optional[float] = None
    ) -> str:
        """
        添加上下文
        
        Args:
            context_type: 上下文类型
            content: 内容
            relevance: 相关性
            priority: 优先级
            metadata: 元数据
            ttl_seconds: 生存时间
            
        Returns:
            上下文ID
        """
        self._context_counter += 1
        context_id = f"ctx_{self._context_counter}"
        
        context = ContextElement(
            context_id=context_id,
            context_type=context_type,
            content=content,
            relevance=relevance,
            priority=priority,
            timestamp=time.time(),
            metadata=metadata or {},
            ttl_seconds=ttl_seconds
        )
        
        self.contexts[context_id] = context
        self.type_index[context_type].add(context_id)
        
        self._enforce_max_contexts()
        
        return context_id
    
    def _enforce_max_contexts(self):
        """强制最大上下文数量"""
        if len(self.contexts) <= self.max_contexts:
            return
        
        expired = [cid for cid, ctx in self.contexts.items() if ctx.is_expired()]
        for cid in expired:
            self._remove_context(cid)
        
        if len(self.contexts) > self.max_contexts:
            sorted_contexts = sorted(
                self.contexts.items(),
                key=lambda x: (x[1].priority.value, -x[1].relevance, x[1].timestamp)
            )
            
            to_remove = len(self.contexts) - self.max_contexts
            for cid, _ in sorted_contexts[:to_remove]:
                self._remove_context(cid)
    
    def _remove_context(self, context_id: str):
        """移除上下文"""
        if context_id in self.contexts:
            ctx = self.contexts[context_id]
            self.type_index[ctx.context_type].discard(context_id)
            del self.contexts[context_id]
    
    def get_relevant_contexts(
        self,
        query: str,
        context_types: Optional[List[ContextType]] = None,
        min_relevance: float = 0.3,
        limit: int = 10
    ) -> List[ContextElement]:
        """
        获取相关上下文
        
        Args:
            query: 查询字符串
            context_types: 限定上下文类型
            min_relevance: 最小相关性
            limit: 返回数量限制
            
        Returns:
            相关上下文列表
        """
        self._clean_expired()
        
        candidates = []
        
        for context_id, context in self.contexts.items():
            if context_types and context.context_type not in context_types:
                continue
            
            relevance = self._compute_relevance(query, context)
            
            if relevance >= min_relevance:
                adjusted_context = ContextElement(
                    context_id=context.context_id,
                    context_type=context.context_type,
                    content=context.content,
                    relevance=relevance,
                    priority=context.priority,
                    timestamp=context.timestamp,
                    metadata=context.metadata,
                    ttl_seconds=context.ttl_seconds
                )
                candidates.append(adjusted_context)
        
        candidates.sort(key=lambda x: (-x.relevance, x.priority.value))
        
        return candidates[:limit]
    
    def _compute_relevance(self, query: str, context: ContextElement) -> float:
        """计算相关性"""
        query_words = set(query.lower().split())
        context_words = set(context.content.lower().split())
        
        if not query_words or not context_words:
            return 0.0
        
        intersection = query_words & context_words
        union = query_words | context_words
        
        jaccard = len(intersection) / len(union) if union else 0
        
        keyword_match = 0
        keywords = self._context_keywords.get(context.context_type, [])
        for keyword in keywords:
            if keyword in query.lower():
                keyword_match += 1
        keyword_score = min(1.0, keyword_match / 3)
        
        recency_factor = 1.0
        age_seconds = time.time() - context.timestamp
        if age_seconds > 3600:
            recency_factor = 0.8
        elif age_seconds > 86400:
            recency_factor = 0.5
        
        base_relevance = context.relevance
        
        return base_relevance * (0.4 * jaccard + 0.3 * keyword_score + 0.3 * recency_factor)
    
    def _clean_expired(self):
        """清理过期上下文"""
        expired = [cid for cid, ctx in self.contexts.items() if ctx.is_expired()]
        for cid in expired:
            self._remove_context(cid)
    
    def detect_context_switch(self) -> Dict[str, Any]:
        """
        检测上下文切换
        
        Returns:
            切换检测结果
        """
        type_counts = defaultdict(int)
        type_relevance = defaultdict(float)
        
        for context in self.contexts.values():
            if not context.is_expired():
                type_counts[context.context_type] += 1
                type_relevance[context.context_type] += context.relevance
        
        if not type_counts:
            return {
                'switch_detected': False,
                'reason': 'no_active_context'
            }
        
        dominant_type = max(type_counts, key=lambda t: type_relevance[t])
        
        switch_detected = (
            self._last_dominant_context is not None and
            dominant_type != self._last_dominant_context
        )
        
        previous_context = self._last_dominant_context
        self._last_dominant_context = dominant_type
        
        return {
            'switch_detected': switch_detected,
            'previous_context': previous_context.value if previous_context else None,
            'current_context': dominant_type.value,
            'context_distribution': {t.value: c for t, c in type_counts.items()},
            'relevance_distribution': {t.value: r for t, r in type_relevance.items()}
        }
    
    def create_snapshot(self) -> ContextSnapshot:
        """
        创建上下文快照
        
        Returns:
            上下文快照
        """
        self._snapshot_counter += 1
        snapshot_id = f"snap_{self._snapshot_counter}"
        
        self._clean_expired()
        
        elements = list(self.contexts.values())
        
        switch_result = self.detect_context_switch()
        dominant_context = None
        
        if switch_result.get('current_context'):
            for ct in ContextType:
                if ct.value == switch_result['current_context']:
                    dominant_context = ct
                    break
        
        coherence_score = self._compute_coherence(elements)
        
        snapshot = ContextSnapshot(
            snapshot_id=snapshot_id,
            timestamp=time.time(),
            elements=elements,
            dominant_context=dominant_context,
            context_switch_detected=switch_result['switch_detected'],
            coherence_score=coherence_score
        )
        
        self.context_history.append(snapshot)
        
        return snapshot
    
    def _compute_coherence(self, elements: List[ContextElement]) -> float:
        """计算上下文一致性"""
        if len(elements) < 2:
            return 1.0
        
        type_counts = defaultdict(int)
        for elem in elements:
            type_counts[elem.context_type] += 1
        
        total = len(elements)
        max_count = max(type_counts.values())
        
        coherence = max_count / total
        
        priorities = [e.priority.value for e in elements]
        priority_variance = sum((p - sum(priorities)/len(priorities))**2 for p in priorities) / len(priorities)
        
        coherence *= (1 - min(1, priority_variance / 2))
        
        return max(0.0, min(1.0, coherence))
    
    def fuse_contexts(
        self,
        context_ids: List[str],
        fusion_strategy: str = "weighted"
    ) -> Dict[str, Any]:
        """
        融合多个上下文
        
        Args:
            context_ids: 上下文ID列表
            fusion_strategy: 融合策略
            
        Returns:
            融合结果
        """
        contexts = [self.contexts.get(cid) for cid in context_ids if cid in self.contexts]
        
        if not contexts:
            return {'error': 'no_valid_contexts'}
        
        if fusion_strategy == "weighted":
            total_weight = sum(c.relevance for c in contexts)
            
            fused_content_parts = []
            for ctx in contexts:
                weight = ctx.relevance / total_weight if total_weight > 0 else 1 / len(contexts)
                fused_content_parts.append(f"[{ctx.context_type.value}:{weight:.2f}] {ctx.content}")
            
            fused_content = "\n".join(fused_content_parts)
            
            types = [c.context_type for c in contexts]
            dominant_type = max(set(types), key=types.count)
            
            avg_relevance = sum(c.relevance for c in contexts) / len(contexts)
            
        elif fusion_strategy == "priority":
            sorted_contexts = sorted(contexts, key=lambda c: c.priority.value)
            fused_content = "\n".join(c.content for c in sorted_contexts)
            dominant_type = sorted_contexts[0].context_type
            avg_relevance = sorted_contexts[0].relevance
            
        else:
            fused_content = "\n".join(c.content for c in contexts)
            types = [c.context_type for c in contexts]
            dominant_type = types[0] if types else None
            avg_relevance = sum(c.relevance for c in contexts) / len(contexts)
        
        return {
            'fused_content': fused_content,
            'dominant_type': dominant_type.value if dominant_type else None,
            'avg_relevance': avg_relevance,
            'context_count': len(contexts),
            'fusion_strategy': fusion_strategy
        }
    
    def get_context_summary(self) -> Dict[str, Any]:
        """
        获取上下文摘要
        
        Returns:
            上下文摘要
        """
        self._clean_expired()
        
        type_distribution = defaultdict(int)
        priority_distribution = defaultdict(int)
        
        for context in self.contexts.values():
            type_distribution[context.context_type.value] += 1
            priority_distribution[context.priority.name] += 1
        
        recent_snapshots = list(self.context_history)[-10:]
        switch_count = sum(1 for s in recent_snapshots if s.context_switch_detected)
        
        return {
            'total_contexts': len(self.contexts),
            'type_distribution': dict(type_distribution),
            'priority_distribution': dict(priority_distribution),
            'recent_switches': switch_count,
            'snapshot_count': len(self.context_history),
            'dominant_context': self._last_dominant_context.value if self._last_dominant_context else None
        }
    
    def update_relevance(
        self,
        context_id: str,
        new_relevance: float
    ) -> bool:
        """
        更新上下文相关性
        
        Args:
            context_id: 上下文ID
            new_relevance: 新相关性值
            
        Returns:
            是否成功
        """
        if context_id not in self.contexts:
            return False
        
        self.contexts[context_id].relevance = new_relevance
        return True
    
    def clear_context_type(self, context_type: ContextType):
        """清除指定类型的所有上下文"""
        context_ids = list(self.type_index[context_type])
        for cid in context_ids:
            self._remove_context(cid)
    
    def reset(self):
        """重置引擎"""
        self.contexts.clear()
        self.context_history.clear()
        self.type_index.clear()
        self._last_dominant_context = None


def create_context_engine(max_contexts: int = 100) -> ContextAwarenessEngine:
    """创建上下文感知引擎实例"""
    return ContextAwarenessEngine(max_contexts=max_contexts)
