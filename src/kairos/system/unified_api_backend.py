"""
import logging
统一API后端系统 - 整合CLI-Anything的API封装模式
logger = logging.getLogger("unified_api_backend")

设计模式来源:
- ollama_backend.py: 统一HTTP方法封装
- novita_backend.py: API密钥管理
- dify_workflow_backend.py: 工作流API

核心特性:
1. 统一的HTTP方法封装 (GET/POST/DELETE/PUT/PATCH/STREAM)
2. 自动重试和超时处理
3. 连接池管理
4. 统一错误处理
5. 请求/响应拦截器
6. 认证管理
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Optional, Union
from urllib.parse import urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class HTTPMethod(Enum):
    """HTTP方法枚举"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class AuthType(Enum):
    """认证类型枚举"""
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    BASIC = "basic"
    CUSTOM = "custom"


@dataclass
class APIConfig:
    """API配置"""
    base_url: str
    auth_type: AuthType = AuthType.NONE
    api_key: Optional[str] = None
    api_key_header: str = "X-API-Key"
    username: Optional[str] = None
    password: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_backoff_factor: float = 0.5
    pool_connections: int = 10
    pool_maxsize: int = 10
    default_headers: Dict[str, str] = field(default_factory=dict)
    verify_ssl: bool = True


@dataclass
class APIResponse:
    """API响应封装"""
    success: bool
    status_code: int
    data: Any
    headers: Dict[str, str]
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    elapsed_time: float = 0.0
    from_cache: bool = False


@dataclass
class RequestInterceptor:
    """请求拦截器"""
    name: str
    before_request: Optional[Callable[[Dict], Dict]] = None
    after_response: Optional[Callable[[APIResponse], APIResponse]] = None
    on_error: Optional[Callable[[Exception], None]] = None


class UnifiedAPIBackend:
    """
    统一API后端系统
    
    整合了CLI-Anything中多个后端模块的设计模式:
    - 统一的HTTP方法封装
    - 自动重试机制
    - 连接池管理
    - 请求/响应拦截器
    - 认证管理
    """
    
    _instances: Dict[str, 'UnifiedAPIBackend'] = {}
    _lock = threading.Lock()
    
    def __new__(cls, name: str = "default", config: Optional[APIConfig] = None):
        """单例模式 - 每个名称一个实例"""
        with cls._lock:
            if name not in cls._instances:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instances[name] = instance
            return cls._instances[name]
    
    def __init__(self, name: str = "default", config: Optional[APIConfig] = None):
        if self._initialized:
            return
        
        self.name = name
        self.config = config or APIConfig(base_url="")
        self._session: Optional[requests.Session] = None
        self._interceptors: List[RequestInterceptor] = []
        self._request_count = 0
        self._error_count = 0
        self._initialized = True
        self._setup_session()
    
    def _setup_session(self):
        """设置请求会话和连接池"""
        self._session = requests.Session()
        
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.retry_backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST", "PATCH"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=self.config.pool_connections,
            pool_maxsize=self.config.pool_maxsize
        )
        
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)
        
        default_headers = {
            "User-Agent": "UnifiedAPIBackend/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        default_headers.update(self.config.default_headers)
        self._session.headers.update(default_headers)
    
    def _build_url(self, endpoint: str) -> str:
        """构建完整URL"""
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        return urljoin(self.config.base_url.rstrip("/") + "/", endpoint.lstrip("/"))
    
    def _build_auth_headers(self) -> Dict[str, str]:
        """构建认证头"""
        headers = {}
        
        if self.config.auth_type == AuthType.API_KEY and self.config.api_key:
            headers[self.config.api_key_header] = self.config.api_key
        elif self.config.auth_type == AuthType.BEARER and self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        elif self.config.auth_type == AuthType.BASIC:
            import base64
            if self.config.username and self.config.password:
                credentials = base64.b64encode(
                    f"{self.config.username}:{self.config.password}".encode()
                ).decode()
                headers["Authorization"] = f"Basic {credentials}"
        
        return headers
    
    def _apply_interceptors_before(self, request_config: Dict) -> Dict:
        """应用请求前拦截器"""
        for interceptor in self._interceptors:
            if interceptor.before_request:
                request_config = interceptor.before_request(request_config)
        return request_config
    
    def _apply_interceptors_after(self, response: APIResponse) -> APIResponse:
        """应用响应后拦截器"""
        for interceptor in self._interceptors:
            if interceptor.after_response:
                response = interceptor.after_response(response)
        return response
    
    def _handle_error(self, e: Exception, method: str, url: str) -> APIResponse:
        """处理错误"""
        self._error_count += 1
        
        for interceptor in self._interceptors:
            if interceptor.on_error:
                try:
                    interceptor.on_error(e)
                except Exception:
                    logger.debug(f"忽略异常: interceptor.on_error(e)", exc_info=True)
                    pass
        
        error_message = str(e)
        error_type = type(e).__name__
        
        if isinstance(e, requests.exceptions.ConnectionError):
            error_message = f"无法连接到 {self.config.base_url}: {e}"
        elif isinstance(e, requests.exceptions.Timeout):
            error_message = f"请求超时: {method} {url}"
        elif isinstance(e, requests.exceptions.HTTPError):
            error_message = f"HTTP错误: {e}"
        
        return APIResponse(
            success=False,
            status_code=0,
            data=None,
            headers={},
            error_message=error_message,
            error_type=error_type
        )
    
    def add_interceptor(self, interceptor: RequestInterceptor):
        """添加拦截器"""
        self._interceptors.append(interceptor)
    
    def remove_interceptor(self, name: str):
        """移除拦截器"""
        self._interceptors = [i for i in self._interceptors if i.name != name]
    
    def request(
        self,
        method: HTTPMethod,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[int] = None,
        **kwargs
    ) -> APIResponse:
        """
        发送HTTP请求
        
        Args:
            method: HTTP方法
            endpoint: API端点
            data: 请求体数据
            params: 查询参数
            headers: 额外请求头
            timeout: 超时时间
            
        Returns:
            APIResponse对象
        """
        url = self._build_url(endpoint)
        timeout = timeout or self.config.timeout
        
        request_config = {
            "method": method.value,
            "url": url,
            "data": data,
            "params": params,
            "headers": headers or {},
            "timeout": timeout
        }
        
        request_config = self._apply_interceptors_before(request_config)
        
        auth_headers = self._build_auth_headers()
        final_headers = {**self._session.headers, **auth_headers, **request_config["headers"]}
        
        start_time = time.time()
        self._request_count += 1
        
        try:
            response = self._session.request(
                method=method.value,
                url=url,
                json=request_config["data"] if method != HTTPMethod.GET else None,
                data=request_config["data"] if method == HTTPMethod.GET else None,
                params=request_config["params"],
                headers=final_headers,
                timeout=request_config["timeout"],
                verify=self.config.verify_ssl,
                **kwargs
            )
            
            elapsed_time = time.time() - start_time
            
            if response.status_code >= 400:
                response.raise_for_status()
            
            content_type = response.headers.get("content-type", "")
            
            if response.status_code == 204 or not response.content:
                result_data = {"status": "ok"}
            elif "application/json" in content_type:
                result_data = response.json()
            else:
                result_data = {"status": "ok", "message": response.text.strip()}
            
            api_response = APIResponse(
                success=True,
                status_code=response.status_code,
                data=result_data,
                headers=dict(response.headers),
                elapsed_time=elapsed_time
            )
            
            return self._apply_interceptors_after(api_response)
            
        except Exception as e:
            return self._handle_error(e, method.value, url)
    
    def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> APIResponse:
        """GET请求"""
        return self.request(HTTPMethod.GET, endpoint, params=params, **kwargs)
    
    def post(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> APIResponse:
        """POST请求"""
        return self.request(HTTPMethod.POST, endpoint, data=data, **kwargs)
    
    def put(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> APIResponse:
        """PUT请求"""
        return self.request(HTTPMethod.PUT, endpoint, data=data, **kwargs)
    
    def delete(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> APIResponse:
        """DELETE请求"""
        return self.request(HTTPMethod.DELETE, endpoint, data=data, **kwargs)
    
    def patch(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> APIResponse:
        """PATCH请求"""
        return self.request(HTTPMethod.PATCH, endpoint, data=data, **kwargs)
    
    def stream(
        self,
        method: HTTPMethod,
        endpoint: str,
        data: Optional[Dict] = None,
        **kwargs
    ) -> Generator[Dict, None, None]:
        """
        流式请求
        
        用于处理NDJSON或SSE响应
        """
        url = self._build_url(endpoint)
        timeout = kwargs.pop("timeout", self.config.timeout * 10)
        
        request_config = {
            "method": method.value,
            "url": url,
            "data": data,
            "timeout": timeout
        }
        
        request_config = self._apply_interceptors_before(request_config)
        auth_headers = self._build_auth_headers()
        final_headers = {**self._session.headers, **auth_headers}
        
        try:
            response = self._session.request(
                method=method.value,
                url=url,
                json=request_config["data"],
                headers=final_headers,
                timeout=request_config["timeout"],
                stream=True,
                verify=self.config.verify_ssl,
                **kwargs
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        yield {"raw": line.decode("utf-8")}
                        
        except Exception as e:
            yield {"error": str(e), "error_type": type(e).__name__}
    
    def is_available(self) -> bool:
        """检查API是否可用"""
        try:
            response = self._session.get(
                self.config.base_url,
                timeout=5,
                verify=self.config.verify_ssl
            )
            return response.status_code < 500
        except Exception:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "name": self.name,
            "base_url": self.config.base_url,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(1, self._request_count),
            "interceptor_count": len(self._interceptors)
        }
    
    def close(self):
        """关闭会话"""
        if self._session:
            self._session.close()
            self._session = None
    
    @classmethod
    def get_instance(cls, name: str = "default") -> Optional['UnifiedAPIBackend']:
        """获取已存在的实例"""
        return cls._instances.get(name)
    
    @classmethod
    def remove_instance(cls, name: str):
        """移除实例"""
        with cls._lock:
            if name in cls._instances:
                instance = cls._instances.pop(name)
                instance.close()


class APIBackendFactory:
    """
    API后端工厂
    
    用于创建和管理多个API后端实例
    """
    
    _registry: Dict[str, APIConfig] = {}
    
    @classmethod
    def register(cls, name: str, config: APIConfig):
        """注册API配置"""
        cls._registry[name] = config
    
    @classmethod
    def create(cls, name: str, config: Optional[APIConfig] = None) -> UnifiedAPIBackend:
        """创建API后端实例"""
        if config is None:
            if name not in cls._registry:
                raise ValueError(f"未找到API配置: {name}")
            config = cls._registry[name]
        return UnifiedAPIBackend(name, config)
    
    @classmethod
    def list_registered(cls) -> List[str]:
        """列出已注册的API"""
        return list(cls._registry.keys())
    
    @classmethod
    def unregister(cls, name: str):
        """注销API配置"""
        cls._registry.pop(name, None)
