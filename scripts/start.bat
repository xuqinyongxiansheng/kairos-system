@echo off
chcp 65001 >nul 2>&1

echo ============================================================
echo   鸿蒙小雨 Gemma4 智能助手 v4.0.0
echo ============================================================
echo.

REM 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    exit /b 1
)

REM 检查 .env 文件
if not exist ".env" (
    if exist ".env.example" (
        echo [提示] 未找到 .env 文件，从 .env.example 复制...
        copy .env.example .env >nul
        echo [提示] 请编辑 .env 文件配置敏感信息
    )
)

REM 设置项目路径
set PYTHONPATH=%~dp0

REM 检查 Ollama
echo [检查] Ollama 服务...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] Ollama 服务未运行，请先启动 Ollama
    echo [提示] 运行: ollama serve
)

REM 启动后端 API
echo [启动] 后端 API 服务 (端口 8000)...
start "Gemma4 API" python -m uvicorn main:app --host 0.0.0.0 --port 8000

REM 等待后端启动
timeout /t 3 /nobreak >nul

REM 启动前端
echo [启动] 前端终端 UI...
cd frontend
.\bun.exe run src\gemma4-entry.ts

echo.
echo [信息] 系统已关闭
pause
