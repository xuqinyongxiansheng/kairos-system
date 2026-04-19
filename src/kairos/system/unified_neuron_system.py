#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一神经元系统架构
参照人类神经学中的强化神经元系统原理设计
实现神经元网络、强化学习、认知控制功能

核心功能：
1. 神经元节点管理（创建、连接、激活）
2. 强化学习机制（权重调整、路径强化）
3. 认知控制（注意力机制、决策支持）
4. 神经可塑性（结构适应、功能重组）
5. 统一API接口（兼容所有现有模块）
"""

import json
import time
import os
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import math

logger = logging.getLogger("UnifiedNeuronSystem")


class NeuronType(Enum):
    """神经元类型枚举"""
    SENSORY = "sensory"           # 感觉神经元（输入处理）
    INTERNEURON = "interneuron"   # 中间神经元（信息处理）
    MOTOR = "motor"               # 运动神经元（输出执行）
    MODULATORY = "modulatory"     # 调制神经元（调节控制）
    MEMORY = "memory"             # 记忆神经元（信息存储）
    DECISION = "decision"         # 决策神经元（决策制定）


class SynapseType(Enum):
    """突触类型枚举"""
    EXCITATORY = "excitatory"     # 兴奋性突触
    INHIBITORY = "inhibitory"     # 抑制性突触
    MODULATORY = "modulatory"     # 调制性突触


class PlasticityType(Enum):
    """可塑性类型"""
    LTP = "long_term_potentiation"    # 长时程增强
    LTD = "long_term_depression"      # 长时程抑制
    STDP = "spike_timing_dependent"   # 脉冲时间依赖


@dataclass
class Neuron:
    """
    神经元节点
    模拟生物神经元的基本特性
    """
    id: str
    neuron_type: str
    name: str
    threshold: float = 0.5             # 激活阈值
    resting_potential: float = 0.0     # 静息电位
    current_potential: float = 0.0     # 当前电位
    refractory_period: float = 0.01    # 不应期（秒）
    last_spike_time: float = 0.0       # 最后发放时间
    spike_count: int = 0               # 发放次数
    connections_in: List[str] = field(default_factory=list)   # 输入连接
    connections_out: List[str] = field(default_factory=list)  # 输出连接
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def receive_input(self, strength: float) -> float:
        """接收输入信号"""
        self.current_potential += strength
        return self.current_potential
    
    def activate(self, current_time: float) -> bool:
        """
        检查是否激活（发放脉冲）
        
        Args:
            current_time: 当前时间戳
        
        Returns:
            是否激活
        """
        # 检查不应期
        if current_time - self.last_spike_time < self.refractory_period:
            return False
        
        # 检查是否达到阈值
        if self.current_potential >= self.threshold:
            self.last_spike_time = current_time
            self.spike_count += 1
            self.current_potential = self.resting_potential  # 重置电位
            return True
        
        return False
    
    def reset(self):
        """重置神经元状态"""
        self.current_potential = self.resting_potential


@dataclass
class Synapse:
    """
    突触连接
    模拟神经元之间的连接和信息传递
    """
    id: str
    source_id: str                    # 源神经元ID
    target_id: str                    # 目标神经元ID
    weight: float = 1.0               # 突触权重
    synapse_type: str = "excitatory"  # 突触类型
    delay: float = 0.001              # 传递延迟（秒）
    plasticity: str = "LTP"           # 可塑性类型
    last_activated: float = 0.0       # 最后激活时间
    activation_count: int = 0         # 激活次数
    strength_history: List[float] = field(default_factory=list)  # 权重历史
    
    def __post_init__(self):
        if not self.strength_history:
            self.strength_history = [self.weight]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def transmit(self, signal: float, current_time: float) -> float:
        """
        传递信号
        
        Args:
            signal: 输入信号强度
            current_time: 当前时间
        
        Returns:
            输出信号强度
        """
        self.last_activated = current_time
        self.activation_count += 1
        
        if self.synapse_type == SynapseType.EXCITATORY.value:
            return signal * self.weight
        elif self.synapse_type == SynapseType.INHIBITORY.value:
            return -signal * self.weight
        else:
            return signal * self.weight * 0.5  # 调制性
    
    def strengthen(self, factor: float = 1.1, max_weight: float = 10.0):
        """强化突触（LTP）"""
        old_weight = self.weight
        self.weight = min(self.weight * factor, max_weight)
        self.strength_history.append(self.weight)
        logger.debug(f"突触 {self.id} 强化: {old_weight:.3f} -> {self.weight:.3f}")
    
    def weaken(self, factor: float = 0.9, min_weight: float = 0.1):
        """弱化突触（LTD）"""
        old_weight = self.weight
        self.weight = max(self.weight * factor, min_weight)
        self.strength_history.append(self.weight)
        logger.debug(f"突触 {self.id} 弱化: {old_weight:.3f} -> {self.weight:.3f}")
    
    def apply_stdp(self, pre_spike_time: float, post_spike_time: float, 
                   learning_rate: float = 0.1):
        """
        应用STDP（脉冲时间依赖可塑性）
        
        如果突触前脉冲先于突触后脉冲，增强连接
        如果突触后脉冲先于突触前脉冲，减弱连接
        """
        time_diff = post_spike_time - pre_spike_time
        
        if time_diff > 0:  # 前脉冲先于后脉冲
            # 指数衰减增强
            delta = learning_rate * math.exp(-time_diff / 0.02)
            self.strengthen(1 + delta)
        else:  # 后脉冲先于前脉冲
            # 指数衰减减弱
            delta = learning_rate * math.exp(time_diff / 0.02)
            self.weaken(1 - delta)


class NeuralCircuit:
    """
    神经回路
    一组协同工作的神经元集合
    """
    
    def __init__(self, circuit_id: str, name: str, circuit_type: str = "default"):
        self.circuit_id = circuit_id
        self.name = name
        self.circuit_type = circuit_type
        self.neurons: Dict[str, Neuron] = {}
        self.synapses: Dict[str, Synapse] = {}
        self.activation_history: List[Dict[str, Any]] = []
        self.created_at = datetime.now().isoformat()
    
    def add_neuron(self, neuron: Neuron):
        """添加神经元"""
        self.neurons[neuron.id] = neuron
    
    def add_synapse(self, synapse: Synapse):
        """添加突触"""
        self.synapses[synapse.id] = synapse
        
        # 更新神经元的连接列表
        if synapse.source_id in self.neurons:
            if synapse.id not in self.neurons[synapse.source_id].connections_out:
                self.neurons[synapse.source_id].connections_out.append(synapse.id)
        
        if synapse.target_id in self.neurons:
            if synapse.id not in self.neurons[synapse.target_id].connections_in:
                self.neurons[synapse.target_id].connections_in.append(synapse.id)
    
    def activate(self, inputs: Dict[str, float], current_time: float) -> Dict[str, bool]:
        """
        激活神经回路
        
        Args:
            inputs: 输入神经元ID到信号强度的映射
            current_time: 当前时间
        
        Returns:
            神经元激活状态
        """
        activation_states = {}
        
        # 重置所有神经元
        for neuron in self.neurons.values():
            neuron.reset()
        
        # 应用输入
        for neuron_id, signal in inputs.items():
            if neuron_id in self.neurons:
                self.neurons[neuron_id].receive_input(signal)
        
        # 传播激活
        max_iterations = 10
        for _ in range(max_iterations):
            new_activations = {}
            
            for neuron in self.neurons.values():
                # 收集输入
                total_input = 0.0
                for synapse_id in neuron.connections_in:
                    if synapse_id in self.synapses:
                        synapse = self.synapses[synapse_id]
                        if synapse.source_id in self.neurons:
                            source = self.neurons[synapse.source_id]
                            if source.current_potential > 0:
                                total_input += synapse.transmit(
                                    source.current_potential, current_time
                                )
                
                neuron.receive_input(total_input)
                new_activations[neuron.id] = neuron.activate(current_time)
            
            activation_states.update(new_activations)
            
            # 检查是否稳定
            if not any(new_activations.values()):
                break
        
        # 记录激活历史
        self.activation_history.append({
            "timestamp": current_time,
            "inputs": inputs,
            "activations": activation_states
        })
        
        return activation_states
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取回路统计信息"""
        return {
            "circuit_id": self.circuit_id,
            "name": self.name,
            "type": self.circuit_type,
            "neuron_count": len(self.neurons),
            "synapse_count": len(self.synapses),
            "total_spikes": sum(n.spike_count for n in self.neurons.values()),
            "activation_count": len(self.activation_history)
        }


class UnifiedNeuronSystem:
    """
    统一神经元系统
    整合神经元网络、强化学习、认知控制功能
    """
    
    def __init__(self, config: Dict = None):
        """初始化统一神经元系统"""
        self.config = config or {}
        
        # 神经元和突触存储
        self.neurons: Dict[str, Neuron] = {}
        self.synapses: Dict[str, Synapse] = {}
        self.circuits: Dict[str, NeuralCircuit] = {}
        
        # 索引
        self.neuron_type_index: Dict[str, List[str]] = defaultdict(list)
        self.connection_graph: Dict[str, List[str]] = defaultdict(list)
        
        # 学习参数
        self.learning_rate = self.config.get("learning_rate", 0.1)
        self.decay_rate = self.config.get("decay_rate", 0.01)
        self.max_weight = self.config.get("max_weight", 10.0)
        self.min_weight = self.config.get("min_weight", 0.1)
        
        # 统计信息
        self.stats = {
            "total_neurons": 0,
            "total_synapses": 0,
            "total_circuits": 0,
            "total_activations": 0,
            "total_reinforcements": 0
        }
        
        # 数据持久化
        self.data_path = self.config.get("data_path", "./data/neuron_system")
        os.makedirs(self.data_path, exist_ok=True)
        
        self._load_data()
        logger.info("统一神经元系统初始化完成")
    
    def _generate_id(self, prefix: str = "neuron") -> str:
        """生成唯一ID"""
        timestamp = datetime.now().timestamp()
        return f"{prefix}_{int(timestamp * 1000)}_{hashlib.md5(str(timestamp).encode()).hexdigest()[:8]}"
    
    def _load_data(self):
        """加载持久化数据"""
        neurons_file = os.path.join(self.data_path, "neurons.json")
        synapses_file = os.path.join(self.data_path, "synapses.json")
        
        if os.path.exists(neurons_file):
            try:
                with open(neurons_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for nid, ndata in data.items():
                        self.neurons[nid] = Neuron(**ndata)
                        self.neuron_type_index[ndata["neuron_type"]].append(nid)
                logger.info(f"加载 {len(self.neurons)} 个神经元")
            except Exception as e:
                logger.error(f"加载神经元数据失败: {e}")
        
        if os.path.exists(synapses_file):
            try:
                with open(synapses_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for sid, sdata in data.items():
                        self.synapses[sid] = Synapse(**sdata)
                        self.connection_graph[sdata["source_id"]].append(sdata["target_id"])
                logger.info(f"加载 {len(self.synapses)} 个突触")
            except Exception as e:
                logger.error(f"加载突触数据失败: {e}")
        
        self.stats["total_neurons"] = len(self.neurons)
        self.stats["total_synapses"] = len(self.synapses)
    
    def _save_data(self):
        """保存持久化数据"""
        neurons_file = os.path.join(self.data_path, "neurons.json")
        synapses_file = os.path.join(self.data_path, "synapses.json")
        
        try:
            with open(neurons_file, 'w', encoding='utf-8') as f:
                json.dump({nid: n.to_dict() for nid, n in self.neurons.items()}, 
                         f, ensure_ascii=False, indent=2)
            
            with open(synapses_file, 'w', encoding='utf-8') as f:
                json.dump({sid: s.to_dict() for sid, s in self.synapses.items()}, 
                         f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
    
    async def create_neuron(
        self,
        neuron_type: str = "interneuron",
        name: str = "",
        threshold: float = 0.5,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        """
        创建神经元
        
        Args:
            neuron_type: 神经元类型
            name: 神经元名称
            threshold: 激活阈值
            metadata: 元数据
        
        Returns:
            创建结果
        """
        try:
            neuron_id = self._generate_id("neuron")
            
            neuron = Neuron(
                id=neuron_id,
                neuron_type=neuron_type,
                name=name or f"Neuron_{neuron_id[:8]}",
                threshold=threshold,
                metadata=metadata or {}
            )
            
            self.neurons[neuron_id] = neuron
            self.neuron_type_index[neuron_type].append(neuron_id)
            self.stats["total_neurons"] += 1
            
            self._save_data()
            
            logger.info(f"创建神经元: {neuron_id} ({neuron_type})")
            
            return {
                "success": True,
                "neuron_id": neuron_id,
                "neuron_type": neuron_type
            }
            
        except Exception as e:
            logger.error(f"创建神经元失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_synapse(
        self,
        source_id: str,
        target_id: str,
        weight: float = 1.0,
        synapse_type: str = "excitatory"
    ) -> Dict[str, Any]:
        """
        创建突触连接
        
        Args:
            source_id: 源神经元ID
            target_id: 目标神经元ID
            weight: 突触权重
            synapse_type: 突触类型
        
        Returns:
            创建结果
        """
        try:
            if source_id not in self.neurons:
                return {"success": False, "error": f"源神经元不存在: {source_id}"}
            if target_id not in self.neurons:
                return {"success": False, "error": f"目标神经元不存在: {target_id}"}
            
            synapse_id = self._generate_id("synapse")
            
            synapse = Synapse(
                id=synapse_id,
                source_id=source_id,
                target_id=target_id,
                weight=weight,
                synapse_type=synapse_type
            )
            
            self.synapses[synapse_id] = synapse
            
            # 更新神经元连接
            self.neurons[source_id].connections_out.append(synapse_id)
            self.neurons[target_id].connections_in.append(synapse_id)
            
            # 更新连接图
            self.connection_graph[source_id].append(target_id)
            
            self.stats["total_synapses"] += 1
            self._save_data()
            
            logger.info(f"创建突触: {source_id} -> {target_id}, 权重: {weight}")
            
            return {
                "success": True,
                "synapse_id": synapse_id,
                "source_id": source_id,
                "target_id": target_id
            }
            
        except Exception as e:
            logger.error(f"创建突触失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_circuit(
        self,
        name: str,
        neuron_ids: List[str],
        circuit_type: str = "default"
    ) -> Dict[str, Any]:
        """
        创建神经回路
        
        Args:
            name: 回路名称
            neuron_ids: 神经元ID列表
            circuit_type: 回路类型
        
        Returns:
            创建结果
        """
        try:
            circuit_id = self._generate_id("circuit")
            
            circuit = NeuralCircuit(
                circuit_id=circuit_id,
                name=name,
                circuit_type=circuit_type
            )
            
            for neuron_id in neuron_ids:
                if neuron_id in self.neurons:
                    circuit.add_neuron(self.neurons[neuron_id])
            
            # 添加回路内的突触
            for synapse in self.synapses.values():
                if synapse.source_id in circuit.neurons and synapse.target_id in circuit.neurons:
                    circuit.add_synapse(synapse)
            
            self.circuits[circuit_id] = circuit
            self.stats["total_circuits"] += 1
            
            logger.info(f"创建神经回路: {name}, 包含 {len(neuron_ids)} 个神经元")
            
            return {
                "success": True,
                "circuit_id": circuit_id,
                "neuron_count": len(circuit.neurons)
            }
            
        except Exception as e:
            logger.error(f"创建神经回路失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def activate_neuron(
        self,
        neuron_id: str,
        signal_strength: float = 1.0
    ) -> Dict[str, Any]:
        """
        激活神经元
        
        Args:
            neuron_id: 神经元ID
            signal_strength: 信号强度
        
        Returns:
            激活结果
        """
        if neuron_id not in self.neurons:
            return {"success": False, "error": "神经元不存在"}
        
        neuron = self.neurons[neuron_id]
        current_time = time.time()
        
        neuron.receive_input(signal_strength)
        activated = neuron.activate(current_time)
        
        self.stats["total_activations"] += 1
        
        # 如果激活，传播到下游神经元
        downstream_activations = []
        if activated:
            for synapse_id in neuron.connections_out:
                if synapse_id in self.synapses:
                    synapse = self.synapses[synapse_id]
                    transmitted_signal = synapse.transmit(signal_strength, current_time)
                    
                    if synapse.target_id in self.neurons:
                        target = self.neurons[synapse.target_id]
                        target.receive_input(transmitted_signal)
                        
                        downstream_activations.append({
                            "target_id": synapse.target_id,
                            "signal": transmitted_signal
                        })
        
        return {
            "success": True,
            "neuron_id": neuron_id,
            "activated": activated,
            "current_potential": neuron.current_potential,
            "downstream_activations": downstream_activations
        }
    
    async def reinforce_path(
        self,
        path: List[str],
        strength: float = 0.5
    ) -> Dict[str, Any]:
        """
        强化神经路径
        
        Args:
            path: 神经元ID列表，表示路径
            strength: 强化强度
        
        Returns:
            强化结果
        """
        if len(path) < 2:
            return {"success": False, "error": "路径至少需要2个神经元"}
        
        reinforced_synapses = []
        
        for i in range(len(path) - 1):
            source_id = path[i]
            target_id = path[i + 1]
            
            # 找到对应的突触
            for synapse in self.synapses.values():
                if synapse.source_id == source_id and synapse.target_id == target_id:
                    synapse.strengthen(1 + strength * self.learning_rate, self.max_weight)
                    reinforced_synapses.append(synapse.id)
                    break
        
        self.stats["total_reinforcements"] += 1
        self._save_data()
        
        logger.info(f"强化路径: {' -> '.join(path[:3])}..., 强化 {len(reinforced_synapses)} 个突触")
        
        return {
            "success": True,
            "path": path,
            "reinforced_count": len(reinforced_synapses),
            "reinforced_synapses": reinforced_synapses
        }
    
    async def apply_hebbian_learning(
        self,
        neuron_id: str,
        learning_rate: float = None
    ) -> Dict[str, Any]:
        """
        应用赫布学习规则
        "一起发放的神经元连接在一起"
        
        Args:
            neuron_id: 神经元ID
            learning_rate: 学习率
        
        Returns:
            学习结果
        """
        if neuron_id not in self.neurons:
            return {"success": False, "error": "神经元不存在"}
        
        neuron = self.neurons[neuron_id]
        lr = learning_rate or self.learning_rate
        
        # 强化所有输入突触
        strengthened = []
        for synapse_id in neuron.connections_in:
            if synapse_id in self.synapses:
                synapse = self.synapses[synapse_id]
                if synapse.activation_count > 0:
                    synapse.strengthen(1 + lr, self.max_weight)
                    strengthened.append(synapse_id)
        
        self._save_data()
        
        return {
            "success": True,
            "neuron_id": neuron_id,
            "strengthened_synapses": strengthened
        }
    
    async def find_path(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 5
    ) -> List[List[str]]:
        """
        查找两个神经元之间的路径
        
        Args:
            start_id: 起始神经元ID
            end_id: 目标神经元ID
            max_depth: 最大搜索深度
        
        Returns:
            路径列表
        """
        if start_id not in self.neurons or end_id not in self.neurons:
            return []
        
        paths = []
        
        def dfs(current_id: str, visited: Set[str], path: List[str]):
            if len(path) > max_depth:
                return
            
            if current_id == end_id:
                paths.append(path.copy())
                return
            
            visited.add(current_id)
            
            for next_id in self.connection_graph.get(current_id, []):
                if next_id not in visited:
                    path.append(next_id)
                    dfs(next_id, visited, path)
                    path.pop()
            
            visited.remove(current_id)
        
        dfs(start_id, set(), [start_id])
        
        # 按路径长度排序
        paths.sort(key=len)
        
        return paths
    
    async def get_neuron_info(self, neuron_id: str) -> Optional[Dict[str, Any]]:
        """获取神经元详细信息"""
        if neuron_id not in self.neurons:
            return None
        
        neuron = self.neurons[neuron_id]
        
        # 获取输入输出连接详情
        input_synapses = []
        for sid in neuron.connections_in:
            if sid in self.synapses:
                synapse = self.synapses[sid]
                input_synapses.append({
                    "synapse_id": sid,
                    "source_id": synapse.source_id,
                    "weight": synapse.weight,
                    "type": synapse.synapse_type
                })
        
        output_synapses = []
        for sid in neuron.connections_out:
            if sid in self.synapses:
                synapse = self.synapses[sid]
                output_synapses.append({
                    "synapse_id": sid,
                    "target_id": synapse.target_id,
                    "weight": synapse.weight,
                    "type": synapse.synapse_type
                })
        
        return {
            **neuron.to_dict(),
            "input_synapses": input_synapses,
            "output_synapses": output_synapses,
            "input_count": len(input_synapses),
            "output_count": len(output_synapses)
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        type_counts = {t: len(ids) for t, ids in self.neuron_type_index.items()}
        
        avg_weight = 0.0
        if self.synapses:
            avg_weight = sum(s.weight for s in self.synapses.values()) / len(self.synapses)
        
        return {
            "total_neurons": self.stats["total_neurons"],
            "total_synapses": self.stats["total_synapses"],
            "total_circuits": self.stats["total_circuits"],
            "total_activations": self.stats["total_activations"],
            "total_reinforcements": self.stats["total_reinforcements"],
            "neurons_by_type": type_counts,
            "average_synapse_weight": round(avg_weight, 3),
            "connection_density": len(self.synapses) / max(len(self.neurons), 1)
        }
    
    async def export_network(self, output_path: str) -> bool:
        """导出神经网络到文件"""
        try:
            data = {
                "neurons": {nid: n.to_dict() for nid, n in self.neurons.items()},
                "synapses": {sid: s.to_dict() for sid, s in self.synapses.items()},
                "circuits": {cid: c.get_statistics() for cid, c in self.circuits.items()},
                "stats": self.stats,
                "exported_at": datetime.now().isoformat()
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"神经网络已导出到: {output_path}")
            return True
        except Exception as e:
            logger.error(f"导出神经网络失败: {e}")
            return False


# 全局实例
_unified_neuron_system = None


def get_unified_neuron_system(config: Dict = None) -> UnifiedNeuronSystem:
    """获取统一神经元系统实例"""
    global _unified_neuron_system
    
    if _unified_neuron_system is None:
        _unified_neuron_system = UnifiedNeuronSystem(config)
    
    return _unified_neuron_system
