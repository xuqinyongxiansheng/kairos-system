"""
Token 追踪与预算系统
借鉴 cc-haha-main 的 tokenEstimation.ts + tokenBudget.ts：
1. 多层次 token 估算（精确API计数 + 粗略估算）
2. 预算追踪器（收益递减检测、阈值控制）
3. 预算决策引擎（90%阈值继续、收益递减停止）
4. 按模型/类型统计 token 消耗
"""

import os
import time
import json
import logging
import asyncio
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger("TokenTracker")

DEFAULT_CONTEXT_WINDOW = 8192
DEFAULT_BUDGET_THRESHOLD = 0.9
DEFAULT_DIMINISHING_RETURNS_THRESHOLD = 0.5


class EstimationMethod(Enum):
    ROUGH = "rough"
    API = "api"
    FALLBACK = "fallback"


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    total_tokens: int = 0
    estimation_method: EstimationMethod = EstimationMethod.ROUGH
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens


@dataclass
class ModelUsage:
    model_name: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    total_tokens: int = 0
    request_count: int = 0
    first_request_time: float = 0.0
    last_request_time: float = 0.0

    def add_usage(self, usage: TokenUsage):
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.cache_read_tokens += usage.cache_read_tokens
        self.cache_creation_tokens += usage.cache_creation_tokens
        self.total_tokens += usage.total_tokens
        self.request_count += 1
        now = time.time()
        if self.first_request_time == 0.0:
            self.first_request_time = now
        self.last_request_time = now


@dataclass
class BudgetDecision:
    should_continue: bool
    reason: str
    usage_percent: float
    remaining_tokens: int
    diminishing_returns: bool = False


class BudgetTracker:
    """预算追踪器 - 收益递减检测"""

    def __init__(self, context_window: int = DEFAULT_CONTEXT_WINDOW):
        self.context_window = context_window
        self.continuation_count = 0
        self.last_delta_tokens = 0
        self.delta_history: List[int] = []
        self.max_delta_history = 10
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def record_continuation(self, input_tokens: int, output_tokens: int):
        self.continuation_count += 1
        delta = output_tokens - self.last_delta_tokens
        self.delta_history.append(delta)
        if len(self.delta_history) > self.max_delta_history:
            self.delta_history = self.delta_history[-self.max_delta_history:]
        self.last_delta_tokens = output_tokens
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

    def check_diminishing_returns(self) -> bool:
        if len(self.delta_history) < 3:
            return False
        recent = self.delta_history[-3:]
        if all(d <= 0 for d in recent):
            return True
        avg_recent = sum(recent) / len(recent)
        if len(self.delta_history) >= 5:
            earlier = self.delta_history[-max(len(self.delta_history), 5):-3]
            if earlier:
                avg_earlier = sum(earlier) / len(earlier)
                if avg_earlier > 0 and avg_recent / avg_earlier < DEFAULT_DIMINISHING_RETURNS_THRESHOLD:
                    return True
        return False

    def get_usage_percent(self) -> float:
        total = self.total_input_tokens + self.total_output_tokens
        return total / self.context_window if self.context_window > 0 else 0.0

    def reset(self):
        self.continuation_count = 0
        self.last_delta_tokens = 0
        self.delta_history.clear()
        self.total_input_tokens = 0
        self.total_output_tokens = 0


class TokenTracker:
    """Token 追踪器 - 多层次估算 + 预算控制"""

    def __init__(self, context_window: int = None):
        self.context_window = context_window or int(os.environ.get(
            "GEMMA4_CONTEXT_WINDOW", str(DEFAULT_CONTEXT_WINDOW)
        ))
        self._model_usage: Dict[str, ModelUsage] = {}
        self._usage_history: List[TokenUsage] = []
        self._max_history = 1000
        self._budget_tracker = BudgetTracker(self.context_window)
        self._session_start = time.time()
        self._total_requests = 0

    def rough_estimate(self, text: str) -> int:
        """粗略 token 估算：中文约 1.5 字/token，英文约 4 字符/token"""
        if not text:
            return 0
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)

    def estimate_messages(self, messages: List[Dict[str, str]]) -> int:
        """估算消息列表的 token 数量"""
        total = 0
        for msg in messages:
            total += self.rough_estimate(msg.get("content", ""))
            total += 4
        return total

    def estimate_messages_by_type(self, messages: List[Dict[str, str]]) -> Dict[str, int]:
        """按消息类型统计 token 分布"""
        by_type: Dict[str, int] = defaultdict(int)
        for msg in messages:
            role = msg.get("role", "unknown")
            tokens = self.rough_estimate(msg.get("content", ""))
            by_type[role] += tokens
        return dict(by_type)

    def record_usage(self, model: str, input_tokens: int, output_tokens: int,
                     cache_read: int = 0, cache_creation: int = 0,
                     method: EstimationMethod = EstimationMethod.ROUGH) -> TokenUsage:
        """记录 token 使用"""
        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read,
            cache_creation_tokens=cache_creation,
            estimation_method=method,
        )

        if model not in self._model_usage:
            self._model_usage[model] = ModelUsage(model_name=model)
        self._model_usage[model].add_usage(usage)

        self._usage_history.append(usage)
        if len(self._usage_history) > self._max_history:
            self._usage_history = self._usage_history[-self._max_history:]

        self._budget_tracker.record_continuation(input_tokens, output_tokens)
        self._total_requests += 1

        return usage

    def record_from_response(self, model: str, response: Dict[str, Any]) -> Optional[TokenUsage]:
        """从 API 响应中提取并记录 token 使用"""
        eval_count = response.get("eval_count") or response.get("prompt_eval_count", 0)
        prompt_eval = response.get("prompt_eval_count", 0)
        eval_tokens = response.get("eval_count", 0)

        if prompt_eval or eval_tokens:
            return self.record_usage(
                model=model,
                input_tokens=prompt_eval,
                output_tokens=eval_tokens,
                method=EstimationMethod.API,
            )
        return None

    def check_budget(self, current_messages: List[Dict[str, str]] = None) -> BudgetDecision:
        """检查 token 预算，返回决策"""
        usage_percent = self._budget_tracker.get_usage_percent()
        remaining = max(0, self.context_window - int(self.context_window * usage_percent))
        diminishing = self._budget_tracker.check_diminishing_returns()

        if current_messages:
            current_tokens = self.estimate_messages(current_messages)
            usage_percent = current_tokens / self.context_window if self.context_window > 0 else 0.0
            remaining = max(0, self.context_window - current_tokens)

        if diminishing:
            return BudgetDecision(
                should_continue=False,
                reason="收益递减检测：输出增量持续下降，建议停止",
                usage_percent=usage_percent,
                remaining_tokens=remaining,
                diminishing_returns=True,
            )

        if usage_percent >= 1.0:
            return BudgetDecision(
                should_continue=False,
                reason="上下文窗口已满，无法继续",
                usage_percent=usage_percent,
                remaining_tokens=0,
            )

        if usage_percent >= DEFAULT_BUDGET_THRESHOLD:
            return BudgetDecision(
                should_continue=True,
                reason=f"已使用 {usage_percent:.1%} 上下文窗口，接近阈值",
                usage_percent=usage_percent,
                remaining_tokens=remaining,
            )

        return BudgetDecision(
            should_continue=True,
            reason="预算充足",
            usage_percent=usage_percent,
            remaining_tokens=remaining,
        )

    def get_model_usage(self, model: str = None) -> Dict[str, Any]:
        """获取模型使用统计"""
        if model:
            mu = self._model_usage.get(model)
            if not mu:
                return {}
            return {
                "model": mu.model_name,
                "input_tokens": mu.input_tokens,
                "output_tokens": mu.output_tokens,
                "cache_read_tokens": mu.cache_read_tokens,
                "cache_creation_tokens": mu.cache_creation_tokens,
                "total_tokens": mu.total_tokens,
                "request_count": mu.request_count,
                "duration_seconds": round(mu.last_request_time - mu.first_request_time, 1) if mu.first_request_time else 0,
            }
        return {name: self.get_model_usage(name) for name in self._model_usage}

    def get_stats(self) -> Dict[str, Any]:
        """获取完整统计"""
        total_input = sum(m.input_tokens for m in self._model_usage.values())
        total_output = sum(m.output_tokens for m in self._model_usage.values())
        total_all = total_input + total_output
        session_duration = time.time() - self._session_start

        return {
            "total_tokens": total_all,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_requests": self._total_requests,
            "context_window": self.context_window,
            "usage_percent": round(total_all / self.context_window * 100, 1) if self.context_window > 0 else 0,
            "session_duration_seconds": round(session_duration, 1),
            "models": len(self._model_usage),
            "continuation_count": self._budget_tracker.continuation_count,
            "diminishing_returns": self._budget_tracker.check_diminishing_returns(),
            "model_details": self.get_model_usage(),
        }

    def reset_session(self):
        """重置会话统计"""
        self._model_usage.clear()
        self._usage_history.clear()
        self._budget_tracker.reset()
        self._session_start = time.time()
        self._total_requests = 0


_token_tracker: Optional[TokenTracker] = None


def get_token_tracker() -> TokenTracker:
    global _token_tracker
    if _token_tracker is None:
        _token_tracker = TokenTracker()
    return _token_tracker
