# -*- coding: utf-8 -*-
"""
交互复利引擎 (Interaction Compound Interest Engine)

从客户交互中学习并获得技能提升的复利模式:

摄取(Ingest):
  - 用户查询: 问题类型、意图、领域
  - 用户反馈: 满意度、纠正、偏好表达
  - 交互模式: 对话结构、响应时间、追问频率
  - 情感信号: 情绪状态、认知负荷、参与度

消化(Digest):
  - 用户偏好提取: 沟通风格、输出格式、技术级别
  - 交互模式分析: 高频问题聚类、对话路径抽象
  - 技能差距识别: 未满足需求→新技能需求
  - 情感洞察: 情绪触发器→响应策略优化

输出(Output):
  - 个性化响应策略: 按用户画像定制交互方式
  - 技能提升计划: 从交互缺口推导技能学习路线
  - 沟通优化方案: 响应速度、语气、信息密度调整
  - 主动服务建议: 基于用户行为预测需求

迭代(Iterate):
  - 交互质量验证: 满意度趋势→策略有效性
  - 高价值模式强化: 高满意度交互模式→复利增长
  - 低效模式淘汰: 低满意度策略→降级或替换
  - 跨用户迁移: 通用高价值模式→全局技能提升

与现有模块的映射:
  - 摄取 → UserStateMonitor + UserProfileModeler + EmotionalCompanion
  - 消化 → ContextAwarenessEngine + KairosEngine
  - 输出 → SkillAutoCreator + SkillSystem
  - 迭代 → DualLoopCompoundEngine(内/外循环复利桥接)

复利公式: S(n) = S(0) × (1 + i)^n
其中 i = 交互学习增量率, n = 交互轮次
"""

import time
import json
import hashlib
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from .compound_engine import (
    CompoundPhase, AssetType, AssetStatus, KnowledgeAsset
)

logger = logging.getLogger("InteractionCompound")


class InteractionType(Enum):
    QUESTION = "question"
    COMMAND = "command"
    FEEDBACK = "feedback"
    CORRECTION = "correction"
    APPROVAL = "approval"
    COMPLAINT = "complaint"
    INQUIRY = "inquiry"


class SatisfactionLevel(Enum):
    VERY_LOW = 1
    LOW = 2
    NEUTRAL = 3
    HIGH = 4
    VERY_HIGH = 5


class SkillGapSource(Enum):
    UNANSWERED_QUESTION = "unanswered_question"
    CORRECTION_FREQUENCY = "correction_frequency"
    LOW_SATISFACTION = "low_satisfaction"
    REPEATED_INQUIRY = "repeated_inquiry"
    EMOTIONAL_TRIGGER = "emotional_trigger"


@dataclass
class InteractionRecord:
    interaction_id: str
    interaction_type: InteractionType
    user_query: str = ""
    system_response: str = ""
    satisfaction: SatisfactionLevel = SatisfactionLevel.NEUTRAL
    user_correction: str = ""
    emotional_state: str = "neutral"
    cognitive_load: str = "medium"
    engagement: str = "active"
    response_time_ms: float = 0.0
    follow_up_count: int = 0
    domain: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interaction_id": self.interaction_id,
            "interaction_type": self.interaction_type.value,
            "user_query": self.user_query,
            "system_response": self.system_response,
            "user_correction": self.user_correction,
            "satisfaction": self.satisfaction.value,
            "emotional_state": self.emotional_state,
            "cognitive_load": self.cognitive_load,
            "engagement": self.engagement,
            "response_time_ms": self.response_time_ms,
            "follow_up_count": self.follow_up_count,
            "domain": self.domain,
            "timestamp": self.timestamp
        }


class InteractionCompoundCycle:
    """
    交互复利引擎

    从客户交互中学习并获得技能提升的复利循环:
    摄取(交互数据) → 消化(偏好+模式+差距) → 输出(策略+技能+优化) → 迭代(验证+强化+迁移)

    复利增量率: i=0.12 (交互学习，中频改进)
    """

    def __init__(self, core_ref=None):
        self.core = core_ref
        self._assets: Dict[str, KnowledgeAsset] = {}
        self._cycle_count = 0
        self._compound_rate = 0.12
        self._interaction_history: List[InteractionRecord] = []
        self._user_preferences: Dict[str, Dict] = {}
        self._skill_gaps: List[Dict] = []
        self._satisfaction_trend: List[float] = []
        self._domain_frequency: Dict[str, int] = defaultdict(int)
        self._correction_patterns: Dict[str, int] = defaultdict(int)
        self._bridge_data: Dict[str, Any] = {}
        self._cross_user_patterns: Dict[str, Dict] = {}

    async def ingest(self, data: Dict[str, Any]) -> List[KnowledgeAsset]:
        assets = []

        interactions = data.get("interactions", [])
        for interaction in interactions:
            iid = interaction.get("interaction_id", hashlib.sha256(
                f"inter_{time.time()}".encode()
            ).hexdigest()[:16])
            record = InteractionRecord(
                interaction_id=iid,
                interaction_type=InteractionType(interaction.get("type", "question")),
                user_query=interaction.get("query", ""),
                system_response=interaction.get("response", ""),
                satisfaction=SatisfactionLevel(interaction.get("satisfaction", 3)),
                user_correction=interaction.get("correction", ""),
                emotional_state=interaction.get("emotional_state", "neutral"),
                cognitive_load=interaction.get("cognitive_load", "medium"),
                engagement=interaction.get("engagement", "active"),
                response_time_ms=interaction.get("response_time_ms", 0),
                follow_up_count=interaction.get("follow_up_count", 0),
                domain=interaction.get("domain", "")
            )
            self._interaction_history.append(record)

            if record.domain:
                self._domain_frequency[record.domain] += 1

            if record.user_correction:
                self._correction_patterns[record.user_correction[:50]] += 1

            aid = hashlib.sha256(
                f"inter_asset_{iid}_{time.time()}".encode()
            ).hexdigest()[:16]
            sat = record.satisfaction.value
            asset = KnowledgeAsset(
                id=aid,
                asset_type=AssetType.CODE_MODULE if record.interaction_type == InteractionType.COMMAND else AssetType.ERROR_SOLUTION if record.interaction_type == InteractionType.CORRECTION else AssetType.ARCHITECTURE_PATTERN,
                phase=CompoundPhase.INGEST,
                status=AssetStatus.RAW,
                content=json.dumps(record.to_dict(), ensure_ascii=False),
                title=f"交互: {record.interaction_type.value} [{record.domain or '通用'}]",
                tags=["interaction", record.interaction_type.value, record.domain or "general", "auto_collected"],
                source="interaction_compound",
                confidence=0.3 + (sat / 5.0) * 0.5
            )
            assets.append(asset)
            self._assets[aid] = asset

        feedback_data = data.get("feedback", [])
        for fb in feedback_data:
            aid = hashlib.sha256(
                f"fb_{fb.get('topic', '')}_{time.time()}".encode()
            ).hexdigest()[:16]
            asset = KnowledgeAsset(
                id=aid, asset_type=AssetType.DEVELOPMENT_SPEC,
                phase=CompoundPhase.INGEST, status=AssetStatus.RAW,
                content=json.dumps(fb, ensure_ascii=False),
                title=f"反馈: {fb.get('topic', '未知')[:40]}",
                tags=["interaction", "feedback", fb.get("topic", ""), "auto_collected"],
                source="interaction_feedback",
                confidence=fb.get("confidence", 0.5)
            )
            assets.append(asset)
            self._assets[aid] = asset

        emotional_signals = data.get("emotional_signals", [])
        for signal in emotional_signals:
            aid = hashlib.sha256(
                f"emo_{signal.get('emotion', '')}_{time.time()}".encode()
            ).hexdigest()[:16]
            asset = KnowledgeAsset(
                id=aid, asset_type=AssetType.DEBUG_TECHNIQUE,
                phase=CompoundPhase.INGEST, status=AssetStatus.RAW,
                content=json.dumps(signal, ensure_ascii=False),
                title=f"情感信号: {signal.get('emotion', '未知')}",
                tags=["interaction", "emotion", signal.get("emotion", ""), "auto_collected"],
                source="interaction_emotion",
                confidence=0.6
            )
            assets.append(asset)
            self._assets[aid] = asset

        return assets

    async def digest(self, raw_assets: List[KnowledgeAsset]) -> List[KnowledgeAsset]:
        results = []
        for asset in raw_assets:
            if asset.status != AssetStatus.RAW:
                continue
            try:
                data = json.loads(asset.content) if isinstance(asset.content, str) else asset.content
            except (json.JSONDecodeError, TypeError):
                data = {"raw": asset.content}

            if asset.asset_type == AssetType.CODE_MODULE:
                self._digest_command_interaction(asset, data)
            elif asset.asset_type == AssetType.ERROR_SOLUTION:
                self._digest_correction_interaction(asset, data)
            elif asset.asset_type == AssetType.ARCHITECTURE_PATTERN:
                self._digest_question_interaction(asset, data)
            elif asset.asset_type == AssetType.DEVELOPMENT_SPEC:
                self._digest_feedback(asset, data)
            elif asset.asset_type == AssetType.DEBUG_TECHNIQUE:
                self._digest_emotional_signal(asset, data)

            asset.status = AssetStatus.ATOMIZED
            asset.tags.append("atomized")
            results.append(asset)

        self._identify_skill_gaps()
        return results

    def _digest_command_interaction(self, asset: KnowledgeAsset, data: Dict):
        asset.metadata.update({
            "command_type": data.get("interaction_type", "command"),
            "domain": data.get("domain", ""),
            "response_time_ms": data.get("response_time_ms", 0),
            "satisfaction": data.get("satisfaction", 3),
            "preference_hints": {
                "fast_response_preferred": data.get("response_time_ms", 0) < 1000,
                "domain": data.get("domain", "")
            }
        })

    def _digest_correction_interaction(self, asset: KnowledgeAsset, data: Dict):
        correction = data.get("user_correction", "")
        asset.metadata.update({
            "correction": correction,
            "original_response": data.get("system_response", ""),
            "skill_gap_type": SkillGapSource.CORRECTION_FREQUENCY.value,
            "learning_opportunity": bool(correction)
        })
        if correction:
            self._skill_gaps.append({
                "source": SkillGapSource.CORRECTION_FREQUENCY.value,
                "correction": correction[:100],
                "domain": data.get("domain", ""),
                "timestamp": time.time()
            })

    def _digest_question_interaction(self, asset: KnowledgeAsset, data: Dict):
        query = data.get("user_query", "")
        follow_ups = data.get("follow_up_count", 0)
        asset.metadata.update({
            "query_summary": query[:200],
            "domain": data.get("domain", ""),
            "follow_up_count": follow_ups,
            "satisfaction": data.get("satisfaction", 3),
            "needs_deep_answer": follow_ups > 2,
            "skill_gap_type": SkillGapSource.REPEATED_INQUIRY.value if follow_ups > 2 else None
        })
        if follow_ups > 2:
            self._skill_gaps.append({
                "source": SkillGapSource.REPEATED_INQUIRY.value,
                "query": query[:100],
                "domain": data.get("domain", ""),
                "follow_ups": follow_ups,
                "timestamp": time.time()
            })

    def _digest_feedback(self, asset: KnowledgeAsset, data: Dict):
        asset.metadata.update({
            "feedback_topic": data.get("topic", ""),
            "feedback_sentiment": data.get("sentiment", "neutral"),
            "improvement_suggestion": data.get("suggestion", "")
        })

    def _digest_emotional_signal(self, asset: KnowledgeAsset, data: Dict):
        emotion = data.get("emotion", "neutral")
        asset.metadata.update({
            "emotion": emotion,
            "trigger": data.get("trigger", ""),
            "optimal_response_style": self._emotion_to_style(emotion)
        })
        if emotion in ("frustrated", "angry", "anxious"):
            self._skill_gaps.append({
                "source": SkillGapSource.EMOTIONAL_TRIGGER.value,
                "emotion": emotion,
                "trigger": data.get("trigger", ""),
                "timestamp": time.time()
            })

    def _emotion_to_style(self, emotion: str) -> str:
        styles = {
            "happy": "enthusiastic_detailed",
            "sad": "gentle_supportive",
            "angry": "calm_precise",
            "anxious": "reassuring_structured",
            "frustrated": "patient_step_by_step",
            "confused": "clear_examples",
            "focused": "concise_technical",
            "neutral": "balanced_professional"
        }
        return styles.get(emotion, "balanced_professional")

    def _identify_skill_gaps(self):
        gap_sources = defaultdict(int)
        for gap in self._skill_gaps:
            gap_sources[gap["source"]] += 1

        for source, count in gap_sources.items():
            if count >= 2 and not any(g["source"] == source and g.get("consolidated") for g in self._skill_gaps):
                self._skill_gaps.append({
                    "source": source,
                    "count": count,
                    "consolidated": True,
                    "skill_needed": f"提升{source}相关技能",
                    "timestamp": time.time()
                })

    async def output(self, atomized_assets: List[KnowledgeAsset]) -> List[Dict]:
        outputs = []

        for asset in atomized_assets:
            if asset.status != AssetStatus.ATOMIZED:
                continue

            if asset.asset_type in (AssetType.CODE_MODULE, AssetType.ARCHITECTURE_PATTERN):
                sat = asset.metadata.get("satisfaction", 3)
                if sat >= 4:
                    asset.apply_compound(self._compound_rate * 1.3)
                    outputs.append({
                        "type": "high_satisfaction_pattern",
                        "asset_id": asset.id,
                        "domain": asset.metadata.get("domain", ""),
                        "satisfaction": sat,
                        "compound_value": round(asset.compound_value, 3),
                        "recommendation": "强化此交互模式，作为标准响应策略"
                    })
                elif sat <= 2:
                    asset.apply_compound(self._compound_rate * 0.3)
                    outputs.append({
                        "type": "low_satisfaction_alert",
                        "asset_id": asset.id,
                        "domain": asset.metadata.get("domain", ""),
                        "satisfaction": sat,
                        "recommendation": "此交互模式需要改进，考虑调整响应策略"
                    })
                else:
                    asset.apply_compound(self._compound_rate)
                asset.status = AssetStatus.STRUCTURED

            elif asset.asset_type == AssetType.ERROR_SOLUTION:
                if asset.metadata.get("learning_opportunity"):
                    asset.apply_compound(self._compound_rate * 1.5)
                    outputs.append({
                        "type": "skill_improvement_plan",
                        "asset_id": asset.id,
                        "correction": asset.metadata.get("correction", "")[:100],
                        "skill_gap": asset.metadata.get("skill_gap_type", ""),
                        "compound_value": round(asset.compound_value, 3),
                        "recommendation": f"从纠正中学习: {asset.metadata.get('correction', '')[:50]}"
                    })
                asset.status = AssetStatus.STRUCTURED

            elif asset.asset_type == AssetType.DEVELOPMENT_SPEC:
                asset.apply_compound(self._compound_rate * 0.8)
                outputs.append({
                    "type": "communication_optimization",
                    "asset_id": asset.id,
                    "topic": asset.metadata.get("feedback_topic", ""),
                    "suggestion": asset.metadata.get("improvement_suggestion", "")
                })
                asset.status = AssetStatus.STRUCTURED

            elif asset.asset_type == AssetType.DEBUG_TECHNIQUE:
                emotion = asset.metadata.get("emotion", "neutral")
                style = asset.metadata.get("optimal_response_style", "balanced_professional")
                asset.apply_compound(self._compound_rate)
                outputs.append({
                    "type": "emotional_response_strategy",
                    "asset_id": asset.id,
                    "emotion": emotion,
                    "recommended_style": style,
                    "recommendation": f"当用户{emotion}时，采用{style}风格响应"
                })
                asset.status = AssetStatus.STRUCTURED

        for gap in self._skill_gaps:
            if gap.get("consolidated"):
                outputs.append({
                    "type": "skill_gap_identified",
                    "source": gap["source"],
                    "count": gap.get("count", 1),
                    "skill_needed": gap.get("skill_needed", ""),
                    "recommendation": f"建议开发新技能: {gap.get('skill_needed', '未知')}"
                })

        return outputs

    async def iterate(self, all_assets: List[KnowledgeAsset]) -> Dict[str, Any]:
        deprecated = []
        optimized = []
        cross_user = defaultdict(list)

        for asset in all_assets:
            if asset.status == AssetStatus.DEPRECATED:
                continue
            domain = asset.metadata.get("domain", "general")
            cross_user[domain].append(asset)

            if asset.reuse_count == 0 and asset.compound_value < 0.25:
                asset.status = AssetStatus.DEPRECATED
                deprecated.append(asset.id)
            elif asset.reuse_count >= 2:
                asset.apply_compound(0.05)
                optimized.append(asset.id)

        for domain, domain_assets in cross_user.items():
            if len(domain_assets) >= 2:
                avg_satisfaction = sum(
                    a.metadata.get("satisfaction", 3) for a in domain_assets
                ) / len(domain_assets)
                self._cross_user_patterns[domain] = {
                    "asset_count": len(domain_assets),
                    "avg_satisfaction": round(avg_satisfaction, 2),
                    "is_high_value": avg_satisfaction >= 4
                }

        if self._interaction_history:
            recent = self._interaction_history[-20:]
            avg_sat = sum(r.satisfaction.value for r in recent) / len(recent)
            self._satisfaction_trend.append(avg_sat)

        return {
            "deprecated_count": len(deprecated),
            "optimized_count": len(optimized),
            "cross_user_patterns": len(self._cross_user_patterns),
            "skill_gaps_identified": len([g for g in self._skill_gaps if g.get("consolidated")]),
            "avg_recent_satisfaction": self._satisfaction_trend[-1] if self._satisfaction_trend else 0
        }

    async def run_cycle(self, input_data: Dict[str, Any] = None) -> Dict[str, Any]:
        self._cycle_count += 1

        raw_assets = await self.ingest(input_data or {})
        atomized = await self.digest(raw_assets)
        outputs = await self.output(atomized)
        iteration = await self.iterate(list(self._assets.values()))

        total_value = sum(a.compound_value for a in self._assets.values())

        self._bridge_data = {
            "interaction_compound_value": round(total_value, 3),
            "interaction_compound_rate": self._compound_rate,
            "interaction_count": len(self._interaction_history),
            "skill_gaps_count": len([g for g in self._skill_gaps if g.get("consolidated")]),
            "cross_user_patterns_count": len(self._cross_user_patterns),
            "avg_satisfaction": round(self._satisfaction_trend[-1], 2) if self._satisfaction_trend else 0,
            "top_domains": sorted(self._domain_frequency.items(), key=lambda x: -x[1])[:5],
            "optimized_count": iteration.get("optimized_count", 0),
            "deprecated_count": iteration.get("deprecated_count", 0)
        }

        return {
            "cycle": self._cycle_count,
            "scope": "interaction",
            "ingested": len(raw_assets),
            "atomized": len(atomized),
            "outputs_generated": len(outputs),
            "deprecated": iteration.get("deprecated_count", 0),
            "compound_value": round(total_value, 3),
            "compound_rate": self._compound_rate,
            "bridge_output": self._bridge_data,
            "skill_gaps": [g for g in self._skill_gaps if g.get("consolidated")],
            "satisfaction_trend": self._satisfaction_trend[-5:]
        }

    def get_bridge_data(self) -> Dict[str, Any]:
        return self._bridge_data

    def get_statistics(self) -> Dict[str, Any]:
        by_status = defaultdict(int)
        by_type = defaultdict(int)
        for asset in self._assets.values():
            by_status[asset.status.value] += 1
            by_type[asset.asset_type.value] += 1
        return {
            "scope": "interaction",
            "cycle_count": self._cycle_count,
            "total_assets": len(self._assets),
            "compound_value": round(sum(a.compound_value for a in self._assets.values()), 3),
            "compound_rate": self._compound_rate,
            "by_status": dict(by_status),
            "by_type": dict(by_type),
            "total_interactions": len(self._interaction_history),
            "skill_gaps_count": len([g for g in self._skill_gaps if g.get("consolidated")]),
            "cross_user_patterns": len(self._cross_user_patterns),
            "domain_distribution": dict(self._domain_frequency),
            "correction_patterns": dict(self._correction_patterns),
            "satisfaction_trend": self._satisfaction_trend[-10:]
        }


_interaction_compound: Optional[InteractionCompoundCycle] = None


def get_interaction_compound(core_ref=None) -> InteractionCompoundCycle:
    global _interaction_compound
    if _interaction_compound is None:
        _interaction_compound = InteractionCompoundCycle(core_ref)
    return _interaction_compound
