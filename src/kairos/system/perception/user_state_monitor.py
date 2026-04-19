# -*- coding: utf-8 -*-
"""
用户状态监控器 (User State Monitor)
Kairos 3.0 4b核心组件

特点:
- 实时监控用户状态
- 情绪状态识别
- 认知负荷评估
- 行为模式分析
- 状态变化预测
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from datetime import datetime
import time


class EmotionalState(Enum):
    """情绪状态"""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    ANXIOUS = "anxious"
    CALM = "calm"
    EXCITED = "excited"
    FRUSTRATED = "frustrated"
    NEUTRAL = "neutral"
    CONFUSED = "confused"
    FOCUSED = "focused"


class CognitiveLoadLevel(Enum):
    """认知负荷水平"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    OVERLOADED = "overloaded"


class EngagementLevel(Enum):
    """参与度水平"""
    DISENGAGED = "disengaged"
    PASSIVE = "passive"
    ACTIVE = "active"
    HIGHLY_ENGAGED = "highly_engaged"


@dataclass
class UserState:
    """用户状态"""
    user_id: str
    timestamp: float
    
    emotional_state: EmotionalState = EmotionalState.NEUTRAL
    emotional_intensity: float = 0.5
    
    cognitive_load: CognitiveLoadLevel = CognitiveLoadLevel.MEDIUM
    cognitive_load_score: float = 0.5
    
    engagement: EngagementLevel = EngagementLevel.ACTIVE
    engagement_score: float = 0.7
    
    focus_duration: float = 0.0
    distraction_count: int = 0
    
    interaction_patterns: Dict[str, Any] = field(default_factory=dict)
    context_signals: Dict[str, Any] = field(default_factory=dict)
    
    confidence: float = 0.8
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'timestamp': self.timestamp,
            'emotional_state': self.emotional_state.value,
            'emotional_intensity': self.emotional_intensity,
            'cognitive_load': self.cognitive_load.value,
            'cognitive_load_score': self.cognitive_load_score,
            'engagement': self.engagement.value,
            'engagement_score': self.engagement_score,
            'focus_duration': self.focus_duration,
            'distraction_count': self.distraction_count,
            'interaction_patterns': self.interaction_patterns,
            'context_signals': self.context_signals,
            'confidence': self.confidence
        }


@dataclass
class StateTransition:
    """状态转换记录"""
    from_state: UserState
    to_state: UserState
    trigger: str
    duration_ms: float
    confidence: float


class UserStateMonitor:
    """
    用户状态监控器
    
    核心功能:
    - 实时状态感知
    - 情绪识别
    - 认知负荷评估
    - 参与度追踪
    - 状态预测
    """
    
    def __init__(self, history_size: int = 1000):
        self.history_size = history_size
        self.state_history: deque = deque(maxlen=history_size)
        self.transitions: List[StateTransition] = []
        self.current_state: Optional[UserState] = None
        
        self._emotion_keywords = self._init_emotion_keywords()
        self._load_indicators = self._init_load_indicators()
        self._engagement_signals = self._init_engagement_signals()
        
        self._interaction_buffer: deque = deque(maxlen=100)
        self._focus_start_time: Optional[float] = None
        self._last_interaction_time: Optional[float] = None
    
    def _init_emotion_keywords(self) -> Dict[EmotionalState, List[str]]:
        """初始化情绪关键词"""
        return {
            EmotionalState.HAPPY: ['开心', '高兴', '快乐', '满意', '谢谢', '太好了', '棒', 'happy', 'great', 'awesome'],
            EmotionalState.SAD: ['难过', '伤心', '失望', '遗憾', 'sad', 'disappointed', 'unhappy'],
            EmotionalState.ANGRY: ['生气', '愤怒', '讨厌', '烦', 'angry', 'frustrated', 'annoying'],
            EmotionalState.ANXIOUS: ['担心', '焦虑', '紧张', '不安', 'anxious', 'worried', 'nervous'],
            EmotionalState.CALM: ['平静', '放松', '冷静', 'calm', 'relaxed', 'peaceful'],
            EmotionalState.EXCITED: ['兴奋', '激动', '期待', 'excited', 'thrilled', 'eager'],
            EmotionalState.FRUSTRATED: ['困惑', '不理解', '怎么', '为什么', 'confused', 'why', 'how'],
            EmotionalState.FOCUSED: ['继续', '下一步', '好的', 'ok', 'continue', 'next']
        }
    
    def _init_load_indicators(self) -> Dict[CognitiveLoadLevel, List[str]]:
        """初始化认知负荷指标"""
        return {
            CognitiveLoadLevel.LOW: ['简单', '容易', 'quick', 'simple'],
            CognitiveLoadLevel.MEDIUM: [],
            CognitiveLoadLevel.HIGH: ['复杂', '困难', '详细', 'complex', 'detailed', 'hard'],
            CognitiveLoadLevel.OVERLOADED: ['太多', '受不了', '慢点', '等等', 'too much', 'slow down']
        }
    
    def _init_engagement_signals(self) -> Dict[str, float]:
        """初始化参与度信号"""
        return {
            'quick_response': 0.1,
            'detailed_question': 0.15,
            'follow_up': 0.1,
            'positive_feedback': 0.2,
            'negative_feedback': -0.1,
            'long_silence': -0.15,
            'topic_change': -0.05,
            'clarification_request': 0.05
        }
    
    def update(
        self,
        user_id: str,
        interaction: Dict[str, Any]
    ) -> UserState:
        """
        更新用户状态
        
        Args:
            user_id: 用户ID
            interaction: 交互数据
                {
                    'message': str,
                    'response_time_ms': float,
                    'message_length': int,
                    'context': dict
                }
            
        Returns:
            更新后的用户状态
        """
        start_time = time.time()
        
        self._interaction_buffer.append({
            'timestamp': start_time,
            'interaction': interaction
        })
        
        previous_state = self.current_state
        
        emotional_state, emotional_intensity = self._detect_emotion(interaction)
        cognitive_load, cognitive_score = self._assess_cognitive_load(interaction)
        engagement, engagement_score = self._assess_engagement(interaction)
        
        focus_duration = self._update_focus_tracking(interaction)
        distraction_count = self._count_distractions()
        
        interaction_patterns = self._analyze_interaction_patterns()
        context_signals = interaction.get('context', {})
        
        confidence = self._compute_confidence(len(self._interaction_buffer))
        
        new_state = UserState(
            user_id=user_id,
            timestamp=start_time,
            emotional_state=emotional_state,
            emotional_intensity=emotional_intensity,
            cognitive_load=cognitive_load,
            cognitive_load_score=cognitive_score,
            engagement=engagement,
            engagement_score=engagement_score,
            focus_duration=focus_duration,
            distraction_count=distraction_count,
            interaction_patterns=interaction_patterns,
            context_signals=context_signals,
            confidence=confidence
        )
        
        if previous_state:
            transition = StateTransition(
                from_state=previous_state,
                to_state=new_state,
                trigger=interaction.get('message', '')[:50],
                duration_ms=(start_time - previous_state.timestamp) * 1000,
                confidence=min(previous_state.confidence, confidence)
            )
            self.transitions.append(transition)
        
        self.current_state = new_state
        self.state_history.append(new_state)
        
        return new_state
    
    def _detect_emotion(
        self,
        interaction: Dict[str, Any]
    ) -> Tuple[EmotionalState, float]:
        """检测情绪状态"""
        message = interaction.get('message', '').lower()
        
        emotion_scores = {}
        for emotion, keywords in self._emotion_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in message:
                    score += 1
            emotion_scores[emotion] = score
        
        if not any(emotion_scores.values()):
            return EmotionalState.NEUTRAL, 0.5
        
        max_emotion = max(emotion_scores, key=emotion_scores.get)
        max_score = emotion_scores[max_emotion]
        
        total_matches = sum(emotion_scores.values())
        intensity = min(1.0, max_score / 3 + 0.3)
        
        return max_emotion, intensity
    
    def _assess_cognitive_load(
        self,
        interaction: Dict[str, Any]
    ) -> Tuple[CognitiveLoadLevel, float]:
        """评估认知负荷"""
        message = interaction.get('message', '')
        message_length = interaction.get('message_length', len(message))
        response_time = interaction.get('response_time_ms', 0)
        
        load_score = 0.5
        
        if message_length > 500:
            load_score += 0.2
        elif message_length < 50:
            load_score -= 0.1
        
        if response_time > 10000:
            load_score += 0.2
        elif response_time < 1000:
            load_score -= 0.1
        
        for level, indicators in self._load_indicators.items():
            for indicator in indicators:
                if indicator in message.lower():
                    if level == CognitiveLoadLevel.LOW:
                        load_score -= 0.15
                    elif level == CognitiveLoadLevel.HIGH:
                        load_score += 0.15
                    elif level == CognitiveLoadLevel.OVERLOADED:
                        load_score += 0.3
        
        load_score = max(0.0, min(1.0, load_score))
        
        if load_score < 0.3:
            level = CognitiveLoadLevel.LOW
        elif load_score < 0.6:
            level = CognitiveLoadLevel.MEDIUM
        elif load_score < 0.85:
            level = CognitiveLoadLevel.HIGH
        else:
            level = CognitiveLoadLevel.OVERLOADED
        
        return level, load_score
    
    def _assess_engagement(
        self,
        interaction: Dict[str, Any]
    ) -> Tuple[EngagementLevel, float]:
        """评估参与度"""
        engagement_score = 0.7
        
        message = interaction.get('message', '')
        response_time = interaction.get('response_time_ms', 0)
        
        if response_time < 3000:
            engagement_score += self._engagement_signals['quick_response']
        
        if len(message) > 100:
            engagement_score += self._engagement_signals['detailed_question']
        
        if '?' in message:
            engagement_score += self._engagement_signals['follow_up']
        
        if any(word in message.lower() for word in ['谢谢', '好的', 'thanks', 'ok']):
            engagement_score += self._engagement_signals['positive_feedback']
        
        if any(word in message.lower() for word in ['不对', '错误', 'wrong', 'error']):
            engagement_score += self._engagement_signals['negative_feedback']
        
        if response_time > 30000:
            engagement_score += self._engagement_signals['long_silence']
        
        engagement_score = max(0.0, min(1.0, engagement_score))
        
        if engagement_score < 0.3:
            level = EngagementLevel.DISENGAGED
        elif engagement_score < 0.5:
            level = EngagementLevel.PASSIVE
        elif engagement_score < 0.8:
            level = EngagementLevel.ACTIVE
        else:
            level = EngagementLevel.HIGHLY_ENGAGED
        
        return level, engagement_score
    
    def _update_focus_tracking(self, interaction: Dict[str, Any]) -> float:
        """更新专注时间追踪"""
        current_time = time.time()
        
        if self._focus_start_time is None:
            self._focus_start_time = current_time
            return 0.0
        
        if self._last_interaction_time:
            gap = current_time - self._last_interaction_time
            if gap > 60:
                self._focus_start_time = current_time
        
        self._last_interaction_time = current_time
        
        return current_time - self._focus_start_time
    
    def _count_distractions(self) -> int:
        """计算分心次数"""
        if len(self._interaction_buffer) < 2:
            return 0
        
        distractions = 0
        interactions = list(self._interaction_buffer)
        
        for i in range(1, len(interactions)):
            time_gap = interactions[i]['timestamp'] - interactions[i-1]['timestamp']
            if time_gap > 30:
                distractions += 1
        
        return distractions
    
    def _analyze_interaction_patterns(self) -> Dict[str, Any]:
        """分析交互模式"""
        if not self._interaction_buffer:
            return {}
        
        interactions = list(self._interaction_buffer)
        
        response_times = [
            i['interaction'].get('response_time_ms', 0)
            for i in interactions
        ]
        
        message_lengths = [
            i['interaction'].get('message_length', 0)
            for i in interactions
        ]
        
        return {
            'avg_response_time_ms': sum(response_times) / len(response_times) if response_times else 0,
            'avg_message_length': sum(message_lengths) / len(message_lengths) if message_lengths else 0,
            'interaction_count': len(interactions),
            'response_time_trend': 'increasing' if len(response_times) > 1 and response_times[-1] > response_times[0] else 'stable'
        }
    
    def _compute_confidence(self, sample_size: int) -> float:
        """计算置信度"""
        base_confidence = 0.5
        sample_bonus = min(0.4, sample_size * 0.02)
        return min(1.0, base_confidence + sample_bonus)
    
    def predict_state_change(self, horizon_seconds: float = 60.0) -> Dict[str, Any]:
        """
        预测状态变化
        
        Args:
            horizon_seconds: 预测时间范围
            
        Returns:
            预测结果
        """
        if not self.current_state:
            return {'prediction': 'unknown', 'confidence': 0}
        
        recent_transitions = self.transitions[-10:]
        
        if not recent_transitions:
            return {
                'prediction': 'stable',
                'confidence': 0.5,
                'current_state': self.current_state.to_dict()
            }
        
        emotion_transitions = {}
        for t in recent_transitions:
            from_emotion = t.from_state.emotional_state.value
            to_emotion = t.to_state.emotional_state.value
            key = f"{from_emotion}->{to_emotion}"
            emotion_transitions[key] = emotion_transitions.get(key, 0) + 1
        
        most_common_transition = max(emotion_transitions, key=emotion_transitions.get)
        
        engagement_trend = 0
        if len(recent_transitions) >= 2:
            recent_engagement = [t.to_state.engagement_score for t in recent_transitions[-3:]]
            older_engagement = [t.to_state.engagement_score for t in recent_transitions[-6:-3]]
            if recent_engagement and older_engagement:
                engagement_trend = sum(recent_engagement) / len(recent_engagement) - sum(older_engagement) / len(older_engagement)
        
        predicted_engagement_change = 'stable'
        if engagement_trend > 0.1:
            predicted_engagement_change = 'increasing'
        elif engagement_trend < -0.1:
            predicted_engagement_change = 'decreasing'
        
        return {
            'current_state': self.current_state.to_dict(),
            'predicted_emotion_transition': most_common_transition,
            'predicted_engagement_change': predicted_engagement_change,
            'confidence': min(0.9, len(recent_transitions) * 0.1),
            'horizon_seconds': horizon_seconds
        }
    
    def get_state_summary(self) -> Dict[str, Any]:
        """
        获取状态摘要
        
        Returns:
            状态摘要
        """
        if not self.current_state:
            return {'status': 'no_data'}
        
        recent_states = list(self.state_history)[-20:]
        
        emotion_distribution = {}
        for state in recent_states:
            emotion = state.emotional_state.value
            emotion_distribution[emotion] = emotion_distribution.get(emotion, 0) + 1
        
        avg_cognitive_load = sum(s.cognitive_load_score for s in recent_states) / len(recent_states)
        avg_engagement = sum(s.engagement_score for s in recent_states) / len(recent_states)
        
        return {
            'current_state': self.current_state.to_dict(),
            'emotion_distribution': emotion_distribution,
            'avg_cognitive_load': avg_cognitive_load,
            'avg_engagement': avg_engagement,
            'total_interactions': len(self._interaction_buffer),
            'focus_duration_minutes': self.current_state.focus_duration / 60,
            'distraction_count': self.current_state.distraction_count,
            'state_history_size': len(self.state_history)
        }
    
    def detect_anomaly(self) -> Dict[str, Any]:
        """
        检测异常状态
        
        Returns:
            异常检测结果
        """
        if not self.current_state or len(self.state_history) < 5:
            return {'anomaly_detected': False, 'reason': 'insufficient_data'}
        
        anomalies = []
        
        recent_states = list(self.state_history)[-10:]
        avg_engagement = sum(s.engagement_score for s in recent_states) / len(recent_states)
        
        if self.current_state.engagement_score < avg_engagement - 0.3:
            anomalies.append({
                'type': 'engagement_drop',
                'severity': 'high',
                'current': self.current_state.engagement_score,
                'expected': avg_engagement
            })
        
        if self.current_state.cognitive_load == CognitiveLoadLevel.OVERLOADED:
            anomalies.append({
                'type': 'cognitive_overload',
                'severity': 'critical',
                'current': self.current_state.cognitive_load_score
            })
        
        if self.current_state.distraction_count > 3:
            anomalies.append({
                'type': 'high_distraction',
                'severity': 'medium',
                'count': self.current_state.distraction_count
            })
        
        if self.current_state.emotional_state in [EmotionalState.ANGRY, EmotionalState.FRUSTRATED]:
            if self.current_state.emotional_intensity > 0.7:
                anomalies.append({
                    'type': 'negative_emotion',
                    'severity': 'high',
                    'emotion': self.current_state.emotional_state.value,
                    'intensity': self.current_state.emotional_intensity
                })
        
        return {
            'anomaly_detected': len(anomalies) > 0,
            'anomalies': anomalies,
            'recommendation': self._generate_recommendation(anomalies)
        }
    
    def _generate_recommendation(self, anomalies: List[Dict]) -> str:
        """生成建议"""
        if not anomalies:
            return "状态正常，继续保持"
        
        critical = [a for a in anomalies if a.get('severity') == 'critical']
        high = [a for a in anomalies if a.get('severity') == 'high']
        
        if critical:
            return "检测到严重问题，建议立即调整交互方式或暂停任务"
        elif high:
            return "检测到潜在问题，建议简化任务或提供更多支持"
        else:
            return "状态略有波动，建议关注用户反馈"
    
    def reset(self, user_id: str = None):
        """重置监控器"""
        self.state_history.clear()
        self.transitions.clear()
        self._interaction_buffer.clear()
        self._focus_start_time = None
        self._last_interaction_time = None
        self.current_state = None


def create_user_state_monitor(history_size: int = 1000) -> UserStateMonitor:
    """创建用户状态监控器实例"""
    return UserStateMonitor(history_size=history_size)
