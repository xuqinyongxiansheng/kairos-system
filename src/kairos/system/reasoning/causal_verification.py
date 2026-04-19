# -*- coding: utf-8 -*-
"""
因果验证引擎 (Causal Verification Engine)
Kairos 3.0 4b核心组件

特点:
- 验证因果关系的有效性
- 检测虚假相关
- 控制混淆变量
- 统计显著性检验
"""

import math
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import time


class VerificationStatus(Enum):
    """验证状态"""
    VALID = "valid"
    INVALID = "invalid"
    UNCERTAIN = "uncertain"
    NEEDS_MORE_DATA = "needs_more_data"


class ConfounderType(Enum):
    """混淆变量类型"""
    OBSERVED = "observed"
    UNOBSERVED = "unobserved"
    POTENTIAL = "potential"


@dataclass
class VerificationResult:
    """验证结果"""
    status: VerificationStatus
    confidence: float
    evidence: List[str]
    issues: List[str]
    recommendations: List[str]
    statistics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'confidence': self.confidence,
            'evidence': self.evidence,
            'issues': self.issues,
            'recommendations': self.recommendations,
            'statistics': self.statistics
        }


@dataclass
class Confounder:
    """混淆变量"""
    name: str
    confounder_type: ConfounderType
    affects_cause: bool
    affects_effect: bool
    strength: float
    controllable: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'type': self.confounder_type.value,
            'affects_cause': self.affects_cause,
            'affects_effect': self.affects_effect,
            'strength': self.strength,
            'controllable': self.controllable
        }


class CausalVerificationEngine:
    """
    因果验证引擎
    
    核心功能:
    - 验证因果链有效性
    - 检测混淆变量
    - 控制选择性偏差
    - 统计检验
    """
    
    def __init__(self):
        self.confounders: Dict[str, List[Confounder]] = defaultdict(list)
        self.verification_history: List[Dict[str, Any]] = []
        self._significance_level = 0.05
    
    def verify_causal_chain(
        self,
        chain: Dict[str, Any],
        data: Optional[Dict[str, List[float]]] = None
    ) -> VerificationResult:
        """
        验证因果链
        
        Args:
            chain: 因果链数据
            data: 可选的观测数据
            
        Returns:
            验证结果
        """
        start_time = time.time()
        
        evidence = []
        issues = []
        recommendations = []
        statistics = {}
        
        nodes = chain.get('nodes', [])
        edges = chain.get('edges', [])
        
        if len(nodes) < 2:
            return VerificationResult(
                status=VerificationStatus.INVALID,
                confidence=0.0,
                evidence=[],
                issues=["因果链至少需要两个节点"],
                recommendations=["添加原因和结果节点"]
            )
        
        if not edges:
            return VerificationResult(
                status=VerificationStatus.INVALID,
                confidence=0.0,
                evidence=[],
                issues=["因果链缺少连接边"],
                recommendations=["添加因果连接"]
            )
        
        node_ids = {n['id'] for n in nodes}
        for edge in edges:
            if edge['source_id'] not in node_ids:
                issues.append(f"边引用不存在的源节点: {edge['source_id']}")
            if edge['target_id'] not in node_ids:
                issues.append(f"边引用不存在的目标节点: {edge['target_id']}")
        
        if issues:
            return VerificationResult(
                status=VerificationStatus.INVALID,
                confidence=0.0,
                evidence=[],
                issues=issues,
                recommendations=["修复节点引用错误"]
            )
        
        cycle_check = self._detect_cycles(nodes, edges)
        if cycle_check['has_cycle']:
            issues.append(f"检测到因果循环: {' -> '.join(cycle_check['cycle'])}")
            recommendations.append("移除循环依赖")
        else:
            evidence.append("因果链无循环")
        
        root_cause = chain.get('root_cause')
        final_effect = chain.get('final_effect')
        
        if root_cause:
            root_reachable = self._check_reachability(root_cause, nodes, edges)
            unreachable = node_ids - root_reachable - {root_cause}
            if unreachable:
                issues.append(f"存在从根原因不可达的节点: {unreachable}")
        
        confounder_check = self._check_confounders(chain)
        if confounder_check['confounders']:
            for cf in confounder_check['confounders']:
                issues.append(f"检测到潜在混淆变量: {cf['name']}")
                recommendations.append(f"控制混淆变量: {cf['name']}")
        else:
            evidence.append("未检测到明显混淆变量")
        
        statistics['avg_edge_strength'] = sum(e['strength'] for e in edges) / len(edges)
        statistics['min_node_confidence'] = min(n['confidence'] for n in nodes)
        statistics['chain_depth'] = self._compute_chain_depth(nodes, edges)
        
        if data:
            stat_test = self._statistical_test(chain, data)
            statistics.update(stat_test['statistics'])
            if stat_test['significant']:
                evidence.append(f"统计检验显著 (p={stat_test['p_value']:.4f})")
            else:
                issues.append(f"统计检验不显著 (p={stat_test['p_value']:.4f})")
                recommendations.append("收集更多数据或检查因果假设")
        
        confidence = self._compute_verification_confidence(
            evidence, issues, statistics
        )
        
        if confidence >= 0.8:
            status = VerificationStatus.VALID
        elif confidence >= 0.5:
            status = VerificationStatus.UNCERTAIN
        elif confidence >= 0.3:
            status = VerificationStatus.NEEDS_MORE_DATA
        else:
            status = VerificationStatus.INVALID
        
        result = VerificationResult(
            status=status,
            confidence=confidence,
            evidence=evidence,
            issues=issues,
            recommendations=recommendations,
            statistics=statistics
        )
        
        elapsed = time.time() - start_time
        self.verification_history.append({
            'chain_id': chain.get('chain_id', 'unknown'),
            'status': status.value,
            'confidence': confidence,
            'elapsed_ms': elapsed * 1000
        })
        
        return result
    
    def _detect_cycles(
        self,
        nodes: List[Dict],
        edges: List[Dict]
    ) -> Dict[str, Any]:
        """检测循环"""
        graph = defaultdict(list)
        for edge in edges:
            graph[edge['source_id']].append(edge['target_id'])
        
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph[node]:
                if neighbor not in visited:
                    result = dfs(neighbor)
                    if result:
                        return result
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]
            
            path.pop()
            rec_stack.remove(node)
            return None
        
        for node in nodes:
            if node['id'] not in visited:
                cycle = dfs(node['id'])
                if cycle:
                    return {'has_cycle': True, 'cycle': cycle}
        
        return {'has_cycle': False, 'cycle': None}
    
    def _check_reachability(
        self,
        start: str,
        nodes: List[Dict],
        edges: List[Dict]
    ) -> Set[str]:
        """检查可达性"""
        graph = defaultdict(list)
        for edge in edges:
            graph[edge['source_id']].append(edge['target_id'])
        
        reachable = set()
        queue = [start]
        
        while queue:
            node = queue.pop(0)
            if node not in reachable:
                reachable.add(node)
                queue.extend(graph[node])
        
        return reachable
    
    def _check_confounders(self, chain: Dict[str, Any]) -> Dict[str, Any]:
        """检查混淆变量"""
        detected = []
        
        nodes = chain.get('nodes', [])
        for node in nodes:
            node_type = node.get('node_type', '')
            content = node.get('content', '').lower()
            
            if 'time' in content or 'date' in content:
                detected.append({
                    'name': '时间因素',
                    'type': 'potential',
                    'strength': 0.7
                })
            
            if 'user' in content or 'person' in content:
                detected.append({
                    'name': '个体差异',
                    'type': 'potential',
                    'strength': 0.6
                })
            
            if 'environment' in content or 'context' in content:
                detected.append({
                    'name': '环境因素',
                    'type': 'potential',
                    'strength': 0.5
                })
        
        return {'confounders': detected}
    
    def _compute_chain_depth(
        self,
        nodes: List[Dict],
        edges: List[Dict]
    ) -> int:
        """计算链深度"""
        if not nodes or not edges:
            return 0
        
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        for edge in edges:
            graph[edge['source_id']].append(edge['target_id'])
            in_degree[edge['target_id']] += 1
        
        node_ids = {n['id'] for n in nodes}
        roots = [nid for nid in node_ids if in_degree[nid] == 0]
        
        max_depth = 0
        for root in roots:
            depth = self._dfs_depth(root, graph, set())
            max_depth = max(max_depth, depth)
        
        return max_depth
    
    def _dfs_depth(
        self,
        node: str,
        graph: Dict[str, List[str]],
        visited: Set[str]
    ) -> int:
        """DFS计算深度"""
        if node in visited:
            return 0
        
        visited.add(node)
        
        if not graph[node]:
            return 1
        
        max_child_depth = 0
        for child in graph[node]:
            child_depth = self._dfs_depth(child, graph, visited.copy())
            max_child_depth = max(max_child_depth, child_depth)
        
        return 1 + max_child_depth
    
    def _statistical_test(
        self,
        chain: Dict[str, Any],
        data: Dict[str, List[float]]
    ) -> Dict[str, Any]:
        """统计检验"""
        cause_data = data.get('cause', [])
        effect_data = data.get('effect', [])
        
        if not cause_data or not effect_data:
            return {
                'significant': False,
                'p_value': 1.0,
                'statistics': {}
            }
        
        n = min(len(cause_data), len(effect_data))
        
        mean_cause = sum(cause_data[:n]) / n
        mean_effect = sum(effect_data[:n]) / n
        
        var_cause = sum((x - mean_cause) ** 2 for x in cause_data[:n]) / n
        var_effect = sum((x - mean_effect) ** 2 for x in effect_data[:n]) / n
        
        if n > 1:
            covariance = sum(
                (cause_data[i] - mean_cause) * (effect_data[i] - mean_effect)
                for i in range(n)
            ) / n
            
            if var_cause > 0 and var_effect > 0:
                correlation = covariance / (math.sqrt(var_cause) * math.sqrt(var_effect))
            else:
                correlation = 0
            
            t_stat = correlation * math.sqrt(n - 2) / math.sqrt(1 - correlation ** 2 + 0.0001)
            
            p_value = 2 * (1 - self._t_cdf(abs(t_stat), n - 2))
        else:
            correlation = 0
            p_value = 1.0
        
        return {
            'significant': p_value < self._significance_level,
            'p_value': p_value,
            'statistics': {
                'correlation': correlation,
                'sample_size': n,
                't_statistic': t_stat if n > 1 else 0
            }
        }
    
    def _t_cdf(self, t: float, df: int) -> float:
        """t分布CDF近似"""
        x = t / math.sqrt(df)
        return 0.5 + 0.5 * math.erf(x / math.sqrt(2))
    
    def _compute_verification_confidence(
        self,
        evidence: List[str],
        issues: List[str],
        statistics: Dict[str, float]
    ) -> float:
        """计算验证置信度"""
        base_confidence = 0.5
        
        base_confidence += len(evidence) * 0.1
        base_confidence -= len(issues) * 0.15
        
        if 'avg_edge_strength' in statistics:
            base_confidence += statistics['avg_edge_strength'] * 0.1
        
        if 'min_node_confidence' in statistics:
            base_confidence += statistics['min_node_confidence'] * 0.1
        
        if 'chain_depth' in statistics:
            depth_penalty = max(0, statistics['chain_depth'] - 5) * 0.05
            base_confidence -= depth_penalty
        
        return max(0.0, min(1.0, base_confidence))
    
    def add_confounder(
        self,
        context: str,
        confounder: Confounder
    ):
        """添加已知混淆变量"""
        self.confounders[context].append(confounder)
    
    def sensitivity_analysis(
        self,
        chain: Dict[str, Any],
        parameter: str,
        variation_range: Tuple[float, float] = (0.8, 1.2)
    ) -> Dict[str, Any]:
        """
        敏感性分析
        
        Args:
            chain: 因果链
            parameter: 参数名
            variation_range: 变化范围
            
        Returns:
            敏感性分析结果
        """
        results = []
        
        for factor in [variation_range[0], 1.0, variation_range[1]]:
            modified_chain = self._modify_parameter(chain, parameter, factor)
            result = self.verify_causal_chain(modified_chain)
            results.append({
                'factor': factor,
                'status': result.status.value,
                'confidence': result.confidence
            })
        
        sensitivity = max(
            abs(results[0]['confidence'] - results[1]['confidence']),
            abs(results[2]['confidence'] - results[1]['confidence'])
        )
        
        return {
            'parameter': parameter,
            'results': results,
            'sensitivity': sensitivity,
            'is_sensitive': sensitivity > 0.1
        }
    
    def _modify_parameter(
        self,
        chain: Dict[str, Any],
        parameter: str,
        factor: float
    ) -> Dict[str, Any]:
        """修改参数"""
        import copy
        modified = copy.deepcopy(chain)
        
        if parameter == 'edge_strength':
            for edge in modified.get('edges', []):
                edge['strength'] *= factor
        
        elif parameter == 'node_confidence':
            for node in modified.get('nodes', []):
                node['confidence'] *= factor
        
        return modified
    
    def get_verification_statistics(self) -> Dict[str, Any]:
        """获取验证统计"""
        if not self.verification_history:
            return {'total_verifications': 0}
        
        status_counts = defaultdict(int)
        total_confidence = 0
        
        for record in self.verification_history:
            status_counts[record['status']] += 1
            total_confidence += record['confidence']
        
        return {
            'total_verifications': len(self.verification_history),
            'status_distribution': dict(status_counts),
            'avg_confidence': total_confidence / len(self.verification_history),
            'known_confounders': sum(len(v) for v in self.confounders.values())
        }


def create_verification_engine() -> CausalVerificationEngine:
    """创建验证引擎实例"""
    return CausalVerificationEngine()
