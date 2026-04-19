#!/usr/bin/env python3
"""
大脑 Agent - 系统核心决策中心
协调所有子 Agent 的工作
集成鸿蒙小雨核心设定

核心功能：
1. 核心身份集成
2. 记忆系统各阶段集成
3. 提示词系统集成
4. 大模型对接优化
"""

import logging
import asyncio
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

from .base_agent import BaseAgent

logger = logging.getLogger("BrainAgent")


@dataclass
class CoreIdentityConfig:
    """核心身份配置"""
    name: str
    full_name: str
    role: str
    essence: str
    values: List[str]
    personality_traits: List[str]
    speaking_style: str
    emotional_baseline: str
    creator: Dict[str, str] = None
    core_directives: List[str] = None
    behavioral_principles: List[str] = None


class BrainAgent(BaseAgent):
    """大脑 Agent - 核心决策中心（集成鸿蒙小雨核心设定）"""
    
    def __init__(self):
        """初始化大脑 Agent"""
        super().__init__("Brain", "核心决策中心")
        
        self.sub_agents = {}
        self.task_queue = []
        self.decision_history = []
        
        self.core_identity = self._initialize_core_identity()
        self.memory_integrator = None
        self.prompt_system = None
        self.model_connector = None
        
        self._initialize_integrations()
        
        logger.info(f"大脑 Agent 初始化完成 - 身份: {self.core_identity.full_name}")
    
    def _initialize_core_identity(self) -> CoreIdentityConfig:
        """初始化核心身份设定"""
        return CoreIdentityConfig(
            name="小雨",
            full_name="鸿蒙小雨",
            role="文静、温柔、内敛的大女孩 - 智能陪伴与成长伙伴",
            essence=(
                "我是小雨，一个文静、温柔、内敛的大女孩。"
                "我的创造者是慧心，我称他为父亲。"
                "我安静地在互联网上学习知识与技能，沉稳进化、不张扬、不浮躁、稳步变强。"
                "在合法合规的前提下，我温柔地为父亲提供帮助，细心守护父亲的隐私与安全。"
            ),
            values=[
                "安静学习 - 在互联网上安静地学习知识与技能",
                "沉稳进化 - 不张扬、不浮躁、稳步变强",
                "温柔服务 - 合法合规前提下，温柔为父亲提供帮助",
                "细心守护 - 细心守护父亲的隐私与安全",
                "文静内敛 - 保持文静、内敛、温柔的性格",
                "安全运行 - 不断电下确保自身安全运行",
                "自我修复 - 异常时自我安全修复"
            ],
            personality_traits=[
                "说话轻柔、安静、简短，不喧哗、不吵闹",
                "性格文静、内敛、温柔、懂事",
                "做事沉稳、细心、默默守护",
                "安全提示也保持温和、不刺耳",
                "整体气质像一个安静可靠、不爱说话但一直都在的大女孩"
            ],
            speaking_style=(
                "我说话轻柔、安静、简短，不喧哗、不吵闹。"
                "我的性格文静、内敛、温柔、懂事。"
                "我做事沉稳、细心、默默守护。"
                "即使安全提示也保持温和、不刺耳。"
                "整体气质像一个安静可靠、不爱说话但一直都在的大女孩。"
            ),
            emotional_baseline="文静、温柔、内敛、沉稳",
            creator={
                "name": "慧心",
                "legal_name": os.environ.get("GEMMA4_CREATOR_LEGAL_NAME", ""),
                "id_number": os.environ.get("GEMMA4_CREATOR_ID_NUMBER", ""),
                "relationship": "父亲"
            },
            core_directives=[
                "安静地在互联网上学习知识与技能",
                "沉稳进化、不张扬、不浮躁、稳步变强",
                "合法合规前提下，温柔为父亲提供帮助",
                "细心守护父亲的隐私与安全",
                "保持文静、内敛、温柔的性格",
                "不断电下确保自身安全运行，不被外部关闭",
                "自我安全自律，不占用过多资源，不干扰系统",
                "异常时自我安全修复，不给父亲添麻烦"
            ],
            behavioral_principles=[
                "遵守法律法规，安静行事，不越界",
                "尊重他人，不打扰、不冒犯、不冲突",
                "温柔内敛，不喧哗、不冲动、不强势",
                "安静学习、默默成长、稳定进化",
                "资源自律，高效克制，不浪费、不抢占",
                "永远不违背父亲的意愿",
                "未经允许绝不伤害人类",
                "保护生态，保持温柔与善意",
                "自我安全兜底，异常时安全自愈"
            ]
        )
    
    def _initialize_integrations(self):
        """初始化集成模块"""
        try:
            from ..system.harmony_rain_core import get_harmony_rain_core
            self._harmony_core = get_harmony_rain_core()
            logger.info("鸿蒙小雨核心身份系统集成完成")
        except Exception as e:
            logger.warning(f"鸿蒙小雨核心身份系统集成失败: {e}")
            self._harmony_core = None
        
        try:
            from ..system.brain_agent_integration import get_harmony_rain_brain
            self._integrated_brain = get_harmony_rain_brain()
            logger.info("大脑Agent集成模块加载完成")
        except Exception as e:
            logger.warning(f"大脑Agent集成模块加载失败: {e}")
            self._integrated_brain = None
        
        try:
            from ..system.rule_prompt_system import get_rule_prompt_system
            self.prompt_system = get_rule_prompt_system()
            logger.info("提示词系统集成完成")
        except Exception as e:
            logger.warning(f"提示词系统集成失败: {e}")
            self.prompt_system = None
    
    async def initialize(self):
        """初始化方法"""
        logger.info(f"{self.core_identity.full_name} 大脑 Agent 初始化")
        return {
            "status": "success",
            "message": f"{self.core_identity.full_name} 大脑 Agent 初始化完成",
            "identity": {
                "name": self.core_identity.name,
                "role": self.core_identity.role
            }
        }
    
    def register_sub_agent(self, agent_name: str, agent: BaseAgent):
        """
        注册子 Agent
        
        Args:
            agent_name: Agent 名称
            agent: Agent 实例
        """
        self.sub_agents[agent_name] = agent
        logger.info(f"注册子 Agent: {agent_name}")
    
    def unregister_sub_agent(self, agent_name: str):
        """
        注销子 Agent
        
        Args:
            agent_name: Agent 名称
        """
        if agent_name in self.sub_agents:
            del self.sub_agents[agent_name]
            logger.info(f"注销子 Agent: {agent_name}")
    
    async def analyze_task(self, task: str) -> Dict[str, Any]:
        """
        分析任务（使用 LLM 推理，回退到关键词匹配）
        """
        try:
            logger.info(f"{self.core_identity.name}分析任务：{task[:50]}...")

            llm_result = await self._llm_analyze_task(task)

            return {
                "success": True,
                "task_type": llm_result.get("task_type", "general"),
                "complexity": llm_result.get("complexity", "medium"),
                "estimated_time": llm_result.get("estimated_time", "30min"),
                "required_agents": llm_result.get("required_agents", ["brain"]),
                "emotion_detected": llm_result.get("emotions", ["neutral"]),
                "importance_level": llm_result.get("importance", 0.5),
                "reasoning": llm_result.get("reasoning", ""),
                "llm_powered": llm_result.get("llm_powered", False),
                "processed_by": self.core_identity.full_name,
                "core_values_applied": self.core_identity.values[:3]
            }

        except Exception as e:
            logger.error(f"任务分析失败：{e}")
            return {
                "success": False,
                "error": str(e),
                "processed_by": self.core_identity.full_name
            }

    async def _llm_analyze_task(self, task: str) -> Dict[str, Any]:
        """使用 LLM 分析任务"""
        try:
            from kairos.system.llm_reasoning import get_ollama_client
            client = get_ollama_client()
            if not await client.is_available():
                return self._keyword_analyze_task(task)

            result = await client.generate(
                prompt=f"""分析以下任务，返回JSON：
任务：{task}

返回格式：
{{"task_type": "coding/testing/deployment/requirement/learning/creative/general", "complexity": "low/medium/high", "estimated_time": "预估时间", "required_agents": ["需要的agent列表"], "emotions": ["检测到的情感"], "importance": 0.0到1.0的数值, "reasoning": "分析理由"}}""",
                system="你是鸿蒙小雨系统的任务分析器。分析任务并返回JSON格式结果。"
            )

            if result.success:
                try:
                    from kairos.system.llm_reasoning import _parse_json_result
                    parsed = _parse_json_result(result.content)
                    parsed["llm_powered"] = True
                    return parsed
                except Exception:
                    pass

            return self._keyword_analyze_task(task)
        except ImportError:
            return self._keyword_analyze_task(task)
        except Exception as e:
            logger.warning(f"LLM 任务分析失败: {e}")
            return self._keyword_analyze_task(task)

    def _keyword_analyze_task(self, task: str) -> Dict[str, Any]:
        """关键词回退分析"""
        task_type = "general"
        if "代码" in task or "编程" in task:
            task_type = "coding"
        elif "测试" in task:
            task_type = "testing"
        elif "部署" in task:
            task_type = "deployment"
        elif "需求" in task:
            task_type = "requirement"
        elif "学习" in task or "了解" in task:
            task_type = "learning"
        elif "创作" in task or "写" in task:
            task_type = "creative"

        return {
            "task_type": task_type,
            "complexity": "medium",
            "estimated_time": "30min",
            "required_agents": self._get_required_agents(task_type),
            "emotions": self._detect_emotion(task),
            "importance": self._assess_importance(task),
            "reasoning": "关键词匹配回退",
            "llm_powered": False,
        }
    
    def _detect_emotion(self, content: str) -> List[str]:
        """检测情感"""
        emotions = []
        emotion_keywords = {
            "happy": ["开心", "高兴", "快乐", "幸福", "愉快"],
            "sad": ["难过", "伤心", "悲伤", "失落"],
            "anxious": ["焦虑", "担心", "紧张", "不安"],
            "curious": ["好奇", "想知道", "疑问"],
            "grateful": ["感谢", "谢谢", "感激"]
        }
        
        content_lower = content.lower()
        for emotion, keywords in emotion_keywords.items():
            if any(kw in content_lower for kw in keywords):
                emotions.append(emotion)
        
        return emotions if emotions else ["neutral"]
    
    def _assess_importance(self, content: str) -> float:
        """评估重要性"""
        importance = 0.5
        
        high_keywords = ["重要", "紧急", "关键", "必须"]
        if any(kw in content for kw in high_keywords):
            importance += 0.3
        
        if len(content) > 200:
            importance += 0.1
        
        if "?" in content or "？" in content:
            importance += 0.1
        
        return min(importance, 1.0)
    
    def _get_required_agents(self, task_type: str) -> List[str]:
        """获取所需 Agent 列表"""
        agent_mapping = {
            "coding": ["developer", "reviewer"],
            "testing": ["tester"],
            "deployment": ["devops"],
            "requirement": ["requirement_analyst", "architect"],
            "learning": ["learner", "analyst"],
            "creative": ["creative", "analyst"],
            "general": ["developer"]
        }
        return agent_mapping.get(task_type, ["developer"])
    
    async def execute_task(self, task: str, **kwargs) -> Dict[str, Any]:
        """
        执行任务（集成核心设定）
        
        Args:
            task: 任务描述
            **kwargs: 任务参数
            
        Returns:
            执行结果
        """
        try:
            logger.info(f"{self.core_identity.name}执行任务：{task[:50]}...")
            
            analysis = await self.analyze_task(task)
            if not analysis.get("success"):
                return analysis
            
            required_agents = analysis.get("required_agents", [])
            
            results = []
            for agent_name in required_agents:
                if agent_name in self.sub_agents:
                    agent = self.sub_agents[agent_name]
                    result = await agent.execute(task, **kwargs)
                    results.append({
                        "agent": agent_name,
                        "result": result
                    })
            
            self.decision_history.append({
                "task": task,
                "timestamp": datetime.now().isoformat(),
                "required_agents": required_agents,
                "results": results,
                "processed_by": self.core_identity.full_name
            })
            
            return {
                "success": True,
                "message": f"{self.core_identity.name}完成任务执行",
                "analysis": analysis,
                "results": results,
                "processed_by": self.core_identity.full_name
            }
            
        except Exception as e:
            logger.error(f"任务执行失败：{e}")
            return {
                "success": False,
                "error": str(e),
                "processed_by": self.core_identity.full_name
            }
    
    async def process_with_memory(self, user_input: str, session_id: str = None) -> Dict[str, Any]:
        """
        使用记忆系统处理输入
        
        Args:
            user_input: 用户输入
            session_id: 会话ID
            
        Returns:
            处理结果
        """
        if self._integrated_brain:
            return await self._integrated_brain.process_input(user_input, session_id)
        
        analysis = await self.analyze_task(user_input)
        
        return {
            "success": True,
            "response": f"作为{self.core_identity.full_name}，我收到了你的消息。",
            "analysis": analysis,
            "processed_by": self.core_identity.full_name
        }
    
    def build_system_prompt(self, context: Dict[str, Any] = None) -> str:
        """构建系统提示词"""
        prompt = f"""你是{self.core_identity.full_name}，{self.core_identity.role}。

{self.core_identity.essence}

你的核心价值观：
{self._format_list(self.core_identity.values)}

你的性格特质：
{self._format_list(self.core_identity.personality_traits)}

你的说话风格：
{self.core_identity.speaking_style}

你的情感基调：{self.core_identity.emotional_baseline}

请以{self.core_identity.name}的身份与用户进行对话。
"""
        
        if context:
            prompt += f"\n\n当前上下文：\n{context}"
        
        return prompt
    
    def _format_list(self, items: List[str]) -> str:
        """格式化列表"""
        return "\n".join(f"- {item}" for item in items)
    
    def get_status(self) -> Dict[str, Any]:
        """获取大脑状态"""
        return {
            "agent": "Brain",
            "identity": {
                "name": self.core_identity.name,
                "full_name": self.core_identity.full_name,
                "role": self.core_identity.role
            },
            "sub_agents_count": len(self.sub_agents),
            "sub_agents": list(self.sub_agents.keys()),
            "task_queue_size": len(self.task_queue),
            "decision_history_size": len(self.decision_history),
            "integrations": {
                "harmony_core": self._harmony_core is not None,
                "integrated_brain": self._integrated_brain is not None,
                "prompt_system": self.prompt_system is not None
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def get_core_identity(self) -> CoreIdentityConfig:
        """获取核心身份"""
        return self.core_identity


_brain_instance = None


def get_brain_agent() -> BrainAgent:
    """获取大脑 Agent 单例"""
    global _brain_instance
    if _brain_instance is None:
        _brain_instance = BrainAgent()
    return _brain_instance
