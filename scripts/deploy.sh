#!/bin/bash
# Gemma4:e4b智能机器人系统部署脚本
# 用于自动化部署系统

set -e

echo "=== Gemma4:e4b智能机器人系统部署脚本 ==="

# 检查Python版本
echo "检查Python版本..."
python --version

# 创建虚拟环境
echo "创建虚拟环境..."
python -m venv venv

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate || venv\Scripts\activate

# 升级pip
echo "升级pip..."
pip install --upgrade pip

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 创建必要的目录
echo "创建必要的目录..."
mkdir -p models/gemma4_e4b
mkdir -p modules/audio
mkdir -p modules/vision
mkdir -p modules/memory
mkdir -p modules/model
mkdir -p modules/learning
mkdir -p logs
mkdir -p frontend

# 下载模型
echo "下载模型..."
python -c "from modules.model.deployer import ModelDeployer; deployer = ModelDeployer(model_repo='google/gemma-4-2b-it', model_path='models/gemma4_e4b', quantization_bits=4); deployer.deploy_model()"

# 启动服务
echo "启动服务..."
if [ "$1" = "--background" ]; then
    echo "在后台启动服务..."
    nohup python api.py > logs/server.log 2>&1 &
    echo "服务已在后台启动，日志输出到 logs/server.log"
else
    echo "在前台启动服务..."
    python api.py
fi

echo "=== 部署完成 ==="
