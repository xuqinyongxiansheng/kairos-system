# 鸿蒙小雨 (hmyx) v4.1 生产环境 Dockerfile
# 多阶段构建 + 安全加固 + 优雅关闭

# ============ 构建阶段 ============
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl git \
    && rm -rf /var/lib/apt/lists/*

COPY project/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============ 运行阶段 ============
FROM python:3.11-slim

LABEL maintainer="hmyx-team"
LABEL description="鸿蒙小雨智能集成系统 v4.1"
LABEL version="4.1.0"
LABEL org.opencontainers.image.source="https://github.com/hmyx/hmyx"

WORKDIR /app

# 创建非root用户（安全最佳实践）
RUN groupadd -r hmyx && useradd -r -g hmyx -d /app -s /sbin/nologin hmyx

# 最小运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl tini \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /app/data /app/log /app/vendor

# 从构建阶段复制Python包
COPY --from=builder /install /usr/local

# 复制项目代码和vendor依赖
COPY project/ .
COPY vendor/ ./vendor/

# ========== 环境变量配置 ==========
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # 运行环境
    GEMMA4_SERVER_ENV=production \
    GEMMA4_SERVER_DEBUG=false \
    GEMMA4_SERVER_HOST=0.0.0.0 \
    GEMMA4_SERVER_PORT=8000 \
    # Ollama LLM
    GEMMA4_OLLAMA_HOST=http://ollama:11434 \
    GEMMA4_OLLAMA_DEFAULT_MODEL=gemma4:e4b \
    GEMMA4_OLLAMA_TIMEOUT=180 \
    GEMMA4_OLLAMA_MAX_HISTORY_MESSAGES=20 \
    # 安全设置
    GEMMA4_SECURITY_AUTH_ENABLED=true \
    GEMMA4_SECURITY_RATE_LIMIT_ENABLED=true \
    GEMMA4_SECURITY_RATE_LIMIT_REQUESTS=100 \
    GEMMA4_SECURITY_RATE_LIMIT_WINDOW=60 \
    GEMMA4_SECURITY_AUDIT_LOG_ENABLED=true \
    GEMMA4_SECURITY_AUDIT_LOG_FILE=/app/log/audit.log \
    # API
    GEMMA4_API_METRICS_ENABLED=true \
    # 日志
    GEMMA4_LOG_LEVEL=INFO \
    GEMMA4_LOG_FILE_PATH=/app/log/hmyx.log \
    # 数据目录
    GEMMA4_MEMORY_VECTOR_DB_PATH=/app/data/vector_store

# 创建必要目录并设置权限
RUN mkdir -p /app/data/sessions /app/data/todos /app/data/team_memory \
    /app/data/dreams /app/data/bridge /app/log \
    && chown -R hmyx:hmyx /app

# 切换到非root用户
USER hmyx

EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# 使用tini作为PID 1，确保信号正确传递（优雅关闭）
ENTRYPOINT ["tini", "--"]

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
