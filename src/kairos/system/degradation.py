"""
优雅降级管理器
借鉴 cc-haha-main 的降级模式，实现三级服务降级：
1. 完整模式：Ollama 可用，所有功能正常
2. 规则模式：Ollama 不可用，使用规则引擎处理简单查询
3. 最小模式：仅保留基础对话和健康检查端点
"""

import os
import time
import logging
import asyncio
from enum import IntEnum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger("DegradationManager")


class ServiceLevel(IntEnum):
    FULL = 3
    RULE_BASED = 2
    MINIMAL = 1


@dataclass
class HealthCheckResult:
    available: bool
    latency_ms: float = 0.0
    error: str = ""


class DegradationManager:
    """服务降级管理器"""

    def __init__(self, ollama_host: str = None):
        self.ollama_host = ollama_host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.current_level = ServiceLevel.FULL
        self._check_history: List[Dict[str, Any]] = []
        self._consecutive_failures = 0
        self._max_history = 100
        self._last_check_time = 0
        self._check_interval = 30
        self._failure_threshold = 3
        self._recovery_threshold = 2

    async def check_ollama_health(self) -> HealthCheckResult:
        """检查 Ollama 服务健康状态"""
        start = time.time()
        try:
            import urllib.request
            url = f"{self.ollama_host}/api/tags"
            req = urllib.request.Request(url, method="GET")
            req.add_header("Connection", "close")
            with urllib.request.urlopen(req, timeout=5) as resp:
                latency = (time.time() - start) * 1000
                if resp.status == 200:
                    return HealthCheckResult(available=True, latency_ms=latency)
                return HealthCheckResult(available=False, latency_ms=latency, error=f"HTTP {resp.status}")
        except Exception as e:
            latency = (time.time() - start) * 1000
            return HealthCheckResult(available=False, latency_ms=latency, error=str(e))

    async def evaluate_service_level(self) -> ServiceLevel:
        """评估当前服务级别"""
        now = time.time()
        if now - self._last_check_time < self._check_interval:
            return self.current_level

        self._last_check_time = now
        health = await self.check_ollama_health()

        self._check_history.append({
            "timestamp": now,
            "available": health.available,
            "latency_ms": health.latency_ms,
            "error": health.error,
        })
        if len(self._check_history) > self._max_history:
            self._check_history = self._check_history[-self._max_history:]

        if health.available:
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1

        old_level = self.current_level

        if health.available and health.latency_ms < 5000:
            if self._consecutive_failures == 0:
                self.current_level = ServiceLevel.FULL
        elif health.available and health.latency_ms >= 5000:
            self.current_level = ServiceLevel.RULE_BASED
        elif self._consecutive_failures >= self._failure_threshold:
            self.current_level = ServiceLevel.MINIMAL
        elif self._consecutive_failures > 0:
            self.current_level = ServiceLevel.RULE_BASED

        if old_level != self.current_level:
            logger.warning(f"服务级别变更: {old_level.name} -> {self.current_level.name}")
            if not health.available:
                logger.warning(f"Ollama 不可用: {health.error}")

        return self.current_level

    def get_fallback_response(self, message: str) -> str:
        """获取降级模式下的回退响应"""
        if self.current_level == ServiceLevel.RULE_BASED:
            return self._rule_based_response(message)
        elif self.current_level == ServiceLevel.MINIMAL:
            return self._minimal_response(message)
        return ""

    def _rule_based_response(self, message: str) -> str:
        """规则模式响应（基于 hybrid_engine.py 的规则引擎）"""
        message_lower = message.lower()

        greeting_keywords = ["你好", "hello", "hi", "嗨", "早上好", "下午好", "晚上好"]
        for kw in greeting_keywords:
            if kw in message_lower:
                return "你好！我是鸿蒙小雨。当前 Ollama 服务响应较慢，我暂时使用规则模式回复。简单的问题我可以直接回答，复杂问题请稍后再试。"

        help_keywords = ["帮助", "help", "功能", "能做什么"]
        for kw in help_keywords:
            if kw in message_lower:
                return ("我可以帮你：\n"
                        "1. 智能对话（需要 Ollama 服务）\n"
                        "2. 知识管理（Wiki 文档查询）\n"
                        "3. 系统监控和健康检查\n"
                        "4. 任务调度和执行\n"
                        "当前 Ollama 服务不可用，仅基础功能可用。")

        status_keywords = ["状态", "status", "健康", "health", "系统"]
        for kw in status_keywords:
            if kw in message_lower:
                return f"当前系统状态：服务级别={self.current_level.name}，Ollama 连续失败次数={self._consecutive_failures}"

        return "当前 Ollama 服务不可用，我暂时无法进行智能对话。你可以尝试：1) 检查 Ollama 是否运行 2) 稍后再试 3) 查询系统状态"

    def _minimal_response(self, message: str) -> str:
        """最小模式响应"""
        return "系统当前处于最小运行模式，Ollama 服务不可用。请检查 Ollama 服务状态后重试。"

    def get_status(self) -> Dict[str, Any]:
        """获取降级管理器状态"""
        recent_checks = self._check_history[-5:] if self._check_history else []
        return {
            "current_level": self.current_level.name,
            "current_level_value": int(self.current_level),
            "consecutive_failures": self._consecutive_failures,
            "ollama_host": self.ollama_host,
            "recent_checks": recent_checks,
            "level_descriptions": {
                "FULL": "完整模式 - Ollama 可用，所有功能正常",
                "RULE_BASED": "规则模式 - Ollama 不可用，使用规则引擎处理简单查询",
                "MINIMAL": "最小模式 - 仅保留基础对话和健康检查端点",
            }
        }


_degradation_manager: Optional[DegradationManager] = None


def get_degradation_manager() -> DegradationManager:
    """获取降级管理器单例"""
    global _degradation_manager
    if _degradation_manager is None:
        _degradation_manager = DegradationManager()
    return _degradation_manager
