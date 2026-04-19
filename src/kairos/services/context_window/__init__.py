"""
上下文窗口管理
借鉴 cc-haha-main 的 context.ts + contextAnalysis.ts + contextSuggestions.ts：
1. 分层上下文构建（系统上下文 + 用户上下文）
2. Token 统计分析（按类型/角色/附件统计分布）
3. 上下文窗口升级检查（大窗口模型检测）
4. Git 状态注入（分支、状态、最近提交）
5. 上下文建议（压缩建议、文件清理建议）
"""

import os
import time
import json
import logging
import asyncio
import subprocess
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from functools import lru_cache
from collections import defaultdict

logger = logging.getLogger("ContextWindow")

DEFAULT_CONTEXT_WINDOW = 8192
LARGE_CONTEXT_WINDOW = 128000
FULL_CONTEXT_WINDOW = 1000000


class ContextCategory(Enum):
    SYSTEM_PROMPT = "system_prompt"
    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE = "assistant_message"
    TOOL_RESULT = "tool_result"
    ATTACHMENT = "attachment"
    CLAUDE_MD = "claude_md"
    GIT_CONTEXT = "git_context"


@dataclass
class ContextAnalysis:
    total_tokens: int = 0
    context_window: int = 0
    usage_percent: float = 0.0
    by_category: Dict[str, int] = field(default_factory=dict)
    by_role: Dict[str, int] = field(default_factory=dict)
    duplicate_file_reads: List[str] = field(default_factory=list)
    largest_messages: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.context_window - self.total_tokens)

    @property
    def is_near_limit(self) -> bool:
        return self.usage_percent > 0.8


@dataclass
class ContextUpgradeCheck:
    current_window: int
    available_windows: List[int]
    can_upgrade: bool
    upgrade_model: Optional[str] = None
    reason: str = ""


@dataclass
class GitContext:
    branch: str = ""
    status: str = ""
    recent_commits: List[str] = field(default_factory=list)
    dirty: bool = False

    def to_system_message(self) -> str:
        parts = []
        if self.branch:
            parts.append(f"当前分支: {self.branch}")
        if self.dirty:
            parts.append(f"工作区状态: 有未提交的变更")
        if self.recent_commits:
            parts.append("最近提交:")
            for c in self.recent_commits[:3]:
                parts.append(f"  {c}")
        return "\n".join(parts) if parts else ""


class ContextWindowManager:
    """上下文窗口管理器"""

    def __init__(self, context_window: int = None):
        self.context_window = context_window or int(os.environ.get(
            "GEMMA4_CONTEXT_WINDOW", str(DEFAULT_CONTEXT_WINDOW)
        ))
        self._system_context_cache: Optional[str] = None
        self._user_context_cache: Optional[str] = None
        self._cache_timestamp: float = 0.0
        self._cache_ttl = 300.0
        self._claude_md_path = os.environ.get(
            "GEMMA4_CLAUDE_MD", "CLAUDE.md"
        )
        self._break_cache_counter = 0

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)

    def get_system_context(self, force_refresh: bool = False) -> str:
        """获取系统上下文（git状态、缓存破坏器）"""
        now = time.time()
        if (not force_refresh and self._system_context_cache
                and now - self._cache_timestamp < self._cache_ttl):
            return self._system_context_cache

        parts = []
        git_ctx = self._get_git_context()
        git_msg = git_ctx.to_system_message()
        if git_msg:
            parts.append(git_msg)

        parts.append(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        self._break_cache_counter += 1
        parts.append(f"[cache_id: {self._break_cache_counter}]")

        self._system_context_cache = "\n".join(parts)
        self._cache_timestamp = now
        return self._system_context_cache

    def get_user_context(self) -> str:
        """获取用户上下文（CLAUDE.md 配置）"""
        if self._user_context_cache is not None:
            return self._user_context_cache

        if os.path.exists(self._claude_md_path):
            try:
                with open(self._claude_md_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    self._user_context_cache = f"[用户配置]\n{content}"
                    return self._user_context_cache
            except Exception as e:
                logger.warning(f"读取 CLAUDE.md 失败: {e}")

        self._user_context_cache = ""
        return self._user_context_cache

    def invalidate_cache(self):
        """使缓存失效"""
        self._system_context_cache = None
        self._user_context_cache = None
        self._cache_timestamp = 0.0

    def _get_git_context(self) -> GitContext:
        """获取 Git 上下文信息"""
        ctx = GitContext()
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=5,
                cwd=os.getcwd(),
            )
            if result.returncode == 0:
                ctx.branch = result.stdout.strip()

            result = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True, text=True, timeout=5,
                cwd=os.getcwd(),
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                lines = [l for l in lines if l.strip()]
                ctx.dirty = len(lines) > 0
                if ctx.dirty:
                    ctx.status = f"{len(lines)} 个文件变更"

            result = subprocess.run(
                ["git", "log", "--oneline", "-5"],
                capture_output=True, text=True, timeout=5,
                cwd=os.getcwd(),
            )
            if result.returncode == 0:
                ctx.recent_commits = [
                    line.strip() for line in result.stdout.strip().split("\n") if line.strip()
                ]
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

        return ctx

    def analyze_context(self, messages: List[Dict[str, str]]) -> ContextAnalysis:
        """分析上下文 token 分布"""
        analysis = ContextAnalysis(context_window=self.context_window)

        by_category: Dict[str, int] = defaultdict(int)
        by_role: Dict[str, int] = defaultdict(int)
        file_read_counts: Dict[str, int] = defaultdict(int)
        message_sizes: List[Dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            tokens = self._estimate_tokens(content)

            by_role[role] += tokens
            analysis.total_tokens += tokens

            if role == "system":
                by_category[ContextCategory.SYSTEM_PROMPT.value] += tokens
            elif role == "user":
                by_category[ContextCategory.USER_MESSAGE.value] += tokens
                for line in content.split("\n"):
                    if "读取文件" in line or "read file" in line.lower():
                        file_path = line.split(":")[-1].strip() if ":" in line else ""
                        if file_path:
                            file_read_counts[file_path] += 1
            elif role == "assistant":
                by_category[ContextCategory.ASSISTANT_MESSAGE.value] += tokens
            elif role in ("tool", "tool_result"):
                by_category[ContextCategory.TOOL_RESULT.value] += tokens

            if tokens > 500:
                message_sizes.append({
                    "role": role,
                    "tokens": tokens,
                    "preview": content[:80],
                })

        analysis.by_category = dict(by_category)
        analysis.by_role = dict(by_role)
        analysis.usage_percent = analysis.total_tokens / self.context_window if self.context_window > 0 else 0.0
        analysis.duplicate_file_reads = [
            f for f, count in file_read_counts.items() if count > 1
        ]
        analysis.largest_messages = sorted(
            message_sizes, key=lambda x: x["tokens"], reverse=True
        )[:5]

        if analysis.is_near_limit:
            analysis.suggestions.append("上下文接近限制，建议执行压缩")
        if analysis.duplicate_file_reads:
            analysis.suggestions.append(
                f"发现 {len(analysis.duplicate_file_reads)} 个重复读取的文件，考虑缓存结果"
            )
        tool_tokens = by_category.get(ContextCategory.TOOL_RESULT.value, 0)
        if tool_tokens > analysis.total_tokens * 0.5:
            analysis.suggestions.append("工具结果占用超过50%上下文，建议清除旧工具结果")

        return analysis

    def check_upgrade(self, available_models: List[Dict[str, Any]] = None) -> ContextUpgradeCheck:
        """检查上下文窗口升级可能性"""
        check = ContextUpgradeCheck(
            current_window=self.context_window,
            available_windows=[self.context_window],
            can_upgrade=False,
        )

        if available_models is None:
            try:
                import ollama
                models_data = ollama.list()
                if models_data and 'models' in models_data:
                    available_models = models_data['models']
            except Exception:
                available_models = []

        model_windows = {
            "gemma4:e4b": 8192,
            "qwen2.5:32b": 32768,
            "llama3.1:70b": 128000,
            "deepseek-coder-v2": 128000,
        }

        for model_info in available_models:
            if isinstance(model_info, dict):
                name = model_info.get("name", "")
            else:
                name = str(model_info)

            for model_key, window in model_windows.items():
                if model_key in name.lower() or name.lower() in model_key:
                    if window > self.context_window:
                        check.available_windows.append(window)
                        if window >= LARGE_CONTEXT_WINDOW and not check.can_upgrade:
                            check.can_upgrade = True
                            check.upgrade_model = name
                            check.reason = f"模型 {name} 支持 {window} token 上下文窗口"

        check.available_windows = sorted(set(check.available_windows), reverse=True)
        return check

    def build_full_context(self, messages: List[Dict[str, str]],
                           include_system: bool = True,
                           include_user: bool = True) -> List[Dict[str, str]]:
        """构建完整上下文（注入系统上下文和用户上下文）"""
        result = []

        if include_system:
            system_ctx = self.get_system_context()
            if system_ctx:
                result.append({"role": "system", "content": system_ctx})

        if include_user:
            user_ctx = self.get_user_context()
            if user_ctx:
                result.append({"role": "system", "content": user_ctx})

        result.extend(messages)
        return result

    def get_stats(self) -> Dict[str, Any]:
        return {
            "context_window": self.context_window,
            "cache_valid": self._system_context_cache is not None
                           and time.time() - self._cache_timestamp < self._cache_ttl,
            "claude_md_loaded": self._user_context_cache is not None,
            "break_cache_counter": self._break_cache_counter,
        }


_context_window_manager: Optional[ContextWindowManager] = None


def get_context_window_manager() -> ContextWindowManager:
    global _context_window_manager
    if _context_window_manager is None:
        _context_window_manager = ContextWindowManager()
    return _context_window_manager
