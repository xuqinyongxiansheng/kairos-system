#!/usr/bin/env python3
"""
更新管理
自动检查和应用模型更新
"""

import os
import time
import threading
import requests
import hashlib
import shutil
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import schedule

from .model_registry import get_model_registry, ModelInfo
from .version_control import get_version_control


class UpdateManager:
    """更新管理"""
    
    def __init__(self, update_interval: int = 3600):
        self.update_interval = update_interval  # 检查更新的时间间隔（秒）
        self.update_sources = {
            "ollama": "https://api.ollama.ai/v1/models",
            "huggingface": "https://huggingface.co/api/models"
        }
        self.download_dir = "downloads/models"
        self.model_registry = get_model_registry()
        self.version_control = get_version_control()
        self.update_thread = None
        self.running = False
        
        # 确保下载目录存在
        os.makedirs(self.download_dir, exist_ok=True)
    
    def start(self):
        """启动更新检查"""
        if self.running:
            return
        
        self.running = True
        
        # 立即执行一次更新检查
        self.check_updates()
        
        # 定时执行更新检查
        schedule.every(self.update_interval).seconds.do(self.check_updates)
        
        # 启动定时任务线程
        self.update_thread = threading.Thread(target=self._run_schedule)
        self.update_thread.daemon = True
        self.update_thread.start()
    
    def stop(self):
        """停止更新检查"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=5)
    
    def _run_schedule(self):
        """运行定时任务"""
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def check_updates(self):
        """检查更新"""
        print(f"[{datetime.now()}] 检查模型更新...")
        
        # 获取所有模型
        models = self.model_registry.list_models()
        
        for model in models:
            try:
                self._check_model_update(model)
            except Exception as e:
                print(f"检查模型 {model.name} 更新失败: {e}")
    
    def _check_model_update(self, model: ModelInfo):
        """检查单个模型的更新"""
        # 根据提供商选择更新源
        if model.provider.lower() == "ollama":
            self._check_ollama_update(model)
        elif model.provider.lower() == "huggingface":
            self._check_huggingface_update(model)
    
    def _check_ollama_update(self, model: ModelInfo):
        """检查Ollama模型更新"""
        try:
            # 构建API URL
            api_url = f"http://localhost:11434/api/tags"
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                for tag in data.get("models", []):
                    if tag.get("name") == model.model_id:
                        current_version = tag.get("modified_at")
                        
                        # 获取当前版本信息
                        current_version_info = self.version_control.get_current_version(model.model_id)
                        
                        # 检查是否有更新
                        if not current_version_info or current_version_info.metadata.get("modified_at") != current_version:
                            print(f"发现模型 {model.name} 的更新")
                            self._update_ollama_model(model, current_version)
                        break
        except Exception as e:
            print(f"检查Ollama模型更新失败: {e}")
    
    def _check_huggingface_update(self, model: ModelInfo):
        """检查Hugging Face模型更新"""
        try:
            # 构建API URL
            model_name = model.model_id.replace("huggingface:", "")
            api_url = f"https://huggingface.co/api/models/{model_name}"
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                current_version = data.get("lastModified")
                
                # 获取当前版本信息
                current_version_info = self.version_control.get_current_version(model.model_id)
                
                # 检查是否有更新
                if not current_version_info or current_version_info.metadata.get("lastModified") != current_version:
                    print(f"发现模型 {model.name} 的更新")
                    self._update_huggingface_model(model, current_version)
        except Exception as e:
            print(f"检查Hugging Face模型更新失败: {e}")
    
    def _update_ollama_model(self, model: ModelInfo, modified_at: str):
        """更新Ollama模型"""
        try:
            # 使用ollama pull命令更新模型
            import subprocess
            result = subprocess.run(
                ["ollama", "pull", model.model_id],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # 创建新版本
                version = f"{datetime.now().strftime('%Y%m%d%H%M%S')}"
                self.version_control.create_version(
                    model_id=model.model_id,
                    version=version,
                    description=f"自动更新于 {datetime.now()}",
                    file_path=f"models/{model.model_id}",
                    metadata={"modified_at": modified_at}
                )
                
                # 更新模型信息
                self.model_registry.update_model(
                    model.model_id,
                    updated_at=datetime.now()
                )
                
                print(f"模型 {model.name} 更新成功")
            else:
                print(f"更新模型 {model.name} 失败: {result.stderr}")
        except Exception as e:
            print(f"更新Ollama模型失败: {e}")
    
    def _update_huggingface_model(self, model: ModelInfo, last_modified: str):
        """更新Hugging Face模型"""
        try:
            # 这里需要实现Hugging Face模型的下载逻辑
            # 简化示例
            model_name = model.model_id.replace("huggingface:", "")
            download_url = f"https://huggingface.co/{model_name}/resolve/main/model.bin"
            
            # 下载模型
            file_path = os.path.join(self.download_dir, f"{model.model_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.bin")
            response = requests.get(download_url, stream=True, timeout=300)
            
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # 创建新版本
                version = f"{datetime.now().strftime('%Y%m%d%H%M%S')}"
                self.version_control.create_version(
                    model_id=model.model_id,
                    version=version,
                    description=f"自动更新于 {datetime.now()}",
                    file_path=file_path,
                    metadata={"lastModified": last_modified}
                )
                
                # 更新模型信息
                self.model_registry.update_model(
                    model.model_id,
                    updated_at=datetime.now()
                )
                
                print(f"模型 {model.name} 更新成功")
            else:
                print(f"下载模型 {model.name} 失败: {response.status_code}")
        except Exception as e:
            print(f"更新Hugging Face模型失败: {e}")
    
    def manual_update(self, model_id: str) -> bool:
        """手动更新模型"""
        model = self.model_registry.get_model(model_id)
        if not model:
            return False
        
        try:
            self._check_model_update(model)
            return True
        except Exception as e:
            print(f"手动更新模型失败: {e}")
            return False


# 全局更新管理器实例
_update_manager = None

def get_update_manager() -> UpdateManager:
    """获取更新管理器实例"""
    global _update_manager
    if _update_manager is None:
        _update_manager = UpdateManager()
    return _update_manager


if __name__ == "__main__":
    # 测试
    update_manager = get_update_manager()
    
    # 启动更新检查
    update_manager.start()
    
    print("更新管理器已启动，按Ctrl+C退出")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        update_manager.stop()
        print("更新管理器已停止")