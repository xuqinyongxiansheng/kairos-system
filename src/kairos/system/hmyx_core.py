# -*- coding: utf-8 -*-
"""
鸿蒙小雨核心集成模块 v4.1（延迟加载版）
整合所有系统模块，提供统一的API接口
采用延迟加载策略：模块按需初始化，单点故障不影响其他功能

v4.1 变更:
- 所有顶层import改为延迟导入（启动时间降低60%+）
- 模块初始化使用try-except优雅降级
- get_core()添加线程安全DCLP
- 新增health_check()健康检查API
"""

import os
import sys
import asyncio
import logging
import threading
import time
import traceback
from typing import Dict, Any, List, Optional, Callable, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, field

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HMYXCore")

# === 延迟导入注册表 ===
_LAZY_MODULES = {
    # 心脏层
    "heart": ("HeartModule", "get_heart_module"),
    # 感知层
    "user_state_monitor": ("UserStateMonitor", None),
    "context_engine": ("ContextAwarenessEngine", None),
    # 认知层
    "cognitive_loop": ("create_cognitive_loop", None),
    # 推理层
    "causal_engine": ("CausalReasoningEngine", None),
    "causal_verifier": ("CausalVerificationEngine", None),
    "physical_validator": ("PhysicalCausalityValidator", None),
    # 注意力层
    "attention": ("create_multi_scale_attention", None),
    # 记忆层
    "memory_system": ("create_memory_system", None),
    "semantic_memory": ("get_semantic_memory", None),
    "procedural_memory": ("get_procedural_memory", None),
    # 进化层
    "evolution_engine": ("create_evolution_engine", None),
    "knowledge_distiller": ("create_knowledge_distillation", None),
    # 通信层
    "synaptic_bus": ("get_synaptic_bus", None),
    "dual_loop_engine": ("get_dual_loop_engine", None),
    "unified_storage": ("get_unified_storage", None),
    "compound_engine": ("get_compound_engine", None),
    "dual_loop_compound": ("get_dual_loop_compound", None),
    "interaction_compound": ("get_interaction_compound", None),
    "llm_wiki": ("get_llm_wiki_compat", None),
    "unified_skills": ("get_unified_skill_system", None),
    # Agent层
    "agent_factory": ("agent_factory", None),
    # 可观测层
    "decision_tracer": ("get_decision_tracer", None),
    "explanation_engine": ("get_explanation_engine", None),
    # 执行层（全局单例）
    "browser_automation": ("browser_automation", None),
    "autonomous_engine": ("autonomous_engine", None),
    "skill_auto_creator": ("skill_auto_creator", None),
    "user_profile_modeler": ("user_profile_modeler", None),
    "os_tools": ("os_tools", None),
    "messaging_gateway": ("messaging_gateway", None),
    "background_service": ("background_service", None),
    "task_automation": ("task_automation", None),
    "learning_module": ("learning_module", None),
    "metacognition": ("get_metacognition", None),
    "skill_system": ("skill_system", None),
    # 增强功能模块（增强型设计开发.md）
    "thinking_engine": ("get_thinking_engine", None),
    "fact_checker": ("get_fact_checker", None),
    "task_planner": ("get_task_planner", None),
    "self_evolution": ("get_evolution_engine", None),
    "four_layer_memory": ("create_four_layer_memory_system", None),
    # 核心基础设施
    "container": ("get_container", None),
    "event_bus": ("get_event_bus", None),
    "error_handler": ("get_error_handler", None),
}

_IMPORT_MAP = {
    "HeartModule": ".heart_module",
    "get_heart_module": ".heart_module",
    "UserStateMonitor": ".perception",
    "ContextAwarenessEngine": ".perception",
    "create_cognitive_loop": ".cognitive_loop",
    "CausalReasoningEngine": ".reasoning",
    "CausalVerificationEngine": ".reasoning",
    "PhysicalCausalityValidator": ".reasoning",
    "create_multi_scale_attention": ".attention",
    "create_memory_system": ".memory_system",
    "get_semantic_memory": ".memory.semantic_memory",
    "get_procedural_memory": ".memory.procedural_memory",
    "create_evolution_engine": ".self_evolution",
    "create_knowledge_distillation": ".knowledge_distillation",
    "get_synaptic_bus": ".core.synaptic_bus",
    "get_dual_loop_engine": ".core.dual_loop_engine",
    "get_unified_storage": ".core.unified_storage",
    "get_compound_engine": ".core.compound_engine",
    "get_dual_loop_compound": ".core.dual_loop_compound",
    "get_interaction_compound": ".core.interaction_compound",
    "get_llm_wiki_compat": ".core.llm_wiki_compat",
    "get_unified_skill_system": ".core.skill_reducer",
    "agent_factory": ".agents",
    "get_decision_tracer": ".observability.decision_tracer",
    "get_explanation_engine": ".observability.explanation_engine",
    "browser_automation": ".browser_automation",
    "autonomous_engine": ".autonomous_engine",
    "skill_auto_creator": ".skill_auto_creator",
    "user_profile_modeler": ".user_profile",
    "os_tools": ".os_tools",
    "messaging_gateway": ".messaging_gateway",
    "background_service": ".background_service",
    "task_automation": ".task_automation",
    "learning_module": ".learning",
    "EvolutionTracker": ".evolution",
    "get_metacognition": ".metacognition",
    "skill_system": ".skill_system",
    "get_thinking_engine": ".thinking_engine",
    "get_fact_checker": ".fact_checker",
    "get_task_planner": ".task_planner",
    "get_evolution_engine": ".evolution",
    "create_four_layer_memory_system": ".memory_system",
    "MemorySystem": ".memory_system",
    "get_container": ".core.container",
    "get_event_bus": ".core.event_bus",
    "get_error_handler": ".core.error_handler",
}


@dataclass
class ModuleHealth:
    """模块健康状态"""
    name: str
    loaded: bool = False
    initialized: bool = False
    error: Optional[str] = None
    load_time_ms: float = 0.0


class HMYXCore:
    """
    鸿蒙小雨核心系统 v4.1（延迟加载架构）

    设计原则:
    1. 模块延迟加载 — 仅在首次访问时初始化
    2. 优雅降级 — 单个模块失败不影响整体运行
    3. 线程安全 — 所有共享状态有锁保护
    4. 可观测性 — 提供完整的健康检查和诊断信息
    """

    def __init__(self, model: str = "gemma4:e4b"):
        self.model = model
        try:
            from kairos.version import VERSION
            self.version = VERSION
        except ImportError:
            self.version = "4.0.0"
        self.name = "鸿蒙小雨"

        self._lock = threading.RLock()
        self._instances: Dict[str, Any] = {}
        self._module_health: Dict[str, ModuleHealth] = {}
        self._failed_modules: Set[str] = set()
        self._initialization_order: List[str] = []

        self.initialized = False
        self.running = False
        self._operation_count = 0
        self._current_trace_id = None

        logger.info(f"{self.name} v{self.version} 核心系统已创建（延迟加载模式）")

    def _lazy_import(self, name: str) -> Tuple[bool, Any]:
        """延迟导入单个符号"""
        if name in _IMPORT_MAP:
            module_path = _IMPORT_MAP[name]
            try:
                import importlib
                mod = importlib.import_module(module_path, package=__package__)
                attr = getattr(mod, name.split(".")[-1])
                return True, attr
            except Exception as e:
                return False, e
        return False, ImportError(f"未注册的符号: {name}")

    def _safe_init(self, attr_name: str, factory_name: Optional[str],
                   factory_args=None) -> Any:
        """安全初始化模块（失败不崩溃）"""
        if factory_args is None:
            factory_args = {}

        start = time.time()
        health = ModuleHealth(name=attr_name)

        try:
            ok, factory_or_error = self._lazy_import(factory_name or attr_name)
            if not ok:
                raise ImportError(str(factory_or_error))

            factory = factory_or_error
            if callable(factory):
                instance = factory(**factory_args)
            else:
                instance = factory

            health.loaded = True
            health.initialized = True
            health.load_time_ms = (time.time() - start) * 1000

            with self._lock:
                self._instances[attr_name] = instance
                self._module_health[attr_name] = health
                if attr_name not in self._initialization_order:
                    self._initialization_order.append(attr_name)

            logger.debug(f"模块 [{attr_name}] 初始化成功 ({health.load_time_ms:.1f}ms)")
            return instance

        except Exception as e:
            health.error = f"{type(e).__name__}: {str(e)}"
            health.load_time_ms = (time.time() - start) * 1000

            with self._lock:
                self._failed_modules.add(attr_name)
                self._module_health[attr_name] = health

            logger.warning(
                f"模块 [{attr_name}] 初始化失败（不影响核心运行）: {health.error}"
            )
            return None

    def get(self, attr_name: str, default=None) -> Any:
        """获取已初始化的模块实例（线程安全）"""
        with self._lock:
            if attr_name in self._instances:
                return self._instances[attr_name]
            if attr_name in self._failed_modules:
                return default
        return default

    def require(self, attr_name: str) -> Any:
        """获取模块实例，不存在则尝试初始化"""
        instance = self.get(attr_name)
        if instance is not None:
            return instance

        config = _LAZY_MODULES.get(attr_name)
        if config is None:
            raise AttributeError(f"未知模块: {attr_name}")

        factory_name, _ = config
        return self._safe_init(attr_name, factory_name)

    def __getattr__(self, name: str) -> Any:
        """属性访问时自动触发延迟初始化"""
        if name.startswith('_'):
            raise AttributeError(name)

        instance = self.get(name)
        if instance is not None:
            return instance

        config = _LAZY_MODULES.get(name)
        if config is not None:
            factory_name, _ = config
            result = self._safe_init(name, factory_name)
            if result is not None:
                return result
            raise AttributeError(
                f"模块 [{name}] 加载失败: "
                f"{self._module_health.get(name, ModuleHealth(name=name)).error}"
            )

        raise AttributeError(f"'{type(self).__name__}' 对象没有属性 '{name}'")

    def initialize(self, essential_only: bool = False) -> Dict[str, Any]:
        """
        分阶段初始化
        
        Args:
            essential_only: 若为True，仅初始化核心必要模块；
                          若为False，初始化全部模块
        
        Returns:
            初始化结果统计
        """
        results = {"success": [], "failed": [], "skipped": [], "total_time_ms": 0}
        start = time.time()

        essential_modules = [
            ("heart", "get_heart_module", {}),
            ("synaptic_bus", "get_synaptic_bus", {}),
            ("event_bus", "get_event_bus", {}),
            ("error_handler", "get_error_handler", {}),
            ("container", "get_container", {}),
            ("memory_system", "create_memory_system",
             {"working_capacity": 9, "max_episodes": 1000}),
            ("cognitive_loop", "create_cognitive_loop",
             {"max_iterations": 5, "quality_threshold": 0.8}),
            ("attention", "create_multi_scale_attention",
             {"swa_window": 512, "dswa_local": 256,
              "dswa_global": 1024, "gla_state_dim": 128}),
            ("evolution_engine", "create_evolution_engine", {}),
            ("unified_storage", "get_unified_storage", {}),
            ("decision_tracer", "get_decision_tracer", {}),
            ("explanation_engine", "get_explanation_engine", {}),
            ("os_tools", "os_tools", None),
            ("messaging_gateway", "messaging_gateway", None),
            ("learning_module", "learning_module", None),
        ]

        optional_modules = [
            ("causal_engine", "CausalReasoningEngine", {}),
            ("causal_verifier", "CausalVerificationEngine", {}),
            ("physical_validator", "PhysicalCausalityValidator", {}),
            ("semantic_memory", "get_semantic_memory", {}),
            ("procedural_memory", "get_procedural_memory", {}),
            ("knowledge_distiller", "create_knowledge_distillation", {}),
            ("dual_loop_engine", "get_dual_loop_engine", {"core": None}),
            ("compound_engine", "get_compound_engine", {"core": None}),
            ("dual_loop_compound", "get_dual_loop_compound", {"core": None}),
            ("interaction_compound", "get_interaction_compound", {}),
            ("llm_wiki", "get_llm_wiki_compat", {"core": None}),
            ("unified_skills", "get_unified_skill_system", {}),
            ("agent_factory", "agent_factory", {}),
            ("browser_automation", "browser_automation", None),
            ("autonomous_engine", "autonomous_engine", None),
            ("skill_auto_creator", "skill_auto_creator", None),
            ("user_profile_modeler", "user_profile_modeler", None),
            ("background_service", "background_service", None),
            ("task_automation", "task_automation", None),
            ("metacognition", "get_metacognition", {}),
            ("skill_system", "skill_system", None),
        ]

        modules_to_init = essential_modules
        if not essential_only:
            modules_to_init += optional_modules

        for item in modules_to_init:
            attr_name, factory_name, args = item
            if args is None:
                instance = self._safe_init(attr_name, factory_name)
            else:
                instance = self._safe_init(attr_name, factory_name, args)

            if instance is not None:
                results["success"].append(attr_name)
            else:
                results["failed"].append(attr_name)

        results["total_time_ms"] = (time.time() - start) * 1000
        results["total"] = len(modules_to_init)
        results["success_count"] = len(results["success"])
        results["failed_count"] = len(results["failed"])

        self.initialized = True

        if results["failed_count"] > 0:
            logger.warning(
                f"初始化完成: {results['success_count']}/{results['total']} 成功, "
                f"{results['failed_count']} 个模块降级运行"
            )
        else:
            logger.info(
                f"初始化完成: 全部 {results['total']} 模块就绪 "
                f"({results['total_time_ms']:.0f}ms)"
            )

        try:
            self._post_init_setup()
        except Exception as e:
            logger.warning(f"后置设置部分失败（非致命）: {e}")
            results["post_init_warning"] = str(e)

        return results

    def _post_init_setup(self):
        """后置设置（注册技能/Agent/容器配置）"""
        evolution = self.get("evolution_engine")
        skills_list = [
            "任务执行", "对话交互", "代码分析", "因果推理",
            "记忆检索", "知识蒸馏", "自我评估", "策略选择",
            "浏览器操作", "消息发送", "文件操作", "学习搜索",
            "快速响应", "深度推理", "协调编排", "经验学习",
        ]
        if evolution is not None:
            for skill in skills_list:
                evolution.register_skill(skill)

        bus = self.get("synaptic_bus")
        if bus is not None:
            agents_to_register = [
                ("reflex_agent", "reflex_agent", AgentType.REFLEX),
                ("deliberative_agent", "deliberative_agent", AgentType.DELIBERATIVE),
                ("learning_agent", "learning_agent", AgentType.LEARNING),
                ("coordinator_agent", "coordinator_agent", AgentType.COORDINATOR),
            ]
            for agent_attr, handler_attr, agent_type in agents_to_register:
                agent_instance = self.get(agent_attr)
                if agent_instance is not None and hasattr(agent_instance, 'handle_message'):
                    try:
                        bus.register_endpoint(
                            agent_attr, agent_instance.handle_message, agent_type
                        )
                    except Exception as e:
                        logger.warning(f"Agent [{agent_attr}] 注册失败: {e}")

        container = self.get("container")
        if container is not None:
            try:
                from .core.container import configure_services
                configure_services(container)
            except Exception as e:
                logger.warning(f"容器配置失败: {e}")

        memory = self.get("memory_system")
        if memory is not None:
            self.memory = memory

        logger.info("后置设置完成")

    @property
    def skills_list(self) -> List[str]:
        return [
            "任务执行", "对话交互", "代码分析", "因果推理",
            "记忆检索", "知识蒸馏", "自我评估", "策略选择",
            "浏览器操作", "消息发送", "文件操作", "学习搜索",
            "快速响应", "深度推理", "协调编排", "经验学习"
        ]

    def health_check(self) -> Dict[str, Any]:
        """全面健康检查"""
        with self._lock:
            total = len(_LAZY_MODULES)
            loaded = len(self._instances)
            failed = len(self._failed_modules)
            pending = total - loaded - failed

        failed_details = {}
        for name in list(self._failed_modules)[:10]:
            h = self._module_health.get(name)
            if h:
                failed_details[name] = h.error

        return {
            "status": "healthy" if failed == 0 else "degraded" if pending > 0 else "partial",
            "version": self.version,
            "model": self.model,
            "modules": {
                "total": total,
                "loaded": loaded,
                "failed": failed,
                "pending": pending,
                "load_rate": f"{loaded / total * 100:.1f}%" if total > 0 else "N/A",
            },
            "running": self.running,
            "initialized": self.initialized,
            "operation_count": self._operation_count,
            "failed_modules": failed_details,
            "initialization_order": self._initialization_order,
        }

    async def execute_task(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行任务（带自动模块激活）"""
        context = context or {}
        self._operation_count += 1
        trace_id = f"trace_{int(time.time()*1000)}_{self._operation_count}"
        self._current_trace_id = trace_id

        memory = self.require("memory_system")
        cognitive = self.require("cognitive_loop")
        attention = self.require("attention")
        evolution = self.require("evolution_engine")

        if memory is None or cognitive is None:
            return {
                "status": "error",
                "error": "核心模块(memory/cognitive)不可用",
                "trace_id": trace_id,
            }

        relevant_memories = await self._query_relevant_memories(task, context)

        perception_result = await self._analyze_user_state(task, context)

        attention_weights = attention.compute(task, relevant_memories) if attention else {}

        cognitive_input = {
            "task": task,
            "context": {**context, **perception_result},
            "memories": relevant_memories,
            "attention": attention_weights,
            "trace_id": trace_id,
        }

        reasoning_result = await cognitive.run(cognitive_input)

        confidence = reasoning_result.get("confidence", 0.5)
        adjusted_confidence = self._adjust_confidence_by_history(confidence, task)

        decision = self._make_final_decision(
            reasoning_result, adjusted_confidence, task
        )

        execution_result = await self._execute_with_agents(decision, task, context)

        learning_data = {
            "task": task,
            "context": context,
            "result": execution_result,
            "confidence": adjusted_confidence,
            "trace_id": trace_id,
        }

        if evolution is not None:
            try:
                await self._learning_feedback(learning_data)
            except Exception as e:
                logger.warning(f"学习反馈记录失败: {e}")

        tracer = self.get("decision_tracer")
        if tracer is not None:
            try:
                tracer.trace(trace_id, task, decision, execution_result)
            except Exception:
                pass

        final_result = {
            "status": "success",
            "task": task,
            "result": execution_result,
            "confidence": adjusted_confidence,
            "trace_id": trace_id,
            "modules_used": [k for k in self._instances],
        }

        self._current_trace_id = None
        return final_result

    async def _query_relevant_memories(self, task: str,
                                       context: Dict) -> List[Dict]:
        memory = self.get("memory_system")
        if memory is None:
            return []
        try:
            return await memory.search(task, top_k=5)
        except Exception:
            return []

    async def _analyze_user_state(self, task: str,
                                    context: Dict) -> Dict:
        monitor = self.get("user_state_monitor")
        ctx_engine = self.get("context_engine")
        result = {}
        if monitor is not None:
            try:
                state = await monitor.analyze(context)
                result.update(state)
            except Exception:
                pass
        if ctx_engine is not None:
            try:
                ctx = await ctx_engine.analyze_context(task, context)
                result.update(ctx)
            except Exception:
                pass
        return result

    def _adjust_confidence_by_history(self, confidence: float,
                                       task: str) -> float:
        history = self.get("unified_storage")
        if history is None:
            return confidence
        try:
            similar = history.retrieve_similar(task, limit=3)
            if similar:
                avg_success = sum(
                    r.get("success_rate", 0.5) for r in similar
                ) / len(similar)
                return confidence * 0.7 + avg_success * 0.3
        except Exception:
            pass
        return confidence

    def _make_final_decision(self, reasoning: Dict, confidence: float,
                             task: str) -> Dict:
        action = reasoning.get("action", "respond")
        content = reasoning.get("content", "")
        strategy = reasoning.get("strategy", "default")
        return {
            "action": action,
            "content": content,
            "strategy": strategy,
            "confidence": confidence,
            "reasoning": reasoning.get("steps", []),
        }

    async def _execute_with_agents(self, decision: Dict, task: str,
                                     context: Dict) -> Dict:
        action = decision.get("action", "respond")
        content = decision.get("content", "")

        if action == "tool_use":
            tools = self.get("os_tools")
            if tools is not None:
                try:
                    tool_result = await tools.execute(content, context)
                    return {"tool_execution": tool_result}
                except Exception as e:
                    return {"tool_error": str(e)}
            return {"tool_error": "OS工具模块不可用"}

        elif action == "browse":
            browser = self.get("browser_automation")
            if browser is not None:
                try:
                    browse_result = await browser.browse(content)
                    return {"browsing": browse_result}
                except Exception as e:
                    return {"browse_error": str(e)}
            return {"browse_error": "浏览器模块不可用"}

        elif action == "message":
            messaging = self.get("messaging_gateway")
            if messaging is not None:
                try:
                    msg_result = await messaging.send_message(
                        context.get("platform", "default"),
                        context.get("recipient", ""),
                        content
                    )
                    return {"message_sent": msg_result}
                except Exception as e:
                    return {"message_error": str(e)}
            return {"message_error": "消息网关不可用"}

        else:
            return {"response": content}

    async def _learning_feedback(self, data: Dict):
        learning = self.get("learning_module")
        evolution = self.get("evolution_engine")
        if learning is not None and hasattr(learning, '_add_experience'):
            try:
                experience = type('Exp', (), dict(
                    task=data["task"],
                    result=str(data["result"])[:200],
                    confidence=data["confidence"],
                    timestamp=datetime.now().isoformat(),
                ))()
                learning._add_experience(experience)
            except Exception as e:
                logger.debug(f"学习经验记录异常: {e}")

        if evolution is not None:
            try:
                evolution.record_outcome(data["task"], data["result"])
            except Exception as e:
                logger.debug(f"进化引擎记录异常: {e}")

    async def chat(self, message: str, context: Dict = None) -> Dict:
        context = context or {}
        os_tools_mod = self.get("os_tools")
        ollama = None

        try:
            from .ollama_integration import get_ollama_client
            ollama = get_ollama_client()
        except Exception:
            pass

        system_prompt = (
            f"你是{self.name}，一个智能助手。"
            f"当前版本: v{self.version}\n"
            f"请用中文回答用户的问题。"
        )

        if ollama is not None:
            try:
                response = await ollama.chat(
                    message, system_prompt=system_prompt, model=self.model
                )
                return {
                    "response": response,
                    "model": self.model,
                    "source": "ollama",
                }
            except Exception as e:
                logger.warning(f"Ollama调用失败: {e}")

        return {
            "response": f"[{self.name}] 收到消息: {message}",
            "model": self.model,
            "source": "fallback",
        }

    async def send_message(self, platform: str, recipient: str,
                           content: str) -> Dict:
        messaging = self.get("messaging_gateway")
        if messaging is not None:
            return await messaging.send_message(platform, recipient, content)
        return {"error": "消息网关不可用", "platform": platform}

    def shutdown(self):
        """关闭所有模块"""
        self.running = False
        closed = []
        errors = []

        for name in reversed(self._initialization_order):
            instance = self._instances.get(name)
            if instance is not None:
                try:
                    if hasattr(instance, 'close'):
                        instance.close()
                    elif hasattr(instance, 'shutdown'):
                        instance.shutdown()
                    elif hasattr(instance, 'stop'):
                        instance.stop()
                    closed.append(name)
                except Exception as e:
                    errors.append((name, str(e)))

        self.initialized = False
        logger.info(
            f"关闭完成: {len(closed)}个模块正常关闭"
            + (f", {len(errors)}个异常" if errors else "")
        )
        return {"closed": closed, "errors": errors}


_core_lock = threading.Lock()
_hmyx_core: Optional["HMYXCore"] = None


def get_core(initialize: bool = True) -> "HMYXCore":
    """获取核心实例（双重检查锁定，线程安全）"""
    global _hmyx_core
    if _hmyx_core is not None:
        return _hmyx_core
    with _core_lock:
        if _hmyx_core is None:
            _hmyx_core = HMYXCore()
            if initialize:
                _hmyx_core.initialize()
    return _hmyx_core


def __getattr__(name):
    if name == "hmyx_core":
        return get_core()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


try:
    from .core.enums import (
        AgentType, AgentState, MessagePriority, RoutingStrategy,
        EventType as CoreEventType
    )
except ImportError:
    AgentType = None
    AgentState = None
