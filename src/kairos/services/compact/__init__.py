"""
上下文压缩服务
借鉴 cc-haha-main 的 4 级渐进压缩策略：
1. 微压缩（MicroCompact）：清除旧工具结果
2. API 微压缩：使用 API 策略压缩冗余内容
3. 会话记忆压缩：保留关键信息的结构化摘要
4. 全量压缩（Full Compact）：LLM 摘要化

完全重写实现，适配本地大模型服务场景
"""

import os
import json
import time
import logging
import asyncio
from enum import IntEnum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger("CompactService")

DEFAULT_CONTEXT_WINDOW = 8192
DEFAULT_MAX_OUTPUT_TOKENS = 4096
DEFAULT_BUFFER_TOKENS = 13000
MAX_HISTORY_LENGTH = 200


class CompactLevel(IntEnum):
    MICRO = 1
    API_MICRO = 2
    SESSION_MEMORY = 3
    FULL = 4


@dataclass
class CompactResult:
    level: CompactLevel
    original_count: int
    compacted_count: int
    original_tokens: int
    compacted_tokens: int
    summary: str = ""
    preserved_keys: List[str] = field(default_factory=list)


def _estimate_tokens(text: str) -> int:
    """估算 token 数量（中文约 1.5 字/token，英文约 4 字符/token）"""
    if not text:
        return 0
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    return int(chinese_chars / 1.5 + other_chars / 4)


def _estimate_messages_tokens(messages: List[Dict[str, str]]) -> int:
    """估算消息列表的 token 数量"""
    total = 0
    for msg in messages:
        total += _estimate_tokens(msg.get("content", ""))
        total += 4
    return total


class CompactService:
    """上下文压缩服务"""

    def __init__(self, context_window: int = None, max_output_tokens: int = None):
        self.context_window = context_window or int(os.environ.get(
            "GEMMA4_CONTEXT_WINDOW", str(DEFAULT_CONTEXT_WINDOW)
        ))
        self.max_output_tokens = max_output_tokens or int(os.environ.get(
            "GEMMA4_MAX_OUTPUT_TOKENS", str(DEFAULT_MAX_OUTPUT_TOKENS)
        ))
        self.buffer_tokens = DEFAULT_BUFFER_TOKENS
        self._total_compactions = 0
        self._compaction_history: List[Dict[str, Any]] = []
        self._max_history = 100
        self._consecutive_failures = 0
        self._max_consecutive_failures = 3
        self._auto_compact_enabled = True
        self._last_auto_compact_time = 0.0
        self._auto_compact_cooldown = 60.0

    def should_compact(self, messages: List[Dict[str, str]]) -> bool:
        """判断是否需要压缩"""
        if self._consecutive_failures >= self._max_consecutive_failures:
            return False
        if len(messages) > MAX_HISTORY_LENGTH:
            return True
        estimated = _estimate_messages_tokens(messages)
        threshold = self.context_window - self.max_output_tokens - self.buffer_tokens
        return estimated > threshold

    async def auto_compact_if_needed(self, messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """自动压缩：当 token 超过阈值时自动触发"""
        if not self._auto_compact_enabled:
            return None
        now = time.time()
        if now - self._last_auto_compact_time < self._auto_compact_cooldown:
            return None
        if not self.should_compact(messages):
            return None

        try:
            result = await self.compact(messages)
            self._last_auto_compact_time = now
            self._consecutive_failures = 0
            logger.info(f"自动压缩完成: {result.get('original_count', 0)} → {result.get('compacted_count', 0)}")
            return result
        except Exception as e:
            self._consecutive_failures += 1
            logger.error(f"自动压缩失败 ({self._consecutive_failures}/{self._max_consecutive_failures}): {e}")
            return None

    def micro_compact_before_api(self, messages: List[Dict[str, str]],
                                  preserve_recent: int = 5) -> List[Dict[str, str]]:
        """API 调用前微压缩：清除旧的只读工具结果"""
        result = []
        recent_tool_results = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role in ("tool", "tool_result"):
                recent_tool_results.append(msg)
            else:
                if recent_tool_results:
                    result.extend(recent_tool_results[-preserve_recent:])
                    recent_tool_results = []
                result.append(msg)

        if recent_tool_results:
            result.extend(recent_tool_results[-preserve_recent:])

        return result

    def _determine_level(self, messages: List[Dict[str, str]]) -> CompactLevel:
        """确定压缩级别"""
        estimated = _estimate_messages_tokens(messages)
        threshold = self.context_window - self.max_output_tokens - self.buffer_tokens

        if estimated > threshold * 2:
            return CompactLevel.FULL
        elif estimated > threshold * 1.5:
            return CompactLevel.SESSION_MEMORY
        elif estimated > threshold:
            return CompactLevel.API_MICRO
        return CompactLevel.MICRO

    async def compact(self, messages: List[Dict[str, str]],
                      level: CompactLevel = None) -> Dict[str, Any]:
        """执行压缩"""
        if not messages:
            return {"original_count": 0, "compacted_count": 0, "level": "none"}

        if level is None:
            level = self._determine_level(messages)

        original_count = len(messages)
        original_tokens = _estimate_messages_tokens(messages)

        if level == CompactLevel.MICRO:
            result = self._micro_compact(messages)
        elif level == CompactLevel.API_MICRO:
            result = self._api_micro_compact(messages)
        elif level == CompactLevel.SESSION_MEMORY:
            result = await self._session_memory_compact(messages)
        else:
            result = await self._full_compact(messages)

        self._total_compactions += 1
        self._compaction_history.append({
            "timestamp": time.time(),
            "level": level.name,
            "original_count": original_count,
            "compacted_count": len(result),
            "original_tokens": original_tokens,
            "compacted_tokens": _estimate_messages_tokens(result),
        })
        if len(self._compaction_history) > self._max_history:
            self._compaction_history = self._compaction_history[-self._max_history:]

        return {
            "level": level.name,
            "original_count": original_count,
            "compacted_count": len(result),
            "original_tokens": original_tokens,
            "compacted_tokens": _estimate_messages_tokens(result),
            "messages": result,
        }

    def _micro_compact(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        微压缩：清除旧工具结果，保留最近对话
        策略：移除 tool_result 角色的旧消息，保留最近 50 条
        """
        result = []
        for msg in messages:
            role = msg.get("role", "")
            if role == "tool_result" or role == "tool":
                content = msg.get("content", "")
                if len(content) > 500:
                    msg = {**msg, "content": content[:200] + "...(已截断)"}
            result.append(msg)

        if len(result) > 50:
            system_msgs = [m for m in result if m.get("role") == "system"]
            other_msgs = [m for m in result if m.get("role") != "system"]
            result = system_msgs + other_msgs[-50:]

        return result

    def _api_micro_compact(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        API 微压缩：压缩冗余内容
        策略：截断长消息，合并连续的 assistant 消息，移除重复内容
        """
        result = []
        prev_role = None

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == prev_role and role == "assistant":
                if result:
                    last = result[-1]
                    last_content = last.get("content", "")
                    if len(last_content) + len(content) < 8000:
                        result[-1] = {**last, "content": last_content + "\n" + content}
                        continue

            if len(content) > 3000:
                msg = {**msg, "content": content[:2000] + f"\n...(已压缩，原始 {len(content)} 字符)"}

            result.append(msg)
            prev_role = role

        system_msgs = [m for m in result if m.get("role") == "system"]
        other_msgs = [m for m in result if m.get("role") != "system"]
        if len(other_msgs) > 30:
            other_msgs = other_msgs[-30:]

        return system_msgs + other_msgs

    async def _session_memory_compact(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        会话记忆压缩：保留关键信息的结构化摘要
        策略：提取用户意图、关键实体、决策记录，生成结构化摘要
        """
        system_msgs = [m for m in messages if m.get("role") == "system"]
        recent_msgs = [m for m in messages if m.get("role") != "system"][-10:]

        older_msgs = [m for m in messages if m.get("role") != "system"][:-10]

        summary_parts = []
        user_intents = []
        key_entities = set()
        decisions = []

        for msg in older_msgs:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user" and content:
                intent = content[:100]
                user_intents.append(intent)
                words = content.split()
                for w in words:
                    if len(w) > 3 and w not in {"的", "了", "是", "在", "和", "有", "不", "这"}:
                        key_entities.add(w)

            elif role == "assistant" and content:
                if any(kw in content for kw in ["决定", "方案", "建议", "结论", "结果"]):
                    decisions.append(content[:200])

        summary_sections = ["[会话记忆摘要]", ""]

        if user_intents:
            summary_sections.append("用户意图:")
            for i, intent in enumerate(user_intents[-5:], 1):
                summary_sections.append(f"  {i}. {intent}")
            summary_sections.append("")

        if key_entities:
            entities_str = ", ".join(list(key_entities)[:20])
            summary_sections.append(f"关键实体: {entities_str}")
            summary_sections.append("")

        if decisions:
            summary_sections.append("决策记录:")
            for d in decisions[-3:]:
                summary_sections.append(f"  - {d}")
            summary_sections.append("")

        summary_sections.append(f"[以上为早期对话摘要，共 {len(older_msgs)} 条消息已压缩]")

        summary_msg = {
            "role": "system",
            "content": "\n".join(summary_sections)
        }

        return system_msgs + [summary_msg] + recent_msgs

    async def _full_compact(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        全量压缩：使用 LLM 生成摘要
        策略：将全部历史发送给 LLM，生成包含 9 个部分的结构化摘要
        """
        system_msgs = [m for m in messages if m.get("role") == "system"]
        recent_msgs = [m for m in messages if m.get("role") != "system"][-5:]
        older_msgs = [m for m in messages if m.get("role") != "system"][:-5]

        if not older_msgs:
            return messages

        conversation_text = []
        for msg in older_msgs:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:500]
            conversation_text.append(f"[{role}] {content}")
        conversation_str = "\n".join(conversation_text)

        if len(conversation_str) > 8000:
            conversation_str = conversation_str[:8000] + "\n...(已截断)"

        summary = await self._llm_summarize(conversation_str)

        if not summary:
            return await self._session_memory_compact(messages)

        summary_msg = {
            "role": "system",
            "content": f"[对话历史摘要]\n{summary}\n[以上为早期对话的 LLM 摘要]"
        }

        return system_msgs + [summary_msg] + recent_msgs

    async def _llm_summarize(self, conversation: str) -> str:
        """使用 LLM 生成对话摘要"""
        try:
            from kairos.system.llm_reasoning import get_ollama_client
            client = get_ollama_client()

            if not await client.is_available():
                return ""

            prompt = f"""请将以下对话历史压缩为结构化摘要，包含以下部分：
1. 主要话题
2. 用户需求
3. 已解决的问题
4. 未解决的问题
5. 关键决策
6. 重要代码/文件引用
7. 当前任务状态
8. 用户偏好
9. 后续行动项

对话历史：
{conversation}

请用中文输出摘要："""

            result = await client.generate(
                prompt=prompt,
                system="你是一个对话摘要助手，擅长提取关键信息并生成结构化摘要。"
            )

            if result.success and result.content:
                return result.content
            return ""
        except Exception as e:
            logger.error(f"LLM 摘要生成失败: {e}")
            return ""

    def get_stats(self) -> Dict[str, Any]:
        """获取压缩服务统计"""
        return {
            "total_compactions": self._total_compactions,
            "context_window": self.context_window,
            "max_output_tokens": self.max_output_tokens,
            "auto_compact_enabled": self._auto_compact_enabled,
            "consecutive_failures": self._consecutive_failures,
            "circuit_broken": self._consecutive_failures >= self._max_consecutive_failures,
            "recent_compactions": self._compaction_history[-5:],
        }


_compact_service: Optional[CompactService] = None


def get_compact_service() -> CompactService:
    global _compact_service
    if _compact_service is None:
        _compact_service = CompactService()
    return _compact_service
