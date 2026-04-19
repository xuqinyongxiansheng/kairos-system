# -*- coding: utf-8 -*-
"""
突触通信总线 (Synaptic Bus)
受神经突触通信启发的统一模块间通信基础设施
替代直接导入+事件总线+依赖注入三种并行通信方式

核心机制:
- 基于消息传递的异步通信
- 置信度路由 (confidence > 0.8 → 快速路径, < 0.3 → 深度路径)
- 优先级调度 (URGENT > HIGH > NORMAL > LOW)
- 超时处理与优雅降级
- 消息追踪与可观测性
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Callable, Union, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .enums import (
    MessagePriority, RoutingStrategy, DeliveryStatus,
    AgentType, EventType
)

logger = logging.getLogger("SynapticBus")


@dataclass
class SynapticMessage:
    """突触消息"""
    sender: str
    recipients: List[str]
    content: Dict[str, Any]
    confidence: float = 0.5
    priority: MessagePriority = MessagePriority.NORMAL
    timeout_ms: float = 5000.0
    fallback_required: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    message_id: str = field(default_factory=lambda: f"syn_{uuid.uuid4().hex[:12]}")
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    trace: List[Dict[str, Any]] = field(default_factory=list)

    def add_trace(self, node: str, action: str, detail: str = ""):
        """添加追踪记录"""
        self.trace.append({
            "node": node,
            "action": action,
            "detail": detail,
            "timestamp": datetime.now().isoformat()
        })

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "recipients": self.recipients,
            "content": self.content,
            "confidence": self.confidence,
            "priority": self.priority.value,
            "timeout_ms": self.timeout_ms,
            "fallback_required": self.fallback_required,
            "metadata": self.metadata,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "timestamp": self.timestamp,
            "trace": self.trace
        }


@dataclass
class DeliveryReceipt:
    """投递回执"""
    message_id: str
    recipient: str
    status: DeliveryStatus
    response: Optional[Any] = None
    latency_ms: float = 0.0
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RouteRule:
    """路由规则"""
    name: str
    condition: Callable[[SynapticMessage], bool]
    target: str
    priority: int = 0
    fallback: Optional[str] = None


class SynapticBus:
    """
    突触通信总线
    
    功能:
    - 统一异步消息传递
    - 置信度路由
    - 优先级调度
    - 超时处理
    - 优雅降级
    - 消息追踪
    - 统计监控
    """

    def __init__(self, max_queue_size: int = 10000, default_timeout_ms: float = 5000.0):
        self._endpoints: Dict[str, Callable] = {}
        self._endpoint_types: Dict[str, AgentType] = {}
        self._route_rules: List[RouteRule] = []
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._pending_replies: Dict[str, asyncio.Future] = {}
        self._delivery_history: List[DeliveryReceipt] = []
        self._max_history = 5000
        self._default_timeout_ms = default_timeout_ms
        self._routing_strategy = RoutingStrategy.CONFIDENCE_BASED
        self._middleware: List[Callable] = []
        self._fallback_handlers: Dict[str, Callable] = {}
        self._stats = {
            "total_sent": 0,
            "total_delivered": 0,
            "total_failed": 0,
            "total_fallback": 0,
            "total_timeout": 0,
            "avg_latency_ms": 0.0,
            "by_priority": {p.name: 0 for p in MessagePriority},
            "by_agent_type": {t.name: 0 for t in AgentType}
        }
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None

        self._register_default_routes()
        logger.info("突触通信总线初始化")

    def _register_default_routes(self):
        """注册默认路由规则"""
        self._route_rules = [
            RouteRule(
                name="高置信度快速路径",
                condition=lambda msg: msg.confidence > 0.8 and not msg.fallback_required,
                target=AgentType.REFLEX.value,
                priority=100,
                fallback=AgentType.DELIBERATIVE.value
            ),
            RouteRule(
                name="低置信度深度路径",
                condition=lambda msg: msg.confidence < 0.3,
                target=AgentType.DELIBERATIVE.value,
                priority=90,
                fallback=AgentType.COORDINATOR.value
            ),
            RouteRule(
                name="学习路径",
                condition=lambda msg: msg.metadata.get("requires_learning", False),
                target=AgentType.LEARNING.value,
                priority=80,
                fallback=AgentType.DELIBERATIVE.value
            ),
            RouteRule(
                name="协调路径",
                condition=lambda msg: len(msg.recipients) > 1 or msg.metadata.get("requires_coordination", False),
                target=AgentType.COORDINATOR.value,
                priority=70,
                fallback=AgentType.DELIBERATIVE.value
            ),
            RouteRule(
                name="降级路径",
                condition=lambda msg: msg.fallback_required,
                target=AgentType.DELIBERATIVE.value,
                priority=50
            ),
        ]

    def register_endpoint(self, endpoint_id: str, handler: Callable,
                         agent_type: AgentType = AgentType.DELIBERATIVE):
        """
        注册通信端点
        
        Args:
            endpoint_id: 端点标识
            handler: 消息处理函数
            agent_type: Agent类型
        """
        self._endpoints[endpoint_id] = handler
        self._endpoint_types[endpoint_id] = agent_type
        logger.info(f"注册端点: {endpoint_id} (类型: {agent_type.value})")

    def unregister_endpoint(self, endpoint_id: str):
        """注销端点"""
        self._endpoints.pop(endpoint_id, None)
        self._endpoint_types.pop(endpoint_id, None)
        logger.info(f"注销端点: {endpoint_id}")

    def add_route_rule(self, rule: RouteRule):
        """添加路由规则"""
        self._route_rules.append(rule)
        self._route_rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"添加路由规则: {rule.name}")

    def add_middleware(self, middleware: Callable):
        """添加中间件"""
        self._middleware.append(middleware)

    def register_fallback(self, endpoint_id: str, handler: Callable):
        """注册降级处理器"""
        self._fallback_handlers[endpoint_id] = handler

    async def send(self, message: SynapticMessage) -> List[DeliveryReceipt]:
        """
        发送消息 (一对多)
        
        Args:
            message: 突触消息
            
        Returns:
            投递回执列表
        """
        start_time = time.time()
        self._stats["total_sent"] += 1
        self._stats["by_priority"][message.priority.name] += 1

        message.add_trace("synaptic_bus", "send", f"发送至 {len(message.recipients)} 个接收者")

        for middleware in self._middleware:
            try:
                if asyncio.iscoroutinefunction(middleware):
                    message = await middleware(message)
                else:
                    message = middleware(message)
                if message is None:
                    return [DeliveryReceipt(
                        message_id=message.message_id if message else "unknown",
                        recipient="middleware",
                        status=DeliveryStatus.FAILED,
                        error="中间件拦截"
                    )]
            except Exception as e:
                logger.error(f"中间件错误: {e}")

        receipts = []
        for recipient in message.recipients:
            receipt = await self._deliver(message, recipient)
            receipts.append(receipt)

        elapsed_ms = (time.time() - start_time) * 1000
        self._update_latency_stats(elapsed_ms)

        return receipts

    async def send_and_wait(self, message: SynapticMessage,
                           timeout_ms: float = None) -> Any:
        """
        发送消息并等待回复
        
        Args:
            message: 突触消息
            timeout_ms: 超时时间
            
        Returns:
            回复内容
        """
        timeout_ms = timeout_ms or message.timeout_ms or self._default_timeout_ms
        reply_id = f"reply_{message.message_id}"
        future = asyncio.get_event_loop().create_future()
        self._pending_replies[reply_id] = future

        message.reply_to = reply_id
        message.add_trace("synaptic_bus", "send_and_wait", f"等待回复 (超时: {timeout_ms}ms)")

        receipts = await self.send(message)

        try:
            result = await asyncio.wait_for(future, timeout=timeout_ms / 1000.0)
            return result
        except asyncio.TimeoutError:
            self._stats["total_timeout"] += 1
            logger.warning(f"消息超时: {message.message_id}")
            return await self._handle_timeout(message)
        finally:
            self._pending_replies.pop(reply_id, None)

    def reply(self, original_message_id: str, response: Any):
        """回复消息"""
        reply_id = f"reply_{original_message_id}"
        future = self._pending_replies.get(reply_id)
        if future and not future.done():
            future.set_result(response)

    async def broadcast(self, sender: str, content: Dict[str, Any],
                       confidence: float = 0.5,
                       priority: MessagePriority = MessagePriority.NORMAL,
                       exclude: Set[str] = None,
                       metadata: Dict[str, Any] = None) -> List[DeliveryReceipt]:
        """
        广播消息到所有端点
        
        Args:
            sender: 发送者
            content: 消息内容
            confidence: 置信度
            priority: 优先级
            exclude: 排除的端点
            metadata: 元数据
            
        Returns:
            投递回执列表
        """
        exclude = exclude or set()
        recipients = [ep for ep in self._endpoints if ep not in exclude]

        message = SynapticMessage(
            sender=sender,
            recipients=recipients,
            content=content,
            confidence=confidence,
            priority=priority,
            metadata=metadata or {}
        )

        return await self.send(message)

    async def route(self, sender: str, content: Dict[str, Any],
                   confidence: float = 0.5,
                   priority: MessagePriority = MessagePriority.NORMAL,
                   metadata: Dict[str, Any] = None) -> List[DeliveryReceipt]:
        """
        基于置信度自动路由消息
        
        Args:
            sender: 发送者
            content: 消息内容
            confidence: 置信度
            priority: 优先级
            metadata: 元数据
            
        Returns:
            投递回执列表
        """
        message = SynapticMessage(
            sender=sender,
            recipients=[],
            content=content,
            confidence=confidence,
            priority=priority,
            metadata=metadata or {}
        )

        target_type = self._resolve_route(message)
        target_endpoints = [
            ep for ep, at in self._endpoint_types.items()
            if at == target_type
        ]

        if not target_endpoints:
            target_endpoints = list(self._endpoints.keys())[:1]
            logger.warning(f"无匹配端点 (类型: {target_type})，使用默认端点")

        message.recipients = target_endpoints
        self._stats["by_agent_type"][target_type.name] += 1

        message.add_trace("synaptic_bus", "route",
                         f"路由至 {target_type.value} ({len(target_endpoints)} 个端点)")

        return await self.send(message)

    def _resolve_route(self, message: SynapticMessage) -> AgentType:
        """解析路由目标"""
        for rule in self._route_rules:
            try:
                if rule.condition(message):
                    try:
                        return AgentType(rule.target)
                    except ValueError:
                        return AgentType.DELIBERATIVE
            except Exception:
                continue
        return AgentType.DELIBERATIVE

    async def _deliver(self, message: SynapticMessage, recipient: str) -> DeliveryReceipt:
        """投递消息到单个端点"""
        start_time = time.time()

        if recipient not in self._endpoints:
            return DeliveryReceipt(
                message_id=message.message_id,
                recipient=recipient,
                status=DeliveryStatus.FAILED,
                error=f"端点不存在: {recipient}"
            )

        handler = self._endpoints[recipient]

        try:
            if asyncio.iscoroutinefunction(handler):
                response = await asyncio.wait_for(
                    handler(message),
                    timeout=message.timeout_ms / 1000.0
                )
            else:
                response = handler(message)

            latency_ms = (time.time() - start_time) * 1000
            self._stats["total_delivered"] += 1

            if message.reply_to:
                self.reply(message.message_id, response)

            receipt = DeliveryReceipt(
                message_id=message.message_id,
                recipient=recipient,
                status=DeliveryStatus.DELIVERED,
                response=response,
                latency_ms=latency_ms
            )

        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            self._stats["total_timeout"] += 1

            fallback_response = await self._handle_fallback(message, recipient)

            receipt = DeliveryReceipt(
                message_id=message.message_id,
                recipient=recipient,
                status=DeliveryStatus.TIMEOUT,
                latency_ms=latency_ms,
                error="超时",
                response=fallback_response
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._stats["total_failed"] += 1

            fallback_response = await self._handle_fallback(message, recipient)

            receipt = DeliveryReceipt(
                message_id=message.message_id,
                recipient=recipient,
                status=DeliveryStatus.FAILED,
                latency_ms=latency_ms,
                error=str(e),
                response=fallback_response
            )

        self._record_delivery(receipt)
        return receipt

    async def _handle_fallback(self, message: SynapticMessage,
                               failed_endpoint: str) -> Optional[Any]:
        """处理降级"""
        if failed_endpoint in self._fallback_handlers:
            try:
                handler = self._fallback_handlers[failed_endpoint]
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(message)
                else:
                    result = handler(message)
                self._stats["total_fallback"] += 1
                return result
            except Exception as e:
                logger.error(f"降级处理失败: {e}")

        if message.fallback_required:
            for rule in self._route_rules:
                if rule.fallback:
                    try:
                        fallback_type = AgentType(rule.fallback)
                        fallback_endpoints = [
                            ep for ep, at in self._endpoint_types.items()
                            if at == fallback_type and ep != failed_endpoint
                        ]
                        if fallback_endpoints:
                            handler = self._endpoints[fallback_endpoints[0]]
                            if asyncio.iscoroutinefunction(handler):
                                result = await handler(message)
                            else:
                                result = handler(message)
                            self._stats["total_fallback"] += 1
                            return result
                    except Exception as e:
                        logger.error(f"降级路由失败: {e}")

        return None

    async def _handle_timeout(self, message: SynapticMessage) -> Any:
        """处理超时"""
        return await self._handle_fallback(message, "") or {
            "status": "timeout",
            "message_id": message.message_id,
            "error": "消息处理超时"
        }

    def _record_delivery(self, receipt: DeliveryReceipt):
        """记录投递"""
        self._delivery_history.append(receipt)
        if len(self._delivery_history) > self._max_history:
            self._delivery_history = self._delivery_history[-self._max_history:]

    def _update_latency_stats(self, latency_ms: float):
        """更新延迟统计"""
        total = self._stats["total_sent"]
        if total > 0:
            current_avg = self._stats["avg_latency_ms"]
            self._stats["avg_latency_ms"] = (
                current_avg * (total - 1) + latency_ms
            ) / total

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_sent": self._stats["total_sent"],
            "total_delivered": self._stats["total_delivered"],
            "total_failed": self._stats["total_failed"],
            "total_fallback": self._stats["total_fallback"],
            "total_timeout": self._stats["total_timeout"],
            "avg_latency_ms": round(self._stats["avg_latency_ms"], 2),
            "delivery_rate": (
                self._stats["total_delivered"] / max(self._stats["total_sent"], 1)
            ),
            "by_priority": dict(self._stats["by_priority"]),
            "by_agent_type": dict(self._stats["by_agent_type"]),
            "endpoints": len(self._endpoints),
            "route_rules": len(self._route_rules),
            "pending_replies": len(self._pending_replies)
        }

    def get_endpoint_info(self) -> Dict[str, Any]:
        """获取端点信息"""
        return {
            endpoint: {
                "type": self._endpoint_types.get(endpoint, AgentType.DELIBERATIVE).value,
                "has_fallback": endpoint in self._fallback_handlers
            }
            for endpoint in self._endpoints
        }

    def get_route_rules(self) -> List[Dict[str, Any]]:
        """获取路由规则"""
        result = []
        for rule in self._route_rules:
            result.append({
                "name": rule.name,
                "target": rule.target,
                "priority": rule.priority,
                "fallback": rule.fallback
            })
        return result

    def get_delivery_history(self, limit: int = 100,
                            status: DeliveryStatus = None) -> List[Dict[str, Any]]:
        """获取投递历史"""
        history = self._delivery_history
        if status:
            history = [r for r in history if r.status == status]
        return [
            {
                "message_id": r.message_id,
                "recipient": r.recipient,
                "status": r.status.value,
                "latency_ms": round(r.latency_ms, 2),
                "error": r.error,
                "timestamp": r.timestamp
            }
            for r in history[-limit:]
        ]


synaptic_bus = SynapticBus()


def get_synaptic_bus() -> SynapticBus:
    """获取全局突触总线"""
    return synaptic_bus
