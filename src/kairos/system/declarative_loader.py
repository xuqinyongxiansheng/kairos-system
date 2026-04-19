"""
声明式配置加载器
从YAML文件加载系统核心定义，实现配置与代码分离
支持热重载、配置验证、环境变量覆盖
"""

import os
import re
import yaml
import json
import logging
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Type, TypeVar, Generic
from dataclasses import dataclass, field, asdict
from datetime import datetime
from functools import lru_cache
from copy import deepcopy

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass
class Metadata:
    """元数据基类"""
    name: str = "鸿蒙小雨"
    version: str = "1.0.0"
    description: str = ""
    createdAt: str = ""
    updatedAt: str = ""
    
    def __post_init__(self):
        if not self.createdAt:
            self.createdAt = datetime.now().isoformat()
        if not self.updatedAt:
            self.updatedAt = datetime.now().isoformat()

@dataclass
class IdentitySpec:
    """身份规格"""
    name: str = ""
    shortName: str = ""
    version: str = ""
    description: str = ""
    identity: Dict[str, Any] = field(default_factory=dict)
    personality: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ModelSpec:
    """模型规格"""
    name: str = ""
    variant: str = ""
    fullName: str = ""
    type: str = "local"
    provider: str = "ollama"
    capabilities: List[str] = field(default_factory=list)
    contextWindow: int = 8192
    maxTokens: int = 4096
    temperature: float = 0.7

@dataclass
class ModelConfigSpec:
    """模型配置规格"""
    primary: ModelSpec = field(default_factory=ModelSpec)
    fallback: List[ModelSpec] = field(default_factory=list)
    routing: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CorsSpec:
    """CORS配置规格"""
    enabled: bool = True
    allowOrigins: List[str] = field(default_factory=list)
    allowMethods: List[str] = field(default_factory=list)
    allowHeaders: List[str] = field(default_factory=list)
    allowCredentials: bool = True
    maxAge: int = 3600

@dataclass
class AuthSpec:
    """认证配置规格"""
    enabled: bool = False
    type: str = "jwt"
    jwt: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RateLimitSpec:
    """速率限制规格"""
    enabled: bool = True
    requests: int = 100
    windowSeconds: int = 60
    strategy: str = "sliding_window"

@dataclass
class InputValidationSpec:
    """输入验证规格"""
    enabled: bool = True
    maxMessageLength: int = 32000
    maxContentLength: int = 500000
    sanitizePatterns: List[str] = field(default_factory=list)

@dataclass
class SignatureSpec:
    """签名验证规格"""
    enabled: bool = False
    algorithm: str = "HMAC-SHA256"
    maxSkewSeconds: int = 300

@dataclass
class IPFilterSpec:
    """IP过滤规格"""
    whitelistEnabled: bool = False
    blacklistEnabled: bool = False
    whitelist: List[str] = field(default_factory=list)
    blacklist: List[str] = field(default_factory=list)

@dataclass
class SecurityConfigSpec:
    """安全配置规格"""
    cors: CorsSpec = field(default_factory=CorsSpec)
    authentication: AuthSpec = field(default_factory=AuthSpec)
    rateLimit: RateLimitSpec = field(default_factory=RateLimitSpec)
    inputValidation: InputValidationSpec = field(default_factory=InputValidationSpec)
    signature: SignatureSpec = field(default_factory=SignatureSpec)
    ipFilter: IPFilterSpec = field(default_factory=IPFilterSpec)

@dataclass
class PrometheusMetricSpec:
    """Prometheus指标规格"""
    name: str = ""
    type: str = "counter"
    labels: List[str] = field(default_factory=list)
    buckets: List[float] = field(default_factory=list)

@dataclass
class PrometheusSpec:
    """Prometheus配置规格"""
    enabled: bool = True
    path: str = "/metrics"
    metrics: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class HealthDependencySpec:
    """健康检查依赖规格"""
    name: str = ""
    check: str = ""
    timeoutSeconds: int = 5
    thresholdPercent: int = 90

@dataclass
class HealthCheckSpec:
    """健康检查规格"""
    enabled: bool = True
    endpoints: Dict[str, str] = field(default_factory=dict)
    dependencies: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class AuditLogSpec:
    """审计日志规格"""
    enabled: bool = True
    path: str = "./log/audit.log"
    format: str = "json"
    fields: List[str] = field(default_factory=list)

@dataclass
class PerformanceTrackingSpec:
    """性能追踪规格"""
    enabled: bool = True
    slowThresholdSeconds: float = 1.0
    sampleRate: float = 1.0

@dataclass
class MonitoringConfigSpec:
    """监控配置规格"""
    prometheus: PrometheusSpec = field(default_factory=PrometheusSpec)
    healthCheck: HealthCheckSpec = field(default_factory=HealthCheckSpec)
    auditLog: AuditLogSpec = field(default_factory=AuditLogSpec)
    performanceTracking: PerformanceTrackingSpec = field(default_factory=PerformanceTrackingSpec)

@dataclass
class CacheSpec:
    """缓存规格"""
    enabled: bool = True
    ttlSeconds: int = 300
    maxSize: int = 1000
    strategy: str = "lru"

@dataclass
class CacheConfigSpec:
    """缓存配置规格"""
    response: CacheSpec = field(default_factory=CacheSpec)
    model: CacheSpec = field(default_factory=CacheSpec)

@dataclass
class APIVersionSpec:
    """API版本规格"""
    prefix: str = ""
    deprecated: bool = False
    sunsetDate: Optional[str] = None
    features: List[str] = field(default_factory=list)

@dataclass
class APIConfigSpec:
    """API配置规格"""
    currentVersion: str = "v1"
    supportedVersions: List[str] = field(default_factory=list)
    versions: Dict[str, APIVersionSpec] = field(default_factory=dict)

@dataclass
class AgentSpec:
    """Agent规格"""
    name: str = ""
    type: str = ""
    description: str = ""
    priority: int = 5
    responsibilities: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    enabled: bool = True

@dataclass
class CharacterSpec:
    """人物设定规格"""
    name: str = ""
    displayName: str = ""
    role: str = ""
    personality: List[str] = field(default_factory=list)
    background: str = ""
    abilities: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    speakingStyle: str = ""
    values: List[str] = field(default_factory=list)
    default: bool = False

@dataclass
class SystemDefinition:
    """系统定义"""
    metadata: Metadata = field(default_factory=Metadata)
    identity: IdentitySpec = field(default_factory=IdentitySpec)
    modelConfig: ModelConfigSpec = field(default_factory=ModelConfigSpec)
    security: SecurityConfigSpec = field(default_factory=SecurityConfigSpec)
    monitoring: MonitoringConfigSpec = field(default_factory=MonitoringConfigSpec)
    cache: CacheConfigSpec = field(default_factory=CacheConfigSpec)
    api: APIConfigSpec = field(default_factory=APIConfigSpec)
    agents: List[AgentSpec] = field(default_factory=list)
    characters: List[CharacterSpec] = field(default_factory=list)

class DeclarativeLoader:
    """声明式配置加载器"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.environ.get(
            "HMYX_CONFIG_PATH",
            os.path.join(os.path.dirname(__file__), "core_definition.yaml")
        )
        self._config: SystemDefinition = None
        self._raw_config: Dict[str, Any] = {}
        self._last_modified: float = 0
        self._lock = threading.RLock()
        self._watchers: List[callable] = []
    
    def load(self, force_reload: bool = False) -> SystemDefinition:
        """加载配置"""
        with self._lock:
            if self._config and not force_reload:
                if not self._check_modified():
                    return self._config
            
            self._raw_config = self._load_yaml()
            self._config = self._parse_config(self._raw_config)
            self._apply_env_overrides()
            self._validate_config()
            
            logger.info(f"配置加载完成: {self.config_path}")
            return self._config
    
    def _load_yaml(self) -> Dict[str, Any]:
        """加载YAML文件"""
        path = Path(self.config_path)
        if not path.exists():
            logger.warning(f"配置文件不存在: {self.config_path}, 使用默认配置")
            return self._get_default_config()
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        documents = list(yaml.safe_load_all(content))
        
        merged = {'spec': {}}
        for doc in documents:
            if doc:
                if 'metadata' in doc and 'metadata' not in merged:
                    merged['metadata'] = doc['metadata']
                if 'kind' in doc:
                    kind = doc['kind']
                    if 'spec' in doc:
                        merged['spec'][kind] = doc['spec']
                        if 'metadata' in doc:
                            merged['spec'][kind]['_metadata'] = doc['metadata']
        
        return merged
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """深度合并字典"""
        result = deepcopy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result
    
    def _parse_config(self, raw: Dict[str, Any]) -> SystemDefinition:
        """解析配置"""
        definition = SystemDefinition()
        
        metadata = raw.get('metadata', {})
        definition.metadata = Metadata(
            name=metadata.get('name', '鸿蒙小雨'),
            version=metadata.get('version', '2.0.0'),
            description=metadata.get('description', ''),
            createdAt=metadata.get('createdAt', ''),
            updatedAt=metadata.get('updatedAt', '')
        )
        
        all_specs = raw.get('spec', {})
        kind = raw.get('kind', '')
        
        docs = [raw]
        if 'documents' in raw:
            docs = raw['documents']
        
        for doc in docs:
            kind = doc.get('kind', '')
            spec = doc.get('spec', {})
            
            if kind == 'Identity':
                definition.identity = IdentitySpec(
                    name=spec.get('name', ''),
                    shortName=spec.get('shortName', ''),
                    version=spec.get('version', ''),
                    description=spec.get('description', ''),
                    identity=spec.get('identity', {}),
                    personality=spec.get('personality', {})
                )
            
            elif kind == 'ModelConfig':
                primary = spec.get('primary', {})
                definition.modelConfig.primary = ModelSpec(
                    name=primary.get('name', 'gemma4'),
                    variant=primary.get('variant', 'e4b'),
                    fullName=primary.get('fullName', 'gemma4:e4b'),
                    type=primary.get('type', 'local'),
                    provider=primary.get('provider', 'ollama'),
                    capabilities=primary.get('capabilities', []),
                    contextWindow=primary.get('contextWindow', 8192),
                    maxTokens=primary.get('maxTokens', 4096),
                    temperature=primary.get('temperature', 0.7)
                )
                
                for fb in spec.get('fallback', []):
                    definition.modelConfig.fallback.append(ModelSpec(
                        name=fb.get('name', ''),
                        variant=fb.get('variant', ''),
                        fullName=fb.get('fullName', ''),
                        type=fb.get('type', 'local'),
                        provider=fb.get('provider', 'ollama')
                    ))
                
                definition.modelConfig.routing = spec.get('routing', {})
            
            elif kind == 'SecurityConfig':
                cors = spec.get('cors', {})
                definition.security.cors = CorsSpec(
                    enabled=cors.get('enabled', True),
                    allowOrigins=cors.get('allowOrigins', []),
                    allowMethods=cors.get('allowMethods', []),
                    allowHeaders=cors.get('allowHeaders', []),
                    allowCredentials=cors.get('allowCredentials', True),
                    maxAge=cors.get('maxAge', 3600)
                )
                
                auth = spec.get('authentication', {})
                definition.security.authentication = AuthSpec(
                    enabled=auth.get('enabled', False),
                    type=auth.get('type', 'jwt'),
                    jwt=auth.get('jwt', {})
                )
                
                rate_limit = spec.get('rateLimit', {})
                definition.security.rateLimit = RateLimitSpec(
                    enabled=rate_limit.get('enabled', True),
                    requests=rate_limit.get('requests', 100),
                    windowSeconds=rate_limit.get('windowSeconds', 60),
                    strategy=rate_limit.get('strategy', 'sliding_window')
                )
                
                input_val = spec.get('inputValidation', {})
                definition.security.inputValidation = InputValidationSpec(
                    enabled=input_val.get('enabled', True),
                    maxMessageLength=input_val.get('maxMessageLength', 32000),
                    maxContentLength=input_val.get('maxContentLength', 500000),
                    sanitizePatterns=input_val.get('sanitizePatterns', [])
                )
                
                sig = spec.get('signature', {})
                definition.security.signature = SignatureSpec(
                    enabled=sig.get('enabled', False),
                    algorithm=sig.get('algorithm', 'HMAC-SHA256'),
                    maxSkewSeconds=sig.get('maxSkewSeconds', 300)
                )
                
                ip_filter = spec.get('ipFilter', {})
                definition.security.ipFilter = IPFilterSpec(
                    whitelistEnabled=ip_filter.get('whitelistEnabled', False),
                    blacklistEnabled=ip_filter.get('blacklistEnabled', False),
                    whitelist=ip_filter.get('whitelist', []),
                    blacklist=ip_filter.get('blacklist', [])
                )
            
            elif kind == 'MonitoringConfig':
                prom = spec.get('prometheus', {})
                definition.monitoring.prometheus = PrometheusSpec(
                    enabled=prom.get('enabled', True),
                    path=prom.get('path', '/metrics'),
                    metrics=prom.get('metrics', [])
                )
                
                health = spec.get('healthCheck', {})
                definition.monitoring.healthCheck = HealthCheckSpec(
                    enabled=health.get('enabled', True),
                    endpoints=health.get('endpoints', {}),
                    dependencies=health.get('dependencies', [])
                )
                
                audit = spec.get('auditLog', {})
                definition.monitoring.auditLog = AuditLogSpec(
                    enabled=audit.get('enabled', True),
                    path=audit.get('path', './log/audit.log'),
                    format=audit.get('format', 'json'),
                    fields=audit.get('fields', [])
                )
                
                perf = spec.get('performanceTracking', {})
                definition.monitoring.performanceTracking = PerformanceTrackingSpec(
                    enabled=perf.get('enabled', True),
                    slowThresholdSeconds=perf.get('slowThresholdSeconds', 1.0),
                    sampleRate=perf.get('sampleRate', 1.0)
                )
            
            elif kind == 'CacheConfig':
                resp_cache = spec.get('response', {})
                definition.cache.response = CacheSpec(
                    enabled=resp_cache.get('enabled', True),
                    ttlSeconds=resp_cache.get('ttlSeconds', 300),
                    maxSize=resp_cache.get('maxSize', 1000),
                    strategy=resp_cache.get('strategy', 'lru')
                )
                
                model_cache = spec.get('model', {})
                definition.cache.model = CacheSpec(
                    enabled=model_cache.get('enabled', True),
                    ttlSeconds=model_cache.get('ttlSeconds', 300)
                )
            
            elif kind == 'APIConfig':
                definition.api.currentVersion = spec.get('currentVersion', 'v1')
                definition.api.supportedVersions = spec.get('supportedVersions', ['v1'])
                
                for ver_name, ver_spec in spec.get('versions', {}).items():
                    definition.api.versions[ver_name] = APIVersionSpec(
                        prefix=ver_spec.get('prefix', ''),
                        deprecated=ver_spec.get('deprecated', False),
                        sunsetDate=ver_spec.get('sunsetDate'),
                        features=ver_spec.get('features', [])
                    )
            
            elif kind == 'AgentDefinition':
                for agent_spec in spec.get('agents', []):
                    definition.agents.append(AgentSpec(
                        name=agent_spec.get('name', ''),
                        type=agent_spec.get('type', ''),
                        description=agent_spec.get('description', ''),
                        priority=agent_spec.get('priority', 5),
                        responsibilities=agent_spec.get('responsibilities', []),
                        capabilities=agent_spec.get('capabilities', []),
                        dependencies=agent_spec.get('dependencies', []),
                        enabled=agent_spec.get('enabled', True)
                    ))
            
            elif kind == 'CharacterDefinition':
                for char_spec in spec.get('characters', []):
                    definition.characters.append(CharacterSpec(
                        name=char_spec.get('name', ''),
                        displayName=char_spec.get('displayName', ''),
                        role=char_spec.get('role', ''),
                        personality=char_spec.get('personality', []),
                        background=char_spec.get('background', ''),
                        abilities=char_spec.get('abilities', []),
                        limitations=char_spec.get('limitations', []),
                        speakingStyle=char_spec.get('speakingStyle', ''),
                        values=char_spec.get('values', []),
                        default=char_spec.get('default', False)
                    ))
        
        return definition
    
    def _apply_env_overrides(self):
        """应用环境变量覆盖"""
        env_mappings = {
            'GEMMA4_ENV': ('metadata', 'environment'),
            'GEMMA4_MODEL': ('modelConfig', 'primary', 'fullName'),
            'GEMMA4_AUTH_ENABLED': ('security', 'authentication', 'enabled'),
            'GEMMA4_RATE_LIMIT_ENABLED': ('security', 'rateLimit', 'enabled'),
            'GEMMA4_RATE_LIMIT_REQUESTS': ('security', 'rateLimit', 'requests'),
            'GEMMA4_METRICS_ENABLED': ('monitoring', 'prometheus', 'enabled'),
            'GEMMA4_AUDIT_LOG_ENABLED': ('monitoring', 'auditLog', 'enabled'),
            'GEMMA4_RESPONSE_CACHE_ENABLED': ('cache', 'response', 'enabled'),
        }
        
        for env_key, path in env_mappings.items():
            value = os.environ.get(env_key)
            if value is not None:
                self._set_nested(self._config, path, self._parse_env_value(value))
    
    def _set_nested(self, obj, path: tuple, value):
        """设置嵌套属性"""
        current = obj
        for key in path[:-1]:
            current = getattr(current, key)
        setattr(current, path[-1], value)
    
    def _parse_env_value(self, value: str):
        """解析环境变量值"""
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value
    
    def _validate_config(self):
        """验证配置"""
        errors = []
        
        if not self._config.metadata.name:
            errors.append("系统名称不能为空")
        
        if not self._config.modelConfig.primary.fullName:
            errors.append("主模型名称不能为空")
        
        if self._config.security.cors.allowCredentials:
            if '*' in self._config.security.cors.allowOrigins:
                errors.append("CORS: allowCredentials=True时不能使用通配符allowOrigins")
        
        for agent in self._config.agents:
            if agent.priority < 1 or agent.priority > 10:
                errors.append(f"Agent {agent.name} 优先级超出范围 [1, 10]")
        
        if errors:
            for error in errors:
                logger.error(f"配置验证失败: {error}")
            raise ValueError(f"配置验证失败: {'; '.join(errors)}")
    
    def _check_modified(self) -> bool:
        """检查文件是否被修改"""
        try:
            mtime = os.path.getmtime(self.config_path)
            if mtime > self._last_modified:
                self._last_modified = mtime
                return True
            return False
        except OSError:
            return False
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'metadata': {
                'name': '鸿蒙小雨',
                'version': '2.0.0'
            },
            'kind': 'SystemDefinition',
            'spec': {}
        }
    
    def get_config(self) -> SystemDefinition:
        """获取配置（延迟加载）"""
        if self._config is None:
            return self.load()
        return self._config
    
    def reload(self) -> SystemDefinition:
        """重新加载配置"""
        return self.load(force_reload=True)
    
    def add_watcher(self, callback: callable):
        """添加配置变更监听器"""
        self._watchers.append(callback)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        config = self.get_config()
        return {
            'metadata': asdict(config.metadata),
            'identity': asdict(config.identity),
            'modelConfig': asdict(config.modelConfig),
            'security': asdict(config.security),
            'monitoring': asdict(config.monitoring),
            'cache': asdict(config.cache),
            'api': asdict(config.api),
            'agents': [asdict(a) for a in config.agents],
            'characters': [asdict(c) for c in config.characters]
        }
    
    def export_json(self, path: str):
        """导出为JSON"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

_loader: Optional[DeclarativeLoader] = None

def get_loader() -> DeclarativeLoader:
    """获取全局加载器实例"""
    global _loader
    if _loader is None:
        _loader = DeclarativeLoader()
    return _loader

def get_config() -> SystemDefinition:
    """获取系统配置"""
    return get_loader().get_config()

def reload_config() -> SystemDefinition:
    """重新加载配置"""
    return get_loader().reload()
