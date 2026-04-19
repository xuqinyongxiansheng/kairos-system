#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鸿蒙小雨环境配置管理器
提供统一的环境配置加载、验证和管理

特性：
1. 多环境支持（development/test/production）
2. 配置验证和类型转换
3. 默认值管理
4. 环境变量覆盖
5. 配置热重载
"""

import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union, get_type_hints
from dataclasses import dataclass, field, fields, asdict
from enum import Enum
from functools import lru_cache
from datetime import datetime

def _get_version() -> str:
    try:
        from kairos.version import VERSION
        return VERSION
    except ImportError:
        return "4.0.0"

logger = logging.getLogger("EnvironmentConfig")

class Environment(Enum):
    """运行环境枚举"""
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"
    
    @classmethod
    def from_string(cls, value: str) -> 'Environment':
        """从字符串创建环境枚举"""
        value = value.lower().strip()
        mapping = {
            "development": cls.DEVELOPMENT,
            "dev": cls.DEVELOPMENT,
            "test": cls.TEST,
            "testing": cls.TEST,
            "production": cls.PRODUCTION,
            "prod": cls.PRODUCTION,
        }
        return mapping.get(value, cls.DEVELOPMENT)


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    debug: bool = True
    reload: bool = False
    
    https_enabled: bool = False
    ssl_cert: str = ""
    ssl_key: str = ""
    
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    cors_methods: List[str] = field(default_factory=lambda: ["*"])
    cors_headers: List[str] = field(default_factory=lambda: ["*"])
    
    max_request_size: int = 10 * 1024 * 1024
    request_timeout: int = 60
    keep_alive_timeout: int = 5


@dataclass
class ModelConfig:
    """模型配置"""
    default_model: str = "gemma4:e4b"
    ollama_host: str = "http://localhost:11434"
    model_cache_ttl: int = 300
    max_concurrent_requests: int = 10
    request_timeout: int = 120
    retry_attempts: int = 3
    retry_delay: float = 1.0


@dataclass
class SecurityConfig:
    """安全配置"""
    auth_enabled: bool = False
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    
    signature_enabled: bool = False
    signature_secret: str = ""
    signature_max_skew: int = 300
    
    ip_whitelist_enabled: bool = False
    ip_blacklist_enabled: bool = False
    ip_whitelist: List[str] = field(default_factory=list)
    ip_blacklist: List[str] = field(default_factory=list)
    
    https_enforce: bool = False


@dataclass
class CacheConfig:
    """缓存配置"""
    response_cache_enabled: bool = True
    response_cache_ttl: int = 300
    max_cache_entries: int = 1000
    
    memory_cache_enabled: bool = True
    memory_cache_max_mb: int = 512


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    
    file_enabled: bool = True
    file_path: str = "./log/hmyx.log"
    file_max_bytes: int = 10 * 1024 * 1024
    file_backup_count: int = 5
    
    console_enabled: bool = True
    console_colorize: bool = True
    
    audit_enabled: bool = True
    audit_path: str = "./log/audit.log"


@dataclass
class MonitoringConfig:
    """监控配置"""
    metrics_enabled: bool = True
    metrics_path: str = "/metrics"
    
    health_check_enabled: bool = True
    health_check_path: str = "/api/health"
    
    performance_tracking: bool = True
    slow_request_threshold: float = 1.0


@dataclass
class DatabaseConfig:
    """数据库配置"""
    enabled: bool = True
    path: str = "./data/hmyx.db"
    pool_size: int = 5
    timeout: int = 30


@dataclass
class MemorySystemConfig:
    """记忆系统配置"""
    working_memory_capacity: int = 9
    longterm_memory_path: str = "./data/memory"
    episodic_max: int = 1000
    forgetting_enabled: bool = True
    forgetting_rate: float = 0.1


@dataclass
class AppConfig:
    """应用总配置"""
    environment: Environment = Environment.DEVELOPMENT
    app_name: str = "鸿蒙小雨"
    app_version: str = _get_version()
    
    server: ServerConfig = field(default_factory=ServerConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    memory: MemorySystemConfig = field(default_factory=MemorySystemConfig)
    
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT
    
    def is_test(self) -> bool:
        return self.environment == Environment.TEST


class ConfigLoader:
    """
    配置加载器
    
    支持多种配置来源，按优先级从高到低：
    1. 环境变量
    2. .env文件
    3. 配置文件（YAML/JSON）
    4. 默认值
    """
    
    _instance: Optional['ConfigLoader'] = None
    _config: Optional[AppConfig] = None
    
    ENV_PREFIXES = ["HMYX_", "GEMMA4_"]
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is not None:
            return
        self._config = self._load_config()
    
    def _load_config(self) -> AppConfig:
        """加载配置"""
        self._load_env_file()
        
        env = self._get_env("ENV", "development")
        environment = Environment.from_string(env)
        
        config = AppConfig(environment=environment)
        
        self._apply_env_to_config(config)
        
        self._validate_config(config)
        
        return config
    
    def _load_env_file(self):
        """加载.env文件"""
        env_file = Path(".env")
        if not env_file.exists():
            for parent in Path.cwd().parents:
                candidate = parent / ".env"
                if candidate.exists():
                    env_file = candidate
                    break
        
        if env_file.exists():
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        if '=' in line:
                            key, _, value = line.partition('=')
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            if key and key not in os.environ:
                                os.environ[key] = value
                logger.info(f"已加载环境配置文件: {env_file}")
            except Exception as e:
                logger.warning(f"加载.env文件失败: {e}")
    
    def _get_env(self, key: str, default: Any = None) -> Any:
        """获取环境变量，支持多个前缀"""
        for prefix in self.ENV_PREFIXES:
            full_key = f"{prefix}{key}"
            if full_key in os.environ:
                return os.environ[full_key]
        if key in os.environ:
            return os.environ[key]
        return default
    
    def _apply_env_to_config(self, config: AppConfig):
        """将环境变量应用到配置"""
        env_mappings = {
            "server.host": ["API_HOST", "HOST"],
            "server.port": ["API_PORT", "PORT"],
            "server.debug": ["DEBUG"],
            "server.https_enabled": ["HTTPS"],
            "server.ssl_cert": ["SSL_CERT"],
            "server.ssl_key": ["SSL_KEY"],
            
            "model.default_model": ["MODEL"],
            "model.ollama_host": ["OLLAMA_HOST"],
            "model.model_cache_ttl": ["MODEL_CACHE_TTL"],
            
            "security.auth_enabled": ["AUTH_ENABLED"],
            "security.jwt_secret": ["JWT_SECRET"],
            "security.jwt_expire_hours": ["JWT_EXPIRE_HOURS"],
            "security.rate_limit_enabled": ["RATE_LIMIT_ENABLED"],
            "security.rate_limit_requests": ["RATE_LIMIT_REQUESTS"],
            "security.rate_limit_window": ["RATE_LIMIT_WINDOW"],
            "security.signature_enabled": ["SIGNATURE_ENABLED"],
            "security.signature_secret": ["SIGNATURE_SECRET"],
            
            "cache.response_cache_enabled": ["RESPONSE_CACHE_ENABLED"],
            "cache.response_cache_ttl": ["RESPONSE_CACHE_TTL"],
            
            "logging.level": ["LOG_LEVEL"],
            "logging.file_path": ["LOG_DIR"],
            "logging.audit_enabled": ["AUDIT_LOG_ENABLED"],
            "logging.audit_path": ["AUDIT_LOG_FILE"],
            
            "monitoring.metrics_enabled": ["METRICS_ENABLED"],
            "monitoring.metrics_path": ["METRICS_PATH"],
            
            "database.path": ["DB_PATH"],
            
            "memory.working_memory_capacity": ["WORKING_MEMORY_CAPACITY"],
            "memory.longterm_memory_path": ["LONGTERM_MEMORY_PATH"],
            "memory.episodic_max": ["EPISODIC_MAX"],
        }
        
        for config_path, env_keys in env_mappings.items():
            value = None
            for env_key in env_keys:
                value = self._get_env(env_key)
                if value is not None:
                    break
            
            if value is not None:
                self._set_nested_attr(config, config_path, value)
    
    def _set_nested_attr(self, obj: Any, path: str, value: Any):
        """设置嵌套属性"""
        parts = path.split('.')
        current = obj
        
        for part in parts[:-1]:
            if hasattr(current, part):
                current = getattr(current, part)
            else:
                return
        
        final_attr = parts[-1]
        if hasattr(current, final_attr):
            current_type = type(getattr(current, final_attr))
            try:
                if current_type == bool:
                    converted = str(value).lower() in ('true', '1', 'yes', 'on')
                elif current_type == int:
                    converted = int(value)
                elif current_type == float:
                    converted = float(value)
                elif current_type == list:
                    converted = value.split(',') if isinstance(value, str) else value
                else:
                    converted = current_type(value)
                setattr(current, final_attr, converted)
            except (ValueError, TypeError) as e:
                logger.warning(f"配置类型转换失败 {path}={value}: {e}")
    
    def _validate_config(self, config: AppConfig):
        """验证配置"""
        if config.is_production():
            if not config.security.jwt_secret:
                logger.warning("生产环境未设置JWT密钥，将自动生成")
            
            if config.server.debug:
                logger.warning("生产环境启用了调试模式，建议关闭")
            
            if "*" in config.server.cors_origins:
                logger.warning("生产环境CORS设置为*，存在安全风险")
        
        if config.security.rate_limit_enabled:
            if config.security.rate_limit_requests <= 0:
                raise ValueError("速率限制请求数必须大于0")
            if config.security.rate_limit_window <= 0:
                raise ValueError("速率限制窗口必须大于0")
        
        if config.server.port < 1 or config.server.port > 65535:
            raise ValueError(f"无效的端口号: {config.server.port}")
    
    @classmethod
    def get_config(cls) -> AppConfig:
        """获取配置实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance._config
    
    @classmethod
    def reload(cls) -> AppConfig:
        """重新加载配置"""
        cls._instance = None
        cls._config = None
        return cls.get_config()


def get_config() -> AppConfig:
    """获取应用配置"""
    return ConfigLoader.get_config()


def setup_logging(config: Optional[LoggingConfig] = None):
    """设置日志系统"""
    if config is None:
        config = get_config().logging
    
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.level.upper(), logging.INFO))
    
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    formatter = logging.Formatter(config.format, config.date_format)
    
    if config.console_enabled:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        if config.console_colorize:
            try:
                import colorlog
                color_formatter = colorlog.ColoredFormatter(
                    "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    datefmt=config.date_format,
                    log_colors={
                        'DEBUG': 'cyan',
                        'INFO': 'green',
                        'WARNING': 'yellow',
                        'ERROR': 'red',
                        'CRITICAL': 'red,bg_white',
                    }
                )
                console_handler.setFormatter(color_formatter)
            except ImportError:
                pass
        root_logger.addHandler(console_handler)
    
    if config.file_enabled:
        log_path = Path(config.file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            config.file_path,
            maxBytes=config.file_max_bytes,
            backupCount=config.file_backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    logger.info(f"日志系统初始化完成，级别: {config.level}")


def ensure_directories():
    """确保必要的目录存在"""
    config = get_config()
    
    directories = [
        Path(config.logging.file_path).parent,
        Path(config.database.path).parent,
        Path(config.memory.longterm_memory_path),
        Path("./log"),
        Path("./data"),
        Path("./data/knowledge"),
        Path("./data/cache"),
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    
    logger.info("必要目录已创建")
