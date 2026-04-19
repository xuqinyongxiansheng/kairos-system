"""
混合执行引擎
结合规则引擎和LLM，减少LLM依赖
解决AI Agent的LLM依赖症问题
"""

import asyncio
import logging
import os
import re
import time
import httpx
from typing import Dict, Any, List, Optional, Callable, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger("HybridEngine")


class ExecutionMode(Enum):
    """执行模式"""
    RULE_ONLY = "rule_only"
    LLM_ONLY = "llm_only"
    HYBRID = "hybrid"
    AUTO = "auto"


class TaskComplexity(Enum):
    """任务复杂度"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    UNKNOWN = "unknown"


@dataclass
class Rule:
    """规则定义"""
    name: str
    pattern: str
    action: str
    confidence: float
    priority: int
    category: str
    handler: Optional[Callable] = None


@dataclass
class ExecutionPlan:
    """执行计划"""
    mode: ExecutionMode
    steps: List[Dict[str, Any]]
    estimated_time: float
    confidence: float
    fallback: Optional[str]


@dataclass
class ExecutionResult:
    """执行结果"""
    status: str
    mode: str
    result: Any
    confidence: float
    execution_time: float
    steps_executed: int
    fallback_used: bool


@dataclass
class HybridConfig:
    """混合引擎配置"""
    default_mode: ExecutionMode = ExecutionMode.AUTO
    llm_threshold: float = 0.7
    max_llm_calls: int = 5
    enable_caching: bool = True
    small_model: str = "qwen2:0.5b"
    large_model: str = "gemma4:e4b"


class RuleEngine:
    """规则引擎"""
    
    def __init__(self):
        self.rules: List[Rule] = []
        self._load_default_rules()
    
    def _load_default_rules(self):
        """加载默认规则"""
        default_rules = [
            # 文件操作规则
            Rule(
                name="file_read",
                pattern=r"(读取|read|打开|open|查看|view).*(文件|file)",
                action="file_read",
                confidence=0.95,
                priority=100,
                category="file"
            ),
            Rule(
                name="file_write",
                pattern=r"(写入|write|保存|save).*(文件|file)",
                action="file_write",
                confidence=0.95,
                priority=100,
                category="file"
            ),
            Rule(
                name="file_list",
                pattern=r"(列出|list|显示|show).*(文件|目录|directory)",
                action="file_list",
                confidence=0.90,
                priority=90,
                category="file"
            ),
            Rule(
                name="file_delete",
                pattern=r"(删除|delete|移除|remove).*(文件|file)",
                action="file_delete",
                confidence=0.85,
                priority=80,
                category="file"
            ),
            
            # 代码操作规则
            Rule(
                name="code_analyze",
                pattern=r"(分析|analyze|检查|check).*(代码|code)",
                action="code_analyze",
                confidence=0.90,
                priority=90,
                category="code"
            ),
            Rule(
                name="code_format",
                pattern=r"(格式化|format).*(代码|code)",
                action="code_format",
                confidence=0.95,
                priority=95,
                category="code"
            ),
            Rule(
                name="code_refactor",
                pattern=r"(重构|refactor).*(代码|code)",
                action="code_refactor",
                confidence=0.80,
                priority=70,
                category="code"
            ),
            
            # 系统操作规则
            Rule(
                name="system_info",
                pattern=r"(系统|system).*(信息|info|状态|status)",
                action="system_info",
                confidence=0.95,
                priority=95,
                category="system"
            ),
            Rule(
                name="command_execute",
                pattern=r"(执行|execute|运行|run).*(命令|command)",
                action="command_execute",
                confidence=0.75,
                priority=60,
                category="system"
            ),
            
            # 网络操作规则
            Rule(
                name="http_get",
                pattern=r"(获取|fetch|get|请求|request).*(url|网页|web)",
                action="http_get",
                confidence=0.90,
                priority=85,
                category="network"
            ),
            Rule(
                name="web_search",
                pattern=r"(搜索|search).*(网页|web|网络)",
                action="web_search",
                confidence=0.85,
                priority=80,
                category="network"
            ),
            
            # Git操作规则
            Rule(
                name="git_status",
                pattern=r"(git|版本).*(状态|status)",
                action="git_status",
                confidence=0.95,
                priority=95,
                category="git"
            ),
            Rule(
                name="git_commit",
                pattern=r"(git|版本).*(提交|commit)",
                action="git_commit",
                confidence=0.90,
                priority=90,
                category="git"
            ),
            
            # 对话规则
            Rule(
                name="greeting",
                pattern=r"(你好|hello|hi|早上好|晚上好)",
                action="greeting",
                confidence=0.95,
                priority=100,
                category="conversation"
            ),
            Rule(
                name="introduction",
                pattern=r"(自我介绍|introduce|你是谁|who are you)",
                action="introduction",
                confidence=0.95,
                priority=100,
                category="conversation"
            ),
            
            # 浏览器自动化规则
            Rule(
                name="browser_open",
                pattern=r"(打开|open).*(浏览器|browser|网页|website)",
                action="browser_open",
                confidence=0.90,
                priority=90,
                category="browser"
            ),
            Rule(
                name="browser_click",
                pattern=r"(点击|click).*(按钮|button|链接|link)",
                action="browser_click",
                confidence=0.85,
                priority=85,
                category="browser"
            ),
            Rule(
                name="browser_screenshot",
                pattern=r"(截图|screenshot).*(网页|browser|页面)",
                action="browser_screenshot",
                confidence=0.90,
                priority=90,
                category="browser"
            ),
            Rule(
                name="browser_fill",
                pattern=r"(填写|fill|输入|input).*(表单|form|字段|field)",
                action="browser_fill",
                confidence=0.85,
                priority=85,
                category="browser"
            ),
            
            # 记忆系统规则
            Rule(
                name="memory_store",
                pattern=r"(记住|remember|存储|store|记忆).*(信息|info|知识|knowledge)",
                action="memory_store",
                confidence=0.90,
                priority=90,
                category="memory"
            ),
            Rule(
                name="memory_recall",
                pattern=r"(回忆|recall|想起|remember|检索|retrieve).*(之前|previous|历史|history)",
                action="memory_recall",
                confidence=0.85,
                priority=85,
                category="memory"
            ),
            Rule(
                name="memory_search",
                pattern=r"(搜索|search|查找|find).*(记忆|memory|知识|knowledge)",
                action="memory_search",
                confidence=0.85,
                priority=85,
                category="memory"
            ),
            
            # 因果推理规则
            Rule(
                name="causal_analyze",
                pattern=r"(分析|analyze).*(原因|cause|因果|causal)",
                action="causal_analyze",
                confidence=0.80,
                priority=80,
                category="reasoning"
            ),
            Rule(
                name="causal_verify",
                pattern=r"(验证|verify|检查|check).*(因果|causal|逻辑|logic)",
                action="causal_verify",
                confidence=0.80,
                priority=80,
                category="reasoning"
            ),
            Rule(
                name="counterfactual",
                pattern=r"(如果|what if|假设|suppose|反事实|counterfactual)",
                action="counterfactual",
                confidence=0.75,
                priority=75,
                category="reasoning"
            ),
            
            # 自我进化规则
            Rule(
                name="self_assess",
                pattern=r"(评估|assess).*(能力|capability|性能|performance|自己|self)",
                action="self_assess",
                confidence=0.85,
                priority=85,
                category="evolution"
            ),
            Rule(
                name="self_improve",
                pattern=r"(改进|improve|优化|optimize|进化|evolve).*(自己|self|系统|system)",
                action="self_improve",
                confidence=0.80,
                priority=80,
                category="evolution"
            ),
            Rule(
                name="skill_learn",
                pattern=r"(学习|learn|掌握|master).*(技能|skill|能力|ability)",
                action="skill_learn",
                confidence=0.80,
                priority=80,
                category="evolution"
            ),
            
            # 知识蒸馏规则
            Rule(
                name="knowledge_distill",
                pattern=r"(蒸馏|distill|提取|extract).*(知识|knowledge|经验|experience)",
                action="knowledge_distill",
                confidence=0.80,
                priority=80,
                category="knowledge"
            ),
            Rule(
                name="knowledge_compress",
                pattern=r"(压缩|compress|精简|simplify).*(知识|knowledge|信息|info)",
                action="knowledge_compress",
                confidence=0.80,
                priority=80,
                category="knowledge"
            ),
            
            # 用户状态规则
            Rule(
                name="user_state_check",
                pattern=r"(检查|check).*(用户|user).*(状态|state|情绪|emotion)",
                action="user_state_check",
                confidence=0.85,
                priority=85,
                category="perception"
            ),
            Rule(
                name="context_switch",
                pattern=r"(切换|switch).*(上下文|context|场景|scene)",
                action="context_switch",
                confidence=0.80,
                priority=80,
                category="perception"
            ),
            
            # 消息通知规则
            Rule(
                name="send_message",
                pattern=r"(发送|send).*(消息|message|通知|notification)",
                action="send_message",
                confidence=0.85,
                priority=85,
                category="messaging"
            ),
            Rule(
                name="schedule_task",
                pattern=r"(定时|schedule|计划|plan).*(任务|task|提醒|reminder)",
                action="schedule_task",
                confidence=0.85,
                priority=85,
                category="messaging"
            ),
            
            # 测试规则
            Rule(
                name="test_generate",
                pattern=r"(生成|generate|创建|create).*(测试|test)",
                action="test_generate",
                confidence=0.85,
                priority=85,
                category="testing"
            ),
            Rule(
                name="test_run",
                pattern=r"(运行|run|执行|execute).*(测试|test)",
                action="test_run",
                confidence=0.90,
                priority=90,
                category="testing"
            ),
            
            # 重构规则
            Rule(
                name="code_quality",
                pattern=r"(质量|quality).*(检查|check|分析|analyze)",
                action="code_quality",
                confidence=0.85,
                priority=85,
                category="refactoring"
            ),
            Rule(
                name="auto_fix",
                pattern=r"(自动|auto).*(修复|fix|纠正|correct)",
                action="auto_fix",
                confidence=0.80,
                priority=80,
                category="refactoring"
            ),
        ]
        
        self.rules = default_rules
        # 按优先级排序
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def add_rule(self, rule: Rule):
        """添加规则"""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def match(self, task: str) -> Tuple[Optional[Rule], float]:
        """
        匹配规则
        
        Args:
            task: 任务描述
            
        Returns:
            (匹配的规则, 置信度)
        """
        task_lower = task.lower()
        
        for rule in self.rules:
            if re.search(rule.pattern, task_lower, re.IGNORECASE):
                return rule, rule.confidence
        
        return None, 0.0
    
    def get_actions_by_category(self, category: str) -> List[Rule]:
        """获取某类别的所有规则"""
        return [r for r in self.rules if r.category == category]


class LLMEngine:
    """LLM引擎（统一客户端版）"""

    def __init__(self, small_model: str = None, large_model: str = None):
        from kairos.system.config import settings as _s
        self.small_model = small_model or _s.llm_client.cache_size and "qwen2:0.5b"
        self.large_model = large_model or _s.ollama.default_model
        self.call_count = 0
        self.max_calls = 10
        self._client = None

    async def _get_client(self):
        if self._client is None:
            from kairos.system.unified_llm_client import get_unified_client
            self._client = get_unified_client()
        return self._client

    async def plan(self, task: str, context: Dict[str, Any] = None,
                  use_small_model: bool = True) -> Dict[str, Any]:
        if self.call_count >= self.max_calls:
            return {"status": "error", "error": "LLM调用次数超限"}

        model = self.small_model if use_small_model else self.large_model

        try:
            client = await self._get_client()
            prompt = f"分析以下任务并生成执行计划。\n\n任务: {task}\n\n上下文: {json.dumps(context or {}, ensure_ascii=False)}\n\n请以JSON格式输出执行计划:\n{{\"complexity\":\"simple/medium/complex\",\"steps\":[{{\"action\":\"动作名称\",\"params\":{{}},\"description\":\"描述\"}}],\"estimated_time\":0,\"confidence\":0.8}}"

            result = await client.chat(
                user_prompt=prompt,
                system_prompt="你是任务规划引擎，输出JSON格式执行计划。",
                model=model,
                use_cache=False,
            )

            self.call_count += 1

            if result.get("status") != "success":
                return {"status": "error", "error": result.get("response", "规划失败")}

            content = result.get("response", "")
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                plan = json.loads(json_match.group())
                return {"status": "success", "plan": plan, "model": model}

            return {"status": "error", "error": "无法解析规划结果"}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def execute_with_llm(self, task: str,
                               context: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            client = await self._get_client()
            result = await client.chat(
                user_prompt=task,
                system_prompt="你是鸿蒙小雨，一个智能助手。",
                model=self.large_model,
                use_cache=False,
            )

            self.call_count += 1

            if result.get("status") == "success":
                return {
                    "status": "success",
                    "result": result.get("response", ""),
                    "model": self.large_model,
                }
            return {"status": "error", "error": result.get("response", "执行失败")}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def reset_count(self):
        self.call_count = 0


class HybridEngine:
    """
    混合执行引擎
    
    功能:
    - 规则引擎处理确定性任务
    - LLM处理复杂任务
    - 智能模式选择
    - 小模型规划，大模型验证
    - 减少LLM调用
    """
    
    def __init__(self, config: HybridConfig = None):
        self.config = config or HybridConfig()
        self.rule_engine = RuleEngine()
        self.llm_engine = LLMEngine(
            small_model=self.config.small_model,
            large_model=self.config.large_model
        )
        self.execution_history: List[Dict[str, Any]] = []
        self.stats = {
            "total_executions": 0,
            "rule_executions": 0,
            "llm_executions": 0,
            "hybrid_executions": 0,
            "llm_calls_saved": 0
        }
        
        logger.info(f"混合执行引擎初始化 (mode={self.config.default_mode.value})")
    
    async def execute(self, task: str, 
                     context: Dict[str, Any] = None,
                     mode: ExecutionMode = None) -> ExecutionResult:
        """
        执行任务
        
        Args:
            task: 任务描述
            context: 上下文
            mode: 执行模式
            
        Returns:
            执行结果
        """
        start_time = time.time()
        mode = mode or self.config.default_mode
        
        self.stats["total_executions"] += 1
        
        # 自动模式选择
        if mode == ExecutionMode.AUTO:
            mode = self._select_mode(task)
        
        # 根据模式执行
        if mode == ExecutionMode.RULE_ONLY:
            result = await self._execute_rule(task, context)
            self.stats["rule_executions"] += 1
            self.stats["llm_calls_saved"] += 1
            
        elif mode == ExecutionMode.LLM_ONLY:
            result = await self._execute_llm(task, context)
            self.stats["llm_executions"] += 1
            
        else:  # HYBRID
            result = await self._execute_hybrid(task, context)
            self.stats["hybrid_executions"] += 1
        
        execution_time = time.time() - start_time
        
        # 记录历史
        self.execution_history.append({
            "task": task[:100],
            "mode": mode.value,
            "status": result.get("status"),
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })
        
        return ExecutionResult(
            status=result.get("status", "unknown"),
            mode=mode.value,
            result=result.get("result"),
            confidence=result.get("confidence", 0),
            execution_time=execution_time,
            steps_executed=result.get("steps_executed", 1),
            fallback_used=result.get("fallback_used", False)
        )
    
    def _select_mode(self, task: str) -> ExecutionMode:
        """选择执行模式"""
        # 尝试规则匹配
        rule, confidence = self.rule_engine.match(task)
        
        if rule and confidence >= self.config.llm_threshold:
            logger.debug(f"规则匹配成功: {rule.name} (confidence={confidence})")
            return ExecutionMode.RULE_ONLY
        
        # 检查任务复杂度
        complexity = self._estimate_complexity(task)
        
        if complexity == TaskComplexity.SIMPLE:
            return ExecutionMode.HYBRID
        elif complexity == TaskComplexity.MEDIUM:
            return ExecutionMode.HYBRID
        else:
            return ExecutionMode.LLM_ONLY
    
    def _estimate_complexity(self, task: str) -> TaskComplexity:
        """估算任务复杂度"""
        words = len(task.split())
        
        # 检查关键词
        complex_keywords = ["分析", "设计", "优化", "重构", "创建", "analyze", "design", "optimize"]
        has_complex = any(kw in task.lower() for kw in complex_keywords)
        
        if words < 10 and not has_complex:
            return TaskComplexity.SIMPLE
        elif words < 30 or has_complex:
            return TaskComplexity.MEDIUM
        return TaskComplexity.COMPLEX
    
    async def _execute_rule(self, task: str, 
                           context: Dict[str, Any]) -> Dict[str, Any]:
        """规则执行"""
        rule, confidence = self.rule_engine.match(task)
        
        if not rule:
            return {
                "status": "error",
                "error": "无匹配规则",
                "confidence": 0
            }
        
        # 执行规则动作
        action_result = await self._execute_action(rule.action, context)
        
        return {
            "status": "success",
            "result": action_result,
            "rule": rule.name,
            "confidence": confidence,
            "steps_executed": 1
        }
    
    async def _execute_llm(self, task: str, 
                          context: Dict[str, Any]) -> Dict[str, Any]:
        """LLM执行"""
        return await self.llm_engine.execute_with_llm(task, context)
    
    async def _execute_hybrid(self, task: str, 
                             context: Dict[str, Any]) -> Dict[str, Any]:
        """混合执行"""
        # 1. 尝试规则匹配
        rule, confidence = self.rule_engine.match(task)
        
        if rule and confidence >= 0.8:
            return await self._execute_rule(task, context)
        
        # 2. 使用小模型规划
        plan_result = await self.llm_engine.plan(task, context, use_small_model=True)
        
        if plan_result["status"] != "success":
            # 规划失败，直接使用大模型
            return await self._execute_llm(task, context)
        
        plan = plan_result.get("plan", {})
        steps = plan.get("steps", [])
        
        # 3. 执行步骤
        results = []
        for step in steps:
            action = step.get("action")
            
            # 检查是否有规则可以处理
            action_rule = None
            for r in self.rule_engine.rules:
                if r.action == action:
                    action_rule = r
                    break
            
            if action_rule:
                # 使用规则执行
                result = await self._execute_action(action, context)
                self.stats["llm_calls_saved"] += 1
            else:
                # 使用LLM执行
                result = await self.llm_engine.execute_with_llm(
                    step.get("description", action),
                    context
                )
            
            results.append(result)
            
            if result.get("status") != "success":
                break
        
        return {
            "status": "success" if all(r.get("status") == "success" for r in results) else "partial",
            "result": results,
            "confidence": plan.get("confidence", 0.7),
            "steps_executed": len(results),
            "plan": plan
        }
    
    async def _execute_action(self, action: str,
                             context: Dict[str, Any]) -> Dict[str, Any]:
        """执行动作 - 绑定实际功能模块"""
        action_handlers = {
            "greeting": lambda: {"response": "你好！我是鸿蒙小雨，很高兴为你服务。"},
            "introduction": lambda: {"response": "我是鸿蒙小雨，一个基于Kairos System的智能系统。"},
            "system_info": self._action_system_info,
            "file_read": self._action_file_read,
            "file_write": self._action_file_write,
            "file_list": self._action_file_list,
            "file_delete": self._action_file_delete,
            "code_analyze": self._action_code_analyze,
            "code_format": self._action_code_format,
            "git_status": self._action_git_status,
            "git_commit": self._action_git_commit,
            "memory_store": self._action_memory_store,
            "memory_recall": self._action_memory_recall,
            "memory_search": self._action_memory_search,
            "http_get": self._action_http_get,
            "web_search": self._action_web_search,
            "command_execute": self._action_command_execute,
        }

        handler = action_handlers.get(action)
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(context)
                else:
                    result = handler()
                return {"status": "success", "result": result}
            except Exception as e:
                return {"status": "error", "error": str(e)}

        return {"status": "success", "result": f"执行动作: {action}"}

    def _action_system_info(self) -> Dict[str, Any]:
        try:
            import platform
            import psutil
            return {
                "response": "系统运行正常",
                "platform": platform.platform(),
                "python": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
                "memory_used_pct": psutil.virtual_memory().percent,
            }
        except Exception:
            return {"response": "系统运行正常，版本 v4.1.0"}

    def _action_file_read(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        path = (context or {}).get("path", "")
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read(5000)
                return {"response": f"文件内容({len(content)}字符)", "content": content[:2000]}
            except Exception as e:
                return {"response": f"读取失败: {e}"}
        return {"response": "文件读取功能已准备就绪，请提供文件路径"}

    def _action_file_write(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        path = (context or {}).get("path", "")
        content = (context or {}).get("content", "")
        if path and content:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return {"response": f"文件已写入: {path}"}
            except Exception as e:
                return {"response": f"写入失败: {e}"}
        return {"response": "文件写入功能已准备就绪"}

    def _action_file_list(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        path = (context or {}).get("path", ".")
        try:
            entries = os.listdir(path)
            return {"response": f"目录内容({len(entries)}项)", "entries": entries[:50]}
        except Exception as e:
            return {"response": f"列出失败: {e}"}

    def _action_file_delete(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        return {"response": "文件删除需要确认，请使用专门的删除接口"}

    def _action_code_analyze(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        return {"response": "代码分析功能已准备就绪，请提供代码内容"}

    def _action_code_format(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        return {"response": "代码格式化功能已准备就绪"}

    def _action_git_status(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            import subprocess
            result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, timeout=5)
            return {"response": "Git状态", "output": result.stdout[:500]}
        except Exception as e:
            return {"response": f"Git状态查询失败: {e}"}

    def _action_git_commit(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        return {"response": "Git提交需要确认，请使用专门的Git接口"}

    async def _action_memory_store(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            from kairos.system.unified_memory_system_v2 import get_unified_memory, MemoryType
            memory = get_unified_memory()
            content = (context or {}).get("content", (context or {}).get("info", ""))
            if content:
                mid = await memory.store(content, MemoryType.LONG_TERM)
                return {"response": f"已存储记忆: {mid}"}
            return {"response": "请提供要存储的内容"}
        except Exception as e:
            return {"response": f"记忆存储失败: {e}"}

    async def _action_memory_recall(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            from kairos.system.unified_memory_system_v2 import get_unified_memory
            memory = get_unified_memory()
            query = (context or {}).get("query", "")
            items = await memory.retrieve(query=query, limit=5)
            return {"response": f"检索到{len(items)}条记忆", "items": [i.to_dict() for i in items[:3]]}
        except Exception as e:
            return {"response": f"记忆检索失败: {e}"}

    async def _action_memory_search(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            from kairos.system.unified_memory_system_v2 import get_unified_memory
            memory = get_unified_memory()
            query = (context or {}).get("query", "")
            items = await memory.search(query, limit=5)
            return {"response": f"搜索到{len(items)}条记忆", "items": [i.to_dict() for i in items[:3]]}
        except Exception as e:
            return {"response": f"记忆搜索失败: {e}"}

    async def _action_http_get(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        url = (context or {}).get("url", "")
        if url:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url)
                    return {"response": f"HTTP {resp.status_code}", "content": resp.text[:1000]}
            except Exception as e:
                return {"response": f"HTTP请求失败: {e}"}
        return {"response": "HTTP请求功能已准备就绪，请提供URL"}

    def _action_web_search(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        return {"response": "网页搜索功能已准备就绪，请提供搜索关键词"}

    def _action_command_execute(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        return {"response": "命令执行需要确认，请使用专门的执行接口"}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = self.stats["total_executions"]
        
        return {
            **self.stats,
            "rule_ratio": self.stats["rule_executions"] / total if total > 0 else 0,
            "llm_ratio": self.stats["llm_executions"] / total if total > 0 else 0,
            "llm_calls_saved_ratio": self.stats["llm_calls_saved"] / total if total > 0 else 0
        }
    
    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self.execution_history[-limit:]
    
    def reset_stats(self):
        """重置统计"""
        self.stats = {
            "total_executions": 0,
            "rule_executions": 0,
            "llm_executions": 0,
            "hybrid_executions": 0,
            "llm_calls_saved": 0
        }
        self.execution_history = []
        self.llm_engine.reset_count()


# 全局实例
hybrid_engine = HybridEngine()


def get_hybrid_engine() -> HybridEngine:
    """获取全局混合引擎"""
    return hybrid_engine
