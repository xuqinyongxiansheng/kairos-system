"""
用户画像建模系统
构建和维护用户偏好、行为模式、决策历史的持久模型
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PreferenceType(Enum):
    """偏好类型"""
    COMMUNICATION_STYLE = "communication_style"
    TASK_PRIORITY = "task_priority"
    OUTPUT_FORMAT = "output_format"
    WORKFLOW_PREFERENCE = "workflow_preference"
    TECHNICAL_LEVEL = "technical_level"
    LANGUAGE_PREFERENCE = "language_preference"


class InteractionType(Enum):
    """交互类型"""
    QUESTION = "question"
    COMMAND = "command"
    FEEDBACK = "feedback"
    CORRECTION = "correction"
    APPROVAL = "approval"


@dataclass
class UserPreference:
    """用户偏好"""
    preference_type: str
    value: Any
    confidence: float
    source: str
    last_updated: str


@dataclass
class BehaviorPattern:
    """行为模式"""
    pattern_id: str
    pattern_type: str
    description: str
    frequency: int
    last_occurred: str
    context: Dict[str, Any]


@dataclass
class DecisionRecord:
    """决策记录"""
    decision_id: str
    context: str
    options: List[str]
    chosen_option: str
    reasoning: str
    outcome: str
    timestamp: str


class UserProfileModeler:
    """用户画像建模器"""
    
    def __init__(self, profile_dir: str = "./data/user_profiles"):
        self.profile_dir = profile_dir
        self.current_user_id: Optional[str] = None
        self.preferences: Dict[str, UserPreference] = {}
        self.behavior_patterns: Dict[str, BehaviorPattern] = {}
        self.decision_history: List[DecisionRecord] = []
        self.interaction_history: List[Dict[str, Any]] = []
        self.corrections: List[Dict[str, Any]] = []
        
        os.makedirs(profile_dir, exist_ok=True)
        
        logger.info("用户画像建模系统初始化")
    
    def set_user(self, user_id: str) -> Dict[str, Any]:
        """设置当前用户"""
        self.current_user_id = user_id
        self._load_profile(user_id)
        
        logger.info(f"设置当前用户: {user_id}")
        return {"status": "success", "user_id": user_id}
    
    def _load_profile(self, user_id: str):
        """加载用户画像"""
        profile_path = os.path.join(self.profile_dir, f"{user_id}.json")
        
        try:
            if os.path.exists(profile_path):
                with open(profile_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 加载偏好
                for pref_type, pref_data in data.get("preferences", {}).items():
                    self.preferences[pref_type] = UserPreference(
                        preference_type=pref_data["preference_type"],
                        value=pref_data["value"],
                        confidence=pref_data["confidence"],
                        source=pref_data["source"],
                        last_updated=pref_data["last_updated"]
                    )
                
                # 加载行为模式
                for pattern_id, pattern_data in data.get("behavior_patterns", {}).items():
                    self.behavior_patterns[pattern_id] = BehaviorPattern(
                        pattern_id=pattern_data["pattern_id"],
                        pattern_type=pattern_data["pattern_type"],
                        description=pattern_data["description"],
                        frequency=pattern_data["frequency"],
                        last_occurred=pattern_data["last_occurred"],
                        context=pattern_data["context"]
                    )
                
                # 加载决策历史
                for dec_data in data.get("decision_history", []):
                    self.decision_history.append(DecisionRecord(
                        decision_id=dec_data["decision_id"],
                        context=dec_data["context"],
                        options=dec_data["options"],
                        chosen_option=dec_data["chosen_option"],
                        reasoning=dec_data["reasoning"],
                        outcome=dec_data["outcome"],
                        timestamp=dec_data["timestamp"]
                    ))
                
                logger.info(f"已加载用户画像: {user_id}")
            else:
                # 创建新用户画像
                self.preferences = {}
                self.behavior_patterns = {}
                self.decision_history = []
                self._save_profile()
                logger.info(f"创建新用户画像: {user_id}")
                
        except Exception as e:
            logger.error(f"加载用户画像失败: {e}")
    
    def _save_profile(self):
        """保存用户画像"""
        if not self.current_user_id:
            return
        
        profile_path = os.path.join(self.profile_dir, f"{self.current_user_id}.json")
        
        try:
            data = {
                "user_id": self.current_user_id,
                "preferences": {
                    pref_type: {
                        "preference_type": pref.preference_type,
                        "value": pref.value,
                        "confidence": pref.confidence,
                        "source": pref.source,
                        "last_updated": pref.last_updated
                    }
                    for pref_type, pref in self.preferences.items()
                },
                "behavior_patterns": {
                    pattern_id: {
                        "pattern_id": pattern.pattern_id,
                        "pattern_type": pattern.pattern_type,
                        "description": pattern.description,
                        "frequency": pattern.frequency,
                        "last_occurred": pattern.last_occurred,
                        "context": pattern.context
                    }
                    for pattern_id, pattern in self.behavior_patterns.items()
                },
                "decision_history": [
                    {
                        "decision_id": dec.decision_id,
                        "context": dec.context,
                        "options": dec.options,
                        "chosen_option": dec.chosen_option,
                        "reasoning": dec.reasoning,
                        "outcome": dec.outcome,
                        "timestamp": dec.timestamp
                    }
                    for dec in self.decision_history
                ],
                "interaction_count": len(self.interaction_history),
                "correction_count": len(self.corrections),
                "last_updated": datetime.now().isoformat()
            }
            
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug("用户画像已保存")
            
        except Exception as e:
            logger.error(f"保存用户画像失败: {e}")
    
    def record_interaction(self, interaction_type: str, content: str, 
                          context: Dict[str, Any] = None) -> Dict[str, Any]:
        """记录交互"""
        interaction = {
            "id": f"int_{int(datetime.now().timestamp())}",
            "type": interaction_type,
            "content": content,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }
        
        self.interaction_history.append(interaction)
        
        # 分析交互并更新偏好
        self._analyze_interaction(interaction)
        
        self._save_profile()
        
        return {"status": "success", "interaction_id": interaction["id"]}
    
    def _analyze_interaction(self, interaction: Dict[str, Any]):
        """分析交互并更新偏好"""
        content = interaction["content"].lower()
        
        # 检测语言偏好
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in content)
        if has_chinese:
            self._update_preference(
                PreferenceType.LANGUAGE_PREFERENCE.value,
                "chinese",
                "interaction_analysis",
                0.1
            )
        
        # 检测技术级别
        technical_keywords = ["代码", "函数", "API", "算法", "数据库", "code", "function", "api"]
        if any(kw in content for kw in technical_keywords):
            self._update_preference(
                PreferenceType.TECHNICAL_LEVEL.value,
                "advanced",
                "interaction_analysis",
                0.1
            )
        
        # 检测输出格式偏好
        if "列表" in content or "list" in content:
            self._update_preference(
                PreferenceType.OUTPUT_FORMAT.value,
                "list",
                "interaction_analysis",
                0.1
            )
        elif "详细" in content or "detailed" in content:
            self._update_preference(
                PreferenceType.OUTPUT_FORMAT.value,
                "detailed",
                "interaction_analysis",
                0.1
            )
    
    def record_correction(self, original_response: str, corrected_response: str,
                         correction_type: str = "general") -> Dict[str, Any]:
        """记录用户纠正"""
        correction = {
            "id": f"corr_{int(datetime.now().timestamp())}",
            "original_response": original_response,
            "corrected_response": corrected_response,
            "correction_type": correction_type,
            "timestamp": datetime.now().isoformat()
        }
        
        self.corrections.append(correction)
        
        # 从纠正中学习
        self._learn_from_correction(correction)
        
        self._save_profile()
        
        logger.info(f"记录用户纠正: {correction_type}")
        return {"status": "success", "correction_id": correction["id"]}
    
    def _learn_from_correction(self, correction: Dict[str, Any]):
        """从纠正中学习"""
        # 分析纠正类型并更新偏好
        original = correction["original_response"].lower()
        corrected = correction["corrected_response"].lower()
        
        # 检测风格纠正
        if len(corrected) < len(original) * 0.7:
            self._update_preference(
                PreferenceType.COMMUNICATION_STYLE.value,
                "concise",
                "correction",
                0.2
            )
        elif len(corrected) > len(original) * 1.3:
            self._update_preference(
                PreferenceType.COMMUNICATION_STYLE.value,
                "detailed",
                "correction",
                0.2
            )
    
    def _update_preference(self, preference_type: str, value: Any, 
                          source: str, confidence_delta: float):
        """更新偏好"""
        if preference_type in self.preferences:
            pref = self.preferences[preference_type]
            
            # 如果值相同，增加置信度
            if pref.value == value:
                pref.confidence = min(1.0, pref.confidence + confidence_delta)
            else:
                # 如果值不同，降低置信度或更新值
                if confidence_delta > 0.15:  # 强信号（如纠正）
                    pref.value = value
                    pref.confidence = confidence_delta
                else:
                    pref.confidence = max(0.0, pref.confidence - confidence_delta * 0.5)
            
            pref.source = source
            pref.last_updated = datetime.now().isoformat()
        else:
            self.preferences[preference_type] = UserPreference(
                preference_type=preference_type,
                value=value,
                confidence=confidence_delta,
                source=source,
                last_updated=datetime.now().isoformat()
            )
    
    def record_decision(self, context: str, options: List[str], 
                       chosen_option: str, reasoning: str = "") -> Dict[str, Any]:
        """记录决策"""
        decision = DecisionRecord(
            decision_id=f"dec_{int(datetime.now().timestamp())}",
            context=context,
            options=options,
            chosen_option=chosen_option,
            reasoning=reasoning,
            outcome="pending",
            timestamp=datetime.now().isoformat()
        )
        
        self.decision_history.append(decision)
        self._save_profile()
        
        return {"status": "success", "decision_id": decision.decision_id}
    
    def update_decision_outcome(self, decision_id: str, outcome: str):
        """更新决策结果"""
        for dec in self.decision_history:
            if dec.decision_id == decision_id:
                dec.outcome = outcome
                self._save_profile()
                return {"status": "success"}
        return {"status": "error", "message": "决策不存在"}
    
    def detect_behavior_pattern(self) -> Dict[str, Any]:
        """检测行为模式"""
        # 分析最近的交互
        recent_interactions = self.interaction_history[-50:]
        
        patterns = {}
        
        # 检测时间模式
        hour_counts = {}
        for interaction in recent_interactions:
            hour = datetime.fromisoformat(interaction["timestamp"]).hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        peak_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        if peak_hours:
            patterns["active_hours"] = [h[0] for h in peak_hours]
        
        # 检测交互类型模式
        type_counts = {}
        for interaction in recent_interactions:
            itype = interaction["type"]
            type_counts[itype] = type_counts.get(itype, 0) + 1
        
        patterns["interaction_types"] = type_counts
        
        return {"status": "success", "patterns": patterns}
    
    def get_user_profile(self) -> Dict[str, Any]:
        """获取用户画像"""
        return {
            "status": "success",
            "profile": {
                "user_id": self.current_user_id,
                "preferences": {
                    pref_type: {
                        "value": pref.value,
                        "confidence": pref.confidence,
                        "source": pref.source
                    }
                    for pref_type, pref in self.preferences.items()
                },
                "behavior_patterns": {
                    pattern_id: {
                        "type": pattern.pattern_type,
                        "description": pattern.description,
                        "frequency": pattern.frequency
                    }
                    for pattern_id, pattern in self.behavior_patterns.items()
                },
                "statistics": {
                    "total_interactions": len(self.interaction_history),
                    "total_corrections": len(self.corrections),
                    "total_decisions": len(self.decision_history),
                    "preferences_count": len(self.preferences)
                }
            }
        }
    
    def get_preference(self, preference_type: str) -> Optional[Any]:
        """获取特定偏好"""
        if preference_type in self.preferences:
            pref = self.preferences[preference_type]
            if pref.confidence > 0.5:  # 只返回置信度高的偏好
                return pref.value
        return None
    
    def get_communication_style(self) -> str:
        """获取推荐的沟通风格"""
        style = self.get_preference(PreferenceType.COMMUNICATION_STYLE.value)
        return style or "balanced"
    
    def get_output_format(self) -> str:
        """获取推荐的输出格式"""
        format_pref = self.get_preference(PreferenceType.OUTPUT_FORMAT.value)
        return format_pref or "structured"
    
    def get_technical_level(self) -> str:
        """获取技术级别"""
        level = self.get_preference(PreferenceType.TECHNICAL_LEVEL.value)
        return level or "intermediate"


user_profile_modeler = UserProfileModeler()
