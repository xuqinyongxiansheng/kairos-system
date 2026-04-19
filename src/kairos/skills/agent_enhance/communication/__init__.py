#!/usr/bin/env python3
"""
通信模块
"""

from .protocol import (
    MessageType,
    MessagePriority,
    AgentMessage,
    CommunicationProtocol,
    MessageValidator
)
from .message import (
    MessageQueue,
    CommunicationChannel,
    CommunicationManager,
    get_communication_manager
)

__all__ = [
    'MessageType',
    'MessagePriority',
    'AgentMessage',
    'CommunicationProtocol',
    'MessageValidator',
    'MessageQueue',
    'CommunicationChannel',
    'CommunicationManager',
    'get_communication_manager'
]