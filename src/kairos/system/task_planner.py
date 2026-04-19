#!/usr/bin/env python3
"""
任务规划闭环引擎 v1.0
实现 Plan→Do→Check→Act 反思迭代循环

设计理念来自增强型设计开发.md：
- 意图解析：理解核心需求、隐藏诉求、约束条件
- 任务规划：拆解多级子任务、排定执行顺序
- 动作执行：调用工具/API落地
- 结果校验：核对执行效果、误差检测
- 复盘修正：记录错误原因、优化规划逻辑、沉淀经验
"""

import time
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger("TaskPlanner")


class PlanStatus(str, Enum):
    """计划状态"""
    PENDING = "待执行"
    IN_PROGRESS = "执行中"
    COMPLETED = "已完成"
    FAILED = "失败"
    REVISED = "已修正"
    CANCELLED = "已取消"


class StepStatus(str, Enum):
    """步骤状态"""
    PENDING = "待执行"
    RUNNING = "运行中"
    DONE = "完成"
    ERROR = "错误"
    SKIPPED = "跳过"


@dataclass
class PlanStep:
    """计划步骤"""
    step_id: str
    description: str
    status: str = StepStatus.PENDING
    tool: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PlanResult:
    """计划执行结果"""
    plan_id: str
    goal: str
    status: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    total_duration_ms: float = 0.0
    revision_count: int = 0
    lessons: List[str] = field(default_factory=list)
    confidence: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TaskPlanner:
    """任务规划闭环引擎

    核心流程：Plan → Do → Check → Act
    每次执行后自动复盘，沉淀经验教训
    """

    def __init__(self, llm_client=None, tool_registry: Dict[str, Callable] = None):
        """初始化任务规划引擎

        Args:
            llm_client: LLM客户端（用于智能规划）
            tool_registry: 工具注册表 {name: callable}
        """
        self.llm_client = llm_client
        self.tool_registry = tool_registry or {}
        self._plan_history: List[PlanResult] = []
        self._lesson_library: List[Dict[str, Any]] = []
        self._stats = {
            "total_plans": 0,
            "completed_plans": 0,
            "failed_plans": 0,
            "revised_plans": 0,
            "avg_steps_per_plan": 0.0
        }

    def register_tool(self, name: str, func: Callable):
        """注册工具"""
        self.tool_registry[name] = func
        logger.info("注册工具: %s", name)

    async def plan_and_execute(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        max_revisions: int = 2
    ) -> PlanResult:
        """完整的 Plan→Do→Check→Act 循环

        Args:
            goal: 目标描述
            context: 上下文信息
            max_revisions: 最大修正次数

        Returns:
            PlanResult 执行结果
        """
        plan_id = f"plan_{int(time.time() * 1000)}"
        logger.info("开始规划: %s (id=%s)", goal[:60], plan_id)

        # Plan: 制定计划
        steps = await self._create_plan(goal, context)
        if not steps:
            return PlanResult(
                plan_id=plan_id, goal=goal,
                status=PlanStatus.FAILED,
                lessons=["无法生成执行计划"]
            )

        revision_count = 0
        total_start = time.time()

        while revision_count <= max_revisions:
            # Do: 执行计划
            execution_results = await self._execute_steps(steps)

            # Check: 校验结果
            check_result = await self._check_results(goal, execution_results, context)

            if check_result["success"]:
                # 成功：沉淀经验
                lessons = self._extract_lessons(goal, steps, execution_results, success=True)
                self._add_lessons(lessons)

                total_ms = (time.time() - total_start) * 1000
                result = PlanResult(
                    plan_id=plan_id, goal=goal,
                    status=PlanStatus.COMPLETED,
                    steps=[s.to_dict() for s in steps],
                    total_duration_ms=round(total_ms, 1),
                    revision_count=revision_count,
                    lessons=lessons,
                    confidence=check_result.get("confidence", 0.8)
                )
                self._record_plan(result)
                return result

            # Act: 修正计划
            if revision_count < max_revisions:
                logger.info("计划未达标，开始第%d次修正", revision_count + 1)
                steps = await self._revise_plan(
                    goal, steps, execution_results, check_result, context
                )
                revision_count += 1
            else:
                break

        # 最终失败
        lessons = self._extract_lessons(goal, steps, execution_results if 'execution_results' in dir() else [], success=False)
        self._add_lessons(lessons)
        total_ms = (time.time() - total_start) * 1000

        result = PlanResult(
            plan_id=plan_id, goal=goal,
            status=PlanStatus.FAILED,
            steps=[s.to_dict() for s in steps],
            total_duration_ms=round(total_ms, 1),
            revision_count=revision_count,
            lessons=lessons,
            confidence=0.0
        )
        self._record_plan(result)
        return result

    async def _create_plan(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[PlanStep]:
        """Plan阶段：制定执行计划"""
        if self.llm_client:
            return await self._llm_create_plan(goal, context)
        return self._rule_create_plan(goal, context)

    async def _llm_create_plan(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[PlanStep]:
        """LLM驱动的智能规划"""
        available_tools = list(self.tool_registry.keys())
        prompt = (
            f"请为以下目标制定执行计划，返回JSON数组。\n"
            f"目标：{goal}\n"
            f"可用工具：{available_tools}\n"
            f"格式：[{{\"description\": \"步骤描述\", \"tool\": \"工具名\", "
            f"\"parameters\": {{}}}}]\n"
        )
        try:
            if hasattr(self.llm_client, 'chat'):
                response = await asyncio.to_thread(
                    self.llm_client.chat, prompt,
                    "你是任务规划专家，只返回JSON数组。"
                )
            elif hasattr(self.llm_client, 'call_llm'):
                result = await self.llm_client.call_llm(
                    user_prompt=prompt,
                    system_prompt="你是任务规划专家，只返回JSON数组。"
                )
                response = result.get("message", {}).get("content", "")
            else:
                return self._rule_create_plan(goal, context)

            steps_data = self._parse_json_array(response)
            if steps_data:
                return [
                    PlanStep(
                        step_id=f"step_{i}",
                        description=s.get("description", f"步骤{i+1}"),
                        tool=s.get("tool", ""),
                        parameters=s.get("parameters", {})
                    )
                    for i, s in enumerate(steps_data)
                ]
        except Exception as e:
            logger.warning("LLM规划失败，回退规则引擎: %s", e)

        return self._rule_create_plan(goal, context)

    def _rule_create_plan(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[PlanStep]:
        """基于规则的任务分解"""
        return [
            PlanStep(
                step_id="step_0",
                description=f"分析目标: {goal}",
                tool="analyze",
                parameters={"goal": goal}
            ),
            PlanStep(
                step_id="step_1",
                description=f"执行核心任务: {goal}",
                tool="execute",
                parameters={"goal": goal, "context": context or {}}
            ),
            PlanStep(
                step_id="step_2",
                description="验证执行结果",
                tool="verify",
                parameters={"goal": goal}
            )
        ]

    async def _execute_steps(self, steps: List[PlanStep]) -> List[Dict[str, Any]]:
        """Do阶段：逐步执行计划"""
        results = []
        for step in steps:
            step_start = time.time()
            step.status = StepStatus.RUNNING
            step.started_at = time.time()

            try:
                if step.tool and step.tool in self.tool_registry:
                    tool_func = self.tool_registry[step.tool]
                    if asyncio.iscoroutinefunction(tool_func):
                        result = await tool_func(**step.parameters)
                    else:
                        result = await asyncio.to_thread(tool_func, **step.parameters)
                    step.result = result if isinstance(result, dict) else {"output": str(result)}
                    step.status = StepStatus.DONE
                else:
                    step.result = {"output": f"模拟执行: {step.description}"}
                    step.status = StepStatus.DONE

            except Exception as e:
                step.error = str(e)
                step.status = StepStatus.ERROR
                step.result = {"error": str(e)}
                logger.error("步骤 %s 执行失败: %s", step.step_id, e)

            step.completed_at = time.time()
            step.duration_ms = (time.time() - step_start) * 1000
            results.append(step.to_dict())

        return results

    async def _check_results(
        self,
        goal: str,
        results: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Check阶段：校验执行结果"""
        error_steps = [r for r in results if r.get("status") == StepStatus.ERROR]
        if error_steps:
            return {
                "success": False,
                "reason": f"{len(error_steps)}个步骤执行失败",
                "failed_steps": error_steps,
                "confidence": 0.0
            }

        completed_steps = [r for r in results if r.get("status") == StepStatus.DONE]
        if not completed_steps:
            return {"success": False, "reason": "无成功步骤", "confidence": 0.0}

        confidence = len(completed_steps) / max(len(results), 1)

        return {
            "success": confidence >= 0.8,
            "reason": "执行成功" if confidence >= 0.8 else f"完成率不足: {confidence:.0%}",
            "confidence": round(confidence, 2)
        }

    async def _revise_plan(
        self,
        goal: str,
        original_steps: List[PlanStep],
        results: List[Dict[str, Any]],
        check_result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[PlanStep]:
        """Act阶段：修正计划"""
        revised_steps = []
        for i, step in enumerate(original_steps):
            if step.status == StepStatus.ERROR:
                revised_steps.append(PlanStep(
                    step_id=f"step_{i}_rev",
                    description=f"重试: {step.description}",
                    tool=step.tool,
                    parameters=step.parameters
                ))
            else:
                revised_steps.append(step)

        if not any(s.status == StepStatus.ERROR for s in original_steps):
            revised_steps.append(PlanStep(
                step_id=f"step_extra",
                description=f"补充执行: 提升完成质量",
                tool="execute",
                parameters={"goal": goal, "context": context or {}}
            ))

        return revised_steps

    def _extract_lessons(
        self,
        goal: str,
        steps: List[PlanStep],
        results: List[Dict[str, Any]],
        success: bool
    ) -> List[str]:
        """提取经验教训"""
        lessons = []

        if success:
            lessons.append(f"目标「{goal[:30]}」执行成功")
            effective_tools = [
                s.tool for s in steps
                if s.status == StepStatus.DONE and s.tool
            ]
            if effective_tools:
                lessons.append(f"有效工具: {', '.join(set(effective_tools))}")
        else:
            lessons.append(f"目标「{goal[:30]}」执行失败")
            error_steps = [s for s in steps if s.status == StepStatus.ERROR]
            for es in error_steps:
                lessons.append(f"步骤失败: {es.description} - {es.error}")

        return lessons

    def _add_lessons(self, lessons: List[str]):
        """添加到经验库"""
        for lesson in lessons:
            self._lesson_library.append({
                "lesson": lesson,
                "timestamp": time.time()
            })

    def _record_plan(self, result: PlanResult):
        """记录计划结果"""
        self._plan_history.append(result)
        self._stats["total_plans"] += 1
        if result.status == PlanStatus.COMPLETED:
            self._stats["completed_plans"] += 1
        elif result.status == PlanStatus.FAILED:
            self._stats["failed_plans"] += 1
        if result.revision_count > 0:
            self._stats["revised_plans"] += 1

    @staticmethod
    def _parse_json_array(text: str) -> Optional[List[Dict]]:
        """解析JSON数组"""
        try:
            t = text.strip()
            if "```json" in t:
                start = t.find("```json") + 7
                end = t.find("```", start)
                t = t[start:end].strip()
            arr_start = t.find("[")
            arr_end = t.rfind("]")
            if arr_start != -1 and arr_end > arr_start:
                return json.loads(t[arr_start:arr_end + 1])
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return dict(self._stats)

    def get_lessons(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取经验教训"""
        return self._lesson_library[-limit:]

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取计划历史"""
        return [r.to_dict() for r in self._plan_history[-limit:]]


_planner_instance: Optional[TaskPlanner] = None


def get_task_planner() -> TaskPlanner:
    """获取任务规划引擎单例"""
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = TaskPlanner()
    return _planner_instance
