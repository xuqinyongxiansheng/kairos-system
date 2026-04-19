#!/usr/bin/env python3
"""
版本控制
管理模型版本，支持版本回滚和切换
"""

import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel


class VersionInfo(BaseModel):
    """版本信息"""
    version_id: str
    model_id: str
    version: str
    timestamp: datetime = datetime.now()
    description: str
    file_path: str
    metadata: Dict[str, Any] = {}
    is_current: bool = False


class VersionControl:
    """版本控制"""
    
    def __init__(self, storage_path: str = "data/version_control.json"):
        self.storage_path = storage_path
        self.versions: Dict[str, List[VersionInfo]] = {}
        self._load_from_disk()
    
    def _load_from_disk(self):
        """从磁盘加载版本信息"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for model_id, model_versions in data.items():
                        versions = []
                        for version_data in model_versions:
                            if 'timestamp' in version_data:
                                version_data['timestamp'] = datetime.fromisoformat(version_data['timestamp'])
                            versions.append(VersionInfo(**version_data))
                        self.versions[model_id] = versions
        except Exception as e:
            print(f"加载版本信息失败: {e}")
    
    def _save_to_disk(self):
        """保存版本信息到磁盘"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            
            # 转换为可序列化的格式
            data = {}
            for model_id, model_versions in self.versions.items():
                versions = []
                for version in model_versions:
                    version_dict = version.model_dump()
                    version_dict['timestamp'] = version_dict['timestamp'].isoformat()
                    versions.append(version_dict)
                data[model_id] = versions
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存版本信息失败: {e}")
    
    def create_version(self, model_id: str, version: str, description: str, 
                      file_path: str, metadata: Dict[str, Any] = None) -> VersionInfo:
        """创建版本"""
        version_id = f"{model_id}:{version}"
        
        # 确保模型版本列表存在
        if model_id not in self.versions:
            self.versions[model_id] = []
        
        # 取消当前版本标记
        for v in self.versions[model_id]:
            v.is_current = False
        
        # 创建新版本
        version_info = VersionInfo(
            version_id=version_id,
            model_id=model_id,
            version=version,
            description=description,
            file_path=file_path,
            metadata=metadata or {},
            is_current=True
        )
        
        # 添加到版本列表
        self.versions[model_id].append(version_info)
        
        # 按版本号排序
        self.versions[model_id].sort(key=lambda x: x.version, reverse=True)
        
        self._save_to_disk()
        return version_info
    
    def get_versions(self, model_id: str) -> List[VersionInfo]:
        """获取模型的所有版本"""
        return self.versions.get(model_id, [])
    
    def get_current_version(self, model_id: str) -> Optional[VersionInfo]:
        """获取当前版本"""
        for version in self.versions.get(model_id, []):
            if version.is_current:
                return version
        return None
    
    def get_version(self, model_id: str, version: str) -> Optional[VersionInfo]:
        """获取指定版本"""
        version_id = f"{model_id}:{version}"
        for v in self.versions.get(model_id, []):
            if v.version == version:
                return v
        return None
    
    def rollback(self, model_id: str, version: str) -> bool:
        """回滚到指定版本"""
        target_version = self.get_version(model_id, version)
        if not target_version:
            return False
        
        # 取消当前版本标记
        for v in self.versions[model_id]:
            v.is_current = False
        
        # 标记目标版本为当前版本
        target_version.is_current = True
        
        self._save_to_disk()
        return True
    
    def delete_version(self, model_id: str, version: str) -> bool:
        """删除版本"""
        version_id = f"{model_id}:{version}"
        versions = self.versions.get(model_id, [])
        
        # 找到要删除的版本
        version_to_delete = None
        for v in versions:
            if v.version == version:
                version_to_delete = v
                break
        
        if not version_to_delete:
            return False
        
        # 不能删除当前版本
        if version_to_delete.is_current and len(versions) > 1:
            # 找到上一个版本并设为当前
            versions.remove(version_to_delete)
            if versions:
                versions[0].is_current = True
        elif version_to_delete.is_current:
            # 如果是最后一个版本，不能删除
            return False
        else:
            versions.remove(version_to_delete)
        
        self._save_to_disk()
        return True
    
    def list_models(self) -> List[str]:
        """列出所有有版本的模型"""
        return list(self.versions.keys())


# 全局版本控制实例
_version_control = None

def get_version_control() -> VersionControl:
    """获取版本控制实例"""
    global _version_control
    if _version_control is None:
        _version_control = VersionControl()
    return _version_control


if __name__ == "__main__":
    # 测试
    vc = get_version_control()
    
    # 创建版本
    vc.create_version(
        model_id="gemma4:e4b",
        version="1.0.0",
        description="初始版本",
        file_path="models/gemma4_e4b_v1.0.0"
    )
    
    vc.create_version(
        model_id="gemma4:e4b",
        version="1.1.0",
        description="更新版本",
        file_path="models/gemma4_e4b_v1.1.0"
    )
    
    # 列出版本
    print("所有版本:")
    for version in vc.get_versions("gemma4:e4b"):
        current = " (当前版本)" if version.is_current else ""
        print(f"- {version.version}: {version.description}{current}")
    
    # 回滚版本
    print("\n回滚到1.0.0版本")
    vc.rollback("gemma4:e4b", "1.0.0")
    
    # 查看当前版本
    current_version = vc.get_current_version("gemma4:e4b")
    print(f"当前版本: {current_version.version}")