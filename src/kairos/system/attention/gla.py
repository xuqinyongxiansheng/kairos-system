# -*- coding: utf-8 -*-
"""
门控线性注意力 (Gated Linear Attention - GLA)
Kairos 3.0 4b核心组件

特点:
- 线性复杂度 O(n)
- 门控机制控制信息流
- 支持无限长度序列
- 高效的递归状态更新
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
import time


@dataclass
class GLAConfig:
    """GLA配置"""
    hidden_dim: int = 512
    state_dim: int = 128
    num_heads: int = 8
    gate_init: float = 0.5
    decay_range: Tuple[float, float] = (0.9, 0.999)
    use_bias: bool = True


@dataclass
class GLAState:
    """GLA状态"""
    kv_state: List[List[float]] = field(default_factory=list)
    position: int = 0
    gates_history: List[float] = field(default_factory=list)
    decay_values: List[float] = field(default_factory=list)


class GatedLinearAttention:
    """
    门控线性注意力实现
    
    核心公式:
    - 状态更新: S_t = γ_t * S_{t-1} + k_t ⊗ v_t
    - 输出: o_t = q_t * S_t
    - 门控: γ_t = sigmoid(g_t) * (γ_max - γ_min) + γ_min
    
    其中:
    - γ_t 是遗忘门，控制历史信息保留程度
    - k_t, v_t, q_t 是键、值、查询向量
    - S_t 是递归状态
    """
    
    def __init__(self, config: GLAConfig = None):
        self.config = config or GLAConfig()
        self.state = GLAState()
        
        self.state.kv_state = [
            [0.0] * self.config.state_dim 
            for _ in range(self.config.num_heads)
        ]
        
        self._gate_weights = self._init_gate_weights()
    
    def _init_gate_weights(self) -> List[float]:
        """初始化门控权重"""
        return [self.config.gate_init] * self.config.num_heads
    
    def compute_gate(
        self,
        gate_input: List[float],
        head_idx: int
    ) -> float:
        """
        计算门控值
        
        Args:
            gate_input: 门控输入
            head_idx: 头索引
            
        Returns:
            门控值 (decay factor)
        """
        gate_sum = sum(gate_input) / len(gate_input)
        
        gate_value = 1.0 / (1.0 + math.exp(-gate_sum))
        
        gamma_min, gamma_max = self.config.decay_range
        gamma = gate_value * (gamma_max - gamma_min) + gamma_min
        
        self.state.gates_history.append(gamma)
        
        return gamma
    
    def update_state(
        self,
        key: List[float],
        value: List[float],
        gate: float,
        head_idx: int
    ):
        """
        更新递归状态
        
        Args:
            key: 键向量
            value: 值向量
            gate: 门控值
            head_idx: 头索引
        """
        state = self.state.kv_state[head_idx]
        
        for i in range(min(len(state), len(key), len(value))):
            state[i] = gate * state[i] + key[i] * value[i]
        
        self.state.decay_values.append(gate)
    
    def compute_output(
        self,
        query: List[float],
        head_idx: int
    ) -> List[float]:
        """
        计算输出
        
        Args:
            query: 查询向量
            head_idx: 头索引
            
        Returns:
            输出向量
        """
        state = self.state.kv_state[head_idx]
        output_dim = len(query)
        output = [0.0] * output_dim
        
        for i in range(min(len(state), output_dim)):
            output[i] = query[i] * state[i]
        
        return output
    
    def forward(
        self,
        queries: List[List[float]],
        keys: List[List[float]],
        values: List[List[float]],
        gates: Optional[List[List[float]]] = None
    ) -> Dict[str, Any]:
        """
        前向传播
        
        Args:
            queries: 查询序列 [seq_len, head_dim]
            keys: 键序列 [seq_len, head_dim]
            values: 值序列 [seq_len, head_dim]
            gates: 可选的门控输入 [seq_len, gate_dim]
            
        Returns:
            包含输出的字典
        """
        start_time = time.time()
        
        seq_len = len(queries)
        num_heads = self.config.num_heads
        head_dim = len(queries[0]) // num_heads if queries else 0
        
        outputs = []
        
        for t in range(seq_len):
            query = queries[t]
            key = keys[t]
            value = values[t]
            
            gate_input = gates[t] if gates else key
            gate = self.compute_gate(gate_input, 0)
            
            head_outputs = []
            for h in range(num_heads):
                start_idx = h * head_dim
                end_idx = start_idx + head_dim
                
                q_head = query[start_idx:end_idx]
                k_head = key[start_idx:end_idx]
                v_head = value[start_idx:end_idx]
                
                self.update_state(k_head, v_head, gate, h)
                
                head_out = self.compute_output(q_head, h)
                head_outputs.append(head_out)
            
            fused_output = []
            for d in range(head_dim):
                val = sum(ho[d] if d < len(ho) else 0 for ho in head_outputs)
                fused_output.append(val / num_heads)
            
            outputs.append(fused_output)
        
        self.state.position += seq_len
        
        elapsed = time.time() - start_time
        
        return {
            'outputs': outputs,
            'position': self.state.position,
            'state_norm': self._compute_state_norm(),
            'avg_gate': sum(self.state.gates_history[-seq_len:]) / seq_len if seq_len > 0 else 0,
            'elapsed_ms': elapsed * 1000
        }
    
    def _compute_state_norm(self) -> float:
        """计算状态范数"""
        total_norm = 0.0
        for state in self.state.kv_state:
            norm = sum(s * s for s in state)
            total_norm += math.sqrt(norm)
        return total_norm / len(self.state.kv_state) if self.state.kv_state else 0
    
    def get_memory_efficiency(self, seq_len: int) -> Dict[str, Any]:
        """
        获取内存效率分析
        
        Args:
            seq_len: 序列长度
            
        Returns:
            内存效率统计
        """
        state_memory = (
            self.config.num_heads * 
            self.config.state_dim * 
            4 / (1024 * 1024)
        )
        
        full_attention_memory = seq_len * seq_len * 4 / (1024 * 1024)
        
        return {
            'state_memory_mb': state_memory,
            'full_attention_mb': full_attention_memory,
            'memory_reduction': (1 - state_memory / full_attention_memory) * 100 
                if full_attention_memory > 0 else 0,
            'constant_memory': True,
            'supports_infinite_length': True
        }
    
    def get_gate_statistics(self) -> Dict[str, Any]:
        """
        获取门控统计信息
        
        Returns:
            门控统计
        """
        if not self.state.gates_history:
            return {'status': 'no_data'}
        
        recent_gates = self.state.gates_history[-1000:]
        
        return {
            'avg_gate': sum(recent_gates) / len(recent_gates),
            'min_gate': min(recent_gates),
            'max_gate': max(recent_gates),
            'gate_variance': sum((g - sum(recent_gates)/len(recent_gates))**2 for g in recent_gates) / len(recent_gates),
            'total_updates': len(self.state.gates_history)
        }
    
    def reset(self):
        """重置状态"""
        self.state = GLAState()
        self.state.kv_state = [
            [0.0] * self.config.state_dim 
            for _ in range(self.config.num_heads)
        ]
    
    def compress_state(self, ratio: float = 0.5) -> Dict[str, Any]:
        """
        压缩状态以节省内存
        
        Args:
            ratio: 压缩比例
            
        Returns:
            压缩结果
        """
        original_size = sum(len(s) for s in self.state.kv_state)
        
        for h in range(len(self.state.kv_state)):
            state = self.state.kv_state[h]
            new_size = int(len(state) * ratio)
            
            if new_size < len(state):
                compressed = []
                step = len(state) / new_size
                for i in range(new_size):
                    idx = int(i * step)
                    compressed.append(state[idx])
                self.state.kv_state[h] = compressed
        
        new_size = sum(len(s) for s in self.state.kv_state)
        
        return {
            'original_size': original_size,
            'compressed_size': new_size,
            'compression_ratio': new_size / original_size if original_size > 0 else 0
        }


def create_gla(
    hidden_dim: int = 512,
    state_dim: int = 128,
    num_heads: int = 8
) -> GatedLinearAttention:
    """
    创建门控线性注意力实例
    
    Args:
        hidden_dim: 隐藏维度
        state_dim: 状态维度
        num_heads: 头数
        
    Returns:
        GLA实例
    """
    config = GLAConfig(
        hidden_dim=hidden_dim,
        state_dim=state_dim,
        num_heads=num_heads
    )
    return GatedLinearAttention(config)
