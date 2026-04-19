"""
工具执行框架
提供参数验证、沙箱隔离、回滚机制、重试策略
解决AI Agent动作有效性不足的问题
"""

import asyncio
import logging
import time
import os
import json
import shutil
from typing import Dict, Any, List, Optional, Callable, Type
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import functools

logger = logging.getLogger("ToolExecutor")


class ExecutionStatus(Enum):
    """执行状态"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"


class RiskLevel(Enum):
    """风险等级"""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    DANGEROUS = "dangerous"


@dataclass
class ExecutionConfig:
    """执行配置"""
    max_retries: int = 3
    timeout: int = 30
    enable_sandbox: bool = True
    enable_rollback: bool = True
    require_confirmation: bool = False
    log_execution: bool = True


@dataclass
class ParameterSchema:
    """参数模式"""
    name: str
    type: Type
    required: bool = True
    default: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None
    allowed_values: Optional[List[Any]] = None


@dataclass
class ExecutionResult:
    """执行结果"""
    status: ExecutionStatus
    result: Any
    error: Optional[str]
    execution_time: float
    retry_count: int
    rollback_data: Optional[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Checkpoint:
    """检查点"""
    id: str
    timestamp: str
    tool_name: str
    params: Dict[str, Any]
    snapshot: Dict[str, Any]


class ParameterValidator:
    """参数验证器"""
    
    def validate(self, params: Dict[str, Any], 
                schema: Dict[str, ParameterSchema]) -> Dict[str, Any]:
        """
        验证参数
        
        Args:
            params: 参数字典
            schema: 参数模式
            
        Returns:
            验证结果
        """
        errors = []
        validated = {}
        
        for name, param_schema in schema.items():
            value = params.get(name, param_schema.default)
            
            # 检查必需参数
            if param_schema.required and value is None:
                errors.append(f"缺少必需参数: {name}")
                continue
            
            if value is None:
                continue
            
            # 类型检查
            if not isinstance(value, param_schema.type):
                try:
                    value = param_schema.type(value)
                except (ValueError, TypeError):
                    errors.append(f"参数类型错误: {name} 期望 {param_schema.type.__name__}")
                    continue
            
            # 范围检查
            if param_schema.min_value is not None:
                if isinstance(value, (int, float)) and value < param_schema.min_value:
                    errors.append(f"参数值过小: {name} 最小值为 {param_schema.min_value}")
            
            if param_schema.max_value is not None:
                if isinstance(value, (int, float)) and value > param_schema.max_value:
                    errors.append(f"参数值过大: {name} 最大值为 {param_schema.max_value}")
            
            # 模式检查
            if param_schema.pattern:
                import re
                if not re.match(param_schema.pattern, str(value)):
                    errors.append(f"参数格式错误: {name}")
            
            # 允许值检查
            if param_schema.allowed_values:
                if value not in param_schema.allowed_values:
                    errors.append(f"参数值无效: {name} 允许值: {param_schema.allowed_values}")
            
            validated[name] = value
        
        if errors:
            return {"valid": False, "errors": errors, "params": validated}
        
        return {"valid": True, "errors": [], "params": validated}


class Sandbox:
    """沙箱隔离"""
    
    DANGEROUS_COMMANDS = [
        "rm -rf", "del /", "format", "mkfs", "dd if=",
        "sudo rm", "chmod 777", "chown root",
        "> /dev/", ":(){ :|:& };:",
        "curl | bash", "wget | sh"
    ]
    
    DANGEROUS_PATHS = [
        "/etc/passwd", "/etc/shadow", "/root",
        "C:\\Windows\\System32", "C:\\Program Files"
    ]
    
    def __init__(self, allowed_paths: List[str] = None):
        self.allowed_paths = allowed_paths or [os.getcwd()]
    
    def is_command_safe(self, command: str) -> bool:
        """检查命令是否安全"""
        command_lower = command.lower()
        
        for dangerous in self.DANGEROUS_COMMANDS:
            if dangerous.lower() in command_lower:
                return False
        
        return True
    
    def is_path_allowed(self, path: str) -> bool:
        """检查路径是否允许"""
        abs_path = os.path.abspath(path)
        
        for allowed in self.allowed_paths:
            if abs_path.startswith(os.path.abspath(allowed)):
                return True
        
        return False
    
    def sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """清理参数"""
        sanitized = {}
        
        for key, value in params.items():
            if isinstance(value, str):
                # 检查路径
                if key in ["path", "file", "directory", "dest", "destination"]:
                    if not self.is_path_allowed(value):
                        raise PermissionError(f"路径访问被拒绝: {value}")
                
                # 检查命令
                if key in ["command", "cmd", "shell"]:
                    if not self.is_command_safe(value):
                        raise PermissionError(f"危险命令被拒绝: {value}")
            
            sanitized[key] = value
        
        return sanitized


class RollbackManager:
    """回滚管理器"""
    
    def __init__(self, max_checkpoints: int = 100):
        self.checkpoints: Dict[str, Checkpoint] = {}
        self.max_checkpoints = max_checkpoints
    
    async def create_checkpoint(self, tool_name: str, 
                               params: Dict[str, Any]) -> Checkpoint:
        """创建检查点"""
        checkpoint_id = f"cp_{int(time.time() * 1000)}"
        
        snapshot = await self._create_snapshot(tool_name, params)
        
        checkpoint = Checkpoint(
            id=checkpoint_id,
            timestamp=datetime.now().isoformat(),
            tool_name=tool_name,
            params=params,
            snapshot=snapshot
        )
        
        self.checkpoints[checkpoint_id] = checkpoint
        
        # 清理旧检查点
        if len(self.checkpoints) > self.max_checkpoints:
            oldest = min(self.checkpoints.keys())
            del self.checkpoints[oldest]
        
        logger.debug(f"创建检查点: {checkpoint_id}")
        return checkpoint
    
    async def _create_snapshot(self, tool_name: str, 
                              params: Dict[str, Any]) -> Dict[str, Any]:
        """创建快照"""
        snapshot = {}
        
        # 文件操作快照
        if tool_name in ["file_write", "file_delete", "file_move"]:
            path = params.get("path") or params.get("source")
            if path and os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        snapshot["original_content"] = f.read()
                    snapshot["original_exists"] = True
                except Exception:
                    snapshot["original_exists"] = False
        
        return snapshot
    
    async def rollback(self, checkpoint: Checkpoint) -> bool:
        """回滚到检查点"""
        try:
            tool_name = checkpoint.tool_name
            snapshot = checkpoint.snapshot
            params = checkpoint.params
            
            # 文件操作回滚
            if tool_name == "file_write":
                path = params.get("path")
                if path:
                    if snapshot.get("original_exists"):
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(snapshot["original_content"])
                    else:
                        if os.path.exists(path):
                            os.remove(path)
            
            elif tool_name == "file_delete":
                path = params.get("path")
                if path and snapshot.get("original_exists"):
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(snapshot["original_content"])
            
            elif tool_name == "file_move":
                source = params.get("source")
                destination = params.get("destination")
                if source and destination:
                    if os.path.exists(destination):
                        shutil.move(destination, source)
            
            logger.info(f"回滚成功: {checkpoint.id}")
            return True
            
        except Exception as e:
            logger.error(f"回滚失败: {e}")
            return False


class ToolExecutor:
    """
    安全工具执行器
    
    功能:
    - 参数验证
    - 沙箱隔离
    - 回滚机制
    - 重试策略
    - 超时控制
    - 执行日志
    """
    
    def __init__(self, config: ExecutionConfig = None):
        self.config = config or ExecutionConfig()
        self.validator = ParameterValidator()
        self.sandbox = Sandbox()
        self.rollback_manager = RollbackManager()
        self.execution_history: List[Dict[str, Any]] = []
        self._tool_schemas: Dict[str, Dict[str, ParameterSchema]] = {}
        
        logger.info("工具执行器初始化")
    
    def register_tool_schema(self, tool_name: str, 
                            schema: Dict[str, ParameterSchema]):
        """注册工具参数模式"""
        self._tool_schemas[tool_name] = schema
    
    async def execute(self, tool_name: str,
                     tool_func: Callable,
                     params: Dict[str, Any],
                     risk_level: RiskLevel = RiskLevel.SAFE) -> ExecutionResult:
        """
        安全执行工具
        
        Args:
            tool_name: 工具名称
            tool_func: 工具函数
            params: 参数
            risk_level: 风险等级
            
        Returns:
            执行结果
        """
        start_time = time.time()
        checkpoint = None
        
        # 1. 参数验证
        if tool_name in self._tool_schemas:
            validation = self.validator.validate(params, self._tool_schemas[tool_name])
            if not validation["valid"]:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    result=None,
                    error=f"参数验证失败: {validation['errors']}",
                    execution_time=time.time() - start_time,
                    retry_count=0,
                    rollback_data=None
                )
            params = validation["params"]
        
        # 2. 沙箱检查
        if self.config.enable_sandbox:
            try:
                params = self.sandbox.sanitize_params(params)
            except PermissionError as e:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    result=None,
                    error=str(e),
                    execution_time=time.time() - start_time,
                    retry_count=0,
                    rollback_data=None
                )
        
        # 3. 创建检查点
        if self.config.enable_rollback:
            checkpoint = await self.rollback_manager.create_checkpoint(tool_name, params)
        
        # 4. 执行（带重试）
        last_error = None
        for attempt in range(self.config.max_retries + 1):
            try:
                result = await self._execute_with_timeout(
                    tool_func, params, self.config.timeout
                )
                
                # 记录执行
                if self.config.log_execution:
                    self._log_execution(tool_name, params, result, attempt)
                
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    result=result,
                    error=None,
                    execution_time=time.time() - start_time,
                    retry_count=attempt,
                    rollback_data=checkpoint.__dict__ if checkpoint else None
                )
                
            except asyncio.TimeoutError:
                last_error = f"执行超时 ({self.config.timeout}s)"
                logger.warning(f"工具执行超时: {tool_name} (attempt {attempt + 1})")
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"工具执行失败: {tool_name} - {e} (attempt {attempt + 1})")
            
            # 重试延迟
            if attempt < self.config.max_retries:
                delay = min(2 ** attempt, 10)
                await asyncio.sleep(delay)
        
        # 5. 执行失败，尝试回滚
        if checkpoint and self.config.enable_rollback:
            rollback_success = await self.rollback_manager.rollback(checkpoint)
            if rollback_success:
                return ExecutionResult(
                    status=ExecutionStatus.ROLLED_BACK,
                    result=None,
                    error=last_error,
                    execution_time=time.time() - start_time,
                    retry_count=self.config.max_retries,
                    rollback_data=checkpoint.__dict__
                )
        
        return ExecutionResult(
            status=ExecutionStatus.FAILED,
            result=None,
            error=last_error,
            execution_time=time.time() - start_time,
            retry_count=self.config.max_retries,
            rollback_data=checkpoint.__dict__ if checkpoint else None
        )
    
    async def _execute_with_timeout(self, func: Callable, 
                                    params: Dict[str, Any],
                                    timeout: int) -> Any:
        """带超时的执行"""
        if asyncio.iscoroutinefunction(func):
            return await asyncio.wait_for(func(**params), timeout=timeout)
        else:
            loop = asyncio.get_event_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(None, functools.partial(func, **params)),
                timeout=timeout
            )
    
    def _log_execution(self, tool_name: str, params: Dict[str, Any],
                      result: Any, retry_count: int):
        """记录执行"""
        log_entry = {
            "tool_name": tool_name,
            "params": {k: str(v)[:100] for k, v in params.items()},
            "result_type": type(result).__name__,
            "retry_count": retry_count,
            "timestamp": datetime.now().isoformat()
        }
        
        self.execution_history.append(log_entry)
        
        # 限制历史大小
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]
    
    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self.execution_history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = len(self.execution_history)
        
        return {
            "total_executions": total,
            "checkpoints": len(self.rollback_manager.checkpoints),
            "tool_schemas": len(self._tool_schemas)
        }


# 全局实例
tool_executor = ToolExecutor()


def get_tool_executor() -> ToolExecutor:
    """获取全局工具执行器"""
    return tool_executor


# 便捷装饰器
def tool(name: str, schema: Dict[str, ParameterSchema] = None,
        risk_level: RiskLevel = RiskLevel.SAFE):
    """
    工具装饰器
    
    Usage:
        @tool("file_read", {
            "path": ParameterSchema(name="path", type=str, required=True)
        })
        async def read_file(path: str) -> str:
            with open(path, 'r') as f:
                return f.read()
    """
    def decorator(func):
        # 注册模式
        if schema:
            tool_executor.register_tool_schema(name, schema)
        
        @functools.wraps(func)
        async def async_wrapper(**kwargs):
            result = await tool_executor.execute(name, func, kwargs, risk_level)
            if result.status == ExecutionStatus.SUCCESS:
                return result.result
            raise Exception(result.error)
        
        @functools.wraps(func)
        def sync_wrapper(**kwargs):
            result = asyncio.run(tool_executor.execute(name, func, kwargs, risk_level))
            if result.status == ExecutionStatus.SUCCESS:
                return result.result
            raise Exception(result.error)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
