# -*- coding: utf-8 -*-
"""
因果推理链 (Causal Reasoning Chain)
Kairos 3.0 4b核心组件

特点:
- 结构化因果推理
- 多步推理链构建
- 置信度传播
- 反事实推理
"""

import math
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import time


class CausalRelationType(Enum):
    """因果关系类型"""
    DIRECT = "direct"
    INDIRECT = "indirect"
    CONDITIONAL = "conditional"
    PROBABILISTIC = "probabilistic"
    TEMPORAL = "temporal"


class NodeType(Enum):
    """节点类型"""
    CAUSE = "cause"
    EFFECT = "effect"
    MEDIATOR = "mediator"
    CONFOUNDER = "confounder"
    CONDITION = "condition"


@dataclass
class CausalNode:
    """因果节点"""
    id: str
    content: str
    node_type: NodeType
    confidence: float = 1.0
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'content': self.content,
            'node_type': self.node_type.value,
            'confidence': self.confidence,
            'evidence': self.evidence,
            'metadata': self.metadata
        }


@dataclass
class CausalEdge:
    """因果边"""
    source_id: str
    target_id: str
    relation_type: CausalRelationType
    strength: float = 1.0
    conditions: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'source_id': self.source_id,
            'target_id': self.target_id,
            'relation_type': self.relation_type.value,
            'strength': self.strength,
            'conditions': self.conditions,
            'evidence': self.evidence
        }


@dataclass
class CausalChain:
    """因果链"""
    nodes: List[CausalNode] = field(default_factory=list)
    edges: List[CausalEdge] = field(default_factory=list)
    root_cause: Optional[str] = None
    final_effect: Optional[str] = None
    chain_confidence: float = 1.0
    
    def add_node(self, node: CausalNode) -> str:
        self.nodes.append(node)
        return node.id
    
    def add_edge(self, edge: CausalEdge):
        self.edges.append(edge)
    
    def get_node(self, node_id: str) -> Optional[CausalNode]:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_children(self, node_id: str) -> List[CausalNode]:
        children = []
        for edge in self.edges:
            if edge.source_id == node_id:
                child = self.get_node(edge.target_id)
                if child:
                    children.append(child)
        return children
    
    def get_parents(self, node_id: str) -> List[CausalNode]:
        parents = []
        for edge in self.edges:
            if edge.target_id == node_id:
                parent = self.get_node(edge.source_id)
                if parent:
                    parents.append(parent)
        return parents
    
    def get_path(self, from_id: str, to_id: str) -> List[List[str]]:
        paths = []
        self._dfs_path(from_id, to_id, [], paths)
        return paths
    
    def _dfs_path(self, current: str, target: str, path: List[str], paths: List[List[str]]):
        path = path + [current]
        if current == target:
            paths.append(path)
            return
        
        for edge in self.edges:
            if edge.source_id == current and edge.target_id not in path:
                self._dfs_path(edge.target_id, target, path, paths)
    
    def compute_chain_confidence(self) -> float:
        if not self.edges:
            return 1.0
        
        total_strength = sum(e.strength for e in self.edges)
        avg_strength = total_strength / len(self.edges)
        
        node_confidence = 1.0
        for node in self.nodes:
            node_confidence *= node.confidence
        
        path_length_factor = 1.0 / (1.0 + 0.1 * len(self.edges))
        
        self.chain_confidence = avg_strength * node_confidence * path_length_factor
        return self.chain_confidence
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'nodes': [n.to_dict() for n in self.nodes],
            'edges': [e.to_dict() for e in self.edges],
            'root_cause': self.root_cause,
            'final_effect': self.final_effect,
            'chain_confidence': self.chain_confidence
        }


class CausalReasoningEngine:
    """
    因果推理引擎
    
    核心功能:
    - 构建因果链
    - 推断因果关系
    - 置信度传播
    - 反事实推理
    """
    
    def __init__(self):
        self.chains: Dict[str, CausalChain] = {}
        self.knowledge_base: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._node_counter = 0
        self._chain_counter = 0
    
    def create_node(
        self,
        content: str,
        node_type: NodeType,
        confidence: float = 1.0,
        evidence: List[str] = None
    ) -> CausalNode:
        """
        创建因果节点
        
        Args:
            content: 节点内容
            node_type: 节点类型
            confidence: 置信度
            evidence: 证据列表
            
        Returns:
            因果节点
        """
        self._node_counter += 1
        node_id = f"node_{self._node_counter}"
        
        return CausalNode(
            id=node_id,
            content=content,
            node_type=node_type,
            confidence=confidence,
            evidence=evidence or []
        )
    
    def create_chain(self) -> Tuple[str, CausalChain]:
        """
        创建新的因果链
        
        Returns:
            (链ID, 因果链)
        """
        self._chain_counter += 1
        chain_id = f"chain_{self._chain_counter}"
        
        chain = CausalChain()
        self.chains[chain_id] = chain
        
        return chain_id, chain
    
    def infer_causality(
        self,
        cause: str,
        effect: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        推断因果关系
        
        Args:
            cause: 原因描述
            effect: 结果描述
            context: 上下文
            
        Returns:
            推断结果
        """
        start_time = time.time()
        
        chain_id, chain = self.create_chain()
        
        cause_node = self.create_node(
            content=cause,
            node_type=NodeType.CAUSE,
            confidence=self._estimate_initial_confidence(cause)
        )
        chain.add_node(cause_node)
        chain.root_cause = cause_node.id
        
        effect_node = self.create_node(
            content=effect,
            node_type=NodeType.EFFECT,
            confidence=self._estimate_initial_confidence(effect)
        )
        chain.add_node(effect_node)
        chain.final_effect = effect_node.id
        
        mediators = self._find_mediators(cause, effect, context)
        prev_node_id = cause_node.id
        
        for mediator in mediators:
            mediator_node = self.create_node(
                content=mediator['content'],
                node_type=NodeType.MEDIATOR,
                confidence=mediator['confidence']
            )
            chain.add_node(mediator_node)
            
            edge = CausalEdge(
                source_id=prev_node_id,
                target_id=mediator_node.id,
                relation_type=CausalRelationType.INDIRECT,
                strength=mediator['strength']
            )
            chain.add_edge(edge)
            prev_node_id = mediator_node.id
        
        final_edge = CausalEdge(
            source_id=prev_node_id,
            target_id=effect_node.id,
            relation_type=CausalRelationType.DIRECT,
            strength=self._estimate_causal_strength(cause, effect)
        )
        chain.add_edge(final_edge)
        
        chain.compute_chain_confidence()
        
        elapsed = time.time() - start_time
        
        return {
            'chain_id': chain_id,
            'chain': chain.to_dict(),
            'confidence': chain.chain_confidence,
            'mediators_count': len(mediators),
            'elapsed_ms': elapsed * 1000
        }
    
    def _estimate_initial_confidence(self, content: str) -> float:
        """估算初始置信度"""
        base_confidence = 0.7
        
        if len(content) > 50:
            base_confidence += 0.1
        
        knowledge = self.knowledge_base.get(content, [])
        if knowledge:
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def _find_mediators(
        self,
        cause: str,
        effect: str,
        context: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """查找中介变量"""
        mediators = []
        
        cause_keywords = set(cause.lower().split())
        effect_keywords = set(effect.lower().split())
        
        for key, knowledge_list in self.knowledge_base.items():
            for knowledge in knowledge_list:
                if 'mediates' in knowledge:
                    mediator_keywords = set(key.lower().split())
                    
                    if mediator_keywords & cause_keywords and mediator_keywords & effect_keywords:
                        mediators.append({
                            'content': key,
                            'confidence': knowledge.get('confidence', 0.7),
                            'strength': knowledge.get('strength', 0.8),
                            'type': CausalRelationType.INDIRECT
                        })
        
        return mediators[:3]
    
    def _estimate_causal_strength(self, cause: str, effect: str) -> float:
        """估算因果强度"""
        base_strength = 0.7
        
        for knowledge_list in self.knowledge_base.values():
            for knowledge in knowledge_list:
                if knowledge.get('cause') == cause and knowledge.get('effect') == effect:
                    base_strength = max(base_strength, knowledge.get('strength', 0.8))
        
        return base_strength
    
    def propagate_confidence(
        self,
        chain_id: str,
        updated_node_id: str,
        new_confidence: float
    ) -> Dict[str, Any]:
        """
        传播置信度更新
        
        Args:
            chain_id: 链ID
            updated_node_id: 更新的节点ID
            new_confidence: 新置信度
            
        Returns:
            更新结果
        """
        chain = self.chains.get(chain_id)
        if not chain:
            return {'error': 'Chain not found'}
        
        node = chain.get_node(updated_node_id)
        if node:
            node.confidence = new_confidence
        
        affected_nodes = []
        
        children = chain.get_children(updated_node_id)
        for child in children:
            propagation_factor = 0.9
            child.confidence = child.confidence * propagation_factor + new_confidence * (1 - propagation_factor)
            affected_nodes.append(child.id)
        
        chain.compute_chain_confidence()
        
        return {
            'chain_id': chain_id,
            'updated_node': updated_node_id,
            'affected_nodes': affected_nodes,
            'new_chain_confidence': chain.chain_confidence
        }
    
    def counterfactual_reasoning(
        self,
        chain_id: str,
        intervention: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        反事实推理
        
        Args:
            chain_id: 链ID
            intervention: 干预 {node_id: new_value}
            
        Returns:
            反事实推理结果
        """
        chain = self.chains.get(chain_id)
        if not chain:
            return {'error': 'Chain not found'}
        
        original_chain = chain.to_dict()
        
        for node_id, new_value in intervention.items():
            node = chain.get_node(node_id)
            if node:
                node.content = new_value
                node.confidence *= 0.8
        
        for edge in chain.edges:
            edge.strength *= 0.9
        
        chain.compute_chain_confidence()
        
        counterfactual_chain = chain.to_dict()
        
        return {
            'chain_id': chain_id,
            'original_chain': original_chain,
            'counterfactual_chain': counterfactual_chain,
            'confidence_change': chain.chain_confidence - original_chain['chain_confidence'],
            'intervention': intervention
        }
    
    def add_knowledge(
        self,
        concept: str,
        knowledge: Dict[str, Any]
    ):
        """
        添加知识到知识库
        
        Args:
            concept: 概念
            knowledge: 知识内容
        """
        self.knowledge_base[concept].append(knowledge)
    
    def find_causal_path(
        self,
        chain_id: str,
        start_node: str,
        end_node: str
    ) -> Dict[str, Any]:
        """
        查找因果路径
        
        Args:
            chain_id: 链ID
            start_node: 起始节点
            end_node: 结束节点
            
        Returns:
            路径信息
        """
        chain = self.chains.get(chain_id)
        if not chain:
            return {'error': 'Chain not found'}
        
        paths = chain.get_path(start_node, end_node)
        
        analyzed_paths = []
        for path in paths:
            path_nodes = [chain.get_node(nid) for nid in path]
            path_confidence = 1.0
            path_strength = 0.0
            
            for i in range(len(path) - 1):
                for edge in chain.edges:
                    if edge.source_id == path[i] and edge.target_id == path[i + 1]:
                        path_confidence *= edge.strength
                        path_strength += edge.strength
                        break
            
            analyzed_paths.append({
                'path': path,
                'nodes': [n.to_dict() if n else None for n in path_nodes],
                'confidence': path_confidence,
                'avg_strength': path_strength / (len(path) - 1) if len(path) > 1 else 0
            })
        
        return {
            'chain_id': chain_id,
            'start': start_node,
            'end': end_node,
            'paths': analyzed_paths,
            'best_path': max(analyzed_paths, key=lambda p: p['confidence']) if analyzed_paths else None
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息
        """
        total_nodes = sum(len(chain.nodes) for chain in self.chains.values())
        total_edges = sum(len(chain.edges) for chain in self.chains.values())
        
        avg_confidence = 0.0
        if self.chains:
            avg_confidence = sum(
                chain.chain_confidence for chain in self.chains.values()
            ) / len(self.chains)
        
        return {
            'total_chains': len(self.chains),
            'total_nodes': total_nodes,
            'total_edges': total_edges,
            'avg_chain_confidence': avg_confidence,
            'knowledge_base_size': sum(len(v) for v in self.knowledge_base.values())
        }


def create_causal_engine() -> CausalReasoningEngine:
    """创建因果推理引擎实例"""
    return CausalReasoningEngine()
