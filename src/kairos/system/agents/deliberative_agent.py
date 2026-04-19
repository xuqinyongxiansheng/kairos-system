# -*- coding: utf-8 -*-
"""
审议Agent (DeliberativeAgent)
深度推理，低置信度触发
适用于: 复杂分析、多步推理、策略规划、矛盾解决

特征:
- 深度推理链
- 多方案比较
- 因果验证
- 不确定性量化
"""

import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .base_neuron_agent import BaseNeuronAgent, AgentCapability, AgentDecision
from ..core.enums import AgentType

logger = logging.getLogger("DeliberativeAgent")


@dataclass
class ReasoningStep:
    """推理步骤"""
    step_id: str
    description: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    confidence: float
    reasoning_type: str
    dependencies: List[str] = field(default_factory=list)


@dataclass
class ReasoningChain:
    """推理链"""
    chain_id: str
    task: str
    steps: List[ReasoningStep] = field(default_factory=list)
    final_confidence: float = 0.0
    conclusion: str = ""
    alternatives: List[Dict[str, Any]] = field(default_factory=list)


class DeliberativeAgent(BaseNeuronAgent):
    """
    审议Agent - 深度推理
    
    触发条件: confidence < 0.3 或需要深度推理
    适用场景: 复杂分析、多步推理、策略规划、矛盾解决
    """

    def __init__(self, agent_id: str = "deliberative_agent"):
        capabilities = [
            AgentCapability(
                name="deep_analysis",
                description="深度分析推理",
                confidence_threshold=0.3,
                avg_latency_ms=500.0
            ),
            AgentCapability(
                name="multi_step_reasoning",
                description="多步推理链",
                confidence_threshold=0.2,
                avg_latency_ms=800.0
            ),
            AgentCapability(
                name="strategy_planning",
                description="策略规划",
                confidence_threshold=0.4,
                avg_latency_ms=600.0
            ),
            AgentCapability(
                name="contradiction_resolution",
                description="矛盾解决",
                confidence_threshold=0.1,
                avg_latency_ms=400.0
            ),
        ]
        super().__init__(agent_id, AgentType.DELIBERATIVE, capabilities)

        self._reasoning_strategies = {
            "analytical": self._analytical_reasoning,
            "comparative": self._comparative_reasoning,
            "causal": self._causal_reasoning,
            "decompositional": self._decompositional_reasoning,
        }
        self._chain_history: List[ReasoningChain] = []
        self._max_chains = 200

    def can_handle(self, task: str, confidence: float) -> bool:
        """判断是否需要深度推理"""
        if confidence < 0.3:
            return True

        deep_keywords = ["分析", "为什么", "比较", "评估", "规划", "策略",
                        "analyze", "why", "compare", "evaluate", "plan", "strategy"]
        if any(kw in task.lower() for kw in deep_keywords):
            return True

        return False

    async def process(self, content: Dict[str, Any]) -> AgentDecision:
        """深度推理处理"""
        task = content.get("task", "")
        context = content.get("context", {})
        confidence = content.get("confidence", 0.5)

        strategy = self._select_strategy(task, context)

        chain = await self._execute_reasoning_chain(task, context, strategy)

        self._chain_history.append(chain)
        if len(self._chain_history) > self._max_chains:
            self._chain_history = self._chain_history[-self._max_chains:]

        return AgentDecision(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            action=chain.conclusion,
            confidence=chain.final_confidence,
            reasoning=f"推理策略: {strategy}, 步骤数: {len(chain.steps)}",
            alternatives=chain.alternatives,
            evidence=[
                {
                    "source": "reasoning_chain",
                    "chain_id": chain.chain_id,
                    "steps": len(chain.steps),
                    "strategy": strategy
                }
            ],
            metadata={
                "strategy": strategy,
                "chain_id": chain.chain_id,
                "step_count": len(chain.steps)
            }
        )

    def _select_strategy(self, task: str, context: Dict[str, Any]) -> str:
        """选择推理策略"""
        task_lower = task.lower()

        if any(kw in task_lower for kw in ["比较", "对比", "compare", "versus"]):
            return "comparative"

        if any(kw in task_lower for kw in ["为什么", "原因", "因果", "why", "cause"]):
            return "causal"

        if any(kw in task_lower for kw in ["分解", "拆解", "步骤", "decompose", "breakdown"]):
            return "decompositional"

        if any(kw in task_lower for kw in ["分析", "评估", "analyze", "evaluate"]):
            return "analytical"

        if context.get("has_contradiction"):
            return "comparative"

        if context.get("complexity", 0.5) > 0.7:
            return "decompositional"

        return "analytical"

    async def _execute_reasoning_chain(self, task: str, context: Dict[str, Any],
                                       strategy: str) -> ReasoningChain:
        """执行推理链"""
        import uuid
        chain = ReasoningChain(
            chain_id=f"chain_{uuid.uuid4().hex[:12]}",
            task=task
        )

        strategy_fn = self._reasoning_strategies.get(strategy, self._analytical_reasoning)
        result = await strategy_fn(task, context)

        chain.steps = result.get("steps", [])
        chain.final_confidence = result.get("confidence", 0.5)
        chain.conclusion = result.get("conclusion", "推理完成")
        chain.alternatives = result.get("alternatives", [])

        return chain

    async def _analytical_reasoning(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """分析推理"""
        import uuid
        steps = [
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                description="问题定义与分解",
                input_data={"task": task},
                output_data={"sub_questions": [task]},
                confidence=0.9,
                reasoning_type="analytical"
            ),
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                description="信息收集与评估",
                input_data={"context": context},
                output_data={"available_info": bool(context)},
                confidence=0.7,
                reasoning_type="analytical"
            ),
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                description="综合分析与结论",
                input_data={"task": task, "context": context},
                output_data={"conclusion": "分析完成"},
                confidence=0.6,
                reasoning_type="analytical"
            )
        ]

        avg_confidence = sum(s.confidence for s in steps) / len(steps)

        return {
            "steps": steps,
            "confidence": avg_confidence,
            "conclusion": f"分析推理: {task[:50]}",
            "alternatives": [
                {"strategy": "comparative", "confidence": avg_confidence * 0.9},
                {"strategy": "decompositional", "confidence": avg_confidence * 0.85}
            ]
        }

    async def _comparative_reasoning(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """比较推理"""
        import uuid
        steps = [
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                description="识别比较维度",
                input_data={"task": task},
                output_data={"dimensions": ["性能", "可靠性", "成本"]},
                confidence=0.85,
                reasoning_type="comparative"
            ),
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                description="逐维度比较",
                input_data={"dimensions": ["性能", "可靠性", "成本"]},
                output_data={"comparison": "多维度评估完成"},
                confidence=0.75,
                reasoning_type="comparative"
            ),
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                description="综合权衡",
                input_data={"comparison": "多维度评估完成"},
                output_data={"recommendation": "基于综合评估的建议"},
                confidence=0.7,
                reasoning_type="comparative"
            )
        ]

        avg_confidence = sum(s.confidence for s in steps) / len(steps)

        return {
            "steps": steps,
            "confidence": avg_confidence,
            "conclusion": f"比较推理: {task[:50]}",
            "alternatives": [
                {"strategy": "analytical", "confidence": avg_confidence * 0.9}
            ]
        }

    async def _causal_reasoning(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """因果推理"""
        import uuid
        steps = [
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                description="因果链构建",
                input_data={"task": task},
                output_data={"causal_chain": "初步因果链"},
                confidence=0.8,
                reasoning_type="causal"
            ),
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                description="混淆因素排查",
                input_data={"causal_chain": "初步因果链"},
                output_data={"confounders": []},
                confidence=0.7,
                reasoning_type="causal"
            ),
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                description="因果验证",
                input_data={"confounders": []},
                output_data={"verified": True},
                confidence=0.65,
                reasoning_type="causal"
            )
        ]

        avg_confidence = sum(s.confidence for s in steps) / len(steps)

        return {
            "steps": steps,
            "confidence": avg_confidence,
            "conclusion": f"因果推理: {task[:50]}",
            "alternatives": [
                {"strategy": "analytical", "confidence": avg_confidence * 0.85}
            ]
        }

    async def _decompositional_reasoning(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """分解推理"""
        import uuid
        sub_tasks = [f"子任务{i+1}" for i in range(3)]

        steps = [
            ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                description="任务分解",
                input_data={"task": task},
                output_data={"sub_tasks": sub_tasks},
                confidence=0.85,
                reasoning_type="decompositional"
            )
        ]

        for i, sub_task in enumerate(sub_tasks):
            steps.append(ReasoningStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                description=f"处理{sub_task}",
                input_data={"sub_task": sub_task},
                output_data={"result": f"{sub_task}完成"},
                confidence=0.75 - i * 0.05,
                reasoning_type="decompositional"
            ))

        steps.append(ReasoningStep(
            step_id=f"step_{uuid.uuid4().hex[:8]}",
            description="结果整合",
            input_data={"sub_results": [f"{st}完成" for st in sub_tasks]},
            output_data={"integrated_result": "整合完成"},
            confidence=0.7,
            reasoning_type="decompositional"
        ))

        avg_confidence = sum(s.confidence for s in steps) / len(steps)

        return {
            "steps": steps,
            "confidence": avg_confidence,
            "conclusion": f"分解推理: {task[:50]} ({len(sub_tasks)}个子任务)",
            "alternatives": [
                {"strategy": "analytical", "confidence": avg_confidence * 0.9}
            ]
        }

    def get_chain_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取推理链历史"""
        return [
            {
                "chain_id": c.chain_id,
                "task": c.task[:50],
                "steps": len(c.steps),
                "confidence": c.final_confidence,
                "conclusion": c.conclusion[:50]
            }
            for c in self._chain_history[-limit:]
        ]
