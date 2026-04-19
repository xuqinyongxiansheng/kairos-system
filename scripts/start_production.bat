@echo off
chcp 65001 >nul
echo ============================================================
echo Gemma4 Autonomous Work System - Production Mode
echo ============================================================
echo.

REM 设置环境变量
set GEMMA4_ENV=production
set GEMMA4_MODEL=qwen2:0.5b
set GEMMA4_MODEL_CACHE_TTL=300

REM HTTPS配置(需要提供证书路径)
REM set GEMMA4_HTTPS=true
REM set GEMMA4_SSL_CERT=path\to\cert.pem
REM set GEMMA4_SSL_KEY=path\to\key.pem

echo Environment: %GEMMA4_ENV%
echo Default Model: %GEMMA4_MODEL%
echo Model Cache TTL: %GEMMA4_MODEL_CACHE_TTL%s
echo.
echo Starting server...
echo.

python main.py

pause
