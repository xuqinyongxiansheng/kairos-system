"""
自主执行循环模块 (OTAC - Observe-Think-Act-Check) - 异步优化版
实现完整的自主任务执行闭环
已迁移到统一LLM客户端，消除同步阻塞
"""

import asyncio
import logging
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from kairos.system.config import settings

logger = logging.getLogger(__name__)


class OTACPhase(Enum):
    OBSERVE = "observe"
    THINK = "think"
    ACT = "act"
    CHECK = "check"


class TaskStatus(Enum):
    PENDING = "pending"
    OBSERVING = "observing"
    THINKING = "thinking"
    ACTING = "acting"
    CHECKING = "checking"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class OTACContext:
    task_id: str
    task_description: str
    current_phase: str
    observations: List[Dict[str, Any]]
    thoughts: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    checks: List[Dict[str, Any]]
    status: str
    iterations: int
    max_iterations: int


class AutonomousExecutionEngine:
    """自主执行引擎（异步版）"""

    def __init__(self, model: str = None, max_iterations: int = None):
        self.model = model or settings.ollama.default_model
        self.max_iterations = max_iterations or settings.cognitive.max_iterations
        self.active_tasks: Dict[str, OTACContext] = {}
        self.task_history: List[Dict[str, Any]] = []
        self.tools = {}
        self.skills = {}
        self._llm_client = None

        self._register_default_tools()
        logger.info("自主执行引擎初始化 (model=%s, max_iterations=%d)", self.model, self.max_iterations)

    async def _get_llm(self):
        if self._llm_client is None:
            from kairos.system.unified_llm_client import get_unified_client
            self._llm_client = get_unified_client()
        return self._llm_client

    async def _llm_chat(self, prompt: str, system: str = None) -> str:
        client = await self._get_llm()
        result = await client.chat(
            user_prompt=prompt,
            system_prompt=system or "你是自主执行引擎，按指令执行任务。",
            model=self.model,
            use_cache=False,
        )
        if result.get("status") == "success":
            return result.get("response", "")
        raise Exception(result.get("message", "LLM调用失败"))

    def _register_default_tools(self):
        self.tools = {
            "browser_navigate": {"description": "导航到指定URL", "parameters": ["url"], "category": "browser"},
            "browser_click": {"description": "点击页面元素", "parameters": ["selector"], "category": "browser"},
            "browser_type": {"description": "在输入框中输入文本", "parameters": ["selector", "text"], "category": "browser"},
            "browser_extract": {"description": "提取页面内容", "parameters": ["selector"], "category": "browser"},
            "file_read": {"description": "读取文件内容", "parameters": ["path"], "category": "file"},
            "file_write": {"description": "写入文件内容", "parameters": ["path", "content"], "category": "file"},
            "command_execute": {"description": "执行系统命令", "parameters": ["command"], "category": "system"},
            "http_request": {"description": "发送HTTP请求", "parameters": ["url", "method", "data"], "category": "network"},
            "search_web": {"description": "搜索网页", "parameters": ["query"], "category": "web"},
            "analyze_code": {"description": "分析代码", "parameters": ["code", "language"], "category": "code"},
        }

    def register_tool(self, name: str, description: str, parameters: List[str],
                      executor: callable, category: str = "custom"):
        self.tools[name] = {"description": description, "parameters": parameters, "executor": executor, "category": category}
        logger.info("工具注册成功: %s", name)

    def register_skill(self, name: str, skill_definition: Dict[str, Any]):
        self.skills[name] = skill_definition
        logger.info("技能注册成功: %s", name)

    async def execute_task(self, task_description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        task_id = f"task_{int(datetime.now().timestamp())}"

        otac_context = OTACContext(
            task_id=task_id,
            task_description=task_description,
            current_phase=OTACPhase.OBSERVE.value,
            observations=[],
            thoughts=[],
            actions=[],
            checks=[],
            status=TaskStatus.PENDING.value,
            iterations=0,
            max_iterations=self.max_iterations,
        )

        self.active_tasks[task_id] = otac_context
        logger.info("开始执行任务: %s - %s...", task_id, task_description[:50])

        try:
            while otac_context.iterations < otac_context.max_iterations:
                otac_context.iterations += 1

                otac_context.status = TaskStatus.OBSERVING.value
                otac_context.current_phase = OTACPhase.OBSERVE.value
                observation = await self._observe(otac_context, context)
                otac_context.observations.append(observation)

                otac_context.status = TaskStatus.THINKING.value
                otac_context.current_phase = OTACPhase.THINK.value
                thought = await self._think(otac_context)
                otac_context.thoughts.append(thought)

                if thought.get("task_completed", False):
                    otac_context.status = TaskStatus.COMPLETED.value
                    break

                otac_context.status = TaskStatus.ACTING.value
                otac_context.current_phase = OTACPhase.ACT.value
                action_result = await self._act(otac_context, thought)
                otac_context.actions.append(action_result)

                otac_context.status = TaskStatus.CHECKING.value
                otac_context.current_phase = OTACPhase.CHECK.value
                check_result = await self._check(otac_context, action_result)
                otac_context.checks.append(check_result)

                if check_result.get("success", False) and check_result.get("task_complete", False):
                    otac_context.status = TaskStatus.COMPLETED.value
                    break
                elif not check_result.get("success", False):
                    logger.warning("任务检查失败，调整策略: %s", check_result.get("error", "unknown"))

            if otac_context.iterations >= otac_context.max_iterations:
                otac_context.status = TaskStatus.FAILED.value

            result = self._build_result(otac_context)
            self.task_history.append(result)
            return result

        except Exception as e:
            logger.error("任务执行失败: %s", e)
            otac_context.status = TaskStatus.FAILED.value
            return self._build_result(otac_context, error=str(e))

    async def _observe(self, context: OTACContext, initial_context: Dict[str, Any] = None) -> Dict[str, Any]:
        observation = {"phase": "observe", "iteration": context.iterations, "timestamp": datetime.now().isoformat(), "data": {}}

        try:
            observation["data"]["task"] = context.task_description
            observation["data"]["previous_actions"] = [a.get("action", "") for a in context.actions[-3:]]
            observation["data"]["previous_results"] = [a.get("result", "") for a in context.actions[-3:]]
            if initial_context:
                observation["data"]["initial_context"] = initial_context

            prompt = f"当前任务: {context.task_description}\n已执行的操作: {json.dumps(context.actions[-3:], ensure_ascii=False, indent=2) if context.actions else '无'}\n请观察并总结当前状态，识别需要关注的关键信息。"

            response_text = await self._llm_chat(prompt)
            observation["analysis"] = response_text
            logger.info("观察阶段完成: 迭代%d", context.iterations)
            return observation

        except Exception as e:
            observation["error"] = str(e)
            logger.error("观察阶段失败: %s", e)
            return observation

    async def _think(self, context: OTACContext) -> Dict[str, Any]:
        thought = {"phase": "think", "iteration": context.iterations, "timestamp": datetime.now().isoformat()}

        try:
            available_tools = list(self.tools.keys())
            available_skills = list(self.skills.keys())

            prompt = f"当前任务: {context.task_description}\n观察结果: {context.observations[-1].get('analysis', '无') if context.observations else '无'}\n可用工具: {available_tools}\n可用技能: {available_skills}\n请思考并决定下一步行动。以JSON格式输出：{{\"reasoning\":\"思考过程\",\"next_action\":\"工具名称\",\"parameters\":{{}},\"expected_outcome\":\"预期结果\",\"task_completed\":false}}"

            response_text = await self._llm_chat(prompt)

            try:
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    thought["plan"] = json.loads(json_match.group())
                else:
                    thought["plan"] = {"reasoning": response_text, "next_action": "unknown"}
            except Exception:
                thought["plan"] = {"reasoning": response_text, "next_action": "unknown"}

            thought["reasoning"] = thought["plan"].get("reasoning", "")
            thought["next_action"] = thought["plan"].get("next_action", "")
            thought["parameters"] = thought["plan"].get("parameters", {})
            thought["task_completed"] = thought["plan"].get("task_completed", False)

            logger.info("思考阶段完成: 下一步行动=%s", thought["next_action"])
            return thought

        except Exception as e:
            thought["error"] = str(e)
            logger.error("思考阶段失败: %s", e)
            return thought

    async def _act(self, context: OTACContext, thought: Dict[str, Any]) -> Dict[str, Any]:
        action = {
            "phase": "act", "iteration": context.iterations,
            "timestamp": datetime.now().isoformat(),
            "action": thought.get("next_action", "unknown"),
            "parameters": thought.get("parameters", {}),
        }

        try:
            tool_name = action["action"]
            if tool_name in self.tools:
                tool = self.tools[tool_name]
                if "executor" in tool and callable(tool["executor"]):
                    result = await tool["executor"](**action["parameters"])
                else:
                    result = {"status": "simulated", "message": f"模拟执行: {tool_name}"}
                action["result"] = result
            elif tool_name in self.skills:
                skill = self.skills[tool_name]
                action["result"] = await self._execute_skill(skill, action["parameters"])
            else:
                action["result"] = {"status": "error", "message": f"未知工具: {tool_name}"}

            logger.info("行动阶段完成: %s", tool_name)
            return action

        except Exception as e:
            action["error"] = str(e)
            action["result"] = {"status": "error", "error": str(e)}
            logger.error("行动阶段失败: %s", e)
            return action

    async def _check(self, context: OTACContext, action_result: Dict[str, Any]) -> Dict[str, Any]:
        check = {"phase": "check", "iteration": context.iterations, "timestamp": datetime.now().isoformat()}

        try:
            prompt = f"当前任务: {context.task_description}\n执行的操作: {action_result.get('action', 'unknown')}\n执行结果: {json.dumps(action_result.get('result', {}), ensure_ascii=False)}\n请检查执行结果是否符合预期，任务是否完成。以JSON格式输出：{{\"success\":true/false,\"analysis\":\"结果分析\",\"issues\":[\"问题列表\"],\"task_complete\":true/false,\"next_steps\":\"建议的下一步\"}}"

            response_text = await self._llm_chat(prompt)

            try:
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    check["evaluation"] = json.loads(json_match.group())
                else:
                    check["evaluation"] = {"success": False, "analysis": response_text}
            except Exception:
                check["evaluation"] = {"success": False, "analysis": response_text}

            check["success"] = check["evaluation"].get("success", False)
            check["task_complete"] = check["evaluation"].get("task_complete", False)

            logger.info("检查阶段完成: 成功=%s", check["success"])
            return check

        except Exception as e:
            check["error"] = str(e)
            check["success"] = False
            logger.error("检查阶段失败: %s", e)
            return check

    async def _execute_skill(self, skill: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        steps = skill.get("steps", [])
        results = []
        for i, step in enumerate(steps):
            step_result = {"step": i + 1, "action": step.get("action", "unknown"), "parameters": step.get("parameters", {})}
            tool_name = step.get("action")
            if tool_name in self.tools:
                tool = self.tools[tool_name]
                if "executor" in tool and callable(tool["executor"]):
                    result = await tool["executor"](**step.get("parameters", {}))
                else:
                    result = {"status": "simulated"}
                step_result["result"] = result
            else:
                step_result["result"] = {"status": "error", "message": f"未知工具: {tool_name}"}
            results.append(step_result)
        return {"status": "success", "steps_executed": len(results), "results": results}

    def _build_result(self, context: OTACContext, error: str = None) -> Dict[str, Any]:
        return {
            "task_id": context.task_id,
            "task_description": context.task_description,
            "status": context.status,
            "iterations": context.iterations,
            "observations_count": len(context.observations),
            "thoughts_count": len(context.thoughts),
            "actions_count": len(context.actions),
            "checks_count": len(context.checks),
            "final_observation": context.observations[-1] if context.observations else None,
            "final_thought": context.thoughts[-1] if context.thoughts else None,
            "final_action": context.actions[-1] if context.actions else None,
            "final_check": context.checks[-1] if context.checks else None,
            "error": error,
            "completed_at": datetime.now().isoformat(),
        }

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        if task_id in self.active_tasks:
            context = self.active_tasks[task_id]
            return {"status": "success", "task": {"task_id": context.task_id, "status": context.status, "current_phase": context.current_phase, "iterations": context.iterations}}
        return {"status": "error", "message": f"任务不存在: {task_id}"}

    def get_available_tools(self) -> Dict[str, Any]:
        return {"status": "success", "tools": self.tools, "count": len(self.tools)}

    def get_available_skills(self) -> Dict[str, Any]:
        return {"status": "success", "skills": self.skills, "count": len(self.skills)}


autonomous_engine = AutonomousExecutionEngine()
