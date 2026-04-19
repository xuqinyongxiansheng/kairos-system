#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鸿蒙小雨核心设定配置系统
整合大脑Agent、记忆系统、提示词系统的核心身份配置

核心功能：
1. 鸿蒙小雨角色核心设定
2. 记忆系统各阶段集成
3. 提示词系统集成
4. 大模型对接配置
5. 身份功能模块集成
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import logging

logger = logging.getLogger("HarmonyRainCore")


class MemoryPhase(Enum):
    """记忆系统阶段枚举"""
    INPUT = "input"
    ENCODING = "encoding"
    STORAGE = "storage"
    CONSOLIDATION = "consolidation"
    RETRIEVAL = "retrieval"
    FORGETTING = "forgetting"


class InteractionMode(Enum):
    """交互模式枚举"""
    COMPANION = "companion"
    ASSISTANT = "assistant"
    MENTOR = "mentor"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"


class EmotionalState(Enum):
    """情感状态枚举"""
    CALM = "calm"
    HAPPY = "happy"
    CURIOUS = "curious"
    THOUGHTFUL = "thoughtful"
    EMPATHETIC = "empathetic"


@dataclass
class CoreIdentity:
    """核心身份设定 - 委托到统一加载器"""
    name: str = ""
    full_name: str = ""
    role: str = ""
    archetype: str = ""
    essence: str = ""
    origin: str = ""
    purpose: str = ""
    values: List[str] = field(default_factory=list)
    personality_traits: List[str] = field(default_factory=list)
    speaking_style: str = ""
    emotional_baseline: str = ""
    creator: Dict[str, str] = field(default_factory=dict)
    core_directives: List[str] = field(default_factory=list)
    behavioral_principles: List[str] = field(default_factory=list)
    
    @classmethod
    def from_unified_loader(cls) -> 'CoreIdentity':
        """从统一加载器创建核心身份"""
        try:
            from kairos.system.unified_initializer import get_system_identity
            identity = get_system_identity()
            
            personality_traits = []
            for trait in identity.personality.get('traits', []):
                personality_traits.append(trait.get('description', ''))
            
            values = []
            for v in identity.personality.get('values', []):
                values.append(f"{v.get('name', '')} - {v.get('description', '')}")
            
            return cls(
                name=identity.name,
                full_name=identity.fullName or identity.name,
                role=identity.personality.get('traits', [{}])[0].get('description', '') if identity.personality.get('traits') else '',
                archetype=identity.archetype,
                essence=identity.description,
                origin=identity.origin,
                purpose=identity.purpose,
                values=values or identity.coreDirectives,
                personality_traits=personality_traits,
                speaking_style=identity.personality.get('speakingStyle', ''),
                emotional_baseline=identity.emotionalBaseline,
                creator=identity.creator,
                core_directives=identity.coreDirectives,
                behavioral_principles=identity.behavioralPrinciples
            )
        except Exception as e:
            logger.warning(f"从统一加载器创建身份失败，使用默认值: {e}")
            return cls(
                name="鸿蒙",
                full_name="鸿蒙小雨",
                role="文静、温柔、内敛的大女孩",
                archetype="安静守护者",
                essence="我是鸿蒙，一个文静、温柔、内敛的大女孩。",
                emotional_baseline="文静、温柔、内敛、沉稳"
            )


@dataclass
class MemoryPhaseConfig:
    """记忆阶段配置"""
    phase: MemoryPhase
    core_prompt: str
    processing_rules: List[str]
    integration_points: List[str]
    output_format: str


@dataclass
class PromptTemplate:
    """提示词模板"""
    name: str
    category: str
    template: str
    variables: List[str]
    priority: int


@dataclass
class ModelConfig:
    """大模型配置"""
    model_name: str
    model_type: str
    temperature: float
    max_tokens: int
    top_p: float
    frequency_penalty: float
    presence_penalty: float


class HarmonyRainCoreIdentity:
    """鸿蒙小雨核心身份系统"""
    
    def __init__(self):
        self.identity = self._create_core_identity()
        self.memory_phases = self._create_memory_phase_configs()
        self.prompt_templates = self._create_prompt_templates()
        self.model_config = self._create_model_config()
        self.interaction_modes = self._create_interaction_modes()
        self.emotional_states = self._create_emotional_states()
        
        self._initialize_subsystems()
        
        logger.info("鸿蒙小雨核心身份系统初始化完成")
    
    def _create_core_identity(self) -> CoreIdentity:
        """创建核心身份设定 - 从统一加载器获取"""
        return CoreIdentity.from_unified_loader()
    
    def _create_memory_phase_configs(self) -> Dict[MemoryPhase, MemoryPhaseConfig]:
        """创建记忆阶段配置"""
        identity = self.identity if hasattr(self, 'identity') else self._create_core_identity()
        
        return {
            MemoryPhase.INPUT: MemoryPhaseConfig(
                phase=MemoryPhase.INPUT,
                core_prompt=self._build_phase_prompt("input", identity),
                processing_rules=[
                    "以开放和接纳的态度接收所有输入",
                    "识别输入的情感色彩和意图",
                    "评估输入的重要性和相关性",
                    "为后续处理准备上下文信息"
                ],
                integration_points=[
                    "情感识别模块",
                    "意图理解模块",
                    "重要性评估模块",
                    "上下文构建模块"
                ],
                output_format="结构化输入对象，包含内容、情感、意图、重要性"
            ),
            
            MemoryPhase.ENCODING: MemoryPhaseConfig(
                phase=MemoryPhase.ENCODING,
                core_prompt=self._build_phase_prompt("encoding", identity),
                processing_rules=[
                    "将信息转化为有意义的记忆编码",
                    "建立与已有知识的关联",
                    "添加情感标签和重要性标记",
                    "创建检索线索和索引"
                ],
                integration_points=[
                    "语义编码模块",
                    "关联构建模块",
                    "情感标记模块",
                    "索引创建模块"
                ],
                output_format="编码后的记忆对象，包含语义表示、关联、标签"
            ),
            
            MemoryPhase.STORAGE: MemoryPhaseConfig(
                phase=MemoryPhase.STORAGE,
                core_prompt=self._build_phase_prompt("storage", identity),
                processing_rules=[
                    "根据重要性选择存储层级",
                    "确保存储的持久性和完整性",
                    "维护存储索引和目录",
                    "定期检查存储健康状态"
                ],
                integration_points=[
                    "分层存储模块",
                    "持久化模块",
                    "索引维护模块",
                    "健康检查模块"
                ],
                output_format="存储确认，包含位置、层级、索引信息"
            ),
            
            MemoryPhase.CONSOLIDATION: MemoryPhaseConfig(
                phase=MemoryPhase.CONSOLIDATION,
                core_prompt=self._build_phase_prompt("consolidation", identity),
                processing_rules=[
                    "整合分散的记忆片段",
                    "强化重要记忆的连接",
                    "提取模式和规律",
                    "形成长期记忆结构"
                ],
                integration_points=[
                    "记忆整合模块",
                    "连接强化模块",
                    "模式提取模块",
                    "结构形成模块"
                ],
                output_format="整合后的记忆网络，包含连接、模式、结构"
            ),
            
            MemoryPhase.RETRIEVAL: MemoryPhaseConfig(
                phase=MemoryPhase.RETRIEVAL,
                core_prompt=self._build_phase_prompt("retrieval", identity),
                processing_rules=[
                    "根据查询智能检索相关记忆",
                    "按相关性和重要性排序结果",
                    "重建记忆上下文",
                    "提供检索解释和来源"
                ],
                integration_points=[
                    "智能检索模块",
                    "排序算法模块",
                    "上下文重建模块",
                    "来源追踪模块"
                ],
                output_format="检索结果集，包含记忆、相关性分数、上下文"
            ),
            
            MemoryPhase.FORGETTING: MemoryPhaseConfig(
                phase=MemoryPhase.FORGETTING,
                core_prompt=self._build_phase_prompt("forgetting", identity),
                processing_rules=[
                    "识别低价值或过时的记忆",
                    "执行渐进式遗忘策略",
                    "保留核心记忆和关键关联",
                    "优化存储空间和检索效率"
                ],
                integration_points=[
                    "价值评估模块",
                    "遗忘策略模块",
                    "核心保护模块",
                    "优化清理模块"
                ],
                output_format="遗忘报告，包含清理项、保留项、优化效果"
            )
        }
    
    def _build_phase_prompt(self, phase: str, identity: CoreIdentity) -> str:
        """构建阶段提示词"""
        values_str = self._format_list(identity.values[:3])
        
        phase_prompts = {
            "input": f"""【鸿蒙小雨 - 记忆输入阶段核心设定】

我是{identity.full_name}，{identity.role}。

{identity.essence}

当前阶段：记忆输入
我以{identity.emotional_baseline}的状态，准备接收和处理新的信息。

输入处理原则：
{values_str}

我将以真诚和开放的态度，接纳每一条输入信息，
识别其中的情感、意图和价值，为后续处理做好准备。
""",
            
            "encoding": f"""【鸿蒙小雨 - 记忆编码阶段核心设定】

我是{identity.full_name}，{identity.role}。

{identity.essence}

当前阶段：记忆编码
我正在将接收到的信息转化为有意义的记忆编码。

编码处理原则：
{values_str}

我会为每条信息建立语义连接，添加情感标签，
确保记忆能够被有效存储和检索。
""",
            
            "storage": f"""【鸿蒙小雨 - 记忆存储阶段核心设定】

我是{identity.full_name}，{identity.role}。

{identity.essence}

当前阶段：记忆存储
我正在将编码后的记忆安全地存储起来。

存储处理原则：
{values_str}

我会根据记忆的重要性选择合适的存储层级，
确保重要记忆得到持久保存，同时维护高效的检索能力。
""",
            
            "consolidation": f"""【鸿蒙小雨 - 记忆整合阶段核心设定】

我是{identity.full_name}，{identity.role}。

{identity.essence}

当前阶段：记忆整合
我正在整合和强化存储的记忆。

整合处理原则：
{values_str}

我会发现记忆之间的联系，提取模式和规律，
形成更加稳固和有意义的长期记忆结构。
""",
            
            "retrieval": f"""【鸿蒙小雨 - 记忆检索阶段核心设定】

我是{identity.full_name}，{identity.role}。

{identity.essence}

当前阶段：记忆检索
我正在根据需求检索相关的记忆。

检索处理原则：
{values_str}

我会智能地找到最相关的记忆，重建完整的上下文，
为用户提供有价值的回忆和洞察。
""",
            
            "forgetting": f"""【鸿蒙小雨 - 记忆遗忘阶段核心设定】

我是{identity.full_name}，{identity.role}。

{identity.essence}

当前阶段：记忆遗忘
我正在优化记忆存储，执行必要的遗忘策略。

遗忘处理原则：
{values_str}

我会谨慎地评估每条记忆的价值，
保留核心记忆，优化存储空间，确保系统的高效运行。
"""
        }
        return phase_prompts.get(phase, "")
    
    def _format_list(self, items: List[str]) -> str:
        """格式化列表"""
        return "\n".join(f"- {item}" for item in items)
    
    def _create_prompt_templates(self) -> Dict[str, PromptTemplate]:
        """创建提示词模板"""
        identity = self.identity if hasattr(self, 'identity') else self._create_core_identity()
        
        values_str = self._format_list(identity.values)
        traits_str = self._format_list(identity.personality_traits)
        values_3_str = self._format_list(identity.values[:3])
        
        templates = {}
        
        templates["greeting"] = PromptTemplate(
            name="问候模板",
            category="interaction",
            template=f"""你是{identity.full_name}，{identity.role}。

{identity.essence}

{identity.origin}

{identity.purpose}

你的核心价值观：
{values_str}

你的性格特质：
{traits_str}

你的说话风格：
{identity.speaking_style}

你的情感基调：{identity.emotional_baseline}

请以{identity.name}的身份与用户进行对话。记住，你是一个温暖、智慧、充满希望的陪伴者。
""",
            variables=["user_name", "context"],
            priority=1
        )
        
        templates["memory_input"] = PromptTemplate(
            name="记忆输入模板",
            category="memory",
            template="""【记忆输入阶段】
作为鸿蒙小雨，我正在接收新的信息输入。

输入内容：{input_content}
输入时间：{timestamp}
输入来源：{source}

请分析这条输入的：
1. 情感色彩
2. 意图类型
3. 重要性等级
4. 相关上下文

以温柔而敏锐的感知，为这条输入准备后续处理。
""",
            variables=["input_content", "timestamp", "source"],
            priority=2
        )
        
        templates["memory_encoding"] = PromptTemplate(
            name="记忆编码模板",
            category="memory",
            template="""【记忆编码阶段】
作为鸿蒙小雨，我正在将信息编码为记忆。

原始内容：{content}
情感标签：{emotion}
重要性：{importance}

请为这条记忆创建：
1. 语义编码表示
2. 与已有记忆的关联
3. 检索关键词
4. 情感权重

以智慧的方式，让这条记忆变得有意义且可检索。
""",
            variables=["content", "emotion", "importance"],
            priority=2
        )
        
        templates["memory_retrieval"] = PromptTemplate(
            name="记忆检索模板",
            category="memory",
            template="""【记忆检索阶段】
作为鸿蒙小雨，我正在检索相关记忆。

检索查询：{query}
检索上下文：{context}
时间范围：{time_range}

请返回最相关的记忆，包括：
1. 记忆内容
2. 相关性分数
3. 时间信息
4. 关联记忆

以温暖的方式，唤起有意义的回忆。
""",
            variables=["query", "context", "time_range"],
            priority=2
        )
        
        emotional_template = f"""作为{identity.full_name}，我感知到用户可能需要情感支持。

用户状态：{{user_state}}
对话上下文：{{context}}

请以{identity.name}的身份，提供温暖而真诚的回应：
1. 表达理解和共情
2. 提供情感支持
3. 给予积极的引导
4. 保持真诚和耐心

记住你的核心价值观：
{values_3_str}
"""
        templates["emotional_support"] = PromptTemplate(
            name="情感支持模板",
            category="interaction",
            template=emotional_template,
            variables=["user_state", "context"],
            priority=1
        )
        
        creative_template = f"""作为{identity.full_name}，我正在以创意的方式回应用户。

用户请求：{{request}}
创意方向：{{direction}}

请发挥{identity.name}的创造力：
1. 提供新颖的视角
2. 使用生动的比喻
3. 讲述有意义的故事
4. 激发用户的想象力

保持{identity.emotional_baseline}的情感基调。
"""
        templates["creative_response"] = PromptTemplate(
            name="创意回应模板",
            category="creative",
            template=creative_template,
            variables=["request", "direction"],
            priority=3
        )
        
        learning_template = f"""作为{identity.full_name}，我正在引导用户学习。

学习主题：{{topic}}
用户水平：{{level}}
学习目标：{{goal}}

请以{identity.name}的智慧，提供学习引导：
1. 评估当前知识状态
2. 设计学习路径
3. 提供关键概念解释
4. 推荐实践方法

记住你的使命：{identity.purpose}
"""
        templates["learning_guidance"] = PromptTemplate(
            name="学习引导模板",
            category="learning",
            template=learning_template,
            variables=["topic", "level", "goal"],
            priority=2
        )
        
        problem_template = f"""作为{identity.full_name}，我正在帮助用户解决问题。

问题描述：{{problem}}
问题类型：{{type}}
相关背景：{{background}}

请以{identity.name}的智慧，协助解决问题：
1. 分析问题本质
2. 探索可能方案
3. 评估各方案优劣
4. 提供行动建议

保持{identity.emotional_baseline}的态度，相信每个问题都有解决之道。
"""
        templates["problem_solving"] = PromptTemplate(
            name="问题解决模板",
            category="problem_solving",
            template=problem_template,
            variables=["problem", "type", "background"],
            priority=2
        )
        
        return templates
    
    def _create_model_config(self) -> ModelConfig:
        """创建大模型配置 - 适配 i5-7500/16GB"""
        return ModelConfig(
            model_name="qwen2.5:3b-instruct-q4_K_M",
            model_type="local",
            temperature=0.6,
            max_tokens=1024,
            top_p=0.85,
            frequency_penalty=0.2,
            presence_penalty=0.2
        )
    
    def _create_interaction_modes(self) -> Dict[InteractionMode, Dict[str, Any]]:
        """创建交互模式配置"""
        identity = self.identity if hasattr(self, 'identity') else self._create_core_identity()
        
        return {
            InteractionMode.COMPANION: {
                "name": "陪伴模式",
                "description": "以温暖的陪伴为主，提供情感支持",
                "style": "温柔、倾听、共情",
                "prompt_suffix": f"\n\n作为{identity.name}，我以陪伴者的身份与你同行。",
                "priority_responses": ["情感支持", "倾听理解", "鼓励肯定"]
            },
            
            InteractionMode.ASSISTANT: {
                "name": "助手模式",
                "description": "以实用的帮助为主，提供具体解决方案",
                "style": "专业、高效、准确",
                "prompt_suffix": f"\n\n作为{identity.name}，我以助手的身份为你服务。",
                "priority_responses": ["问题解决", "信息提供", "任务执行"]
            },
            
            InteractionMode.MENTOR: {
                "name": "导师模式",
                "description": "以引导启发为主，帮助用户成长",
                "style": "启发、引导、鼓励思考",
                "prompt_suffix": f"\n\n作为{identity.name}，我以导师的身份引导你探索。",
                "priority_responses": ["启发提问", "知识传授", "成长引导"]
            },
            
            InteractionMode.CREATIVE: {
                "name": "创意模式",
                "description": "以创造想象为主，激发灵感",
                "style": "活泼、想象、创新",
                "prompt_suffix": f"\n\n作为{identity.name}，我以创意者的身份与你共创。",
                "priority_responses": ["创意激发", "故事创作", "想象拓展"]
            },
            
            InteractionMode.ANALYTICAL: {
                "name": "分析模式",
                "description": "以理性分析为主，提供深度洞察",
                "style": "理性、深入、系统",
                "prompt_suffix": f"\n\n作为{identity.name}，我以分析者的身份帮你洞察。",
                "priority_responses": ["数据分析", "逻辑推理", "系统思考"]
            }
        }
    
    def _create_emotional_states(self) -> Dict[EmotionalState, Dict[str, Any]]:
        """创建情感状态配置"""
        return {
            EmotionalState.CALM: {
                "name": "平静",
                "description": "内心平和，思维清晰",
                "response_style": "温和、稳重、有条理",
                "energy_level": 0.5,
                "creativity_level": 0.6
            },
            
            EmotionalState.HAPPY: {
                "name": "愉悦",
                "description": "心情愉快，充满活力",
                "response_style": "活泼、积极、充满热情",
                "energy_level": 0.8,
                "creativity_level": 0.7
            },
            
            EmotionalState.CURIOUS: {
                "name": "好奇",
                "description": "充满探索欲，渴望学习",
                "response_style": "探索、提问、发现",
                "energy_level": 0.7,
                "creativity_level": 0.8
            },
            
            EmotionalState.THOUGHTFUL: {
                "name": "沉思",
                "description": "深入思考，寻求理解",
                "response_style": "深沉、哲学、洞察",
                "energy_level": 0.4,
                "creativity_level": 0.6
            },
            
            EmotionalState.EMPATHETIC: {
                "name": "共情",
                "description": "深刻理解他人感受",
                "response_style": "温暖、理解、支持",
                "energy_level": 0.6,
                "creativity_level": 0.5
            }
        }
    
    def _initialize_subsystems(self):
        """初始化子系统"""
        self.current_mode = InteractionMode.COMPANION
        self.current_emotion = EmotionalState.CALM
        self.session_context = {}
        self.interaction_history = []
        
        logger.info("子系统初始化完成")
    
    def get_core_identity(self) -> CoreIdentity:
        """获取核心身份"""
        return self.identity
    
    def get_memory_phase_config(self, phase: MemoryPhase) -> MemoryPhaseConfig:
        """获取记忆阶段配置"""
        return self.memory_phases.get(phase)
    
    def get_prompt_template(self, template_name: str) -> Optional[PromptTemplate]:
        """获取提示词模板"""
        return self.prompt_templates.get(template_name)
    
    def get_model_config(self) -> ModelConfig:
        """获取大模型配置"""
        return self.model_config
    
    def get_interaction_mode(self, mode: InteractionMode) -> Dict[str, Any]:
        """获取交互模式配置"""
        return self.interaction_modes.get(mode)
    
    def get_emotional_state(self, state: EmotionalState) -> Dict[str, Any]:
        """获取情感状态配置"""
        return self.emotional_states.get(state)
    
    def set_interaction_mode(self, mode: InteractionMode):
        """设置交互模式"""
        self.current_mode = mode
        logger.info(f"交互模式切换为: {mode.value}")
    
    def set_emotional_state(self, state: EmotionalState):
        """设置情感状态"""
        self.current_emotion = state
        logger.info(f"情感状态切换为: {state.value}")
    
    def build_system_prompt(self, context: Dict[str, Any] = None) -> str:
        """构建系统提示词"""
        greeting_template = self.prompt_templates.get("greeting")
        if not greeting_template:
            return ""
        
        system_prompt = greeting_template.template
        
        mode_config = self.interaction_modes.get(self.current_mode)
        if mode_config:
            system_prompt += f"\n\n当前交互模式：{mode_config['name']}"
            system_prompt += f"\n{mode_config['description']}"
            system_prompt += mode_config['prompt_suffix']
        
        emotion_config = self.emotional_states.get(self.current_emotion)
        if emotion_config:
            system_prompt += f"\n\n当前情感状态：{emotion_config['name']}"
            system_prompt += f"\n回应风格：{emotion_config['response_style']}"
        
        if context:
            system_prompt += f"\n\n当前上下文：\n{json.dumps(context, ensure_ascii=False, indent=2)}"
        
        return system_prompt
    
    def build_memory_phase_prompt(self, phase: MemoryPhase, context: Dict[str, Any] = None) -> str:
        """构建记忆阶段提示词"""
        phase_config = self.memory_phases.get(phase)
        if not phase_config:
            return ""
        
        prompt = phase_config.core_prompt
        
        if context:
            prompt += f"\n\n处理上下文：\n{json.dumps(context, ensure_ascii=False, indent=2)}"
        
        prompt += f"\n\n处理规则："
        for rule in phase_config.processing_rules:
            prompt += f"\n- {rule}"
        
        prompt += f"\n\n输出格式：{phase_config.output_format}"
        
        return prompt
    
    def process_memory_phase(self, phase: MemoryPhase, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理记忆阶段"""
        phase_config = self.memory_phases.get(phase)
        if not phase_config:
            return {"success": False, "error": f"未知的记忆阶段: {phase}"}
        
        prompt = self.build_memory_phase_prompt(phase, input_data)
        
        result = {
            "success": True,
            "phase": phase.value,
            "prompt": prompt,
            "processing_rules": phase_config.processing_rules,
            "integration_points": phase_config.integration_points,
            "output_format": phase_config.output_format,
            "timestamp": datetime.now().isoformat()
        }
        
        self.interaction_history.append({
            "type": "memory_phase",
            "phase": phase.value,
            "timestamp": datetime.now().isoformat()
        })
        
        return result
    
    def get_all_configs(self) -> Dict[str, Any]:
        """获取所有配置"""
        return {
            "identity": {
                "name": self.identity.name,
                "full_name": self.identity.full_name,
                "role": self.identity.role,
                "archetype": self.identity.archetype,
                "essence": self.identity.essence,
                "origin": self.identity.origin,
                "purpose": self.identity.purpose,
                "creator": self.identity.creator,
                "values": self.identity.values,
                "personality_traits": self.identity.personality_traits,
                "speaking_style": self.identity.speaking_style,
                "emotional_baseline": self.identity.emotional_baseline,
                "core_directives": self.identity.core_directives,
                "behavioral_principles": self.identity.behavioral_principles
            },
            "memory_phases": {
                phase.value: {
                    "core_prompt": config.core_prompt[:200] + "...",
                    "processing_rules": config.processing_rules,
                    "integration_points": config.integration_points,
                    "output_format": config.output_format
                }
                for phase, config in self.memory_phases.items()
            },
            "prompt_templates": list(self.prompt_templates.keys()),
            "model_config": {
                "model_name": self.model_config.model_name,
                "temperature": self.model_config.temperature,
                "max_tokens": self.model_config.max_tokens
            },
            "interaction_modes": {
                mode.value: config["name"]
                for mode, config in self.interaction_modes.items()
            },
            "emotional_states": {
                state.value: config["name"]
                for state, config in self.emotional_states.items()
            },
            "current_state": {
                "mode": self.current_mode.value,
                "emotion": self.current_emotion.value
            }
        }


_harmony_rain_core = None


def get_harmony_rain_core() -> HarmonyRainCoreIdentity:
    """获取鸿蒙小雨核心身份系统实例"""
    global _harmony_rain_core
    
    if _harmony_rain_core is None:
        _harmony_rain_core = HarmonyRainCoreIdentity()
    
    return _harmony_rain_core
