# -*- coding: utf-8 -*-
"""
反射Agent (ReflexAgent)
快速模式匹配，高置信度触发
适用于: 简单查询、已知模式、快速响应场景

特征:
- 延迟 < 100ms
- 置信度阈值 > 0.8
- 模式缓存加速
- 无深度推理
"""

import logging
import time
from typing import Dict, Any, List, Optional
from difflib import SequenceMatcher

from .base_neuron_agent import BaseNeuronAgent, AgentCapability, AgentDecision
from ..core.enums import AgentType

logger = logging.getLogger("ReflexAgent")


class ReflexAgent(BaseNeuronAgent):
    """
    反射Agent - 快速模式匹配
    
    触发条件: confidence > 0.8
    响应时间: < 100ms
    适用场景: 简单查询、已知模式、快速响应
    """

    def __init__(self, agent_id: str = "reflex_agent"):
        capabilities = [
            AgentCapability(
                name="pattern_match",
                description="快速模式匹配",
                confidence_threshold=0.8,
                avg_latency_ms=20.0
            ),
            AgentCapability(
                name="simple_query",
                description="简单查询响应",
                confidence_threshold=0.9,
                avg_latency_ms=10.0
            ),
            AgentCapability(
                name="cached_response",
                description="缓存响应",
                confidence_threshold=0.85,
                avg_latency_ms=5.0
            ),
        ]
        super().__init__(agent_id, AgentType.REFLEX, capabilities)

        self._patterns: Dict[str, Dict[str, Any]] = {}
        self._response_cache: Dict[str, Any] = {}
        self._max_cache_size = 500
        self._similarity_threshold = 0.75

        self._register_default_patterns()

    def _register_default_patterns(self):
        """注册默认模式"""
        default_patterns = {
            "greeting": {
                "patterns": ["你好", "hello", "hi", "嗨", "早上好", "晚上好"],
                "response": {"action": "greet", "confidence": 0.95},
                "category": "social"
            },
            "status_query": {
                "patterns": ["状态", "status", "怎么样", "运行情况", "系统状态"],
                "response": {"action": "get_status", "confidence": 0.9},
                "category": "system"
            },
            "help": {
                "patterns": ["帮助", "help", "怎么用", "使用方法", "功能"],
                "response": {"action": "show_help", "confidence": 0.92},
                "category": "system"
            },
            "cancel": {
                "patterns": ["取消", "cancel", "停止", "stop", "终止"],
                "response": {"action": "cancel_task", "confidence": 0.88},
                "category": "control"
            },
            "confirm": {
                "patterns": ["确认", "yes", "好的", "ok", "确定", "同意"],
                "response": {"action": "confirm", "confidence": 0.9},
                "category": "control"
            },
            "deny": {
                "patterns": ["拒绝", "no", "不", "取消", "否定"],
                "response": {"action": "deny", "confidence": 0.9},
                "category": "control"
            }
        }
        self._patterns.update(default_patterns)

    def register_pattern(self, name: str, patterns: List[str],
                        response: Dict[str, Any], category: str = "custom"):
        """
        注册模式
        
        Args:
            name: 模式名称
            patterns: 模式列表
            response: 响应定义
            category: 类别
        """
        self._patterns[name] = {
            "patterns": patterns,
            "response": response,
            "category": category
        }
        logger.info(f"注册反射模式: {name} ({len(patterns)} 个变体)")

    def can_handle(self, task: str, confidence: float) -> bool:
        """判断是否能快速处理"""
        if confidence < 0.8:
            return False

        cache_key = task.lower().strip()
        if cache_key in self._response_cache:
            return True

        for pattern_data in self._patterns.values():
            for pattern in pattern_data["patterns"]:
                if pattern.lower() in task.lower():
                    return True

        for pattern_data in self._patterns.values():
            for pattern in pattern_data["patterns"]:
                similarity = SequenceMatcher(None, task.lower(), pattern.lower()).ratio()
                if similarity > self._similarity_threshold:
                    return True

        return False

    async def process(self, content: Dict[str, Any]) -> AgentDecision:
        """快速处理"""
        task = content.get("task", "")
        confidence = content.get("confidence", 0.5)

        cache_key = task.lower().strip()
        if cache_key in self._response_cache:
            cached = self._response_cache[cache_key]
            return AgentDecision(
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                action=cached["action"],
                confidence=cached.get("confidence", 0.95),
                reasoning=f"缓存命中: {cache_key[:30]}",
                evidence=[{"source": "cache", "key": cache_key}]
            )

        best_match = None
        best_similarity = 0.0

        for name, pattern_data in self._patterns.items():
            for pattern in pattern_data["patterns"]:
                if pattern.lower() in task.lower():
                    best_match = (name, pattern_data, 1.0)
                    break

                similarity = SequenceMatcher(None, task.lower(), pattern.lower()).ratio()
                if similarity > best_similarity and similarity > self._similarity_threshold:
                    best_similarity = similarity
                    best_match = (name, pattern_data, similarity)

            if best_match and best_match[2] == 1.0:
                break

        if best_match:
            name, pattern_data, similarity = best_match
            response = pattern_data["response"]
            final_confidence = min(confidence, response.get("confidence", 0.9)) * similarity

            self._add_to_cache(cache_key, response)

            return AgentDecision(
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                action=response["action"],
                confidence=final_confidence,
                reasoning=f"模式匹配: {name} (相似度: {similarity:.2f})",
                evidence=[
                    {"source": "pattern", "name": name, "similarity": similarity},
                    {"source": "category", "value": pattern_data.get("category", "unknown")}
                ],
                metadata={"pattern_name": name, "similarity": similarity}
            )

        return AgentDecision(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            action="no_match",
            confidence=0.0,
            reasoning="无匹配模式，建议转交DeliberativeAgent"
        )

    def _add_to_cache(self, key: str, response: Dict[str, Any]):
        """添加到缓存"""
        if len(self._response_cache) >= self._max_cache_size:
            oldest_key = next(iter(self._response_cache))
            del self._response_cache[oldest_key]
        self._response_cache[key] = response

    def get_pattern_stats(self) -> Dict[str, Any]:
        """获取模式统计"""
        return {
            "total_patterns": len(self._patterns),
            "cache_size": len(self._response_cache),
            "categories": list(set(
                p.get("category", "unknown") for p in self._patterns.values()
            ))
        }
