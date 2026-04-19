#!/usr/bin/env python3
"""
环境变量配置模块
用于配置 MiniMax API Key 和其他环境变量
"""

import os
from typing import Dict, Any, Optional


class EnvConfig:
    """环境变量配置"""
    
    DEFAULT_CONFIG = {
        "MINIMAX_API_KEY": "",
        "MINIMAX_BASE_URL": "https://api.minimax.chat",
        "OPENAI_API_KEY": "",
        "ANTHROPIC_API_KEY": "",
        "CLAUDE_MEM_MODE": "code--zh",
        "CLAUDE_MEM_PORT": "37777",
        "CLAUDE_MEM_DATA_DIR": "data/claude_mem",
    }
    
    def __init__(self, env_file: str = ".env"):
        self.env_file = env_file
        self.config = dict(self.DEFAULT_CONFIG)
        self._load_env()
    
    def _load_env(self):
        """加载环境变量"""
        # 先从 .env 文件加载
        if os.path.exists(self.env_file):
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        self.config[key] = value
        
        # 然后从系统环境变量覆盖
        for key in self.config:
            if key in os.environ:
                self.config[key] = os.environ[key]
    
    def get(self, key: str, default: str = None) -> Optional[str]:
        """获取配置值"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: str):
        """设置配置值"""
        self.config[key] = value
        os.environ[key] = value
    
    def save(self):
        """保存配置到 .env 文件"""
        with open(self.env_file, 'w', encoding='utf-8') as f:
            f.write("# 环境变量配置\n")
            f.write("# 请填入你的 API Key\n\n")
            for key, value in self.config.items():
                f.write(f"{key}={value}\n")
    
    def is_configured(self, key: str) -> bool:
        """检查是否已配置"""
        return bool(self.config.get(key))
    
    def get_status(self) -> Dict[str, Any]:
        """获取配置状态"""
        return {
            "minimax_api_key": self.is_configured("MINIMAX_API_KEY"),
            "openai_api_key": self.is_configured("OPENAI_API_KEY"),
            "anthropic_api_key": self.is_configured("ANTHROPIC_API_KEY"),
            "claude_mem_mode": self.get("CLAUDE_MEM_MODE"),
        }


# 全局配置实例
_env_config = None

def get_env_config() -> EnvConfig:
    """获取环境变量配置实例"""
    global _env_config
    if _env_config is None:
        _env_config = EnvConfig()
    return _env_config


if __name__ == "__main__":
    config = get_env_config()
    
    print("环境变量配置状态:")
    status = config.get_status()
    for key, value in status.items():
        print(f"  {key}: {'已配置' if value else '未配置'}")
    
    print("\n配置方法:")
    print("  1. 编辑 .env 文件，填入你的 API Key")
    print("  2. 或设置环境变量:")
    print("     set MINIMAX_API_KEY=your_key_here")
    print("     set OPENAI_API_KEY=your_key_here")