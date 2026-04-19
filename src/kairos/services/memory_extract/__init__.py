"""
自动记忆提取系统
借鉴 cc-haha-main 的 extractMemories.ts + prompts.ts：
1. 查询循环结束时自动从对话中提取持久化记忆
2. 工具权限沙箱（只读 + 仅 auto-memory 目录写权限）
3. 游标追踪（lastMemoryMessageUuid 确保只处理新增消息）
4. 互斥机制（主代理写入时跳过 forked 提取）
5. 节流控制（每 N 轮才运行一次）
"""

import os
import re
import time
import json
import logging
import asyncio
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("MemoryExtract")

MEMORY_DIR = os.environ.get(
    "GEMMA4_MEMORY_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "memory")
)

MEMORY_CATEGORIES = ["user", "feedback", "project", "reference"]

EXTRACT_PROMPT_TEMPLATE = """分析以下对话，提取值得持久化的记忆。

记忆分类：
- user: 用户偏好、习惯、工作风格
- feedback: 用户对输出的反馈（喜欢/不喜欢的模式）
- project: 项目特定知识（架构、约定、依赖）
- reference: 常用参考信息（API、命令、配置）

对话内容:
{transcript}

请以 JSON 格式输出提取的记忆:
```json
{{
  "memories": [
    {{
      "category": "user|feedback|project|reference",
      "content": "记忆内容",
      "confidence": 0.0-1.0,
      "source": "对话来源摘要"
    }}
  ]
}}
```"""


@dataclass
class ExtractedMemory:
    category: str
    content: str
    confidence: float = 0.8
    source: str = ""
    extracted_at: float = 0.0
    message_uuid: str = ""

    def __post_init__(self):
        if self.extracted_at == 0.0:
            self.extracted_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "content": self.content,
            "confidence": self.confidence,
            "source": self.source,
            "extracted_at": self.extracted_at,
            "message_uuid": self.message_uuid,
        }


class MemoryPathValidator:
    """记忆路径安全验证"""

    @staticmethod
    def validate(path: str) -> bool:
        if not path:
            return False
        if '\\' in path and len(path) <= 3:
            return False
        if path.startswith('/'):
            if len(path) == 1:
                return False
        if '\x00' in path:
            return False
        if path.startswith('\\\\'):
            return False
        return True


class MemorySandbox:
    """记忆工具权限沙箱"""

    ALLOWED_READ_TOOLS = {"file_read", "grep", "glob", "list_dir"}
    ALLOWED_WRITE_DIR = MEMORY_DIR
    SAFE_BASH_COMMANDS = {"ls", "cat", "head", "tail", "pwd", "echo", "find", "wc"}

    @classmethod
    def can_use_tool(cls, tool_name: str, tool_input: Dict[str, Any]) -> bool:
        """检查工具是否在沙箱权限内"""
        if tool_name in cls.ALLOWED_READ_TOOLS:
            return True

        if tool_name == "bash":
            command = tool_input.get("command", "").strip()
            first_word = command.split()[0] if command.split() else ""
            return first_word in cls.SAFE_BASH_COMMANDS

        if tool_name in ("file_edit", "file_write"):
            path = tool_input.get("path", "")
            abs_path = os.path.abspath(path)
            abs_memory_dir = os.path.abspath(cls.ALLOWED_WRITE_DIR)
            return abs_path.startswith(abs_memory_dir)

        return False


class MemoryExtractor:
    """自动记忆提取器"""

    def __init__(self, ollama_chat_fn=None):
        self._chat_fn = ollama_chat_fn
        self._last_message_index = 0
        self._extraction_count = 0
        self._skip_count = 0
        self._error_count = 0
        self._is_extracting = False
        self._pending_context: Optional[List[Dict[str, str]]] = None
        self._throttle_interval = 5
        self._turns_since_last_extract = 0
        self._memories: List[ExtractedMemory] = []
        self._max_memories = 1000

    def notify_message(self, messages: List[Dict[str, str]]):
        """通知新消息到达"""
        self._turns_since_last_extract += 1
        if self._is_extracting:
            self._pending_context = list(messages)

    def should_extract(self) -> bool:
        """判断是否应该执行提取"""
        if self._is_extracting:
            return False
        if self._turns_since_last_extract < self._throttle_interval:
            return False
        return True

    async def extract(self, messages: List[Dict[str, str]]) -> List[ExtractedMemory]:
        """从对话中提取记忆"""
        if self._is_extracting:
            return []

        if not self.should_extract():
            self._skip_count += 1
            return []

        self._is_extracting = True
        new_memories = []

        try:
            new_messages = messages[self._last_message_index:]
            if len(new_messages) < 2:
                return []

            transcript = self._build_transcript(new_messages)
            if not transcript:
                return []

            if not self._chat_fn:
                self._chat_fn = self._get_default_chat_fn()

            prompt = EXTRACT_PROMPT_TEMPLATE.format(transcript=transcript[:4000])
            response = await self._chat_fn(prompt)

            parsed = self._parse_response(response)
            for mem_data in parsed:
                memory = ExtractedMemory(
                    category=mem_data.get("category", "project"),
                    content=mem_data.get("content", ""),
                    confidence=float(mem_data.get("confidence", 0.8)),
                    source=mem_data.get("source", ""),
                )
                if memory.content and memory.category in MEMORY_CATEGORIES:
                    new_memories.append(memory)
                    self._memories.append(memory)

            if len(self._memories) > self._max_memories:
                self._memories = self._memories[-self._max_memories:]

            self._last_message_index = len(messages)
            self._turns_since_last_extract = 0
            self._extraction_count += 1

            await self._persist_memories(new_memories)

            logger.info(f"记忆提取完成: {len(new_memories)} 条新记忆")

        except Exception as e:
            self._error_count += 1
            logger.error(f"记忆提取失败: {e}")
        finally:
            self._is_extracting = False
            if self._pending_context:
                self._pending_context = None

        return new_memories

    def _build_transcript(self, messages: List[Dict[str, str]], max_length: int = 4000) -> str:
        """构建对话转录"""
        lines = []
        total_len = 0
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            prefix = {"user": "User", "assistant": "Asst", "tool": "Tool"}.get(role, "Sys")
            line = f"{prefix}: {content[:300]}"
            if total_len + len(line) > max_length:
                break
            lines.append(line)
            total_len += len(line)
        return "\n".join(lines)

    def _parse_response(self, response: str) -> List[Dict[str, Any]]:
        """解析 LLM 提取结果"""
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return data.get("memories", [])
            except json.JSONDecodeError:
                pass

        try:
            data = json.loads(response)
            return data.get("memories", [])
        except json.JSONDecodeError:
            pass

        return []

    async def _persist_memories(self, memories: List[ExtractedMemory]):
        """持久化记忆到磁盘"""
        if not memories:
            return

        os.makedirs(MEMORY_DIR, exist_ok=True)

        for category in MEMORY_CATEGORIES:
            cat_memories = [m for m in memories if m.category == category]
            if not cat_memories:
                continue

            filepath = os.path.join(MEMORY_DIR, f"{category}.jsonl")
            try:
                with open(filepath, "a", encoding="utf-8") as f:
                    for m in cat_memories:
                        f.write(json.dumps(m.to_dict(), ensure_ascii=False) + "\n")
            except Exception as e:
                logger.error(f"持久化记忆失败 [{category}]: {e}")

    def _get_default_chat_fn(self):
        """获取默认 LLM 聊天函数"""
        async def _chat(prompt: str) -> str:
            try:
                import ollama
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: ollama.chat(
                        model="gemma4:e4b",
                        messages=[{"role": "user", "content": prompt}],
                    )
                )
                return response.get("message", {}).get("content", "")
            except Exception as e:
                logger.error(f"LLM 调用失败: {e}")
                return ""
        return _chat

    def load_memories(self, category: str = None) -> List[ExtractedMemory]:
        """从磁盘加载记忆"""
        loaded = []
        categories = [category] if category else MEMORY_CATEGORIES

        for cat in categories:
            filepath = os.path.join(MEMORY_DIR, f"{cat}.jsonl")
            if not os.path.exists(filepath):
                continue
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            loaded.append(ExtractedMemory(
                                category=data.get("category", cat),
                                content=data.get("content", ""),
                                confidence=data.get("confidence", 0.8),
                                source=data.get("source", ""),
                                extracted_at=data.get("extracted_at", 0),
                            ))
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.error(f"加载记忆失败 [{cat}]: {e}")

        return loaded

    def search_memories(self, query: str, category: str = None,
                        limit: int = 10) -> List[ExtractedMemory]:
        """搜索记忆"""
        all_memories = self.load_memories(category)
        query_lower = query.lower()
        scored = []
        for m in all_memories:
            score = 0
            if query_lower in m.content.lower():
                score += 10
            for word in query_lower.split():
                if word in m.content.lower():
                    score += 1
            if score > 0:
                scored.append((score, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:limit]]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "extraction_count": self._extraction_count,
            "skip_count": self._skip_count,
            "error_count": self._error_count,
            "is_extracting": self._is_extracting,
            "total_memories": len(self._memories),
            "turns_since_last_extract": self._turns_since_last_extract,
            "throttle_interval": self._throttle_interval,
            "memory_dir": MEMORY_DIR,
        }


_memory_extractor: Optional[MemoryExtractor] = None


def get_memory_extractor() -> MemoryExtractor:
    global _memory_extractor
    if _memory_extractor is None:
        _memory_extractor = MemoryExtractor()
    return _memory_extractor
