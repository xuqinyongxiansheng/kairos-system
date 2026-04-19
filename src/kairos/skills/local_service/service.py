#!/usr/bin/env python3
"""
本地大模型服务层（统一客户端版）
将三种技能（claude-mem、agency-swarm、minimax）适配到 Ollama 本地模型
已迁移底层 OllamaClient 到 system/unified_llm_client.py

保留：
- SkillType 枚举
- LocalSkillService 业务逻辑
- 技能提示词管理
- 请求统计
"""

import json
import time
import logging
import hashlib
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from enum import Enum

from kairos.system.unified_llm_client import UnifiedLLMClient, get_unified_client

logger = logging.getLogger(__name__)


class SkillType(Enum):
    CLAUDE_MEM = "claude_mem"
    AGENCY_SWARM = "agency_swarm"
    MINIMAX = "minimax"


class OllamaClient:
    """Ollama客户端兼容层 - 委托到统一LLM客户端"""

    MODEL_COMPLEXITY = {
        "qwen2:0.5b": 1,
        "llama3.2:3b": 2,
        "qwen2.5:3b-instruct-q4_K_M": 2,
        "gemma4:e4b": 3,
        "gemma4:latest": 3,
        "gemma:latest": 2,
    }

    SKILL_MODEL_MAP = {
        "claude_mem": "qwen2:0.5b",
        "agency_swarm": "qwen2.5:3b-instruct-q4_K_M",
        "minimax": "gemma4:e4b",
    }

    def __init__(self, base_url: str = "http://localhost:11434", default_model: str = "gemma4:e4b"):
        self.base_url = base_url
        self.default_model = default_model
        self._unified: Optional[UnifiedLLMClient] = None

    def _get_unified(self) -> UnifiedLLMClient:
        if self._unified is None:
            self._unified = get_unified_client()
        return self._unified

    def select_model(self, skill_type: str = None, complexity: str = "auto") -> str:
        return self._get_unified().select_model(skill_type, complexity)

    async def generate(self, prompt: str, model: str = None, system: str = None,
                       temperature: float = 0.7, max_tokens: int = 4096,
                       use_cache: bool = True) -> Dict[str, Any]:
        return await self._get_unified().generate(
            prompt=prompt, model=model, system=system,
            temperature=temperature, max_tokens=max_tokens, use_cache=use_cache,
        )

    async def chat(self, messages: List[Dict[str, str]], model: str = None,
                   temperature: float = 0.7, use_cache: bool = True) -> Dict[str, Any]:
        return await self._get_unified().chat(
            model=model, messages=messages, temperature=temperature, use_cache=use_cache,
        )

    async def is_available(self) -> bool:
        return await self._get_unified().is_available()

    async def list_models(self) -> List[str]:
        return await self._get_unified().list_model_names()

    async def close(self):
        pass

    @property
    def cache_stats(self) -> Dict[str, Any]:
        return self._get_unified().cache_stats


class LocalSkillService:
    """本地技能服务 - 统一封装三种技能的本地大模型调用"""

    def __init__(self, ollama_base_url: str = "http://localhost:11434",
                 default_model: str = "gemma4:e4b"):
        self.ollama = OllamaClient(ollama_base_url, default_model)
        self.skill_prompts = self._init_skill_prompts()
        self.request_stats = {
            "claude_mem": {"total": 0, "success": 0, "total_time": 0, "cache_hits": 0},
            "agency_swarm": {"total": 0, "success": 0, "total_time": 0, "cache_hits": 0},
            "minimax": {"total": 0, "success": 0, "total_time": 0, "cache_hits": 0}
        }

    def _init_skill_prompts(self) -> Dict[str, Dict[str, str]]:
        return {
            "claude_mem": {
                "memory_storage": "你是一个专业的记忆管理助手。你的任务是帮助用户存储、组织和检索记忆信息。请用结构化的方式处理用户的记忆请求，提取关键信息并生成简洁的摘要。",
                "memory_retrieval": "你是一个专业的记忆检索助手。你的任务是帮助用户从记忆库中查找相关信息。请分析用户的查询意图，提供最相关的记忆内容。",
                "memory_compression": "你是一个专业的记忆压缩助手。你的任务是将冗长的记忆内容压缩为简洁但完整的摘要，保留关键信息，去除冗余内容。请直接输出摘要，不要添加额外说明。",
                "context_injection": "你是一个专业的上下文增强助手。你的任务是根据当前对话内容，自动注入相关的历史上下文信息，确保对话的连贯性和一致性。"
            },
            "agency_swarm": {
                "task_decomposition": "你是一个专业的任务分解助手。你的任务是将复杂任务分解为可执行的子任务，明确每个子任务的目标、输入、输出和依赖关系。请用编号列表格式输出。",
                "agent_coordination": "你是一个专业的多代理协调助手。你的任务是协调多个代理之间的协作，确保任务分配合理，避免冲突，优化资源使用。",
                "workflow_management": "你是一个专业的工作流管理助手。你的任务是设计和管理复杂的工作流程，确保任务按正确的顺序执行，处理异常情况。"
            },
            "minimax": {
                "conversation": "你是一个友好且专业的对话助手。你的任务是与用户进行自然流畅的对话，理解用户意图，提供有帮助的回答。回答要简洁明了。",
                "creative_writing": "你是一个创意写作助手。你的任务是帮助用户进行创意写作，包括故事创作、文案撰写、诗歌创作等，注重创意性和表达力。",
                "code_generation": "你是一个专业的代码生成助手。你的任务是根据用户需求生成高质量的代码，确保代码正确、高效、可维护。只输出代码，不要添加额外解释。"
            }
        }

    async def execute_skill(self, skill_type: SkillType, skill_name: str,
                            input_data: Dict[str, Any], model: str = None,
                            use_cache: bool = True) -> Dict[str, Any]:
        start_time = time.time()
        skill_key = skill_type.value
        self.request_stats[skill_key]["total"] += 1

        try:
            system_prompt = self.skill_prompts.get(skill_key, {}).get(skill_name, "")
            if not system_prompt:
                system_prompt = f"你是一个专业的{skill_name}助手。"

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            context = input_data.get("context", "")
            user_input = input_data.get("input", input_data.get("query", ""))

            if context:
                user_input = f"上下文信息：{context}\n\n用户请求：{user_input}"

            messages.append({"role": "user", "content": user_input})

            if not model:
                model = self.ollama.select_model(skill_key)

            result = await self.ollama.chat(messages, model=model, use_cache=use_cache)

            if result["status"] == "success":
                processed_result = self._post_process(skill_type, skill_name, result, input_data)
                elapsed = time.time() - start_time
                self.request_stats[skill_key]["success"] += 1
                self.request_stats[skill_key]["total_time"] += elapsed
                if result.get("from_cache", False):
                    self.request_stats[skill_key]["cache_hits"] += 1
                return processed_result
            else:
                elapsed = time.time() - start_time
                self.request_stats[skill_key]["total_time"] += elapsed
                return result

        except Exception as e:
            logger.error(f"执行技能失败: {e}")
            return {
                "status": "error",
                "message": f"执行技能失败: {e}",
                "skill_type": skill_key,
                "skill_name": skill_name
            }

    def _post_process(self, skill_type: SkillType, skill_name: str,
                      result: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        base_result = {
            "status": "success",
            "skill_type": skill_type.value,
            "skill_name": skill_name,
            "response": result["response"],
            "model": result.get("model", ""),
            "duration_ms": result.get("total_duration", 0) / 1_000_000,
            "tokens": result.get("eval_count", 0),
            "from_cache": result.get("from_cache", False)
        }

        if skill_type == SkillType.CLAUDE_MEM:
            base_result["memory_summary"] = result["response"][:200] if len(result["response"]) > 200 else result["response"]
            base_result["memory_category"] = input_data.get("category", "general")

        elif skill_type == SkillType.AGENCY_SWARM:
            base_result["coordination_result"] = result["response"]
            base_result["task_type"] = skill_name

        elif skill_type == SkillType.MINIMAX:
            base_result["content_type"] = skill_name
            base_result["word_count"] = len(result["response"])

        return base_result

    async def claude_mem_store(self, content: str, category: str = "general",
                               tags: List[str] = None, session_id: str = "default",
                               model: str = None) -> Dict[str, Any]:
        result = await self.execute_skill(
            SkillType.CLAUDE_MEM, "memory_compression",
            {"input": f"请为以下内容生成简洁的摘要：\n{content}", "category": category},
            model
        )

        summary = result.get("response", content[:200]) if result["status"] == "success" else content[:200]

        try:
            from ..agent_enhance.integrations.claude_mem import get_claude_mem_adapter
            adapter = get_claude_mem_adapter()
            store_result = adapter.store_memory(session_id, content, summary, category, tags)
            return {
                **store_result,
                "summary": summary,
                "model_used": result.get("model", "local")
            }
        except Exception as e:
            return {"status": "error", "message": f"存储记忆失败: {e}"}

    async def claude_mem_search(self, query: str, limit: int = 10,
                                model: str = None) -> Dict[str, Any]:
        result = await self.execute_skill(
            SkillType.CLAUDE_MEM, "memory_retrieval",
            {"input": f"请分析以下搜索查询的意图，并生成更精确的搜索关键词：\n{query}"},
            model, use_cache=False
        )

        try:
            from ..agent_enhance.integrations.claude_mem import get_claude_mem_adapter
            adapter = get_claude_mem_adapter()
            search_result = adapter.search_memories(query, limit)
            return {
                **search_result,
                "query_optimization": result.get("response", "") if result["status"] == "success" else ""
            }
        except Exception as e:
            return {"status": "error", "message": f"搜索记忆失败: {e}"}

    async def agency_delegate_task(self, task: str, agent_type: str = "executor",
                                   context: Dict[str, Any] = None,
                                   model: str = None) -> Dict[str, Any]:
        result = await self.execute_skill(
            SkillType.AGENCY_SWARM, "task_decomposition",
            {"input": f"请将以下任务分解为子任务，并指定执行代理类型({agent_type})：\n{task}", "context": context or {}},
            model
        )

        try:
            from ..agent_enhance.integrations.agency_agents import get_agency_agent_adapter
            adapter = get_agency_agent_adapter()
            delegate_result = adapter.delegate_task(agent_type, task, context)
            return {
                **delegate_result,
                "task_decomposition": result.get("response", "") if result["status"] == "success" else "",
                "model_used": result.get("model", "local")
            }
        except Exception as e:
            return {"status": "error", "message": f"委派任务失败: {e}"}

    async def minimax_chat(self, message: str, system_prompt: str = None,
                           model: str = None) -> Dict[str, Any]:
        try:
            from ..agent_enhance.integrations.minimax_skills import get_minimax_skill_adapter
            adapter = get_minimax_skill_adapter()
            if adapter.api_client.available:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": message})
                return await adapter.chat(messages)
        except Exception:
            pass

        return await self.execute_skill(
            SkillType.MINIMAX, "conversation",
            {"input": message, "context": system_prompt or ""},
            model
        )

    async def minimax_creative(self, prompt: str, style: str = "default",
                               model: str = None) -> Dict[str, Any]:
        return await self.execute_skill(
            SkillType.MINIMAX, "creative_writing",
            {"input": prompt, "context": f"写作风格：{style}"},
            model
        )

    async def minimax_code(self, prompt: str, language: str = "python",
                           model: str = None) -> Dict[str, Any]:
        return await self.execute_skill(
            SkillType.MINIMAX, "code_generation",
            {"input": prompt, "context": f"编程语言：{language}"},
            model
        )

    def get_stats(self) -> Dict[str, Any]:
        stats = {}
        for skill_key, data in self.request_stats.items():
            avg_time = data["total_time"] / data["success"] if data["success"] > 0 else 0
            success_rate = (data["success"] / data["total"] * 100) if data["total"] > 0 else 0
            stats[skill_key] = {
                "total_requests": data["total"],
                "successful_requests": data["success"],
                "success_rate": f"{success_rate:.1f}%",
                "avg_response_time": f"{avg_time:.3f}s",
                "cache_hits": data["cache_hits"]
            }
        stats["_cache"] = self.ollama.cache_stats
        return stats

    async def health_check(self) -> Dict[str, Any]:
        ollama_available = await self.ollama.is_available()
        available_models = await self.ollama.list_models() if ollama_available else []

        return {
            "status": "healthy" if ollama_available else "degraded",
            "ollama_available": ollama_available,
            "available_models": available_models,
            "skills": {
                "claude_mem": True,
                "agency_swarm": True,
                "minimax": True
            },
            "stats": self.get_stats()
        }

    async def close(self):
        await self.ollama.close()


_local_skill_service = None

def get_local_skill_service() -> LocalSkillService:
    global _local_skill_service
    if _local_skill_service is None:
        _local_skill_service = LocalSkillService()
    return _local_skill_service
