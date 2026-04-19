#!/usr/bin/env python3
"""
鸿蒙小雨 v4.1 集中配置管理系统
统一管理所有环境变量、模型参数、安全设置
支持.env文件 + 环境变量 + 默认值 三级覆盖

使用方式:
    from kairos.system.config import settings
    model = settings.ollama.default_model
    host = settings.server.host
"""

import os
from typing import List, Optional, Set
from pathlib import Path
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).parent.parent


class ServerSettings(BaseSettings):
    """服务器基础配置"""

    host: str = Field(default="127.0.0.1", description="监听地址")
    port: int = Field(default=8000, ge=1, le=65535)
    env: str = Field(default="development", description="运行环境")
    debug: bool = Field(default=False)
    workers: int = Field(default=1, ge=1, description="Worker进程数")
    reload: bool = Field(default=False, description="热重载开关")
    max_request_size: int = Field(default=10, ge=1, description="最大请求大小(MB)")
    request_timeout: int = Field(default=60, ge=1, description="请求超时(秒)")
    keep_alive_timeout: int = Field(default=5, ge=1, description="Keep-Alive超时(秒)")

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        return self.env == "development"

    class Config:
        env_prefix = "GEMMA4_SERVER_"


class OllamaSettings(BaseSettings):
    """Ollama LLM服务配置"""

    host: str = Field(default="http://127.0.0.1:11434", description="Ollama API地址")
    default_model: str = Field(default="gemma4:e4b", description="默认模型名称")
    timeout: float = Field(default=180.0, gt=0, description="请求超时(秒)")
    max_retries: int = Field(default=2, ge=0, le=5, description="最大重试次数")
    max_history_messages: int = Field(default=20, ge=1, le=100, description="历史消息上限")
    context_tokens: int = Field(default=4096, ge=512, le=128000, description="上下文窗口大小")
    model_cache_ttl: int = Field(default=300, ge=0, description="模型列表缓存TTL(秒)")
    max_concurrent_requests: int = Field(default=10, ge=1, description="最大并发请求数")
    request_timeout: int = Field(default=120, ge=1, description="Ollama请求超时(秒)")
    retry_attempts: int = Field(default=3, ge=0, le=10, description="重试次数")
    retry_delay: float = Field(default=1.0, ge=0, description="重试延迟(秒)")

    temperature: float = Field(default=0.6, ge=0.0, le=2.0)
    top_p: float = Field(default=0.85, ge=0.0, le=1.0)
    top_k: int = Field(default=40, ge=0)

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        return v.rstrip("/")

    class Config:
        env_prefix = "GEMMA4_OLLAMA_"


class SecuritySettings(BaseSettings):
    """安全相关配置"""

    auth_enabled: bool = Field(default=False, description="是否启用JWT认证")
    jwt_secret: str = Field(default="", description="JWT密钥(生产必填)")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_hours: int = Field(default=24, ge=1)

    rate_limit_enabled: bool = Field(default=True)
    rate_limit_requests: int = Field(default=100, ge=1)
    rate_limit_window: int = Field(default=60, ge=1)

    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000",
        description="CORS允许的来源"
    )

    https_enforce: bool = Field(default=False)
    https_enabled: bool = Field(default=False, description="HTTPS服务开关")
    ssl_cert: str = Field(default="", description="SSL证书路径")
    ssl_key: str = Field(default="", description="SSL密钥路径")

    signature_enabled: bool = Field(default=False)
    signature_secret: str = Field(default="")
    signature_max_skew: int = Field(default=300, ge=1, description="签名最大时间偏移(秒)")

    ip_whitelist_enabled: bool = Field(default=False)
    ip_blacklist_enabled: bool = Field(default=False)

    trusted_proxy_enabled: bool = Field(default=False, description="可信代理开关")
    trusted_proxy_header: str = Field(default="X-Forwarded-For", description="可信代理头部")
    api_key_hash: str = Field(default="", description="API密钥哈希")

    audit_log_enabled: bool = Field(default=True)
    audit_log_file: str = Field(default="./log/audit.log")

    response_cache_enabled: bool = Field(default=True)
    response_cache_ttl: int = Field(default=300, ge=0)
    max_cache_entries: int = Field(default=1000, ge=1, description="最大缓存条目数")

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ip_whitelist(self) -> Set[str]:
        raw = os.environ.get("GEMMA4_IP_WHITELIST", "")
        return set(o.strip() for o in raw.split(",") if o.strip())

    @property
    def ip_blacklist(self) -> Set[str]:
        raw = os.environ.get("GEMMA4_IP_BLACKLIST", "")
        return set(o.strip() for o in raw.split(",") if o.strip())

    class Config:
        env_prefix = "GEMMA4_SECURITY_"


class APISettings(BaseSettings):
    """API接口配置"""

    version: str = Field(default="v4.0.0")
    prefix: str = Field(default="/api")
    docs_url: str = Field(default="/docs")
    redoc_url: str = Field(default="/redoc")
    openapi_url: str = Field(default="/openapi.json")

    public_endpoints: List[str] = Field(default=[
        "/api/health", "/api/core", "/docs", "/redoc",
        "/openapi.json", "/api/v1/health", "/api/v2/health",
        "/metrics", "/api/ready", "/api/live", "/", "/chat"
    ])

    chat_max_message_length: int = Field(default=32000, ge=1, le=100000)
    metrics_enabled: bool = Field(default=True)
    metrics_path: str = Field(default="/metrics")

    class Config:
        env_prefix = "GEMMA4_API_"


class MemorySettings(BaseSettings):
    """记忆系统配置"""

    max_sessions: int = Field(default=50, ge=1, description="最大会话数")
    session_ttl_days: int = Field(default=30, ge=1)
    vector_db_path: str = Field(default="./data/vector_store")
    knowledge_graph_path: str = Field(default="./data/knowledge_graph.json")
    working_memory_capacity: int = Field(default=9, ge=1, description="工作记忆容量")
    longterm_memory_path: str = Field(default="./data/memory", description="长期记忆路径")
    episodic_max: int = Field(default=1000, ge=1, description="情景记忆上限")
    forgetting_enabled: bool = Field(default=True, description="遗忘机制开关")
    forgetting_rate: float = Field(default=0.1, ge=0, le=1, description="遗忘速率")

    class Config:
        env_prefix = "GEMMA4_MEMORY_"


class LoggingSettings(BaseSettings):
    """日志配置"""

    level: str = Field(default="INFO")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    date_format: str = Field(default="%Y-%m-%d %H:%M:%S", description="日期格式")
    file_path: str = Field(default="./log/hmyx.log")
    file_enabled: bool = Field(default=True, description="文件日志开关")
    max_size_mb: int = Field(default=50, ge=1)
    backup_count: int = Field(default=5, ge=0)
    console_output: bool = Field(default=True)
    console_colorize: bool = Field(default=True, description="控制台彩色输出")

    class Config:
        env_prefix = "GEMMA4_LOG_"


class CacheSettings(BaseSettings):
    """缓存配置"""

    response_cache_enabled: bool = Field(default=True)
    response_cache_ttl: int = Field(default=300, ge=0)
    max_cache_entries: int = Field(default=1000, ge=1)
    memory_cache_enabled: bool = Field(default=True, description="内存缓存开关")
    memory_cache_max_mb: int = Field(default=512, ge=1, description="内存缓存最大MB")

    class Config:
        env_prefix = "GEMMA4_CACHE_"


class MonitoringSettings(BaseSettings):
    """监控配置"""

    metrics_enabled: bool = Field(default=True)
    metrics_path: str = Field(default="/metrics")
    health_check_enabled: bool = Field(default=True, description="健康检查开关")
    health_check_path: str = Field(default="/api/health", description="健康检查路径")
    performance_tracking: bool = Field(default=True, description="性能追踪开关")
    slow_request_threshold: float = Field(default=1.0, ge=0, description="慢请求阈值(秒)")

    class Config:
        env_prefix = "GEMMA4_MONITORING_"


class DatabaseSettings(BaseSettings):
    """数据库配置"""

    enabled: bool = Field(default=True, description="数据库开关")
    path: str = Field(default="./data/hmyx.db", description="数据库路径")
    pool_size: int = Field(default=5, ge=1, description="连接池大小")
    timeout: int = Field(default=30, ge=1, description="超时时间(秒)")

    class Config:
        env_prefix = "GEMMA4_DATABASE_"


class CognitiveLoopSettings(BaseSettings):
    """认知闭环配置"""

    max_iterations: int = Field(default=10, ge=1, le=100, description="最大迭代次数")
    quality_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="质量阈值")
    llm_enabled: bool = Field(default=True, description="是否启用LLM语义推理")
    feedback_adjustment_step: float = Field(default=0.1, ge=0.01, le=0.5, description="反馈调整步长")
    history_maxlen: int = Field(default=100, ge=1, description="迭代历史最大长度")

    class Config:
        env_prefix = "GEMMA4_COGNITIVE_"


class AutoDreamSettings(BaseSettings):
    """AutoDream记忆整合配置"""

    enabled: bool = Field(default=True, description="AutoDream开关")
    interval_seconds: int = Field(default=300, ge=60, description="运行间隔(秒)")
    min_sessions: int = Field(default=5, ge=1, description="最小会话数门控")
    min_hours_since_last: int = Field(default=24, ge=1, description="最小运行间隔(小时)")
    scan_cooldown_seconds: int = Field(default=600, ge=60, description="扫描冷却时间(秒)")
    lock_file: str = Field(default="./data/autodream.lock", description="PID锁文件路径")

    class Config:
        env_prefix = "GEMMA4_AUTODREAM_"


class BackgroundServiceSettings(BaseSettings):
    """后台服务调度配置"""

    enabled: bool = Field(default=True, description="后台服务开关")
    check_interval_seconds: int = Field(default=10, ge=1, description="调度检查间隔(秒)")
    max_concurrent_tasks: int = Field(default=3, ge=1, description="最大并发任务数")
    task_timeout_seconds: int = Field(default=300, ge=10, description="任务超时(秒)")
    history_maxlen: int = Field(default=100, ge=1, description="执行历史最大长度")

    class Config:
        env_prefix = "GEMMA4_BACKGROUND_"


class CircuitBreakerSettings(BaseSettings):
    """熔断器配置"""

    failure_threshold: int = Field(default=5, ge=1, description="连续失败阈值")
    recovery_timeout: float = Field(default=30.0, gt=0, description="恢复超时(秒)")
    half_open_attempts: int = Field(default=3, ge=1, description="半开状态尝试次数")

    class Config:
        env_prefix = "GEMMA4_CIRCUIT_"


class LLMClientSettings(BaseSettings):
    """统一LLM客户端配置"""

    cache_size: int = Field(default=256, ge=0, description="LRU缓存最大条目数")
    cache_ttl: float = Field(default=300.0, gt=0, description="缓存TTL(秒)")
    max_concurrent: int = Field(default=4, ge=1, description="最大并发推理数")
    retry_max_attempts: int = Field(default=3, ge=1, le=10, description="重试最大次数")
    retry_base_delay: float = Field(default=0.5, ge=0, description="重试基础延迟(秒)")
    retry_max_delay: float = Field(default=10.0, gt=0, description="重试最大延迟(秒)")
    retry_backoff_factor: float = Field(default=2.0, ge=1.0, description="重试退避因子")
    health_check_interval: float = Field(default=30.0, gt=0, description="健康检查间隔(秒)")
    connection_pool_size: int = Field(default=10, ge=1, description="连接池大小")
    keepalive_connections: int = Field(default=5, ge=1, description="保持连接数")

    class Config:
        env_prefix = "GEMMA4_LLM_CLIENT_"


class DegradationSettings(BaseSettings):
    """服务降级配置"""

    enabled: bool = Field(default=True, description="降级开关")
    latency_threshold: float = Field(default=5.0, gt=0, description="降级延迟阈值(秒)")
    consecutive_failures: int = Field(default=3, ge=1, description="连续失败次数阈值")
    recovery_check_interval: int = Field(default=60, ge=10, description="恢复检查间隔(秒)")

    class Config:
        env_prefix = "GEMMA4_DEGRADATION_"


class SelfEvolutionSettings(BaseSettings):
    """自我进化配置"""

    enabled: bool = Field(default=True, description="自我进化开关")
    experience_success: int = Field(default=10, ge=1, description="成功经验值")
    experience_failure: int = Field(default=2, ge=0, description="失败经验值")
    auto_evolve_interval_hours: int = Field(default=24, ge=1, description="自动进化间隔(小时)")
    max_skill_level: int = Field(default=5, ge=1, description="最大技能等级")

    class Config:
        env_prefix = "GEMMA4_EVOLUTION_"


class Settings(BaseSettings):
    """全局配置聚合"""

    server: ServerSettings = Field(default_factory=ServerSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    api: APISettings = Field(default_factory=APISettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    cognitive: CognitiveLoopSettings = Field(default_factory=CognitiveLoopSettings)
    autodream: AutoDreamSettings = Field(default_factory=AutoDreamSettings)
    background: BackgroundServiceSettings = Field(default_factory=BackgroundServiceSettings)
    circuit: CircuitBreakerSettings = Field(default_factory=CircuitBreakerSettings)
    llm_client: LLMClientSettings = Field(default_factory=LLMClientSettings)
    degradation: DegradationSettings = Field(default_factory=DegradationSettings)
    evolution: SelfEvolutionSettings = Field(default_factory=SelfEvolutionSettings)

    ENV: str = Field(default="development")
    GEMMA4_ENV: Optional[str] = None
    GEMMA4_MODEL: Optional[str] = None
    GEMMA4_JWT_SECRET: Optional[str] = None

    model_config = {
        "env_file": str(_PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }

    def __init__(self, **data):
        super().__init__(**data)
        if self.GEMMA4_ENV:
            self.server.env = self.GEMMA4_ENV
        if self.GEMMA4_MODEL:
            self.ollama.default_model = self.GEMMA4_MODEL
        if self.GEMMA4_JWT_SECRET:
            self.security.jwt_secret = self.GEMMA4_JWT_SECRET

    @property
    def app_title(self) -> str:
        return f"鸿蒙小雨 v{self.api.version}"

    def validate_production(self) -> List[str]:
        """生产环境校验，返回警告列表"""
        warnings = []
        if self.server.is_production:
            if not self.security.auth_enabled:
                warnings.append("生产环境未启用认证 (GEMMA4_SECURITY_AUTH_ENABLED=true)")
            if not self.security.jwt_secret:
                warnings.append("生产环境未设置JWT密钥 (GEMMA4_SECURITY_JWT_SECRET)")
            if not self.security.https_enforce:
                warnings.append("生产环境未强制HTTPS")
        return warnings


@lru_cache()
def get_settings() -> Settings:
    """获取全局配置单例（带缓存）"""
    return Settings()


settings = get_settings()
