# -*- coding: utf-8 -*-
"""
解释引擎 (Explanation Engine)
为系统决策生成人类可理解的解释

核心功能:
- 决策路径解释
- 置信度解释
- 替代方案说明
- 因果链解释
- 自然语言生成
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .decision_tracer import DecisionTracer, DecisionTrace, TraceNode, get_decision_tracer

logger = logging.getLogger("ExplanationEngine")


@dataclass
class Explanation:
    """解释结果"""
    explanation_id: str
    trace_id: str
    summary: str
    decision_path: List[str]
    confidence_explanation: str
    alternatives: List[str]
    evidence: List[str]
    reasoning_chain: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "explanation_id": self.explanation_id,
            "trace_id": self.trace_id,
            "summary": self.summary,
            "decision_path": self.decision_path,
            "confidence_explanation": self.confidence_explanation,
            "alternatives": self.alternatives,
            "evidence": self.evidence,
            "reasoning_chain": self.reasoning_chain,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }

    def to_text(self) -> str:
        """转换为自然语言文本"""
        parts = [f"## 决策解释\n"]
        parts.append(f"**摘要**: {self.summary}\n")
        parts.append(f"**置信度**: {self.confidence_explanation}\n")

        if self.decision_path:
            parts.append("\n### 决策路径")
            for i, step in enumerate(self.decision_path, 1):
                parts.append(f"  {i}. {step}")

        if self.reasoning_chain:
            parts.append("\n### 推理链")
            for i, step in enumerate(self.reasoning_chain, 1):
                parts.append(f"  {i}. {step}")

        if self.evidence:
            parts.append("\n### 支撑证据")
            for ev in self.evidence:
                parts.append(f"  - {ev}")

        if self.alternatives:
            parts.append("\n### 替代方案")
            for alt in self.alternatives:
                parts.append(f"  - {alt}")

        return "\n".join(parts)


class ExplanationEngine:
    """
    解释引擎
    
    功能:
    - 从决策追踪生成解释
    - 置信度解释
    - 推理链可视化
    - 替代方案说明
    - 自然语言生成
    """

    def __init__(self, tracer: DecisionTracer = None):
        self._tracer = tracer or get_decision_tracer()
        self._explanation_templates = {
            "high_confidence": "系统对此决策有较高信心 (置信度: {confidence:.1%})，基于{evidence_count}条证据支持。",
            "medium_confidence": "系统对此决策有一定信心 (置信度: {confidence:.1%})，建议关注替代方案。",
            "low_confidence": "系统对此决策信心较低 (置信度: {confidence:.1%})，强烈建议人工审核。",
            "reflex_decision": "此决策由快速模式匹配生成，基于历史模式 '{pattern}' 的匹配。",
            "deliberative_decision": "此决策经过深度推理生成，使用了 '{strategy}' 推理策略，共{steps}个推理步骤。",
            "learning_decision": "此决策基于学习经验生成，参考了{experience_count}条历史经验。",
            "coordinator_decision": "此决策由协调器生成，将任务分配给{agent_type}类型的Agent处理。"
        }
        self._explanation_history: List[Explanation] = []
        self._max_history = 1000

        logger.info("解释引擎初始化")

    def explain(self, trace_id: str) -> Optional[Explanation]:
        """
        生成决策解释
        
        Args:
            trace_id: 追踪ID
            
        Returns:
            解释结果
        """
        trace = self._tracer.get_trace(trace_id)
        if not trace:
            logger.warning(f"追踪不存在: {trace_id}")
            return None

        import uuid
        explanation_id = f"expl_{uuid.uuid4().hex[:12]}"

        decision_path = self._build_decision_path(trace)
        confidence_exp = self._explain_confidence(trace)
        alternatives = self._find_alternatives(trace)
        evidence = self._collect_evidence(trace)
        reasoning_chain = self._build_reasoning_chain(trace)
        summary = self._generate_summary(trace, confidence_exp, decision_path)

        explanation = Explanation(
            explanation_id=explanation_id,
            trace_id=trace_id,
            summary=summary,
            decision_path=decision_path,
            confidence_explanation=confidence_exp,
            alternatives=alternatives,
            evidence=evidence,
            reasoning_chain=reasoning_chain,
            metadata={
                "task": trace.task,
                "outcome": trace.outcome,
                "node_count": len(trace.nodes),
                "duration_ms": trace.total_duration_ms
            }
        )

        self._explanation_history.append(explanation)
        if len(self._explanation_history) > self._max_history:
            self._explanation_history = self._explanation_history[-self._max_history:]

        return explanation

    def explain_decision(self, agent_id: str, action: str,
                        confidence: float, reasoning: str,
                        evidence: List[Dict[str, Any]] = None,
                        alternatives: List[Dict[str, Any]] = None) -> Explanation:
        """
        直接解释单个决策
        
        Args:
            agent_id: Agent ID
            action: 决策动作
            confidence: 置信度
            reasoning: 推理过程
            evidence: 证据
            alternatives: 替代方案
            
        Returns:
            解释结果
        """
        import uuid

        if confidence > 0.8:
            confidence_exp = self._explanation_templates["high_confidence"].format(
                confidence=confidence, evidence_count=len(evidence or [])
            )
        elif confidence > 0.5:
            confidence_exp = self._explanation_templates["medium_confidence"].format(
                confidence=confidence, evidence_count=len(evidence or [])
            )
        else:
            confidence_exp = self._explanation_templates["low_confidence"].format(
                confidence=confidence, evidence_count=len(evidence or [])
            )

        alt_texts = []
        if alternatives:
            for alt in alternatives:
                alt_texts.append(
                    f"{alt.get('action', '未知')} (置信度: {alt.get('confidence', 0):.1%})"
                )

        evidence_texts = []
        if evidence:
            for ev in evidence:
                evidence_texts.append(
                    f"[{ev.get('source', '未知')}] {ev.get('detail', str(ev)[:50])}"
                )

        return Explanation(
            explanation_id=f"expl_{uuid.uuid4().hex[:12]}",
            trace_id="direct",
            summary=f"Agent '{agent_id}' 决定执行 '{action}'",
            decision_path=[f"{agent_id}: {action}"],
            confidence_explanation=confidence_exp,
            alternatives=alt_texts,
            evidence=evidence_texts,
            reasoning_chain=[reasoning] if reasoning else [],
            metadata={"agent_id": agent_id, "action": action}
        )

    def _build_decision_path(self, trace: DecisionTrace) -> List[str]:
        """构建决策路径"""
        paths = trace.get_all_paths()
        if not paths:
            return ["无决策路径"]

        main_path = paths[0]
        path_descriptions = []

        for node in main_path:
            desc = f"[{node.node_type.value}] {node.agent_id}: {node.description}"
            if node.confidence < 1.0:
                desc += f" (置信度: {node.confidence:.1%})"
            path_descriptions.append(desc)

        return path_descriptions

    def _explain_confidence(self, trace: DecisionTrace) -> str:
        """解释置信度"""
        decisions = [
            n for n in trace.nodes.values()
            if n.node_type.value == "decision"
        ]

        if not decisions:
            return "无决策节点，无法评估置信度"

        avg_confidence = sum(d.confidence for d in decisions) / len(decisions)
        min_confidence = min(d.confidence for d in decisions)
        max_confidence = max(d.confidence for d in decisions)

        if avg_confidence > 0.8:
            level = "高"
        elif avg_confidence > 0.5:
            level = "中"
        else:
            level = "低"

        return (
            f"整体置信度{level} (平均: {avg_confidence:.1%}, "
            f"范围: {min_confidence:.1%} ~ {max_confidence:.1%}), "
            f"共{len(decisions)}个决策节点"
        )

    def _find_alternatives(self, trace: DecisionTrace) -> List[str]:
        """查找替代方案"""
        alternatives = []

        for node in trace.nodes.values():
            if node.node_type.value == "decision":
                alts = node.metadata.get("alternatives", [])
                for alt in alts:
                    if isinstance(alt, dict):
                        alternatives.append(
                            f"{alt.get('action', alt.get('strategy', '未知'))} "
                            f"(置信度: {alt.get('confidence', 0):.1%})"
                        )
                    else:
                        alternatives.append(str(alt))

        return alternatives[:5]

    def _collect_evidence(self, trace: DecisionTrace) -> List[str]:
        """收集证据"""
        evidence = []

        for node in trace.nodes.values():
            ev_list = node.metadata.get("evidence", [])
            if isinstance(ev_list, list):
                for ev in ev_list:
                    if isinstance(ev, dict):
                        source = ev.get("source", "未知")
                        detail = ev.get("detail", ev.get("name", str(ev)[:50]))
                        evidence.append(f"[{source}] {detail}")
                    else:
                        evidence.append(str(ev))

            if node.output_data:
                for key, value in node.output_data.items():
                    if isinstance(value, (bool, (int, float))):
                        evidence.append(f"[{node.agent_id}] {key} = {value}")

        return evidence[:10]

    def _build_reasoning_chain(self, trace: DecisionTrace) -> List[str]:
        """构建推理链"""
        chain = []

        for node in trace.nodes.values():
            if node.reasoning:
                chain.append(f"{node.agent_id}: {node.reasoning}")

        return chain

    def _generate_summary(self, trace: DecisionTrace,
                         confidence_exp: str,
                         decision_path: List[str]) -> str:
        """生成摘要"""
        outcome = trace.outcome or "进行中"
        node_count = len(trace.nodes)
        duration = trace.total_duration_ms

        summary = (
            f"任务 '{trace.task[:40]}' 的决策过程: "
            f"共{node_count}个决策节点, "
            f"耗时{duration:.0f}ms, "
            f"结果: {outcome}. "
            f"{confidence_exp}"
        )

        return summary

    def get_explanation(self, explanation_id: str) -> Optional[Explanation]:
        """获取解释"""
        for expl in self._explanation_history:
            if expl.explanation_id == explanation_id:
                return expl
        return None

    def get_recent_explanations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取最近的解释"""
        return [
            {
                "explanation_id": e.explanation_id,
                "trace_id": e.trace_id,
                "summary": e.summary[:100],
                "timestamp": e.timestamp
            }
            for e in self._explanation_history[-limit:]
        ]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_explanations": len(self._explanation_history),
            "templates_available": len(self._explanation_templates)
        }


explanation_engine = ExplanationEngine()


def get_explanation_engine() -> ExplanationEngine:
    """获取全局解释引擎"""
    return explanation_engine
