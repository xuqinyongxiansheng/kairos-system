"""
心跳工具
提供系统心跳检测功能
"""

import logging
import asyncio
from typing import Dict, Any, Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class Heartbeat:
    """心跳检测器"""
    
    def __init__(self, interval: float = 5.0):
        self.interval = interval
        self.callbacks = []
        self.running = False
        self.last_beat = None
        self.beat_count = 0
    
    async def start(self):
        """启动心跳"""
        if self.running:
            return {'status': 'warning', 'message': '心跳已在运行'}
        
        self.running = True
        logger.info(f"心跳启动，间隔：{self.interval}秒")
        
        asyncio.create_task(self._beat_loop())
        
        return {'status': 'success', 'message': '心跳已启动'}
    
    async def stop(self):
        """停止心跳"""
        self.running = False
        logger.info("心跳已停止")
        return {'status': 'success', 'message': '心跳已停止'}
    
    async def _beat_loop(self):
        """心跳循环"""
        while self.running:
            await self._beat()
            await asyncio.sleep(self.interval)
    
    async def _beat(self):
        """执行一次心跳"""
        self.last_beat = datetime.now().isoformat()
        self.beat_count += 1
        
        logger.debug(f"心跳 #{self.beat_count}")
        
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self.beat_count)
                else:
                    callback(self.beat_count)
            except Exception as e:
                logger.error(f"心跳回调失败：{e}")
    
    def register_callback(self, callback: Callable):
        """注册心跳回调"""
        self.callbacks.append(callback)
        logger.info(f"心跳回调注册")
    
    def unregister_callback(self, callback: Callable):
        """注销心跳回调"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            logger.info(f"心跳回调注销")
    
    async def get_status(self) -> Dict[str, Any]:
        """获取心跳状态"""
        return {
            'status': 'success',
            'running': self.running,
            'interval': self.interval,
            'last_beat': self.last_beat,
            'beat_count': self.beat_count,
            'callbacks_count': len(self.callbacks)
        }
