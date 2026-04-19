# -*- coding: utf-8 -*-
"""
双循环复利引擎 (Dual-Loop Compound Interest Engine)

为内循环和外循环各置一套独立的复利闭环:

内循环复利 (InnerCompoundCycle):
  聚焦操作级知识的复利增长
  摄取: 执行记录、技能调用日志、性能指标
  消化: 执行模式提取、瓶颈识别、参数关联
  输出: 技能优化建议、路由参数调优、缓存策略
  迭代: 执行效率验证、高频模式强化、低效模式淘汰

外循环复利 (OuterCompoundCycle):
  聚焦战略级知识的复利增长
  摄取: 环境变化、知识增量、系统指标、内循环桥接数据
  消化: 架构模式抽象、策略效果评估、进化趋势分析
  输出: 策略更新方案、知识整合计划、系统迭代路线图
  迭代: 策略验证、资产淘汰、跨循环知识迁移

双循环复利协同:
  内循环复利产出 → 桥接 → 外循环复利摄取
  外循环复利产出 → 桥接 → 内循环复利摄取
  形成"复利中的复利"——双层复利嵌套
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

from .interaction_compound import (
    InteractionCompoundCycle, InteractionType, SatisfactionLevel,
    SkillGapSource, InteractionRecord, get_interaction_compound
)

logger = logging.getLogger("DualLoopCompound")


class CompoundScope(Enum):
    INNER = "inner"
    OUTER = "outer"


@dataclass
class CompoundCycleResult:
    scope: CompoundScope
    cycle: int
    ingested: int = 0
    atomized: int = 0
    outputs_generated: int = 0
    deprecated: int = 0
    compound_value: float = 0.0
    compound_rate: float = 0.0
    bridge_output: Dict[str, Any] = field(default_factory=dict)


class InnerCompoundCycle:
    """
    内循环复利引擎

    聚焦操作级知识: 执行模式、技能优化、参数调优、缓存策略
    复利增量率: r=0.15 (高频操作，每次微改进累积)
    """

    def __init__(self, core_ref=None):
        self.core = core_ref
        self.scope = CompoundScope.INNER
        self._assets: Dict[str, KnowledgeAsset] = {}
        self._cycle_count = 0
        self._compound_rate = 0.15
        self._execution_patterns: Dict[str, Dict] = {}
        self._skill_usage_stats: Dict[str, int] = defaultdict(int)
        self._parameter_history: List[Dict] = []
        self._bridge_data: Dict[str, Any] = {}

    async def ingest(self, data: Dict[str, Any]) -> List[KnowledgeAsset]:
        assets = []
        execution_records = data.get("execution_records", [])
        for record in execution_records:
            aid = hashlib.sha256(
                f"inner_exec_{record.get('task', '')}_{time.time()}".encode()
            ).hexdigest()[:16]
            asset = KnowledgeAsset(
                id=aid, asset_type=AssetType.CODE_MODULE,
                phase=CompoundPhase.INGEST, status=AssetStatus.RAW,
                content=json.dumps(record, ensure_ascii=False),
                title=f"执行: {record.get('task', '未知')[:40]}",
                tags=["inner_loop", "execution", "auto_collected"],
                source="inner_loop_execution",
                confidence=0.7 if record.get("success") else 0.3
            )
            assets.append(asset)
            self._assets[aid] = asset

        skill_logs = data.get("skill_logs", [])
        for log in skill_logs:
            skill_name = log.get("skill", "unknown")
            self._skill_usage_stats[skill_name] += 1
            aid = hashlib.sha256(
                f"inner_skill_{skill_name}_{time.time()}".encode()
            ).hexdigest()[:16]
            asset = KnowledgeAsset(
                id=aid, asset_type=AssetType.SKILL_DEFINITION,
                phase=CompoundPhase.INGEST, status=AssetStatus.RAW,
                content=json.dumps(log, ensure_ascii=False),
                title=f"技能调用: {skill_name}",
                tags=["inner_loop", "skill", skill_name, "auto_collected"],
                source="inner_loop_skill",
                confidence=0.6
            )
            assets.append(asset)
            self._assets[aid] = asset

        performance_metrics = data.get("performance_metrics", {})
        if performance_metrics:
            aid = hashlib.sha256(
                f"inner_perf_{time.time()}".encode()
            ).hexdigest()[:16]
            asset = KnowledgeAsset(
                id=aid, asset_type=AssetType.DEBUG_TECHNIQUE,
                phase=CompoundPhase.INGEST, status=AssetStatus.RAW,
                content=json.dumps(performance_metrics, ensure_ascii=False),
                title="性能指标快照",
                tags=["inner_loop", "performance", "auto_collected"],
                source="inner_loop_metrics",
                confidence=0.8
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
                task = data.get("task", "")
                actions = data.get("actions", [])
                asset.metadata.update({
                    "inputs": [{"tool": a.get("tool", ""), "params": a.get("parameters", {})} for a in actions],
                    "outputs": [{"tool": a.get("tool", ""), "result": a.get("result", {})} for a in actions if "result" in a],
                    "dependencies": [a.get("tool", "") for a in actions],
                    "success": data.get("success", False)
                })
                if task:
                    pattern_key = hashlib.sha256(task.encode()).hexdigest()[:8]
                    self._execution_patterns[pattern_key] = {
                        "task": task, "action_count": len(actions),
                        "success": data.get("success", False)
                    }
            elif asset.asset_type == AssetType.SKILL_DEFINITION:
                skill_name = data.get("skill", "unknown")
                asset.metadata.update({
                    "skill_name": skill_name,
                    "usage_count": self._skill_usage_stats.get(skill_name, 0),
                    "execution_time": data.get("execution_time", 0)
                })
            elif asset.asset_type == AssetType.DEBUG_TECHNIQUE:
                asset.metadata.update({
                    "success_rate": data.get("success_rate", 0),
                    "avg_response_time": data.get("avg_response_time", 0),
                    "cache_hit_rate": data.get("cache_hit_rate", "0%")
                })

            asset.status = AssetStatus.ATOMIZED
            asset.tags.append("atomized")
            results.append(asset)
        return results

    async def output(self, atomized_assets: List[KnowledgeAsset]) -> List[Dict]:
        outputs = []
        for asset in atomized_assets:
            if asset.status != AssetStatus.ATOMIZED:
                continue

            if asset.asset_type == AssetType.CODE_MODULE:
                if asset.metadata.get("success"):
                    asset.apply_compound(self._compound_rate)
                    outputs.append({
                        "type": "execution_pattern_validated",
                        "asset_id": asset.id,
                        "title": asset.title,
                        "confidence": asset.confidence,
                        "compound_value": round(asset.compound_value, 3)
                    })
                asset.status = AssetStatus.STRUCTURED

            elif asset.asset_type == AssetType.SKILL_DEFINITION:
                usage = asset.metadata.get("usage_count", 0)
                if usage >= 2:
                    asset.apply_compound(self._compound_rate * 1.2)
                    outputs.append({
                        "type": "skill_optimization_hint",
                        "asset_id": asset.id,
                        "skill": asset.metadata.get("skill_name", ""),
                        "usage_count": usage,
                        "compound_value": round(asset.compound_value, 3)
                    })
                asset.status = AssetStatus.STRUCTURED

            elif asset.asset_type == AssetType.DEBUG_TECHNIQUE:
                asset.apply_compound(self._compound_rate * 0.8)
                cache_rate = asset.metadata.get("cache_hit_rate", "0%")
                outputs.append({
                    "type": "performance_snapshot",
                    "asset_id": asset.id,
                    "success_rate": asset.metadata.get("success_rate", 0),
                    "cache_hit_rate": cache_rate
                })
                asset.status = AssetStatus.STRUCTURED

        return outputs

    async def iterate(self, all_assets: List[KnowledgeAsset]) -> Dict[str, Any]:
        deprecated = []
        optimized = []
        for asset in all_assets:
            if asset.reuse_count == 0 and asset.compound_value < 0.3:
                asset.status = AssetStatus.DEPRECATED
                deprecated.append(asset.id)
            elif asset.reuse_count >= 2:
                asset.apply_compound(0.05)
                optimized.append(asset.id)

        top_skills = sorted(
            self._skill_usage_stats.items(),
            key=lambda x: -x[1]
        )[:5]

        return {
            "deprecated_count": len(deprecated),
            "optimized_count": len(optimized),
            "top_skills": top_skills,
            "execution_patterns_found": len(self._execution_patterns)
        }

    async def run_cycle(self, input_data: Dict[str, Any] = None) -> CompoundCycleResult:
        self._cycle_count += 1
        start_time = time.time()

        raw_assets = await self.ingest(input_data or {})
        atomized = await self.digest(raw_assets)
        outputs = await self.output(atomized)
        iteration = await self.iterate(list(self._assets.values()))

        total_value = sum(a.compound_value for a in self._assets.values())

        self._bridge_data = {
            "inner_compound_value": round(total_value, 3),
            "inner_compound_rate": self._compound_rate,
            "inner_execution_patterns": len(self._execution_patterns),
            "inner_top_skills": iteration.get("top_skills", [])[:3],
            "inner_optimized_count": iteration.get("optimized_count", 0),
            "inner_deprecated_count": iteration.get("deprecated_count", 0)
        }

        return CompoundCycleResult(
            scope=self.scope,
            cycle=self._cycle_count,
            ingested=len(raw_assets),
            atomized=len(atomized),
            outputs_generated=len(outputs),
            deprecated=iteration.get("deprecated_count", 0),
            compound_value=round(total_value, 3),
            compound_rate=self._compound_rate,
            bridge_output=self._bridge_data
        )

    def get_bridge_data(self) -> Dict[str, Any]:
        return self._bridge_data

    def get_statistics(self) -> Dict[str, Any]:
        by_status = defaultdict(int)
        for asset in self._assets.values():
            by_status[asset.status.value] += 1
        return {
            "scope": self.scope.value,
            "cycle_count": self._cycle_count,
            "total_assets": len(self._assets),
            "compound_value": round(sum(a.compound_value for a in self._assets.values()), 3),
            "compound_rate": self._compound_rate,
            "by_status": dict(by_status),
            "execution_patterns": len(self._execution_patterns),
            "skill_usage": dict(self._skill_usage_stats)
        }


class OuterCompoundCycle:
    """
    外循环复利引擎

    聚焦战略级知识: 架构模式、策略迭代、系统进化、跨循环迁移
    复利增量率: r=0.10 (低频战略，每次大幅改进)
    """

    def __init__(self, core_ref=None):
        self.core = core_ref
        self.scope = CompoundScope.OUTER
        self._assets: Dict[str, KnowledgeAsset] = {}
        self._cycle_count = 0
        self._compound_rate = 0.10
        self._strategy_history: List[Dict] = []
        self._architecture_patterns: Dict[str, Dict] = {}
        self._evolution_trends: List[Dict] = []
        self._bridge_data: Dict[str, Any] = {}
        self._cross_loop_knowledge: List[Dict] = []

    async def ingest(self, data: Dict[str, Any]) -> List[KnowledgeAsset]:
        assets = []

        environment_changes = data.get("environment_changes", [])
        for change in environment_changes:
            aid = hashlib.sha256(
                f"outer_env_{change.get('type', '')}_{time.time()}".encode()
            ).hexdigest()[:16]
            asset = KnowledgeAsset(
                id=aid, asset_type=AssetType.ARCHITECTURE_PATTERN,
                phase=CompoundPhase.INGEST, status=AssetStatus.RAW,
                content=json.dumps(change, ensure_ascii=False),
                title=f"环境变化: {change.get('type', '未知')[:40]}",
                tags=["outer_loop", "environment", "auto_collected"],
                source="outer_loop_environment",
                confidence=0.6
            )
            assets.append(asset)
            self._assets[aid] = asset

        knowledge_updates = data.get("knowledge_updates", [])
        for update in knowledge_updates:
            aid = hashlib.sha256(
                f"outer_know_{update.get('topic', '')}_{time.time()}".encode()
            ).hexdigest()[:16]
            asset = KnowledgeAsset(
                id=aid, asset_type=AssetType.ARCHITECTURE_PATTERN,
                phase=CompoundPhase.INGEST, status=AssetStatus.RAW,
                content=json.dumps(update, ensure_ascii=False),
                title=f"知识更新: {update.get('topic', '未知')[:40]}",
                tags=["outer_loop", "knowledge", "auto_collected"],
                source="outer_loop_knowledge",
                confidence=update.get("confidence", 0.5)
            )
            assets.append(asset)
            self._assets[aid] = asset

        inner_bridge = data.get("inner_bridge_data", {})
        if inner_bridge:
            aid = hashlib.sha256(
                f"outer_bridge_{time.time()}".encode()
            ).hexdigest()[:16]
            asset = KnowledgeAsset(
                id=aid, asset_type=AssetType.ARCHITECTURE_PATTERN,
                phase=CompoundPhase.INGEST, status=AssetStatus.RAW,
                content=json.dumps(inner_bridge, ensure_ascii=False),
                title="内循环桥接数据",
                tags=["outer_loop", "bridge", "cross_loop", "auto_collected"],
                source="inner_to_outer_bridge",
                confidence=0.8
            )
            assets.append(asset)
            self._assets[aid] = asset
            self._cross_loop_knowledge.append(inner_bridge)

        strategy_results = data.get("strategy_results", {})
        if strategy_results:
            aid = hashlib.sha256(
                f"outer_strategy_{time.time()}".encode()
            ).hexdigest()[:16]
            asset = KnowledgeAsset(
                id=aid, asset_type=AssetType.DEVELOPMENT_SPEC,
                phase=CompoundPhase.INGEST, status=AssetStatus.RAW,
                content=json.dumps(strategy_results, ensure_ascii=False),
                title="策略执行结果",
                tags=["outer_loop", "strategy", "auto_collected"],
                source="outer_loop_strategy",
                confidence=0.7
            )
            assets.append(asset)
            self._assets[aid] = asset
            self._strategy_history.append(strategy_results)

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

            if asset.asset_type == AssetType.ARCHITECTURE_PATTERN:
                asset.metadata.update({
                    "scenario": data.get("scenario", data.get("type", "")),
                    "advantages": data.get("advantages", []),
                    "limitations": data.get("limitations", []),
                    "pattern_type": data.get("pattern_type", "unknown")
                })
                if "bridge" in asset.tags:
                    asset.metadata.update({
                        "inner_compound_value": data.get("inner_compound_value", 0),
                        "inner_execution_patterns": data.get("inner_execution_patterns", 0),
                        "inner_top_skills": data.get("inner_top_skills", [])
                    })
                pattern_key = data.get("scenario", data.get("type", "unknown"))
                self._architecture_patterns[pattern_key] = {
                    "advantages": data.get("advantages", []),
                    "limitations": data.get("limitations", [])
                }

            elif asset.asset_type == AssetType.DEVELOPMENT_SPEC:
                asset.metadata.update({
                    "strategy_effectiveness": data.get("effectiveness", 0),
                    "strategy_type": data.get("type", "unknown"),
                    "applied_count": data.get("applied_count", 0)
                })

            asset.status = AssetStatus.ATOMIZED
            asset.tags.append("atomized")
            results.append(asset)
        return results

    async def output(self, atomized_assets: List[KnowledgeAsset]) -> List[Dict]:
        outputs = []
        for asset in atomized_assets:
            if asset.status != AssetStatus.ATOMIZED:
                continue

            if asset.asset_type == AssetType.ARCHITECTURE_PATTERN:
                asset.apply_compound(self._compound_rate)
                if "bridge" in asset.tags:
                    inner_cv = asset.metadata.get("inner_compound_value", 0)
                    outputs.append({
                        "type": "cross_loop_synthesis",
                        "asset_id": asset.id,
                        "inner_compound_value": inner_cv,
                        "synthesis": f"内循环复利价值={inner_cv}, 需评估是否需要策略调整"
                    })
                else:
                    outputs.append({
                        "type": "architecture_pattern_validated",
                        "asset_id": asset.id,
                        "scenario": asset.metadata.get("scenario", ""),
                        "compound_value": round(asset.compound_value, 3)
                    })
                asset.status = AssetStatus.STRUCTURED

            elif asset.asset_type == AssetType.DEVELOPMENT_SPEC:
                effectiveness = asset.metadata.get("strategy_effectiveness", 0)
                if effectiveness > 0.5:
                    asset.apply_compound(self._compound_rate * 1.5)
                    outputs.append({
                        "type": "strategy_update_proposal",
                        "asset_id": asset.id,
                        "strategy_type": asset.metadata.get("strategy_type", ""),
                        "effectiveness": effectiveness,
                        "compound_value": round(asset.compound_value, 3)
                    })
                else:
                    asset.apply_compound(self._compound_rate * 0.5)
                    outputs.append({
                        "type": "strategy_review_needed",
                        "asset_id": asset.id,
                        "effectiveness": effectiveness
                    })
                asset.status = AssetStatus.STRUCTURED

        return outputs

    async def iterate(self, all_assets: List[KnowledgeAsset]) -> Dict[str, Any]:
        deprecated = []
        optimized = []
        strategy_updates = []

        for asset in all_assets:
            if asset.status == AssetStatus.DEPRECATED:
                continue
            if asset.reuse_count == 0 and asset.compound_value < 0.2:
                asset.status = AssetStatus.DEPRECATED
                deprecated.append(asset.id)
            elif asset.reuse_count >= 2:
                asset.apply_compound(0.05)
                optimized.append(asset.id)
                if asset.asset_type == AssetType.DEVELOPMENT_SPEC:
                    strategy_updates.append({
                        "type": asset.metadata.get("strategy_type", ""),
                        "value": round(asset.compound_value, 3)
                    })

        self._evolution_trends.append({
            "cycle": self._cycle_count,
            "total_assets": len(all_assets),
            "deprecated": len(deprecated),
            "optimized": len(optimized)
        })

        return {
            "deprecated_count": len(deprecated),
            "optimized_count": len(optimized),
            "strategy_updates": strategy_updates,
            "architecture_patterns_found": len(self._architecture_patterns),
            "cross_loop_transfers": len(self._cross_loop_knowledge)
        }

    async def run_cycle(self, input_data: Dict[str, Any] = None) -> CompoundCycleResult:
        self._cycle_count += 1
        start_time = time.time()

        raw_assets = await self.ingest(input_data or {})
        atomized = await self.digest(raw_assets)
        outputs = await self.output(atomized)
        iteration = await self.iterate(list(self._assets.values()))

        total_value = sum(a.compound_value for a in self._assets.values())

        self._bridge_data = {
            "outer_compound_value": round(total_value, 3),
            "outer_compound_rate": self._compound_rate,
            "outer_architecture_patterns": len(self._architecture_patterns),
            "outer_strategy_updates": iteration.get("strategy_updates", []),
            "outer_cross_loop_transfers": iteration.get("cross_loop_transfers", 0),
            "outer_optimized_count": iteration.get("optimized_count", 0),
            "outer_deprecated_count": iteration.get("deprecated_count", 0)
        }

        return CompoundCycleResult(
            scope=self.scope,
            cycle=self._cycle_count,
            ingested=len(raw_assets),
            atomized=len(atomized),
            outputs_generated=len(outputs),
            deprecated=iteration.get("deprecated_count", 0),
            compound_value=round(total_value, 3),
            compound_rate=self._compound_rate,
            bridge_output=self._bridge_data
        )

    def get_bridge_data(self) -> Dict[str, Any]:
        return self._bridge_data

    def get_statistics(self) -> Dict[str, Any]:
        by_status = defaultdict(int)
        by_type = defaultdict(int)
        for asset in self._assets.values():
            by_status[asset.status.value] += 1
            by_type[asset.asset_type.value] += 1
        return {
            "scope": self.scope.value,
            "cycle_count": self._cycle_count,
            "total_assets": len(self._assets),
            "compound_value": round(sum(a.compound_value for a in self._assets.values()), 3),
            "compound_rate": self._compound_rate,
            "by_status": dict(by_status),
            "by_type": dict(by_type),
            "architecture_patterns": len(self._architecture_patterns),
            "strategy_history_count": len(self._strategy_history),
            "cross_loop_transfers": len(self._cross_loop_knowledge)
        }


class DualLoopCompoundEngine:
    """
    双循环复利引擎

    内循环复利 + 外循环复利 + 双层复利桥接

    架构:
    ┌──────────────────────────────────────────────────┐
    │          DualLoopCompoundEngine                    │
    │                                                    │
    │  ┌──────────────────┐  ┌──────────────────────┐  │
    │  │ InnerCompoundCycle│  │ OuterCompoundCycle   │  │
    │  │ 操作级复利        │  │ 战略级复利           │  │
    │  │ r=0.15 高频      │  │ r=0.10 低频          │  │
    │  │ 执行模式/技能优化 │  │ 架构模式/策略迭代    │  │
    │  └────────┬─────────┘  └──────────┬───────────┘  │
    │           │                       │               │
    │           └─────── 复利桥接 ───────┘               │
    │            内→外: 执行模式+技能统计                │
    │            外→内: 策略更新+架构建议                │
    └──────────────────────────────────────────────────┘
    """

    def __init__(self, core_ref=None):
        self.core = core_ref
        self.inner_compound = InnerCompoundCycle(core_ref)
        self.outer_compound = OuterCompoundCycle(core_ref)
        self.interaction_compound = get_interaction_compound(core_ref)
        self._cycle_count = 0
        self._history: List[Dict] = []

    async def run_inner_compound(self, input_data: Dict[str, Any] = None) -> CompoundCycleResult:
        return await self.inner_compound.run_cycle(input_data)

    async def run_outer_compound(self, input_data: Dict[str, Any] = None) -> CompoundCycleResult:
        return await self.outer_compound.run_cycle(input_data)

    async def run_interaction_compound(self, input_data: Dict[str, Any] = None) -> Dict[str, Any]:
        return await self.interaction_compound.run_cycle(input_data)

    async def run_dual_compound(self, inner_data: Dict[str, Any] = None,
                                 outer_data: Dict[str, Any] = None,
                                 interaction_data: Dict[str, Any] = None) -> Dict[str, Any]:
        self._cycle_count += 1

        inner_result = await self.inner_compound.run_cycle(inner_data or {})

        outer_input = outer_data or {}
        outer_input["inner_bridge_data"] = self.inner_compound.get_bridge_data()

        outer_result = await self.outer_compound.run_cycle(outer_input)

        interaction_input = interaction_data or {}
        interaction_input["inner_bridge"] = self.inner_compound.get_bridge_data()
        interaction_input["outer_bridge"] = self.outer_compound.get_bridge_data()

        interaction_result = await self.interaction_compound.run_cycle(interaction_input)

        cross_loop_data = {
            "inner_to_outer": self.inner_compound.get_bridge_data(),
            "outer_to_inner": self.outer_compound.get_bridge_data(),
            "interaction_to_inner": {
                "skill_gaps": interaction_result.get("skill_gaps", []),
                "satisfaction_trend": interaction_result.get("satisfaction_trend", [])
            },
            "interaction_to_outer": {
                "cross_user_patterns": self.interaction_compound._cross_user_patterns,
                "domain_distribution": dict(self.interaction_compound._domain_frequency)
            }
        }

        result = {
            "cycle": self._cycle_count,
            "inner_compound": {
                "cycle": inner_result.cycle,
                "ingested": inner_result.ingested,
                "atomized": inner_result.atomized,
                "outputs_generated": inner_result.outputs_generated,
                "compound_value": inner_result.compound_value,
                "compound_rate": inner_result.compound_rate
            },
            "outer_compound": {
                "cycle": outer_result.cycle,
                "ingested": outer_result.ingested,
                "atomized": outer_result.atomized,
                "outputs_generated": outer_result.outputs_generated,
                "compound_value": outer_result.compound_value,
                "compound_rate": outer_result.compound_rate
            },
            "interaction_compound": {
                "cycle": interaction_result.get("cycle", 0),
                "ingested": interaction_result.get("ingested", 0),
                "atomized": interaction_result.get("atomized", 0),
                "outputs_generated": interaction_result.get("outputs_generated", 0),
                "compound_value": interaction_result.get("compound_value", 0),
                "compound_rate": interaction_result.get("compound_rate", 0),
                "skill_gaps_count": interaction_result.get("bridge_output", {}).get("skill_gaps_count", 0),
                "avg_satisfaction": interaction_result.get("bridge_output", {}).get("avg_satisfaction", 0)
            },
            "cross_loop_bridge": cross_loop_data,
            "total_compound_value": round(
                inner_result.compound_value + outer_result.compound_value +
                interaction_result.get("compound_value", 0), 3
            )
        }

        self._history.append(result)
        if len(self._history) > 200:
            self._history = self._history[-200:]

        return result

    def get_statistics(self) -> Dict[str, Any]:
        inner_stats = self.inner_compound.get_statistics()
        outer_stats = self.outer_compound.get_statistics()
        interaction_stats = self.interaction_compound.get_statistics()
        return {
            "total_cycles": self._cycle_count,
            "inner_compound": inner_stats,
            "outer_compound": outer_stats,
            "interaction_compound": interaction_stats,
            "total_compound_value": round(
                inner_stats.get("compound_value", 0) +
                outer_stats.get("compound_value", 0) +
                interaction_stats.get("compound_value", 0), 3
            ),
            "cross_loop_bridge": {
                "inner_to_outer": self.inner_compound.get_bridge_data(),
                "outer_to_inner": self.outer_compound.get_bridge_data(),
                "interaction_bridge": self.interaction_compound.get_bridge_data()
            }
        }

    def get_trajectory(self, last_n: int = 10) -> List[Dict]:
        return self._history[-last_n:]


_dual_loop_compound: Optional[DualLoopCompoundEngine] = None


def get_dual_loop_compound(core_ref=None) -> DualLoopCompoundEngine:
    global _dual_loop_compound
    if _dual_loop_compound is None:
        _dual_loop_compound = DualLoopCompoundEngine(core_ref)
    return _dual_loop_compound
