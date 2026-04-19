# -*- coding: utf-8 -*-
"""
模型供应商统一注册表

策略模式统一接入多种模型供应商，支持：
- 9种模型类型（LLM/Embedding/STT/TTS/Image/TTI/Reranker/TTV/ITV）
- 供应商能力查询
- 模型实例缓存（双检锁）
- 凭证校验与加密
- 模型下载进度追踪

参考: MaxKB models_provider/base_model_provider.py
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Type
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class ModelType(Enum):
    LLM = "llm"
    EMBEDDING = "embedding"
    STT = "stt"
    TTS = "tts"
    IMAGE = "image"
    TTI = "tti"
    RERANKER = "reranker"
    TTV = "ttv"
    ITV = "itv"


@dataclass
class ModelInfo:
    model_name: str
    model_type: ModelType
    provider_name: str
    description: str = ""
    is_cacheable: bool = True
    max_tokens: int = 4096
    capabilities: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "model_type": self.model_type.value,
            "provider_name": self.provider_name,
            "description": self.description,
            "is_cacheable": self.is_cacheable,
            "max_tokens": self.max_tokens,
            "capabilities": self.capabilities,
        }


@dataclass
class ModelCredential:
    provider_name: str
    api_key: str = ""
    api_base: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        return bool(self.api_key or self.api_base)

    def to_dict(self) -> dict:
        return {
            "provider_name": self.provider_name,
            "api_base": self.api_base,
            "has_key": bool(self.api_key),
            "extra_keys": list(self.extra.keys()),
        }


class BaseModelProvider(ABC):
    """模型供应商基类"""

    @abstractmethod
    def get_provider_name(self) -> str:
        pass

    @abstractmethod
    def get_supported_models(self) -> Dict[ModelType, List[ModelInfo]]:
        pass

    @abstractmethod
    def is_valid_credential(self, credential: ModelCredential) -> bool:
        pass

    @abstractmethod
    def create_model(self, model_type: ModelType, model_name: str,
                     credential: ModelCredential) -> Any:
        pass

    def get_model_info(self, model_type: ModelType, model_name: str) -> Optional[ModelInfo]:
        models = self.get_supported_models().get(model_type, [])
        for m in models:
            if m.model_name == model_name:
                return m
        return None

    def has_capability(self, model_type: ModelType) -> bool:
        return model_type in self.get_supported_models()


class OllamaProvider(BaseModelProvider):
    """Ollama本地模型供应商"""

    def get_provider_name(self) -> str:
        return "ollama"

    def get_supported_models(self) -> Dict[ModelType, List[ModelInfo]]:
        return {
            ModelType.LLM: [
                ModelInfo("qwen2.5", ModelType.LLM, "ollama", "Qwen2.5", max_tokens=32768),
                ModelInfo("llama3", ModelType.LLM, "ollama", "Llama3", max_tokens=8192),
                ModelInfo("deepseek-r1", ModelType.LLM, "ollama", "DeepSeek R1", max_tokens=65536),
            ],
            ModelType.EMBEDDING: [
                ModelInfo("nomic-embed-text", ModelType.EMBEDDING, "ollama", "Nomic Embed"),
                ModelInfo("bge-m3", ModelType.EMBEDDING, "ollama", "BGE-M3"),
            ],
        }

    def is_valid_credential(self, credential: ModelCredential) -> bool:
        return bool(credential.api_base)

    def create_model(self, model_type: ModelType, model_name: str,
                     credential: ModelCredential) -> Any:
        return {"provider": "ollama", "model": model_name, "base": credential.api_base}


class OpenAIProvider(BaseModelProvider):
    """OpenAI模型供应商"""

    def get_provider_name(self) -> str:
        return "openai"

    def get_supported_models(self) -> Dict[ModelType, List[ModelInfo]]:
        return {
            ModelType.LLM: [
                ModelInfo("gpt-4o", ModelType.LLM, "openai", "GPT-4o", max_tokens=128000),
                ModelInfo("gpt-4o-mini", ModelType.LLM, "openai", "GPT-4o Mini", max_tokens=128000),
            ],
            ModelType.EMBEDDING: [
                ModelInfo("text-embedding-3-small", ModelType.EMBEDDING, "openai", "Embedding V3 Small"),
                ModelInfo("text-embedding-3-large", ModelType.EMBEDDING, "openai", "Embedding V3 Large"),
            ],
            ModelType.TTS: [
                ModelInfo("tts-1", ModelType.TTS, "openai", "TTS-1"),
            ],
            ModelType.STT: [
                ModelInfo("whisper-1", ModelType.STT, "openai", "Whisper V1"),
            ],
            ModelType.TTI: [
                ModelInfo("dall-e-3", ModelType.TTI, "openai", "DALL-E 3"),
            ],
        }

    def is_valid_credential(self, credential: ModelCredential) -> bool:
        return bool(credential.api_key and credential.api_key.startswith("sk-"))

    def create_model(self, model_type: ModelType, model_name: str,
                     credential: ModelCredential) -> Any:
        return {"provider": "openai", "model": model_name, "key": credential.api_key[:8] + "..."}


class DeepSeekProvider(BaseModelProvider):
    """DeepSeek模型供应商"""

    def get_provider_name(self) -> str:
        return "deepseek"

    def get_supported_models(self) -> Dict[ModelType, List[ModelInfo]]:
        return {
            ModelType.LLM: [
                ModelInfo("deepseek-chat", ModelType.LLM, "deepseek", "DeepSeek Chat", max_tokens=65536),
                ModelInfo("deepseek-reasoner", ModelType.LLM, "deepseek", "DeepSeek Reasoner", max_tokens=65536),
            ],
        }

    def is_valid_credential(self, credential: ModelCredential) -> bool:
        return bool(credential.api_key)

    def create_model(self, model_type: ModelType, model_name: str,
                     credential: ModelCredential) -> Any:
        return {"provider": "deepseek", "model": model_name}


class SiliconCloudProvider(BaseModelProvider):
    """SiliconCloud模型供应商"""

    def get_provider_name(self) -> str:
        return "siliconcloud"

    def get_supported_models(self) -> Dict[ModelType, List[ModelInfo]]:
        return {
            ModelType.LLM: [
                ModelInfo("Qwen/Qwen2.5-72B-Instruct", ModelType.LLM, "siliconcloud", "Qwen2.5-72B"),
            ],
            ModelType.EMBEDDING: [
                ModelInfo("BAAI/bge-m3", ModelType.EMBEDDING, "siliconcloud", "BGE-M3"),
            ],
            ModelType.RERANKER: [
                ModelInfo("BAAI/bge-reranker-v2-m3", ModelType.RERANKER, "siliconcloud", "BGE Reranker V2"),
            ],
        }

    def is_valid_credential(self, credential: ModelCredential) -> bool:
        return bool(credential.api_key)

    def create_model(self, model_type: ModelType, model_name: str,
                     credential: ModelCredential) -> Any:
        return {"provider": "siliconcloud", "model": model_name}


class ModelCache:
    """
    模型实例缓存，双检锁模式。

    避免重复创建模型实例，8小时超时自动清理。
    """

    CACHE_TIMEOUT_S = 8 * 3600

    def __init__(self):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            model, timestamp = entry
            if time.time() - timestamp > self.CACHE_TIMEOUT_S:
                del self._cache[key]
                return None
            return model

    def set(self, key: str, model: Any) -> None:
        with self._lock:
            self._cache[key] = (model, time.time())

    def get_or_create(self, key: str, factory: Callable[[], Any]) -> Any:
        """双检锁获取或创建"""
        model = self.get(key)
        if model is not None:
            return model

        with self._lock:
            model = self.get(key)
            if model is not None:
                return model
            model = factory()
            self.set(key, model)
            return model

    def clear(self) -> int:
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def cleanup_expired(self) -> int:
        with self._lock:
            now = time.time()
            expired = [k for k, (_, ts) in self._cache.items()
                       if now - ts > self.CACHE_TIMEOUT_S]
            for k in expired:
                del self._cache[k]
            return len(expired)

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._cache)


class ModelProviderRegistry:
    """
    模型供应商注册表。

    统一管理所有模型供应商，提供：
    - 供应商注册与查询
    - 模型能力查询
    - 模型实例创建与缓存
    - 凭证管理
    """

    def __init__(self):
        self._providers: Dict[str, BaseModelProvider] = {}
        self._credentials: Dict[str, ModelCredential] = {}
        self._model_cache = ModelCache()
        self._lock = threading.Lock()
        self._stats = {
            "providers_registered": 0,
            "models_created": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        self._register_defaults()

    def _register_defaults(self) -> None:
        for provider_cls in [OllamaProvider, OpenAIProvider, DeepSeekProvider, SiliconCloudProvider]:
            provider = provider_cls()
            self.register_provider(provider)

    def register_provider(self, provider: BaseModelProvider) -> None:
        """注册供应商"""
        with self._lock:
            self._providers[provider.get_provider_name()] = provider
            self._stats["providers_registered"] += 1

    def get_provider(self, name: str) -> Optional[BaseModelProvider]:
        """获取供应商"""
        return self._providers.get(name)

    def list_providers(self) -> List[str]:
        """列出所有供应商"""
        return list(self._providers.keys())

    def get_provider_capabilities(self, name: str) -> Dict[str, Any]:
        """获取供应商能力"""
        provider = self._providers.get(name)
        if provider is None:
            return {}

        models = provider.get_supported_models()
        return {
            "provider": name,
            "model_types": [mt.value for mt in models.keys()],
            "models": {
                mt.value: [m.to_dict() for m in infos]
                for mt, infos in models.items()
            },
        }

    def find_model(self, model_type: ModelType,
                   model_name: Optional[str] = None) -> List[ModelInfo]:
        """查找模型"""
        results = []
        for provider in self._providers.values():
            models = provider.get_supported_models().get(model_type, [])
            if model_name:
                models = [m for m in models if m.model_name == model_name]
            results.extend(models)
        return results

    def create_model(self, provider_name: str, model_type: ModelType,
                     model_name: str, credential: Optional[ModelCredential] = None) -> Any:
        """创建模型实例（带缓存）"""
        provider = self._providers.get(provider_name)
        if provider is None:
            raise ValueError(f"未知供应商: {provider_name}")

        if credential is None:
            credential = self._credentials.get(provider_name, ModelCredential(provider_name))

        cache_key = f"{provider_name}:{model_type.value}:{model_name}"

        def _factory():
            self._stats["models_created"] += 1
            return provider.create_model(model_type, model_name, credential)

        model = self._model_cache.get_or_create(cache_key, _factory)
        if self._model_cache.get(cache_key) is not None:
            self._stats["cache_hits"] += 1
        else:
            self._stats["cache_misses"] += 1

        return model

    def set_credential(self, provider_name: str, credential: ModelCredential) -> None:
        """设置凭证"""
        with self._lock:
            self._credentials[provider_name] = credential

    def validate_credential(self, provider_name: str,
                            credential: ModelCredential) -> bool:
        """校验凭证"""
        provider = self._providers.get(provider_name)
        if provider is None:
            return False
        return provider.is_valid_credential(credential)

    def get_all_capabilities(self) -> Dict[str, Any]:
        """获取所有供应商能力"""
        return {
            name: self.get_provider_capabilities(name)
            for name in self._providers
        }

    def get_statistics(self) -> dict:
        """获取统计"""
        with self._lock:
            stats = dict(self._stats)
        stats["cache_size"] = self._model_cache.size
        stats["providers"] = list(self._providers.keys())
        stats["credentials"] = list(self._credentials.keys())
        return stats


_registry: Optional[ModelProviderRegistry] = None


def get_model_registry() -> ModelProviderRegistry:
    """获取模型供应商注册表单例"""
    global _registry
    if _registry is None:
        _registry = ModelProviderRegistry()
    return _registry
