"""
日志工具
提供增强的日志记录功能
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json


class Logger:
    """增强日志记录器"""
    
    def __init__(self, name: str = 'app', level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        self.log_history = []
    
    def info(self, message: str, context: Dict[str, Any] = None):
        """记录信息日志"""
        self._log('info', message, context)
    
    def warning(self, message: str, context: Dict[str, Any] = None):
        """记录警告日志"""
        self._log('warning', message, context)
    
    def error(self, message: str, context: Dict[str, Any] = None):
        """记录错误日志"""
        self._log('error', message, context)
    
    def debug(self, message: str, context: Dict[str, Any] = None):
        """记录调试日志"""
        self._log('debug', message, context)
    
    def _log(self, level: str, message: str, context: Dict[str, Any] = None):
        """记录日志"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            'context': context or {}
        }
        
        self.log_history.append(log_entry)
        
        log_message = message
        if context:
            log_message += f" | {json.dumps(context, ensure_ascii=False)}"
        
        getattr(self.logger, level)(log_message)
    
    def get_logs(self, level: str = None, 
                limit: int = 100) -> list:
        """获取日志"""
        logs = self.log_history
        
        if level:
            logs = [l for l in logs if l['level'] == level]
        
        return logs[-limit:]
    
    def clear_logs(self):
        """清空日志"""
        self.log_history = []
        self.logger.info("日志已清空")
    
    def get_summary(self) -> Dict[str, Any]:
        """获取日志摘要"""
        summary = {
            'info': 0,
            'warning': 0,
            'error': 0,
            'debug': 0
        }
        
        for log in self.log_history:
            level = log['level']
            if level in summary:
                summary[level] += 1
        
        return {
            'status': 'success',
            'total_logs': len(self.log_history),
            'by_level': summary
        }
