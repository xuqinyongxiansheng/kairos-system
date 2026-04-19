# -*- coding: utf-8 -*-
"""
滑动窗口注意力 (Sliding Window Attention - SWA)
Kairos 3.0 4b核心组件

特点:
- 线性复杂度 O(n*w) 而非 O(n^2)
- 保留局部上下文信息
- 支持因果掩码
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
import time


@dataclass
class AttentionConfig:
    """注意力配置"""
    window_size: int = 512
    num_heads: int = 8
    head_dim: int = 64
    dropout: float = 0.1
    causal: bool = True
    max_seq_len: int = 8192


@dataclass
class AttentionState:
    """注意力状态"""
    key_cache: deque = field(default_factory=lambda: deque(maxlen=8192))
    value_cache: deque = field(default_factory=lambda: deque(maxlen=8192))
    position: int = 0
    last_attention_weights: Optional[List[float]] = None


class SlidingWindowAttention:
    """
    滑动窗口注意力实现
    
    核心思想:
    - 每个token只关注窗口内的其他token
    - 窗口大小w，复杂度从O(n^2)降到O(n*w)
    - 适合长序列处理
    """
    
    def __init__(self, config: AttentionConfig = None):
        self.config = config or AttentionConfig()
        self.state = AttentionState()
        self._attention_scores: List[float] = []
        
    def compute_attention(
        self,
        query: List[float],
        keys: List[List[float]],
        values: List[List[float]],
        mask: Optional[List[bool]] = None
    ) -> Tuple[List[float], List[float]]:
        """
        计算滑动窗口注意力
        
        Args:
            query: 查询向量 [head_dim]
            keys: 键向量列表 [seq_len, head_dim]
            values: 值向量列表 [seq_len, head_dim]
            mask: 可选掩码
            
        Returns:
            output: 注意力输出
            weights: 注意力权重
        """
        if not keys or not values:
            return [], []
        
        head_dim = len(query)
        scale = 1.0 / math.sqrt(head_dim)
        
        scores = []
        for i, key in enumerate(keys):
            if mask and not mask[i]:
                scores.append(float('-inf'))
            else:
                score = sum(q * k for q, k in zip(query, key)) * scale
                scores.append(score)
        
        max_score = max(s for s in scores if s != float('-inf'))
        exp_scores = [math.exp(s - max_score) if s != float('-inf') else 0 for s in scores]
        sum_exp = sum(exp_scores)
        
        if sum_exp == 0:
            weights = [1.0 / len(scores)] * len(scores)
        else:
            weights = [e / sum_exp for e in exp_scores]
        
        output = [0.0] * head_dim
        for i, (w, v) in enumerate(zip(weights, values)):
            for j in range(head_dim):
                output[j] += w * v[j]
        
        return output, weights
    
    def forward(
        self,
        queries: List[List[float]],
        keys: List[List[float]],
        values: List[List[float]],
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        前向传播
        
        Args:
            queries: 查询序列 [seq_len, head_dim]
            keys: 键序列 [seq_len, head_dim]
            values: 值序列 [seq_len, head_dim]
            use_cache: 是否使用KV缓存
            
        Returns:
            包含输出和注意力的字典
        """
        start_time = time.time()
        
        if use_cache:
            for k, v in zip(keys, values):
                self.state.key_cache.append(k)
                self.state.value_cache.append(v)
        
        outputs = []
        all_weights = []
        
        window_size = self.config.window_size
        seq_len = len(queries)
        
        for i, query in enumerate(queries):
            if use_cache:
                cache_len = len(self.state.key_cache)
                start_idx = max(0, cache_len - window_size)
                window_keys = list(self.state.key_cache)[start_idx:]
                window_values = list(self.state.value_cache)[start_idx:]
            else:
                start_idx = max(0, i - window_size + 1)
                window_keys = keys[start_idx:i+1]
                window_values = values[start_idx:i+1]
            
            if self.config.causal:
                mask = [True] * len(window_keys)
            else:
                mask = None
            
            output, weights = self.compute_attention(
                query, window_keys, window_values, mask
            )
            outputs.append(output)
            all_weights.append(weights)
        
        self.state.position += seq_len
        self.state.last_attention_weights = all_weights[-1] if all_weights else None
        
        elapsed = time.time() - start_time
        
        return {
            'outputs': outputs,
            'attention_weights': all_weights,
            'position': self.state.position,
            'cache_size': len(self.state.key_cache),
            'elapsed_ms': elapsed * 1000
        }
    
    def get_window_context(
        self,
        position: int,
        context: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        获取窗口内的上下文
        
        Args:
            position: 当前位置
            context: 完整上下文列表
            
        Returns:
            窗口内的上下文
        """
        window_size = self.config.window_size
        start_idx = max(0, position - window_size + 1)
        return context[start_idx:position + 1]
    
    def reset_cache(self):
        """重置KV缓存"""
        self.state = AttentionState()
    
    def get_attention_pattern(self) -> Dict[str, Any]:
        """
        获取注意力模式分析
        
        Returns:
            注意力模式统计
        """
        if not self.state.last_attention_weights:
            return {'pattern': 'unknown', 'entropy': 0}
        
        weights = self.state.last_attention_weights
        
        entropy = 0
        for w in weights:
            if w > 0:
                entropy -= w * math.log2(w + 1e-10)
        
        max_entropy = math.log2(len(weights)) if weights else 0
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
        
        if normalized_entropy < 0.3:
            pattern = 'focused'
        elif normalized_entropy < 0.7:
            pattern = 'balanced'
        else:
            pattern = 'diffuse'
        
        return {
            'pattern': pattern,
            'entropy': entropy,
            'normalized_entropy': normalized_entropy,
            'max_weight': max(weights) if weights else 0,
            'min_weight': min(weights) if weights else 0
        }
    
    def estimate_memory(self, seq_len: int) -> Dict[str, float]:
        """
        估算内存使用
        
        Args:
            seq_len: 序列长度
            
        Returns:
            内存估算
        """
        head_dim = self.config.head_dim
        num_heads = self.config.num_heads
        window_size = self.config.window_size
        
        full_attention_memory = seq_len * seq_len * num_heads * 4 / (1024 * 1024)
        swa_memory = seq_len * window_size * num_heads * 4 / (1024 * 1024)
        
        return {
            'full_attention_mb': full_attention_memory,
            'swa_memory_mb': swa_memory,
            'savings_percent': (1 - swa_memory / full_attention_memory) * 100 if full_attention_memory > 0 else 0
        }


def create_swa(
    window_size: int = 512,
    num_heads: int = 8,
    head_dim: int = 64,
    causal: bool = True
) -> SlidingWindowAttention:
    """
    创建滑动窗口注意力实例
    
    Args:
        window_size: 窗口大小
        num_heads: 注意力头数
        head_dim: 每个头的维度
        causal: 是否使用因果掩码
        
    Returns:
        SWA实例
    """
    config = AttentionConfig(
        window_size=window_size,
        num_heads=num_heads,
        head_dim=head_dim,
        causal=causal
    )
    return SlidingWindowAttention(config)
