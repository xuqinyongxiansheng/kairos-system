"""
成本追踪系统
借鉴 cc-haha-main 的 cost-tracker.ts + modelCost.ts：
1. 按模型统计成本（inputTokens、outputTokens、costUSD）
2. 会话持久化（跨会话恢复成本数据）
3. 格式化输出（总成本、API时长、代码变更统计）
4. 本地模型零成本模式（仅统计使用量）
"""

import os
import time
import json
import logging
import threading
import tempfile
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger("CostTracker")

DATA_DIR = os.environ.get("GEMMA4_DATA_DIR", "data")
COST_FILE = os.path.join(DATA_DIR, "cost_state.json")

LOCAL_MODEL_COST_PER_MILLION = {
    "input": 0.0,
    "output": 0.0,
    "cache_read": 0.0,
    "cache_creation": 0.0,
}

CLOUD_MODEL_COSTS = {
    "claude-3-opus": {"input": 15.0, "output": 75.0, "cache_read": 1.5, "cache_creation": 18.75},
    "claude-3-sonnet": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_creation": 3.75},
    "claude-3-haiku": {"input": 0.25, "output": 1.25, "cache_read": 0.03, "cache_creation": 0.3},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0, "cache_read": 0.0, "cache_creation": 0.0},
    "gpt-4o": {"input": 5.0, "output": 15.0, "cache_read": 2.5, "cache_creation": 0.0},
    "gemma4:e4b": LOCAL_MODEL_COST_PER_MILLION,
    "qwen2.5:32b": LOCAL_MODEL_COST_PER_MILLION,
}


@dataclass
class ModelCostRecord:
    model_name: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    request_count: int = 0
    cost_usd: float = 0.0
    first_request: float = 0.0
    last_request: float = 0.0

    def add(self, input_tokens: int, output_tokens: int,
            cache_read: int = 0, cache_creation: int = 0):
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.cache_read_tokens += cache_read
        self.cache_creation_tokens += cache_creation
        self.request_count += 1
        now = time.time()
        if self.first_request == 0.0:
            self.first_request = now
        self.last_request = now
        self._recalculate_cost()

    def _recalculate_cost(self):
        costs = CLOUD_MODEL_COSTS.get(self.model_name, LOCAL_MODEL_COST_PER_MILLION)
        self.cost_usd = (
            self.input_tokens * costs["input"] / 1_000_000
            + self.output_tokens * costs["output"] / 1_000_000
            + self.cache_read_tokens * costs["cache_read"] / 1_000_000
            + self.cache_creation_tokens * costs["cache_creation"] / 1_000_000
        )


class CostTracker:
    """成本追踪器"""

    def __init__(self):
        self._model_costs: Dict[str, ModelCostRecord] = {}
        self._session_start = time.time()
        self._code_changes: Dict[str, int] = defaultdict(int)
        self._total_cost_usd = 0.0
        self._is_local_model = True
        self._lock = threading.Lock()

    def record_usage(self, model: str, input_tokens: int, output_tokens: int,
                     cache_read: int = 0, cache_creation: int = 0):
        """记录模型使用和成本"""
        with self._lock:
            if model not in self._model_costs:
                self._model_costs[model] = ModelCostRecord(model_name=model)
                if model not in CLOUD_MODEL_COSTS or CLOUD_MODEL_COSTS[model] == LOCAL_MODEL_COST_PER_MILLION:
                    self._is_local_model = True

            self._model_costs[model].add(input_tokens, output_tokens, cache_read, cache_creation)
            self._total_cost_usd = sum(m.cost_usd for m in self._model_costs.values())

    def record_code_change(self, change_type: str):
        """记录代码变更"""
        self._code_changes[change_type] += 1

    def get_model_cost(self, model: str) -> Dict[str, Any]:
        record = self._model_costs.get(model)
        if not record:
            return {}
        return {
            "model": record.model_name,
            "input_tokens": record.input_tokens,
            "output_tokens": record.output_tokens,
            "cache_read_tokens": record.cache_read_tokens,
            "cache_creation_tokens": record.cache_creation_tokens,
            "request_count": record.request_count,
            "cost_usd": round(record.cost_usd, 6),
            "duration_seconds": round(record.last_request - record.first_request, 1) if record.first_request else 0,
        }

    def get_total_cost(self) -> Dict[str, Any]:
        """获取总成本"""
        total_input = sum(m.input_tokens for m in self._model_costs.values())
        total_output = sum(m.output_tokens for m in self._model_costs.values())
        total_requests = sum(m.request_count for m in self._model_costs.values())
        session_duration = time.time() - self._session_start

        return {
            "total_cost_usd": round(self._total_cost_usd, 6),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_requests": total_requests,
            "session_duration_seconds": round(session_duration, 1),
            "is_local_model": self._is_local_model,
            "models": len(self._model_costs),
            "code_changes": dict(self._code_changes),
        }

    def format_cost_report(self) -> str:
        """格式化成本报告"""
        total = self.get_total_cost()
        lines = ["成本报告", "=" * 40, ""]

        if self._is_local_model:
            lines.append("模式: 本地模型（零成本）")
        else:
            lines.append(f"总成本: ${total['total_cost_usd']:.4f}")

        lines.append(f"总输入 Token: {total['total_input_tokens']:,}")
        lines.append(f"总输出 Token: {total['total_output_tokens']:,}")
        lines.append(f"总请求次数: {total['total_requests']}")
        lines.append(f"会话时长: {total['session_duration_seconds']:.0f}秒")
        lines.append("")

        if self._model_costs:
            lines.append("按模型统计:")
            for model, record in self._model_costs.items():
                lines.append(f"  {model}:")
                lines.append(f"    输入: {record.input_tokens:,} | 输出: {record.output_tokens:,}")
                if record.cost_usd > 0:
                    lines.append(f"    成本: ${record.cost_usd:.4f}")
                lines.append(f"    请求: {record.request_count}")

        if self._code_changes:
            lines.append("")
            lines.append("代码变更:")
            for change_type, count in self._code_changes.items():
                lines.append(f"  {change_type}: {count}")

        return "\n".join(lines)

    def save_session(self):
        """保存当前会话成本"""
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            data = {
                "session_start": self._session_start,
                "total_cost_usd": self._total_cost_usd,
                "models": {
                    name: {
                        "input_tokens": m.input_tokens,
                        "output_tokens": m.output_tokens,
                        "cache_read_tokens": m.cache_read_tokens,
                        "cache_creation_tokens": m.cache_creation_tokens,
                        "request_count": m.request_count,
                        "cost_usd": m.cost_usd,
                    }
                    for name, m in self._model_costs.items()
                },
                "code_changes": dict(self._code_changes),
                "saved_at": time.time(),
            }
            tmp_fd, tmp_path = tempfile.mkstemp(
                dir=DATA_DIR, suffix=".tmp", prefix="cost_"
            )
            try:
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, COST_FILE)
            except Exception:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise
        except Exception as e:
            logger.error(f"成本数据保存失败: {e}")

    def restore_session(self) -> bool:
        """恢复会话成本数据"""
        try:
            if not os.path.exists(COST_FILE):
                return False
            with open(COST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._session_start = data.get("session_start", time.time())
            self._total_cost_usd = data.get("total_cost_usd", 0.0)
            self._code_changes = defaultdict(int, data.get("code_changes", {}))

            for name, m_data in data.get("models", {}).items():
                record = ModelCostRecord(model_name=name)
                record.input_tokens = m_data.get("input_tokens", 0)
                record.output_tokens = m_data.get("output_tokens", 0)
                record.cache_read_tokens = m_data.get("cache_read_tokens", 0)
                record.cache_creation_tokens = m_data.get("cache_creation_tokens", 0)
                record.request_count = m_data.get("request_count", 0)
                record.cost_usd = m_data.get("cost_usd", 0.0)
                self._model_costs[name] = record

            logger.info(f"成本数据恢复: {len(self._model_costs)} 个模型")
            return True
        except Exception as e:
            logger.error(f"成本数据恢复失败: {e}")
            return False

    def reset(self):
        self._model_costs.clear()
        self._code_changes.clear()
        self._total_cost_usd = 0.0
        self._session_start = time.time()


_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker
