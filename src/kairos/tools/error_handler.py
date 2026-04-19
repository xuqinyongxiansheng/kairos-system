"""
错误处理器
提供统一的错误处理机制
"""

import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self):
        self.error_handlers = {}
        self.error_history = []
        self.default_handler = None
    
    def register_handler(self, error_type: type, 
                        handler_func: Callable):
        """
        注册错误处理器
        
        Args:
            error_type: 错误类型
            handler_func: 处理函数
        """
        self.error_handlers[error_type] = handler_func
        logger.info(f"错误处理器注册：{error_type.__name__}")
    
    def set_default_handler(self, handler_func: Callable):
        """设置默认处理器"""
        self.default_handler = handler_func
        logger.info("默认错误处理器已设置")
    
    async def handle(self, error: Exception, 
                    context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理错误
        
        Args:
            error: 错误对象
            context: 错误上下文
            
        Returns:
            处理结果
        """
        logger.error(f"错误发生：{type(error).__name__}: {str(error)}")
        
        error_record = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {}
        }
        
        self.error_history.append(error_record)
        
        handler = self.error_handlers.get(type(error), self.default_handler)
        
        if handler:
            try:
                result = await handler(error, context) if self._is_async(handler) else handler(error, context)
                return result
            except Exception as e:
                logger.error(f"错误处理器失败：{e}")
        
        return {
            'status': 'error',
            'error_type': type(error).__name__,
            'error_message': str(error)
        }
    
    def _is_async(self, func: Callable) -> bool:
        """判断函数是否为异步"""
        import asyncio
        return asyncio.iscoroutinefunction(func)
    
    async def retry(self, func: Callable, max_retries: int = 3,
                   delay: float = 1.0, **kwargs) -> Dict[str, Any]:
        """
        重试执行
        
        Args:
            func: 执行函数
            max_retries: 最大重试次数
            delay: 重试延迟
            **kwargs: 函数参数
            
        Returns:
            执行结果
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"执行尝试 #{attempt + 1}/{max_retries}")
                
                if asyncio.iscoroutinefunction(func):
                    result = await func(**kwargs)
                else:
                    result = func(**kwargs)
                
                return {
                    'status': 'success',
                    'result': result,
                    'attempts': attempt + 1
                }
                
            except Exception as e:
                last_error = e
                logger.warning(f"尝试失败：{e}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
        
        return {
            'status': 'error',
            'error_type': type(last_error).__name__,
            'error_message': str(last_error),
            'attempts': max_retries
        }
    
    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        error_counts = {}
        
        for error in self.error_history:
            error_type = error['error_type']
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        return {
            'status': 'success',
            'total_errors': len(self.error_history),
            'error_types': error_counts
        }
