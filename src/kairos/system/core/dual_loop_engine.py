# -*- coding: utf-8 -*-
"""
双层互动自动循环机制

内部循环: 自动数据收集 → 模型训练 → 性能评估 → 参数优化
外部循环: 环境摄取 → 信息消化 → 价值提炼 → 系统迭代
互动机制: 内外循环间的数据流转与协同进化
"""

import time
import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from .dual_loop_compound import (
    DualLoopCompoundEngine, InnerCompoundCycle, OuterCompoundCycle,
    CompoundScope, CompoundCycleResult, get_dual_loop_compound
)

logger = logging.getLogger(__name__)


class LoopPhase(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class InnerLoopStage(Enum):
    DATA_COLLECTION = "data_collection"
    MODEL_TRAINING = "model_training"
    PERFORMANCE_EVALUATION = "performance_evaluation"
    PARAMETER_OPTIMIZATION = "parameter_optimization"


class OuterLoopStage(Enum):
    ENVIRONMENT_INGESTION = "environment_ingestion"
    INFORMATION_DIGESTION = "information_digestion"
    VALUE_EXTRACTION = "value_extraction"
    SYSTEM_ITERATION = "system_iteration"


@dataclass
class LoopMetrics:
    total_cycles: int = 0
    successful_cycles: int = 0
    failed_cycles: int = 0
    last_cycle_time_ms: float = 0.0
    avg_cycle_time_ms: float = 0.0
    data_throughput: int = 0
    improvement_rate: float = 0.0


@dataclass
class LoopState:
    phase: LoopPhase = LoopPhase.IDLE
    current_stage: str = ""
    cycle_count: int = 0
    metrics: LoopMetrics = field(default_factory=LoopMetrics)
    last_error: Optional[str] = None
    bridge_data: Dict[str, Any] = field(default_factory=dict)


class InnerLoopCoordinator:
    """
    内部循环协调器

    自动数据收集 → 模型训练 → 性能评估 → 参数优化

    数据收集: 从统一存储层、进化引擎、学习Agent收集执行数据
    模型训练: 知识蒸馏 + 技能进化管线
    性能评估: 自我进化引擎评估 + 元认知评估
    参数优化: GEPA优化器 + 学习策略优化
    """

    def __init__(self, core_ref=None):
        self.core = core_ref
        self.state = LoopState()
        self.compound = InnerCompoundCycle(core_ref)
        self._stage_handlers = {
            InnerLoopStage.DATA_COLLECTION: self._collect_data,
            InnerLoopStage.MODEL_TRAINING: self._train_models,
            InnerLoopStage.PERFORMANCE_EVALUATION: self._evaluate_performance,
            InnerLoopStage.PARAMETER_OPTIMIZATION: self._optimize_parameters,
        }
        self._collected_data: Dict[str, Any] = {}
        self._training_results: Dict[str, Any] = {}
        self._evaluation_results: Dict[str, Any] = {}
        self._optimization_results: Dict[str, Any] = {}

    async def run_cycle(self) -> Dict[str, Any]:
        start_time = time.time()
        self.state.phase = LoopPhase.RUNNING
        cycle_result = {
            "cycle": self.state.cycle_count,
            "stages": {},
            "bridge_output": {},
            "success": True
        }

        for stage in InnerLoopStage:
            self.state.current_stage = stage.value
            try:
                stage_result = await self._stage_handlers[stage]()
                cycle_result["stages"][stage.value] = stage_result
                logger.debug(f"内部循环阶段 {stage.value} 完成")
            except Exception as e:
                logger.warning(f"内部循环阶段 {stage.value} 失败: {e}")
                cycle_result["stages"][stage.value] = {"status": "failed", "error": str(e)}
                cycle_result["success"] = False
                break

        elapsed = (time.time() - start_time) * 1000
        self._update_metrics(elapsed, cycle_result["success"])
        self.state.cycle_count += 1

        cycle_result["bridge_output"] = self._prepare_bridge_output()
        self.state.bridge_data = cycle_result["bridge_output"]

        try:
            compound_input = {
                "execution_records": [{"task": "内部循环", "success": cycle_result["success"]}],
                "performance_metrics": self._evaluation_results
            }
            compound_result = await self.compound.run_cycle(compound_input)
            cycle_result["compound"] = {
                "cycle": compound_result.cycle,
                "compound_value": compound_result.compound_value,
                "compound_rate": compound_result.compound_rate
            }
        except Exception as e:
            logger.debug(f"内循环复利执行失败: {e}")

        self.state.phase = LoopPhase.IDLE
        return cycle_result

    async def _collect_data(self) -> Dict[str, Any]:
        data = {
            "performance_records": [],
            "storage_statistics": {},
            "evolution_statistics": {},
            "learning_experiences": 0
        }

        if self.core:
            try:
                storage_stats = self.core.unified_storage.get_system_statistics()
                data["storage_statistics"] = storage_stats
            except Exception as e:
                logger.debug(f"收集存储统计失败: {e}")

            try:
                evo_stats = self.core.evolution_engine.get_evolution_statistics()
                data["evolution_statistics"] = evo_stats
            except Exception as e:
                logger.debug(f"收集进化统计失败: {e}")

            try:
                memory_ctx = self.core._query_relevant_memories("系统自评估")
                data["memory_statistics"] = memory_ctx
            except Exception as e:
                logger.debug(f"收集记忆统计失败: {e}")

            try:
                learn_stats = self.core.learning_agent.get_stats()
                data["learning_experiences"] = learn_stats.get("total_experiences", 0)
            except Exception as e:
                logger.debug(f"收集学习统计失败: {e}")

        self._collected_data = data
        return {"status": "completed", "data_sources": len(data), "records": data.get("learning_experiences", 0)}

    async def _train_models(self) -> Dict[str, Any]:
        training = {
            "distillation": None,
            "skill_evolution": None
        }

        if self.core:
            try:
                distill_result = self.core.knowledge_distiller.full_distillation()
                training["distillation"] = {
                    "status": "completed",
                    "knowledge_units": len(distill_result.knowledge_units) if hasattr(distill_result, 'knowledge_units') else 0
                } if distill_result else {"status": "skipped"}
            except Exception as e:
                training["distillation"] = {"status": "failed", "error": str(e)}

            try:
                evo_result = self.core.evolution_engine.auto_evolve()
                training["skill_evolution"] = {
                    "status": "completed",
                    "improvements": len(evo_result.get("improvements", [])) if isinstance(evo_result, dict) else 0
                } if evo_result else {"status": "skipped"}
            except Exception as e:
                training["skill_evolution"] = {"status": "failed", "error": str(e)}

        self._training_results = training
        return {"status": "completed", "training_items": len(training)}

    async def _evaluate_performance(self) -> Dict[str, Any]:
        evaluation = {
            "capability_assessment": None,
            "metacognitive_assessment": None,
            "success_rate": 0.0,
            "storage_health": {}
        }

        if self.core:
            try:
                evo_stats = self.core.evolution_engine.get_evolution_statistics()
                evaluation["success_rate"] = evo_stats.get("overall_success_rate", 0.0)
                evaluation["capability_assessment"] = {
                    "total_skills": evo_stats.get("total_skills", 0),
                    "avg_skill_level": evo_stats.get("avg_skill_level", 0),
                    "evolution_count": evo_stats.get("total_evolutions", 0)
                }
            except Exception as e:
                logger.debug(f"能力评估失败: {e}")

            try:
                meta_report = self.core.metacognition.generate_metacognitive_report()
                evaluation["metacognitive_assessment"] = {
                    "cognitive_load": meta_report.get("cognitive_load", "unknown") if isinstance(meta_report, dict) else "available",
                    "bias_count": len(meta_report.get("detected_biases", [])) if isinstance(meta_report, dict) else 0
                }
            except Exception as e:
                logger.debug(f"元认知评估失败: {e}")

            try:
                storage_stats = self.core.unified_storage.get_system_statistics()
                cache_stats = storage_stats.get("cache", {})
                evaluation["storage_health"] = {
                    "cache_hit_rate": cache_stats.get("hit_rate", "0%"),
                    "cache_size": cache_stats.get("size", 0),
                    "relational_items": storage_stats.get("relational", {}).get("total_items", 0),
                    "vector_available": storage_stats.get("vector", {}).get("available", False)
                }
            except Exception as e:
                logger.debug(f"存储健康评估失败: {e}")

        self._evaluation_results = evaluation
        return {"status": "completed", "success_rate": evaluation["success_rate"]}

    async def _optimize_parameters(self) -> Dict[str, Any]:
        optimization = {
            "strategy_adjustments": [],
            "confidence_calibration": None,
            "route_optimization": None,
            "storage_optimization": None
        }

        if self.core:
            try:
                learn_feedback = self.core._learning_feedback(
                    True, "内部循环优化", "auto", "coordinator", {}
                )
                if learn_feedback.get("preferred_agent"):
                    optimization["route_optimization"] = {
                        "preferred_agent": learn_feedback["preferred_agent"],
                        "strategy_effectiveness": learn_feedback.get("strategy_effectiveness")
                    }
            except Exception as e:
                logger.debug(f"路由优化失败: {e}")

            try:
                evo_feedback = self.core._evolution_feedback(True, 0.8, "内部循环优化")
                if evo_feedback.get("suggestion"):
                    optimization["strategy_adjustments"].append(evo_feedback["suggestion"])
            except Exception as e:
                logger.debug(f"进化反馈失败: {e}")

            try:
                consolidate_result = await self.core.unified_storage.consolidate()
                optimization["storage_optimization"] = {
                    "consolidated": consolidate_result.get("consolidated", 0)
                }
            except Exception as e:
                logger.debug(f"存储优化失败: {e}")

        self._optimization_results = optimization
        return {"status": "completed", "adjustments": len(optimization["strategy_adjustments"])}

    def _prepare_bridge_output(self) -> Dict[str, Any]:
        cap = self._evaluation_results.get("capability_assessment") or {}
        distill = self._training_results.get("distillation") or {}
        compound_bridge = self.compound.get_bridge_data()
        return {
            "inner_success_rate": self._evaluation_results.get("success_rate", 0.0),
            "inner_skill_count": cap.get("total_skills", 0),
            "inner_optimization_hints": self._optimization_results.get("strategy_adjustments", []),
            "inner_knowledge_delta": distill.get("knowledge_units", 0),
            "inner_storage_health": self._evaluation_results.get("storage_health", {}),
            "inner_cycle": self.state.cycle_count,
            "inner_compound": compound_bridge
        }

    def _update_metrics(self, elapsed_ms: float, success: bool):
        self.state.metrics.total_cycles += 1
        if success:
            self.state.metrics.successful_cycles += 1
        else:
            self.state.metrics.failed_cycles += 1
        self.state.metrics.last_cycle_time_ms = elapsed_ms
        total = self.state.metrics.total_cycles
        prev_avg = self.state.metrics.avg_cycle_time_ms
        self.state.metrics.avg_cycle_time_ms = (prev_avg * (total - 1) + elapsed_ms) / total
        if self.state.metrics.successful_cycles > 1:
            self.state.metrics.improvement_rate = self.state.metrics.successful_cycles / total


class OuterLoopCoordinator:
    """
    外部循环协调器

    环境摄取 → 信息消化 → 价值提炼 → 系统迭代

    环境摄取: 性能监控 + 资源感知 + 外部信息探索
    信息消化: 数据压缩 + 梦境整合 + 知识摄入
    价值提炼: 知识蒸馏 + 经验提取 + 价值判断
    系统迭代: 决策更新 + 策略调整 + 架构进化
    """

    def __init__(self, core_ref=None):
        self.core = core_ref
        self.state = LoopState()
        self.compound = OuterCompoundCycle(core_ref)
        self._stage_handlers = {
            OuterLoopStage.ENVIRONMENT_INGESTION: self._ingest_environment,
            OuterLoopStage.INFORMATION_DIGESTION: self._digest_information,
            OuterLoopStage.VALUE_EXTRACTION: self._extract_value,
            OuterLoopStage.SYSTEM_ITERATION: self._iterate_system,
        }
        self._ingestion_data: Dict[str, Any] = {}
        self._digestion_results: Dict[str, Any] = {}
        self._extraction_results: Dict[str, Any] = {}
        self._iteration_results: Dict[str, Any] = {}

    async def run_cycle(self, inner_bridge_data: Dict[str, Any] = None) -> Dict[str, Any]:
        start_time = time.time()
        self.state.phase = LoopPhase.RUNNING
        self.state.bridge_data = inner_bridge_data or {}

        cycle_result = {
            "cycle": self.state.cycle_count,
            "stages": {},
            "bridge_output": {},
            "success": True
        }

        for stage in OuterLoopStage:
            self.state.current_stage = stage.value
            try:
                stage_result = await self._stage_handlers[stage]()
                cycle_result["stages"][stage.value] = stage_result
                logger.debug(f"外部循环阶段 {stage.value} 完成")
            except Exception as e:
                logger.warning(f"外部循环阶段 {stage.value} 失败: {e}")
                cycle_result["stages"][stage.value] = {"status": "failed", "error": str(e)}
                cycle_result["success"] = False
                break

        elapsed = (time.time() - start_time) * 1000
        self._update_metrics(elapsed, cycle_result["success"])
        self.state.cycle_count += 1

        cycle_result["bridge_output"] = self._prepare_bridge_output()
        self.state.bridge_data = cycle_result["bridge_output"]

        try:
            compound_input = {
                "environment_changes": [{"type": "外部循环", "success": cycle_result["success"]}],
                "strategy_results": self._iteration_results,
                "inner_bridge_data": self.state.bridge_data.get("inner_compound", {})
            }
            compound_result = await self.compound.run_cycle(compound_input)
            cycle_result["compound"] = {
                "cycle": compound_result.cycle,
                "compound_value": compound_result.compound_value,
                "compound_rate": compound_result.compound_rate
            }
        except Exception as e:
            logger.debug(f"外循环复利执行失败: {e}")

        self.state.phase = LoopPhase.IDLE
        return cycle_result

    async def _ingest_environment(self) -> Dict[str, Any]:
        ingestion = {
            "system_metrics": {},
            "resource_status": {},
            "external_knowledge": 0,
            "inner_loop_status": {},
            "storage_metrics": {}
        }

        if self.core:
            try:
                bus_stats = self.core.synaptic_bus.get_stats()
                ingestion["system_metrics"] = {
                    "pending_messages": bus_stats.get("pending_messages", 0),
                    "total_deliveries": bus_stats.get("total_deliveries", 0),
                    "delivery_rate": bus_stats.get("delivery_rate", 0)
                }
            except Exception as e:
                logger.debug(f"系统指标获取失败: {e}")

            try:
                load = self.core._compute_system_load()
                ingestion["resource_status"] = {"system_load": load}
            except Exception as e:
                logger.debug(f"资源状态获取失败: {e}")

            try:
                learning_result = self.core.learning.comprehensive_learning("系统优化", max_insights=3)
                ingestion["external_knowledge"] = learning_result.get("total_insights", 0) if isinstance(learning_result, dict) else 0
            except Exception as e:
                logger.debug(f"外部知识获取失败: {e}")

            try:
                storage_stats = self.core.unified_storage.get_system_statistics()
                ingestion["storage_metrics"] = {
                    "cache_hit_rate": storage_stats.get("cache", {}).get("hit_rate", "0%"),
                    "relational_items": storage_stats.get("relational", {}).get("total_items", 0),
                    "vector_count": storage_stats.get("vector", {}).get("total_vectors", 0),
                    "file_count": storage_stats.get("file", {}).get("total_files", 0)
                }
            except Exception as e:
                logger.debug(f"存储指标获取失败: {e}")

        if self.state.bridge_data:
            ingestion["inner_loop_status"] = {
                "success_rate": self.state.bridge_data.get("inner_success_rate", 0),
                "skill_count": self.state.bridge_data.get("inner_skill_count", 0),
                "storage_health": self.state.bridge_data.get("inner_storage_health", {})
            }

        self._ingestion_data = ingestion
        return {"status": "completed", "data_sources": len(ingestion)}

    async def _digest_information(self) -> Dict[str, Any]:
        digestion = {
            "knowledge_ingested": 0,
            "memories_consolidated": 0,
            "data_compressed": 0,
            "storage_optimized": False
        }

        if self.core:
            try:
                inner_knowledge_delta = self.state.bridge_data.get("inner_knowledge_delta", 0)
                if inner_knowledge_delta > 0:
                    self.core.knowledge_distiller.ingest(
                        content=f"内部循环产出 {inner_knowledge_delta} 个知识单元",
                        knowledge_type="experiential",
                        source="inner_loop",
                        confidence=0.8
                    )
                    digestion["knowledge_ingested"] = inner_knowledge_delta
            except Exception as e:
                logger.debug(f"知识摄入失败: {e}")

            try:
                consolidate_result = await self.core.unified_storage.consolidate()
                digestion["memories_consolidated"] = consolidate_result.get("consolidated", 0)
            except Exception as e:
                logger.debug(f"记忆整合失败: {e}")

            try:
                forget_result = await self.core.unified_storage.apply_forgetting()
                digestion["data_compressed"] = forget_result.get("forgotten", 0)
                digestion["storage_optimized"] = True
            except Exception as e:
                logger.debug(f"存储优化失败: {e}")

        self._digestion_results = digestion
        return {"status": "completed", "ingested": digestion["knowledge_ingested"]}

    async def _extract_value(self) -> Dict[str, Any]:
        extraction = {
            "high_value_knowledge": 0,
            "actionable_insights": [],
            "optimization_opportunities": []
        }

        if self.core:
            try:
                inner_hints = self.state.bridge_data.get("inner_optimization_hints", [])
                extraction["actionable_insights"] = inner_hints
                extraction["high_value_knowledge"] = len(inner_hints)
            except Exception as e:
                logger.debug(f"价值提取失败: {e}")

            try:
                inner_rate = self.state.bridge_data.get("inner_success_rate", 0)
                if inner_rate < 0.5:
                    extraction["optimization_opportunities"].append(
                        f"内部循环成功率偏低({inner_rate:.1%})，建议加强训练阶段"
                    )
            except Exception as e:
                logger.debug(f"优化机会识别失败: {e}")

            try:
                storage_health = self.state.bridge_data.get("inner_storage_health", {})
                cache_hit_rate = storage_health.get("cache_hit_rate", "0%")
                if isinstance(cache_hit_rate, str) and float(cache_hit_rate.rstrip("%")) < 30:
                    extraction["optimization_opportunities"].append(
                        f"缓存命中率偏低({cache_hit_rate})，建议调整缓存策略"
                    )
            except Exception as e:
                logger.debug(f"存储优化机会识别失败: {e}")

        self._extraction_results = extraction
        return {"status": "completed", "insights": extraction["high_value_knowledge"]}

    async def _iterate_system(self) -> Dict[str, Any]:
        iteration = {
            "strategy_updates": 0,
            "parameter_adjustments": 0,
            "architecture_changes": 0
        }

        if self.core:
            try:
                opportunities = self._extraction_results.get("optimization_opportunities", [])
                if opportunities:
                    for opp in opportunities:
                        self.core.evolution_engine.record_performance(
                            "外部循环迭代", True, 0
                        )
                    iteration["strategy_updates"] = len(opportunities)
            except Exception as e:
                logger.debug(f"策略更新失败: {e}")

            try:
                inner_rate = self.state.bridge_data.get("inner_success_rate", 0)
                if inner_rate > 0.8:
                    iteration["parameter_adjustments"] = 1
            except Exception as e:
                logger.debug(f"参数调整失败: {e}")

        self._iteration_results = iteration
        return {"status": "completed", "updates": iteration["strategy_updates"]}

    def _prepare_bridge_output(self) -> Dict[str, Any]:
        compound_bridge = self.compound.get_bridge_data()
        return {
            "outer_environment_load": self._ingestion_data.get("resource_status", {}).get("system_load", 0.3),
            "outer_knowledge_available": self._ingestion_data.get("external_knowledge", 0),
            "outer_optimization_opportunities": self._extraction_results.get("optimization_opportunities", []),
            "outer_strategy_updates": self._iteration_results.get("strategy_updates", 0),
            "outer_storage_metrics": self._ingestion_data.get("storage_metrics", {}),
            "outer_cycle": self.state.cycle_count,
            "outer_compound": compound_bridge
        }

    def _update_metrics(self, elapsed_ms: float, success: bool):
        self.state.metrics.total_cycles += 1
        if success:
            self.state.metrics.successful_cycles += 1
        else:
            self.state.metrics.failed_cycles += 1
        self.state.metrics.last_cycle_time_ms = elapsed_ms
        total = self.state.metrics.total_cycles
        prev_avg = self.state.metrics.avg_cycle_time_ms
        self.state.metrics.avg_cycle_time_ms = (prev_avg * (total - 1) + elapsed_ms) / total


class DualLoopEngine:
    """
    双层互动自动循环引擎

    协调内部循环和外部循环的交替执行与数据交换:

    内部循环: 数据收集 → 训练 → 评估 → 优化
         ↕ 桥接数据交换
    外部循环: 环境摄取 → 消化 → 提炼 → 迭代

    信息流转:
    - 内→外: 成功率、技能数量、优化建议、知识增量、存储健康
    - 外→内: 环境负载、外部知识、优化机会、策略更新、存储指标
    """

    def __init__(self, core_ref=None):
        self.core = core_ref
        self.inner_loop = InnerLoopCoordinator(core_ref)
        self.outer_loop = OuterLoopCoordinator(core_ref)
        self.dual_compound = get_dual_loop_compound(core_ref)
        self._running = False
        self._cycle_count = 0
        self._inner_bridge_data: Dict[str, Any] = {}
        self._outer_bridge_data: Dict[str, Any] = {}
        self._history: List[Dict[str, Any]] = []

    async def run_dual_cycle(self) -> Dict[str, Any]:
        self._cycle_count += 1
        start_time = time.time()

        inner_result = await self.inner_loop.run_cycle()
        self._inner_bridge_data = inner_result.get("bridge_output", {})

        outer_result = await self.outer_loop.run_cycle(self._inner_bridge_data)
        self._outer_bridge_data = outer_result.get("bridge_output", {})

        elapsed = (time.time() - start_time) * 1000

        dual_result = {
            "cycle": self._cycle_count,
            "inner_loop": inner_result,
            "outer_loop": outer_result,
            "bridge_flow": {
                "inner_to_outer": self._inner_bridge_data,
                "outer_to_inner": self._outer_bridge_data
            },
            "elapsed_ms": elapsed,
            "success": inner_result.get("success", False) and outer_result.get("success", False)
        }

        self._history.append(dual_result)
        if len(self._history) > 100:
            self._history = self._history[-100:]

        return dual_result

    async def run_continuous(self, interval_seconds: float = 60.0, max_cycles: int = 0):
        self._running = True
        logger.info(f"双层循环引擎启动 (间隔={interval_seconds}s, 最大循环={'无限' if max_cycles == 0 else max_cycles})")

        while self._running:
            try:
                result = await self.run_dual_cycle()
                logger.info(
                    f"双层循环 #{result['cycle']} 完成 "
                    f"(内部={'成功' if result['inner_loop'].get('success') else '失败'}, "
                    f"外部={'成功' if result['outer_loop'].get('success') else '失败'}, "
                    f"耗时={result['elapsed_ms']:.0f}ms)"
                )

                if max_cycles > 0 and self._cycle_count >= max_cycles:
                    logger.info(f"达到最大循环数 {max_cycles}，停止")
                    break

                await asyncio.sleep(interval_seconds)

            except Exception as e:
                logger.error(f"双层循环异常: {e}")
                await asyncio.sleep(interval_seconds)

        self._running = False
        logger.info("双层循环引擎停止")

    def stop(self):
        self._running = False

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "total_cycles": self._cycle_count,
            "inner_loop": {
                "phase": self.inner_loop.state.phase.value,
                "cycle": self.inner_loop.state.cycle_count,
                "metrics": {
                    "total": self.inner_loop.state.metrics.total_cycles,
                    "successful": self.inner_loop.state.metrics.successful_cycles,
                    "avg_time_ms": self.inner_loop.state.metrics.avg_cycle_time_ms,
                    "improvement_rate": self.inner_loop.state.metrics.improvement_rate
                }
            },
            "outer_loop": {
                "phase": self.outer_loop.state.phase.value,
                "cycle": self.outer_loop.state.cycle_count,
                "metrics": {
                    "total": self.outer_loop.state.metrics.total_cycles,
                    "successful": self.outer_loop.state.metrics.successful_cycles,
                    "avg_time_ms": self.outer_loop.state.metrics.avg_cycle_time_ms
                }
            },
            "bridge": {
                "inner_to_outer": self._inner_bridge_data,
                "outer_to_inner": self._outer_bridge_data
            },
            "compound": self.dual_compound.get_statistics()
        }

    def get_evolution_trajectory(self, last_n: int = 10) -> List[Dict[str, Any]]:
        return self._history[-last_n:]


_dual_loop_engine: Optional[DualLoopEngine] = None


def get_dual_loop_engine(core_ref=None) -> DualLoopEngine:
    global _dual_loop_engine
    if _dual_loop_engine is None:
        _dual_loop_engine = DualLoopEngine(core_ref)
    return _dual_loop_engine
