"""
消息总线系统
实现模块间通信
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """消息类"""
    message_id: str
    message_type: str
    timestamp: str
    sender: str
    payload: Dict[str, Any]
    
    def __post_init__(self):
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class MessageBus:
    """消息总线"""
    
    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.running: bool = False
        self.worker_task: Optional[asyncio.Task] = None
        self.message_history = []
    
    def register_handler(self, message_type: str, handler: Callable):
        """注册消息处理器"""
        if message_type not in self.handlers:
            self.handlers[message_type] = []
        self.handlers[message_type].append(handler)
        logger.info(f"Handler registered for message type: {message_type}")
    
    def unregister_handler(self, message_type: str, handler: Callable):
        """注销消息处理器"""
        if message_type in self.handlers:
            try:
                self.handlers[message_type].remove(handler)
                if not self.handlers[message_type]:
                    del self.handlers[message_type]
                logger.info(f"Handler unregistered for message type: {message_type}")
            except ValueError:
                logger.warning(f"Handler not found for message type: {message_type}")
    
    async def publish(self, message: Message) -> Dict[str, Any]:
        """发布消息"""
        await self.message_queue.put(message)
        
        self.message_history.append({
            'message': message.to_dict(),
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"Message published: {message.message_type}")
        
        return {
            'status': 'success',
            'message_id': message.message_id
        }
    
    async def _process_messages(self):
        """处理消息队列"""
        while self.running:
            try:
                message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=1.0
                )
                
                await self._dispatch_message(message)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    
    async def _dispatch_message(self, message: Message):
        """分发消息"""
        handlers = self.handlers.get(message.message_type, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Handler error for {message.message_type}: {e}")
    
    async def start(self):
        """启动消息总线"""
        self.running = True
        self.worker_task = asyncio.create_task(self._process_messages())
        logger.info("MessageBus started")
    
    async def stop(self):
        """停止消息总线"""
        self.running = False
        
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        
        logger.info("MessageBus stopped")
    
    async def get_message_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取消息历史"""
        return self.message_history[-limit:]
    
    async def get_bus_status(self) -> Dict[str, Any]:
        """获取总线状态"""
        return {
            'status': 'success',
            'running': self.running,
            'queue_size': self.message_queue.qsize(),
            'registered_types': list(self.handlers.keys()),
            'total_messages': len(self.message_history)
        }


class ServiceRegistry:
    """服务注册表"""
    
    def __init__(self):
        self.services: Dict[str, Dict[str, Any]] = {}
    
    def register_service(self, name: str, endpoint: str, metadata: Dict[str, Any] = None):
        """注册服务"""
        self.services[name] = {
            'endpoint': endpoint,
            'metadata': metadata or {},
            'registered_at': datetime.now().isoformat(),
            'status': 'active'
        }
        logger.info(f"Service registered: {name}")
    
    def unregister_service(self, name: str):
        """注销服务"""
        if name in self.services:
            del self.services[name]
            logger.info(f"Service unregistered: {name}")
    
    def get_service(self, name: str) -> Optional[Dict[str, Any]]:
        """获取服务"""
        return self.services.get(name)
    
    def list_services(self) -> Dict[str, Any]:
        """列出所有服务"""
        return {
            'status': 'success',
            'services': [
                {
                    'name': name,
                    'endpoint': info['endpoint'],
                    'status': info['status']
                }
                for name, info in self.services.items()
            ],
            'count': len(self.services)
        }


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.metrics: Dict[str, List[Dict[str, Any]]] = {}
    
    def record_metric(self, metric_type: str, value: Any, metadata: Dict[str, Any] = None):
        """记录指标"""
        if metric_type not in self.metrics:
            self.metrics[metric_type] = []
        
        self.metrics[metric_type].append({
            'value': value,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        })
    
    def get_metrics(self, metric_type: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取指标"""
        return self.metrics.get(metric_type, [])[-limit:]
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        return {
            'status': 'success',
            'metrics': {
                k: v[-100:] for k, v in self.metrics.items()
            },
            'total_types': len(self.metrics)
        }
