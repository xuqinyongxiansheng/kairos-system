#!/usr/bin/env python3
"""
Gemma4 大脑兼容层

已迁移到 system/unified_llm_client.py
此文件保留以维持向后兼容性，所有调用自动委托到统一客户端

使用方式（不变）：
    from kairos.system.gemma4_brain import get_gemma4_brain
    brain = await get_gemma4_brain()
    response = await brain.chat("你好")
"""

from kairos.system.unified_llm_client import (
    UnifiedLLMClient,
    get_unified_client,
)

import logging
from typing import Optional

logger = logging.getLogger("Gemma4Brain")

logger.info("gemma4_brain.py 已委托到 unified_llm_client.py，向后兼容")


class Gemma4BrainError(Exception):
    def __init__(self, message: str, error_type: str = "unknown"):
        self.message = message
        self.error_type = error_type
        super().__init__(message)


class Gemma4Brain:
    """Gemma4大脑兼容层 - 委托到统一客户端"""

    DEFAULT_MODEL = "gemma4:e4b"
    DEFAULT_HOST = "http://127.0.0.1:11434"
    DEFAULT_TIMEOUT = 180.0
    MAX_RETRIES = 2
    MAX_HISTORY_MESSAGES = 20
    MAX_CONTEXT_TOKENS = 4096

    def __init__(self, model: str = DEFAULT_MODEL, host: str = DEFAULT_HOST,
                 timeout: float = DEFAULT_TIMEOUT, max_history: int = MAX_HISTORY_MESSAGES):
        self.model = model
        self.host = host
        self.timeout = timeout
        self.max_history = max_history
        self._client: Optional[UnifiedLLMClient] = None

    def _get_client(self) -> UnifiedLLMClient:
        if self._client is None:
            self._client = get_unified_client()
        return self._client

    async def call_llm(self, user_prompt: str, system_prompt: str = None,
                       tools: list = None, history_messages: list = None,
                       **kwargs) -> dict:
        client = self._get_client()
        model = kwargs.get("model", self.model)
        try:
            result = await client.chat(
                model=model,
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                use_cache=False,
                tools=tools,
            )
            if result.get("status") == "success":
                return {"message": {"content": result["response"]}}
            raise Gemma4BrainError(result.get("response", "调用失败"), "llm_error")
        except Gemma4BrainError:
            raise
        except Exception as e:
            raise Gemma4BrainError(str(e), "unknown") from e

    async def chat(self, user_prompt: str, system_prompt: str = "你是智能机器人大脑，回答简洁专业。") -> str:
        try:
            response = await self.call_llm(user_prompt, system_prompt)
            return response.get("message", {}).get("content", "")
        except Gemma4BrainError as e:
            return f"[错误] {e.message}"

    async def decision(self, user_prompt: str, system_prompt: str) -> dict:
        client = self._get_client()
        return await client.decision(user_prompt, system_prompt, model=self.model)

    async def memory_summary(self, content: str) -> str:
        client = self._get_client()
        return await client.memory_summary(content, model=self.model)

    async def tool_call(self, user_prompt: str, system_prompt: str, tools: list) -> dict:
        client = self._get_client()
        return await client.tool_call(user_prompt, system_prompt, tools, model=self.model)

    async def is_available(self) -> bool:
        client = self._get_client()
        return await client.is_available()

    async def list_models(self) -> list:
        client = self._get_client()
        return await client.list_models()

    async def close(self):
        pass


_gemma4_brain: Optional[Gemma4Brain] = None


async def get_gemma4_brain(**kwargs) -> Gemma4Brain:
    global _gemma4_brain
    if _gemma4_brain is None:
        _gemma4_brain = Gemma4Brain(**kwargs)
    return _gemma4_brain


def get_gemma4_brain_sync() -> Gemma4Brain:
    global _gemma4_brain
    if _gemma4_brain is None:
        _gemma4_brain = Gemma4Brain()
    return _gemma4_brain
