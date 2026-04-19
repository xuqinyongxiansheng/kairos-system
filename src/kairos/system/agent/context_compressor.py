# -*- coding: utf-8 -*-
"""
上下文压缩系统 (Context Compressor)
源自Hermes Agent架构分析，实现4阶段压缩算法

4阶段压缩:
1. Phase 1: 修剪旧工具结果（替换为占位符，无需LLM调用）
2. Phase 2: 分离头部/中间/尾部消息
3. Phase 3: LLM总结中间部分（使用廉价辅助模型）
4. Phase 4: 组装压缩后的消息序列

结构化摘要模板保留关键信息: Goal/Progress/Decisions/Files/Next Steps
"""

import json
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("ContextCompressor")

TOOL_RESULT_PLACEHOLDER = "[工具结果已压缩 - 原始内容{size}字符]"
MAX_TOOL_RESULT_CHARS = 200
PROTECT_FIRST_N_DEFAULT = 3
PROTECT_LAST_N_DEFAULT = 20
COMPRESSION_THRESHOLD = 0.5
AGGRESSIVE_THRESHOLD = 0.85

COMPRESSION_PROMPT = """请将以下对话历史压缩为结构化摘要，保留所有关键信息。

请按以下格式输出:

## 目标
用户想要完成什么任务

## 进展
已经完成了哪些步骤

## 决策
做出了哪些关键决定

## 涉及数据
涉及的文件、数据或资源

## 下一步
接下来需要做什么

## 关键上下文
任何不应丢失的重要细节

---
对话历史:
{content}"""


@dataclass
class CompressionResult:
    """压缩结果"""
    original_count: int
    compressed_count: int
    compression_ratio: float
    phases_executed: List[str]
    summary: str = ""
    messages: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_count": self.original_count,
            "compressed_count": self.compressed_count,
            "compression_ratio": round(self.compression_ratio, 3),
            "phases_executed": self.phases_executed,
            "summary": self.summary[:200] if self.summary else "",
            "messages_count": len(self.messages)
        }


class ContextCompressor:
    """
    上下文压缩器 - 4阶段压缩算法
    
    使用方式:
    1. should_compress() 检查是否需要压缩
    2. compress() 执行压缩
    3. 返回 CompressionResult
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.max_context_tokens = self.config.get("max_context_tokens", 8192)
        self.protect_first_n = self.config.get("protect_first_n", PROTECT_FIRST_N_DEFAULT)
        self.protect_last_n = self.config.get("protect_last_n", PROTECT_LAST_N_DEFAULT)
        self.max_tool_result_chars = self.config.get("max_tool_result_chars", MAX_TOOL_RESULT_CHARS)
        self.threshold = self.config.get("compression_threshold", COMPRESSION_THRESHOLD)
        self.aggressive_threshold = self.config.get("aggressive_threshold", AGGRESSIVE_THRESHOLD)
        self._llm_summarize = self.config.get("llm_summarize_fn", None)

    def estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += len(content)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict):
                        total += len(str(part.get("text", "")))
                    elif isinstance(part, str):
                        total += len(part)
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                total += len(json.dumps(tool_calls, ensure_ascii=False))
        return max(total // 3, 1)

    def should_compress(self, messages: List[Dict[str, Any]],
                        context_length: int = None) -> Tuple[bool, str]:
        if context_length is None:
            context_length = self.estimate_tokens(messages)

        ratio = context_length / self.max_context_tokens

        if ratio >= self.aggressive_threshold:
            return True, "aggressive"
        elif ratio >= self.threshold:
            return True, "normal"
        return False, ""

    def compress(self, messages: List[Dict[str, Any]],
                 mode: str = "normal") -> CompressionResult:
        original_count = len(messages)
        phases = []
        current = list(messages)

        # Phase 1: 修剪旧工具结果
        current, p1_count = self._prune_old_tool_results(current)
        if p1_count > 0:
            phases.append("prune_tool_results:" + str(p1_count))

        # Phase 2: 分离头部/中间/尾部
        head, middle, tail = self._split_messages(current)
        phases.append("split:" + str(len(head)) + "/" + str(len(middle)) + "/" + str(len(tail)))

        # Phase 3: 总结中间部分
        summary = ""
        if middle:
            summary = self._summarize_middle(middle)
            phases.append("summarize:" + str(len(middle)) + "->1")

        # Phase 4: 组装
        result_messages = self._assemble(head, middle, tail, summary)
        phases.append("assemble:" + str(len(result_messages)))

        compressed_count = len(result_messages)
        ratio = compressed_count / max(original_count, 1)

        return CompressionResult(
            original_count=original_count,
            compressed_count=compressed_count,
            compression_ratio=ratio,
            phases_executed=phases,
            summary=summary,
            messages=result_messages
        )

    def _prune_old_tool_results(self, messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
        pruned_count = 0
        result = []
        protected_range = max(len(messages) - self.protect_last_n, 0)

        for i, msg in enumerate(messages):
            if msg.get("role") == "tool" and i < protected_range:
                content = msg.get("content", "")
                if isinstance(content, str) and len(content) > self.max_tool_result_chars:
                    new_msg = dict(msg)
                    new_msg["content"] = TOOL_RESULT_PLACEHOLDER.format(size=len(content))
                    result.append(new_msg)
                    pruned_count += 1
                    continue
            result.append(msg)

        return result, pruned_count

    def _split_messages(self, messages: List[Dict[str, Any]]) -> Tuple[
            List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        n = len(messages)
        if n <= self.protect_first_n + self.protect_last_n:
            return list(messages), [], []

        head_end = self.protect_first_n
        tail_start = max(n - self.protect_last_n, head_end)

        head = messages[:head_end]
        middle = messages[head_end:tail_start]
        tail = messages[tail_start:]

        return head, middle, tail

    def _summarize_middle(self, middle: List[Dict[str, Any]]) -> str:
        if not middle:
            return ""

        content_parts = []
        for msg in middle:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, str):
                truncated = content[:500] if len(content) > 500 else content
                content_parts.append("[" + role + "] " + truncated)

        full_content = "\n".join(content_parts)

        if self._llm_summarize:
            try:
                prompt = COMPRESSION_PROMPT.format(content=full_content)
                summary = self._llm_summarize(prompt)
                if summary:
                    return summary
            except Exception as e:
                logger.warning("LLM总结失败，使用本地压缩: %s", e)

        return self._local_summarize(middle)

    def _local_summarize(self, middle: List[Dict[str, Any]]) -> str:
        user_msgs = []
        assistant_msgs = []
        tool_calls = set()

        for msg in middle:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user" and isinstance(content, str):
                user_msgs.append(content[:100])
            elif role == "assistant":
                if isinstance(content, str) and content.strip():
                    assistant_msgs.append(content[:100])
                for tc in msg.get("tool_calls", []):
                    fn = tc.get("function", {}).get("name", "")
                    if fn:
                        tool_calls.add(fn)

        lines = ["## 上下文压缩摘要", ""]
        if user_msgs:
            lines.append("### 用户请求")
            for u in user_msgs[:5]:
                lines.append("- " + u)
            if len(user_msgs) > 5:
                lines.append("- ... (共" + str(len(user_msgs)) + "条)")
            lines.append("")

        if assistant_msgs:
            lines.append("### 系统响应")
            for a in assistant_msgs[:3]:
                lines.append("- " + a)
            lines.append("")

        if tool_calls:
            lines.append("### 使用的工具")
            lines.append(", ".join(sorted(tool_calls)))
            lines.append("")

        lines.append("### 统计")
        lines.append("原始消息数: " + str(len(middle)))

        return "\n".join(lines)

    def _assemble(self, head: List[Dict[str, Any]],
                  middle: List[Dict[str, Any]],
                  tail: List[Dict[str, Any]],
                  summary: str) -> List[Dict[str, Any]]:
        result = list(head)

        if summary:
            result.append({
                "role": "user",
                "content": "[系统自动压缩的上下文摘要]\n" + summary,
                "_compressed": True
            })

        result.extend(tail)
        return result
