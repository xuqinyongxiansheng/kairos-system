#!/usr/bin/env python3
"""
神经元系统 - 管理系统中的神经元节点
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("NeuronSystem")


class Neuron:
    """神经元类"""
    
    def __init__(self, neuron_id: str, neuron_type: str, metadata: Dict[str, Any] = None):
        """
        初始化神经元
        
        Args:
            neuron_id: 神经元 ID
            neuron_type: 神经元类型
            metadata: 元数据
        """
        self.id = neuron_id
        self.type = neuron_type
        self.metadata = metadata or {}
        self.status = "inactive"
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.event_history = []
        
        logger.info(f"神经元创建：{self.id} ({self.type})")
    
    def activate(self, payload: Dict[str, Any] = None):
        """激活神经元"""
        self.status = "active"
        self.last_activity = datetime.now()
        
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": "activation",
            "payload": payload or {}
        }
        self.event_history.append(event)
        
        logger.info(f"神经元激活：{self.id}")
    
    def deactivate(self):
        """停用神经元"""
        self.status = "inactive"
        self.last_activity = datetime.now()
        
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": "deactivation"
        }
        self.event_history.append(event)
        
        logger.info(f"神经元停用：{self.id}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取神经元状态"""
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "metadata": self.metadata,
            "event_count": len(self.event_history)
        }
    
    def __str__(self):
        return f"Neuron(id='{self.id}', type='{self.type}', status='{self.status}')"


class NeuronSystem:
    """神经元系统"""
    
    def __init__(self):
        """初始化神经元系统"""
        self.neurons = {}
        logger.info("神经元系统初始化完成")
    
    def register_neuron(self, neuron: Neuron):
        """注册神经元"""
        if neuron.id in self.neurons:
            logger.warning(f"神经元已存在：{neuron.id}")
            return
        
        self.neurons[neuron.id] = neuron
        logger.info(f"神经元注册成功：{neuron.id}")
    
    def unregister_neuron(self, neuron_id: str):
        """注销神经元"""
        if neuron_id in self.neurons:
            del self.neurons[neuron_id]
            logger.info(f"神经元注销成功：{neuron_id}")
        else:
            logger.warning(f"神经元不存在：{neuron_id}")
    
    def get_neuron(self, neuron_id: str) -> Optional[Neuron]:
        """获取神经元"""
        return self.neurons.get(neuron_id)
    
    def activate_neuron(self, neuron_id: str, payload: Dict[str, Any] = None) -> bool:
        """激活神经元"""
        neuron = self.get_neuron(neuron_id)
        if neuron:
            neuron.activate(payload)
            return True
        else:
            logger.error(f"神经元不存在：{neuron_id}")
            return False
    
    def deactivate_neuron(self, neuron_id: str) -> bool:
        """停用神经元"""
        neuron = self.get_neuron(neuron_id)
        if neuron:
            neuron.deactivate()
            return True
        else:
            logger.error(f"神经元不存在：{neuron_id}")
            return False
    
    def get_all_neurons(self) -> Dict[str, Neuron]:
        """获取所有神经元"""
        return self.neurons.copy()
    
    def get_neurons_by_type(self, neuron_type: str) -> list:
        """根据类型获取神经元"""
        return [neuron for neuron in self.neurons.values() if neuron.type == neuron_type]
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        active_count = sum(1 for neuron in self.neurons.values() if neuron.status == "active")
        inactive_count = len(self.neurons) - active_count
        
        return {
            "total_neurons": len(self.neurons),
            "active_neurons": active_count,
            "inactive_neurons": inactive_count,
            "neuron_types": list(set(neuron.type for neuron in self.neurons.values()))
        }
    
    def shutdown(self):
        """关闭神经元系统"""
        logger.info("神经元系统正在关闭")
        self.neurons.clear()
        logger.info("神经元系统关闭完成")


# 全局神经元系统实例
neuron_system = NeuronSystem()
