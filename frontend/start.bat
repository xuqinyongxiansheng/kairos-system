@echo off

set ROOT_DIR=%~dp0
set CALLER_DIR=%CD%

cd /d %ROOT_DIR%

REM 检查是否安装了bun
where bun >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: 未找到bun命令。请先安装bun。
    pause
    exit /b 1
)

REM 启动Gemma4 CLI
echo 启动Gemma4自主工作系统...
bun --env-file=.env ./src/entrypoints/cli.tsx %*

pause