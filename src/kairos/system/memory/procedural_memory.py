# -*- coding: utf-8 -*-
"""
程序记忆 (Procedural Memory)
存储学习到的流程和策略，支持自动复用

核心功能:
- 流程定义 (步骤序列/条件/参数)
- 流程执行 (顺序/条件/循环)
- 策略模板 (可参数化复用)
- 执行追踪 (成功/失败/优化)
- 自动优化 (步骤合并/跳过/重排)
"""

import logging
import uuid
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger("ProceduralMemory")


class StepType(Enum):
    """步骤类型"""
    ACTION = "action"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    SUB_PROCEDURE = "sub_procedure"


class ProcedureStatus(Enum):
    """流程状态"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    OPTIMIZED = "optimized"


@dataclass
class ProcedureStep:
    """流程步骤"""
    step_id: str
    step_type: StepType
    name: str
    description: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None
    next_step_id: Optional[str] = None
    on_failure: str = "abort"
    retry_count: int = 0
    timeout_ms: float = 30000.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "step_id": self.step_id,
            "step_type": self.step_type.value,
            "name": self.name,
            "description": self.description,
            "action": self.action,
            "parameters": self.parameters,
            "condition": self.condition,
            "next_step_id": self.next_step_id,
            "on_failure": self.on_failure,
            "retry_count": self.retry_count,
            "timeout_ms": self.timeout_ms
        }


@dataclass
class Procedure:
    """流程定义"""
    procedure_id: str
    name: str
    description: str
    category: str
    steps: List[ProcedureStep] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: ProcedureStatus = ProcedureStatus.ACTIVE
    version: int = 1
    success_count: int = 0
    failure_count: int = 0
    avg_duration_ms: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """成功率"""
        total = self.success_count + self.failure_count
        return self.success_count / max(total, 1)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "procedure_id": self.procedure_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "steps": [s.to_dict() for s in self.steps],
            "parameters": self.parameters,
            "status": self.status.value,
            "version": self.version,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(self.success_rate, 3),
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class ProceduralMemory:
    """
    程序记忆系统
    
    功能:
    - 流程存储与检索
    - 流程执行
    - 策略模板管理
    - 执行追踪
    - 自动优化
    """

    def __init__(self, max_procedures: int = 5000):
        self._procedures: Dict[str, Procedure] = {}
        self._name_index: Dict[str, str] = {}
        self._category_index: Dict[str, Set[str]] = {}
        self._execution_history: List[Dict[str, Any]] = []
        self._max_procedures = max_procedures
        self._max_history = 5000
        self._action_registry: Dict[str, Callable] = {}

        self._register_default_procedures()
        logger.info("程序记忆系统初始化")

    def _register_default_procedures(self):
        """注册默认流程"""
        self.create_procedure(
            name="simple_task",
            description="简单任务执行流程",
            category="execution",
            steps=[
                ProcedureStep(
                    step_id="step_1",
                    step_type=StepType.ACTION,
                    name="分析任务",
                    description="分析任务需求和上下文",
                    action="analyze_task"
                ),
                ProcedureStep(
                    step_id="step_2",
                    step_type=StepType.ACTION,
                    name="执行任务",
                    description="执行任务核心逻辑",
                    action="execute_task"
                ),
                ProcedureStep(
                    step_id="step_3",
                    step_type=StepType.ACTION,
                    name="验证结果",
                    description="验证执行结果",
                    action="verify_result"
                )
            ],
            tags=["default", "execution"]
        )

        self.create_procedure(
            name="learning_cycle",
            description="学习循环流程",
            category="learning",
            steps=[
                ProcedureStep(
                    step_id="step_1",
                    step_type=StepType.ACTION,
                    name="观察",
                    description="观察当前状态和输入",
                    action="observe"
                ),
                ProcedureStep(
                    step_id="step_2",
                    step_type=StepType.ACTION,
                    name="思考",
                    description="分析并制定策略",
                    action="think"
                ),
                ProcedureStep(
                    step_id="step_3",
                    step_type=StepType.ACTION,
                    name="行动",
                    description="执行策略",
                    action="act"
                ),
                ProcedureStep(
                    step_id="step_4",
                    step_type=StepType.ACTION,
                    name="反思",
                    description="评估结果并学习",
                    action="reflect"
                )
            ],
            tags=["default", "learning", "otac"]
        )

        self.create_procedure(
            name="error_recovery",
            description="错误恢复流程",
            category="recovery",
            steps=[
                ProcedureStep(
                    step_id="step_1",
                    step_type=StepType.CONDITION,
                    name="检测错误",
                    description="检测错误类型和严重程度",
                    action="detect_error",
                    condition="error_detected"
                ),
                ProcedureStep(
                    step_id="step_2",
                    step_type=StepType.ACTION,
                    name="分类错误",
                    description="确定错误类别",
                    action="classify_error"
                ),
                ProcedureStep(
                    step_id="step_3",
                    step_type=StepType.ACTION,
                    name="选择恢复策略",
                    description="基于错误类型选择恢复策略",
                    action="select_recovery"
                ),
                ProcedureStep(
                    step_id="step_4",
                    step_type=StepType.ACTION,
                    name="执行恢复",
                    description="执行恢复操作",
                    action="execute_recovery",
                    on_failure="escalate"
                )
            ],
            tags=["default", "recovery", "error"]
        )

    def create_procedure(self, name: str, description: str, category: str,
                        steps: List[ProcedureStep] = None,
                        parameters: Dict[str, Any] = None,
                        tags: List[str] = None) -> str:
        """
        创建流程
        
        Args:
            name: 流程名称
            description: 描述
            category: 类别
            steps: 步骤列表
            parameters: 参数
            tags: 标签
            
        Returns:
            流程ID
        """
        if name in self._name_index:
            proc_id = self._name_index[name]
            proc = self._procedures[proc_id]
            proc.steps = steps or proc.steps
            proc.parameters = parameters or proc.parameters
            proc.version += 1
            proc.updated_at = datetime.now().isoformat()
            if tags:
                proc.tags = tags
            logger.info(f"更新流程: {name} (v{proc.version})")
            return proc_id

        if len(self._procedures) >= self._max_procedures:
            self._evict_lowest_success()

        procedure_id = f"proc_{uuid.uuid4().hex[:12]}"
        procedure = Procedure(
            procedure_id=procedure_id,
            name=name,
            description=description,
            category=category,
            steps=steps or [],
            parameters=parameters or {},
            tags=tags or []
        )

        self._procedures[procedure_id] = procedure
        self._name_index[name] = procedure_id

        if category not in self._category_index:
            self._category_index[category] = set()
        self._category_index[category].add(procedure_id)

        logger.info(f"创建流程: {name} (类别: {category}, 步骤: {len(steps or [])})")
        return procedure_id

    def get_procedure(self, name: str) -> Optional[Procedure]:
        """获取流程"""
        proc_id = self._name_index.get(name)
        return self._procedures.get(proc_id) if proc_id else None

    def find_procedures(self, query: str = None, category: str = None,
                       tags: List[str] = None, limit: int = 20) -> List[Procedure]:
        """查找流程"""
        results = list(self._procedures.values())

        if category:
            results = [p for p in results if p.category == category]

        if tags:
            results = [p for p in results if any(t in p.tags for t in tags)]

        if query:
            query_lower = query.lower()
            scored = []
            for proc in results:
                score = 0.0
                if query_lower in proc.name.lower():
                    score += 1.0
                if query_lower in proc.description.lower():
                    score += 0.5
                if score > 0:
                    scored.append((proc, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            results = [p for p, _ in scored]

        results.sort(key=lambda p: p.success_rate, reverse=True)
        return results[:limit]

    def record_execution(self, procedure_name: str, success: bool,
                        duration_ms: float = 0.0,
                        context: Dict[str, Any] = None):
        """记录执行结果"""
        proc = self.get_procedure(procedure_name)
        if not proc:
            return

        if success:
            proc.success_count += 1
        else:
            proc.failure_count += 1

        total = proc.success_count + proc.failure_count
        proc.avg_duration_ms = (
            proc.avg_duration_ms * (total - 1) + duration_ms
        ) / total

        proc.updated_at = datetime.now().isoformat()

        self._execution_history.append({
            "procedure_id": proc.procedure_id,
            "procedure_name": procedure_name,
            "success": success,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat(),
            "context": context or {}
        })

        if len(self._execution_history) > self._max_history:
            self._execution_history = self._execution_history[-self._max_history:]

    def register_action(self, action_name: str, handler: Callable):
        """注册动作处理器"""
        self._action_registry[action_name] = handler

    def optimize_procedure(self, procedure_name: str) -> Dict[str, Any]:
        """
        优化流程
        
        Args:
            procedure_name: 流程名称
            
        Returns:
            优化结果
        """
        proc = self.get_procedure(procedure_name)
        if not proc:
            return {"status": "error", "message": "流程不存在"}

        optimizations = []

        executions = [
            e for e in self._execution_history
            if e["procedure_name"] == procedure_name
        ]

        if not executions:
            return {"status": "no_data", "message": "无执行数据"}

        recent_success_rate = sum(1 for e in executions[-20:] if e["success"]) / min(len(executions), 20)

        if recent_success_rate < 0.5:
            optimizations.append({
                "type": "restructure",
                "description": f"成功率低 ({recent_success_rate:.1%})，建议重构流程"
            })

        avg_duration = sum(e["duration_ms"] for e in executions[-20:]) / min(len(executions), 20)
        if avg_duration > 5000:
            optimizations.append({
                "type": "performance",
                "description": f"平均耗时 {avg_duration:.0f}ms，建议优化性能"
            })

        if proc.success_rate > 0.9 and proc.success_count > 10:
            proc.status = ProcedureStatus.OPTIMIZED
            optimizations.append({
                "type": "status_upgrade",
                "description": "流程已标记为优化状态"
            })

        return {
            "status": "success",
            "procedure": procedure_name,
            "success_rate": recent_success_rate,
            "avg_duration_ms": avg_duration,
            "optimizations": optimizations
        }

    def _evict_lowest_success(self):
        """驱逐成功率最低的流程"""
        if not self._procedures:
            return

        min_proc_id = min(
            self._procedures,
            key=lambda pid: self._procedures[pid].success_rate
        )
        proc = self._procedures[min_proc_id]
        self._name_index.pop(proc.name, None)
        if proc.category in self._category_index:
            self._category_index[proc.category].discard(min_proc_id)
        del self._procedures[min_proc_id]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_procedures": len(self._procedures),
            "total_executions": len(self._execution_history),
            "categories": len(self._category_index),
            "registered_actions": len(self._action_registry),
            "by_status": {
                s.value: sum(1 for p in self._procedures.values() if p.status == s)
                for s in ProcedureStatus
            },
            "top_procedures": [
                {
                    "name": p.name,
                    "success_rate": round(p.success_rate, 3),
                    "executions": p.success_count + p.failure_count,
                    "avg_duration_ms": round(p.avg_duration_ms, 2)
                }
                for p in sorted(
                    self._procedures.values(),
                    key=lambda x: x.success_count + x.failure_count,
                    reverse=True
                )[:10]
            ]
        }


procedural_memory = ProceduralMemory()


def get_procedural_memory() -> ProceduralMemory:
    """获取全局程序记忆"""
    return procedural_memory
