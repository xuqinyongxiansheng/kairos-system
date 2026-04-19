#!/usr/bin/env python3
"""
Minimax Skills 适配器
深度集成 MiniMax AI 技能系统和 mini-agent
"""

import os
import json
import logging
import httpx
from typing import Dict, Any, Optional, List

from ..professional_agents.base_agent import ProfessionalAgent, get_agent_registry

logger = logging.getLogger(__name__)


class MinimaxAPIClient:
    """MiniMax API 客户端"""
    
    def __init__(self, api_key: str = None, base_url: str = "https://api.minimax.chat"):
        self.api_key = api_key or os.environ.get("MINIMAX_API_KEY", "")
        self.base_url = base_url
        self.available = bool(self.api_key)
    
    async def chat_completion(self, messages: List[Dict[str, str]], model: str = "MiniMax-Text-01",
                              temperature: float = 0.7, max_tokens: int = 4096) -> Dict[str, Any]:
        """聊天补全"""
        if not self.available:
            return {
                "status": "error",
                "message": "MiniMax API Key 未配置，请设置环境变量 MINIMAX_API_KEY"
            }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1/text/chatcompletion_v2",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    },
                    timeout=60.0
                )
                if response.status_code == 200:
                    return {
                        "status": "success",
                        "data": response.json()
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"API 请求失败: {response.status_code}",
                        "detail": response.text
                    }
        except Exception as e:
            return {
                "status": "error",
                "message": f"API 请求异常: {e}"
            }
    
    async def vision_analysis(self, image_url: str = None, image_base64: str = None,
                               prompt: str = "请描述这张图片") -> Dict[str, Any]:
        """视觉分析"""
        if not self.available:
            return {
                "status": "error",
                "message": "MiniMax API Key 未配置"
            }
        
        messages = [{"role": "user", "content": prompt}]
        if image_url:
            messages[0]["content"] = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        
        return await self.chat_completion(messages, model="MiniMax-VL-01")


class MinimaxSkillAdapter:
    """Minimax Skills 适配器 - 深度集成 MiniMax AI 技能系统"""
    
    def __init__(self, minimax_dir: str = "project/vendor/mini-agent"):
        self.minimax_dir = minimax_dir
        self.api_client = MinimaxAPIClient()
        self.skills = {}
        self.agents = {}
        self._check_mini_agent()
        self._init_skills()
        self._init_agents()
    
    def _check_mini_agent(self):
        """检查 mini-agent 是否可用"""
        self.mini_agent_available = os.path.exists(self.minimax_dir)
        if self.mini_agent_available:
            logger.info("mini-agent 仓库已就绪")
        else:
            logger.info("mini-agent 仓库未找到，使用内置 MiniMax 技能系统")
    
    def _init_skills(self):
        """初始化技能"""
        self.skills["minimax_conversation"] = {
            "name": "MiniMax 对话技能",
            "description": "基于 MiniMax Text-01 模型的高质量对话能力",
            "version": "1.0.0",
            "model": "MiniMax-Text-01",
            "author": "MiniMax AI"
        }
        self.skills["minimax_vision"] = {
            "name": "MiniMax 视觉技能",
            "description": "基于 MiniMax VL-01 模型的视觉理解能力",
            "version": "1.0.0",
            "model": "MiniMax-VL-01",
            "author": "MiniMax AI"
        }
        self.skills["minimax_creative"] = {
            "name": "MiniMax 创意技能",
            "description": "基于 MiniMax 模型的创意内容生成能力",
            "version": "1.0.0",
            "model": "MiniMax-Text-01",
            "author": "MiniMax AI"
        }
        self.skills["minimax_code"] = {
            "name": "MiniMax 代码技能",
            "description": "基于 MiniMax 模型的代码生成和理解能力",
            "version": "1.0.0",
            "model": "MiniMax-Text-01",
            "author": "MiniMax AI"
        }
    
    def _init_agents(self):
        """初始化代理"""
        self.agents["chat_agent"] = {
            "name": "MiniMax 对话代理",
            "description": "基于 MiniMax 模型的对话代理，支持多轮对话和上下文理解",
            "skills": ["conversation", "summarization", "question_answering", "translation"],
            "capabilities": ["text_generation", "context_understanding", "multi_turn_dialogue", "streaming_response"]
        }
        self.agents["vision_agent"] = {
            "name": "MiniMax 视觉代理",
            "description": "基于 MiniMax VL-01 模型的视觉理解代理",
            "skills": ["image_analysis", "object_detection", "scene_understanding", "ocr"],
            "capabilities": ["image_processing", "visual_understanding", "multimodal_analysis"]
        }
        self.agents["creative_agent"] = {
            "name": "MiniMax 创意代理",
            "description": "基于 MiniMax 模型的创意内容生成代理",
            "skills": ["creative_writing", "brainstorming", "storytelling", "copywriting"],
            "capabilities": ["content_generation", "style_adaptation", "tone_control"]
        }
    
    async def chat(self, messages: List[Dict[str, str]], model: str = "MiniMax-Text-01",
                   temperature: float = 0.7) -> Dict[str, Any]:
        """聊天接口"""
        return await self.api_client.chat_completion(messages, model, temperature)
    
    async def analyze_image(self, image_url: str = None, image_base64: str = None,
                            prompt: str = "请描述这张图片") -> Dict[str, Any]:
        """图像分析接口"""
        return await self.api_client.vision_analysis(image_url, image_base64, prompt)
    
    def list_skills(self) -> List[str]:
        """列出所有技能"""
        return list(self.skills.keys())
    
    def get_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """获取技能详情"""
        return self.skills.get(skill_name)
    
    def convert_to_professional_agent(self, agent_name: str) -> Optional[ProfessionalAgent]:
        """将 minimax agent 转换为专业代理"""
        agent_data = self.agents.get(agent_name)
        if not agent_data:
            return None
        
        adapter = self
        
        class MinimaxProfessionalAgent(ProfessionalAgent):
            def __init__(self, agent_data, adapter_ref):
                super().__init__(
                    agent_id=f"minimax_{agent_name}",
                    name=agent_data["name"],
                    description=agent_data["description"]
                )
                for skill in agent_data.get("skills", []):
                    self.add_skill(skill)
                for capability in agent_data.get("capabilities", []):
                    self.add_capability(capability)
                self._adapter = adapter_ref
            
            async def process_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
                """处理任务"""
                ctx = context or {}
                
                if "对话" in task or "聊天" in task or "chat" in task.lower():
                    messages = ctx.get("messages", [{"role": "user", "content": task}])
                    model = ctx.get("model", "MiniMax-Text-01")
                    temperature = ctx.get("temperature", 0.7)
                    return await self._adapter.chat(messages, model, temperature)
                
                elif "图像" in task or "视觉" in task or "vision" in task.lower() or "image" in task.lower():
                    image_url = ctx.get("image_url")
                    image_base64 = ctx.get("image_base64")
                    prompt = ctx.get("prompt", task)
                    return await self._adapter.analyze_image(image_url, image_base64, prompt)
                
                elif "技能" in task or "skill" in task.lower():
                    if "列表" in task or "list" in task.lower():
                        return {
                            "status": "success",
                            "skills": self._adapter.list_skills(),
                            "skills_detail": {k: v["description"] for k, v in self._adapter.skills.items()}
                        }
                    else:
                        skill_name = ctx.get("skill_name")
                        if skill_name:
                            return {
                                "status": "success",
                                "skill": self._adapter.get_skill(skill_name)
                            }
                        return {
                            "status": "success",
                            "skills": self._adapter.list_skills()
                        }
                
                else:
                    # 默认使用对话接口处理
                    messages = [{"role": "user", "content": task}]
                    if ctx.get("system_prompt"):
                        messages.insert(0, {"role": "system", "content": ctx["system_prompt"]})
                    return await self._adapter.chat(messages)
        
        return MinimaxProfessionalAgent(agent_data, adapter)
    
    def register_all_agents(self):
        """注册所有 minimax agents"""
        agent_registry = get_agent_registry()
        for agent_name in self.agents:
            agent = self.convert_to_professional_agent(agent_name)
            if agent:
                agent_registry.register_agent(agent)
                logger.info(f"注册 Minimax Agent: {agent_name}")


_minimax_skill_adapter = None

def get_minimax_skill_adapter() -> MinimaxSkillAdapter:
    """获取 Minimax 技能适配器实例"""
    global _minimax_skill_adapter
    if _minimax_skill_adapter is None:
        _minimax_skill_adapter = MinimaxSkillAdapter()
    return _minimax_skill_adapter