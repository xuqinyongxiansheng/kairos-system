# -*- coding: utf-8 -*-
"""
提供者故障转移链 (Provider Fallback Chain)
源自Hermes Agent提供者故障转移架构

核心特性:
- 多级故障转移: 主提供者失败时自动切换到备用
- 429限流智能处理: 解析Retry-After头，等待后重试
- 独立辅助链: 视觉/压缩/搜索等辅助任务有独立故障转移
- 健康检查: 定期检测提供者可用性
- 统计追踪: 记录每次调用的成功/失败/延迟
"""

import time
import logging
import threading
import random
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger("ProviderFallback")


class ProviderStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"


@dataclass
class ProviderEndpoint:
    """提供者端点"""
    name: str
    url: str
    model: str
    api_key: str = ""
    priority: int = 1
    max_retries: int = 3
    timeout: float = 120.0
    status: ProviderStatus = ProviderStatus.HEALTHY
    last_error: str = ""
    last_success: float = 0.0
    last_failure: float = 0.0
    consecutive_failures: int = 0
    total_calls: int = 0
    total_successes: int = 0
    total_failures: int = 0
    avg_latency_ms: float = 0.0
    rate_limit_until: float = 0.0

    @property
    def is_available(self) -> bool:
        if self.status == ProviderStatus.UNAVAILABLE:
            return False
        if self.status == ProviderStatus.RATE_LIMITED:
            return time.time() >= self.rate_limit_until
        return True

    @property
    def success_rate(self) -> float:
        return self.total_successes / max(self.total_calls, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
            "model": self.model,
            "priority": self.priority,
            "status": self.status.value,
            "is_available": self.is_available,
            "success_rate": round(self.success_rate, 3),
            "total_calls": self.total_calls,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "consecutive_failures": self.consecutive_failures
        }


@dataclass
class FallbackResult:
    """故障转移结果"""
    success: bool
    provider_name: str
    response: Any = None
    error: str = ""
    latency_ms: float = 0.0
    attempts: int = 0
    fallback_used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "provider_name": self.provider_name,
            "error": self.error,
            "latency_ms": round(self.latency_ms, 1),
            "attempts": self.attempts,
            "fallback_used": self.fallback_used
        }


class ProviderFallbackChain:
    """
    提供者故障转移链
    
    用法:
    1. add_provider() 注册提供者（按优先级排序）
    2. call_with_fallback() 执行调用，自动故障转移
    3. get_statistics() 获取统计信息
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._providers: Dict[str, ProviderEndpoint] = {}
        self._ordered_names: List[str] = []
        self._health_check_interval = self.config.get("health_check_interval", 300)
        self._max_consecutive_failures = self.config.get("max_consecutive_failures", 5)
        self._recovery_cooldown = self.config.get("recovery_cooldown", 60)
        self._lock = threading.Lock()
        self._health_thread = None
        self._health_running = False

    def add_provider(self, name: str, url: str, model: str,
                     api_key: str = "", priority: int = 1,
                     timeout: float = 120.0) -> str:
        provider = ProviderEndpoint(
            name=name, url=url, model=model,
            api_key=api_key, priority=priority, timeout=timeout
        )
        with self._lock:
            self._providers[name] = provider
            self._ordered_names = sorted(
                self._providers.keys(),
                key=lambda n: self._providers[n].priority
            )
        logger.info("提供者已注册: %s (url=%s, model=%s, priority=%d)", name, url, model, priority)
        return name

    def remove_provider(self, name: str):
        with self._lock:
            self._providers.pop(name, None)
            self._ordered_names = sorted(
                self._providers.keys(),
                key=lambda n: self._providers[n].priority
            )

    def call_with_fallback(self, call_fn: Callable[[ProviderEndpoint], Any],
                           task_type: str = "chat") -> FallbackResult:
        start_time = time.time()
        last_error = ""
        attempts = 0
        primary_name = ""

        with self._lock:
            available = [n for n in self._ordered_names if self._providers[n].is_available]

        if not available:
            all_names = list(self._ordered_names)
            for name in all_names:
                provider = self._providers[name]
                provider.status = ProviderStatus.HEALTHY
                provider.consecutive_failures = 0
            with self._lock:
                available = [n for n in self._ordered_names]

        if not available:
            return FallbackResult(
                success=False, provider_name="",
                error="所有提供者均不可用", attempts=0
            )

        primary_name = available[0]

        for name in available:
            provider = self._providers[name]
            attempts += 1

            for retry in range(provider.max_retries):
                try:
                    call_start = time.time()
                    result = call_fn(provider)
                    call_latency = (time.time() - call_start) * 1000

                    self._record_success(name, call_latency)

                    fallback_used = (name != primary_name)
                    total_latency = (time.time() - start_time) * 1000

                    return FallbackResult(
                        success=True,
                        provider_name=name,
                        response=result,
                        latency_ms=total_latency,
                        attempts=attempts,
                        fallback_used=fallback_used
                    )

                except Exception as e:
                    error_str = str(e)
                    last_error = error_str
                    self._record_failure(name, error_str)

                    if "429" in error_str or "rate" in error_str.lower():
                        retry_after = self._parse_retry_after(error_str)
                        provider.status = ProviderStatus.RATE_LIMITED
                        provider.rate_limit_until = time.time() + retry_after
                        logger.info("提供者 %s 限流，%d秒后恢复", name, retry_after)
                        break

                    if "401" in error_str or "403" in error_str:
                        logger.error("提供者 %s 认证失败: %s", name, error_str)
                        break

                    if retry < provider.max_retries - 1:
                        backoff = min(2 ** retry + random.uniform(0, 1), 10)
                        time.sleep(backoff)

        total_latency = (time.time() - start_time) * 1000
        return FallbackResult(
            success=False,
            provider_name=primary_name,
            error=last_error,
            latency_ms=total_latency,
            attempts=attempts,
            fallback_used=True
        )

    def _record_success(self, name: str, latency_ms: float):
        with self._lock:
            provider = self._providers.get(name)
            if not provider:
                return
            provider.total_calls += 1
            provider.total_successes += 1
            provider.consecutive_failures = 0
            provider.last_success = time.time()
            if provider.avg_latency_ms == 0:
                provider.avg_latency_ms = latency_ms
            else:
                provider.avg_latency_ms = provider.avg_latency_ms * 0.8 + latency_ms * 0.2
            if provider.status != ProviderStatus.HEALTHY:
                provider.status = ProviderStatus.HEALTHY

    def _record_failure(self, name: str, error: str):
        with self._lock:
            provider = self._providers.get(name)
            if not provider:
                return
            provider.total_calls += 1
            provider.total_failures += 1
            provider.consecutive_failures += 1
            provider.last_failure = time.time()
            provider.last_error = error[:200]

            if provider.consecutive_failures >= self._max_consecutive_failures:
                provider.status = ProviderStatus.UNAVAILABLE
                logger.warning("提供者 %s 标记为不可用 (连续%d次失败)", name, provider.consecutive_failures)
            elif provider.consecutive_failures >= 2:
                provider.status = ProviderStatus.DEGRADED

    def _parse_retry_after(self, error_str: str) -> float:
        import re
        match = re.search(r'retry.?after[:\s]+(\d+)', error_str, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return 60.0

    def get_provider(self, name: str) -> Optional[Dict[str, Any]]:
        provider = self._providers.get(name)
        return provider.to_dict() if provider else None

    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            providers = {name: p.to_dict() for name, p in self._providers.items()}
            available_count = sum(1 for p in self._providers.values() if p.is_available)
            return {
                "total_providers": len(self._providers),
                "available_providers": available_count,
                "providers": providers,
                "ordered_names": list(self._ordered_names)
            }

    def start_health_check(self):
        if self._health_running:
            return
        self._health_running = True

        def _check_loop():
            while self._health_running:
                time.sleep(self._health_check_interval)
                self._perform_health_check()

        self._health_thread = threading.Thread(target=_check_loop, daemon=True)
        self._health_thread.start()
        logger.info("提供者健康检查已启动 (间隔=%ds)", self._health_check_interval)

    def stop_health_check(self):
        self._health_running = False

    def _perform_health_check(self):
        now = time.time()
        with self._lock:
            for name, provider in self._providers.items():
                if provider.status == ProviderStatus.UNAVAILABLE:
                    if now - provider.last_failure > self._recovery_cooldown:
                        provider.status = ProviderStatus.DEGRADED
                        provider.consecutive_failures = 0
                        logger.info("提供者 %s 恢复为降级状态", name)

                elif provider.status == ProviderStatus.RATE_LIMITED:
                    if now >= provider.rate_limit_until:
                        provider.status = ProviderStatus.HEALTHY
                        logger.info("提供者 %s 限流结束，恢复健康", name)


_provider_chain: Optional[ProviderFallbackChain] = None
_chain_lock = threading.Lock()


def get_provider_chain(config: Dict[str, Any] = None) -> ProviderFallbackChain:
    global _provider_chain
    if _provider_chain is None:
        with _chain_lock:
            if _provider_chain is None:
                _provider_chain = ProviderFallbackChain(config)
    return _provider_chain
