#!/usr/bin/env python3
"""
统一 LLM 客户端（UnifiedLLMClient）

合并三套客户端的全部优秀特性：
- system/llm_client.py: 熔断器 + 重试 + 统计
- system/gemma4_brain.py: httpx异步 + 连接池 + 消息构建 + JSON解析
- skills/local_service/service.py: LRU缓存 + Semaphore并发 + 智能模型选择

统一接口，向后兼容，一处定义全局使用
"""

import os
import json
import time
import hashlib
import asyncio
import logging
import threading
from typing import Dict, Any, Optional, List, Tuple, Literal
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

import httpx

from kairos.system.config import settings

logger = logging.getLogger("UnifiedLLMClient")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 0.5
    max_delay: float = 10.0
    backoff_factor: float = 2.0


@dataclass
class CircuitConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_attempts: int = 3


class CircuitBreaker:
    """熔断器"""

    def __init__(self, config: CircuitConfig = None):
        self.config = config or CircuitConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self._lock = threading.RLock()

    def should_allow(self) -> bool:
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            elif self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.config.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    return True
                return False
            elif self.state == CircuitState.HALF_OPEN:
                return True
            return False

    def record_success(self):
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
            elif self.state == CircuitState.CLOSED:
                self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.state == CircuitState.CLOSED and self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"熔断器打开，连续失败 {self.failure_count} 次")
            elif self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning("熔断器重新打开（半开状态下失败）")

    @property
    def current_state(self) -> str:
        return self.state.value


class LRUCache:
    """LRU 缓存"""

    def __init__(self, max_size: int = 256, ttl: float = 300.0):
        self._cache: OrderedDict[str, Tuple[float, Any]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl
        self._hits = 0
        self._misses = 0

    def _make_key(self, data: Dict[str, Any]) -> str:
        raw = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, data: Dict[str, Any]) -> Optional[Any]:
        key = self._make_key(data)
        if key in self._cache:
            ts, value = self._cache[key]
            if time.time() - ts < self._ttl:
                self._cache.move_to_end(key)
                self._hits += 1
                return value
            del self._cache[key]
        self._misses += 1
        return None

    def put(self, data: Dict[str, Any], value: Any):
        key = self._make_key(data)
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = (time.time(), value)
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def invalidate(self, data: Dict[str, Any]):
        key = self._make_key(data)
        self._cache.pop(key, None)

    def clear(self):
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    @property
    def stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self._hits / total * 100:.1f}%" if total > 0 else "0.0%",
        }


class ModelSelector:
    """智能模型选择器"""

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
        "perception": "qwen2:0.5b",
        "decision": "qwen2.5:3b-instruct-q4_K_M",
        "execution": "gemma4:e4b",
        "thinking": "gemma4:e4b",
        "memory": "qwen2:0.5b",
        "creative": "gemma4:e4b",
        "code": "gemma4:e4b",
    }

    def __init__(self, default_model: str = None):
        self.default_model = default_model or settings.ollama.default_model

    def select(self, skill_type: str = None, complexity: str = "auto",
               preferred_model: str = None) -> str:
        if preferred_model:
            return preferred_model
        if skill_type and skill_type in self.SKILL_MODEL_MAP:
            return self.SKILL_MODEL_MAP[skill_type]
        if complexity != "auto" and complexity in self.MODEL_COMPLEXITY:
            target = self.MODEL_COMPLEXITY[complexity]
            candidates = [m for m, c in self.MODEL_COMPLEXITY.items() if c == target]
            if candidates:
                return candidates[0]
        return self.default_model


class UnifiedLLMClient:
    """
    统一 LLM 客户端

    特性：
    - httpx 异步连接池（复用连接，非阻塞）
    - 熔断器（CircuitBreaker，防止级联故障）
    - LRU 缓存（相同输入直接返回，减少推理次数）
    - Semaphore 并发控制（限制同时推理数）
    - 智能模型选择（根据技能类型自动选模型）
    - 指数退避重试（3次重试，2^n秒间隔）
    - 历史消息截断（防止上下文溢出）
    - 统一统计（请求/成功/失败/缓存/延迟）
    - 健康检查（定时检测 Ollama 可用性）
    - 向后兼容（chat/generate/embedding/list 接口不变）
    """

    def __init__(
        self,
        base_url: str = None,
        default_model: str = None,
        timeout: float = None,
        max_concurrent: int = None,
        cache_size: int = None,
        cache_ttl: float = None,
        max_history: int = None,
    ):
        self.base_url = (base_url or settings.ollama.host).rstrip("/")
        self.default_model = default_model or settings.ollama.default_model
        self.timeout = timeout or settings.ollama.timeout
        self.max_history = max_history or settings.ollama.max_history_messages

        _max_concurrent = max_concurrent or settings.llm_client.max_concurrent
        _cache_size = cache_size or settings.llm_client.cache_size
        _cache_ttl = cache_ttl or settings.llm_client.cache_ttl

        self._client: Optional[httpx.AsyncClient] = None
        self._semaphore = asyncio.Semaphore(_max_concurrent)
        self._cache = LRUCache(max_size=_cache_size, ttl=_cache_ttl)
        self._circuit_breaker = CircuitBreaker(CircuitConfig(
            failure_threshold=settings.circuit.failure_threshold,
            recovery_timeout=settings.circuit.recovery_timeout,
            half_open_attempts=settings.circuit.half_open_attempts,
        ))
        self._retry_config = RetryConfig(
            max_attempts=settings.llm_client.retry_max_attempts,
            base_delay=settings.llm_client.retry_base_delay,
            max_delay=settings.llm_client.retry_max_delay,
            backoff_factor=settings.llm_client.retry_backoff_factor,
        )
        self._model_selector = ModelSelector(self.default_model)

        self._model_list_cache: Optional[List[str]] = None
        self._model_list_ts: float = 0
        self._healthy: bool = True
        self._last_health_check: float = 0
        self._health_check_interval: float = 30.0

        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "retry_count": 0,
            "circuit_opens": 0,
            "total_response_time": 0.0,
        }
        self._stats_lock = threading.Lock()

        self._executor = ThreadPoolExecutor(max_workers=max_concurrent)

        self._default_options: Dict[str, Any] = {
            "temperature": settings.ollama.temperature,
            "num_ctx": settings.ollama.context_tokens,
            "num_predict": 1024,
            "top_p": settings.ollama.top_p,
            "top_k": settings.ollama.top_k,
            "num_batch": 128,
            "stream": False,
        }

        logger.info(
            "统一LLM客户端初始化 | 地址:%s | 默认模型:%s | 超时:%.0fs | 并发:%d | 缓存:%d/%.0fs",
            self.base_url, self.default_model, self.timeout, max_concurrent, cache_size, cache_ttl,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
        self._executor.shutdown(wait=False)
        logger.info("统一LLM客户端已关闭")

    def select_model(self, skill_type: str = None, complexity: str = "auto",
                     preferred_model: str = None) -> str:
        return self._model_selector.select(skill_type, complexity, preferred_model)

    def _truncate_history(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if len(messages) <= self.max_history:
            return list(messages)
        truncated = messages[-self.max_history:]
        logger.warning("历史消息截断 %d → %d 条", len(messages), len(truncated))
        return truncated

    def _build_messages(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        history_messages: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history_messages:
            messages.extend(self._truncate_history(history_messages))
        messages.append({"role": "user", "content": user_prompt})
        return messages

    @staticmethod
    def _parse_response(response_text: str) -> Dict[str, Any]:
        text = response_text.strip()
        if not text:
            return {"message": {"content": ""}}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            lines = [l for l in text.split("\n") if l.strip()]
            if lines:
                try:
                    return json.loads(lines[-1])
                except json.JSONDecodeError:
                    pass
            return {"message": {"content": text}}

    async def _retry_with_backoff(self, func, *args, **kwargs) -> Any:
        last_error = None
        for attempt in range(self._retry_config.max_attempts):
            try:
                start_time = time.time()
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time

                self._circuit_breaker.record_success()
                with self._stats_lock:
                    self._stats["successful_requests"] += 1
                    self._stats["total_response_time"] += elapsed
                return result
            except Exception as e:
                last_error = e
                self._circuit_breaker.record_failure()

                if attempt < self._retry_config.max_attempts - 1:
                    delay = min(
                        self._retry_config.base_delay * (self._retry_config.backoff_factor ** attempt),
                        self._retry_config.max_delay,
                    )
                    logger.warning("请求失败(尝试%d/%d): %s, %.1fs后重试", attempt + 1, self._retry_config.max_attempts, e, delay)
                    await asyncio.sleep(delay)
                    with self._stats_lock:
                        self._stats["retry_count"] += 1
                else:
                    logger.error("所有重试失败(%d次): %s", self._retry_config.max_attempts, e)

        with self._stats_lock:
            self._stats["failed_requests"] += 1
        raise last_error

    async def chat(
        self,
        model: str = None,
        messages: List[Dict[str, str]] = None,
        user_prompt: str = None,
        system_prompt: str = None,
        history_messages: List[Dict[str, str]] = None,
        temperature: float = None,
        use_cache: bool = True,
        skill_type: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        model = model or self.select_model(skill_type)

        if messages is None:
            messages = self._build_messages(
                user_prompt or "", system_prompt, history_messages
            )

        cache_key = {
            "method": "chat", "model": model,
            "messages_hash": hashlib.md5(
                json.dumps(messages, ensure_ascii=False).encode()
            ).hexdigest(),
            "temperature": temperature or self._default_options["temperature"],
        }
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                with self._stats_lock:
                    self._stats["cache_hits"] += 1
                return {**cached, "from_cache": True}

        if not self._circuit_breaker.should_allow():
            raise Exception(f"熔断器状态: {self._circuit_breaker.current_state}，请求被拒绝")

        with self._stats_lock:
            self._stats["total_requests"] += 1

        options = dict(self._default_options)
        if temperature is not None:
            options["temperature"] = temperature
        options.update(kwargs.get("options", {}))

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": options,
        }
        if kwargs.get("tools"):
            payload["tools"] = kwargs["tools"]

        async def _do_chat():
            async with self._semaphore:
                client = await self._get_client()
                response = await client.post("/api/chat", json=payload)
                response.raise_for_status()
                return self._parse_response(response.text)

        result = await self._retry_with_backoff(_do_chat)

        content = result.get("message", {}).get("content", "")
        formatted = {
            "status": "success",
            "response": content,
            "message": result.get("message", {}),
            "model": model,
            "total_duration": result.get("total_duration", 0),
            "prompt_eval_count": result.get("prompt_eval_count", 0),
            "eval_count": result.get("eval_count", 0),
            "from_cache": False,
        }

        if use_cache:
            self._cache.put(cache_key, formatted)

        return formatted

    async def generate(
        self,
        prompt: str,
        model: str = None,
        system: str = None,
        temperature: float = None,
        max_tokens: int = 4096,
        use_cache: bool = True,
        skill_type: str = None,
        **kwargs,
    ) -> Dict[str, Any]:
        model = model or self.select_model(skill_type)

        cache_key = {
            "method": "generate", "model": model,
            "prompt": prompt[:500],
            "system": (system or "")[:200],
            "temperature": temperature or self._default_options["temperature"],
            "max_tokens": max_tokens,
        }
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                with self._stats_lock:
                    self._stats["cache_hits"] += 1
                return {**cached, "from_cache": True}

        if not self._circuit_breaker.should_allow():
            raise Exception(f"熔断器状态: {self._circuit_breaker.current_state}，请求被拒绝")

        with self._stats_lock:
            self._stats["total_requests"] += 1

        options = dict(self._default_options)
        if temperature is not None:
            options["temperature"] = temperature
        options["num_predict"] = max_tokens
        options.update(kwargs.get("options", {}))

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        if system:
            payload["system"] = system

        async def _do_generate():
            async with self._semaphore:
                client = await self._get_client()
                response = await client.post("/api/generate", json=payload)
                response.raise_for_status()
                return response.json()

        result = await self._retry_with_backoff(_do_generate)

        formatted = {
            "status": "success",
            "response": result.get("response", ""),
            "model": model,
            "total_duration": result.get("total_duration", 0),
            "eval_count": result.get("eval_count", 0),
            "from_cache": False,
        }

        if use_cache:
            self._cache.put(cache_key, formatted)

        return formatted

    async def embedding(self, model: str = None, prompt: str = None,
                        input_text: str = None, **kwargs) -> Dict[str, Any]:
        model = model or self.default_model
        text = prompt or input_text or ""

        if not self._circuit_breaker.should_allow():
            raise Exception(f"熔断器状态: {self._circuit_breaker.current_state}")

        with self._stats_lock:
            self._stats["total_requests"] += 1

        payload = {"model": model, "prompt": text}

        async def _do_embedding():
            async with self._semaphore:
                client = await self._get_client()
                response = await client.post("/api/embeddings", json=payload)
                response.raise_for_status()
                return response.json()

        return await self._retry_with_backoff(_do_embedding)

    async def list_models(self) -> List[Dict[str, Any]]:
        now = time.time()
        if self._model_list_cache and now - self._model_list_ts < 60:
            return self._model_list_cache
        try:
            client = await self._get_client()
            response = await client.get("/api/tags", timeout=10.0)
            response.raise_for_status()
            data = response.json()
            models = data.get("models", [])
            self._model_list_cache = models
            self._model_list_ts = now
            return models
        except Exception as e:
            logger.warning("获取模型列表失败: %s", e)
            return []

    async def list_model_names(self) -> List[str]:
        models = await self.list_models()
        return [m.get("name", "") for m in models if m.get("name")]

    async def health_check(self) -> bool:
        now = time.time()
        if now - self._last_health_check < self._health_check_interval:
            return self._healthy
        try:
            client = await self._get_client()
            response = await client.get("/api/tags", timeout=5.0)
            self._healthy = response.status_code == 200
        except Exception:
            self._healthy = False
        self._last_health_check = now
        return self._healthy

    async def is_available(self) -> bool:
        return await self.health_check()

    async def decision(self, user_prompt: str, system_prompt: str,
                       model: str = None, **kwargs) -> Dict[str, Any]:
        result = await self.chat(
            model=model, user_prompt=user_prompt,
            system_prompt=system_prompt, use_cache=False, **kwargs,
        )
        if result.get("status") != "success":
            return {"error": result.get("response", "决策调用失败")}

        content = result.get("response", "")
        for marker in ["```json", "```"]:
            if marker in content:
                start = content.find(marker) + len(marker)
                end = content.find("```", start)
                if end > start:
                    content = content[start:end].strip()
                    break

        json_start = content.find("{")
        json_end = content.rfind("}")
        if json_start != -1 and json_end > json_start:
            content = content[json_start:json_end + 1]

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"error": "决策结果JSON解析失败", "raw": content}

    async def tool_call(self, user_prompt: str, system_prompt: str,
                        tools: List[Dict], model: str = None, **kwargs) -> Dict[str, Any]:
        result = await self.chat(
            model=model, user_prompt=user_prompt,
            system_prompt=system_prompt, tools=tools,
            use_cache=False, **kwargs,
        )
        if result.get("status") != "success":
            return {"error": result.get("response", "工具调用失败")}

        message = result.get("message", {})
        has_tools = "tool_calls" in message and bool(message["tool_calls"])
        return {
            "has_tool_call": has_tools,
            "tool_calls": message.get("tool_calls", []),
            "content": message.get("content", ""),
        }

    async def memory_summary(self, content: str, model: str = None) -> str:
        result = await self.chat(
            model=model or self.select_model("memory"),
            user_prompt=content,
            system_prompt="你擅长精简总结，将输入内容提炼为100字以内的核心信息，用于长期记忆存储，不添加多余内容。",
            use_cache=False,
        )
        return result.get("response", "")

    def get_stats(self) -> Dict[str, Any]:
        with self._stats_lock:
            stats = dict(self._stats)
        stats["circuit_state"] = self._circuit_breaker.current_state
        stats["healthy"] = self._healthy
        avg_time = (
            stats["total_response_time"] / stats["successful_requests"]
            if stats["successful_requests"] > 0 else 0
        )
        stats["avg_response_time"] = f"{avg_time:.3f}s"
        stats["cache"] = self._cache.stats
        return stats

    def reset_stats(self):
        with self._stats_lock:
            self._stats = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "cache_hits": 0,
                "retry_count": 0,
                "circuit_opens": 0,
                "total_response_time": 0.0,
            }
        self._cache.clear()

    @property
    def cache_stats(self) -> Dict[str, Any]:
        return self._cache.stats

    @property
    def circuit_state(self) -> str:
        return self._circuit_breaker.current_state


_unified_client: Optional[UnifiedLLMClient] = None
_client_lock = threading.Lock()


def get_unified_client() -> UnifiedLLMClient:
    global _unified_client
    if _unified_client is None:
        with _client_lock:
            if _unified_client is None:
                _unified_client = UnifiedLLMClient()
                logger.info("统一LLM客户端实例已创建")
    return _unified_client


def close_unified_client():
    global _unified_client
    if _unified_client:
        _unified_client = None
        logger.info("统一LLM客户端实例已清除")


def get_llm_client() -> UnifiedLLMClient:
    return get_unified_client()


async def get_gemma4_brain(**kwargs) -> UnifiedLLMClient:
    return get_unified_client()
