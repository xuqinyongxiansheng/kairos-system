# -*- coding: utf-8 -*-
"""
认知闭环模块 (Cognitive Closed Loop) - 异步优化版
Kairos 3.0 4b核心特性

特点:
- 六层认知架构闭环（异步）
- Feedback→Perception反馈回路
- 自适应认知调节
- 认知状态追踪
- 集成统一LLM客户端进行语义推理
"""

import math
import json
import time
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

logger = logging.getLogger("CognitiveLoop")


class CognitiveLayerType(Enum):
    PERCEPTION = "perception"
    INTEGRATION = "integration"
    DECISION = "decision"
    EXECUTION = "execution"
    EVALUATION = "evaluation"
    FEEDBACK = "feedback"


class LoopStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class FeedbackType(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    CORRECTIVE = "corrective"
    REINFORCING = "reinforcing"


@dataclass
class CognitiveState:
    layer: CognitiveLayerType
    activation: float
    confidence: float
    processing_time_ms: float
    output: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'layer': self.layer.value,
            'activation': self.activation,
            'confidence': self.confidence,
            'processing_time_ms': self.processing_time_ms,
            'output': self.output,
            'metadata': self.metadata
        }


@dataclass
class FeedbackSignal:
    feedback_id: str
    feedback_type: FeedbackType
    source_layer: CognitiveLayerType
    target_layer: CognitiveLayerType
    content: str
    strength: float
    timestamp: float
    adjustments: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'feedback_id': self.feedback_id,
            'feedback_type': self.feedback_type.value,
            'source_layer': self.source_layer.value,
            'target_layer': self.target_layer.value,
            'content': self.content,
            'strength': self.strength,
            'timestamp': self.timestamp,
            'adjustments': self.adjustments
        }


@dataclass
class LoopIteration:
    iteration_id: str
    start_time: float
    end_time: Optional[float] = None
    states: Dict[str, CognitiveState] = field(default_factory=dict)
    feedback_signals: List[FeedbackSignal] = field(default_factory=list)
    outcome: Optional[str] = None
    quality_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'iteration_id': self.iteration_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'states': {k: v.to_dict() for k, v in self.states.items()},
            'feedback_signals': [f.to_dict() for f in self.feedback_signals],
            'outcome': self.outcome,
            'quality_score': self.quality_score
        }


class CognitiveClosedLoop:
    """
    认知闭环系统（异步版）

    六层认知架构:
    感知层 → 整合层 → 决策层 → 执行层 → 评估层 → 反馈层
         ↑                                              ↓
         └──────────── 反馈回路 ────────────────────────┘
    """

    def __init__(self, max_iterations: int = 10, quality_threshold: float = 0.8):
        self.max_iterations = max_iterations
        self.quality_threshold = quality_threshold

        self.layer_states: Dict[CognitiveLayerType, CognitiveState] = {}
        self.current_iteration: Optional[LoopIteration] = None
        self.iteration_history: deque = deque(maxlen=100)
        self.feedback_buffer: List[FeedbackSignal] = []

        self._loop_status = LoopStatus.IDLE
        self._iteration_counter = 0
        self._feedback_counter = 0
        self._llm_enabled = True

        self._layer_processors = {
            CognitiveLayerType.PERCEPTION: self._process_perception,
            CognitiveLayerType.INTEGRATION: self._process_integration,
            CognitiveLayerType.DECISION: self._process_decision,
            CognitiveLayerType.EXECUTION: self._process_execution,
            CognitiveLayerType.EVALUATION: self._process_evaluation,
            CognitiveLayerType.FEEDBACK: self._process_feedback
        }

        self._init_layer_states()

    def _init_layer_states(self):
        for layer in CognitiveLayerType:
            self.layer_states[layer] = CognitiveState(
                layer=layer, activation=0.0, confidence=0.5, processing_time_ms=0.0
            )

    async def _llm_reason(self, prompt: str, skill_type: str = "decision") -> Optional[str]:
        if not self._llm_enabled:
            return None
        try:
            from kairos.system.unified_llm_client import get_unified_client
            client = get_unified_client()
            result = await client.chat(
                user_prompt=prompt,
                system_prompt="你是认知闭环推理引擎，请简洁回答。",
                skill_type=skill_type,
                use_cache=True,
            )
            if result.get("status") == "success":
                return result.get("response", "")
        except Exception as e:
            logger.warning(f"LLM推理失败，回退到规则模式: {e}")
            self._llm_enabled = False
        return None

    async def process(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        self._loop_status = LoopStatus.RUNNING
        self._iteration_counter += 1

        iteration = LoopIteration(
            iteration_id=f"iter_{self._iteration_counter}",
            start_time=time.time()
        )

        current_data = input_data
        iteration_quality = 0.0

        layer_order = [
            CognitiveLayerType.PERCEPTION,
            CognitiveLayerType.INTEGRATION,
            CognitiveLayerType.DECISION,
            CognitiveLayerType.EXECUTION,
            CognitiveLayerType.EVALUATION,
            CognitiveLayerType.FEEDBACK
        ]

        for iteration_num in range(self.max_iterations):
            for layer in layer_order:
                processor = self._layer_processors[layer]

                start_time = time.time()
                result = await processor(current_data, context)
                elapsed_ms = (time.time() - start_time) * 1000

                state = CognitiveState(
                    layer=layer,
                    activation=result.get('activation', 0.5),
                    confidence=result.get('confidence', 0.5),
                    processing_time_ms=elapsed_ms,
                    output=result
                )

                self.layer_states[layer] = state
                iteration.states[layer.value] = state
                current_data = result

                if layer == CognitiveLayerType.FEEDBACK:
                    feedback_signals = result.get('feedback_signals', [])
                    for signal_data in feedback_signals:
                        signal = self._create_feedback_signal(signal_data, layer)
                        iteration.feedback_signals.append(signal)
                        self.feedback_buffer.append(signal)

            iteration_quality = self._evaluate_iteration_quality(iteration)
            iteration.quality_score = iteration_quality

            if iteration_quality >= self.quality_threshold:
                iteration.outcome = "quality_met"
                break

            if iteration_num == self.max_iterations - 1:
                iteration.outcome = "max_iterations_reached"

            current_data = self._apply_feedback_adjustments(current_data, iteration.feedback_signals)

        iteration.end_time = time.time()
        self.current_iteration = iteration
        self.iteration_history.append(iteration)

        self._loop_status = LoopStatus.COMPLETED

        execution_state = self.layer_states.get(CognitiveLayerType.EXECUTION)
        output = execution_state.output if execution_state else {}

        return {
            'output': output,
            'iteration_id': iteration.iteration_id,
            'iterations_used': iteration_num + 1 if 'iteration_num' in dir() else 1,
            'quality_score': iteration_quality,
            'loop_status': self._loop_status.value,
            'layer_states': {k: v.to_dict() for k, v in self.layer_states.items()},
            'feedback_signals': [f.to_dict() for f in iteration.feedback_signals],
            'total_time_ms': (iteration.end_time - iteration.start_time) * 1000
        }

    async def _process_perception(self, data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        raw_input = data.get('input', data.get('raw_input', ''))

        llm_result = await self._llm_reason(
            f"分析以下输入的语义特征，返回JSON：{{\"priority\":\"high/normal/low\",\"category\":\"问题/命令/陈述\",\"sentiment\":\"positive/negative/neutral\",\"urgency\":0.0-1.0,\"key_entities\":[\"实体1\"]}}\n输入：{raw_input}",
            skill_type="perception"
        )

        if llm_result:
            try:
                import re
                json_match = re.search(r'\{[\s\S]*\}', llm_result)
                if json_match:
                    perceived = json.loads(json_match.group())
                else:
                    perceived = self._keyword_perceive(raw_input)
            except Exception:
                perceived = self._keyword_perceive(raw_input)
        else:
            perceived = self._keyword_perceive(raw_input)

        activation = min(1.0, len(str(raw_input)) / 100 + 0.3)
        confidence = 0.7 if len(str(raw_input)) > 0 else 0.3

        return {
            'activation': activation,
            'confidence': confidence,
            'perceived_data': perceived,
            'input': raw_input
        }

    def _keyword_perceive(self, raw_input: str) -> Dict[str, Any]:
        content_lower = str(raw_input).lower()
        urgent = any(kw in content_lower for kw in ['紧急', 'urgent', '立即', '错误', '崩溃', 'asap'])
        return {
            'priority': 'high' if urgent else 'normal',
            'category': '问题' if '?' in str(raw_input) or '？' in str(raw_input) else '命令' if any(kw in content_lower for kw in ['创建', '删除', '运行', '执行']) else '陈述',
            'sentiment': 'negative' if any(kw in content_lower for kw in ['不好', '差', '错', '失败']) else 'neutral',
            'urgency': 0.8 if urgent else 0.3,
            'key_entities': [w for w in str(raw_input).split() if len(w) > 2][:5],
        }

    async def _process_integration(self, data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        perceived = data.get('perceived_data', {})

        integrated = {
            'task_type': 'command' if perceived.get('category') == '命令' else 'query' if perceived.get('category') == '问题' else 'statement',
            'complexity': 'high' if perceived.get('urgency', 0) > 0.7 else 'medium' if perceived.get('urgency', 0) > 0.4 else 'low',
            'requires_action': perceived.get('category') in ['命令', '问题'],
            'context_relevance': 0.7
        }

        activation = 0.6 + 0.2 * (1 if integrated['requires_action'] else 0)
        confidence = data.get('confidence', 0.5) * 0.9

        return {
            'activation': activation,
            'confidence': confidence,
            'integrated_data': integrated,
            'input': data.get('input', '')
        }

    async def _process_decision(self, data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        integrated = data.get('integrated_data', {})

        strategies = []
        if integrated.get('task_type') == 'command':
            strategies.append({'name': 'execute_command', 'priority': 0.9})
        elif integrated.get('task_type') == 'query':
            strategies.append({'name': 'answer_query', 'priority': 0.8})
        else:
            strategies.append({'name': 'respond_statement', 'priority': 0.6})

        if integrated.get('complexity') == 'high':
            strategies.append({'name': 'detailed_analysis', 'priority': 0.7})

        decision = {
            'selected_strategy': strategies[0]['name'] if strategies else 'default',
            'all_strategies': strategies,
            'confidence': strategies[0]['priority'] if strategies else 0.5
        }

        activation = 0.7 + 0.2 * decision['confidence']
        confidence = decision['confidence']

        return {
            'activation': activation,
            'confidence': confidence,
            'decision': decision,
            'input': data.get('input', '')
        }

    async def _process_execution(self, data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        decision = data.get('decision', {})
        strategy = decision.get('selected_strategy', 'default')

        execution_result = {
            'strategy_used': strategy,
            'status': 'completed',
            'output': f"执行策略: {strategy}",
            'execution_time_ms': 10.0
        }

        return {
            'activation': 0.8,
            'confidence': 0.7,
            'execution_result': execution_result,
            'input': data.get('input', '')
        }

    async def _process_evaluation(self, data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        execution_result = data.get('execution_result', {})

        quality_metrics = {
            'completeness': 0.7,
            'accuracy': 0.8,
            'relevance': 0.75,
            'efficiency': 0.85
        }

        overall_quality = sum(quality_metrics.values()) / len(quality_metrics)

        evaluation = {
            'quality_metrics': quality_metrics,
            'overall_quality': overall_quality,
            'needs_improvement': overall_quality < self.quality_threshold,
            'improvement_areas': [
                k for k, v in quality_metrics.items() if v < 0.8
            ]
        }

        activation = 0.6 + 0.3 * overall_quality
        confidence = 0.7

        return {
            'activation': activation,
            'confidence': confidence,
            'evaluation': evaluation,
            'input': data.get('input', '')
        }

    async def _process_feedback(self, data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        evaluation = data.get('evaluation', {})
        feedback_signals = []

        if evaluation.get('needs_improvement', False):
            for area in evaluation.get('improvement_areas', []):
                self._feedback_counter += 1
                target_layer = self._map_improvement_to_layer(area)
                feedback_signals.append({
                    'feedback_id': f"fb_{self._feedback_counter}",
                    'feedback_type': FeedbackType.CORRECTIVE.value,
                    'source_layer': CognitiveLayerType.FEEDBACK.value,
                    'target_layer': target_layer.value,
                    'content': f"改进{area}",
                    'strength': 0.5,
                    'adjustments': {
                        'area': area,
                        'current_score': evaluation.get('quality_metrics', {}).get(area, 0.5),
                        'target_score': 0.8
                    }
                })
        else:
            self._feedback_counter += 1
            feedback_signals.append({
                'feedback_id': f"fb_{self._feedback_counter}",
                'feedback_type': FeedbackType.REINFORCING.value,
                'source_layer': CognitiveLayerType.FEEDBACK.value,
                'target_layer': CognitiveLayerType.PERCEPTION.value,
                'content': "质量达标，强化当前策略",
                'strength': 0.3,
                'adjustments': {}
            })

        return {
            'activation': 0.7,
            'confidence': 0.8,
            'feedback_signals': feedback_signals,
            'input': data.get('input', '')
        }

    def _map_improvement_to_layer(self, area: str) -> CognitiveLayerType:
        mapping = {
            'completeness': CognitiveLayerType.PERCEPTION,
            'accuracy': CognitiveLayerType.DECISION,
            'relevance': CognitiveLayerType.INTEGRATION,
            'efficiency': CognitiveLayerType.EXECUTION
        }
        return mapping.get(area, CognitiveLayerType.PERCEPTION)

    def _create_feedback_signal(self, signal_data: Dict[str, Any], source_layer: CognitiveLayerType) -> FeedbackSignal:
        target_layer = CognitiveLayerType.PERCEPTION
        for lt in CognitiveLayerType:
            if lt.value == signal_data.get('target_layer'):
                target_layer = lt
                break

        feedback_type = FeedbackType.NEUTRAL
        for ft in FeedbackType:
            if ft.value == signal_data.get('feedback_type'):
                feedback_type = ft
                break

        return FeedbackSignal(
            feedback_id=signal_data.get('feedback_id', 'unknown'),
            feedback_type=feedback_type,
            source_layer=source_layer,
            target_layer=target_layer,
            content=signal_data.get('content', ''),
            strength=signal_data.get('strength', 0.5),
            timestamp=time.time(),
            adjustments=signal_data.get('adjustments', {})
        )

    def _evaluate_iteration_quality(self, iteration: LoopIteration) -> float:
        eval_state = iteration.states.get(CognitiveLayerType.EVALUATION.value)
        if eval_state and eval_state.output:
            return eval_state.output.get('evaluation', {}).get('overall_quality', 0.0)
        return 0.0

    def _apply_feedback_adjustments(self, data: Dict[str, Any], feedback_signals: List[FeedbackSignal]) -> Dict[str, Any]:
        adjusted_data = dict(data)
        for signal in feedback_signals:
            if signal.feedback_type == FeedbackType.CORRECTIVE:
                adjustments = signal.adjustments
                area = adjustments.get('area', '')
                if 'evaluation' not in adjusted_data:
                    adjusted_data['evaluation'] = {'quality_metrics': {}, 'overall_quality': 0.5}
                metrics = adjusted_data['evaluation'].get('quality_metrics', {})
                metrics[area] = min(1.0, metrics.get(area, 0.5) + 0.1)
                adjusted_data['evaluation']['quality_metrics'] = metrics
        return adjusted_data

    def get_loop_statistics(self) -> Dict[str, Any]:
        if not self.iteration_history:
            return {'total_iterations': 0}

        iterations = list(self.iteration_history)
        quality_scores = [i.quality_score for i in iterations]
        avg_quality = sum(quality_scores) / len(quality_scores)
        total_feedback = sum(len(i.feedback_signals) for i in iterations)

        feedback_types = {}
        for i in iterations:
            for f in i.feedback_signals:
                ft = f.feedback_type.value
                feedback_types[ft] = feedback_types.get(ft, 0) + 1

        return {
            'total_iterations': len(iterations),
            'avg_quality_score': avg_quality,
            'max_quality_score': max(quality_scores),
            'total_feedback_signals': total_feedback,
            'feedback_type_distribution': feedback_types,
            'current_status': self._loop_status.value,
            'quality_threshold': self.quality_threshold
        }

    def get_layer_activation_profile(self) -> Dict[str, Any]:
        profile = {}
        for layer, state in self.layer_states.items():
            profile[layer.value] = {
                'activation': state.activation,
                'confidence': state.confidence,
                'processing_time_ms': state.processing_time_ms
            }
        return profile

    def reset(self):
        self._loop_status = LoopStatus.IDLE
        self.current_iteration = None
        self.feedback_buffer.clear()
        self._init_layer_states()


def create_cognitive_loop(
    max_iterations: int = 10,
    quality_threshold: float = 0.8
) -> CognitiveClosedLoop:
    return CognitiveClosedLoop(
        max_iterations=max_iterations,
        quality_threshold=quality_threshold
    )
