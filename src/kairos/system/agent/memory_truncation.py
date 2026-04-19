# -*- coding: utf-8 -*-
"""
记忆截断引擎

双限制截断策略（行数 + 字节数），防止记忆入口文件膨胀：
- 行数上限：防止索引条目过多导致token浪费
- 字节数上限：防止长行索引条目绕过行数限制

漂移检测：识别记忆内容是否与当前状态不一致，
提醒系统验证记忆的时效性。

参考: Claude Code memdir.ts truncateEntrypointContent
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class TruncationReason(Enum):
    NONE = "none"
    LINE_LIMIT = "line_limit"
    BYTE_LIMIT = "byte_limit"
    BOTH_LIMITS = "both_limits"


@dataclass
class TruncationResult:
    content: str
    original_line_count: int
    original_byte_count: int
    result_line_count: int
    result_byte_count: int
    was_line_truncated: bool
    was_byte_truncated: bool
    reason: TruncationReason
    warning: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "original_line_count": self.original_line_count,
            "original_byte_count": self.original_byte_count,
            "result_line_count": self.result_line_count,
            "result_byte_count": self.result_byte_count,
            "was_line_truncated": self.was_line_truncated,
            "was_byte_truncated": self.was_byte_truncated,
            "reason": self.reason.value,
            "warning": self.warning,
        }


@dataclass
class DriftReport:
    entry_name: str
    drift_score: float
    is_stale: bool
    last_verified: Optional[str]
    age_days: float
    recommendation: str

    def to_dict(self) -> dict:
        return {
            "entry_name": self.entry_name,
            "drift_score": self.drift_score,
            "is_stale": self.is_stale,
            "last_verified": self.last_verified,
            "age_days": self.age_days,
            "recommendation": self.recommendation,
        }


class MemoryTruncator:
    """
    记忆截断器，对记忆入口内容执行双限制截断。

    截断策略：
    1. 先按行数截断（自然边界，保留完整行）
    2. 再按字节数截断（在最后一个换行符处切割，避免切断行）
    3. 追加警告说明哪个限制触发了截断
    """

    DEFAULT_MAX_LINES = 200
    DEFAULT_MAX_BYTES = 25000

    def __init__(self, max_lines: int = DEFAULT_MAX_LINES,
                 max_bytes: int = DEFAULT_MAX_BYTES):
        self._max_lines = max_lines
        self._max_bytes = max_bytes

    @property
    def max_lines(self) -> int:
        return self._max_lines

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    def truncate(self, content: str) -> TruncationResult:
        """
        对内容执行双限制截断。

        Args:
            content: 原始内容

        Returns:
            TruncationResult 包含截断后的内容和元信息
        """
        trimmed = content.strip()
        if not trimmed:
            return TruncationResult(
                content="",
                original_line_count=0,
                original_byte_count=0,
                result_line_count=0,
                result_byte_count=0,
                was_line_truncated=False,
                was_byte_truncated=False,
                reason=TruncationReason.NONE,
            )

        content_lines = trimmed.split('\n')
        original_line_count = len(content_lines)
        original_byte_count = len(trimmed.encode('utf-8'))

        was_line_truncated = original_line_count > self._max_lines
        was_byte_truncated = original_byte_count > self._max_bytes

        if not was_line_truncated and not was_byte_truncated:
            return TruncationResult(
                content=trimmed,
                original_line_count=original_line_count,
                original_byte_count=original_byte_count,
                result_line_count=original_line_count,
                result_byte_count=original_byte_count,
                was_line_truncated=False,
                was_byte_truncated=False,
                reason=TruncationReason.NONE,
            )

        truncated = trimmed
        if was_line_truncated:
            truncated = '\n'.join(content_lines[:self._max_lines])

        byte_truncated_flag = was_byte_truncated
        truncated_bytes = len(truncated.encode('utf-8'))
        if truncated_bytes > self._max_bytes:
            byte_truncated_flag = True
            cut_at = truncated.rfind('\n', 0, self._max_bytes)
            if cut_at > 0:
                truncated = truncated[:cut_at]
            else:
                truncated = truncated[:self._max_bytes]

        if was_line_truncated and byte_truncated_flag:
            reason = TruncationReason.BOTH_LIMITS
        elif was_line_truncated:
            reason = TruncationReason.LINE_LIMIT
        else:
            reason = TruncationReason.BYTE_LIMIT

        warning = self._build_warning(
            reason, original_line_count, original_byte_count
        )

        result_lines = truncated.count('\n') + 1
        result_bytes = len(truncated.encode('utf-8'))

        return TruncationResult(
            content=truncated + '\n\n' + warning if warning else truncated,
            original_line_count=original_line_count,
            original_byte_count=original_byte_count,
            result_line_count=result_lines,
            result_byte_count=result_bytes,
            was_line_truncated=was_line_truncated,
            was_byte_truncated=byte_truncated_flag,
            reason=reason,
            warning=warning,
        )

    def _build_warning(self, reason: TruncationReason,
                       line_count: int, byte_count: int) -> str:
        if reason == TruncationReason.LINE_LIMIT:
            return (
                f"> 警告: 记忆入口超过行数限制 "
                f"({line_count}行，上限{self._max_lines}行)。"
                f"仅加载了部分内容。请保持索引条目每行不超过200字符，"
                f"将详细信息移至主题文件。"
            )
        elif reason == TruncationReason.BYTE_LIMIT:
            return (
                f"> 警告: 记忆入口超过字节限制 "
                f"({self._format_size(byte_count)}，"
                f"上限{self._format_size(self._max_bytes)})。"
                f"索引条目过长。请保持索引简洁，将详细信息移至主题文件。"
            )
        elif reason == TruncationReason.BOTH_LIMITS:
            return (
                f"> 警告: 记忆入口同时超过行数和字节限制 "
                f"({line_count}行，{self._format_size(byte_count)})。"
                f"仅加载了部分内容。请精简索引条目。"
            )
        return ""

    @staticmethod
    def _format_size(size: int) -> str:
        if size < 1024:
            return f"{size}B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f}KB"
        else:
            return f"{size / (1024 * 1024):.1f}MB"

    def check_limits(self, content: str) -> Dict:
        """检查内容是否超限，不执行截断"""
        trimmed = content.strip()
        if not trimmed:
            return {
                "within_limits": True,
                "line_count": 0,
                "byte_count": 0,
                "line_limit": self._max_lines,
                "byte_limit": self._max_bytes,
            }

        lines = trimmed.split('\n')
        byte_count = len(trimmed.encode('utf-8'))
        line_count = len(lines)

        return {
            "within_limits": line_count <= self._max_lines and byte_count <= self._max_bytes,
            "line_count": line_count,
            "byte_count": byte_count,
            "line_limit": self._max_lines,
            "byte_limit": self._max_bytes,
            "line_usage": f"{line_count}/{self._max_lines}",
            "byte_usage": f"{self._format_size(byte_count)}/{self._format_size(self._max_bytes)}",
        }


class MemoryDriftDetector:
    """
    记忆漂移检测器，识别记忆内容是否与当前状态不一致。

    漂移信号：
    - 时间衰减：记忆越老，越可能过时
    - 引用失效：记忆中提到的文件/函数可能已不存在
    - 上下文矛盾：记忆内容与当前对话上下文矛盾

    参考: Claude Code MEMORY_DRIFT_CAVEAT + memoryAge.ts
    """

    STALE_THRESHOLD_DAYS = 30.0
    WARNING_THRESHOLD_DAYS = 7.0

    def __init__(self, stale_days: float = STALE_THRESHOLD_DAYS,
                 warning_days: float = WARNING_THRESHOLD_DAYS):
        self._stale_days = stale_days
        self._warning_days = warning_days
        self._verification_log: Dict[str, str] = {}

    def check_drift(self, entry_name: str, created_at: str,
                    last_verified: Optional[str] = None) -> DriftReport:
        """
        检查记忆条目的漂移状态。

        Args:
            entry_name: 条目名称
            created_at: 创建时间 ISO格式
            last_verified: 最后验证时间 ISO格式

        Returns:
            DriftReport 包含漂移评估结果
        """
        try:
            created = datetime.fromisoformat(created_at)
        except (ValueError, TypeError):
            return DriftReport(
                entry_name=entry_name,
                drift_score=0.5,
                is_stale=False,
                last_verified=last_verified,
                age_days=0,
                recommendation="无法解析创建时间，建议验证记忆内容",
            )

        now = datetime.now()
        age_days = (now - created).total_seconds() / 86400

        verified_age = age_days
        if last_verified:
            try:
                verified = datetime.fromisoformat(last_verified)
                verified_age = (now - verified).total_seconds() / 86400
            except (ValueError, TypeError):
                verified_age = age_days

        drift_score = self._calculate_drift_score(age_days, verified_age)
        is_stale = drift_score >= 0.7

        recommendation = self._generate_recommendation(
            drift_score, age_days, is_stale
        )

        return DriftReport(
            entry_name=entry_name,
            drift_score=round(drift_score, 3),
            is_stale=is_stale,
            last_verified=last_verified,
            age_days=round(age_days, 1),
            recommendation=recommendation,
        )

    def _calculate_drift_score(self, age_days: float,
                               verified_age: float) -> float:
        """计算漂移分数（0-1，越高越可能过时）"""
        age_factor = min(1.0, age_days / self._stale_days)
        verified_factor = min(1.0, verified_age / self._stale_days) * 0.7
        return min(1.0, age_factor * 0.6 + verified_factor * 0.4)

    def _generate_recommendation(self, drift_score: float,
                                 age_days: float,
                                 is_stale: bool) -> str:
        if is_stale:
            return (
                f"记忆已过时（{age_days:.0f}天前创建，漂移分数{drift_score:.2f}）。"
                f"建议验证当前状态后再依赖此记忆。"
            )
        elif drift_score >= 0.4:
            return (
                f"记忆可能过时（{age_days:.0f}天前创建，漂移分数{drift_score:.2f}）。"
                f"建议在关键决策前验证。"
            )
        else:
            return "记忆较新，可信度较高。"

    def record_verification(self, entry_name: str) -> None:
        """记录验证时间"""
        self._verification_log[entry_name] = datetime.now().isoformat()

    def get_freshness_text(self, age_days: float) -> str:
        """生成新鲜度提示文本"""
        if age_days < 1:
            return "今天"
        elif age_days < 2:
            return "昨天"
        else:
            return f"{int(age_days)}天前"

    def get_freshness_warning(self, age_days: float) -> Optional[str]:
        """如果记忆较旧，返回新鲜度警告"""
        if age_days <= 1:
            return None
        return (
            f"注意: 此记忆创建于{self.get_freshness_text(age_days)}，"
            f"内容可能已过时。使用前请验证当前状态。"
        )


class MemoryTruncationEngine:
    """
    记忆截断引擎，整合截断器与漂移检测器。

    提供：
    - 双限制截断（行数 + 字节数）
    - 漂移检测与新鲜度追踪
    - 批量检查与报告
    """

    def __init__(self, max_lines: int = MemoryTruncator.DEFAULT_MAX_LINES,
                 max_bytes: int = MemoryTruncator.DEFAULT_MAX_BYTES,
                 stale_days: float = MemoryDriftDetector.STALE_THRESHOLD_DAYS):
        self._truncator = MemoryTruncator(max_lines, max_bytes)
        self._drift_detector = MemoryDriftDetector(stale_days)
        self._stats = {
            "truncations": 0,
            "line_truncations": 0,
            "byte_truncations": 0,
            "drift_checks": 0,
            "stale_detected": 0,
        }

    def truncate(self, content: str) -> TruncationResult:
        """执行截断"""
        result = self._truncator.truncate(content)
        if result.was_line_truncated or result.was_byte_truncated:
            self._stats["truncations"] += 1
            if result.was_line_truncated:
                self._stats["line_truncations"] += 1
            if result.was_byte_truncated:
                self._stats["byte_truncations"] += 1
        return result

    def check_drift(self, entry_name: str, created_at: str,
                    last_verified: Optional[str] = None) -> DriftReport:
        """检查漂移"""
        self._stats["drift_checks"] += 1
        report = self._drift_detector.check_drift(
            entry_name, created_at, last_verified
        )
        if report.is_stale:
            self._stats["stale_detected"] += 1
        return report

    def check_limits(self, content: str) -> Dict:
        """检查限制"""
        return self._truncator.check_limits(content)

    def record_verification(self, entry_name: str) -> None:
        """记录验证"""
        self._drift_detector.record_verification(entry_name)

    def get_freshness_warning(self, age_days: float) -> Optional[str]:
        """获取新鲜度警告"""
        return self._drift_detector.get_freshness_warning(age_days)

    def get_statistics(self) -> dict:
        """获取统计"""
        return self._stats.copy()


_truncation_engine: Optional[MemoryTruncationEngine] = None


def get_truncation_engine() -> MemoryTruncationEngine:
    """获取记忆截断引擎单例"""
    global _truncation_engine
    if _truncation_engine is None:
        _truncation_engine = MemoryTruncationEngine()
    return _truncation_engine
