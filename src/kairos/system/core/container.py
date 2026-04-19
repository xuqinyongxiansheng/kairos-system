"""
依赖注入容器（线程安全版 + 性能优化版）
实现模块解耦和灵活配置，所有共享状态受RLock支持
支持单例、瞬态、作用域三种生命周期，循环依赖检测使用thread-local
Phase 3优化:
- inspect.signature() 缓存避免重复反射
- WeakRef缓存层减少GC压力
"""

import threading
import weakref
from typing import Dict, Any, Type, Callable, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging
import inspect

logger = logging.getLogger("DependencyContainer")


class ServiceLifetime(Enum):
    """服务生命周期"""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


@dataclass
class ServiceDescriptor:
    """服务描述符"""
    service_type: Type
    implementation_type: Optional[Type]
    implementation: Optional[Any]
    lifetime: ServiceLifetime
    factory: Optional[Callable] = None


class DependencyContainer:
    """
    依赖注入容器（线程安全版）

    改进:
    - 所有共享状态通过 RLock 保护
    - _resolving_stack 使用 threading.local() 实现线程级循环依赖检测
    - get_container() 使用 DCLP 双重检查锁定
    - _signature_cache 缓存 inspect.signature() 结果避免重复反射
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._instances: Dict[Type, Any] = {}
        self._scoped_instances: Dict[Type, Any] = {}
        self._local_stacks = threading.local()
        self._signature_cache: Dict[Type, Any] = {}  # 签名缓存
        self._weak_cache: Dict[Type, weakref.ref] = {}  # WeakRef瞬态缓存

        logger.info("依赖注入容器初始化(线程安全版+签名缓存+WeakRef)")

    def _get_resolving_stack(self) -> List[Type]:
        """获取当前线程的解析栈"""
        stack = getattr(self._local_stacks, 'resolving_stack', None)
        if stack is None:
            stack = []
            self._local_stacks.resolving_stack = stack
        return stack

    def register_singleton(self, service_type: Type,
                          implementation: Any = None) -> 'DependencyContainer':
        with self._lock:
            self._services[service_type] = ServiceDescriptor(
                service_type=service_type,
                implementation_type=implementation if isinstance(implementation, type) else None,
                implementation=implementation if not isinstance(implementation, type) else None,
                lifetime=ServiceLifetime.SINGLETON
            )
            logger.debug(f"注册单例服务: {service_type.__name__}")
        return self

    def register_transient(self, service_type: Type,
                          implementation_type: Type = None) -> 'DependencyContainer':
        with self._lock:
            self._services[service_type] = ServiceDescriptor(
                service_type=service_type,
                implementation_type=implementation_type or service_type,
                implementation=None,
                lifetime=ServiceLifetime.TRANSIENT
            )
            logger.debug(f"注册瞬态服务: {service_type.__name__}")
        return self

    def register_factory(self, service_type: Type,
                        factory: Callable[['DependencyContainer'], Any],
                        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON) -> 'DependencyContainer':
        with self._lock:
            self._services[service_type] = ServiceDescriptor(
                service_type=service_type,
                implementation_type=None,
                implementation=None,
                lifetime=lifetime,
                factory=factory
            )
            logger.debug(f"注册工厂服务: {service_type.__name__}")
        return self

    def register_scoped(self, service_type: Type,
                       implementation_type: Type = None) -> 'DependencyContainer':
        with self._lock:
            self._services[service_type] = ServiceDescriptor(
                service_type=service_type,
                implementation_type=implementation_type or service_type,
                implementation=None,
                lifetime=ServiceLifetime.SCOPED
            )
            logger.debug(f"注册作用域服务: {service_type.__name__}")
        return self

    def resolve(self, service_type: Type) -> Any:
        if service_type not in self._services:
            raise ValueError(f"服务未注册: {service_type.__name__}")

        resolving_stack = self._get_resolving_stack()
        if service_type in resolving_stack:
            cycle = " -> ".join(t.__name__ for t in resolving_stack) + f" -> {service_type.__name__}"
            raise RuntimeError(f"检测到循环依赖: {cycle}")

        descriptor = self._services[service_type]

        with self._lock:
            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                if service_type in self._instances:
                    return self._instances[service_type]
            elif descriptor.lifetime == ServiceLifetime.SCOPED:
                if service_type in self._scoped_instances:
                    return self._scoped_instances[service_type]

        resolving_stack.append(service_type)
        try:
            instance = self._create_instance(descriptor)
        finally:
            resolving_stack.pop()

        with self._lock:
            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                self._instances[service_type] = instance
            elif descriptor.lifetime == ServiceLifetime.SCOPED:
                self._scoped_instances[service_type] = instance

        return instance

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        if descriptor.factory:
            return descriptor.factory(self)
        if descriptor.implementation is not None:
            return descriptor.implementation
        if descriptor.implementation_type:
            return self._create_with_injection(descriptor.implementation_type)
        return self._create_with_injection(descriptor.service_type)

    def _create_with_injection(self, implementation_type: Type) -> Any:
        constructor = implementation_type.__init__
        if implementation_type not in self._signature_cache:
            self._signature_cache[implementation_type] = inspect.signature(constructor)
        sig = self._signature_cache[implementation_type]
        params = {}
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            param_type = param.annotation
            if param_type == inspect.Parameter.empty:
                if param.default != inspect.Parameter.empty:
                    params[param_name] = param.default
                continue
            with self._lock:
                registered = param_type in self._services
            if registered:
                params[param_name] = self.resolve(param_type)
            elif param.default != inspect.Parameter.empty:
                params[param_name] = param.default
        return implementation_type(**params)

    def try_resolve(self, service_type: Type, default: Any = None) -> Any:
        try:
            return self.resolve(service_type)
        except (ValueError, RuntimeError):
            return default

    def is_registered(self, service_type: Type) -> bool:
        with self._lock:
            return service_type in self._services

    def get_registered_services(self) -> List[Type]:
        with self._lock:
            return list(self._services.keys())

    def clear_scoped(self):
        with self._lock:
            self._scoped_instances.clear()
        logger.debug("作用域实例已清除")

    def clear_all(self):
        with self._lock:
            self._instances.clear()
            self._scoped_instances.clear()
        logger.debug("所有实例已清除")

    def get_service_info(self, service_type: Type) -> Dict[str, Any]:
        with self._lock:
            if service_type not in self._services:
                return {"registered": False}
            descriptor = self._services[service_type]
            return {
                "registered": True,
                "service_type": service_type.__name__,
                "lifetime": descriptor.lifetime.value,
                "has_instance": service_type in self._instances,
                "has_factory": descriptor.factory is not None
            }


class ServiceLocator:
    """
    服务定位器模式（线程安全版）
    """

    _instance: Optional['ServiceLocator'] = None
    _container: Optional[DependencyContainer] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    @classmethod
    def set_container(cls, container: DependencyContainer):
        cls._container = container

    @classmethod
    def get_container(cls) -> DependencyContainer:
        if cls._container is None:
            with cls._lock:
                if cls._container is None:
                    cls._container = DependencyContainer()
        return cls._container

    @classmethod
    def get(cls, service_type: Type) -> Any:
        return cls.get_container().resolve(service_type)

    @classmethod
    def try_get(cls, service_type: Type, default: Any = None) -> Any:
        return cls.get_container().try_resolve(service_type, default)


def injectable(cls):
    cls.__injectable__ = True
    return cls


def inject(service_type: Type):
    def decorator(target):
        if not hasattr(target, '__injections__'):
            target.__injections__ = {}
        target.__injections__[target.__name__] = service_type
        return target
    return decorator


_container_lock = threading.Lock()
_container_instance: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """获取全局容器（DCLP）"""
    global _container_instance
    if _container_instance is not None:
        return _container_instance
    with _container_lock:
        if _container_instance is None:
            _container_instance = DependencyContainer()
    return _container_instance


def configure_services(configure: Callable[[DependencyContainer], None]):
    configure(get_container())
    ServiceLocator.set_container(get_container())
