"""
Agent任务流适配器
将Agent请求路由到六层认知流程
实现Agent层与六层认知架构的深度集成
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import os
import sys

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger("AgentTaskFlow")


class FlowPhase(Enum):
    """流程阶段"""
    INIT = "init"
    PERCEPTION = "perception"
    INTEGRATION = "integration"
    DECISION = "decision"
    EXECUTION = "execution"
    EVALUATION = "evaluation"
    FEEDBACK = "feedback"
    COMPLETED = "completed"
    FAILED = "failed"


class FlowStatus(Enum):
    """流程状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class LayerResult:
    """层处理结果"""
    layer_name: str
    status: str
    data: Dict[str, Any]
    insights: List[str]
    timestamp: str
    duration_ms: float


@dataclass
class FlowContext:
    """流程上下文"""
    flow_id: str
    task: str
    source_agent: str
    current_phase: FlowPhase
    status: FlowStatus
    layer_results: Dict[str, LayerResult]
    context_data: Dict[str, Any]
    created_at: str
    updated_at: str
    iterations: int
    max_iterations: int


class BaseLayer:
    """基础层"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"Layer.{name}")
    
    async def process(self, context: FlowContext) -> LayerResult:
        """处理"""
        raise NotImplementedError


class PerceptionLayer(BaseLayer):
    """感知层 - 接收和理解输入"""
    
    def __init__(self):
        super().__init__("perception")
    
    async def process(self, context: FlowContext) -> LayerResult:
        start_time = datetime.now()
        
        # 分析任务
        task = context.task
        insights = []
        
        # 提取关键信息
        keywords = self._extract_keywords(task)
        entities = self._extract_entities(task)
        intent = self._detect_intent(task)
        
        insights.append(f"检测到关键词: {', '.join(keywords[:5])}")
        insights.append(f"意图识别: {intent}")
        
        result_data = {
            "keywords": keywords,
            "entities": entities,
            "intent": intent,
            "complexity": self._estimate_complexity(task)
        }
        
        duration = (datetime.now() - start_time).total_seconds() * 1000
        
        return LayerResult(
            layer_name=self.name,
            status="success",
            data=result_data,
            insights=insights,
            timestamp=datetime.now().isoformat(),
            duration_ms=duration
        )
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        import re
        words = re.findall(r'\b\w+\b', text.lower())
        stopwords = {'的', '是', '在', '和', '了', '有', '不', '我', '他', '她'}
        return [w for w in words if w not in stopwords and len(w) > 1]
    
    def _extract_entities(self, text: str) -> List[str]:
        """提取实体"""
        import re
        # 简单的实体识别
        entities = []
        # 文件路径
        entities.extend(re.findall(r'[a-zA-Z0-9_/.-]+\.[a-zA-Z]+', text))
        # 函数名
        entities.extend(re.findall(r'\b[a-z_][a-z0-9_]*\(\)', text))
        return entities
    
    def _detect_intent(self, text: str) -> str:
        """检测意图"""
        text_lower = text.lower()
        
        if any(w in text_lower for w in ['读取', 'read', '打开', 'open']):
            return "read"
        elif any(w in text_lower for w in ['写入', 'write', '保存', 'save']):
            return "write"
        elif any(w in text_lower for w in ['执行', 'execute', '运行', 'run']):
            return "execute"
        elif any(w in text_lower for w in ['分析', 'analyze', '检查', 'check']):
            return "analyze"
        elif any(w in text_lower for w in ['创建', 'create', '新建', 'new']):
            return "create"
        elif any(w in text_lower for w in ['删除', 'delete', '移除', 'remove']):
            return "delete"
        
        return "unknown"
    
    def _estimate_complexity(self, text: str) -> str:
        """估算复杂度"""
        words = len(text.split())
        if words < 10:
            return "low"
        elif words < 30:
            return "medium"
        return "high"


class IntegrationLayer(BaseLayer):
    """汇知层 - 整合知识"""
    
    def __init__(self):
        super().__init__("integration")
    
    async def process(self, context: FlowContext) -> LayerResult:
        start_time = datetime.now()
        
        perception_result = context.layer_results.get("perception")
        insights = []
        
        # 整合感知结果
        related_knowledge = []
        
        if perception_result:
            keywords = perception_result.data.get("keywords", [])
            intent = perception_result.data.get("intent", "")
            
            insights.append(f"整合关键词知识: {len(keywords)} 个")
            insights.append(f"意图相关上下文: {intent}")
            
            related_knowledge = self._retrieve_knowledge(keywords, intent)
        
        result_data = {
            "related_knowledge": related_knowledge,
            "context_relevance": self._calculate_relevance(perception_result)
        }
        
        duration = (datetime.now() - start_time).total_seconds() * 1000
        
        return LayerResult(
            layer_name=self.name,
            status="success",
            data=result_data,
            insights=insights,
            timestamp=datetime.now().isoformat(),
            duration_ms=duration
        )
    
    def _retrieve_knowledge(self, keywords: List[str], intent: str) -> List[Dict[str, Any]]:
        """检索相关知识"""
        # 简化实现
        knowledge = []
        for kw in keywords[:3]:
            knowledge.append({
                "keyword": kw,
                "relevance": 0.8,
                "source": "memory"
            })
        return knowledge
    
    def _calculate_relevance(self, perception_result: LayerResult) -> float:
        """计算相关性"""
        if not perception_result:
            return 0.0
        return 0.75


class DecisionLayer(BaseLayer):
    """命策层 - 制定决策"""
    
    def __init__(self):
        super().__init__("decision")
    
    async def process(self, context: FlowContext) -> LayerResult:
        start_time = datetime.now()
        
        insights = []
        
        # 获取前两层结果
        perception = context.layer_results.get("perception")
        integration = context.layer_results.get("integration")
        
        # 制定执行计划
        plan = self._create_plan(perception, integration, context.task)
        
        insights.append(f"生成执行计划: {len(plan.get('steps', []))} 步")
        insights.append(f"选择策略: {plan.get('strategy', 'default')}")
        
        result_data = {
            "plan": plan,
            "strategy": plan.get("strategy", "default"),
            "estimated_steps": len(plan.get("steps", []))
        }
        
        duration = (datetime.now() - start_time).total_seconds() * 1000
        
        return LayerResult(
            layer_name=self.name,
            status="success",
            data=result_data,
            insights=insights,
            timestamp=datetime.now().isoformat(),
            duration_ms=duration
        )
    
    def _create_plan(self, perception: LayerResult, integration: LayerResult,
                    task: str) -> Dict[str, Any]:
        """创建执行计划"""
        steps = []
        
        if perception:
            intent = perception.data.get("intent", "unknown")
            
            # 根据意图生成步骤
            if intent == "read":
                steps = [
                    {"action": "file_read", "description": "读取文件"},
                    {"action": "content_parse", "description": "解析内容"},
                    {"action": "result_return", "description": "返回结果"}
                ]
            elif intent == "write":
                steps = [
                    {"action": "prepare_content", "description": "准备内容"},
                    {"action": "file_write", "description": "写入文件"},
                    {"action": "verify_write", "description": "验证写入"}
                ]
            elif intent == "execute":
                steps = [
                    {"action": "validate_input", "description": "验证输入"},
                    {"action": "execute_command", "description": "执行命令"},
                    {"action": "capture_output", "description": "捕获输出"}
                ]
            else:
                steps = [
                    {"action": "analyze_task", "description": "分析任务"},
                    {"action": "execute_generic", "description": "执行通用操作"}
                ]
        
        return {
            "steps": steps,
            "strategy": "sequential",
            "fallback": "ask_user"
        }


class ExecutionLayer(BaseLayer):
    """行成层 - 执行操作"""
    
    def __init__(self):
        super().__init__("execution")
    
    async def process(self, context: FlowContext) -> LayerResult:
        start_time = datetime.now()
        
        insights = []
        
        # 获取决策结果
        decision = context.layer_results.get("decision")
        
        execution_results = []
        
        if decision:
            plan = decision.data.get("plan", {})
            steps = plan.get("steps", [])
            
            for i, step in enumerate(steps):
                result = await self._execute_step(step, context)
                execution_results.append(result)
                insights.append(f"步骤 {i+1}: {step.get('description', 'unknown')} - {result.get('status', 'unknown')}")
                
                if result.get("status") == "failed":
                    break
        
        result_data = {
            "execution_results": execution_results,
            "steps_completed": len([r for r in execution_results if r.get("status") == "success"]),
            "steps_total": len(execution_results)
        }
        
        duration = (datetime.now() - start_time).total_seconds() * 1000
        
        return LayerResult(
            layer_name=self.name,
            status="success",
            data=result_data,
            insights=insights,
            timestamp=datetime.now().isoformat(),
            duration_ms=duration
        )
    
    async def _execute_step(self, step: Dict[str, Any], 
                           context: FlowContext) -> Dict[str, Any]:
        """执行步骤"""
        action = step.get("action", "")
        
        # 模拟执行
        await asyncio.sleep(0.1)
        
        return {
            "action": action,
            "status": "success",
            "result": f"执行 {action} 完成"
        }


class EvaluationLayer(BaseLayer):
    """衡质层 - 评估质量"""
    
    def __init__(self):
        super().__init__("evaluation")
    
    async def process(self, context: FlowContext) -> LayerResult:
        start_time = datetime.now()
        
        insights = []
        
        # 获取执行结果
        execution = context.layer_results.get("execution")
        
        quality_score = 0.0
        issues = []
        
        if execution:
            results = execution.data.get("execution_results", [])
            success_count = sum(1 for r in results if r.get("status") == "success")
            total_count = len(results)
            
            quality_score = success_count / total_count if total_count > 0 else 0
            
            insights.append(f"执行成功率: {quality_score:.1%}")
            
            if quality_score < 1.0:
                issues.append("部分步骤执行失败")
                insights.append("需要反馈修正")
        
        result_data = {
            "quality_score": quality_score,
            "issues": issues,
            "needs_feedback": quality_score < 0.8
        }
        
        duration = (datetime.now() - start_time).total_seconds() * 1000
        
        return LayerResult(
            layer_name=self.name,
            status="success",
            data=result_data,
            insights=insights,
            timestamp=datetime.now().isoformat(),
            duration_ms=duration
        )


class FeedbackLayer(BaseLayer):
    """回衡层 - 反馈修正"""
    
    def __init__(self):
        super().__init__("feedback")
    
    async def process(self, context: FlowContext) -> LayerResult:
        start_time = datetime.now()
        
        insights = []
        
        # 获取评估结果
        evaluation = context.layer_results.get("evaluation")
        
        corrections = []
        
        if evaluation and evaluation.data.get("needs_feedback"):
            issues = evaluation.data.get("issues", [])
            
            for issue in issues:
                correction = self._generate_correction(issue, context)
                corrections.append(correction)
                insights.append(f"修正建议: {correction.get('description', '')}")
        
        result_data = {
            "corrections": corrections,
            "feedback_applied": len(corrections) > 0
        }
        
        duration = (datetime.now() - start_time).total_seconds() * 1000
        
        return LayerResult(
            layer_name=self.name,
            status="success",
            data=result_data,
            insights=insights,
            timestamp=datetime.now().isoformat(),
            duration_ms=duration
        )
    
    def _generate_correction(self, issue: str, 
                            context: FlowContext) -> Dict[str, Any]:
        """生成修正"""
        return {
            "issue": issue,
            "description": f"针对 '{issue}' 的修正建议",
            "action": "retry_with_adjustment"
        }


class AgentTaskFlow:
    """
    Agent任务流适配器
    
    功能:
    - 将Agent请求路由到六层认知流程
    - 管理流程状态和上下文
    - 支持回溯和重试
    - 提供流程监控
    """
    
    def __init__(self, max_iterations: int = 3):
        self.layers = {
            "perception": PerceptionLayer(),
            "integration": IntegrationLayer(),
            "decision": DecisionLayer(),
            "execution": ExecutionLayer(),
            "evaluation": EvaluationLayer(),
            "feedback": FeedbackLayer()
        }
        
        self.layer_order = [
            "perception", "integration", "decision",
            "execution", "evaluation", "feedback"
        ]
        
        self.max_iterations = max_iterations
        self.active_flows: Dict[str, FlowContext] = {}
        self.flow_history: List[Dict[str, Any]] = []
        
        logger.info("Agent任务流适配器初始化")
    
    async def process(self, task: str, 
                     source_agent: str = "unknown",
                     context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        通过六层流程处理任务
        
        Args:
            task: 任务描述
            source_agent: 来源Agent
            context_data: 上下文数据
            
        Returns:
            处理结果
        """
        flow_id = f"flow_{int(datetime.now().timestamp() * 1000)}"
        
        flow_context = FlowContext(
            flow_id=flow_id,
            task=task,
            source_agent=source_agent,
            current_phase=FlowPhase.INIT,
            status=FlowStatus.RUNNING,
            layer_results={},
            context_data=context_data or {},
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            iterations=0,
            max_iterations=self.max_iterations
        )
        
        self.active_flows[flow_id] = flow_context
        
        logger.info(f"开始处理任务: {flow_id} - {task[:50]}...")
        
        try:
            # 依次通过六层
            for layer_name in self.layer_order:
                layer = self.layers[layer_name]
                
                flow_context.current_phase = FlowPhase[layer_name.upper()]
                flow_context.updated_at = datetime.now().isoformat()
                
                result = await layer.process(flow_context)
                flow_context.layer_results[layer_name] = result
                
                # 检查是否需要反馈修正
                if layer_name == "evaluation" and result.data.get("needs_feedback"):
                    feedback_result = await self.layers["feedback"].process(flow_context)
                    flow_context.layer_results["feedback"] = feedback_result
                    
                    # 如果需要重试
                    if flow_context.iterations < flow_context.max_iterations:
                        flow_context.iterations += 1
                        # 可以选择重新执行某些层
            
            flow_context.current_phase = FlowPhase.COMPLETED
            flow_context.status = FlowStatus.COMPLETED
            flow_context.updated_at = datetime.now().isoformat()
            
            # 构建结果
            result = self._build_result(flow_context)
            
            # 记录历史
            self.flow_history.append({
                "flow_id": flow_id,
                "task": task,
                "status": "completed",
                "iterations": flow_context.iterations,
                "timestamp": datetime.now().isoformat()
            })
            
            return result
            
        except Exception as e:
            flow_context.status = FlowStatus.FAILED
            flow_context.current_phase = FlowPhase.FAILED
            
            logger.error(f"任务处理失败: {e}")
            
            return {
                "status": "error",
                "error": str(e),
                "flow_id": flow_id
            }
    
    def _build_result(self, context: FlowContext) -> Dict[str, Any]:
        """构建结果"""
        execution = context.layer_results.get("execution")
        evaluation = context.layer_results.get("evaluation")
        
        return {
            "status": "success",
            "flow_id": context.flow_id,
            "task": context.task,
            "source_agent": context.source_agent,
            "iterations": context.iterations,
            "quality_score": evaluation.data.get("quality_score", 0) if evaluation else 0,
            "execution_results": execution.data if execution else {},
            "layer_insights": {
                name: result.insights
                for name, result in context.layer_results.items()
            },
            "completed_at": datetime.now().isoformat()
        }
    
    def get_flow_status(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """获取流程状态"""
        if flow_id in self.active_flows:
            ctx = self.active_flows[flow_id]
            return {
                "flow_id": ctx.flow_id,
                "status": ctx.status.value,
                "current_phase": ctx.current_phase.value,
                "iterations": ctx.iterations
            }
        return None
    
    def get_flow_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取流程历史"""
        return self.flow_history[-limit:]


# 全局实例
agent_task_flow = AgentTaskFlow()


def get_agent_task_flow() -> AgentTaskFlow:
    """获取全局任务流适配器"""
    return agent_task_flow
