# -*- coding: utf-8 -*-
"""
多尺度注意力融合 (Multi-Scale Attention Fusion)
Kairos 3.0 4b核心组件

特点:
- 融合SWA、DSWA、GLA三种注意力机制
- 自适应选择最优注意力策略
- 多尺度特征提取
- 动态权重分配
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import time

from .swa import SlidingWindowAttention, AttentionConfig
from .dswa import DualSlidingWindowAttention, DualWindowConfig
from .gla import GatedLinearAttention, GLAConfig


class AttentionType(Enum):
    """注意力类型"""
    SWA = "swa"
    DSWA = "dswa"
    GLA = "gla"
    HYBRID = "hybrid"


@dataclass
class MultiScaleConfig:
    """多尺度配置"""
    swa_window: int = 512
    dswa_local_window: int = 256
    dswa_global_window: int = 1024
    gla_state_dim: int = 128
    num_heads: int = 8
    head_dim: int = 64
    adaptive_selection: bool = True
    fusion_strategy: str = "weighted"


@dataclass
class MultiScaleState:
    """多尺度状态"""
    total_tokens: int = 0
    attention_usage: Dict[str, int] = field(default_factory=lambda: {
        'swa': 0, 'dswa': 0, 'gla': 0, 'hybrid': 0
    })
    performance_history: List[Dict[str, float]] = field(default_factory=list)
    current_strategy: AttentionType = AttentionType.HYBRID


class MultiScaleAttention:
    """
    多尺度注意力融合
    
    核心思想:
    - SWA: 适合中等长度序列，局部依赖强
    - DSWA: 适合长序列，需要全局上下文
    - GLA: 适合超长序列，内存受限场景
    - HYBRID: 融合多种注意力，取长补短
    """
    
    def __init__(self, config: MultiScaleConfig = None):
        self.config = config or MultiScaleConfig()
        self.state = MultiScaleState()
        
        self.swa = SlidingWindowAttention(AttentionConfig(
            window_size=self.config.swa_window,
            num_heads=self.config.num_heads,
            head_dim=self.config.head_dim
        ))
        
        self.dswa = DualSlidingWindowAttention(DualWindowConfig(
            local_window=self.config.dswa_local_window,
            global_window=self.config.dswa_global_window,
            num_heads=self.config.num_heads,
            head_dim=self.config.head_dim
        ))
        
        self.gla = GatedLinearAttention(GLAConfig(
            state_dim=self.config.gla_state_dim,
            num_heads=self.config.num_heads
        ))
        
        self._strategy_scores = {
            AttentionType.SWA: 0.0,
            AttentionType.DSWA: 0.0,
            AttentionType.GLA: 0.0
        }
    
    def analyze_sequence_characteristics(
        self,
        sequence: List[List[float]]
    ) -> Dict[str, float]:
        """
        分析序列特征
        
        Args:
            sequence: 输入序列
            
        Returns:
            特征字典
        """
        seq_len = len(sequence)
        if seq_len == 0:
            return {'length': 0, 'complexity': 0, 'variance': 0}
        
        dim = len(sequence[0]) if sequence else 0
        
        total_variance = 0.0
        for d in range(dim):
            values = [s[d] for s in sequence]
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            total_variance += variance
        
        avg_variance = total_variance / dim if dim > 0 else 0
        
        local_coherence = 0.0
        for i in range(1, min(100, seq_len)):
            diff = sum(
                (sequence[i][d] - sequence[i-1][d]) ** 2 
                for d in range(dim)
            )
            local_coherence += math.sqrt(diff)
        local_coherence = local_coherence / min(99, seq_len - 1) if seq_len > 1 else 0
        
        return {
            'length': seq_len,
            'complexity': min(1.0, avg_variance * 10),
            'variance': avg_variance,
            'local_coherence': local_coherence,
            'dimension': dim
        }
    
    def select_optimal_strategy(
        self,
        characteristics: Dict[str, float]
    ) -> AttentionType:
        """
        选择最优注意力策略
        
        Args:
            characteristics: 序列特征
            
        Returns:
            最优策略
        """
        if not self.config.adaptive_selection:
            return AttentionType.HYBRID
        
        seq_len = characteristics['length']
        complexity = characteristics['complexity']
        local_coherence = characteristics['local_coherence']
        
        scores = {
            AttentionType.SWA: 0.0,
            AttentionType.DSWA: 0.0,
            AttentionType.GLA: 0.0
        }
        
        if seq_len < 512:
            scores[AttentionType.SWA] += 2.0
        elif seq_len < 2048:
            scores[AttentionType.DSWA] += 2.0
        else:
            scores[AttentionType.GLA] += 2.0
        
        if complexity > 0.7:
            scores[AttentionType.DSWA] += 1.5
        elif complexity < 0.3:
            scores[AttentionType.SWA] += 1.0
        
        if local_coherence < 0.5:
            scores[AttentionType.SWA] += 1.0
        else:
            scores[AttentionType.DSWA] += 0.5
            scores[AttentionType.GLA] += 0.5
        
        for strategy, score in scores.items():
            self._strategy_scores[strategy] = (
                0.7 * self._strategy_scores[strategy] + 0.3 * score
            )
        
        best_strategy = max(scores, key=scores.get)
        return best_strategy
    
    def compute_fusion_weights(
        self,
        strategy: AttentionType,
        characteristics: Dict[str, float]
    ) -> Dict[str, float]:
        """
        计算融合权重
        
        Args:
            strategy: 当前策略
            characteristics: 序列特征
            
        Returns:
            各注意力机制的权重
        """
        if strategy == AttentionType.HYBRID:
            complexity = characteristics['complexity']
            
            if complexity < 0.3:
                return {
                    'swa': 0.6,
                    'dswa': 0.3,
                    'gla': 0.1
                }
            elif complexity < 0.7:
                return {
                    'swa': 0.3,
                    'dswa': 0.5,
                    'gla': 0.2
                }
            else:
                return {
                    'swa': 0.2,
                    'dswa': 0.3,
                    'gla': 0.5
                }
        else:
            weights = {'swa': 0.0, 'dswa': 0.0, 'gla': 0.0}
            weights[strategy.value] = 1.0
            return weights
    
    def forward(
        self,
        queries: List[List[float]],
        keys: List[List[float]],
        values: List[List[float]],
        strategy: Optional[AttentionType] = None
    ) -> Dict[str, Any]:
        """
        多尺度前向传播
        
        Args:
            queries: 查询序列
            keys: 键序列
            values: 值序列
            strategy: 可选的指定策略
            
        Returns:
            输出字典
        """
        start_time = time.time()
        
        characteristics = self.analyze_sequence_characteristics(keys)
        
        if strategy is None:
            strategy = self.select_optimal_strategy(characteristics)
        
        weights = self.compute_fusion_weights(strategy, characteristics)
        
        self.state.current_strategy = strategy
        self.state.attention_usage[strategy.value] += 1
        self.state.total_tokens += len(queries)
        
        if strategy == AttentionType.SWA:
            result = self.swa.forward(queries, keys, values)
            outputs = result['outputs']
        elif strategy == AttentionType.DSWA:
            result = self.dswa.forward(queries, keys, values)
            outputs = result['outputs']
        elif strategy == AttentionType.GLA:
            result = self.gla.forward(queries, keys, values)
            outputs = result['outputs']
        else:
            swa_result = self.swa.forward(queries, keys, values)
            dswa_result = self.dswa.forward(queries, keys, values)
            gla_result = self.gla.forward(queries, keys, values)
            
            outputs = []
            for i in range(len(queries)):
                fused = []
                for d in range(len(queries[0])):
                    val = (
                        weights['swa'] * swa_result['outputs'][i][d] +
                        weights['dswa'] * dswa_result['outputs'][i][d] +
                        weights['gla'] * gla_result['outputs'][i][d]
                    )
                    fused.append(val)
                outputs.append(fused)
            
            result = {
                'swa_result': swa_result,
                'dswa_result': dswa_result,
                'gla_result': gla_result
            }
        
        elapsed = time.time() - start_time
        
        performance = {
            'elapsed_ms': elapsed * 1000,
            'strategy': strategy.value,
            'seq_len': len(queries)
        }
        self.state.performance_history.append(performance)
        
        return {
            'outputs': outputs,
            'strategy': strategy.value,
            'fusion_weights': weights,
            'characteristics': characteristics,
            'elapsed_ms': elapsed * 1000,
            'total_tokens': self.state.total_tokens
        }
    
    def get_attention_statistics(self) -> Dict[str, Any]:
        """
        获取注意力统计信息
        
        Returns:
            统计信息
        """
        total_usage = sum(self.state.attention_usage.values())
        usage_percent = {
            k: (v / total_usage * 100) if total_usage > 0 else 0
            for k, v in self.state.attention_usage.items()
        }
        
        recent_perf = self.state.performance_history[-100:]
        avg_elapsed = (
            sum(p['elapsed_ms'] for p in recent_perf) / len(recent_perf)
            if recent_perf else 0
        )
        
        return {
            'total_tokens_processed': self.state.total_tokens,
            'attention_usage': self.state.attention_usage,
            'usage_percent': usage_percent,
            'current_strategy': self.state.current_strategy.value,
            'avg_elapsed_ms': avg_elapsed,
            'strategy_scores': {k.value: v for k, v in self._strategy_scores.items()}
        }
    
    def get_multi_scale_context(
        self,
        position: int,
        context: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取多尺度上下文
        
        Args:
            position: 当前位置
            context: 完整上下文
            
        Returns:
            多尺度上下文
        """
        swa_start = max(0, position - self.config.swa_window + 1)
        dswa_local_start = max(0, position - self.config.dswa_local_window + 1)
        dswa_global_start = max(0, position - self.config.dswa_global_window + 1)
        
        return {
            'swa_context': context[swa_start:position + 1],
            'dswa_local_context': context[dswa_local_start:position + 1],
            'dswa_global_context': context[dswa_global_start:position + 1],
            'gla_full_context': context[:position + 1]
        }
    
    def reset(self):
        """重置所有状态"""
        self.state = MultiScaleState()
        self.swa.reset_cache()
        self.dswa.reset()
        self.gla.reset()
        self._strategy_scores = {
            AttentionType.SWA: 0.0,
            AttentionType.DSWA: 0.0,
            AttentionType.GLA: 0.0
        }
    
    def optimize_for_sequence(
        self,
        expected_length: int,
        memory_budget_mb: float = 100.0
    ) -> Dict[str, Any]:
        """
        为特定序列长度优化配置
        
        Args:
            expected_length: 预期序列长度
            memory_budget_mb: 内存预算(MB)
            
        Returns:
            优化建议
        """
        recommendations = []
        
        if expected_length < 512:
            recommendations.append({
                'strategy': 'SWA',
                'reason': '短序列，SWA效率最高',
                'expected_speedup': '1.5x'
            })
        elif expected_length < 2048:
            recommendations.append({
                'strategy': 'DSWA',
                'reason': '中等长度，双窗口平衡',
                'expected_speedup': '2x'
            })
        else:
            recommendations.append({
                'strategy': 'GLA',
                'reason': '长序列，线性复杂度',
                'expected_speedup': '5x+'
            })
        
        swa_mem = self.swa.estimate_memory(expected_length)
        dswa_eff = self.dswa.estimate_efficiency(expected_length)
        gla_mem = self.gla.get_memory_efficiency(expected_length)
        
        return {
            'expected_length': expected_length,
            'memory_budget_mb': memory_budget_mb,
            'recommendations': recommendations,
            'memory_analysis': {
                'swa': swa_mem,
                'dswa': dswa_eff,
                'gla': gla_mem
            }
        }


def create_multi_scale_attention(
    swa_window: int = 512,
    dswa_local: int = 256,
    dswa_global: int = 1024,
    gla_state_dim: int = 128,
    adaptive: bool = True
) -> MultiScaleAttention:
    """
    创建多尺度注意力实例
    
    Args:
        swa_window: SWA窗口大小
        dswa_local: DSWA局部窗口
        dswa_global: DSWA全局窗口
        gla_state_dim: GLA状态维度
        adaptive: 是否启用自适应选择
        
    Returns:
        多尺度注意力实例
    """
    config = MultiScaleConfig(
        swa_window=swa_window,
        dswa_local_window=dswa_local,
        dswa_global_window=dswa_global,
        gla_state_dim=gla_state_dim,
        adaptive_selection=adaptive
    )
    return MultiScaleAttention(config)
