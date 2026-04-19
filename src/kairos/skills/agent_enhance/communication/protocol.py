#!/usr/bin/env python3
"""
通信协议
定义Agent间通信的协议和规范
"""

import json
import time
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel


class MessageType:
    """消息类型"""
    TEXT = "text"
    CODE = "code"
    DATA = "data"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    SYSTEM = "system"
    TASK = "task"
    RESULT = "result"
    ERROR = "error"


class MessagePriority:
    """消息优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class AgentMessage(BaseModel):
    """Agent消息"""
    message_id: str
    sender: str
    receiver: str
    content: str
    message_type: str = MessageType.TEXT
    priority: int = MessagePriority.NORMAL
    timestamp: datetime = datetime.now()
    metadata: Dict[str, Any] = {}
    correlation_id: Optional[str] = None  # 关联ID，用于请求-响应配对


class CommunicationProtocol:
    """通信协议"""
    
    @staticmethod
    def serialize_message(message: AgentMessage) -> str:
        """序列化消息"""
        message_dict = message.model_dump()
        message_dict['timestamp'] = message_dict['timestamp'].isoformat()
        return json.dumps(message_dict, ensure_ascii=False)
    
    @staticmethod
    def deserialize_message(message_str: str) -> AgentMessage:
        """反序列化消息"""
        message_dict = json.loads(message_str)
        if 'timestamp' in message_dict:
            message_dict['timestamp'] = datetime.fromisoformat(message_dict['timestamp'])
        return AgentMessage(**message_dict)
    
    @staticmethod
    def create_message(sender: str, receiver: str, content: str, 
                      message_type: str = MessageType.TEXT, 
                      priority: int = MessagePriority.NORMAL,
                      metadata: Optional[Dict[str, Any]] = None,
                      correlation_id: Optional[str] = None) -> AgentMessage:
        """创建消息"""
        message_id = f"msg_{int(time.time() * 1000)}"
        return AgentMessage(
            message_id=message_id,
            sender=sender,
            receiver=receiver,
            content=content,
            message_type=message_type,
            priority=priority,
            metadata=metadata or {},
            correlation_id=correlation_id
        )
    
    @staticmethod
    def create_task_message(sender: str, receiver: str, task: str, 
                          context: Optional[Dict[str, Any]] = None) -> AgentMessage:
        """创建任务消息"""
        metadata = context or {}
        metadata['task_type'] = 'task'
        return CommunicationProtocol.create_message(
            sender=sender,
            receiver=receiver,
            content=task,
            message_type=MessageType.TASK,
            priority=MessagePriority.NORMAL,
            metadata=metadata
        )
    
    @staticmethod
    def create_result_message(sender: str, receiver: str, result: str, 
                            correlation_id: str, 
                            metadata: Optional[Dict[str, Any]] = None) -> AgentMessage:
        """创建结果消息"""
        return CommunicationProtocol.create_message(
            sender=sender,
            receiver=receiver,
            content=result,
            message_type=MessageType.RESULT,
            priority=MessagePriority.NORMAL,
            metadata=metadata or {},
            correlation_id=correlation_id
        )
    
    @staticmethod
    def create_error_message(sender: str, receiver: str, error: str, 
                           correlation_id: Optional[str] = None) -> AgentMessage:
        """创建错误消息"""
        return CommunicationProtocol.create_message(
            sender=sender,
            receiver=receiver,
            content=error,
            message_type=MessageType.ERROR,
            priority=MessagePriority.HIGH,
            correlation_id=correlation_id
        )


class MessageValidator:
    """消息验证器"""
    
    @staticmethod
    def validate_message(message: AgentMessage) -> bool:
        """验证消息"""
        # 验证必填字段
        if not message.message_id:
            return False
        if not message.sender:
            return False
        if not message.receiver:
            return False
        if not message.content:
            return False
        
        # 验证消息类型
        valid_types = [
            MessageType.TEXT,
            MessageType.CODE,
            MessageType.DATA,
            MessageType.IMAGE,
            MessageType.AUDIO,
            MessageType.VIDEO,
            MessageType.SYSTEM,
            MessageType.TASK,
            MessageType.RESULT,
            MessageType.ERROR
        ]
        if message.message_type not in valid_types:
            return False
        
        # 验证优先级
        if message.priority < MessagePriority.LOW or message.priority > MessagePriority.URGENT:
            return False
        
        return True
    
    @staticmethod
    def validate_message_str(message_str: str) -> bool:
        """验证消息字符串"""
        try:
            message = CommunicationProtocol.deserialize_message(message_str)
            return MessageValidator.validate_message(message)
        except Exception:
            return False