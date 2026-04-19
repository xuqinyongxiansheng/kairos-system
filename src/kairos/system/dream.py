#!/usr/bin/env python3
"""
做梦功能模块 - 基于 claudecode 实现模拟认知处理和信息重组
"""

import asyncio
import random
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DreamType(Enum):
    """做梦类型枚举"""
    NORMAL = "normal"
    LUCID = "lucid"
    NIGHTMARE = "nightmare"
    RECURRING = "recurring"
    PROPHETIC = "prophetic"


class DreamStage(Enum):
    """做梦阶段枚举"""
    REM = "rem"
    NON_REM_1 = "non_rem_1"
    NON_REM_2 = "non_rem_2"
    NON_REM_3 = "non_rem_3"


class DreamElement:
    """做梦元素类"""
    
    def __init__(self, element_type: str, content: Any, significance: float = 0.5):
        self.element_type = element_type
        self.content = content
        self.significance = significance
        self.connections = []
    
    def add_connection(self, element_id: str, connection_type: str, strength: float):
        """添加元素间的连接"""
        self.connections.append({
            "element_id": element_id,
            "connection_type": connection_type,
            "strength": strength
        })
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "element_type": self.element_type,
            "content": self.content,
            "significance": self.significance,
            "connections": self.connections
        }


class Dream:
    """做梦类"""
    
    def __init__(self, dream_type: DreamType = DreamType.NORMAL):
        self.id = str(uuid.uuid4())
        self.type = dream_type
        self.stage = DreamStage.REM
        self.elements = {}
        self.narration = ""
        self.emotional_tone = "neutral"
        self.start_time = datetime.now()
        self.duration = random.randint(5, 30)
        self.significance = random.random()
        self.memory_connections = []
    
    def add_element(self, element_id: str, element: DreamElement):
        """添加做梦元素"""
        self.elements[element_id] = element
    
    def connect_elements(self, element1_id: str, element2_id: str, connection_type: str, strength: float):
        """连接两个做梦元素"""
        if element1_id in self.elements and element2_id in self.elements:
            self.elements[element1_id].add_connection(element2_id, connection_type, strength)
            self.elements[element2_id].add_connection(element1_id, connection_type, strength)
    
    def connect_to_memory(self, memory_id: str, strength: float, connection_type: str = "related"):
        """连接到记忆"""
        self.memory_connections.append({
            "memory_id": memory_id,
            "strength": strength,
            "connection_type": connection_type
        })
    
    def generate_narration(self):
        """生成做梦叙述"""
        elements_list = list(self.elements.values())
        if not elements_list:
            self.narration = "一个模糊的梦，难以描述具体内容。"
            return
        
        elements_list.sort(key=lambda x: x.significance, reverse=True)
        
        narration_parts = []
        
        if elements_list:
            main_element = elements_list[0]
            narration_parts.append(f"我梦见{main_element.content}")
        
        for i in range(1, min(3, len(elements_list))):
            element = elements_list[i]
            narration_parts.append(f"，还有{element.content}")
        
        if self.emotional_tone == "positive":
            narration_parts.append("，感觉很愉快")
        elif self.emotional_tone == "negative":
            narration_parts.append("，感觉有些不安")
        
        self.narration = "".join(narration_parts) + "。"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.id,
            "type": self.type.value,
            "stage": self.stage.value,
            "elements": {k: v.to_dict() for k, v in self.elements.items()},
            "narration": self.narration,
            "emotional_tone": self.emotional_tone,
            "start_time": self.start_time.isoformat(),
            "duration": self.duration,
            "significance": self.significance,
            "memory_connections": self.memory_connections
        }


class DreamGenerator:
    """做梦生成器"""
    
    def __init__(self, memory_system=None):
        self.memory_system = memory_system
        self.dreams = []
        self.cognitive_patterns = self._load_cognitive_patterns()
    
    def _load_cognitive_patterns(self) -> Dict[str, List[str]]:
        """加载认知模式"""
        return {
            "themes": ["探索", "学习", "创造", "解决问题", "社交互动", "自我反思"],
            "emotions": ["快乐", "好奇", "焦虑", "惊讶", "平静", "兴奋"],
            "settings": ["熟悉的地方", "陌生的环境", "未来场景", "过去回忆", "抽象空间"],
            "characters": ["自己", "熟悉的人", "陌生人", "虚构角色", "动物"],
            "actions": ["发现", "创造", "学习", "交流", "解决问题", "探索"]
        }
    
    def _extract_recent_memories(self, hours: int = 24) -> List[Dict[str, Any]]:
        """提取最近的记忆"""
        if not self.memory_system:
            return []
        
        try:
            memories = []
            cutoff_time = time.time() - (hours * 3600)
            
            if hasattr(self.memory_system, 'memories'):
                for memory_id, memory in self.memory_system.memories.items():
                    if memory.timestamp >= cutoff_time:
                        memories.append({
                            "id": memory_id,
                            "content": memory.content,
                            "metadata": memory.metadata.__dict__,
                            "timestamp": memory.timestamp
                        })
            
            return memories
            
        except Exception as e:
            logger.error(f"提取记忆失败：{e}")
            return []
    
    def _generate_dream_elements(self, memories: List[Dict[str, Any]]) -> Dict[str, DreamElement]:
        """基于记忆生成做梦元素"""
        elements = {}
        
        if memories:
            for i, memory in enumerate(memories[:5]):
                element_id = f"element_{i}"
                content = str(memory.get("content", "未知内容"))
                
                if len(content) > 50:
                    content = content[:50] + "..."
                
                significance = random.uniform(0.3, 1.0)
                element = DreamElement("memory_based", content, significance)
                elements[element_id] = element
        
        for i in range(random.randint(1, 3)):
            element_id = f"random_element_{i}"
            theme = random.choice(self.cognitive_patterns["themes"])
            setting = random.choice(self.cognitive_patterns["settings"])
            content = f"{theme}在{setting}"
            significance = random.uniform(0.2, 0.8)
            element = DreamElement("random", content, significance)
            elements[element_id] = element
        
        return elements
    
    def _connect_elements(self, elements: Dict[str, DreamElement]):
        """连接做梦元素"""
        element_ids = list(elements.keys())
        
        for i, elem_id1 in enumerate(element_ids):
            for j, elem_id2 in enumerate(element_ids):
                if i != j and random.random() < 0.3:
                    connection_types = ["related_to", "part_of", "similar_to", "causes", "follows"]
                    connection_type = random.choice(connection_types)
                    strength = random.uniform(0.1, 1.0)
                    
                    elements[elem_id1].add_connection(elem_id2, connection_type, strength)
    
    def _connect_to_memories(self, dream: Dream, memories: List[Dict[str, Any]]):
        """连接做梦到记忆"""
        for memory in memories[:3]:
            strength = random.uniform(0.2, 1.0)
            dream.connect_to_memory(memory["id"], strength)
    
    async def generate_dream(self, dream_type: Optional[DreamType] = None) -> Dream:
        """生成做梦"""
        try:
            if dream_type is None:
                dream_type = random.choice([t for t in DreamType])
            
            dream = Dream(dream_type)
            
            emotions = ["positive", "negative", "neutral"]
            dream.emotional_tone = random.choice(emotions)
            
            stages = [DreamStage.REM, DreamStage.NON_REM_2]
            dream.stage = random.choice(stages)
            
            memories = self._extract_recent_memories()
            
            elements = self._generate_dream_elements(memories)
            
            for elem_id, element in elements.items():
                dream.add_element(elem_id, element)
            
            self._connect_elements(elements)
            
            self._connect_to_memories(dream, memories)
            
            dream.generate_narration()
            
            self.dreams.append(dream)
            
            logger.info(f"生成做梦：{dream.type.value}, 持续时间：{dream.duration}分钟")
            return dream
            
        except Exception as e:
            logger.error(f"生成做梦失败：{e}")
            raise
    
    async def analyze_dream(self, dream: Dream) -> Dict[str, Any]:
        """分析做梦"""
        analysis = {
            "dream_id": dream.id,
            "type": dream.type.value,
            "emotional_tone": dream.emotional_tone,
            "element_count": len(dream.elements),
            "memory_connections": len(dream.memory_connections),
            "significance_score": dream.significance,
            "interpretation": self._generate_interpretation(dream)
        }
        
        return analysis
    
    def _generate_interpretation(self, dream: Dream) -> str:
        """生成做梦解释"""
        interpretations = []
        
        if dream.type == DreamType.NORMAL:
            interpretations.append("这是一个普通的梦，反映了您近期的经历和思考。")
        elif dream.type == DreamType.LUCID:
            interpretations.append("您在梦中意识到自己在做梦，这显示了您的自我意识能力。")
        elif dream.type == DreamType.NIGHTMARE:
            interpretations.append("这个噩梦可能反映了您潜意识中的焦虑或担忧。")
        elif dream.type == DreamType.RECURRING:
            interpretations.append("这个重复出现的梦可能暗示着未解决的问题或模式。")
        elif dream.type == DreamType.PROPHETIC:
            interpretations.append("这个梦可能包含对未来的象征性预示。")
        
        if dream.emotional_tone == "positive":
            interpretations.append("梦中的积极情绪表明您的心理状态良好。")
        elif dream.emotional_tone == "negative":
            interpretations.append("梦中的负面情绪可能反映了当前的压力或挑战。")
        
        if len(dream.elements) > 5:
            interpretations.append("梦的内容丰富，显示了活跃的思维活动。")
        
        if len(dream.memory_connections) > 0:
            interpretations.append("梦与您的记忆有明显关联，表明记忆正在被处理和重组。")
        
        return " ".join(interpretations)
    
    async def get_dream_history(self, days: int = 7) -> List[Dream]:
        """获取做梦历史"""
        cutoff_time = datetime.now() - timedelta(days=days)
        return [dream for dream in self.dreams if dream.start_time >= cutoff_time]


class CognitiveProcessor:
    """认知处理器"""
    
    def __init__(self):
        self.pattern_recognizer = PatternRecognizer()
        self.association_builder = AssociationBuilder()
        self.metaphor_generator = MetaphorGenerator()
    
    async def process_dream(self, dream: Dream) -> Dict[str, Any]:
        """处理做梦，进行认知分析"""
        try:
            patterns = await self.pattern_recognizer.recognize_patterns(dream)
            associations = await self.association_builder.build_associations(dream)
            metaphors = await self.metaphor_generator.generate_metaphors(dream)
            
            return {
                "patterns": patterns,
                "associations": associations,
                "metaphors": metaphors,
                "cognitive_analysis": self._generate_cognitive_analysis(dream, patterns, associations)
            }
            
        except Exception as e:
            logger.error(f"认知处理失败：{e}")
            raise
    
    def _generate_cognitive_analysis(self, dream: Dream, patterns: List[str], associations: List[Dict[str, Any]]) -> str:
        """生成认知分析"""
        analysis_parts = []
        
        if patterns:
            analysis_parts.append(f"识别到的认知模式：{', '.join(patterns)}")
        
        if associations:
            analysis_parts.append(f"建立了{len(associations)}个重要关联")
        
        if dream.significance > 0.7:
            analysis_parts.append("这个梦具有较高的认知重要性")
        
        return " ".join(analysis_parts)


class PatternRecognizer:
    """模式识别器"""
    
    def __init__(self):
        self.pattern_templates = [
            {"name": "问题解决", "keywords": ["解决", "寻找", "发现", "答案", "解决方案"]},
            {"name": "探索", "keywords": ["探索", "发现", "旅行", "新地方", "未知"]},
            {"name": "学习", "keywords": ["学习", "了解", "理解", "发现", "知识"]},
            {"name": "社交互动", "keywords": ["交谈", "交流", "朋友", "家人", "关系"]},
            {"name": "创造", "keywords": ["创造", "发明", "设计", "构建", "制作"]}
        ]
    
    async def recognize_patterns(self, dream: Dream) -> List[str]:
        """识别做梦中的模式"""
        patterns = []
        
        text_to_analyze = dream.narration
        
        for element in dream.elements.values():
            text_to_analyze += f" {element.content}"
        
        for pattern in self.pattern_templates:
            for keyword in pattern["keywords"]:
                if keyword in text_to_analyze:
                    patterns.append(pattern["name"])
                    break
        
        return list(set(patterns))


class AssociationBuilder:
    """关联构建器"""
    
    def __init__(self):
        self.association_types = ["因果", "相似", "对比", "时序", "层级"]
    
    async def build_associations(self, dream: Dream) -> List[Dict[str, Any]]:
        """构建元素间的关联"""
        associations = []
        
        for element_id, element in dream.elements.items():
            for connection in element.connections:
                if connection["strength"] > 0.5:
                    associations.append({
                        "source_element": element_id,
                        "target_element": connection["element_id"],
                        "connection_type": connection["connection_type"],
                        "strength": connection["strength"]
                    })
        
        return associations[:5]


class MetaphorGenerator:
    """隐喻生成器"""
    
    def __init__(self):
        self.metaphor_templates = [
            "就像{source}一样，{target}也具有{quality}",
            "{source}象征着{target}的{quality}",
            "{target}如同{source}，都展现出{quality}"
        ]
    
    async def generate_metaphors(self, dream: Dream) -> List[str]:
        """生成隐喻"""
        metaphors = []
        
        elements_list = sorted(dream.elements.values(), key=lambda x: x.significance, reverse=True)
        
        if len(elements_list) >= 2:
            elem1 = elements_list[0]
            elem2 = elements_list[1]
            
            qualities = ["深度", "复杂性", "重要性", "意义", "关联性"]
            quality = random.choice(qualities)
            
            template = random.choice(self.metaphor_templates)
            metaphor = template.format(
                source=elem1.content,
                target=elem2.content,
                quality=quality
            )
            
            metaphors.append(metaphor)
        
        return metaphors


# 全局做梦模块实例
dream_module = DreamGenerator()
cognitive_processor = CognitiveProcessor()
