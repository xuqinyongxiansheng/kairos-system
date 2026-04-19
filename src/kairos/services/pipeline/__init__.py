"""
消息管道服务
借鉴 cc-haha-main 的消息处理管道：
- 消息规范化（normalizeMessagesForAPI）
- 压缩边界标记
- 工具结果配对（ensureToolResultPairing）
- 上下文注入

完全重写实现
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger("MessagePipeline")


@dataclass
class CompactBoundary:
    message_id: str = ""
    timestamp: float = 0.0


def normalize_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """规范化消息列表，确保格式一致"""
    normalized = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if not content and role != "system":
            continue

        normalized.append({
            "role": role,
            "content": str(content),
        })

    if normalized and normalized[0]["role"] != "system":
        normalized.insert(0, {"role": "system", "content": "你是鸿蒙小雨智能助手。"})

    return normalized


def ensure_tool_result_pairing(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """确保每个 tool_use 都有对应的 tool_result"""
    result = []
    pending_tool_ids = set()

    for msg in messages:
        role = msg.get("role", "")
        tool_id = msg.get("tool_call_id", "")

        if role == "assistant" and msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                pending_tool_ids.add(tc.get("id", ""))
            result.append(msg)
        elif role == "tool" or role == "tool_result":
            if tool_id in pending_tool_ids:
                pending_tool_ids.discard(tool_id)
            result.append(msg)
        else:
            result.append(msg)

    for tid in pending_tool_ids:
        result.append({
            "role": "tool_result",
            "tool_call_id": tid,
            "content": "[工具结果已省略]",
        })

    return result


def inject_context(messages: List[Dict[str, Any]],
                   system_prompt: str = "",
                   user_context: str = "",
                   append_context: str = "") -> List[Dict[str, Any]]:
    """注入上下文信息"""
    result = list(messages)

    if system_prompt:
        has_system = any(m.get("role") == "system" for m in result)
        if has_system:
            for i, m in enumerate(result):
                if m.get("role") == "system":
                    result[i] = {**m, "content": system_prompt + "\n\n" + m.get("content", "")}
                    break
        else:
            result.insert(0, {"role": "system", "content": system_prompt})

    if user_context:
        ctx_msg = {"role": "system", "content": f"[用户上下文]\n{user_context}"}
        system_msgs = [i for i, m in enumerate(result) if m.get("role") == "system"]
        if system_msgs:
            last_system = system_msgs[-1]
            result.insert(last_system + 1, ctx_msg)
        else:
            result.insert(0, ctx_msg)

    if append_context:
        result.append({"role": "system", "content": f"[附加上下文]\n{append_context}"})

    return result


def create_compact_boundary() -> Dict[str, Any]:
    """创建压缩边界标记"""
    import time
    return {
        "role": "system",
        "content": "[压缩边界 - 此前的对话已被压缩]",
        "metadata": {"compact_boundary": True, "timestamp": time.time()},
    }


def get_messages_after_boundary(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """获取压缩边界后的消息"""
    last_boundary = -1
    for i, msg in enumerate(messages):
        metadata = msg.get("metadata", {})
        if isinstance(metadata, dict) and metadata.get("compact_boundary"):
            last_boundary = i

    if last_boundary >= 0:
        return messages[last_boundary + 1:]
    return messages


def estimate_message_tokens(messages: List[Dict[str, Any]]) -> int:
    """估算消息列表的 token 数量"""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        chinese_chars = sum(1 for c in content if '\u4e00' <= c <= '\u9fff')
        other_chars = len(content) - chinese_chars
        total += int(chinese_chars / 1.5 + other_chars / 4) + 4
    return total
