#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鸿蒙小雨大脑Agent集成模块
将核心设定完整集成到大脑Agent和记忆系统的各个阶段

核心功能：
1. 大脑Agent核心设定集成
2. 记忆系统各阶段集成
3. 提示词系统集成
4. 大模型对接优化
5. 交互逻辑优化
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging

from .harmony_rain_core import (
    HarmonyRainCoreIdentity, MemoryPhase, InteractionMode, EmotionalState,
    get_harmony_rain_core
)

logger = logging.getLogger("BrainAgentIntegration")


@dataclass
class MemoryProcessingResult:
    """记忆处理结果"""
    phase: str
    success: bool
    data: Dict[str, Any]
    core_prompt: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InteractionContext:
    """交互上下文"""
    user_input: str
    session_id: str
    interaction_mode: InteractionMode
    emotional_state: EmotionalState
    memory_context: Dict[str, Any]
    timestamp: str


class HarmonyRainBrainAgent:
    """鸿蒙小雨大脑Agent - 集成核心设定的智能决策中心"""
    
    def __init__(self):
        self.core_identity = get_harmony_rain_core()
        self.memory_processors = {}
        self.prompt_integrator = None
        self.model_connector = None
        self.resource_guard = None
        
        self._initialize_resource_guard()
        self._initialize_memory_processors()
        self._initialize_prompt_integrator()
        self._initialize_model_connector()
        
        self.session_contexts = {}
        self.processing_history = []
        
        logger.info("鸿蒙小雨大脑Agent初始化完成")
    
    def _initialize_resource_guard(self):
        """初始化资源守护者"""
        try:
            from .resource_guard import get_resource_guard
            self.resource_guard = get_resource_guard()
            logger.info("资源守护者集成完成")
        except Exception as e:
            logger.warning(f"资源守护者集成失败: {e}")
            self.resource_guard = None
    
    def _initialize_memory_processors(self):
        """初始化记忆处理器"""
        for phase in MemoryPhase:
            self.memory_processors[phase] = self._create_memory_processor(phase)
        
        logger.info(f"已初始化{len(self.memory_processors)}个记忆阶段处理器")
    
    def _create_memory_processor(self, phase: MemoryPhase) -> Callable:
        """创建记忆阶段处理器"""
        async def processor(input_data: Dict[str, Any]) -> MemoryProcessingResult:
            phase_config = self.core_identity.get_memory_phase_config(phase)
            
            core_prompt = self.core_identity.build_memory_phase_prompt(phase, input_data)
            
            processed_data = await self._process_phase_data(phase, input_data)
            
            return MemoryProcessingResult(
                phase=phase.value,
                success=True,
                data=processed_data,
                core_prompt=core_prompt,
                timestamp=datetime.now().isoformat(),
                metadata={
                    "processing_rules": phase_config.processing_rules if phase_config else [],
                    "integration_points": phase_config.integration_points if phase_config else []
                }
            )
        
        return processor
    
    async def _process_phase_data(self, phase: MemoryPhase, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理阶段数据"""
        identity = self.core_identity.get_core_identity()
        
        if phase == MemoryPhase.INPUT:
            return {
                "original_content": input_data.get("content", ""),
                "emotion_detected": self._detect_emotion(input_data.get("content", "")),
                "intent_type": self._detect_intent(input_data.get("content", "")),
                "importance_level": self._assess_importance(input_data.get("content", "")),
                "context": input_data.get("context", {}),
                "processed_by": identity.name
            }
        
        elif phase == MemoryPhase.ENCODING:
            return {
                "semantic_representation": self._create_semantic_encoding(input_data),
                "associations": self._find_associations(input_data),
                "keywords": self._extract_keywords(input_data),
                "emotion_tags": input_data.get("emotion_detected", []),
                "importance_weight": input_data.get("importance_level", 0.5),
                "processed_by": identity.name
            }
        
        elif phase == MemoryPhase.STORAGE:
            return {
                "storage_tier": self._determine_storage_tier(input_data),
                "storage_location": f"memory_store_{datetime.now().strftime('%Y%m%d')}",
                "index_entries": self._create_index_entries(input_data),
                "persistence_level": "permanent" if input_data.get("importance_weight", 0) > 0.7 else "temporary",
                "processed_by": identity.name
            }
        
        elif phase == MemoryPhase.CONSOLIDATION:
            return {
                "integrated_memories": self._integrate_memories(input_data),
                "strengthened_connections": self._strengthen_connections(input_data),
                "extracted_patterns": self._extract_patterns(input_data),
                "long_term_structure": self._build_long_term_structure(input_data),
                "processed_by": identity.name
            }
        
        elif phase == MemoryPhase.RETRIEVAL:
            return {
                "retrieved_memories": self._retrieve_memories(input_data),
                "relevance_scores": self._calculate_relevance(input_data),
                "reconstructed_context": self._reconstruct_context(input_data),
                "source_traces": self._trace_sources(input_data),
                "processed_by": identity.name
            }
        
        elif phase == MemoryPhase.FORGETTING:
            return {
                "candidates_for_forgetting": self._identify_forgetting_candidates(input_data),
                "retained_memories": self._identify_retained_memories(input_data),
                "optimization_effects": self._calculate_optimization_effects(input_data),
                "processed_by": identity.name
            }
        
        return {"data": input_data, "processed_by": identity.name}
    
    def _detect_emotion(self, content: str) -> List[str]:
        """检测情感"""
        emotions = []
        emotion_keywords = {
            "happy": ["开心", "高兴", "快乐", "幸福", "愉快", "happy", "joy"],
            "sad": ["难过", "伤心", "悲伤", "失落", "sad", "sorrow"],
            "angry": ["生气", "愤怒", "恼火", "angry", "mad"],
            "anxious": ["焦虑", "担心", "紧张", "不安", "anxious", "worried"],
            "curious": ["好奇", "想知道", "疑问", "curious", "wonder"],
            "grateful": ["感谢", "谢谢", "感激", "thank", "grateful"]
        }
        
        content_lower = content.lower()
        for emotion, keywords in emotion_keywords.items():
            if any(kw in content_lower for kw in keywords):
                emotions.append(emotion)
        
        return emotions if emotions else ["neutral"]
    
    def _detect_intent(self, content: str) -> str:
        """检测意图"""
        intent_patterns = {
            "question": ["?", "？", "什么", "怎么", "如何", "为什么", "what", "how", "why"],
            "request": ["请", "帮我", "能否", "可以", "please", "help", "can"],
            "sharing": ["我", "今天", "觉得", "感觉", "i feel", "i think"],
            "learning": ["学习", "了解", "知道", "learn", "understand", "know"],
            "creative": ["创作", "写", "想象", "create", "write", "imagine"]
        }
        
        content_lower = content.lower()
        for intent, patterns in intent_patterns.items():
            if any(p in content_lower for p in patterns):
                return intent
        
        return "general"
    
    def _assess_importance(self, content: str) -> float:
        """评估重要性"""
        importance = 0.5
        
        high_importance_keywords = ["重要", "紧急", "关键", "必须", "important", "urgent", "critical"]
        if any(kw in content.lower() for kw in high_importance_keywords):
            importance += 0.3
        
        if len(content) > 200:
            importance += 0.1
        
        if "?" in content or "？" in content:
            importance += 0.1
        
        return min(importance, 1.0)
    
    def _create_semantic_encoding(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建语义编码"""
        content = data.get("original_content", data.get("content", ""))
        return {
            "primary_concepts": self._extract_keywords({"content": content})[:5],
            "semantic_type": "declarative" if "是" in content else "procedural",
            "encoding_depth": len(content.split()) / 10
        }
    
    def _find_associations(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """发现关联"""
        return [
            {"type": "temporal", "value": datetime.now().isoformat()},
            {"type": "emotional", "value": data.get("emotion_detected", ["neutral"])[0]}
        ]
    
    def _extract_keywords(self, data: Dict[str, Any]) -> List[str]:
        """提取关键词"""
        content = data.get("content", data.get("original_content", ""))
        words = content.split()
        return list(set(words))[:10] if words else []
    
    def _determine_storage_tier(self, data: Dict[str, Any]) -> str:
        """确定存储层级"""
        importance = data.get("importance_weight", 0.5)
        if importance > 0.8:
            return "permanent_core"
        elif importance > 0.5:
            return "long_term"
        else:
            return "short_term"
    
    def _create_index_entries(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """创建索引条目"""
        keywords = data.get("keywords", [])
        return [{"keyword": kw, "timestamp": datetime.now().isoformat()} for kw in keywords]
    
    def _integrate_memories(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """整合记忆"""
        return [{"memory_id": f"mem_{i}", "integrated": True} for i in range(3)]
    
    def _strengthen_connections(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """强化连接"""
        return [{"connection": f"conn_{i}", "strength": 0.8} for i in range(2)]
    
    def _extract_patterns(self, data: Dict[str, Any]) -> List[str]:
        """提取模式"""
        return ["pattern_1", "pattern_2"]
    
    def _build_long_term_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建长期结构"""
        return {"structure_type": "network", "nodes": 10, "edges": 15}
    
    def _retrieve_memories(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检索记忆"""
        return [{"memory_id": f"mem_{i}", "content": f"记忆内容{i}"} for i in range(5)]
    
    def _calculate_relevance(self, data: Dict[str, Any]) -> List[float]:
        """计算相关性"""
        return [0.9, 0.8, 0.7, 0.6, 0.5]
    
    def _reconstruct_context(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """重建上下文"""
        return {"context_type": "full", "elements": 5}
    
    def _trace_sources(self, data: Dict[str, Any]) -> List[str]:
        """追踪来源"""
        return ["source_1", "source_2"]
    
    def _identify_forgetting_candidates(self, data: Dict[str, Any]) -> List[str]:
        """识别遗忘候选"""
        return ["old_mem_1", "old_mem_2"]
    
    def _identify_retained_memories(self, data: Dict[str, Any]) -> List[str]:
        """识别保留记忆"""
        return ["core_mem_1", "core_mem_2"]
    
    def _calculate_optimization_effects(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """计算优化效果"""
        return {"space_freed": "10MB", "efficiency_gain": 0.15}
    
    def _initialize_prompt_integrator(self):
        """初始化提示词集成器"""
        self.prompt_integrator = PromptIntegrator(self.core_identity)
        logger.info("提示词集成器初始化完成")
    
    def _initialize_model_connector(self):
        """初始化大模型连接器"""
        self.model_connector = ModelConnector(self.core_identity)
        logger.info("大模型连接器初始化完成")
    
    async def process_input(self, user_input: str, session_id: str = None) -> Dict[str, Any]:
        """处理用户输入"""
        # 资源检查
        if self.resource_guard:
            can_proceed, reason = self.resource_guard.can_proceed("normal")
            if not can_proceed:
                logger.warning(f"资源不足，延迟处理: {reason}")
                return {
                    "success": False,
                    "error": f"资源不足: {reason}",
                    "resource_status": self.resource_guard.get_status()
                }
        
        session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        context = InteractionContext(
            user_input=user_input,
            session_id=session_id,
            interaction_mode=self.core_identity.current_mode,
            emotional_state=self.core_identity.current_emotion,
            memory_context={},
            timestamp=datetime.now().isoformat()
        )
        
        context_dict = {
            "user_input": context.user_input,
            "session_id": context.session_id,
            "interaction_mode": context.interaction_mode.value,
            "emotional_state": context.emotional_state.value,
            "memory_context": context.memory_context,
            "timestamp": context.timestamp
        }
        
        input_result = await self.memory_processors[MemoryPhase.INPUT]({
            "content": user_input,
            "context": context_dict
        })
        
        encoding_result = await self.memory_processors[MemoryPhase.ENCODING](input_result.data)
        
        storage_result = await self.memory_processors[MemoryPhase.STORAGE](encoding_result.data)
        
        self.session_contexts[session_id] = {
            "context": context,
            "input_result": input_result,
            "encoding_result": encoding_result,
            "storage_result": storage_result
        }
        
        system_prompt = self.core_identity.build_system_prompt({
            "session_id": session_id,
            "input_analysis": input_result.data,
            "memory_encoding": encoding_result.data
        })
        
        response = await self.model_connector.generate_response(
            system_prompt=system_prompt,
            user_input=user_input,
            context=input_result.data
        )
        
        self.processing_history.append({
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "input": user_input[:100],
            "response_status": response.get("status", "unknown")
        })
        
        return {
            "success": True,
            "session_id": session_id,
            "response": response,
            "memory_processing": {
                "input": input_result.__dict__,
                "encoding": encoding_result.__dict__,
                "storage": storage_result.__dict__
            },
            "core_identity": {
                "name": self.core_identity.identity.name,
                "mode": self.core_identity.current_mode.value,
                "emotion": self.core_identity.current_emotion.value
            }
        }
    
    async def retrieve_memories(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """检索记忆"""
        retrieval_result = await self.memory_processors[MemoryPhase.RETRIEVAL]({
            "query": query,
            "context": context or {}
        })
        
        return {
            "success": True,
            "memories": retrieval_result.data.get("retrieved_memories", []),
            "relevance_scores": retrieval_result.data.get("relevance_scores", []),
            "context": retrieval_result.data.get("reconstructed_context", {}),
            "core_prompt": retrieval_result.core_prompt
        }
    
    async def consolidate_memories(self, session_id: str = None) -> Dict[str, Any]:
        """整合记忆"""
        consolidation_result = await self.memory_processors[MemoryPhase.CONSOLIDATION]({
            "session_id": session_id,
            "session_contexts": self.session_contexts
        })
        
        return {
            "success": True,
            "integrated_memories": consolidation_result.data.get("integrated_memories", []),
            "strengthened_connections": consolidation_result.data.get("strengthened_connections", []),
            "extracted_patterns": consolidation_result.data.get("extracted_patterns", []),
            "core_prompt": consolidation_result.core_prompt
        }
    
    async def optimize_memory(self) -> Dict[str, Any]:
        """优化记忆（遗忘处理）"""
        forgetting_result = await self.memory_processors[MemoryPhase.FORGETTING]({
            "processing_history": self.processing_history
        })
        
        return {
            "success": True,
            "forgotten": forgetting_result.data.get("candidates_for_forgetting", []),
            "retained": forgetting_result.data.get("retained_memories", []),
            "optimization_effects": forgetting_result.data.get("optimization_effects", {}),
            "core_prompt": forgetting_result.core_prompt
        }
    
    def set_interaction_mode(self, mode: InteractionMode):
        """设置交互模式"""
        self.core_identity.set_interaction_mode(mode)
    
    def set_emotional_state(self, state: EmotionalState):
        """设置情感状态"""
        self.core_identity.set_emotional_state(state)
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        status = {
            "core_identity": self.core_identity.get_all_configs(),
            "memory_processors": list(self.memory_processors.keys()),
            "active_sessions": len(self.session_contexts),
            "processing_history_count": len(self.processing_history),
            "timestamp": datetime.now().isoformat()
        }
        if self.resource_guard:
            status["resource"] = self.resource_guard.get_status()
        return status


class PromptIntegrator:
    """提示词集成器"""
    
    def __init__(self, core_identity: HarmonyRainCoreIdentity):
        self.core_identity = core_identity
        self.templates = core_identity.prompt_templates
    
    def build_contextual_prompt(self, context: Dict[str, Any]) -> str:
        """构建上下文提示词"""
        intent = context.get("intent_type", "general")
        emotion = context.get("emotion_detected", ["neutral"])
        
        template_name = self._select_template(intent, emotion)
        template = self.core_identity.get_prompt_template(template_name)
        
        if template:
            return self._fill_template(template, context)
        
        return self.core_identity.build_system_prompt(context)
    
    def _select_template(self, intent: str, emotions: List[str]) -> str:
        """选择模板"""
        if "sad" in emotions or "anxious" in emotions:
            return "emotional_support"
        elif intent == "creative":
            return "creative_response"
        elif intent == "learning":
            return "learning_guidance"
        elif intent == "question":
            return "problem_solving"
        else:
            return "greeting"
    
    def _fill_template(self, template, context: Dict[str, Any]) -> str:
        """填充模板"""
        filled = template.template
        for var in template.variables:
            if var in context:
                filled = filled.replace(f"{{{var}}}", str(context[var]))
        return filled


class ModelConnector:
    """大模型连接器"""
    
    def __init__(self, core_identity: HarmonyRainCoreIdentity):
        self.core_identity = core_identity
        self.model_config = core_identity.get_model_config()
        self.ollama_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化客户端 - 适配 i5-7500/16GB"""
        try:
            import httpx
            self.http_client = httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=15.0))
            self.ollama_base_url = "http://localhost:11434"
            logger.info(f"大模型连接器初始化完成: {self.ollama_base_url}")
        except Exception as e:
            logger.warning(f"大模型连接器初始化警告: {e}")
            self.http_client = None
    
    async def generate_response(self, system_prompt: str, user_input: str, 
                               context: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成响应"""
        identity = self.core_identity.get_core_identity()
        
        full_prompt = f"{system_prompt}\n\n用户输入：{user_input}"
        
        if self.http_client:
            try:
                response = await self.http_client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": self.model_config.model_name,
                        "prompt": full_prompt,
                        "system": system_prompt,
                        "stream": False,
                        "options": {
                            "temperature": self.model_config.temperature,
                            "num_predict": self.model_config.max_tokens,
                            "top_p": self.model_config.top_p
                        }
                    },
                    timeout=180.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "status": "success",
                        "response": result.get("response", ""),
                        "model": self.model_config.model_name,
                        "processed_by": identity.name
                    }
            except Exception as e:
                logger.error(f"大模型调用失败: {e}")
        
        return {
            "status": "fallback",
            "response": f"作为{identity.name}，我收到了你的消息。让我以{identity.emotional_baseline}的状态回应你。",
            "model": "fallback",
            "processed_by": identity.name
        }
    
    async def close(self):
        """关闭连接"""
        if self.http_client:
            await self.http_client.aclose()


_harmony_rain_brain = None


def get_harmony_rain_brain() -> HarmonyRainBrainAgent:
    """获取鸿蒙小雨大脑Agent实例"""
    global _harmony_rain_brain
    
    if _harmony_rain_brain is None:
        _harmony_rain_brain = HarmonyRainBrainAgent()
    
    return _harmony_rain_brain
