# -*- coding: utf-8 -*-
"""
渐进式披露系统 (Progressive Disclosure)
源自Hermes Agent技能系统架构分析

三级披露:
- Level 0: 目录级 (~50 tokens/项) - 仅名称和类别
- Level 1: 摘要级 (~200 tokens/项) - 名称、描述、核心要点
- Level 2: 完整级 (~1000 tokens/项) - 完整内容

条件激活: 根据场景自动加载相关原则，而非全部加载
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("ProgressiveDisclosure")


class DisclosureLevel(Enum):
    CATALOG = 0
    SUMMARY = 1
    FULL = 2


@dataclass
class DisclosableItem:
    """可披露项"""
    item_id: str
    name: str
    category: str
    description: str
    core_idea: str = ""
    full_content: str = ""
    tags: List[str] = field(default_factory=list)
    activation_conditions: Dict[str, Any] = field(default_factory=dict)
    token_estimate: int = 0

    def disclose(self, level: DisclosureLevel) -> Dict[str, Any]:
        if level == DisclosureLevel.CATALOG:
            return {
                "id": self.item_id,
                "name": self.name,
                "category": self.category
            }
        elif level == DisclosureLevel.SUMMARY:
            return {
                "id": self.item_id,
                "name": self.name,
                "category": self.category,
                "description": self.description,
                "core_idea": self.core_idea,
                "tags": self.tags
            }
        else:
            return {
                "id": self.item_id,
                "name": self.name,
                "category": self.category,
                "description": self.description,
                "core_idea": self.core_idea,
                "full_content": self.full_content,
                "tags": self.tags,
                "token_estimate": self.token_estimate
            }


class ProgressiveDisclosureEngine:
    """
    渐进式披露引擎
    
    用法:
    1. register() 注册可披露项
    2. list_catalog() 获取目录级视图
    3. view_summary() 获取摘要级视图
    4. view_full() 获取完整级视图
    5. auto_select() 根据上下文自动选择最相关的项
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._items: Dict[str, DisclosableItem] = {}
        self._category_index: Dict[str, List[str]] = {}
        self._tag_index: Dict[str, List[str]] = {}
        self._max_catalog_tokens = self.config.get("max_catalog_tokens", 2000)
        self._max_summary_tokens = self.config.get("max_summary_tokens", 4000)

    def register(self, item: DisclosableItem):
        self._items[item.item_id] = item
        if item.category not in self._category_index:
            self._category_index[item.category] = []
        self._category_index[item.category].append(item.item_id)
        for tag in item.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            self._tag_index[tag].append(item.item_id)

    def register_batch(self, items: List[DisclosableItem]):
        for item in items:
            self.register(item)

    def list_catalog(self, category: str = None,
                     tags: List[str] = None) -> List[Dict[str, Any]]:
        item_ids = self._filter_ids(category, tags)
        return [self._items[iid].disclose(DisclosureLevel.CATALOG) for iid in item_ids if iid in self._items]

    def view_summary(self, item_id: str) -> Optional[Dict[str, Any]]:
        item = self._items.get(item_id)
        if not item:
            return None
        return item.disclose(DisclosureLevel.SUMMARY)

    def view_full(self, item_id: str) -> Optional[Dict[str, Any]]:
        item = self._items.get(item_id)
        if not item:
            return None
        return item.disclose(DisclosureLevel.FULL)

    def view_summaries_batch(self, item_ids: List[str]) -> List[Dict[str, Any]]:
        results = []
        for iid in item_ids:
            item = self._items.get(iid)
            if item:
                results.append(item.disclose(DisclosureLevel.SUMMARY))
        return results

    def auto_select(self, context: Dict[str, Any],
                    level: DisclosureLevel = DisclosureLevel.SUMMARY,
                    max_items: int = 10) -> List[Dict[str, Any]]:
        scored: List[Tuple[str, float]] = []

        context_category = context.get("category", "")
        context_sentiment = context.get("sentiment", "")
        context_keywords = set(context.get("keywords", []))
        context_tags = set(context.get("tags", []))

        for item_id, item in self._items.items():
            score = 0.0

            if context_category and item.category == context_category:
                score += 3.0

            if context_category in item.activation_conditions.get("requires_category", []):
                score += 5.0

            if context_sentiment and context_sentiment in item.activation_conditions.get("requires_sentiment", []):
                score += 3.0

            keyword_overlap = context_keywords & set(item.tags)
            score += len(keyword_overlap) * 1.0

            tag_overlap = context_tags & set(item.tags)
            score += len(tag_overlap) * 0.5

            if item.activation_conditions.get("fallback_for"):
                has_primary = any(
                    self._items.get(iid, DisclosableItem("", "", "", "", "")).category == item.activation_conditions["fallback_for"]
                    for iid in self._items
                )
                if not has_primary:
                    score += 2.0

            scored.append((item_id, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        top_ids = [sid for sid, _ in scored[:max_items] if _ > 0]

        return [self._items[iid].disclose(level) for iid in top_ids if iid in self._items]

    def estimate_tokens(self, items: List[Dict[str, Any]]) -> int:
        total = 0
        for item in items:
            total += len(str(item)) // 3
        return max(total, 1)

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "total_items": len(self._items),
            "categories": {k: len(v) for k, v in self._category_index.items()},
            "tags_count": len(self._tag_index),
            "catalog_tokens": self.estimate_tokens(self.list_catalog()),
            "all_summary_tokens": self.estimate_tokens(
                [item.disclose(DisclosureLevel.SUMMARY) for item in self._items.values()]
            )
        }

    def _filter_ids(self, category: str = None, tags: List[str] = None) -> List[str]:
        if category and category in self._category_index:
            ids = set(self._category_index[category])
        else:
            ids = set(self._items.keys())

        if tags:
            tag_ids = set()
            for tag in tags:
                if tag in self._tag_index:
                    tag_ids.update(self._tag_index[tag])
            ids = ids & tag_ids

        return sorted(ids)
