#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一技能系统
整合所有技能模块，提供统一的技能管理、执行和优化功能

核心功能：
1. 技能注册与管理
2. 技能执行引擎
3. 技能依赖管理
4. 技能性能优化
5. 技能缓存机制
6. 技能安全控制
"""

import asyncio
import logging
import os
import json
import hashlib
import importlib
import inspect
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import threading

logger = logging.getLogger("UnifiedSkillSystem")


class SkillCategory(Enum):
    """技能分类"""
    GENERAL = "general"
    AI = "ai"
    VOICE = "voice"
    VISION = "vision"
    WEB = "web"
    SYSTEM = "system"
    DATA = "data"
    COMMUNICATION = "communication"
    AUTOMATION = "automation"
    KNOWLEDGE = "knowledge"
    CODING = "coding"
    ANALYSIS = "analysis"


class SkillStatus(Enum):
    """技能状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    DEPRECATED = "deprecated"


class SecurityLevel(Enum):
    """安全级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExecutionMode(Enum):
    """执行模式"""
    SYNC = "sync"
    ASYNC = "async"
    THREAD = "thread"


@dataclass
class SkillMetadata:
    """技能元数据"""
    name: str
    function: Callable
    description: str = ""
    category: str = "general"
    version: str = "1.0.0"
    author: str = ""
    
    # 参数定义
    parameters: Dict[str, Any] = field(default_factory=dict)
    returns: str = "Any"
    
    # 依赖关系
    dependencies: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    
    # 安全与权限
    security_level: str = "low"
    permissions: List[str] = field(default_factory=list)
    
    # 执行配置
    execution_mode: str = "async"
    timeout: int = 30
    max_retries: int = 3
    rate_limit: int = 100
    
    # 缓存配置
    cache_enabled: bool = True
    cache_ttl: int = 300
    
    # 标签与分类
    tags: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    
    # 统计信息
    created_at: str = ""
    last_used: str = ""
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_execution_time: float = 0.0
    last_error: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "version": self.version,
            "author": self.author,
            "parameters": self.parameters,
            "returns": self.returns,
            "dependencies": self.dependencies,
            "security_level": self.security_level,
            "permissions": self.permissions,
            "execution_mode": self.execution_mode,
            "timeout": self.timeout,
            "cache_enabled": self.cache_enabled,
            "tags": self.tags,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "average_execution_time": self.get_average_execution_time(),
            "success_rate": self.get_success_rate(),
            "health_score": self.get_health_score()
        }
    
    def update_stats(self, success: bool, execution_time: float, error: str = None):
        """更新统计信息"""
        self.usage_count += 1
        self.last_used = datetime.now().isoformat()
        self.total_execution_time += execution_time
        
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
            if error:
                self.last_error = error
    
    def get_average_execution_time(self) -> float:
        """获取平均执行时间"""
        if self.usage_count == 0:
            return 0.0
        return self.total_execution_time / self.usage_count
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.usage_count == 0:
            return 0.0
        return self.success_count / self.usage_count
    
    def get_health_score(self) -> float:
        """获取健康分数"""
        if self.usage_count == 0:
            return 0.0
        
        success_rate = self.get_success_rate()
        avg_time = self.get_average_execution_time()
        time_factor = max(0, 1 - (avg_time / 10))
        
        return success_rate * 0.7 + time_factor * 0.3


@dataclass
class SkillExecutionResult:
    """技能执行结果"""
    success: bool
    result: Any = None
    error: str = None
    execution_time: float = 0.0
    from_cache: bool = False
    skill_name: str = ""
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SkillCache:
    """技能缓存"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, Tuple[Any, float, float]] = {}  # key -> (value, expire_time, created_at)
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self._lock:
            if key not in self._cache:
                return None
            
            value, expire_time, _ = self._cache[key]
            
            if datetime.now().timestamp() > expire_time:
                del self._cache[key]
                return None
            
            return value
    
    def set(self, key: str, value: Any, ttl: int = None):
        """设置缓存"""
        with self._lock:
            if len(self._cache) >= self.max_size:
                self._evict_oldest()
            
            expire_time = datetime.now().timestamp() + (ttl or self.default_ttl)
            self._cache[key] = (value, expire_time, datetime.now().timestamp())
    
    def delete(self, key: str):
        """删除缓存"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
    
    def _evict_oldest(self):
        """淘汰最旧的缓存"""
        if not self._cache:
            return
        
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][2])
        del self._cache[oldest_key]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            return {
                "total_entries": len(self._cache),
                "max_size": self.max_size,
                "usage_ratio": len(self._cache) / self.max_size
            }


class SkillDependencyResolver:
    """技能依赖解析器"""
    
    def __init__(self):
        self._dependency_graph: Dict[str, Set[str]] = {}
    
    def add_skill(self, skill_name: str, dependencies: List[str]):
        """添加技能依赖"""
        self._dependency_graph[skill_name] = set(dependencies)
    
    def remove_skill(self, skill_name: str):
        """移除技能"""
        if skill_name in self._dependency_graph:
            del self._dependency_graph[skill_name]
    
    def get_execution_order(self, skill_names: List[str]) -> List[str]:
        """获取执行顺序（拓扑排序）"""
        visited = set()
        order = []
        
        def visit(skill_name: str):
            if skill_name in visited:
                return
            visited.add(skill_name)
            
            for dep in self._dependency_graph.get(skill_name, set()):
                if dep in self._dependency_graph:
                    visit(dep)
            
            order.append(skill_name)
        
        for skill_name in skill_names:
            visit(skill_name)
        
        return order
    
    def check_circular_dependency(self, skill_name: str) -> bool:
        """检查循环依赖"""
        visited = set()
        path = set()
        
        def visit(name: str) -> bool:
            if name in path:
                return True
            if name in visited:
                return False
            
            visited.add(name)
            path.add(name)
            
            for dep in self._dependency_graph.get(name, set()):
                if visit(dep):
                    return True
            
            path.remove(name)
            return False
        
        return visit(skill_name)


class UnifiedSkillSystem:
    """
    统一技能系统
    整合所有技能模块，提供统一的技能管理、执行和优化功能
    """
    
    def __init__(self, config: Dict = None):
        """初始化统一技能系统"""
        self.config = config or {}
        
        # 技能存储
        self.skills: Dict[str, SkillMetadata] = {}
        
        # 技能缓存
        self.cache = SkillCache(
            max_size=self.config.get("cache_max_size", 1000),
            default_ttl=self.config.get("cache_ttl", 300)
        )
        
        # 依赖解析器
        self.dependency_resolver = SkillDependencyResolver()
        
        # 线程池
        self.executor = ThreadPoolExecutor(
            max_workers=self.config.get("max_workers", 5)
        )
        
        # 执行日志
        self._execution_log: List[Dict[str, Any]] = []
        self._log_lock = threading.Lock()
        
        # 状态
        self._running = True
        
        logger.info("统一技能系统初始化完成")
    
    def register_skill(
        self,
        name: str,
        function: Callable,
        description: str = "",
        category: str = "general",
        version: str = "1.0.0",
        author: str = "",
        dependencies: List[str] = None,
        security_level: str = "low",
        permissions: List[str] = None,
        timeout: int = 30,
        cache_enabled: bool = True,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        注册技能
        
        Args:
            name: 技能名称
            function: 技能函数
            description: 描述
            category: 分类
            version: 版本
            author: 作者
            dependencies: 依赖
            security_level: 安全级别
            permissions: 权限
            timeout: 超时时间
            cache_enabled: 是否启用缓存
            tags: 标签
        
        Returns:
            注册结果
        """
        try:
            if name in self.skills:
                return {
                    "success": False,
                    "error": f"技能 '{name}' 已存在"
                }
            
            # 提取参数信息
            parameters = self._extract_parameters(function)
            
            # 判断执行模式
            execution_mode = "async" if asyncio.iscoroutinefunction(function) else "sync"
            
            # 创建元数据
            metadata = SkillMetadata(
                name=name,
                function=function,
                description=description,
                category=category,
                version=version,
                author=author,
                parameters=parameters,
                dependencies=dependencies or [],
                security_level=security_level,
                permissions=permissions or [],
                execution_mode=execution_mode,
                timeout=timeout,
                cache_enabled=cache_enabled,
                tags=tags or []
            )
            
            self.skills[name] = metadata
            
            # 添加到依赖图
            self.dependency_resolver.add_skill(name, dependencies or [])
            
            logger.info(f"技能注册成功: {name} ({category})")
            
            return {
                "success": True,
                "skill_name": name,
                "category": category,
                "execution_mode": execution_mode
            }
            
        except Exception as e:
            logger.error(f"技能注册失败: {e}")
            return {"success": False, "error": str(e)}
    
    def unregister_skill(self, name: str) -> Dict[str, Any]:
        """注销技能"""
        if name not in self.skills:
            return {"success": False, "error": f"技能 '{name}' 不存在"}
        
        del self.skills[name]
        self.dependency_resolver.remove_skill(name)
        
        # 清理相关缓存
        self.cache.delete(name)
        
        logger.info(f"技能注销成功: {name}")
        return {"success": True, "skill_name": name}
    
    async def execute_skill(
        self,
        name: str,
        parameters: Dict[str, Any] = None,
        user_context: Dict[str, Any] = None,
        use_cache: bool = True
    ) -> SkillExecutionResult:
        """
        执行技能
        
        Args:
            name: 技能名称
            parameters: 参数
            user_context: 用户上下文
            use_cache: 是否使用缓存
        
        Returns:
            执行结果
        """
        if name not in self.skills:
            return SkillExecutionResult(
                success=False,
                error=f"技能 '{name}' 不存在",
                skill_name=name
            )
        
        skill = self.skills[name]
        start_time = datetime.now()
        
        try:
            # 权限检查
            if not self._check_permissions(skill, user_context):
                return SkillExecutionResult(
                    success=False,
                    error=f"权限不足: {skill.permissions}",
                    skill_name=name
                )
            
            # 检查缓存
            if use_cache and skill.cache_enabled:
                cache_key = self._generate_cache_key(name, parameters or {})
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    return SkillExecutionResult(
                        success=True,
                        result=cached_result,
                        from_cache=True,
                        skill_name=name
                    )
            
            # 参数验证
            validation = self._validate_parameters(skill, parameters or {})
            if not validation["valid"]:
                return SkillExecutionResult(
                    success=False,
                    error=validation["error"],
                    skill_name=name
                )
            
            # 执行技能
            result = await self._execute_function(skill, parameters or {})
            
            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 更新统计
            skill.update_stats(True, execution_time)
            
            # 更新缓存
            if skill.cache_enabled:
                cache_key = self._generate_cache_key(name, parameters or {})
                self.cache.set(cache_key, result, skill.cache_ttl)
            
            # 记录执行日志
            self._log_execution(name, True, execution_time, parameters)
            
            return SkillExecutionResult(
                success=True,
                result=result,
                execution_time=execution_time,
                skill_name=name
            )
            
        except asyncio.TimeoutError:
            execution_time = (datetime.now() - start_time).total_seconds()
            skill.update_stats(False, execution_time, f"执行超时 ({skill.timeout}秒)")
            self._log_execution(name, False, execution_time, parameters, "Timeout")
            
            return SkillExecutionResult(
                success=False,
                error=f"执行超时 ({skill.timeout}秒)",
                execution_time=execution_time,
                skill_name=name
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            skill.update_stats(False, execution_time, str(e))
            self._log_execution(name, False, execution_time, parameters, str(e))
            
            logger.error(f"技能执行失败: {name} - {e}")
            return SkillExecutionResult(
                success=False,
                error=str(e),
                execution_time=execution_time,
                skill_name=name
            )
    
    async def execute_skill_chain(
        self,
        chain: List[Dict[str, Any]],
        user_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        执行技能链
        
        Args:
            chain: 技能链配置
            user_context: 用户上下文
        
        Returns:
            执行结果
        """
        results = []
        context = {}
        
        for i, step in enumerate(chain):
            skill_name = step.get("skill")
            parameters = step.get("parameters", {})
            
            # 处理上下文变量
            processed_params = self._process_context_variables(parameters, context)
            
            result = await self.execute_skill(skill_name, processed_params, user_context)
            
            if not result.success:
                return {
                    "success": False,
                    "failed_step": i,
                    "skill": skill_name,
                    "error": result.error,
                    "partial_results": results
                }
            
            context[f"step_{i}_result"] = result.result
            results.append(result.to_dict())
        
        return {
            "success": True,
            "results": results,
            "final_context": context
        }
    
    async def _execute_function(self, skill: SkillMetadata, parameters: Dict[str, Any]) -> Any:
        """执行技能函数"""
        if skill.execution_mode == "async":
            return await asyncio.wait_for(
                skill.function(**parameters),
                timeout=skill.timeout
            )
        else:
            loop = asyncio.get_event_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(
                    self.executor,
                    lambda: skill.function(**parameters)
                ),
                timeout=skill.timeout
            )
    
    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        """获取技能信息"""
        if name in self.skills:
            return self.skills[name].to_dict()
        return None
    
    def get_skills_by_category(self, category: str) -> List[Dict[str, Any]]:
        """按分类获取技能"""
        return [
            skill.to_dict() 
            for skill in self.skills.values() 
            if skill.category == category
        ]
    
    def get_skills_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """按标签获取技能"""
        return [
            skill.to_dict() 
            for skill in self.skills.values() 
            if tag in skill.tags
        ]
    
    def search_skills(self, query: str) -> List[Dict[str, Any]]:
        """搜索技能"""
        query_lower = query.lower()
        results = []
        
        for skill in self.skills.values():
            if (query_lower in skill.name.lower() or
                query_lower in skill.description.lower() or
                any(query_lower in tag.lower() for tag in skill.tags)):
                results.append(skill.to_dict())
        
        # 按使用次数排序
        results.sort(key=lambda x: x.get("usage_count", 0), reverse=True)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        total_skills = len(self.skills)
        active_skills = sum(1 for s in self.skills.values() if s.usage_count > 0)
        
        total_executions = sum(s.usage_count for s in self.skills.values())
        total_successes = sum(s.success_count for s in self.skills.values())
        total_failures = sum(s.failure_count for s in self.skills.values())
        
        avg_health = sum(s.get_health_score() for s in self.skills.values()) / max(total_skills, 1)
        
        return {
            "total_skills": total_skills,
            "active_skills": active_skills,
            "total_executions": total_executions,
            "total_successes": total_successes,
            "total_failures": total_failures,
            "success_rate": total_successes / max(total_executions, 1),
            "average_health_score": round(avg_health, 3),
            "cache_stats": self.cache.get_statistics(),
            "categories": self._get_category_stats()
        }
    
    def _get_category_stats(self) -> Dict[str, int]:
        """获取分类统计"""
        stats = {}
        for skill in self.skills.values():
            stats[skill.category] = stats.get(skill.category, 0) + 1
        return stats
    
    def _extract_parameters(self, func: Callable) -> Dict[str, Any]:
        """提取函数参数"""
        sig = inspect.signature(func)
        params = {}
        
        for name, param in sig.parameters.items():
            params[name] = {
                "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                "default": param.default if param.default != inspect.Parameter.empty else None,
                "required": param.default == inspect.Parameter.empty
            }
        
        return params
    
    def _check_permissions(self, skill: SkillMetadata, user_context: Dict[str, Any]) -> bool:
        """检查权限"""
        if not skill.permissions:
            return True
        
        if not user_context or "permissions" not in user_context:
            return False
        
        user_perms = set(user_context.get("permissions", []))
        required_perms = set(skill.permissions)
        
        return required_perms.issubset(user_perms)
    
    def _validate_parameters(self, skill: SkillMetadata, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证参数"""
        for name, info in skill.parameters.items():
            if info.get("required") and name not in parameters:
                return {"valid": False, "error": f"缺少必需参数: {name}"}
        
        return {"valid": True}
    
    def _generate_cache_key(self, skill_name: str, parameters: Dict[str, Any]) -> str:
        """生成缓存键"""
        params_str = json.dumps(parameters, sort_keys=True, ensure_ascii=False)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()
        return f"{skill_name}_{params_hash}"
    
    def _process_context_variables(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """处理上下文变量"""
        processed = {}
        
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith("$"):
                var_name = value[1:]
                if var_name in context:
                    processed[key] = context[var_name]
                else:
                    processed[key] = value
            else:
                processed[key] = value
        
        return processed
    
    def _log_execution(self, skill_name: str, success: bool, execution_time: float,
                      parameters: Dict[str, Any], error: str = None):
        """记录执行日志"""
        with self._log_lock:
            self._execution_log.append({
                "timestamp": datetime.now().isoformat(),
                "skill": skill_name,
                "success": success,
                "execution_time": execution_time,
                "parameters": parameters,
                "error": error
            })
            
            # 限制日志大小
            if len(self._execution_log) > 10000:
                self._execution_log = self._execution_log[-5000:]
    
    def get_execution_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取执行日志"""
        with self._log_lock:
            return self._execution_log[-limit:]
    
    def shutdown(self):
        """关闭系统"""
        self._running = False
        self.executor.shutdown(wait=True)
        self.cache.clear()
        logger.info("统一技能系统已关闭")


# 技能装饰器
def skill(
    name: str,
    description: str = "",
    category: str = "general",
    version: str = "1.0.0",
    dependencies: List[str] = None,
    security_level: str = "low",
    permissions: List[str] = None,
    timeout: int = 30,
    tags: List[str] = None
):
    """技能装饰器"""
    def decorator(func):
        func._skill_metadata = {
            "name": name,
            "description": description,
            "category": category,
            "version": version,
            "dependencies": dependencies or [],
            "security_level": security_level,
            "permissions": permissions or [],
            "timeout": timeout,
            "tags": tags or []
        }
        return func
    return decorator


# 全局实例
_unified_skill_system = None


def get_unified_skill_system(config: Dict = None) -> UnifiedSkillSystem:
    """获取统一技能系统实例"""
    global _unified_skill_system
    
    if _unified_skill_system is None:
        _unified_skill_system = UnifiedSkillSystem(config)
    
    return _unified_skill_system
