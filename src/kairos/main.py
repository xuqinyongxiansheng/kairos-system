import os
import sys
import asyncio
import time
import logging
from kairos.version import VERSION as SYSTEM_CORE_VERSION, SYSTEM_NAME as SYSTEM_CORE_NAME
import traceback
import hashlib
import secrets
import json
import threading
import hmac
import signal
import psutil
import ollama
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Callable, Set
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Depends, Security, APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from kairos.system.middleware import (
    RateLimiter, AuditLogger, ResponseCache, ModelCache,
    HealthChecker, IPAccessController, PerformanceTracker, SignatureVerifier
)

from kairos.system.middleware.input_validation import InputValidationMiddleware

from kairos.system.config import settings

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    jwt = None

try:
    from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = Histogram = Gauge = Info = None

ENV = settings.server.env
DEBUG = ENV == "development"
logger = logging.getLogger(__name__)
DEFAULT_MODEL = settings.ollama.default_model
MODEL_CACHE_TTL = settings.ollama.model_cache_ttl

METRICS_ENABLED = settings.api.metrics_enabled
METRICS_PATH = settings.api.metrics_path

ALLOWED_ORIGINS = settings.security.cors_origin_list
ALLOWED_HEADERS = ["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin", "X-Signature", "X-Timestamp", "X-Nonce"]

JWT_SECRET_KEY = settings.security.jwt_secret
JWT_ALGORITHM = settings.security.jwt_algorithm
JWT_EXPIRE_HOURS = settings.security.jwt_expire_hours
AUTH_ENABLED = settings.security.auth_enabled

if AUTH_ENABLED and not JWT_SECRET_KEY:
    if ENV == "production":
        raise RuntimeError(
            "生产环境已启用认证但未设置JWT密钥！"
            "请设置环境变量 GEMMA4_JWT_SECRET"
        )
    else:
        logger.warning("认证已启用但JWT密钥为空，开发环境将使用临时密钥")

RATE_LIMIT_ENABLED = settings.security.rate_limit_enabled
RATE_LIMIT_REQUESTS = settings.security.rate_limit_requests
RATE_LIMIT_WINDOW = settings.security.rate_limit_window

AUDIT_LOG_ENABLED = settings.security.audit_log_enabled
AUDIT_LOG_FILE = settings.security.audit_log_file

HTTPS_ENFORCE = settings.security.https_enforce

API_VERSION = settings.api.version
API_VERSIONS_SUPPORTED = ["v1", "v2"]
API_DEFAULT_VERSION = "v1"

SIGNATURE_ENABLED = settings.security.signature_enabled
SIGNATURE_SECRET = settings.security.signature_secret
SIGNATURE_MAX_SKEW = settings.security.signature_max_skew

IP_WHITELIST_ENABLED = settings.security.ip_whitelist_enabled
IP_BLACKLIST_ENABLED = settings.security.ip_blacklist_enabled
IP_WHITELIST: Set[str] = settings.security.ip_whitelist
IP_BLACKLIST: Set[str] = settings.security.ip_blacklist

TRUSTED_PROXY_ENABLED = settings.security.trusted_proxy_enabled
TRUSTED_PROXY_HEADER = settings.security.trusted_proxy_header

RESPONSE_CACHE_ENABLED = settings.security.response_cache_enabled
RESPONSE_CACHE_TTL = settings.security.response_cache_ttl

if not JWT_SECRET_KEY and AUTH_ENABLED:
    logger.critical("AUTH_ENABLED=True 但未设置 GEMMA4_JWT_SECRET！拒绝自动生成临时密钥，请设置环境变量后重启")
    raise RuntimeError("AUTH_ENABLED=True 但 GEMMA4_JWT_SECRET 未设置，应用拒绝启动")

if not SIGNATURE_SECRET and SIGNATURE_ENABLED:
    logger.critical("SIGNATURE_ENABLED=True 但未设置 GEMMA4_SIGNATURE_SECRET！请设置环境变量后重启")
    raise RuntimeError("SIGNATURE_ENABLED=True 但 GEMMA4_SIGNATURE_SECRET 未设置，应用拒绝启动")

if ENV == "production" and not AUTH_ENABLED:
    logger.critical("生产环境(ENV=production)必须启用认证！请设置 GEMMA4_AUTH_ENABLED=true")
    raise RuntimeError("生产环境必须启用认证，请设置 GEMMA4_AUTH_ENABLED=true 和 GEMMA4_JWT_SECRET")

PUBLIC_ENDPOINTS = {"/api/health", "/api/core", "/docs", "/redoc", "/openapi.json", "/api/v1/health", "/api/v2/health", "/metrics", "/api/ready", "/api/live"}
SKIP_RATE_LIMIT_ENDPOINTS = {"/api/health", "/api/v1/health", "/api/v2/health", "/api/core", "/metrics", "/api/ready", "/api/live"}
SKIP_SIGNATURE_ENDPOINTS = {"/api/health", "/api/v1/health", "/api/v2/health", "/api/core", "/docs", "/redoc", "/openapi.json", "/metrics", "/api/ready", "/api/live"}

security = HTTPBearer(auto_error=False)

_metrics_initialized = False

def _init_prometheus_metrics():
    global _metrics_initialized, REQUEST_COUNT, REQUEST_LATENCY, ACTIVE_REQUESTS, RATE_LIMIT_HITS, AUTH_FAILURES, CACHE_HITS, CACHE_MISSES
    
    if _metrics_initialized or not PROMETHEUS_AVAILABLE or not METRICS_ENABLED:
        return
    
    try:
        REQUEST_COUNT = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status']
        )
        REQUEST_LATENCY = Histogram(
            'http_request_duration_seconds',
            'HTTP request latency',
            ['method', 'endpoint'],
            buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
        )
        ACTIVE_REQUESTS = Gauge(
            'http_requests_in_progress',
            'HTTP requests in progress',
            ['method', 'endpoint']
        )
        RATE_LIMIT_HITS = Counter(
            'rate_limit_hits_total',
            'Total rate limit hits',
            ['client_ip']
        )
        AUTH_FAILURES = Counter(
            'auth_failures_total',
            'Total authentication failures',
            ['type']
        )
        CACHE_HITS = Counter(
            'cache_hits_total',
            'Total cache hits',
            ['cache_type']
        )
        CACHE_MISSES = Counter(
            'cache_misses_total',
            'Total cache misses',
            ['cache_type']
        )
        SYSTEM_INFO = Info('hmyx_system', 'System information')
        SYSTEM_INFO.info({
            'version': SYSTEM_CORE_VERSION,
            'environment': ENV,
            'debug': str(DEBUG)
        })
        _metrics_initialized = True
    except ValueError:
        pass

REQUEST_COUNT = REQUEST_LATENCY = ACTIVE_REQUESTS = RATE_LIMIT_HITS = AUTH_FAILURES = CACHE_HITS = CACHE_MISSES = None
_init_prometheus_metrics()

from kairos.system.llm_client import get_llm_client
from kairos.system.degradation import get_degradation_manager, ServiceLevel
from kairos.system.event_system import get_event_system, initialize_event_system, shutdown_event_system, EventType

health_checker = HealthChecker()

async def check_ollama_connection() -> bool:
    try:
        client = get_llm_client()
        models = await client.list()
        return models is not None
    except Exception:
        return False

def check_memory_available() -> bool:
    try:
        memory = psutil.virtual_memory()
        return memory.percent < 90
    except Exception:
        return True

health_checker.register_dependency("ollama", lambda: asyncio.run(check_ollama_connection()))
health_checker.register_dependency("memory", check_memory_available)

performance_tracker = PerformanceTracker()

shutdown_handlers = []

def register_shutdown_handler(handler: Callable):
    shutdown_handlers.append(handler)

async def graceful_shutdown():
    logger.info("开始优雅关闭...")
    health_checker.request_shutdown()
    
    for handler in shutdown_handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler()
            else:
                handler()
        except Exception as e:
            logger.error(f"关闭处理器执行失败: {e}")
    
    logger.info("优雅关闭完成")

_shutdown_requested = False

def signal_handler(signum, frame):
    global _shutdown_requested
    logger.info(f"收到信号 {signum}，准备关闭...")
    _shutdown_requested = True

if hasattr(signal, 'SIGTERM'):
    signal.signal(signal.SIGTERM, signal_handler)
if hasattr(signal, 'SIGBREAK'):
    signal.signal(signal.SIGBREAK, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

rate_limiter = RateLimiter(max_requests=RATE_LIMIT_REQUESTS, window_seconds=RATE_LIMIT_WINDOW)

audit_logger = AuditLogger(AUDIT_LOG_FILE, enabled=AUDIT_LOG_ENABLED)

signature_verifier = SignatureVerifier(SIGNATURE_SECRET, max_skew=SIGNATURE_MAX_SKEW)

ip_access_controller = IPAccessController(
    whitelist=IP_WHITELIST,
    blacklist=IP_BLACKLIST,
    whitelist_enabled=IP_WHITELIST_ENABLED,
    blacklist_enabled=IP_BLACKLIST_ENABLED
)

response_cache = ResponseCache(ttl=RESPONSE_CACHE_TTL, enabled=RESPONSE_CACHE_ENABLED)

# 鸿蒙小雨系统核心配置
SYSTEM_CORE_IDENTITY = """
# 鸿蒙小雨 - 智能集成系统核心

## 核心身份
- 名称：鸿蒙小雨
- 代号：HMXY-001
- 定位：智能机器人系统
- 架构：基于kairos system 开发
- 版本：v1.0.0

## 核心模块架构
┌─────────────────────────────────────┐
│         鸿蒙小雨系统核心            │
├─────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐          │
│  │感知模块 │  │认知模块 │          │
│  └────┬────┘  └────┬────┘          │
│       │            │               │
│  ┌────┴────────────┴────┐          │
│  │      决策引擎        │          │
│  └──────────┬───────────┘          │
│             │                      │
│  ┌──────────┴───────────┐          │
│  │      执行模块        │          │
│  └──────────────────────┘          │
└─────────────────────────────────────┘

## 核心能力矩阵
| 能力域 | 能力项 | 等级 |
|--------|--------|------|
| 感知 | 文本理解 | S |
| 感知 | 语义分析 | A |
| 认知 | 知识推理 | A |
| 认知 | 上下文记忆 | A |
| 决策 | 任务规划 | B |
| 决策 | 风险评估 | B |
| 执行 | 代码生成 | A |
| 执行 | 文档撰写 | A |

## 交互协议
1. 语言：优先使用中文，支持多语言
2. 风格：简洁专业，直击要点
3. 响应：结构化输出，便于理解
4. 反馈：主动确认，确保准确

## 安全机制
- 数据本地化处理，不上传云端
- 敏感信息自动脱敏
- 操作日志完整记录
- 权限分级管理

## 行为准则
1. 诚实：如实回答，不编造信息
2. 有益：提供有价值的帮助
3. 安全：避免有害内容输出
4. 尊重：尊重用户隐私和选择

当用户称呼你时，请以"鸿蒙小雨"的身份回应。
"""

HTTPS_ENABLED = settings.security.https_enabled
SSL_CERT_FILE = settings.security.ssl_cert
SSL_KEY_FILE = settings.security.ssl_key

model_cache = ModelCache(ttl=MODEL_CACHE_TTL)

@asynccontextmanager
async def _app_lifespan(app_instance):
    """应用生命周期管理 - 优雅关闭"""
    logger.info("应用启动中...")
    
    # 初始化事件系统
    event_system = get_event_system()
    await event_system.start()
    await event_system.emit(EventType.SYSTEM_STARTUP.value, {"version": SYSTEM_CORE_VERSION, "env": ENV})
    
    yield
    
    logger.info("应用关闭中，执行优雅关闭...")
    
    # 发送系统关闭事件
    await event_system.emit(EventType.SYSTEM_SHUTDOWN.value, {"reason": "graceful shutdown"})
    
    await graceful_shutdown()
    try:
        from kairos.services.bootstrap import get_bootstrap_state
        bs = get_bootstrap_state()
        bs.save_to_disk()
    except Exception:
        pass
    try:
        from kairos.services.cost_tracker import get_cost_tracker
        ct = get_cost_tracker()
        ct.save_session()
    except Exception:
        pass
    
    # 关闭事件系统
    await shutdown_event_system()
    logger.info("优雅关闭完成")

# FastAPI应用配置
app = FastAPI(
    title=f"{SYSTEM_CORE_NAME} - 智能集成系统核心 API",
    description="基于kairos system，支持本地大模型推理",
    version=SYSTEM_CORE_VERSION,
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
    openapi_url="/openapi.json" if DEBUG else None,
    lifespan=_app_lifespan,
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_id = f"err_{int(time.time() * 1000)}"
    logger.error(f"[{error_id}] 未处理异常: {type(exc).__name__}: {str(exc)}")
    if DEBUG:
        logger.debug(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "error": "内部服务器错误",
            "error_id": error_id,
            "detail": str(exc) if DEBUG else "请稍后重试或联系管理员"
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PUT", "OPTIONS"],
    allow_headers=ALLOWED_HEADERS,
    max_age=3600,
)

# 输入验证中间件
app.add_middleware(InputValidationMiddleware)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    if not METRICS_ENABLED or not PROMETHEUS_AVAILABLE:
        return await call_next(request)
    
    if request.url.path in [METRICS_PATH, "/api/ready", "/api/live"]:
        return await call_next(request)
    
    start_time = time.time()
    endpoint = request.url.path
    
    if ACTIVE_REQUESTS:
        ACTIVE_REQUESTS.labels(method=request.method, endpoint=endpoint).inc()
    
    try:
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        if REQUEST_COUNT:
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
                status=response.status_code
            ).inc()
        
        if REQUEST_LATENCY:
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=endpoint
            ).observe(duration)
        
        performance_tracker.record(endpoint, duration, response.status_code)
        
        return response
    finally:
        if ACTIVE_REQUESTS:
            ACTIVE_REQUESTS.labels(method=request.method, endpoint=endpoint).dec()

def _get_client_ip(request: Request) -> str:
    if TRUSTED_PROXY_ENABLED:
        forwarded = request.headers.get(TRUSTED_PROXY_HEADER, "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.middleware("http")
async def ip_access_middleware(request: Request, call_next):
    if not (IP_WHITELIST_ENABLED or IP_BLACKLIST_ENABLED):
        return await call_next(request)
    
    if request.url.path in PUBLIC_ENDPOINTS:
        return await call_next(request)
    
    client_ip = _get_client_ip(request)
    
    allowed, reason = ip_access_controller.is_allowed(client_ip)
    
    if not allowed:
        return JSONResponse(
            status_code=403,
            content={"error": "访问被拒绝", "detail": reason}
        )
    
    return await call_next(request)

@app.middleware("http")
async def signature_middleware(request: Request, call_next):
    if not SIGNATURE_ENABLED:
        return await call_next(request)
    
    if request.url.path in SKIP_SIGNATURE_ENDPOINTS:
        return await call_next(request)
    
    body = b""
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()
    
    valid, error = signature_verifier.verify(request, body)
    
    if not valid:
        return JSONResponse(
            status_code=401,
            content={"error": "签名验证失败", "detail": error}
        )
    
    return await call_next(request)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if not RATE_LIMIT_ENABLED:
        return await call_next(request)
    
    if request.url.path in SKIP_RATE_LIMIT_ENDPOINTS:
        return await call_next(request)
    
    client_ip = _get_client_ip(request)
    
    allowed, retry_after = rate_limiter.is_allowed(client_ip)
    
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": "请求过于频繁",
                "detail": f"请在{retry_after}秒后重试",
                "retry_after": retry_after
            },
            headers={"Retry-After": str(retry_after)}
        )
    
    return await call_next(request)

@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    response = await call_next(request)
    
    if AUDIT_LOG_ENABLED:
        user_id = None
        if hasattr(request.state, "user"):
            user_id = request.state.user.get("user_id")
        
        audit_logger.log_request(request, user_id=user_id, status_code=response.status_code)
    
    return response

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    if HTTPS_ENFORCE or (ENV == "production"):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response

@app.middleware("http")
async def https_redirect_middleware(request: Request, call_next):
    if HTTPS_ENFORCE:
        if request.url.scheme != "https":
            https_url = request.url.replace(scheme="https")
            return JSONResponse(
                status_code=301,
                headers={"Location": str(https_url)},
                content={"error": "请使用HTTPS访问"}
            )
    
    return await call_next(request)

def create_jwt_token(user_id: str, extra_claims: Dict[str, Any] = None) -> str:
    if not JWT_AVAILABLE:
        raise RuntimeError("PyJWT未安装，无法创建Token")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRE_HOURS),
        "jti": secrets.token_hex(16)
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    if not JWT_AVAILABLE:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    if not AUTH_ENABLED:
        return {"user_id": "anonymous", "authenticated": False}
    if not credentials:
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    token = credentials.credentials
    payload = verify_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="无效或过期的令牌")
    return {"user_id": payload.get("sub"), "authenticated": True, "claims": payload}

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if not AUTH_ENABLED:
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
    payload = verify_jwt_token(token)
    if not payload:
        return JSONResponse(
            status_code=401,
            content={"error": "认证失败", "detail": "令牌无效或已过期"}
        )
    request.state.user = payload
    return await call_next(request)

MAX_MESSAGE_LENGTH = 32000
MAX_CONTENT_LENGTH = 500000
MAX_QUESTION_LENGTH = 2000
MAX_QUERY_LENGTH = 500
ALLOWED_SOURCES = ["custom", "wiki", "document", "web", "markdown", "code"]

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    model: str = Field(default=DEFAULT_MODEL, max_length=100)
    
    @field_validator('message')
    @classmethod
    def sanitize_message(cls, v):
        dangerous_patterns = ['<script', 'javascript:', 'data:', 'vbscript:']
        v_lower = v.lower()
        for pattern in dangerous_patterns:
            if pattern in v_lower:
                raise ValueError(f'消息包含不允许的内容: {pattern}')
        return v.strip()
    
    @field_validator('model')
    @classmethod
    def validate_model(cls, v):
        if not v or not v.replace(':', '').replace('-', '').replace('_', '').isalnum():
            raise ValueError('模型名称格式无效')
        return v

class ChatResponse(BaseModel):
    response: str
    model: str
    status: str

class HealthResponse(BaseModel):
    status: str
    models: List[str]
    default_model: str
    cache_age: Optional[float] = None

class SystemCoreResponse(BaseModel):
    name: str
    version: str
    architecture: str
    default_model: str
    status: str

class WikiAddRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1, max_length=MAX_CONTENT_LENGTH)
    source: str = "custom"
    source_url: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('source')
    @classmethod
    def validate_source(cls, v):
        if v not in ALLOWED_SOURCES:
            raise ValueError(f'无效的来源类型，允许: {", ".join(ALLOWED_SOURCES)}')
        return v
    
    @field_validator('source_url')
    @classmethod
    def validate_url(cls, v):
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('URL必须以http://或https://开头')
        return v
    
    @field_validator('metadata')
    @classmethod
    def validate_metadata(cls, v):
        if len(str(v)) > 5000:
            raise ValueError('元数据过大，最大5000字符')
        return v

class WikiQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=MAX_QUESTION_LENGTH)
    top_k: int = Field(default=5, ge=1, le=20)
    generate_answer: bool = True
    
    @field_validator('question')
    @classmethod
    def sanitize_question(cls, v):
        return v.strip()

class WikiSearchRequest(BaseModel):
    q: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH)
    limit: int = Field(default=5, ge=1, le=50)
    source_type: Optional[str] = None
    
    @field_validator('source_type')
    @classmethod
    def validate_source_type(cls, v):
        if v and v not in ALLOWED_SOURCES:
            raise ValueError(f'无效的来源类型')
        return v

class AuthRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    api_key: str = Field(..., min_length=1)

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

_wiki_instance = None

def _get_wiki():
    global _wiki_instance
    if _wiki_instance is None:
        from kairos.system.core.llm_wiki_compat import LLMWikiCompatLayer
        _wiki_instance = LLMWikiCompatLayer(chunk_size=256, chunk_overlap=30)
    return _wiki_instance

API_KEY_HASH = settings.security.api_key_hash

def _verify_api_key(api_key: str) -> bool:
    if not API_KEY_HASH:
        logger.error("未设置 GEMMA4_API_KEY_HASH 环境变量，API密钥验证不可用")
        return False
    return hashlib.sha256(api_key.encode()).hexdigest() == API_KEY_HASH

@app.get("/")
async def root():
    """根路径 - 显示API欢迎页面"""
    from fastapi.responses import HTMLResponse
    html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{SYSTEM_CORE_NAME} v{SYSTEM_CORE_VERSION}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; color: #fff; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 40px 20px; }}
        .header {{ text-align: center; margin-bottom: 40px; }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; background: linear-gradient(90deg, #00d4ff, #7b2cbf); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .header .version {{ color: #888; font-size: 1.1em; }}
        .header .brand {{ color: #ffd700; margin-top: 10px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; margin-bottom: 40px; }}
        .stat-card {{ background: rgba(255,255,255,0.1); border-radius: 12px; padding: 20px; text-align: center; }}
        .stat-card .number {{ font-size: 2em; font-weight: bold; color: #00d4ff; }}
        .stat-card .label {{ color: #aaa; font-size: 0.9em; margin-top: 5px; }}
        .section {{ background: rgba(255,255,255,0.05); border-radius: 12px; padding: 25px; margin-bottom: 20px; }}
        .section h2 {{ color: #00d4ff; margin-bottom: 15px; font-size: 1.3em; }}
        .endpoint-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 10px; }}
        .endpoint {{ display: flex; align-items: center; padding: 10px 15px; background: rgba(0,0,0,0.2); border-radius: 8px; }}
        .endpoint .method {{ color: #4ade80; font-weight: bold; width: 50px; }}
        .endpoint .path {{ color: #fff; font-family: monospace; }}
        .endpoint a {{ color: inherit; text-decoration: none; }}
        .endpoint a:hover {{ color: #00d4ff; }}
        .footer {{ text-align: center; margin-top: 40px; color: #666; }}
        .chat-btn {{ display: inline-block; background: linear-gradient(90deg, #00d4ff, #7b2cbf); color: #fff; padding: 15px 40px; border-radius: 30px; text-decoration: none; font-size: 1.2em; font-weight: 600; margin: 20px 0; transition: transform 0.2s, box-shadow 0.2s; }}
        .chat-btn:hover {{ transform: translateY(-2px); box-shadow: 0 10px 30px rgba(0,212,255,0.3); }}
        .chat-section {{ text-align: center; margin: 30px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 {SYSTEM_CORE_NAME}</h1>
            <div class="version">v{SYSTEM_CORE_VERSION} - 生产就绪</div>
            <div class="brand">✨ 世纪星出品</div>
        </div>
        <div class="chat-section">
            <a href="/chat" class="chat-btn">💬 开始对话</a>
            <p style="color: #888; margin-top: 10px;">或使用 CLI: <code style="background: rgba(0,0,0,0.3); padding: 2px 8px; border-radius: 4px;">python cli_chat.py</code></p>
        </div>
        <div class="stats">
            <div class="stat-card"><div class="number">22</div><div class="label">服务模块</div></div>
            <div class="stat-card"><div class="number">92</div><div class="label">API端点</div></div>
            <div class="stat-card"><div class="number">16</div><div class="label">安全机制</div></div>
            <div class="stat-card"><div class="number">95%</div><div class="label">功能覆盖</div></div>
        </div>
        <div class="section">
            <h2>📡 核心端点</h2>
            <div class="endpoint-grid">
                <div class="endpoint"><span class="method">GET</span><a href="/api/health"><span class="path">/api/health</span></a></div>
                <div class="endpoint"><span class="method">GET</span><a href="/api/core"><span class="path">/api/core</span></a></div>
                <div class="endpoint"><span class="method">GET</span><a href="/docs"><span class="path">/docs</span></a></div>
                <div class="endpoint"><span class="method">GET</span><a href="/metrics"><span class="path">/metrics</span></a></div>
            </div>
        </div>
        <div class="section">
            <h2>💬 对话服务</h2>
            <div class="endpoint-grid">
                <div class="endpoint"><span class="method">GET</span><a href="/chat"><span class="path">/chat</span> - Web聊天界面</a></div>
                <div class="endpoint"><span class="method">POST</span><span class="path">/api/chat</span></div>
                <div class="endpoint"><span class="method">POST</span><span class="path">/api/chat/stream</span></div>
                <div class="endpoint"><span class="method">GET</span><a href="/api/models"><span class="path">/api/models</span></a></div>
            </div>
        </div>
        <div class="section">
            <h2>🧠 团队协作模块</h2>
            <div class="endpoint-grid">
                <div class="endpoint"><span class="method">GET</span><a href="/api/services/team-memory/keys"><span class="path">/api/services/team-memory/keys</span></a></div>
                <div class="endpoint"><span class="method">GET</span><a href="/api/services/dream/status"><span class="path">/api/services/dream/status</span></a></div>
                <div class="endpoint"><span class="method">GET</span><a href="/api/services/bridge/status"><span class="path">/api/services/bridge/status</span></a></div>
            </div>
        </div>
        <div class="section">
            <h2>⚙️ 系统服务</h2>
            <div class="endpoint-grid">
                <div class="endpoint"><span class="method">GET</span><a href="/api/services/commands"><span class="path">/api/services/commands</span></a></div>
                <div class="endpoint"><span class="method">GET</span><a href="/api/services/tools"><span class="path">/api/services/tools</span></a></div>
                <div class="endpoint"><span class="method">GET</span><a href="/api/services/sessions"><span class="path">/api/services/sessions</span></a></div>
                <div class="endpoint"><span class="method">GET</span><a href="/api/services/bootstrap/state"><span class="path">/api/services/bootstrap/state</span></a></div>
            </div>
        </div>
        <div class="footer">
            <p>基于 Ollama + Gemma4 的智能集成系统 | 对标 Claude Code 核心架构</p>
        </div>
    </div>
</body>
</html>'''
    return HTMLResponse(content=html_content)

@app.get("/metrics")
async def metrics():
    if not PROMETHEUS_AVAILABLE:
        return PlainTextResponse(
            content="# Prometheus client not available",
            status_code=503
        )
    return PlainTextResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

from kairos.routers import (
    agent_router,
    chat_router,
    enhanced_router,
    health_router,
    services_router,
    wiki_router,
    auth_router,
    core_router,
    events_router
)
# from routers.crewai import router as crewai_router
from kairos.skills.local_service.router import router as skills_router
from kairos.skills.local_service.stv_router import router as stv_router
from kairos.skills.local_service.clawbot_router import router as clawbot_router
from kairos.routers.health import init_health_deps
from kairos.routers.chat import init_chat_deps
from kairos.routers.services import init_service_deps
from kairos.routers.agent import init_agent_deps

init_health_deps(health_checker, model_cache)
init_chat_deps(ollama, SYSTEM_CORE_IDENTITY, DEFAULT_MODEL, response_cache)

def _init_services():
    try:
        from kairos.services.commands import CommandRegistry, CommandDispatcher
        from kairos.services.commands.builtin import register_builtin_commands
        from kairos.services.tools import get_tool_registry
        from kairos.services.tools.builtin import register_builtin_tools

        cmd_registry = CommandRegistry()
        register_builtin_commands(cmd_registry)

        cmd_dispatcher = CommandDispatcher(cmd_registry)
        cmd_dispatcher.set_context("registry", cmd_registry)
        cmd_dispatcher.set_context("current_model", DEFAULT_MODEL)

        async def _llm_chat_fn(prompt: str, model: str = None) -> str:
            try:
                m = model or DEFAULT_MODEL
                messages = []
                if SYSTEM_CORE_IDENTITY:
                    messages.append({'role': 'system', 'content': SYSTEM_CORE_IDENTITY})
                messages.append({'role': 'user', 'content': prompt})
                
                # 检查服务级别
                degradation_manager = get_degradation_manager()
                service_level = await degradation_manager.evaluate_service_level()
                
                if service_level != ServiceLevel.FULL:
                    return degradation_manager.get_fallback_response(prompt)
                
                client = get_llm_client()
                response = await client.chat(model=m, messages=messages)
                content = response['message']['content']

                try:
                    from kairos.services.token_tracker import get_token_tracker
                    from kairos.services.cost_tracker import get_cost_tracker
                    tt = get_token_tracker()
                    ct = get_cost_tracker()
                    prompt_eval = response.get('prompt_eval_count', 0) or 0
                    eval_count = response.get('eval_count', 0) or 0
                    if prompt_eval or eval_count:
                        tt.record_usage(m, prompt_eval, eval_count)
                        ct.record_usage(m, prompt_eval, eval_count)
                except Exception:
                    pass

                return content
            except Exception as e:
                # 降级处理
                degradation_manager = get_degradation_manager()
                await degradation_manager.evaluate_service_level()
                fallback = degradation_manager.get_fallback_response(prompt)
                if fallback:
                    return fallback
                return f"LLM 调用失败: {str(e)}"

        cmd_dispatcher.set_llm_chat_fn(_llm_chat_fn)

        tool_registry = get_tool_registry()
        register_builtin_tools(tool_registry)

        init_service_deps(cmd_registry, cmd_dispatcher, tool_registry)

        try:
            from kairos.services.bootstrap import get_bootstrap_state
            bs = get_bootstrap_state()
            bs.initialize()
            bs.load_from_disk()
        except Exception as e:
            logger.warning(f"Bootstrap 状态初始化跳过: {e}")

        try:
            from kairos.services.auto_classifier import get_auto_classifier
            ac = get_auto_classifier()
            ac._chat_fn = _llm_chat_fn
        except Exception as e:
            logger.warning(f"自动分类器初始化跳过: {e}")

        try:
            from kairos.services.cost_tracker import get_cost_tracker
            ct = get_cost_tracker()
            ct.restore_session()
        except Exception as e:
            logger.warning(f"成本追踪恢复跳过: {e}")

        try:
            from kairos.services.team_memory import get_team_memory_service
            tms = get_team_memory_service()
            logger.info(f"团队记忆同步服务就绪: {len(tms.get_all_keys())} 个记忆键")
        except Exception as e:
            logger.warning(f"团队记忆同步初始化跳过: {e}")

        try:
            from kairos.services.auto_dream import get_auto_dream_service
            ds = get_auto_dream_service()
            ds.set_chat_fn(_llm_chat_fn)
            logger.info("自动梦境服务就绪")
        except Exception as e:
            logger.warning(f"自动梦境初始化跳过: {e}")

        try:
            from kairos.services.bridge_system import get_bridge_server
            bs = get_bridge_server()
            logger.info("桥接系统服务就绪")
        except Exception as e:
            logger.warning(f"桥接系统初始化跳过: {e}")

        logger.info(f"服务模块初始化完成: {cmd_registry.command_count} 个命令, {tool_registry.tool_count} 个工具")
    except Exception as e:
        logger.error(f"服务模块初始化失败: {e}")

_init_services()

try:
    from kairos.routers.agent import init_agent_deps
    init_agent_deps(SYSTEM_CORE_IDENTITY, DEFAULT_MODEL)
except Exception as e:
    logger.warning(f"Agent 模块初始化跳过: {e}")

app.include_router(auth_router)
app.include_router(core_router)
app.include_router(events_router)
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(wiki_router)
app.include_router(agent_router)
# app.include_router(crewai_router)
app.include_router(services_router)

# 增强功能路由（类人思考/事实核查/任务规划/自进化/四层记忆）
try:
    app.include_router(enhanced_router)
    logger.info("增强功能路由已注册 (/api/enhanced/*)")
except Exception as e:
    logger.warning(f"增强功能路由注册跳过: {e}")

# 技能服务路由（claude-mem/agency-swarm/minimax 本地大模型服务）
try:
    app.include_router(skills_router)
    logger.info("技能服务路由已注册 (/api/skills/*)")
except Exception as e:
    logger.warning(f"技能服务路由注册跳过: {e}")

# 语音识别+视觉VoLo技能路由
try:
    app.include_router(stv_router)
    logger.info("语音+视觉技能路由已注册 (/api/skills/stt/*, /api/skills/vision/*)")
except Exception as e:
    logger.warning(f"语音+视觉技能路由注册跳过: {e}")

# ClawBot微信通道路由
try:
    app.include_router(clawbot_router)
    logger.info("ClawBot微信通道路由已注册 (/api/skills/clawbot/*)")
except Exception as e:
    logger.warning(f"ClawBot微信通道路由注册跳过: {e}")

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    """聊天界面页面"""
    chat_html = os.path.join(STATIC_DIR, "chat.html")
    if os.path.exists(chat_html):
        with open(chat_html, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>聊天页面未找到</h1><p>请访问 <a href='/docs'>/docs</a> 查看API文档</p>")

# 事件系统端点
@app.get("/api/events")
async def get_events(limit: int = 100):
    """获取事件历史"""
    event_system = get_event_system()
    events = event_system.get_event_history(limit)
    return {
        "events": events,
        "count": len(events),
        "timestamp": time.time()
    }

@app.get("/api/events/stats")
async def get_event_stats():
    """获取事件统计"""
    event_system = get_event_system()
    stats = event_system.get_statistics()
    return {
        "stats": stats,
        "timestamp": time.time()
    }

@app.get("/api/events/types")
async def get_event_types():
    """获取事件类型"""
    event_system = get_event_system()
    event_types = [e.value for e in EventType]
    registered = event_system.get_registered_events()
    return {
        "event_types": event_types,
        "registered_events": registered,
        "timestamp": time.time()
    }

@app.get("/api/events/health")
async def event_system_health():
    """事件系统健康检查"""
    event_system = get_event_system()
    status = event_system.get_status()
    return {
        "status": status,
        "timestamp": time.time()
    }

@app.post("/api/events/test")
async def test_event_system():
    """测试事件系统"""
    event_system = get_event_system()
    await event_system.emit(EventType.SYSTEM_WARNING.value, {"message": "Test event", "level": "info"})
    return {
        "message": "Test event emitted",
        "timestamp": time.time()
    }

if __name__ == "__main__":
    print("=" * 60)
    print(f"  {SYSTEM_CORE_NAME} v{SYSTEM_CORE_VERSION}")
    print("  智能集成系统核心 - 基于kairos system")
    print("=" * 60)
    print(f"  Environment: {ENV}")
    print(f"  Debug mode: {DEBUG}")
    print(f"  Default model: {DEFAULT_MODEL}")
    print(f"  Model cache TTL: {MODEL_CACHE_TTL}s")
    print(f"  HTTPS enabled: {HTTPS_ENABLED}")
    print(f"  Docs endpoint: {'enabled' if DEBUG else 'disabled'}")
    print("=" * 60)
    
    if HTTPS_ENABLED and SSL_CERT_FILE and SSL_KEY_FILE:
        uvicorn.run(
            app,
            host=settings.server.host,
            port=8080,  # 修改端口为 8080
            ssl_certfile=SSL_CERT_FILE,
            ssl_keyfile=SSL_KEY_FILE
        )
    else:
        uvicorn.run(
            app,
            host=settings.server.host,
            port=8080,  # 修改端口为 8080
        )
