# Makefile for Project
# 项目工程化管理工具

.PHONY: help install dev-install test test-cov lint format check clean run

# 默认目标
help:
	@echo "可用命令:"
	@echo "  make install      - 安装生产依赖"
	@echo "  make dev-install  - 安装开发依赖"
	@echo "  make test         - 运行测试"
	@echo "  make test-cov     - 运行测试并生成覆盖率报告"
	@echo "  make lint         - 运行代码检查"
	@echo "  make format       - 格式化代码"
	@echo "  make check        - 运行所有检查(格式+类型+安全)"
	@echo "  make clean        - 清理缓存文件"
	@echo "  make run          - 启动开发服务器"

# 安装依赖
install:
	pip install -r requirements.txt

dev-install: install
	pip install -r requirements-dev.txt

# 测试
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing

# 代码质量
lint:
	ruff check .
	mypy system/ routers/ models/
	bandit -r system/ routers/

format:
	ruff format .

check: format lint
	@echo "所有检查完成"

# 清理
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "清理完成"

# 运行
run:
	python main.py

# 预提交检查
pre-commit:
	pre-commit run --all-files
