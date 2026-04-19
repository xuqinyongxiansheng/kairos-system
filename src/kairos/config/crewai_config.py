#!/usr/bin/env python3
"""
CrewAI 配置
"""

import os
from pydantic_settings import BaseSettings
from typing import Optional


class CrewAIConfig(BaseSettings):
    """CrewAI 配置"""
    # 基础配置
    openai_api_key: Optional[str] = os.environ.get("CREWAI_OPENAI_API_KEY")
    temperature: float = float(os.environ.get("CREWAI_TEMPERATURE", "0.7"))
    
    # 本地模型配置
    local_model_endpoint: str = os.environ.get("LOCAL_MODEL_ENDPOINT", "http://localhost:11434")
    default_model: str = os.environ.get("DEFAULT_MODEL", "gemma4:e4b")
    
    # 工具配置
    serper_api_key: Optional[str] = os.environ.get("SERPER_API_KEY")
    
    # 系统配置
    log_level: str = os.environ.get("LOG_LEVEL", "INFO")
    max_runtime: int = int(os.environ.get("MAX_RUNTIME", "3600"))
    
    # 代理配置
    proxy: Optional[str] = os.environ.get("HTTP_PROXY")
    
    class Config:
        env_file = ".env.crewai"
        case_sensitive = False


# 全局配置实例
_crewai_config = None

def get_crewai_config() -> CrewAIConfig:
    """获取 CrewAI 配置"""
    global _crewai_config
    if _crewai_config is None:
        _crewai_config = CrewAIConfig()
    return _crewai_config


if __name__ == "__main__":
    # 测试配置
    config = get_crewai_config()
    print(f"默认模型: {config.default_model}")
    print(f"本地模型端点: {config.local_model_endpoint}")
    print(f"温度参数: {config.temperature}")