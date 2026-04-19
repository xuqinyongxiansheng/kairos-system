#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鸿蒙小雨统一启动入口
Single Source of Truth - 系统启动的唯一入口

职责：
1. 环境初始化和配置加载
2. 依赖检查和验证
3. FastAPI应用创建和中间件注册
4. API路由注册
5. 优雅启动和关闭

设计原则：
- 启动流程分阶段、可观测
- 配置统一由 environment.py 管理
- 安全中间件按需启用
- 健康检查贯穿全流程
"""

import os
import sys
import asyncio
import time
import logging
import hashlib
import secrets
import json
import threading
import hmac
import signal
import traceback
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Callable, Set
from dataclasses import dataclass, field
from pathlib import Path
from contextlib import asynccontextmanager

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "vendor"))

os.environ.setdefault("GEMMA4_ENV", "development")
os.environ.setdefault("HMYX_ENV", "development")

import psutil
from fastapi import FastAPI, HTTPException, Request, Depends, Security, APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
import uvicorn

try:
    import jwt as pyjwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    pyjwt = None

try:
    from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = Histogram = Gauge = Info = None

logger = logging.getLogger("HMYX.Bootstrap")


# ============================================================
# 阶段1: 启动结果和依赖检查
# ============================================================

@dataclass
class StartupResult:
    """启动结果"""
    success: bool
    message: str
    elapsed_ms: float = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    phase_results: Dict[str, Any] = field(default_factory=dict)


class DependencyChecker:
    """依赖检查器"""

    REQUIRED_PACKAGES = {
        "fastapi": "FastAPI框架",
        "uvicorn": "ASGI服务器",
        "pydantic": "数据验证",
        "psutil": "系统监控",
    }

    OPTIONAL_PACKAGES = {
        "ollama": "Ollama客户端",
        "jwt": "JWT认证",
        "prometheus_client": "Prometheus监控",
        "yaml": "YAML配置",
        "chromadb": "向量数据库",
    }

    def check_required(self) -> List[str]:
        missing = []
        for package, name in self.REQUIRED_PACKAGES.items():
            try:
                __import__(package)
            except ImportError:
                missing.append(f"{package} ({name})")
        return missing

    def check_optional(self) -> Dict[str, bool]:
        results = {}
        for package, name in self.OPTIONAL_PACKAGES.items():
            try:
                __import__(package)
                results[name] = True
            except ImportError:
                results[name] = False
        return results


# ============================================================
# 阶段2: 安全组件
# ============================================================

class RateLimiter:
    """基于IP的滑动窗口速率限制器"""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, client_id: str) -> tuple:
        now = time.time()
        window_start = now - self.window_seconds
        with self._lock:
            self._requests[client_id] = [
                t for t in self._requests[client_id] if t > window_start
            ]
            if len(self._requests[client_id]) >= self.max_requests:
                retry_after = int(self._requests[client_id][0] - window_start) + 1
                return False, retry_after
            self._requests[client_id].append(now)
            return True, 0

    def cleanup(self):
        now = time.time()
        window_start = now - self.window_seconds
        with self._lock:
            for client_id in list(self._requests.keys()):
                self._requests[client_id] = [
                    t for t in self._requests[client_id] if t > window_start
                ]
                if not self._requests[client_id]:
                    del self._requests[client_id]


class AuditLogger:
    """API审计日志记录器"""

    def __init__(self, log_file: str, enabled: bool = True):
        self.enabled = enabled
        self.log_file = log_file
        self._lock = threading.Lock()
        if enabled:
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)

    def log(self, event: Dict[str, Any]):
        if not self.enabled:
            return
        event["timestamp"] = datetime.now(timezone.utc).isoformat()
        with self._lock:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event, ensure_ascii=False) + "\n")
            except Exception as e:
                logger.error(f"审计日志写入失败: {e}")

    def log_request(self, request: Request, user_id: str = None, status_code: int = 200):
        self.log({
            "type": "api_request",
            "method": request.method,
            "path": request.url.path,
            "client_ip": self._get_client_ip(request),
            "user_id": user_id,
            "status_code": status_code
        })

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


class SignatureVerifier:
    """请求签名验证器"""

    def __init__(self, secret: str, max_skew: int = 300):
        self.secret = secret.encode() if secret else b""
        self.max_skew = max_skew
        self._nonces = defaultdict(float)
        self._lock = threading.Lock()

    def verify(self, request: Request, body: bytes = b"") -> tuple:
        if not self.secret:
            return True, ""
        signature = request.headers.get("X-Signature", "")
        timestamp = request.headers.get("X-Timestamp", "")
        nonce = request.headers.get("X-Nonce", "")
        if not all([signature, timestamp, nonce]):
            return False, "缺少签名参数"
        try:
            ts = int(timestamp)
        except ValueError:
            return False, "时间戳格式无效"
        now = int(time.time())
        if abs(now - ts) > self.max_skew:
            return False, "请求已过期"
        with self._lock:
            if nonce in self._nonces:
                return False, "请求已被使用"
            self._nonces[nonce] = now
            self._cleanup_nonces(now)
        expected = self._compute_signature(
            method=request.method, path=request.url.path,
            timestamp=timestamp, nonce=nonce, body=body
        )
        if not hmac.compare_digest(signature, expected):
            return False, "签名验证失败"
        return True, ""

    def _compute_signature(self, method: str, path: str, timestamp: str, nonce: str, body: bytes) -> str:
        message = f"{method.upper()}:{path}:{timestamp}:{nonce}:{body.hex() if body else ''}"
        return hmac.new(self.secret, message.encode(), hashlib.sha256).hexdigest()

    def _cleanup_nonces(self, now: int):
        expire = now - self.max_skew * 2
        for nonce in list(self._nonces.keys()):
            if self._nonces[nonce] < expire:
                del self._nonces[nonce]


class IPAccessController:
    """IP访问控制器"""

    def __init__(self, whitelist: Set[str], blacklist: Set[str],
                 whitelist_enabled: bool = False, blacklist_enabled: bool = False):
        self.whitelist = whitelist
        self.blacklist = blacklist
        self.whitelist_enabled = whitelist_enabled
        self.blacklist_enabled = blacklist_enabled

    def is_allowed(self, client_ip: str) -> tuple:
        if self.blacklist_enabled and client_ip in self.blacklist:
            return False, "IP已被封禁"
        if self.whitelist_enabled and client_ip not in self.whitelist:
            return False, "IP不在白名单中"
        return True, ""


class ResponseCache:
    """API响应缓存"""

    def __init__(self, ttl: int = 300, enabled: bool = True):
        self.ttl = ttl
        self.enabled = enabled
        self._cache: Dict[str, tuple] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        if not self.enabled:
            return None
        with self._lock:
            if key in self._cache:
                data, expire = self._cache[key]
                if time.time() < expire:
                    return data
                del self._cache[key]
        return None

    def set(self, key: str, value: Any):
        if not self.enabled:
            return
        with self._lock:
            self._cache[key] = (value, time.time() + self.ttl)

    def clear(self):
        with self._lock:
            self._cache.clear()

    def generate_key(self, request: Request) -> str:
        return f"{request.method}:{request.url.path}:{request.query_params}"


class HealthChecker:
    """健康检查器"""

    def __init__(self):
        self._start_time = time.time()
        self._shutdown_requested = False
        self._dependencies: Dict[str, Callable[[], bool]] = {}

    def register_dependency(self, name: str, check_func: Callable[[], bool]):
        self._dependencies[name] = check_func

    def check_all(self) -> Dict[str, Any]:
        results = {}
        all_healthy = True
        for name, check_func in self._dependencies.items():
            try:
                healthy = check_func()
                results[name] = {"status": "healthy" if healthy else "unhealthy"}
                if not healthy:
                    all_healthy = False
            except Exception as e:
                results[name] = {"status": "error", "message": str(e)}
                all_healthy = False
        return {
            "status": "healthy" if all_healthy else "degraded",
            "dependencies": results,
            "uptime_seconds": int(time.time() - self._start_time),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def check_live(self) -> bool:
        return not self._shutdown_requested

    def check_ready(self) -> tuple:
        if self._shutdown_requested:
            return False, "shutdown in progress"
        for name, check_func in self._dependencies.items():
            try:
                if not check_func():
                    return False, f"{name} not ready"
            except Exception:
                return False, f"{name} check failed"
        return True, "ready"

    def request_shutdown(self):
        self._shutdown_requested = True


class PerformanceTracker:
    """性能追踪器"""

    def __init__(self, slow_threshold: float = 1.0):
        self._requests = defaultdict(list)
        self._lock = threading.Lock()
        self._slow_threshold = slow_threshold

    def record(self, endpoint: str, duration: float, status_code: int):
        with self._lock:
            self._requests[endpoint].append({
                "duration": duration,
                "status_code": status_code,
                "timestamp": time.time()
            })
            if len(self._requests[endpoint]) > 1000:
                self._requests[endpoint] = self._requests[endpoint][-500:]

    def get_stats(self, endpoint: str = None) -> Dict[str, Any]:
        with self._lock:
            if endpoint:
                requests = self._requests.get(endpoint, [])
            else:
                requests = []
                for reqs in self._requests.values():
                    requests.extend(reqs)
            if not requests:
                return {"count": 0}
            durations = [r["duration"] for r in requests]
            return {
                "count": len(requests),
                "avg_duration": sum(durations) / len(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "p50": sorted(durations)[len(durations) // 2],
                "slow_requests": len([d for d in durations if d > self._slow_threshold])
            }


class ModelCache:
    """模型列表缓存"""

    def __init__(self, ttl: int = 300):
        self._models: Optional[List[str]] = None
        self._last_update: float = 0
        self._ttl = ttl
        self._lock = asyncio.Lock()

    async def get_models(self) -> List[str]:
        async with self._lock:
            now = time.time()
            if self._models is None or (now - self._last_update) > self._ttl:
                try:
                    import ollama
                    models = ollama.list()
                    self._models = []
                    if models and 'models' in models:
                        for m in models['models']:
                            if isinstance(m, dict):
                                self._models.append(m.get('name', 'unknown'))
                    self._last_update = now
                except Exception:
                    if self._models is None:
                        self._models = []
        return self._models or []

    async def refresh(self) -> List[str]:
        async with self._lock:
            try:
                import ollama
                models = ollama.list()
                self._models = []
                if models and 'models' in models:
                    for m in models['models']:
                        if isinstance(m, dict):
                            self._models.append(m.get('name', 'unknown'))
                self._last_update = time.time()
            except Exception:
                pass
        return self._models or []


# ============================================================
# 阶段3: 应用工厂
# ============================================================

# 全局组件实例（由create_app初始化）
_health_checker: Optional[HealthChecker] = None
_rate_limiter: Optional[RateLimiter] = None
_audit_logger: Optional[AuditLogger] = None
_signature_verifier: Optional[SignatureVerifier] = None
_ip_controller: Optional[IPAccessController] = None
_response_cache: Optional[ResponseCache] = None
_performance_tracker: Optional[PerformanceTracker] = None
_model_cache: Optional[ModelCache] = None
_prometheus_metrics: Dict[str, Any] = {}
_shutdown_handlers: List[Callable] = []


def _init_prometheus(config):
    """初始化Prometheus指标"""
    global _prometheus_metrics
    if not PROMETHEUS_AVAILABLE or not config.monitoring.metrics_enabled:
        return
    try:
        _prometheus_metrics = {
            'request_count': Counter(
                'http_requests_total', 'Total HTTP requests',
                ['method', 'endpoint', 'status']
            ),
            'request_latency': Histogram(
                'http_request_duration_seconds', 'HTTP request latency',
                ['method', 'endpoint'],
                buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
            ),
            'active_requests': Gauge(
                'http_requests_in_progress', 'HTTP requests in progress',
                ['method', 'endpoint']
            ),
        }
        Info('hmyx_system', 'System information').info({
            'version': config.app_version,
            'environment': config.environment.value,
        })
    except ValueError:
        pass


def _check_ollama_connection() -> bool:
    try:
        import ollama
        models = ollama.list()
        return models is not None
    except Exception:
        return False


def _check_memory_available() -> bool:
    try:
        memory = psutil.virtual_memory()
        return memory.percent < 90
    except Exception:
        return True


def create_app() -> FastAPI:
    """
    应用工厂 - 创建并配置FastAPI应用

    启动阶段：
    1. 加载环境配置
    2. 初始化日志
    3. 检查依赖
    4. 加载核心定义
    5. 初始化安全组件
    6. 注册中间件
    7. 注册路由
    """
    global _health_checker, _rate_limiter, _audit_logger, _signature_verifier
    global _ip_controller, _response_cache, _performance_tracker, _model_cache

    from kairos.system.environment import get_config, setup_logging, ensure_directories

    config = get_config()
    setup_logging(config.logging)
    ensure_directories()

    logger.info("=" * 60)
    logger.info("鸿蒙小雨系统启动中...")
    logger.info("=" * 60)

    # 阶段1: 依赖检查
    dep_checker = DependencyChecker()
    missing = dep_checker.check_required()
    if missing:
        logger.error(f"缺少必需依赖: {', '.join(missing)}")

    optional = dep_checker.check_optional()
    for name, available in optional.items():
        if not available:
            logger.warning(f"可选依赖不可用: {name}")

    # 阶段2: 加载核心定义
    try:
        from kairos.system.unified_initializer import get_core_loader
        loader = get_core_loader()
        if loader.load():
            identity = loader.get_system_identity()
            if identity:
                logger.info(f"系统身份: {identity.name} v{identity.version}")
            logger.info(f"已加载 {len(loader.get_all_characters())} 个人物定义")
            logger.info(f"已加载 {len(loader.get_all_agents())} 个Agent定义")
        else:
            logger.error("核心定义加载失败")
    except Exception as e:
        logger.error(f"加载核心定义失败: {e}")

    # 阶段3: 初始化安全组件
    sec = config.security

    _health_checker = HealthChecker()
    _rate_limiter = RateLimiter(
        max_requests=sec.rate_limit_requests,
        window_seconds=sec.rate_limit_window
    )
    _audit_logger = AuditLogger(
        config.logging.audit_path,
        enabled=config.logging.audit_enabled
    )
    _signature_verifier = SignatureVerifier(
        sec.signature_secret,
        max_skew=sec.signature_max_skew
    )
    _ip_controller = IPAccessController(
        whitelist=set(sec.ip_whitelist),
        blacklist=set(sec.ip_blacklist),
        whitelist_enabled=sec.ip_whitelist_enabled,
        blacklist_enabled=sec.ip_blacklist_enabled
    )
    _response_cache = ResponseCache(
        ttl=config.cache.response_cache_ttl,
        enabled=config.cache.response_cache_enabled
    )
    _performance_tracker = PerformanceTracker()
    _model_cache = ModelCache(ttl=config.model.model_cache_ttl)

    _health_checker.register_dependency("ollama", _check_ollama_connection)
    _health_checker.register_dependency("memory", _check_memory_available)

    _init_prometheus(config)

    # JWT密钥处理
    jwt_secret = sec.jwt_secret
    if not jwt_secret and sec.auth_enabled:
        jwt_secret = secrets.token_hex(32)
        logger.warning("未设置JWT密钥，已自动生成临时密钥")

    if not sec.signature_secret and sec.signature_enabled:
        sec.signature_secret = secrets.token_hex(32)
        logger.warning("未设置签名密钥，已自动生成临时密钥")

    # 阶段4: 创建FastAPI应用
    is_debug = config.is_development()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("应用启动完成")
        yield
        logger.info("应用关闭中...")
        _health_checker.request_shutdown()
        for handler in reversed(_shutdown_handlers):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
            except Exception as e:
                logger.error(f"关闭处理器执行失败: {e}")
        logger.info("应用已关闭")

    app = FastAPI(
        title=f"{config.app_name} API",
        description="基于kairos system的智能集成系统核心",
        version=config.app_version,
        docs_url="/docs" if is_debug else None,
        redoc_url="/redoc" if is_debug else None,
        openapi_url="/openapi.json" if is_debug else None,
        lifespan=lifespan,
    )

    # 阶段5: 注册中间件
    _register_middleware(app, config)

    # 阶段6: 注册路由
    _register_routes(app, config)

    logger.info("=" * 60)
    logger.info(f"启动完成 - {config.app_name} v{config.app_version}")
    logger.info(f"环境: {config.environment.value}")
    logger.info("=" * 60)

    return app


def _register_middleware(app: FastAPI, config):
    """注册所有中间件"""

    sec = config.security
    mon = config.monitoring

    PUBLIC_ENDPOINTS = {
        "/api/health", "/api/core", "/docs", "/redoc", "/openapi.json",
        "/api/v1/health", "/api/v2/health", "/metrics",
        "/api/ready", "/api/live", "/"
    }
    SKIP_RATE_LIMIT = {
        "/api/health", "/api/v1/health", "/api/v2/health",
        "/api/core", "/metrics", "/api/ready", "/api/live", "/"
    }
    SKIP_SIGNATURE = {
        "/api/health", "/api/v1/health", "/api/v2/health",
        "/api/core", "/docs", "/redoc", "/openapi.json",
        "/metrics", "/api/ready", "/api/live", "/"
    }

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.server.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "PUT", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With",
                       "Accept", "Origin", "X-Signature", "X-Timestamp", "X-Nonce"],
        max_age=3600,
    )

    # 安全头
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if config.is_production():
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # 指标中间件
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        if not mon.metrics_enabled or not PROMETHEUS_AVAILABLE:
            return await call_next(request)
        if request.url.path in [mon.metrics_path, "/api/ready", "/api/live"]:
            return await call_next(request)

        start_time = time.time()
        endpoint = request.url.path

        if _prometheus_metrics.get('active_requests'):
            _prometheus_metrics['active_requests'].labels(
                method=request.method, endpoint=endpoint).inc()

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            if _prometheus_metrics.get('request_count'):
                _prometheus_metrics['request_count'].labels(
                    method=request.method, endpoint=endpoint,
                    status=response.status_code).inc()
            if _prometheus_metrics.get('request_latency'):
                _prometheus_metrics['request_latency'].labels(
                    method=request.method, endpoint=endpoint).observe(duration)

            _performance_tracker.record(endpoint, duration, response.status_code)
            return response
        finally:
            if _prometheus_metrics.get('active_requests'):
                _prometheus_metrics['active_requests'].labels(
                    method=request.method, endpoint=endpoint).dec()

    # 速率限制
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        if not sec.rate_limit_enabled:
            return await call_next(request)
        if request.url.path in SKIP_RATE_LIMIT:
            return await call_next(request)

        client_ip = request.headers.get("X-Forwarded-For", "")
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        allowed, retry_after = _rate_limiter.is_allowed(client_ip)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"error": "请求过于频繁", "retry_after": retry_after},
                headers={"Retry-After": str(retry_after)}
            )
        return await call_next(request)

    # 审计日志
    @app.middleware("http")
    async def audit_middleware(request: Request, call_next):
        response = await call_next(request)
        if config.logging.audit_enabled:
            user_id = None
            if hasattr(request.state, "user"):
                user_id = request.state.user.get("user_id")
            _audit_logger.log_request(request, user_id=user_id, status_code=response.status_code)
        return response

    # IP访问控制
    @app.middleware("http")
    async def ip_access_middleware(request: Request, call_next):
        if not (sec.ip_whitelist_enabled or sec.ip_blacklist_enabled):
            return await call_next(request)
        if request.url.path in PUBLIC_ENDPOINTS:
            return await call_next(request)

        client_ip = request.headers.get("X-Forwarded-For", "")
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        allowed, reason = _ip_controller.is_allowed(client_ip)
        if not allowed:
            return JSONResponse(status_code=403, content={"error": "访问被拒绝", "detail": reason})
        return await call_next(request)

    # 签名验证
    @app.middleware("http")
    async def signature_middleware(request: Request, call_next):
        if not sec.signature_enabled:
            return await call_next(request)
        if request.url.path in SKIP_SIGNATURE:
            return await call_next(request)

        body = b""
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()

        valid, error = _signature_verifier.verify(request, body)
        if not valid:
            return JSONResponse(status_code=401, content={"error": "签名验证失败", "detail": error})
        return await call_next(request)

    # JWT认证
    security_scheme = HTTPBearer(auto_error=False)

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        if not sec.auth_enabled:
            return await call_next(request)
        if request.url.path in PUBLIC_ENDPOINTS:
            return await call_next(request)
        if request.method == "OPTIONS":
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": "未授权访问", "detail": "请提供有效的Bearer Token"}
            )

        token = auth_header.replace("Bearer ", "")
        payload = _verify_jwt_token(token, sec.jwt_secret, sec.jwt_algorithm)
        if not payload:
            return JSONResponse(
                status_code=401,
                content={"error": "认证失败", "detail": "令牌无效或已过期"}
            )
        request.state.user = payload
        return await call_next(request)

    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        error_id = f"err_{int(time.time() * 1000)}"
        logger.error(f"[{error_id}] 未处理异常: {type(exc).__name__}: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "内部服务器错误",
                "error_id": error_id,
                "detail": str(exc) if config.is_development() else "请稍后重试"
            }
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "status_code": exc.status_code}
        )


def _create_jwt_token(user_id: str, secret: str, algorithm: str, expire_hours: int,
                      extra_claims: Dict[str, Any] = None) -> str:
    if not JWT_AVAILABLE:
        raise RuntimeError("PyJWT未安装")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(hours=expire_hours),
        "jti": secrets.token_hex(16)
    }
    if extra_claims:
        payload.update(extra_claims)
    return pyjwt.encode(payload, secret, algorithm=algorithm)


def _verify_jwt_token(token: str, secret: str, algorithm: str) -> Optional[Dict[str, Any]]:
    if not JWT_AVAILABLE:
        return None
    try:
        return pyjwt.decode(token, secret, algorithms=[algorithm])
    except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
        return None


def _register_routes(app: FastAPI, config):
    """注册所有API路由"""

    sec = config.security
    mon = config.monitoring
    default_model = config.model.default_model

    # 系统身份提示词
    system_identity = _build_system_identity()

    # ---- 根路由 ----
    @app.get("/")
    async def root():
        return {
            "name": f"{config.app_name} API",
            "version": config.app_version,
            "status": "running",
            "environment": config.environment.value,
            "endpoints": {
                "health": "/api/health",
                "core": "/api/core",
                "chat": "/api/chat",
                "chat_ui": "/chat",
                "documents": "/api/v1/documents",
                "search": "/api/v1/search",
                "metrics": "/metrics",
                "docs": "/docs"
            }
        }

    @app.get("/chat")
    async def chat_ui():
        """聊天界面"""
        from fastapi.responses import FileResponse
        frontend_path = project_root / "frontend" / "index.html"
        if frontend_path.exists():
            return FileResponse(str(frontend_path), media_type="text/html")
        return JSONResponse(
            status_code=404,
            content={"error": "前端界面未找到", "hint": "请确认 frontend/index.html 存在"}
        )

    # ---- 健康检查 ----
    @app.get("/api/health")
    async def health():
        try:
            models = await _model_cache.get_models()
            cache_age = time.time() - _model_cache._last_update if _model_cache._last_update > 0 else None
            return {
                "status": "ok",
                "models": models,
                "default_model": default_model,
                "cache_age": cache_age
            }
        except Exception:
            return {"status": "error", "models": [], "default_model": default_model}

    @app.get("/api/health/detailed")
    async def health_detailed():
        return _health_checker.check_all()

    @app.get("/api/ready")
    async def readiness():
        ready, message = _health_checker.check_ready()
        if ready:
            return {"status": "ready", "message": message}
        return JSONResponse(status_code=503, content={"status": "not_ready", "message": message})

    @app.get("/api/live")
    async def liveness():
        if _health_checker.check_live():
            return {"status": "alive"}
        return JSONResponse(status_code=503, content={"status": "terminating"})

    # ---- 核心信息 ----
    @app.get("/api/core")
    async def get_core_info():
        return {
            "name": config.app_name,
            "version": config.app_version,
            "architecture": "鸿蒙分布式架构",
            "default_model": default_model,
            "status": "online"
        }

    # ---- 指标 ----
    @app.get("/metrics")
    async def metrics():
        if not PROMETHEUS_AVAILABLE:
            return PlainTextResponse(content="# Prometheus client not available", status_code=503)
        return PlainTextResponse(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # ---- 性能 ----
    @app.get("/api/performance")
    async def performance_stats(endpoint: Optional[str] = None):
        stats = _performance_tracker.get_stats(endpoint)
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)
        return {
            "requests": stats,
            "system": {
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available / (1024 * 1024),
                "cpu_percent": cpu
            },
            "cache": {
                "enabled": config.cache.response_cache_enabled,
                "entries": len(_response_cache._cache) if _response_cache.enabled else 0
            }
        }

    # ---- 认证 ----
    class AuthRequest(BaseModel):
        user_id: str = Field(..., min_length=1, max_length=100)
        api_key: str = Field(..., min_length=1)

    class AuthResponse(BaseModel):
        access_token: str
        token_type: str = "bearer"
        expires_in: int

    API_KEY_HASH = os.environ.get("GEMMA4_API_KEY_HASH", "")

    _generated_key: Optional[str] = None

    def _ensure_api_key() -> str:
        global _generated_key
        if API_KEY_HASH:
            return API_KEY_HASH
        if _generated_key is None:
            import secrets
            _generated_key = secrets.token_urlsafe(32)
            key_hash = hashlib.sha256(_generated_key.encode()).hexdigest()
            logger.warning(
                "============================================\n"
                "  安全警告: 未配置GEMMA4_API_KEY_HASH环境变量\n"
                "  系统已自动生成临时API密钥(仅本次有效):\n"
                "  密钥: %s\n"
                "  请设置GEMMA4_API_KEY_HASH=%s 到环境变量中\n"
                "============================================",
                _generated_key, key_hash,
            )
            return key_hash
        return hashlib.sha256(_generated_key.encode()).hexdigest()

    def _verify_api_key(api_key: str) -> bool:
        expected = _ensure_api_key()
        return hashlib.sha256(api_key.encode()).hexdigest() == expected

    @app.post("/api/auth/token", response_model=AuthResponse)
    async def get_auth_token(request: AuthRequest):
        if not JWT_AVAILABLE:
            raise HTTPException(status_code=503, detail="JWT服务不可用")
        if not _verify_api_key(request.api_key):
            raise HTTPException(status_code=401, detail="API密钥无效")
        token = _create_jwt_token(
            request.user_id, sec.jwt_secret, sec.jwt_algorithm, sec.jwt_expire_hours
        )
        return AuthResponse(access_token=token, expires_in=sec.jwt_expire_hours * 3600)

    # ---- 聊天 ----
    class ChatRequest(BaseModel):
        message: str = Field(..., min_length=1, max_length=32000)
        model: str = Field(default=default_model, max_length=100)

        @field_validator('message')
        @classmethod
        def sanitize_message(cls, v):
            dangerous = ['<script', 'javascript:', 'data:', 'vbscript:']
            v_lower = v.lower()
            for pattern in dangerous:
                if pattern in v_lower:
                    raise ValueError(f'消息包含不允许的内容: {pattern}')
            return v.strip()

    class ChatResponse(BaseModel):
        response: str
        model: str
        status: str

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest):
        model = request.model or default_model
        try:
            import ollama
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ollama.chat(
                    model=model,
                    messages=[
                        {'role': 'system', 'content': system_identity},
                        {'role': 'user', 'content': request.message}
                    ]
                )
            )
            content = response['message']['content']
            return ChatResponse(response=content, model=model, status="ok")
        except Exception as e:
            return ChatResponse(response=f"Error: {str(e)}", model=model, status="error")

    @app.post("/api/refresh-models")
    async def refresh_models():
        models = await _model_cache.refresh()
        return {"status": "ok", "models": models}

    @app.get("/api/versions")
    async def get_api_versions():
        return {
            "current_version": "v1",
            "api_version": config.app_version,
            "supported_versions": ["v1", "v2"],
            "deprecated_versions": []
        }

    # ---- Wiki/文档 ----
    _wiki_instance = None

    def _get_wiki():
        nonlocal _wiki_instance
        if _wiki_instance is None:
            from kairos.system.core.llm_wiki_compat import LLMWikiCompatLayer
            _wiki_instance = LLMWikiCompatLayer(chunk_size=256, chunk_overlap=30)
        return _wiki_instance

    ALLOWED_SOURCES = ["custom", "wiki", "document", "web", "markdown", "code"]

    class WikiAddRequest(BaseModel):
        title: str = Field(..., min_length=1, max_length=500)
        content: str = Field(..., min_length=1, max_length=500000)
        source: str = "custom"
        source_url: str = ""
        metadata: Dict[str, Any] = Field(default_factory=dict)

        @field_validator('source')
        @classmethod
        def validate_source(cls, v):
            if v not in ALLOWED_SOURCES:
                raise ValueError(f'无效的来源类型')
            return v

    class WikiQueryRequest(BaseModel):
        question: str = Field(..., min_length=1, max_length=2000)
        top_k: int = Field(default=5, ge=1, le=20)
        generate_answer: bool = True

    @app.post("/api/v1/documents")
    async def wiki_add_document(request: WikiAddRequest):
        from kairos.system.core.llm_wiki_compat import WikiSourceType
        try:
            source = WikiSourceType(request.source)
        except ValueError:
            source = WikiSourceType.CUSTOM
        wiki = _get_wiki()
        result = await wiki.add_document(
            title=request.title, content=request.content,
            source=source, source_url=request.source_url,
            metadata=request.metadata
        )
        if result.get("status") == "rejected_low_memory":
            raise HTTPException(status_code=503, detail="内存不足")
        return result

    @app.get("/api/v1/documents/{doc_id}")
    async def wiki_get_document(doc_id: str):
        wiki = _get_wiki()
        result = await wiki.get_document(doc_id)
        if not result:
            raise HTTPException(status_code=404, detail="文档不存在")
        return result

    @app.get("/api/v1/documents")
    async def wiki_list_documents(source_type: Optional[str] = None,
                                  limit: int = 20, offset: int = 0):
        from kairos.system.core.llm_wiki_compat import WikiSourceType
        st = None
        if source_type:
            try:
                st = WikiSourceType(source_type)
            except ValueError:
                pass
        wiki = _get_wiki()
        return wiki.list_documents(source_type=st, limit=limit, offset=offset)

    @app.post("/api/v1/query")
    async def wiki_query(request: WikiQueryRequest):
        wiki = _get_wiki()
        return await wiki.query(
            question=request.question,
            top_k=request.top_k,
            generate_answer=request.generate_answer
        )

    @app.get("/api/v1/search")
    async def wiki_search(q: str, limit: int = 5, source_type: Optional[str] = None):
        from kairos.system.core.llm_wiki_compat import WikiSourceType
        st = None
        if source_type:
            try:
                st = WikiSourceType(source_type)
            except ValueError:
                pass
        wiki = _get_wiki()
        return await wiki.search(query=q, limit=limit, source_type=st)

    @app.delete("/api/v1/documents/{doc_id}")
    async def wiki_delete_document(doc_id: str):
        wiki = _get_wiki()
        success = await wiki.delete_document(doc_id)
        if not success:
            raise HTTPException(status_code=404, detail="文档不存在")
        return {"status": "deleted", "doc_id": doc_id}

    @app.get("/api/v1/health")
    async def wiki_health():
        wiki = _get_wiki()
        return wiki.health_check()

    # ---- V2 API ----
    router_v2 = APIRouter(prefix="/api/v2", tags=["v2"])

    class ChatRequestV2(BaseModel):
        message: str = Field(..., min_length=1, max_length=32000)
        model: str = Field(default=default_model, max_length=100)
        stream: bool = Field(default=False)
        context: Optional[Dict[str, Any]] = Field(default=None)

        @field_validator('message')
        @classmethod
        def sanitize_message(cls, v):
            dangerous = ['<script', 'javascript:', 'data:', 'vbscript:']
            v_lower = v.lower()
            for pattern in dangerous:
                if pattern in v_lower:
                    raise ValueError(f'消息包含不允许的内容: {pattern}')
            return v.strip()

    class ChatResponseV2(BaseModel):
        response: str
        model: str
        status: str
        version: str = "v2"
        processing_time_ms: Optional[float] = None
        cached: bool = False

    @router_v2.get("/health")
    async def health_v2():
        return {
            "status": "ok", "version": "v2",
            "api_version": config.app_version,
            "features": ["streaming", "context", "caching"]
        }

    @router_v2.get("/core")
    async def get_core_info_v2():
        return {
            "name": config.app_name,
            "version": config.app_version,
            "api_version": config.app_version,
            "architecture": "鸿蒙分布式架构",
            "default_model": default_model,
            "status": "online",
            "features": {
                "rate_limiting": sec.rate_limit_enabled,
                "audit_logging": config.logging.audit_enabled,
                "signature_verification": sec.signature_enabled,
                "ip_filtering": sec.ip_whitelist_enabled or sec.ip_blacklist_enabled,
                "response_caching": config.cache.response_cache_enabled
            }
        }

    @router_v2.post("/chat", response_model=ChatResponseV2)
    async def chat_v2(request: ChatRequestV2):
        start_time = time.time()
        model = request.model or default_model

        cache_key = f"chat:{model}:{hashlib.md5(request.message.encode()).hexdigest()}"
        if config.cache.response_cache_enabled:
            cached = _response_cache.get(cache_key)
            if cached:
                return ChatResponseV2(
                    response=cached, model=model, status="ok",
                    processing_time_ms=(time.time() - start_time) * 1000, cached=True
                )

        try:
            import ollama
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ollama.chat(
                    model=model,
                    messages=[
                        {'role': 'system', 'content': system_identity},
                        {'role': 'user', 'content': request.message}
                    ]
                )
            )
            content = response['message']['content']
            if config.cache.response_cache_enabled:
                _response_cache.set(cache_key, content)
            return ChatResponseV2(
                response=content, model=model, status="ok",
                processing_time_ms=(time.time() - start_time) * 1000, cached=False
            )
        except Exception as e:
            return ChatResponseV2(
                response=f"Error: {str(e)}", model=model, status="error",
                processing_time_ms=(time.time() - start_time) * 1000
            )

    @router_v2.get("/models")
    async def list_models_v2():
        models = await _model_cache.get_models()
        return {
            "models": models, "default": default_model,
            "cache_age": time.time() - _model_cache._last_update if _model_cache._last_update > 0 else None
        }

    @router_v2.get("/cache/stats")
    async def cache_stats_v2():
        return {
            "enabled": config.cache.response_cache_enabled,
            "ttl": config.cache.response_cache_ttl,
            "entries": len(_response_cache._cache) if _response_cache.enabled else 0
        }

    @router_v2.delete("/cache")
    async def clear_cache_v2():
        _response_cache.clear()
        return {"status": "cleared"}

    app.include_router(router_v2)

    # ---- 方法论引擎API ----
    @app.get("/api/methodology/principles")
    async def list_principles(category: Optional[str] = None, module: Optional[str] = None):
        from kairos.system.methodology import get_methodology_engine, ThoughtCategory
        engine = get_methodology_engine()
        if category:
            try:
                cat = ThoughtCategory(category)
                principles = engine.get_by_category(cat)
            except ValueError:
                principles = list(engine._principles.values())
        elif module:
            principles = engine.get_by_module(module)
        else:
            principles = list(engine._principles.values())
        return {
            "total": len(principles),
            "principles": [
                {"id": p.id, "name": p.name, "category": p.category.value,
                 "essence": p.core_essence, "source": p.source,
                 "module": p.integration_module,
                 "effectiveness": p.effectiveness_score,
                 "activations": p.activation_count}
                for p in principles
            ]
        }

    @app.get("/api/methodology/search")
    async def search_principles(q: str, limit: int = 10):
        from kairos.system.methodology import get_methodology_engine
        engine = get_methodology_engine()
        results = engine.search(q, limit=limit)
        return {
            "query": q, "count": len(results),
            "results": [
                {"id": p.id, "name": p.name, "essence": p.core_essence,
                 "category": p.category.value, "relevance": p.effectiveness_score}
                for p in results
            ]
        }

    @app.post("/api/methodology/match")
    async def match_strategy(problem: str):
        from kairos.system.methodology import get_methodology_engine
        engine = get_methodology_engine()
        recommendations = engine.match_strategy(problem)
        return {
            "problem": problem, "count": len(recommendations),
            "recommendations": [
                {"principle_id": r.principle_id, "principle_name": r.principle_name,
                 "category": r.category.value, "relevance": r.relevance,
                 "reasoning": r.reasoning, "action_steps": r.action_steps,
                 "module_target": r.module_target}
                for r in recommendations
            ]
        }

    @app.post("/api/methodology/enhance")
    async def enhance_decision(decision: str):
        from kairos.system.methodology import get_methodology_engine
        engine = get_methodology_engine()
        result = engine.enhance_decision(decision)
        return {
            "original": result.original_decision,
            "enhanced": result.enhanced_decision,
            "applied_principles": result.applied_principles,
            "confidence_boost": result.confidence_boost,
            "risk_mitigations": result.risk_mitigations,
            "alternatives": result.alternative_options
        }

    @app.post("/api/methodology/contradiction")
    async def analyze_contradiction(situation: str):
        from kairos.system.methodology import get_methodology_engine
        engine = get_methodology_engine()
        return engine.analyze_contradiction(situation)

    @app.post("/api/methodology/persistent-war")
    async def persistent_war_strategy(challenge: str):
        from kairos.system.methodology import get_methodology_engine
        engine = get_methodology_engine()
        return engine.get_persistent_war_strategy(challenge)

    @app.get("/api/methodology/statistics")
    async def methodology_statistics():
        from kairos.system.methodology import get_methodology_engine
        engine = get_methodology_engine()
        return engine.get_statistics()

    # ============================================================
    # 工作记忆区 API 端点
    # ============================================================

    @app.post("/api/working-memory/records")
    async def create_interaction_record(request: Request):
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        body = await request.json()
        result = wm.create_record(
            customer_id=body.get("customer_id", ""),
            session_id=body.get("session_id", ""),
            dialogue_content=body.get("dialogue_content", ""),
            customer_needs=body.get("customer_needs", ""),
            system_response=body.get("system_response", ""),
            follow_ups=body.get("follow_ups"),
            category=body.get("category"),
            sentiment=body.get("sentiment"),
            tags=body.get("tags"),
            metadata=body.get("metadata")
        )
        return result

    @app.get("/api/working-memory/records/{record_id}")
    async def get_interaction_record(record_id: str):
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        result = wm.get_record(record_id)
        if not result:
            raise HTTPException(status_code=404, detail="交互记录不存在")
        return result

    @app.get("/api/working-memory/records")
    async def search_interaction_records(
        query: str = None,
        customer_id: str = None,
        category: str = None,
        sentiment: str = None,
        status: str = None,
        start_time: str = None,
        end_time: str = None,
        tags: str = None,
        limit: int = 20,
        offset: int = 0
    ):
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        tag_list = tags.split(",") if tags else None
        return wm.search_records(
            query=query, customer_id=customer_id,
            category=category, sentiment=sentiment,
            status=status, start_time=start_time,
            end_time=end_time, tags=tag_list,
            limit=limit, offset=offset
        )

    @app.put("/api/working-memory/records/{record_id}")
    async def update_interaction_record(record_id: str, request: Request):
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        body = await request.json()
        return wm.update_record(
            record_id=record_id,
            status=body.get("status"),
            satisfaction_score=body.get("satisfaction_score"),
            resolution_time_ms=body.get("resolution_time_ms"),
            follow_ups=body.get("follow_ups"),
            tags=body.get("tags"),
            metadata=body.get("metadata")
        )

    @app.delete("/api/working-memory/records/{record_id}")
    async def delete_interaction_record(record_id: str):
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        return wm.delete_record(record_id)

    @app.get("/api/working-memory/customers/{customer_id}/history")
    async def get_customer_history(customer_id: str, limit: int = 50):
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        return wm.get_customer_history(customer_id, limit)

    @app.post("/api/working-memory/experience/extract")
    async def extract_experience(request: Request):
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        return wm.extract_experience(
            since=body.get("since"),
            rule_types=body.get("rule_types")
        )

    @app.get("/api/working-memory/rules")
    async def get_experience_rules(
        rule_type: str = None,
        status: str = None,
        min_confidence: float = 0.0,
        tags: str = None,
        limit: int = 20
    ):
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        tag_list = tags.split(",") if tags else None
        return wm.get_rules(
            rule_type=rule_type, status=status,
            min_confidence=min_confidence, tags=tag_list,
            limit=limit
        )

    @app.get("/api/working-memory/rules/{rule_id}")
    async def get_experience_rule(rule_id: str):
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        result = wm.get_rule(rule_id)
        if not result:
            raise HTTPException(status_code=404, detail="经验规则不存在")
        return result

    @app.post("/api/working-memory/rules/{rule_id}/apply")
    async def apply_experience_rule(rule_id: str, request: Request):
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        body = await request.json()
        return wm.apply_rule(rule_id, body.get("success", True))

    @app.put("/api/working-memory/rules/{rule_id}")
    async def update_experience_rule(rule_id: str, request: Request):
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        body = await request.json()
        return wm.update_rule(
            rule_id=rule_id,
            status=body.get("status"),
            priority=body.get("priority"),
            tags=body.get("tags")
        )

    @app.delete("/api/working-memory/rules/{rule_id}")
    async def delete_experience_rule(rule_id: str):
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        return wm.delete_rule(rule_id)

    @app.post("/api/working-memory/rules/match")
    async def match_experience_rules(request: Request):
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        body = await request.json()
        return wm.match_rules(
            customer_needs=body.get("customer_needs", ""),
            category=body.get("category"),
            sentiment=body.get("sentiment"),
            limit=body.get("limit", 5)
        )

    @app.post("/api/working-memory/backups")
    async def create_working_memory_backup(request: Request):
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        return wm.create_backup(body.get("backup_type", "full"))

    @app.get("/api/working-memory/backups")
    async def list_working_memory_backups():
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        return wm.list_backups()

    @app.post("/api/working-memory/backups/{backup_name}/restore")
    async def restore_working_memory_backup(backup_name: str):
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        return wm.restore_backup(backup_name)

    @app.post("/api/working-memory/auto-backup/start")
    async def start_auto_backup(request: Request):
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        return wm.start_auto_backup(
            interval_hours=body.get("interval_hours", 24),
            backup_type=body.get("backup_type", "incremental")
        )

    @app.post("/api/working-memory/auto-backup/stop")
    async def stop_auto_backup():
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        return wm.stop_auto_backup()

    @app.post("/api/working-memory/auto-extraction/start")
    async def start_auto_extraction(request: Request):
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        return wm.start_auto_extraction(
            interval_hours=body.get("interval_hours", 6)
        )

    @app.post("/api/working-memory/auto-extraction/stop")
    async def stop_auto_extraction():
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        return wm.stop_auto_extraction()

    @app.get("/api/working-memory/statistics")
    async def working_memory_statistics():
        from kairos.system.memory.working_memory import get_working_memory
        wm = get_working_memory()
        return wm.get_statistics()

    # ============================================================
    # Agent优化模块 API 端点（源自Hermes Agent架构分析）
    # ============================================================

    @app.post("/api/agent/compress")
    async def compress_context(request: Request):
        from kairos.system.agent.context_compressor import ContextCompressor
        body = await request.json()
        messages = body.get("messages", [])
        mode = body.get("mode", "normal")
        config = body.get("config", {})
        compressor = ContextCompressor(config)
        result = compressor.compress(messages, mode)
        return result.to_dict()

    @app.post("/api/agent/compress/check")
    async def check_compression_needed(request: Request):
        from kairos.system.agent.context_compressor import ContextCompressor
        body = await request.json()
        messages = body.get("messages", [])
        config = body.get("config", {})
        compressor = ContextCompressor(config)
        needed, mode = compressor.should_compress(messages)
        return {"needed": needed, "mode": mode}

    @app.get("/api/agent/disclosure/catalog")
    async def disclosure_catalog(category: str = None, tags: str = None):
        from kairos.system.agent.progressive_disclosure import ProgressiveDisclosureEngine
        engine = ProgressiveDisclosureEngine()
        tag_list = tags.split(",") if tags else None
        return {"items": engine.list_catalog(category, tag_list)}

    @app.get("/api/agent/disclosure/summary/{item_id}")
    async def disclosure_summary(item_id: str):
        from kairos.system.agent.progressive_disclosure import ProgressiveDisclosureEngine
        engine = ProgressiveDisclosureEngine()
        result = engine.view_summary(item_id)
        if not result:
            raise HTTPException(status_code=404, detail="项目不存在")
        return result

    @app.get("/api/agent/disclosure/full/{item_id}")
    async def disclosure_full(item_id: str):
        from kairos.system.agent.progressive_disclosure import ProgressiveDisclosureEngine
        engine = ProgressiveDisclosureEngine()
        result = engine.view_full(item_id)
        if not result:
            raise HTTPException(status_code=404, detail="项目不存在")
        return result

    @app.post("/api/agent/disclosure/auto-select")
    async def disclosure_auto_select(request: Request):
        from kairos.system.agent.progressive_disclosure import ProgressiveDisclosureEngine, DisclosureLevel
        body = await request.json()
        engine = ProgressiveDisclosureEngine()
        context = body.get("context", {})
        level = DisclosureLevel(body.get("level", 1))
        max_items = body.get("max_items", 10)
        return {"items": engine.auto_select(context, level, max_items)}

    @app.post("/api/agent/provider/register")
    async def register_provider(request: Request):
        from kairos.system.agent.provider_fallback import get_provider_chain
        body = await request.json()
        chain = get_provider_chain()
        name = chain.add_provider(
            name=body.get("name", ""),
            url=body.get("url", ""),
            model=body.get("model", ""),
            api_key=body.get("api_key", ""),
            priority=body.get("priority", 1),
            timeout=body.get("timeout", 120.0)
        )
        return {"success": True, "name": name}

    @app.get("/api/agent/provider/statistics")
    async def provider_statistics():
        from kairos.system.agent.provider_fallback import get_provider_chain
        chain = get_provider_chain()
        return chain.get_statistics()

    @app.post("/api/agent/provider/call")
    async def provider_call(request: Request):
        from kairos.system.agent.provider_fallback import get_provider_chain
        body = await request.json()
        chain = get_provider_chain()
        result = chain.call_with_fallback(
            call_fn=lambda p: None,
            task_type=body.get("task_type", "chat")
        )
        return result.to_dict()

    @app.get("/api/agent/plugin/available")
    async def plugin_available(plugin_type: str = None):
        from kairos.system.agent.plugin_architecture import get_plugin_registry
        registry = get_plugin_registry()
        return registry.list_available(plugin_type)

    @app.get("/api/agent/plugin/active")
    async def plugin_active():
        from kairos.system.agent.plugin_architecture import get_plugin_registry
        registry = get_plugin_registry()
        return registry.list_active()

    @app.post("/api/agent/plugin/activate")
    async def plugin_activate(request: Request):
        from kairos.system.agent.plugin_architecture import get_plugin_registry
        body = await request.json()
        registry = get_plugin_registry()
        success = registry.activate_plugin(
            plugin_type=body.get("plugin_type", ""),
            name=body.get("name", ""),
            config=body.get("config", {})
        )
        return {"success": success}

    @app.get("/api/agent/plugin/statistics")
    async def plugin_statistics():
        from kairos.system.agent.plugin_architecture import get_plugin_registry
        registry = get_plugin_registry()
        return registry.get_statistics()

    @app.post("/api/agent/interrupt/{call_id}")
    async def interrupt_call(call_id: str):
        from kairos.system.agent.interruptible_call import InterruptibleAPICall
        caller = InterruptibleAPICall()
        result = caller.interrupt(call_id)
        return {"success": result}

    @app.get("/api/agent/interrupt/active")
    async def active_interrupts():
        from kairos.system.agent.interruptible_call import InterruptibleAPICall
        caller = InterruptibleAPICall()
        return {"active_calls": caller.get_active_calls()}

    # ---- Claude Code优化模块端点 ----

    @app.get("/api/agent/query-guard/{channel}")
    async def query_guard_status(channel: str):
        from kairos.system.agent.query_guard import get_query_guard_manager
        manager = get_query_guard_manager()
        guard = manager.get_guard(channel)
        return guard.get_snapshot()._asdict() if hasattr(guard.get_snapshot(), '_asdict') else {"channel": channel, "snapshot": guard.get_snapshot().__dict__}

    @app.get("/api/agent/query-guard/channels")
    async def query_guard_channels():
        from kairos.system.agent.query_guard import get_query_guard_manager
        manager = get_query_guard_manager()
        return {"channels": manager.list_channels(), "snapshots": {k: v.__dict__ for k, v in manager.get_all_snapshots().items()}}

    @app.post("/api/agent/query-guard/force-end-all")
    async def query_guard_force_end_all():
        from kairos.system.agent.query_guard import get_query_guard_manager
        manager = get_query_guard_manager()
        count = manager.force_end_all()
        return {"ended_count": count}

    @app.post("/api/agent/memory-taxonomy/evaluate")
    async def memory_taxonomy_evaluate(request: dict):
        from kairos.system.agent.memory_taxonomy import get_memory_taxonomy
        engine = get_memory_taxonomy()
        decision = engine.evaluate(request.get("content", ""), request.get("context", ""))
        return {
            "should_save": decision.should_save,
            "category": decision.category.value if decision.category else None,
            "reason": decision.reason,
            "derivable_issue": decision.derivable_issue,
            "suggested_content": decision.suggested_content,
        }

    @app.get("/api/agent/memory-taxonomy/types")
    async def memory_taxonomy_types():
        from kairos.system.agent.memory_taxonomy import get_memory_taxonomy, MEMORY_TYPE_SPECS
        engine = get_memory_taxonomy()
        specs = {}
        for cat, spec in MEMORY_TYPE_SPECS.items():
            specs[cat.value] = {
                "name": spec.name,
                "description": spec.description,
                "when_to_save": spec.when_to_save,
                "how_to_use": spec.how_to_use,
                "body_structure": spec.body_structure,
            }
        return specs

    @app.get("/api/agent/memory-taxonomy/statistics")
    async def memory_taxonomy_statistics():
        from kairos.system.agent.memory_taxonomy import get_memory_taxonomy
        engine = get_memory_taxonomy()
        return engine.get_statistics()

    @app.post("/api/agent/memory-truncation/truncate")
    async def memory_truncation_truncate(request: dict):
        from kairos.system.agent.memory_truncation import get_truncation_engine
        engine = get_truncation_engine()
        result = engine.truncate(request.get("content", ""))
        return result.to_dict()

    @app.post("/api/agent/memory-truncation/check-limits")
    async def memory_truncation_check_limits(request: dict):
        from kairos.system.agent.memory_truncation import get_truncation_engine
        engine = get_truncation_engine()
        return engine.check_limits(request.get("content", ""))

    @app.post("/api/agent/memory-truncation/check-drift")
    async def memory_truncation_check_drift(request: dict):
        from kairos.system.agent.memory_truncation import get_truncation_engine
        engine = get_truncation_engine()
        report = engine.check_drift(
            request.get("entry_name", ""),
            request.get("created_at", ""),
            request.get("last_verified"),
        )
        return report.to_dict()

    @app.get("/api/agent/memory-truncation/statistics")
    async def memory_truncation_statistics():
        from kairos.system.agent.memory_truncation import get_truncation_engine
        engine = get_truncation_engine()
        return engine.get_statistics()

    @app.post("/api/agent/retry/execute")
    async def retry_execute(request: dict):
        from kairos.system.agent.enterprise_retry import get_enterprise_retry, RetryMode, RetryConfig
        import time as _time
        import random as _random

        retry = get_enterprise_retry()
        mode = RetryMode(request.get("mode", "foreground"))
        config = RetryConfig(
            max_retries=request.get("max_retries", 3),
            mode=mode,
        )

        _SAFE_FUNCTIONS = {
            "noop": lambda: None,
            "timestamp": lambda: _time.time(),
            "random_int": lambda: _random.randint(0, 100),
            "hello": lambda: "hello",
        }

        func_name = request.get("function", "noop")
        if func_name not in _SAFE_FUNCTIONS:
            return {
                "success": False,
                "error": f"不允许的函数: {func_name}，可用函数: {list(_SAFE_FUNCTIONS.keys())}",
                "error_category": "SECURITY_VIOLATION",
            }
        fn = _SAFE_FUNCTIONS[func_name]
        result = retry.execute(fn, config)
        return result.to_dict()

    @app.get("/api/agent/retry/statistics")
    async def retry_statistics():
        from kairos.system.agent.enterprise_retry import get_enterprise_retry
        retry = get_enterprise_retry()
        return retry.get_statistics()

    @app.post("/api/agent/circular-buffer/add")
    async def circular_buffer_add(request: dict):
        from kairos.system.agent.circular_buffer import CircularBuffer
        buf = CircularBuffer(request.get("capacity", 100))
        items = request.get("items", [])
        buf.add_all(items)
        return {"added": len(items), "length": buf.length, "capacity": buf.capacity}

    @app.get("/api/agent/context-isolation/statistics")
    async def context_isolation_statistics():
        from kairos.system.agent.circular_buffer import get_agent_context_manager
        manager = get_agent_context_manager()
        return manager.get_statistics()

    @app.post("/api/agent/abort/create")
    async def abort_create(request: dict):
        from kairos.system.agent.abort_activity import get_abort_manager
        manager = get_abort_manager()
        ctrl = manager.create(
            controller_id=request.get("controller_id"),
            parent_id=request.get("parent_id"),
        )
        return {"controller_id": ctrl.id, "is_aborted": ctrl.is_aborted}

    @app.post("/api/agent/abort/{controller_id}")
    async def abort_controller(controller_id: str, request: dict = None):
        from kairos.system.agent.abort_activity import get_abort_manager
        manager = get_abort_manager()
        reason = (request or {}).get("reason", "API请求中止")
        success = manager.abort(controller_id, reason)
        return {"success": success, "controller_id": controller_id}

    @app.get("/api/agent/abort/active")
    async def abort_active():
        from kairos.system.agent.abort_activity import get_abort_manager
        manager = get_abort_manager()
        return {"active": [info.__dict__ for info in manager.list_active()]}

    @app.get("/api/agent/activity/state")
    async def activity_state():
        from kairos.system.agent.abort_activity import get_activity_manager
        manager = get_activity_manager()
        state = manager.get_state()
        return {
            "is_user_active": state.is_user_active,
            "is_cli_active": state.is_cli_active,
            "active_operation_count": state.active_operation_count,
            "user_idle_seconds": state.user_idle_seconds,
            "cli_active_seconds": state.cli_active_seconds,
        }

    @app.get("/api/agent/activity/statistics")
    async def activity_statistics():
        from kairos.system.agent.abort_activity import get_activity_manager
        manager = get_activity_manager()
        return manager.get_statistics()

    @app.get("/api/agent/optimization/health")
    async def optimization_health():
        from kairos.system.agent.optimization_center import get_optimization_center
        center = get_optimization_center()
        return center.health_check()

    @app.get("/api/agent/optimization/statistics")
    async def optimization_statistics():
        from kairos.system.agent.optimization_center import get_optimization_center
        center = get_optimization_center()
        return center.get_full_statistics()

    @app.get("/api/agent/optimization/config")
    async def optimization_config():
        from kairos.system.agent.optimization_center import get_optimization_center
        center = get_optimization_center()
        return center.config.snapshot()

    @app.post("/api/agent/optimization/config")
    async def optimization_config_set(request: dict):
        from kairos.system.agent.optimization_center import get_optimization_center
        center = get_optimization_center()
        key = request.get("key", "")
        value = request.get("value")
        if center.config.validate(key, value):
            center.config.set(key, value)
            return {"success": True, "key": key}
        return {"success": False, "error": "配置值验证失败"}

    @app.get("/api/agent/optimization/circuit-breakers")
    async def circuit_breakers():
        from kairos.system.agent.optimization_center import get_optimization_center
        center = get_optimization_center()
        return {
            "circuit_breakers": {
                name: cb.get_info()
                for name, cb in center._circuit_breakers.items()
            }
        }

    # ---- MaxKB优化模块端点 ----

    @app.post("/api/agent/workflow/run")
    async def workflow_run(request: dict):
        from kairos.system.agent.workflow_engine import Workflow, WorkflowManage, WorkflowMode
        wf_data = request.get("workflow", {})
        query = request.get("query", "")
        mode = request.get("mode", "application")
        wf = Workflow.from_dict(wf_data)
        manage = WorkflowManage(wf, WorkflowMode(mode))
        ctx = manage.run(query)
        return ctx.to_dict()

    @app.post("/api/agent/workflow/builder")
    async def workflow_builder(request: dict):
        from kairos.system.agent.workflow_engine import WorkflowBuilder
        builder = WorkflowBuilder()
        nodes = request.get("nodes", [])
        edges = request.get("edges", [])
        for n in nodes:
            builder.add_node(n.get("id", ""), n.get("type", ""), **n.get("kwargs", {}))
        for e in edges:
            builder.add_edge(e.get("source", ""), e.get("target", ""))
        if not nodes:
            builder.add_start()
        wf = builder.build()
        return {"nodes": len(wf.nodes), "edges": len(wf.edges)}

    @app.get("/api/agent/workflow/node-types")
    async def workflow_node_types():
        from kairos.system.agent.workflow_engine import NODE_TYPE_MAP, NodeType
        return {"node_types": [nt.value for nt in NodeType]}

    @app.post("/api/agent/search")
    async def hybrid_search(request: dict):
        from kairos.system.agent.hybrid_search import get_hybrid_search_engine
        engine = get_hybrid_search_engine()
        results = engine.search(
            query=request.get("query", ""),
            mode=request.get("mode", "blend"),
            top_k=request.get("top_k", 5),
            similarity=request.get("similarity", 0.6),
        )
        return {"results": [r.to_dict() for r in results]}

    @app.post("/api/agent/search/index")
    async def hybrid_search_index(request: dict):
        from kairos.system.agent.hybrid_search import get_hybrid_search_engine
        engine = get_hybrid_search_engine()
        success = engine.index(
            doc_id=request.get("doc_id", ""),
            content=request.get("content", ""),
            embedding=request.get("embedding"),
            metadata=request.get("metadata"),
        )
        return {"success": success}

    @app.get("/api/agent/search/statistics")
    async def hybrid_search_statistics():
        from kairos.system.agent.hybrid_search import get_hybrid_search_engine
        engine = get_hybrid_search_engine()
        return engine.get_statistics()

    @app.get("/api/agent/model/providers")
    async def model_providers():
        from kairos.system.agent.model_provider import get_model_registry
        registry = get_model_registry()
        return {"providers": registry.list_providers()}

    @app.get("/api/agent/model/capabilities")
    async def model_capabilities():
        from kairos.system.agent.model_provider import get_model_registry
        registry = get_model_registry()
        return registry.get_all_capabilities()

    @app.post("/api/agent/model/create")
    async def model_create(request: dict):
        from kairos.system.agent.model_provider import get_model_registry, ModelType, ModelCredential
        registry = get_model_registry()
        model_type = ModelType(request.get("model_type", "llm"))
        credential = ModelCredential(
            provider_name=request.get("provider", ""),
            api_key=request.get("api_key", ""),
            api_base=request.get("api_base", ""),
        )
        model = registry.create_model(
            request.get("provider", ""),
            model_type,
            request.get("model_name", ""),
            credential,
        )
        return {"success": True, "model": str(model)}

    @app.get("/api/agent/model/statistics")
    async def model_statistics():
        from kairos.system.agent.model_provider import get_model_registry
        registry = get_model_registry()
        return registry.get_statistics()

    @app.post("/api/agent/sandbox/execute")
    async def sandbox_execute(request: dict):
        from kairos.system.agent.enhancement import get_sandbox
        sandbox = get_sandbox()
        result = sandbox.execute(
            code=request.get("code", ""),
            context=request.get("context"),
            language=request.get("language", "python"),
        )
        return result.to_dict()

    @app.get("/api/agent/event-memory/events")
    async def event_memory_events():
        from kairos.system.agent.enhancement import get_event_memory
        em = get_event_memory()
        events = em.get_recent_events(20)
        return {"events": [{"type": e.event_type.value, "id": e.entry_id, "ts": e.timestamp} for e in events]}

    @app.post("/api/agent/openai/chat/completions")
    async def openai_chat_completions(request: dict):
        from kairos.system.agent.enhancement import get_openai_api, ChatCompletionRequest
        api = get_openai_api()
        req = ChatCompletionRequest.from_dict(request)
        resp = api.chat_completions(req)
        return resp.to_dict()

    @app.get("/api/agent/perf/cache/statistics")
    async def perf_cache_statistics():
        from kairos.system.agent.perf_infra import get_mem_cache
        cache = get_mem_cache()
        return cache.get_statistics()

    @app.post("/api/agent/perf/cache/clear")
    async def perf_cache_clear():
        from kairos.system.agent.perf_infra import get_mem_cache
        cache = get_mem_cache()
        cache.clear()
        return {"success": True}

    @app.get("/api/agent/perf/memory")
    async def perf_memory():
        from kairos.system.agent.perf_infra import get_memory_guard
        guard = get_memory_guard()
        return guard.check_memory()

    @app.post("/api/agent/perf/gc")
    async def perf_gc():
        from kairos.system.agent.perf_infra import get_memory_guard
        guard = get_memory_guard()
        return guard.force_gc()

    # ---- 前端静态文件挂载 ----
    frontend_dir = project_root / "frontend"
    if frontend_dir.exists():
        from fastapi.staticfiles import StaticFiles
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
        logger.info(f"前端静态文件已挂载: {frontend_dir}")


def _build_system_identity() -> str:
    """构建系统身份提示词"""
    try:
        from kairos.system.unified_initializer import get_core_loader
        loader = get_core_loader()
        identity = loader.get_system_identity()
        if identity:
            return f"""# {identity.fullName or identity.name}

## 核心身份
- 名称：{identity.name}
- 代号：{identity.shortName}
- 定位：{identity.archetype}
- 版本：v{identity.version}

## 核心指令
{chr(10).join(f'- {d}' for d in identity.coreDirectives)}

## 行为准则
{chr(10).join(f'- {p}' for p in identity.behavioralPrinciples)}

当用户称呼你时，请以"{identity.name}"的身份回应。"""
    except Exception:
        return "# 鸿蒙小雨\n智能集成系统核心 - 基于kairos system"


# ============================================================
# 启动入口
# ============================================================

app = create_app()


def run_server(host: str = None, port: int = None, reload: bool = False):
    """运行服务器"""
    from kairos.system.environment import get_config
    config = get_config()

    host = host or config.server.host
    port = port or config.server.port

    print("=" * 60)
    print(f"  {config.app_name} v{config.app_version}")
    print("  智能集成系统核心 - 基于kairos system")
    print("=" * 60)
    print(f"  环境: {config.environment.value}")
    print(f"  地址: http://{host}:{port}")
    print(f"  文档: http://{host}:{port}/docs")
    print("=" * 60)

    uvicorn.run(
        "system.bootstrap:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="鸿蒙小雨系统启动器")
    parser.add_argument("--host", default=None, help="服务器地址")
    parser.add_argument("--port", type=int, default=None, help="服务器端口")
    parser.add_argument("--reload", action="store_true", help="启用热重载")
    parser.add_argument("--env", choices=["development", "test", "production"], help="运行环境")

    args = parser.parse_args()

    if args.env:
        os.environ["HMYX_ENV"] = args.env
        os.environ["GEMMA4_ENV"] = args.env

    run_server(host=args.host, port=args.port, reload=args.reload)
