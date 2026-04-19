# -*- coding: utf-8 -*-
"""
决策追踪器 (Decision Tracer)
记录和追踪系统中的每个决策，提供完整的决策链路可观测性

核心功能:
- 决策节点记录 (输入/输出/置信度/推理)
- 决策链路追踪 (关联ID串联)
- 决策树构建 (分支/合并)
- 历史回溯与审计
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger("DecisionTracer")


class TraceNodeType(Enum):
    """追踪节点类型"""
    DECISION = "decision"
    ACTION = "action"
    OBSERVATION = "observation"
    FEEDBACK = "feedback"
    ERROR = "error"
    BRANCH = "branch"
    MERGE = "merge"


@dataclass
class TraceNode:
    """追踪节点"""
    node_id: str
    node_type: TraceNodeType
    agent_id: str
    description: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    confidence: float
    reasoning: str
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "agent_id": self.agent_id,
            "description": self.description,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms
        }


@dataclass
class DecisionTrace:
    """决策追踪记录"""
    trace_id: str
    task: str
    root_node_id: str
    nodes: Dict[str, TraceNode] = field(default_factory=dict)
    status: str = "in_progress"
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None
    total_duration_ms: float = 0.0
    outcome: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: TraceNode):
        """添加节点"""
        self.nodes[node.node_id] = node
        if node.parent_id and node.parent_id in self.nodes:
            parent = self.nodes[node.parent_id]
            if node.node_id not in parent.children_ids:
                parent.children_ids.append(node.node_id)

    def get_path_to_root(self, node_id: str) -> List[TraceNode]:
        """获取从节点到根的路径"""
        path = []
        current_id = node_id
        visited = set()

        while current_id and current_id not in visited:
            visited.add(current_id)
            node = self.nodes.get(current_id)
            if node:
                path.append(node)
                current_id = node.parent_id
            else:
                break

        return list(reversed(path))

    def get_all_paths(self) -> List[List[TraceNode]]:
        """获取所有从根到叶的路径"""
        leaves = [
            nid for nid, node in self.nodes.items()
            if not node.children_ids
        ]
        return [self.get_path_to_root(leaf_id) for leaf_id in leaves]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trace_id": self.trace_id,
            "task": self.task,
            "root_node_id": self.root_node_id,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration_ms": self.total_duration_ms,
            "outcome": self.outcome,
            "node_count": len(self.nodes),
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "metadata": self.metadata
        }


class DecisionTracer:
    """
    决策追踪器
    
    功能:
    - 创建和追踪决策链
    - 记录每个决策节点
    - 构建决策树
    - 提供历史回溯
    - 生成追踪报告
    """

    def __init__(self, max_traces: int = 5000):
        self._traces: Dict[str, DecisionTrace] = {}
        self._active_traces: Dict[str, str] = {}
        self._max_traces = max_traces
        self._stats = {
            "total_traces": 0,
            "completed_traces": 0,
            "avg_nodes_per_trace": 0.0,
            "avg_duration_ms": 0.0,
            "by_outcome": {}
        }

        logger.info("决策追踪器初始化")

    def start_trace(self, task: str, metadata: Dict[str, Any] = None) -> str:
        """
        开始追踪
        
        Args:
            task: 任务描述
            metadata: 元数据
            
        Returns:
            追踪ID
        """
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        root_node_id = f"node_{uuid.uuid4().hex[:12]}"

        root_node = TraceNode(
            node_id=root_node_id,
            node_type=TraceNodeType.OBSERVATION,
            agent_id="system",
            description=f"开始追踪: {task[:50]}",
            input_data={"task": task},
            output_data={},
            confidence=1.0,
            reasoning="追踪起始点",
            metadata=metadata or {}
        )

        trace = DecisionTrace(
            trace_id=trace_id,
            task=task,
            root_node_id=root_node_id,
            metadata=metadata or {}
        )
        trace.add_node(root_node)

        self._traces[trace_id] = trace
        self._active_traces[task] = trace_id
        self._stats["total_traces"] += 1

        logger.debug(f"开始追踪: {trace_id} (任务: {task[:30]})")
        return trace_id

    def add_decision(self, trace_id: str, agent_id: str,
                    description: str, input_data: Dict[str, Any],
                    output_data: Dict[str, Any], confidence: float,
                    reasoning: str, parent_node_id: str = None,
                    duration_ms: float = 0.0,
                    metadata: Dict[str, Any] = None) -> str:
        """
        添加决策节点
        
        Args:
            trace_id: 追踪ID
            agent_id: Agent ID
            description: 描述
            input_data: 输入数据
            output_data: 输出数据
            confidence: 置信度
            reasoning: 推理过程
            parent_node_id: 父节点ID
            duration_ms: 持续时间
            metadata: 元数据
            
        Returns:
            节点ID
        """
        if trace_id not in self._traces:
            logger.warning(f"追踪不存在: {trace_id}")
            return ""

        trace = self._traces[trace_id]

        if parent_node_id is None:
            parent_node_id = trace.root_node_id

        node_id = f"node_{uuid.uuid4().hex[:12]}"

        node = TraceNode(
            node_id=node_id,
            node_type=TraceNodeType.DECISION,
            agent_id=agent_id,
            description=description,
            input_data=input_data,
            output_data=output_data,
            confidence=confidence,
            reasoning=reasoning,
            parent_id=parent_node_id,
            duration_ms=duration_ms,
            metadata=metadata or {}
        )

        trace.add_node(node)
        logger.debug(f"添加决策节点: {node_id} (追踪: {trace_id})")
        return node_id

    def add_action(self, trace_id: str, agent_id: str,
                   description: str, input_data: Dict[str, Any],
                   output_data: Dict[str, Any], parent_node_id: str = None,
                   duration_ms: float = 0.0) -> str:
        """添加动作节点"""
        if trace_id not in self._traces:
            return ""

        trace = self._traces[trace_id]
        if parent_node_id is None:
            parent_node_id = trace.root_node_id

        node_id = f"node_{uuid.uuid4().hex[:12]}"
        node = TraceNode(
            node_id=node_id,
            node_type=TraceNodeType.ACTION,
            agent_id=agent_id,
            description=description,
            input_data=input_data,
            output_data=output_data,
            confidence=1.0,
            reasoning="",
            parent_id=parent_node_id,
            duration_ms=duration_ms
        )

        trace.add_node(node)
        return node_id

    def add_feedback(self, trace_id: str, node_id: str,
                    feedback: str, success: bool,
                    quality: float = 0.0) -> str:
        """添加反馈节点"""
        if trace_id not in self._traces:
            return ""

        trace = self._traces[trace_id]
        feedback_node_id = f"node_{uuid.uuid4().hex[:12]}"

        node = TraceNode(
            node_id=feedback_node_id,
            node_type=TraceNodeType.FEEDBACK,
            agent_id="system",
            description=feedback,
            input_data={"success": success},
            output_data={"quality": quality},
            confidence=1.0 if success else 0.0,
            reasoning=f"反馈: {'成功' if success else '失败'}",
            parent_id=node_id,
            metadata={"success": success, "quality": quality}
        )

        trace.add_node(node)
        return feedback_node_id

    def add_error(self, trace_id: str, error: str,
                  parent_node_id: str = None,
                  metadata: Dict[str, Any] = None) -> str:
        """添加错误节点"""
        if trace_id not in self._traces:
            return ""

        trace = self._traces[trace_id]
        if parent_node_id is None:
            parent_node_id = trace.root_node_id

        node_id = f"node_{uuid.uuid4().hex[:12]}"
        node = TraceNode(
            node_id=node_id,
            node_type=TraceNodeType.ERROR,
            agent_id="system",
            description=error,
            input_data={},
            output_data={},
            confidence=0.0,
            reasoning=f"错误: {error}",
            parent_id=parent_node_id,
            metadata=metadata or {}
        )

        trace.add_node(node)
        return node_id

    def end_trace(self, trace_id: str, outcome: str = "completed",
                  metadata: Dict[str, Any] = None):
        """结束追踪"""
        if trace_id not in self._traces:
            return

        trace = self._traces[trace_id]
        trace.status = outcome
        trace.end_time = datetime.now().isoformat()
        trace.outcome = outcome
        if metadata:
            trace.metadata.update(metadata)

        try:
            start = datetime.fromisoformat(trace.start_time)
            end = datetime.fromisoformat(trace.end_time)
            trace.total_duration_ms = (end - start).total_seconds() * 1000
        except (ValueError, TypeError):
            pass

        self._stats["completed_traces"] += 1
        self._stats["by_outcome"][outcome] = self._stats["by_outcome"].get(outcome, 0) + 1

        total = self._stats["completed_traces"]
        self._stats["avg_nodes_per_trace"] = (
            self._stats["avg_nodes_per_trace"] * (total - 1) + len(trace.nodes)
        ) / total
        self._stats["avg_duration_ms"] = (
            self._stats["avg_duration_ms"] * (total - 1) + trace.total_duration_ms
        ) / total

        task_key = None
        for task, tid in self._active_traces.items():
            if tid == trace_id:
                task_key = task
                break
        if task_key:
            del self._active_traces[task_key]

        if len(self._traces) > self._max_traces:
            oldest_id = next(iter(self._traces))
            del self._traces[oldest_id]

        logger.debug(f"结束追踪: {trace_id} (结果: {outcome})")

    def get_trace(self, trace_id: str) -> Optional[DecisionTrace]:
        """获取追踪记录"""
        return self._traces.get(trace_id)

    def get_trace_dict(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """获取追踪记录(字典格式)"""
        trace = self.get_trace(trace_id)
        return trace.to_dict() if trace else None

    def get_decision_path(self, trace_id: str, node_id: str = None) -> List[Dict[str, Any]]:
        """获取决策路径"""
        trace = self.get_trace(trace_id)
        if not trace:
            return []

        if node_id:
            path = trace.get_path_to_root(node_id)
        else:
            leaves = [nid for nid, n in trace.nodes.items() if not n.children_ids]
            if leaves:
                path = trace.get_path_to_root(leaves[-1])
            else:
                path = [trace.nodes[trace.root_node_id]]

        return [node.to_dict() for node in path]

    def get_recent_traces(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取最近的追踪记录"""
        traces = list(self._traces.values())[-limit:]
        return [
            {
                "trace_id": t.trace_id,
                "task": t.task[:50],
                "status": t.status,
                "node_count": len(t.nodes),
                "duration_ms": round(t.total_duration_ms, 2),
                "outcome": t.outcome,
                "start_time": t.start_time
            }
            for t in traces
        ]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_traces": self._stats["total_traces"],
            "completed_traces": self._stats["completed_traces"],
            "active_traces": len(self._active_traces),
            "avg_nodes_per_trace": round(self._stats["avg_nodes_per_trace"], 1),
            "avg_duration_ms": round(self._stats["avg_duration_ms"], 2),
            "by_outcome": dict(self._stats["by_outcome"]),
            "stored_traces": len(self._traces)
        }


decision_tracer = DecisionTracer()


def get_decision_tracer() -> DecisionTracer:
    """获取全局决策追踪器"""
    return decision_tracer
