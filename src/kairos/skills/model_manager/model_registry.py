#!/usr/bin/env python3
"""
模型注册中心
管理AI模型的注册、查询和基本信息
"""

import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel


class ModelInfo(BaseModel):
    """模型信息"""
    model_id: str
    name: str
    provider: str
    version: str
    description: str
    capabilities: List[str]
    parameters: Dict[str, Any]
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    is_active: bool = True
    dependencies: List[str] = []
    metadata: Dict[str, Any] = {}


class ModelRegistry:
    """模型注册中心"""
    
    def __init__(self, storage_path: str = "data/model_registry.json"):
        self.storage_path = storage_path
        self.models: Dict[str, ModelInfo] = {}
        self._load_from_disk()
    
    def _load_from_disk(self):
        """从磁盘加载模型注册信息"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for model_id, model_data in data.items():
                        # 转换datetime字段
                        if 'created_at' in model_data:
                            model_data['created_at'] = datetime.fromisoformat(model_data['created_at'])
                        if 'updated_at' in model_data:
                            model_data['updated_at'] = datetime.fromisoformat(model_data['updated_at'])
                        self.models[model_id] = ModelInfo(**model_data)
        except Exception as e:
            print(f"加载模型注册失败: {e}")
    
    def _save_to_disk(self):
        """保存模型注册信息到磁盘"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            
            # 转换为可序列化的格式
            data = {}
            for model_id, model_info in self.models.items():
                model_dict = model_info.model_dump()
                model_dict['created_at'] = model_dict['created_at'].isoformat()
                model_dict['updated_at'] = model_dict['updated_at'].isoformat()
                data[model_id] = model_dict
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存模型注册失败: {e}")
    
    def register_model(self, model_info: ModelInfo) -> bool:
        """注册模型"""
        try:
            model_info.updated_at = datetime.now()
            self.models[model_info.model_id] = model_info
            self._save_to_disk()
            return True
        except Exception as e:
            print(f"注册模型失败: {e}")
            return False
    
    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """获取模型信息"""
        return self.models.get(model_id)
    
    def list_models(self, active_only: bool = True) -> List[ModelInfo]:
        """列出模型"""
        if active_only:
            return [model for model in self.models.values() if model.is_active]
        return list(self.models.values())
    
    def update_model(self, model_id: str, **kwargs) -> bool:
        """更新模型信息"""
        if model_id in self.models:
            model = self.models[model_id]
            for key, value in kwargs.items():
                if hasattr(model, key):
                    setattr(model, key, value)
            model.updated_at = datetime.now()
            self._save_to_disk()
            return True
        return False
    
    def deactivate_model(self, model_id: str) -> bool:
        """停用模型"""
        return self.update_model(model_id, is_active=False)
    
    def activate_model(self, model_id: str) -> bool:
        """激活模型"""
        return self.update_model(model_id, is_active=True)
    
    def delete_model(self, model_id: str) -> bool:
        """删除模型"""
        if model_id in self.models:
            del self.models[model_id]
            self._save_to_disk()
            return True
        return False
    
    def search_models(self, query: str) -> List[ModelInfo]:
        """搜索模型"""
        query = query.lower()
        results = []
        for model in self.models.values():
            if (query in model.name.lower() or 
                query in model.description.lower() or
                any(query in cap.lower() for cap in model.capabilities)):
                results.append(model)
        return results
    
    def get_models_by_capability(self, capability: str) -> List[ModelInfo]:
        """根据能力获取模型"""
        return [model for model in self.models.values() 
                if model.is_active and capability in model.capabilities]
    
    def get_models_by_provider(self, provider: str) -> List[ModelInfo]:
        """根据提供商获取模型"""
        return [model for model in self.models.values() 
                if model.is_active and model.provider == provider]


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
    
    # 注册模型
    model_info = ModelInfo(
        model_id="gemma4:e4b",
        name="Gemma4 4-bit",
        provider="Ollama",
        version="1.0.0",
        description="Gemma4 4-bit量化版本",
        capabilities=["text_generation", "conversation", "coding"],
        parameters={"temperature": 0.7, "max_tokens": 2048}
    )
    
    registry.register_model(model_info)
    
    # 列出模型
    print("所有模型:")
    for model in registry.list_models():
        print(f"- {model.name} ({model.model_id})")
    
    # 搜索模型
    print("\n搜索包含'gemma'的模型:")
    for model in registry.search_models("gemma"):
        print(f"- {model.name} ({model.model_id})")
    
    # 根据能力获取模型
    print("\n支持coding的模型:")
    for model in registry.get_models_by_capability("coding"):
        print(f"- {model.name} ({model.model_id})")