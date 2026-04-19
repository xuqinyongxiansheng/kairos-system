#!/usr/bin/env python3
"""
模型注册中心
管理可用的AI模型信息
"""

import json
import os
from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime


class ModelInfo(BaseModel):
    """模型信息"""
    name: str
    provider: str
    capabilities: List[str]
    performance: Dict[str, float]
    cost: float
    availability: bool
    last_updated: datetime = datetime.now()
    description: Optional[str] = None


class ModelRegistry:
    """模型注册中心"""
    
    def __init__(self, storage_path: str = "data/model_registry.json"):
        self.storage_path = storage_path
        self.models: Dict[str, ModelInfo] = {}
        self._load_from_disk()
        self._initialize_default_models()
    
    def _load_from_disk(self):
        """从磁盘加载模型信息"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for model_name, model_data in data.items():
                        # 转换last_updated为datetime
                        if 'last_updated' in model_data:
                            model_data['last_updated'] = datetime.fromisoformat(model_data['last_updated'])
                        self.models[model_name] = ModelInfo(**model_data)
        except Exception as e:
            print(f"加载模型注册失败: {e}")
    
    def _save_to_disk(self):
        """保存模型信息到磁盘"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            
            # 转换为可序列化的格式
            data = {}
            for model_name, model_info in self.models.items():
                model_dict = model_info.model_dump()
                model_dict['last_updated'] = model_dict['last_updated'].isoformat()
                data[model_name] = model_dict
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存模型注册失败: {e}")
    
    def _initialize_default_models(self):
        """初始化默认模型"""
        default_models = [
            ModelInfo(
                name="gemma4:e4b",
                provider="Ollama",
                capabilities=["text_generation", "conversation", "coding"],
                performance={"accuracy": 0.85, "speed": 0.7, "cost_efficiency": 0.9},
                cost=0.0,
                availability=True,
                description="Gemma4 4-bit量化版本，平衡性能和资源使用"
            ),
            ModelInfo(
                name="gemma:latest",
                provider="Ollama",
                capabilities=["text_generation", "conversation"],
                performance={"accuracy": 0.8, "speed": 0.8, "cost_efficiency": 0.95},
                cost=0.0,
                availability=True,
                description="Gemma基础版本"
            ),
            ModelInfo(
                name="gemma4:latest",
                provider="Ollama",
                capabilities=["text_generation", "conversation", "coding", "reasoning"],
                performance={"accuracy": 0.9, "speed": 0.6, "cost_efficiency": 0.8},
                cost=0.0,
                availability=True,
                description="Gemma4最新版本"
            )
        ]
        
        for model in default_models:
            if model.name not in self.models:
                self.models[model.name] = model
        
        self._save_to_disk()
    
    def register_model(self, model_info: ModelInfo):
        """注册新模型"""
        self.models[model_info.name] = model_info
        self._save_to_disk()
        return True
    
    def get_model(self, model_name: str) -> Optional[ModelInfo]:
        """获取模型信息"""
        return self.models.get(model_name)
    
    def list_models(self, capability: Optional[str] = None) -> List[ModelInfo]:
        """列出模型，可按能力过滤"""
        if capability:
            return [model for model in self.models.values() if capability in model.capabilities]
        return list(self.models.values())
    
    def update_model(self, model_name: str, **kwargs):
        """更新模型信息"""
        if model_name in self.models:
            model = self.models[model_name]
            for key, value in kwargs.items():
                if hasattr(model, key):
                    setattr(model, key, value)
            model.last_updated = datetime.now()
            self._save_to_disk()
            return True
        return False
    
    def remove_model(self, model_name: str):
        """移除模型"""
        if model_name in self.models:
            del self.models[model_name]
            self._save_to_disk()
            return True
        return False
    
    def get_available_models(self) -> List[ModelInfo]:
        """获取可用模型"""
        return [model for model in self.models.values() if model.availability]
    
    def search_models(self, query: str) -> List[ModelInfo]:
        """搜索模型"""
        query = query.lower()
        results = []
        for model in self.models.values():
            if (query in model.name.lower() or 
                (model.description and query in model.description.lower()) or
                any(query in cap.lower() for cap in model.capabilities)):
                results.append(model)
        return results


# 全局模型注册中心实例
_model_registry = None

def get_model_registry() -> ModelRegistry:
    """获取模型注册中心实例"""
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistry()
    return _model_registry


if __name__ == "__main__":
    # 测试
    registry = get_model_registry()
    
    # 列出所有模型
    print("所有模型:")
    for model in registry.list_models():
        print(f"- {model.name}: {model.description}")
    
    # 按能力过滤
    print("\n支持编程的模型:")
    for model in registry.list_models("coding"):
        print(f"- {model.name}")
    
    # 搜索模型
    print("\n搜索包含'gemma'的模型:")
    for model in registry.search_models("gemma"):
        print(f"- {model.name}")