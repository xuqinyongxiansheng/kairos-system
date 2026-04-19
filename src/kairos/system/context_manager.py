"""
上下文管理器
借鉴Claude Code的智能上下文管理机制
支持: Token计数、智能截断、向量检索、层级摘要
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json
import os
import re

logger = logging.getLogger("ContextManager")


class ContextPriority(Enum):
    """上下文优先级"""
    CRITICAL = 100
    HIGH = 80
    NORMAL = 50
    LOW = 20
    DISPOSABLE = 0


class ContentType(Enum):
    """内容类型"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    CODE = "code"
    DOCUMENT = "document"
    MEMORY = "memory"
    TOOL_RESULT = "tool_result"


@dataclass
class ContextItem:
    """上下文项"""
    id: str
    content: str
    content_type: ContentType
    priority: int
    tokens: int
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    summary: Optional[str] = None
    embeddings: Optional[List[float]] = None


@dataclass
class ContextConfig:
    """上下文配置"""
    max_tokens: int = 128000
    reserve_tokens: int = 4000
    summary_threshold: float = 0.8
    enable_vector_search: bool = True
    enable_summarization: bool = True
    compression_ratio: float = 0.3


class ContextManager:
    """
    智能上下文管理器
    
    功能:
    - Token计数与管理
    - 智能截断（保留高优先级内容）
    - 向量检索相关内容
    - 层级摘要生成
    - 上下文压缩
    """
    
    def __init__(self, config: ContextConfig = None):
        self.config = config or ContextConfig()
        self.context_buffer: List[ContextItem] = []
        self.summaries: Dict[str, str] = {}
        self.total_tokens = 0
        self._item_counter = 0
        
        # 尝试加载tokenizer
        self._tokenizer = self._load_tokenizer()
        
        logger.info(f"上下文管理器初始化 (max_tokens={self.config.max_tokens})")
    
    def _load_tokenizer(self):
        """加载tokenizer"""
        try:
            import tiktoken
            return tiktoken.get_encoding("cl100k_base")
        except ImportError:
            logger.warning("tiktoken未安装，使用简单估算")
            return None
    
    def count_tokens(self, text: str) -> int:
        """
        计算token数量
        
        Args:
            text: 文本内容
            
        Returns:
            token数量
        """
        if self._tokenizer:
            return len(self._tokenizer.encode(text))
        
        # 简单估算：中文约1.5字符/token，英文约4字符/token
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_chars = len(text) - chinese_chars
        
        return int(chinese_chars / 1.5 + other_chars / 4)
    
    def add_context(self, content: str,
                   content_type: ContentType = ContentType.USER,
                   priority: int = 50,
                   metadata: Dict[str, Any] = None) -> str:
        """
        添加上下文
        
        Args:
            content: 内容
            content_type: 内容类型
            priority: 优先级
            metadata: 元数据
            
        Returns:
            上下文ID
        """
        self._item_counter += 1
        item_id = f"ctx_{self._item_counter}"
        
        tokens = self.count_tokens(content)
        
        item = ContextItem(
            id=item_id,
            content=content,
            content_type=content_type,
            priority=priority,
            tokens=tokens,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        
        self.context_buffer.append(item)
        self.total_tokens += tokens
        
        # 检查是否需要截断
        if self.total_tokens > self.config.max_tokens * self.config.summary_threshold:
            self._smart_truncate()
        
        logger.debug(f"添加上下文: {item_id} ({tokens} tokens)")
        return item_id
    
    def add_system_context(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """添加系统上下文"""
        return self.add_context(content, ContentType.SYSTEM, ContextPriority.CRITICAL.value, metadata)
    
    def add_user_context(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """添加用户上下文"""
        return self.add_context(content, ContentType.USER, ContextPriority.HIGH.value, metadata)
    
    def add_assistant_context(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """添加助手上下文"""
        return self.add_context(content, ContentType.ASSISTANT, ContextPriority.NORMAL.value, metadata)
    
    def add_code_context(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """添加代码上下文"""
        return self.add_context(content, ContentType.CODE, ContextPriority.HIGH.value, metadata)
    
    def add_memory_context(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """添加记忆上下文"""
        return self.add_context(content, ContentType.MEMORY, ContextPriority.LOW.value, metadata)
    
    def _smart_truncate(self):
        """智能截断 - 保留高优先级内容"""
        # 按优先级排序
        sorted_items = sorted(self.context_buffer, key=lambda x: x.priority, reverse=True)
        
        kept_items = []
        total = 0
        max_keep = self.config.max_tokens - self.config.reserve_tokens
        
        for item in sorted_items:
            if total + item.tokens <= max_keep:
                kept_items.append(item)
                total += item.tokens
            else:
                # 生成摘要替代
                if self.config.enable_summarization:
                    summary = self._generate_summary(item)
                    self.summaries[item.id] = summary
        
        self.context_buffer = kept_items
        self.total_tokens = total
        
        logger.info(f"上下文截断: 保留 {len(kept_items)} 项, {total} tokens")
    
    def _generate_summary(self, item: ContextItem) -> str:
        """
        生成内容摘要
        
        Args:
            item: 上下文项
            
        Returns:
            摘要文本
        """
        content = item.content
        
        # 简单摘要策略
        if len(content) <= 200:
            return content
        
        # 提取关键信息
        lines = content.split('\n')
        
        # 提取标题和首尾
        summary_parts = []
        
        # 首行
        if lines:
            summary_parts.append(lines[0][:100])
        
        # 中间关键行
        key_lines = [l for l in lines if l.strip() and (
            l.strip().startswith('#') or
            l.strip().startswith('-') or
            l.strip().startswith('*') or
            'important' in l.lower() or
            '关键' in l or
            '重要' in l
        )][:3]
        summary_parts.extend(key_lines)
        
        # 末行
        if len(lines) > 1:
            summary_parts.append(lines[-1][:100])
        
        summary = '\n'.join(summary_parts)
        
        # 压缩
        if len(summary) > len(content) * self.config.compression_ratio:
            summary = summary[:int(len(content) * self.config.compression_ratio)]
        
        return summary
    
    def get_context(self, query: str = None,
                   include_summaries: bool = True) -> str:
        """
        获取优化后的上下文
        
        Args:
            query: 查询字符串（用于向量检索）
            include_summaries: 是否包含摘要
            
        Returns:
            上下文字符串
        """
        items = self.context_buffer
        
        # 如果有查询，进行相关性排序
        if query and self.config.enable_vector_search:
            items = self._retrieve_relevant(query, items)
        
        # 构建上下文
        context_parts = []
        
        for item in items:
            context_parts.append(item.content)
        
        # 添加摘要
        if include_summaries and self.summaries:
            context_parts.append("\n--- 历史摘要 ---")
            for item_id, summary in self.summaries.items():
                context_parts.append(f"[{item_id}]: {summary}")
        
        return "\n\n".join(context_parts)
    
    def _retrieve_relevant(self, query: str, items: List[ContextItem]) -> List[ContextItem]:
        """
        检索相关内容
        
        Args:
            query: 查询字符串
            items: 上下文项列表
            
        Returns:
            排序后的上下文项
        """
        # 简单关键词匹配
        query_lower = query.lower()
        query_keywords = set(re.findall(r'\w+', query_lower))
        
        scored_items = []
        for item in items:
            content_lower = item.content.lower()
            content_keywords = set(re.findall(r'\w+', content_lower))
            
            # 计算关键词重叠
            overlap = len(query_keywords & content_keywords)
            score = overlap / max(len(query_keywords), 1)
            
            # 结合优先级
            final_score = score * 0.5 + item.priority / 100 * 0.5
            
            scored_items.append((final_score, item))
        
        # 按分数排序
        scored_items.sort(key=lambda x: x[0], reverse=True)
        
        return [item for _, item in scored_items]
    
    def remove_context(self, item_id: str) -> bool:
        """
        移除上下文
        
        Args:
            item_id: 上下文ID
            
        Returns:
            是否成功
        """
        for i, item in enumerate(self.context_buffer):
            if item.id == item_id:
                self.total_tokens -= item.tokens
                self.context_buffer.pop(i)
                return True
        return False
    
    def clear_context(self, keep_system: bool = True):
        """
        清除上下文
        
        Args:
            keep_system: 是否保留系统上下文
        """
        if keep_system:
            self.context_buffer = [
                item for item in self.context_buffer
                if item.content_type == ContentType.SYSTEM
            ]
            self.total_tokens = sum(item.tokens for item in self.context_buffer)
        else:
            self.context_buffer.clear()
            self.total_tokens = 0
        
        self.summaries.clear()
        logger.info("上下文已清除")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        type_counts = {}
        for item in self.context_buffer:
            type_name = item.content_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        return {
            "total_items": len(self.context_buffer),
            "total_tokens": self.total_tokens,
            "max_tokens": self.config.max_tokens,
            "utilization": self.total_tokens / self.config.max_tokens,
            "summaries_count": len(self.summaries),
            "by_type": type_counts
        }
    
    def get_item(self, item_id: str) -> Optional[ContextItem]:
        """获取特定上下文项"""
        for item in self.context_buffer:
            if item.id == item_id:
                return item
        return None
    
    def update_priority(self, item_id: str, priority: int) -> bool:
        """更新优先级"""
        for item in self.context_buffer:
            if item.id == item_id:
                item.priority = priority
                return True
        return False
    
    def compress(self) -> Dict[str, Any]:
        """
        压缩上下文
        
        Returns:
            压缩结果
        """
        original_tokens = self.total_tokens
        original_items = len(self.context_buffer)
        
        # 对低优先级内容生成摘要
        for item in self.context_buffer:
            if item.priority < ContextPriority.NORMAL.value and not item.summary:
                item.summary = self._generate_summary(item)
                item.content = item.summary
                new_tokens = self.count_tokens(item.summary)
                self.total_tokens -= (item.tokens - new_tokens)
                item.tokens = new_tokens
        
        return {
            "status": "success",
            "original_tokens": original_tokens,
            "compressed_tokens": self.total_tokens,
            "compression_ratio": self.total_tokens / original_tokens if original_tokens > 0 else 1,
            "original_items": original_items,
            "compressed_items": len(self.context_buffer)
        }
    
    def export_context(self) -> Dict[str, Any]:
        """导出上下文"""
        return {
            "config": {
                "max_tokens": self.config.max_tokens,
                "reserve_tokens": self.config.reserve_tokens
            },
            "items": [
                {
                    "id": item.id,
                    "content": item.content,
                    "content_type": item.content_type.value,
                    "priority": item.priority,
                    "tokens": item.tokens,
                    "timestamp": item.timestamp,
                    "metadata": item.metadata
                }
                for item in self.context_buffer
            ],
            "summaries": self.summaries,
            "stats": self.get_stats()
        }
    
    def import_context(self, data: Dict[str, Any]):
        """导入上下文"""
        self.clear_context(keep_system=False)
        
        for item_data in data.get("items", []):
            item = ContextItem(
                id=item_data["id"],
                content=item_data["content"],
                content_type=ContentType(item_data["content_type"]),
                priority=item_data["priority"],
                tokens=item_data["tokens"],
                timestamp=item_data["timestamp"],
                metadata=item_data.get("metadata", {})
            )
            self.context_buffer.append(item)
            self.total_tokens += item.tokens
        
        self.summaries = data.get("summaries", {})
        
        logger.info(f"导入上下文: {len(self.context_buffer)} 项")


# 全局实例
context_manager = ContextManager()


def get_context_manager() -> ContextManager:
    """获取全局上下文管理器"""
    return context_manager
