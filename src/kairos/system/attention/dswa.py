# -*- coding: utf-8 -*-
"""
双滑动窗口注意力 (Dual Sliding Window Attention - DSWA)
Kairos 3.0 4b核心组件

特点:
- 双窗口机制：局部窗口 + 全局窗口
- 局部窗口捕获精细特征
- 全局窗口捕获长距离依赖
- 动态窗口大小调整
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
import time

from .swa import SlidingWindowAttention, AttentionConfig


@dataclass
class DualWindowConfig:
    """双窗口配置"""
    local_window: int = 256
    global_window: int = 1024
    local_weight: float = 0.6
    global_weight: float = 0.4
    num_heads: int = 8
    head_dim: int = 64
    dynamic_adjustment: bool = True


@dataclass
class DualWindowState:
    """双窗口状态"""
    local_cache: deque = field(default_factory=lambda: deque(maxlen=2048))
    global_cache: deque = field(default_factory=lambda: deque(maxlen=8192))
    position: int = 0
    window_adjustments: List[int] = field(default_factory=list)


class DualSlidingWindowAttention:
    """
    双滑动窗口注意力实现
    
    核心思想:
    - 局部窗口：小窗口，高权重，捕获局部模式
    - 全局窗口：大窗口，低权重，捕获全局上下文
    - 动态调整：根据内容复杂度调整窗口大小
    """
    
    def __init__(self, config: DualWindowConfig = None):
        self.config = config or DualWindowConfig()
        self.state = DualWindowState()
        
        self.local_attention = SlidingWindowAttention(AttentionConfig(
            window_size=config.local_window if config else 256,
            num_heads=config.num_heads if config else 8,
            head_dim=config.head_dim if config else 64,
            causal=True
        ))
        
        self.global_attention = SlidingWindowAttention(AttentionConfig(
            window_size=config.global_window if config else 1024,
            num_heads=config.num_heads if config else 8,
            head_dim=config.head_dim if config else 64,
            causal=True
        ))
    
    def compute_content_complexity(self, vectors: List[List[float]]) -> float:
        """
        计算内容复杂度
        
        Args:
            vectors: 向量序列
            
        Returns:
            复杂度分数 (0-1)
        """
        if len(vectors) < 2:
            return 0.0
        
        total_variance = 0.0
        dim = len(vectors[0])
        
        for d in range(dim):
            values = [v[d] for v in vectors]
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            total_variance += variance
        
        avg_variance = total_variance / dim if dim > 0 else 0
        
        complexity = min(1.0, avg_variance * 10)
        
        return complexity
    
    def adjust_window_weights(self, complexity: float) -> Tuple[float, float]:
        """
        根据复杂度调整窗口权重
        
        Args:
            complexity: 内容复杂度
            
        Returns:
            (局部权重, 全局权重)
        """
        if not self.config.dynamic_adjustment:
            return self.config.local_weight, self.config.global_weight
        
        if complexity < 0.3:
            local_weight = 0.8
            global_weight = 0.2
        elif complexity < 0.7:
            local_weight = 0.6
            global_weight = 0.4
        else:
            local_weight = 0.4
            global_weight = 0.6
        
        return local_weight, global_weight
    
    def forward(
        self,
        queries: List[List[float]],
        keys: List[List[float]],
        values: List[List[float]]
    ) -> Dict[str, Any]:
        """
        双窗口前向传播
        
        Args:
            queries: 查询序列
            keys: 键序列
            values: 值序列
            
        Returns:
            包含融合输出的字典
        """
        start_time = time.time()
        
        complexity = self.compute_content_complexity(keys)
        local_weight, global_weight = self.adjust_window_weights(complexity)
        
        local_result = self.local_attention.forward(
            queries, keys, values, use_cache=True
        )
        
        global_result = self.global_attention.forward(
            queries, keys, values, use_cache=True
        )
        
        local_outputs = local_result['outputs']
        global_outputs = global_result['outputs']
        
        fused_outputs = []
        for local_out, global_out in zip(local_outputs, global_outputs):
            fused = [
                local_weight * l + global_weight * g
                for l, g in zip(local_out, global_out)
            ]
            fused_outputs.append(fused)
        
        self.state.position += len(queries)
        self.state.window_adjustments.append(int(complexity * 100))
        
        elapsed = time.time() - start_time
        
        return {
            'outputs': fused_outputs,
            'local_outputs': local_outputs,
            'global_outputs': global_outputs,
            'local_attention': local_result['attention_weights'],
            'global_attention': global_result['attention_weights'],
            'local_weight': local_weight,
            'global_weight': global_weight,
            'complexity': complexity,
            'position': self.state.position,
            'elapsed_ms': elapsed * 1000
        }
    
    def get_dual_attention_pattern(self) -> Dict[str, Any]:
        """
        获取双窗口注意力模式分析
        
        Returns:
            模式分析结果
        """
        local_pattern = self.local_attention.get_attention_pattern()
        global_pattern = self.global_attention.get_attention_pattern()
        
        return {
            'local': local_pattern,
            'global': global_pattern,
            'adjustments_count': len(self.state.window_adjustments),
            'avg_complexity': sum(self.state.window_adjustments[-100:]) / 100 
                if self.state.window_adjustments else 0
        }
    
    def get_context_windows(
        self,
        position: int,
        context: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取局部和全局上下文窗口
        
        Args:
            position: 当前位置
            context: 完整上下文
            
        Returns:
            包含局部和全局窗口的字典
        """
        local_start = max(0, position - self.config.local_window + 1)
        global_start = max(0, position - self.config.global_window + 1)
        
        return {
            'local_context': context[local_start:position + 1],
            'global_context': context[global_start:position + 1],
            'local_window_size': position - local_start + 1,
            'global_window_size': position - global_start + 1
        }
    
    def reset(self):
        """重置所有状态"""
        self.state = DualWindowState()
        self.local_attention.reset_cache()
        self.global_attention.reset_cache()
    
    def estimate_efficiency(self, seq_len: int) -> Dict[str, Any]:
        """
        估算效率提升
        
        Args:
            seq_len: 序列长度
            
        Returns:
            效率统计
        """
        local_mem = self.local_attention.estimate_memory(seq_len)
        global_mem = self.global_attention.estimate_memory(seq_len)
        
        full_attention_ops = seq_len * seq_len
        dswa_ops = seq_len * (self.config.local_window + self.config.global_window)
        
        return {
            'local_memory': local_mem,
            'global_memory': global_mem,
            'total_swa_memory_mb': local_mem['swa_memory_mb'] + global_mem['swa_memory_mb'],
            'full_attention_memory_mb': local_mem['full_attention_mb'],
            'operations_reduction': (1 - dswa_ops / full_attention_ops) * 100 
                if full_attention_ops > 0 else 0,
            'local_window': self.config.local_window,
            'global_window': self.config.global_window
        }


def create_dswa(
    local_window: int = 256,
    global_window: int = 1024,
    local_weight: float = 0.6,
    global_weight: float = 0.4,
    dynamic: bool = True
) -> DualSlidingWindowAttention:
    """
    创建双滑动窗口注意力实例
    
    Args:
        local_window: 局部窗口大小
        global_window: 全局窗口大小
        local_weight: 局部权重
        global_weight: 全局权重
        dynamic: 是否启用动态调整
        
    Returns:
        DSWA实例
    """
    config = DualWindowConfig(
        local_window=local_window,
        global_window=global_window,
        local_weight=local_weight,
        global_weight=global_weight,
        dynamic_adjustment=dynamic
    )
    return DualSlidingWindowAttention(config)
