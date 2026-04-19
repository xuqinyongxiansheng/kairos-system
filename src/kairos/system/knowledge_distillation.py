# -*- coding: utf-8 -*-
"""
知识蒸馏模块 (Knowledge Distillation)
Kairos 3.0 4b核心特性

特点:
- 从经验中提取知识
- 知识压缩与泛化
- 跨领域知识迁移
- 知识一致性验证
- 渐进式蒸馏
"""

import math
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import time


class KnowledgeType(Enum):
    """知识类型"""
    FACTUAL = "factual"
    PROCEDURAL = "procedural"
    CONCEPTUAL = "conceptual"
    METACOGNITIVE = "metacognitive"
    EXPERIENTIAL = "experiential"


class DistillationPhase(Enum):
    """蒸馏阶段"""
    EXTRACTION = "extraction"
    COMPRESSION = "compression"
    GENERALIZATION = "generalization"
    VALIDATION = "validation"
    INTEGRATION = "integration"


class KnowledgeStatus(Enum):
    """知识状态"""
    RAW = "raw"
    DISTILLED = "distilled"
    VALIDATED = "validated"
    INTEGRATED = "integrated"
    DEPRECATED = "deprecated"


@dataclass
class KnowledgeUnit:
    """知识单元"""
    knowledge_id: str
    knowledge_type: KnowledgeType
    content: str
    status: KnowledgeStatus
    
    source: str
    confidence: float
    generality: float
    
    created_at: float
    last_updated: float
    access_count: int = 0
    
    tags: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    related_knowledge: Set[str] = field(default_factory=set)
    
    compressed_content: Optional[str] = None
    compression_ratio: float = 1.0
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'knowledge_id': self.knowledge_id,
            'knowledge_type': self.knowledge_type.value,
            'content': self.content,
            'status': self.status.value,
            'source': self.source,
            'confidence': self.confidence,
            'generality': self.generality,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'access_count': self.access_count,
            'tags': self.tags,
            'prerequisites': self.prerequisites,
            'related_knowledge': list(self.related_knowledge),
            'compressed_content': self.compressed_content,
            'compression_ratio': self.compression_ratio,
            'metadata': self.metadata
        }


@dataclass
class DistillationResult:
    """蒸馏结果"""
    result_id: str
    phase: DistillationPhase
    input_count: int
    output_count: int
    compression_ratio: float
    quality_score: float
    knowledge_units: List[Dict[str, Any]]
    elapsed_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'result_id': self.result_id,
            'phase': self.phase.value,
            'input_count': self.input_count,
            'output_count': self.output_count,
            'compression_ratio': self.compression_ratio,
            'quality_score': self.quality_score,
            'knowledge_units': self.knowledge_units,
            'elapsed_ms': self.elapsed_ms
        }


class KnowledgeDistillation:
    """
    知识蒸馏引擎
    
    核心功能:
    - 从原始经验中提取知识
    - 压缩冗余知识
    - 泛化特定知识
    - 验证知识一致性
    - 迁移跨领域知识
    """
    
    def __init__(self):
        self.knowledge_base: Dict[str, KnowledgeUnit] = {}
        self.type_index: Dict[KnowledgeType, Set[str]] = defaultdict(set)
        self.tag_index: Dict[str, Set[str]] = defaultdict(set)
        
        self.distillation_history: List[DistillationResult] = []
        self._knowledge_counter = 0
        self._distillation_counter = 0
    
    def ingest(
        self,
        content: str,
        knowledge_type: KnowledgeType = KnowledgeType.EXPERIENTIAL,
        source: str = "experience",
        confidence: float = 0.7,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        摄入原始知识
        
        Args:
            content: 知识内容
            knowledge_type: 知识类型
            source: 来源
            confidence: 置信度
            tags: 标签
            metadata: 元数据
            
        Returns:
            知识ID
        """
        self._knowledge_counter += 1
        knowledge_id = f"know_{self._knowledge_counter}"
        
        unit = KnowledgeUnit(
            knowledge_id=knowledge_id,
            knowledge_type=knowledge_type,
            content=content,
            status=KnowledgeStatus.RAW,
            source=source,
            confidence=confidence,
            generality=0.3,
            created_at=time.time(),
            last_updated=time.time(),
            tags=tags or [],
            metadata=metadata or {}
        )
        
        self.knowledge_base[knowledge_id] = unit
        self.type_index[knowledge_type].add(knowledge_id)
        
        for tag in (tags or []):
            self.tag_index[tag].add(knowledge_id)
        
        return knowledge_id
    
    def extract_knowledge(
        self,
        raw_contents: List[Dict[str, Any]]
    ) -> DistillationResult:
        """
        从原始内容中提取知识
        
        Args:
            raw_contents: 原始内容列表
            
        Returns:
            蒸馏结果
        """
        start_time = time.time()
        self._distillation_counter += 1
        
        extracted_units = []
        
        for raw in raw_contents:
            content = raw.get('content', '')
            knowledge_type = KnowledgeType(raw.get('type', 'experiential'))
            
            patterns = self._identify_patterns(content)
            
            for pattern in patterns:
                self._knowledge_counter += 1
                knowledge_id = f"know_{self._knowledge_counter}"
                
                unit = KnowledgeUnit(
                    knowledge_id=knowledge_id,
                    knowledge_type=knowledge_type,
                    content=pattern['content'],
                    status=KnowledgeStatus.DISTILLED,
                    source=raw.get('source', 'extraction'),
                    confidence=pattern['confidence'],
                    generality=pattern['generality'],
                    created_at=time.time(),
                    last_updated=time.time(),
                    tags=pattern.get('tags', []),
                    metadata={'extraction_method': 'pattern_mining'}
                )
                
                self.knowledge_base[knowledge_id] = unit
                self.type_index[knowledge_type].add(knowledge_id)
                for tag in unit.tags:
                    self.tag_index[tag].add(knowledge_id)
                
                extracted_units.append(unit.to_dict())
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        result = DistillationResult(
            result_id=f"dist_{self._distillation_counter}",
            phase=DistillationPhase.EXTRACTION,
            input_count=len(raw_contents),
            output_count=len(extracted_units),
            compression_ratio=len(extracted_units) / len(raw_contents) if raw_contents else 0,
            quality_score=self._compute_quality_score(extracted_units),
            knowledge_units=extracted_units,
            elapsed_ms=elapsed_ms
        )
        
        self.distillation_history.append(result)
        return result
    
    def _identify_patterns(self, content: str) -> List[Dict[str, Any]]:
        """识别模式"""
        patterns = []
        
        sentences = [s.strip() for s in content.split('.') if s.strip()]
        
        for sentence in sentences:
            if len(sentence) < 10:
                continue
            
            confidence = 0.6
            generality = 0.4
            
            if any(word in sentence.lower() for word in ['always', 'never', '必须', '总是', '从不']):
                confidence += 0.15
                generality += 0.2
            
            if any(word in sentence.lower() for word in ['sometimes', '可能', 'usually', '通常']):
                generality += 0.1
            
            if 'if' in sentence.lower() or '如果' in sentence.lower():
                confidence += 0.1
                generality += 0.1
            
            tags = self._extract_tags(sentence)
            
            patterns.append({
                'content': sentence,
                'confidence': min(1.0, confidence),
                'generality': min(1.0, generality),
                'tags': tags
            })
        
        return patterns
    
    def _extract_tags(self, content: str) -> List[str]:
        """提取标签"""
        tags = []
        
        tech_keywords = ['python', 'code', 'api', 'database', 'algorithm', '代码', '算法', '接口']
        for keyword in tech_keywords:
            if keyword in content.lower():
                tags.append('technology')
                break
        
        action_keywords = ['create', 'delete', 'update', 'run', '创建', '删除', '修改', '运行']
        for keyword in action_keywords:
            if keyword in content.lower():
                tags.append('action')
                break
        
        concept_keywords = ['concept', 'theory', 'principle', '概念', '理论', '原理']
        for keyword in concept_keywords:
            if keyword in content.lower():
                tags.append('concept')
                break
        
        if not tags:
            tags.append('general')
        
        return tags
    
    def compress_knowledge(
        self,
        knowledge_ids: List[str] = None,
        target_ratio: float = 0.5
    ) -> DistillationResult:
        """
        压缩知识
        
        Args:
            knowledge_ids: 要压缩的知识ID列表
            target_ratio: 目标压缩比
            
        Returns:
            蒸馏结果
        """
        start_time = time.time()
        self._distillation_counter += 1
        
        if knowledge_ids is None:
            knowledge_ids = [
                kid for kid, unit in self.knowledge_base.items()
                if unit.status == KnowledgeStatus.DISTILLED
            ]
        
        groups = self._group_similar_knowledge(knowledge_ids)
        
        compressed_units = []
        for group_key, group_ids in groups.items():
            if len(group_ids) < 2:
                continue
            
            group_units = [
                self.knowledge_base[kid] for kid in group_ids
                if kid in self.knowledge_base
            ]
            
            merged_content = self._merge_contents(group_units)
            
            self._knowledge_counter += 1
            knowledge_id = f"know_{self._knowledge_counter}"
            
            avg_confidence = sum(u.confidence for u in group_units) / len(group_units)
            max_generality = max(u.generality for u in group_units)
            
            all_tags = set()
            for u in group_units:
                all_tags.update(u.tags)
            
            compressed_unit = KnowledgeUnit(
                knowledge_id=knowledge_id,
                knowledge_type=group_units[0].knowledge_type,
                content=merged_content,
                status=KnowledgeStatus.DISTILLED,
                source='compression',
                confidence=min(1.0, avg_confidence + 0.05),
                generality=min(1.0, max_generality + 0.1),
                created_at=time.time(),
                last_updated=time.time(),
                tags=list(all_tags),
                compressed_content=merged_content,
                compression_ratio=len(group_ids) / 1,
                metadata={
                    'merged_from': group_ids,
                    'original_count': len(group_ids)
                }
            )
            
            self.knowledge_base[knowledge_id] = compressed_unit
            self.type_index[compressed_unit.knowledge_type].add(knowledge_id)
            for tag in all_tags:
                self.tag_index[tag].add(knowledge_id)
            
            for kid in group_ids:
                if kid in self.knowledge_base:
                    self.knowledge_base[kid].status = KnowledgeStatus.DEPRECATED
            
            compressed_units.append(compressed_unit.to_dict())
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        result = DistillationResult(
            result_id=f"dist_{self._distillation_counter}",
            phase=DistillationPhase.COMPRESSION,
            input_count=len(knowledge_ids),
            output_count=len(compressed_units),
            compression_ratio=len(compressed_units) / len(knowledge_ids) if knowledge_ids else 0,
            quality_score=self._compute_quality_score(compressed_units),
            knowledge_units=compressed_units,
            elapsed_ms=elapsed_ms
        )
        
        self.distillation_history.append(result)
        return result
    
    def _group_similar_knowledge(self, knowledge_ids: List[str]) -> Dict[str, List[str]]:
        """分组相似知识"""
        groups = defaultdict(list)
        
        for kid in knowledge_ids:
            unit = self.knowledge_base.get(kid)
            if not unit:
                continue
            
            group_key = f"{unit.knowledge_type.value}_{'_'.join(sorted(unit.tags))}"
            groups[group_key].append(kid)
        
        return dict(groups)
    
    def _merge_contents(self, units: List[KnowledgeUnit]) -> str:
        """合并内容"""
        unique_contents = []
        seen = set()
        
        for unit in units:
            normalized = unit.content.strip().lower()
            if normalized not in seen:
                seen.add(normalized)
                unique_contents.append(unit.content.strip())
        
        if len(unique_contents) == 1:
            return unique_contents[0]
        
        merged = " | ".join(unique_contents[:3])
        
        if len(unique_contents) > 3:
            merged += f" | ...(共{len(unique_contents)}条)"
        
        return merged
    
    def generalize_knowledge(
        self,
        knowledge_ids: List[str] = None
    ) -> DistillationResult:
        """
        泛化知识
        
        Args:
            knowledge_ids: 要泛化的知识ID列表
            
        Returns:
            蒸馏结果
        """
        start_time = time.time()
        self._distillation_counter += 1
        
        if knowledge_ids is None:
            knowledge_ids = [
                kid for kid, unit in self.knowledge_base.items()
                if unit.status in [KnowledgeStatus.DISTILLED, KnowledgeStatus.VALIDATED]
                and unit.generality < 0.7
            ]
        
        generalized_units = []
        
        for kid in knowledge_ids:
            unit = self.knowledge_base.get(kid)
            if not unit:
                continue
            
            generalized_content = self._generalize_content(unit.content)
            
            self._knowledge_counter += 1
            new_kid = f"know_{self._knowledge_counter}"
            
            generalized_unit = KnowledgeUnit(
                knowledge_id=new_kid,
                knowledge_type=unit.knowledge_type,
                content=generalized_content,
                status=KnowledgeStatus.VALIDATED,
                source='generalization',
                confidence=unit.confidence * 0.9,
                generality=min(1.0, unit.generality + 0.2),
                created_at=time.time(),
                last_updated=time.time(),
                tags=unit.tags + ['generalized'],
                related_knowledge=unit.related_knowledge | {kid},
                metadata={'generalized_from': kid}
            )
            
            self.knowledge_base[new_kid] = generalized_unit
            self.type_index[generalized_unit.knowledge_type].add(new_kid)
            for tag in generalized_unit.tags:
                self.tag_index[tag].add(new_kid)
            
            generalized_units.append(generalized_unit.to_dict())
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        result = DistillationResult(
            result_id=f"dist_{self._distillation_counter}",
            phase=DistillationPhase.GENERALIZATION,
            input_count=len(knowledge_ids),
            output_count=len(generalized_units),
            compression_ratio=len(generalized_units) / len(knowledge_ids) if knowledge_ids else 0,
            quality_score=self._compute_quality_score(generalized_units),
            knowledge_units=generalized_units,
            elapsed_ms=elapsed_ms
        )
        
        self.distillation_history.append(result)
        return result
    
    def _generalize_content(self, content: str) -> str:
        """泛化内容"""
        generalized = content
        
        specific_patterns = {
            'python': '编程语言',
            'javascript': '编程语言',
            'java': '编程语言',
            'mysql': '数据库',
            'postgresql': '数据库',
            'mongodb': '数据库',
            'windows': '操作系统',
            'linux': '操作系统',
            'macos': '操作系统'
        }
        
        for specific, general in specific_patterns.items():
            generalized = generalized.replace(specific, general)
        
        return generalized
    
    def validate_knowledge(
        self,
        knowledge_ids: List[str] = None
    ) -> Dict[str, Any]:
        """
        验证知识一致性
        
        Args:
            knowledge_ids: 要验证的知识ID列表
            
        Returns:
            验证结果
        """
        if knowledge_ids is None:
            knowledge_ids = list(self.knowledge_base.keys())
        
        contradictions = []
        redundancies = []
        validated = 0
        
        units = [
            self.knowledge_base[kid] for kid in knowledge_ids
            if kid in self.knowledge_base
        ]
        
        for i, unit_a in enumerate(units):
            for unit_b in units[i+1:]:
                similarity = self._compute_similarity(unit_a.content, unit_b.content)
                
                if similarity > 0.9:
                    redundancies.append({
                        'unit_a': unit_a.knowledge_id,
                        'unit_b': unit_b.knowledge_id,
                        'similarity': similarity
                    })
                
                if similarity > 0.5 and self._check_contradiction(unit_a.content, unit_b.content):
                    contradictions.append({
                        'unit_a': unit_a.knowledge_id,
                        'unit_b': unit_b.knowledge_id,
                        'similarity': similarity
                    })
        
        for unit in units:
            if unit.status == KnowledgeStatus.DISTILLED:
                unit.status = KnowledgeStatus.VALIDATED
                validated += 1
        
        return {
            'total_checked': len(units),
            'validated': validated,
            'contradictions': contradictions,
            'redundancies': redundancies,
            'consistency_score': 1.0 - len(contradictions) / max(1, len(units))
        }
    
    def _compute_similarity(self, content_a: str, content_b: str) -> float:
        """计算相似度"""
        words_a = set(content_a.lower().split())
        words_b = set(content_b.lower().split())
        
        if not words_a or not words_b:
            return 0.0
        
        intersection = words_a & words_b
        union = words_a | words_b
        
        return len(intersection) / len(union)
    
    def _check_contradiction(self, content_a: str, content_b: str) -> bool:
        """检查矛盾"""
        negation_words = ['不', '非', '无', 'not', 'no', 'never', 'cannot']
        
        for neg in negation_words:
            if neg in content_a.lower() and neg not in content_b.lower():
                return True
            if neg not in content_a.lower() and neg in content_b.lower():
                return True
        
        return False
    
    def _compute_quality_score(self, units: List[Dict[str, Any]]) -> float:
        """计算质量分数"""
        if not units:
            return 0.0
        
        total_confidence = sum(u.get('confidence', 0.5) for u in units)
        total_generality = sum(u.get('generality', 0.5) for u in units)
        
        avg_confidence = total_confidence / len(units)
        avg_generality = total_generality / len(units)
        
        return avg_confidence * 0.6 + avg_generality * 0.4
    
    def full_distillation(self) -> Dict[str, Any]:
        """
        完整蒸馏流程
        
        Returns:
            蒸馏结果
        """
        extraction_result = None
        compression_result = self.compress_knowledge()
        generalization_result = self.generalize_knowledge()
        validation_result = self.validate_knowledge()
        
        return {
            'compression': compression_result.to_dict(),
            'generalization': generalization_result.to_dict(),
            'validation': validation_result,
            'total_knowledge': len(self.knowledge_base),
            'active_knowledge': sum(
                1 for u in self.knowledge_base.values()
                if u.status in [KnowledgeStatus.VALIDATED, KnowledgeStatus.INTEGRATED]
            )
        }
    
    def query_knowledge(
        self,
        query: str,
        knowledge_types: List[KnowledgeType] = None,
        min_confidence: float = 0.3,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        查询知识
            
        Args:
            query: 查询字符串
            knowledge_types: 知识类型过滤
            min_confidence: 最低置信度
            limit: 返回数量限制
            
        Returns:
            知识列表
        """
        results = []
        query_lower = query.lower()
        
        for unit in self.knowledge_base.values():
            if unit.status == KnowledgeStatus.DEPRECATED:
                continue
            
            if knowledge_types and unit.knowledge_type not in knowledge_types:
                continue
            
            if unit.confidence < min_confidence:
                continue
            
            score = 0
            if query_lower in unit.content.lower():
                score += 0.5
            
            for tag in unit.tags:
                if query_lower in tag.lower():
                    score += 0.2
            
            score += unit.confidence * 0.2
            score += unit.generality * 0.1
            
            if score > 0:
                results.append((unit.to_dict(), score))
        
        results.sort(key=lambda x: -x[1])
        return [r for r, _ in results[:limit]]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        status_counts = defaultdict(int)
        type_counts = defaultdict(int)
        
        for unit in self.knowledge_base.values():
            status_counts[unit.status.value] += 1
            type_counts[unit.knowledge_type.value] += 1
        
        return {
            'total_knowledge': len(self.knowledge_base),
            'status_distribution': dict(status_counts),
            'type_distribution': dict(type_counts),
            'tag_count': len(self.tag_index),
            'distillation_history_count': len(self.distillation_history)
        }
    
    def reset(self):
        """重置蒸馏引擎"""
        self.knowledge_base.clear()
        self.type_index.clear()
        self.tag_index.clear()
        self.distillation_history.clear()


def create_knowledge_distillation() -> KnowledgeDistillation:
    """创建知识蒸馏实例"""
    return KnowledgeDistillation()
