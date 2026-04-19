#!/bin/bash
# Gemma4:e4b智能机器人系统启动脚本
# 用于启动系统和监控服务

set -e

echo "=== Gemma4:e4b智能机器人系统启动脚本 ==="

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate || venv\Scripts\activate

# 启动API服务
echo "启动API服务..."
python api.py > logs/api.log 2>&1 &
API_PID=$!
echo "API服务已启动，PID: $API_PID"

# 等待API服务启动
echo "等待API服务启动..."
sleep 5

# 启动监控服务
echo "启动监控服务..."
python monitor.py > logs/monitor.log 2>&1 &
MONITOR_PID=$!
echo "监控服务已启动，PID: $MONITOR_PID"

# 记录进程ID
echo "$API_PID" > logs/api.pid
echo "$MONITOR_PID" > logs/monitor.pid

echo "=== 系统启动完成 ==="
echo "API服务日志: logs/api.log"
echo "监控服务日志: logs/monitor.log"
