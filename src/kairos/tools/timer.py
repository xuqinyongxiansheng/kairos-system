"""
计时器工具
提供定时器和倒计时功能
"""

import logging
import asyncio
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class Timer:
    """计时器"""
    
    def __init__(self):
        self.timers = {}
        self.timer_id = 0
    
    async def start_timer(self, duration: float, 
                         callback: Optional[Callable] = None,
                         name: str = None) -> Dict[str, Any]:
        """
        启动计时器
        
        Args:
            duration: 持续时间（秒）
            callback: 回调函数
            name: 计时器名称
            
        Returns:
            启动结果
        """
        self.timer_id += 1
        timer_id = self.timer_id
        
        if name is None:
            name = f"timer_{timer_id}"
        
        logger.info(f"计时器启动：{name}, {duration}秒")
        
        asyncio.create_task(self._run_timer(timer_id, name, duration, callback))
        
        self.timers[timer_id] = {
            'name': name,
            'duration': duration,
            'start_time': datetime.now().isoformat(),
            'end_time': (datetime.now() + timedelta(seconds=duration)).isoformat(),
            'status': 'running'
        }
        
        return {
            'status': 'success',
            'timer_id': timer_id,
            'name': name
        }
    
    async def _run_timer(self, timer_id: int, name: str, 
                        duration: float, callback: Optional[Callable]):
        """运行计时器"""
        try:
            await asyncio.sleep(duration)
            
            self.timers[timer_id]['status'] = 'completed'
            logger.info(f"计时器完成：{name}")
            
            if callback:
                if asyncio.iscoroutinefunction(callback):
                    await callback(timer_id)
                else:
                    callback(timer_id)
                    
        except asyncio.CancelledError:
            self.timers[timer_id]['status'] = 'cancelled'
            logger.info(f"计时器取消：{name}")
        except Exception as e:
            self.timers[timer_id]['status'] = 'error'
            logger.error(f"计时器错误：{name}, {e}")
    
    async def cancel_timer(self, timer_id: int) -> Dict[str, Any]:
        """取消计时器"""
        if timer_id not in self.timers:
            return {
                'status': 'not_found',
                'message': f'计时器不存在：{timer_id}'
            }
        
        self.timers[timer_id]['status'] = 'cancelled'
        logger.info(f"计时器取消：{self.timers[timer_id]['name']}")
        
        return {
            'status': 'success',
            'message': '计时器已取消'
        }
    
    async def get_timer_status(self, timer_id: int) -> Dict[str, Any]:
        """获取计时器状态"""
        if timer_id not in self.timers:
            return {
                'status': 'not_found',
                'message': f'计时器不存在：{timer_id}'
            }
        
        return {
            'status': 'success',
            'timer': self.timers[timer_id]
        }
    
    async def get_summary(self) -> Dict[str, Any]:
        """获取计时器摘要"""
        running = sum(1 for t in self.timers.values() if t['status'] == 'running')
        completed = sum(1 for t in self.timers.values() if t['status'] == 'completed')
        cancelled = sum(1 for t in self.timers.values() if t['status'] == 'cancelled')
        
        return {
            'status': 'success',
            'total_timers': len(self.timers),
            'running': running,
            'completed': completed,
            'cancelled': cancelled
        }
