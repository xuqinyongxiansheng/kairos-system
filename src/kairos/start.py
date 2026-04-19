#!/usr/bin/env python3
"""
Gemma4智能机器人系统启动脚本
负责启动API服务和必要的组件
"""

import os
import sys
import subprocess
import time
import logging
import argparse

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("StartScript")

def check_environment():
    """
    检查环境
    """
    logger.info("检查环境...")
    
    # 检查Python版本
    if sys.version_info < (3, 12):
        logger.error("Python版本需要3.12或更高")
        return False
    
    # 检查依赖
    try:
        import torch
        import transformers
        import fastapi
        import uvicorn
        logger.info("核心依赖检查通过")
    except ImportError as e:
        logger.error(f"依赖检查失败: {str(e)}")
        logger.info("请运行: pip install -r requirements.txt")
        return False
    
    # 检查模型目录
    model_path = "models/gemma4_e4b/"
    if not os.path.exists(model_path):
        logger.warning(f"模型目录不存在: {model_path}")
        logger.info("请确保Gemma4:e4b模型已正确部署")
    
    return True

def start_api_server(host="0.0.0.0", port=8000):
    """
    启动API服务器
    """
    logger.info(f"启动API服务器，监听 {host}:{port}")
    
    try:
        # 启动uvicorn服务器
        cmd = [
            sys.executable,
            "-m", "uvicorn",
            "api:app",
            "--host", host,
            "--port", str(port),
            "--reload"
        ]
        
        logger.info(f"执行命令: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        
    except subprocess.CalledProcessError as e:
        logger.error(f"启动API服务器失败: {str(e)}")
        return False
    except KeyboardInterrupt:
        logger.info("API服务器已停止")
        return True
    except Exception as e:
        logger.error(f"启动API服务器时发生错误: {str(e)}")
        return False

def main():
    """
    主函数
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Gemma4智能机器人系统启动脚本")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="API服务器主机")
    parser.add_argument("--port", type=int, default=8000, help="API服务器端口")
    args = parser.parse_args()
    
    # 检查环境
    if not check_environment():
        sys.exit(1)
    
    # 启动API服务器
    logger.info("启动Gemma4智能机器人系统...")
    start_api_server(args.host, args.port)

if __name__ == "__main__":
    main()