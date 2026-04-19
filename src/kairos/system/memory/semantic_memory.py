# -*- coding: utf-8 -*-
"""
语义记忆 (Semantic Memory)
存储概念知识和关系，支持概念检索和推理

核心功能:
- 概念节点存储 (名称/属性/类别)
- 关系网络 (is-a/part-of/cause-of/related-to)
- 概念检索 (关键词/属性/关系)
- 知识推理 (传递性/继承性)
- 概念激活与扩散
"""

import logging
import uuid
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger("SemanticMemory")


class RelationType(Enum):
    """关系类型"""
    IS_A = "is_a"
    PART_OF = "part_of"
    CAUSE_OF = "cause_of"
    RELATED_TO = "related_to"
    DEPENDS_ON = "depends_on"
    OPPOSITE_OF = "opposite_of"
    INSTANCE_OF = "instance_of"
    HAS_PROPERTY = "has_property"


@dataclass
class SemanticNode:
    """语义节点"""
    node_id: str
    name: str
    category: str
    properties: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    activation: float = 0.0
    access_count: int = 0
    confidence: float = 1.0
    source: str = "unknown"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def activate(self, strength: float = 1.0):
        """激活节点"""
        self.activation = min(self.activation + strength, 1.0)
        self.access_count += 1
        self.updated_at = datetime.now().isoformat()

    def decay(self, rate: float = 0.1):
        """衰减激活"""
        self.activation = max(self.activation - rate, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "node_id": self.node_id,
            "name": self.name,
            "category": self.category,
            "properties": self.properties,
            "description": self.description,
            "activation": round(self.activation, 3),
            "access_count": self.access_count,
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


@dataclass
class SemanticRelation:
    """语义关系"""
    relation_id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    strength: float = 1.0
    confidence: float = 1.0
    bidirectional: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "relation_id": self.relation_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "strength": self.strength,
            "confidence": self.confidence,
            "bidirectional": self.bidirectional
        }


class SemanticMemory:
    """
    语义记忆系统
    
    功能:
    - 概念存储与检索
    - 关系网络管理
    - 激活扩散
    - 知识推理
    - 概念聚类
    """

    def __init__(self, max_nodes: int = 10000, max_relations: int = 50000,
                 activation_decay_rate: float = 0.1,
                 spreading_rate: float = 0.3):
        self._nodes: Dict[str, SemanticNode] = {}
        self._relations: Dict[str, SemanticRelation] = {}
        self._name_index: Dict[str, str] = {}
        self._category_index: Dict[str, Set[str]] = {}
        self._max_nodes = max_nodes
        self._max_relations = max_relations
        self._activation_decay_rate = activation_decay_rate
        self._spreading_rate = spreading_rate

        logger.info("语义记忆系统初始化")

    def add_concept(self, name: str, category: str,
                   properties: Dict[str, Any] = None,
                   description: str = "",
                   confidence: float = 1.0,
                   source: str = "user") -> str:
        """
        添加概念
        
        Args:
            name: 概念名称
            category: 类别
            properties: 属性
            description: 描述
            confidence: 置信度
            source: 来源
            
        Returns:
            节点ID
        """
        if name in self._name_index:
            node_id = self._name_index[name]
            node = self._nodes[node_id]
            if properties:
                node.properties.update(properties)
            if description:
                node.description = description
            node.confidence = max(node.confidence, confidence)
            node.updated_at = datetime.now().isoformat()
            return node_id

        if len(self._nodes) >= self._max_nodes:
            self._evict_lowest_activation()

        node_id = f"sem_{uuid.uuid4().hex[:12]}"
        node = SemanticNode(
            node_id=node_id,
            name=name,
            category=category,
            properties=properties or {},
            description=description,
            confidence=confidence,
            source=source
        )

        self._nodes[node_id] = node
        self._name_index[name] = node_id

        if category not in self._category_index:
            self._category_index[category] = set()
        self._category_index[category].add(node_id)

        logger.debug(f"添加概念: {name} (类别: {category})")
        return node_id

    def add_relation(self, source_name: str, target_name: str,
                    relation_type: RelationType,
                    strength: float = 1.0,
                    confidence: float = 1.0,
                    bidirectional: bool = False,
                    metadata: Dict[str, Any] = None) -> Optional[str]:
        """
        添加关系
        
        Args:
            source_name: 源概念名称
            target_name: 目标概念名称
            relation_type: 关系类型
            strength: 关系强度
            confidence: 置信度
            bidirectional: 是否双向
            metadata: 元数据
            
        Returns:
            关系ID
        """
        source_id = self._name_index.get(source_name)
        target_id = self._name_index.get(target_name)

        if not source_id or not target_id:
            logger.warning(f"概念不存在: {source_name} 或 {target_name}")
            return None

        if len(self._relations) >= self._max_relations:
            self._evict_weakest_relation()

        relation_id = f"rel_{uuid.uuid4().hex[:12]}"
        relation = SemanticRelation(
            relation_id=relation_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            strength=strength,
            confidence=confidence,
            bidirectional=bidirectional,
            metadata=metadata or {}
        )

        self._relations[relation_id] = relation
        logger.debug(f"添加关系: {source_name} --{relation_type.value}--> {target_name}")
        return relation_id

    def get_concept(self, name: str) -> Optional[SemanticNode]:
        """获取概念"""
        node_id = self._name_index.get(name)
        if node_id:
            node = self._nodes[node_id]
            node.activate()
            return node
        return None

    def search_concepts(self, query: str, limit: int = 10) -> List[SemanticNode]:
        """搜索概念"""
        results = []
        query_lower = query.lower()

        for node in self._nodes.values():
            score = 0.0

            if query_lower == node.name.lower():
                score = 1.0
            elif query_lower in node.name.lower():
                score = 0.8
            elif query_lower in node.description.lower():
                score = 0.5
            elif query_lower in node.category.lower():
                score = 0.4
            else:
                for prop_val in node.properties.values():
                    if isinstance(prop_val, str) and query_lower in prop_val.lower():
                        score = 0.3
                        break

            score += node.activation * 0.2

            if score > 0:
                results.append((node, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return [node for node, _ in results[:limit]]

    def get_related(self, name: str, relation_type: RelationType = None,
                   depth: int = 1) -> List[Tuple[SemanticNode, RelationType, float]]:
        """
        获取相关概念
        
        Args:
            name: 概念名称
            relation_type: 关系类型过滤
            depth: 搜索深度
            
        Returns:
            (节点, 关系类型, 强度) 列表
        """
        node_id = self._name_index.get(name)
        if not node_id:
            return []

        results = []
        visited = {node_id}
        current_level = [node_id]

        for _ in range(depth):
            next_level = []
            for nid in current_level:
                for rel in self._relations.values():
                    if relation_type and rel.relation_type != relation_type:
                        continue

                    target = None
                    if rel.source_id == nid and rel.target_id not in visited:
                        target = rel.target_id
                    elif rel.bidirectional and rel.target_id == nid and rel.source_id not in visited:
                        target = rel.source_id

                    if target and target not in visited:
                        visited.add(target)
                        next_level.append(target)
                        if target in self._nodes:
                            node = self._nodes[target]
                            node.activate(self._spreading_rate)
                            results.append((node, rel.relation_type, rel.strength))

            current_level = next_level

        return results

    def get_category_members(self, category: str) -> List[SemanticNode]:
        """获取类别成员"""
        node_ids = self._category_index.get(category, set())
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    def infer_is_a(self, name: str) -> List[str]:
        """推理 is-a 关系链"""
        chain = []
        current_name = name
        visited = set()

        while current_name and current_name not in visited:
            visited.add(current_name)
            chain.append(current_name)

            node_id = self._name_index.get(current_name)
            if not node_id:
                break

            parent = None
            for rel in self._relations.values():
                if rel.source_id == node_id and rel.relation_type == RelationType.IS_A:
                    parent = self._nodes.get(rel.target_id)
                    if parent:
                        parent_name = parent.name
                        break

            current_name = parent.name if parent else None

        return chain

    def decay_all(self):
        """衰减所有节点激活"""
        for node in self._nodes.values():
            node.decay(self._activation_decay_rate)

    def _evict_lowest_activation(self):
        """驱逐最低激活节点"""
        if not self._nodes:
            return

        min_node_id = min(self._nodes, key=lambda nid: self._nodes[nid].activation)
        node = self._nodes[min_node_id]
        self._remove_node(min_node_id, node)

    def _evict_weakest_relation(self):
        """驱逐最弱关系"""
        if not self._relations:
            return

        min_rel_id = min(self._relations, key=lambda rid: self._relations[rid].strength)
        del self._relations[min_rel_id]

    def _remove_node(self, node_id: str, node: SemanticNode):
        """移除节点"""
        self._name_index.pop(node.name, None)
        if node.category in self._category_index:
            self._category_index[node.category].discard(node_id)
        del self._nodes[node_id]

        rels_to_remove = [
            rid for rid, rel in self._relations.items()
            if rel.source_id == node_id or rel.target_id == node_id
        ]
        for rid in rels_to_remove:
            del self._relations[rid]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_nodes": len(self._nodes),
            "total_relations": len(self._relations),
            "categories": len(self._category_index),
            "avg_activation": (
                sum(n.activation for n in self._nodes.values()) / max(len(self._nodes), 1)
            ),
            "by_relation_type": {
                rt.value: sum(1 for r in self._relations.values() if r.relation_type == rt)
                for rt in RelationType
            },
            "top_activated": [
                {"name": n.name, "activation": round(n.activation, 3)}
                for n in sorted(self._nodes.values(), key=lambda x: x.activation, reverse=True)[:10]
            ]
        }


semantic_memory = SemanticMemory()


def get_semantic_memory() -> SemanticMemory:
    """获取全局语义记忆"""
    return semantic_memory
