"""
事件系统单元测试
"""

import pytest
import asyncio
from kairos.system.event_system import Event, EventBus, EventSystem, EventType, get_event_system


class TestEvent:
    """测试 Event 类"""
    
    def test_event_creation(self):
        """测试事件创建"""
        event = Event(
            event_type="test.event",
            data={"key": "value"},
            source="test",
            priority=1
        )
        
        assert event.event_type == "test.event"
        assert event.data == {"key": "value"}
        assert event.source == "test"
        assert event.priority == 1
        assert event.event_id is not None
        assert event.timestamp is not None
    
    def test_event_to_dict(self):
        """测试事件转换为字典"""
        event = Event(
            event_type="test.event",
            data={"key": "value"}
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["event_type"] == "test.event"
        assert event_dict["data"] == {"key": "value"}
        assert "event_id" in event_dict
        assert "timestamp" in event_dict


class TestEventBus:
    """测试 EventBus 类"""
    
    @pytest.mark.asyncio
    async def test_event_bus_start_stop(self):
        """测试事件总线启动和停止"""
        bus = EventBus()
        
        await bus.start()
        assert bus._running is True
        
        await bus.stop()
        assert bus._running is False
    
    @pytest.mark.asyncio
    async def test_register_handler(self):
        """测试注册事件处理器"""
        bus = EventBus()
        
        def handler(event):
            pass
        
        bus.register_handler("test.event", handler)
        
        assert "test.event" in bus._handlers
        assert len(bus._handlers["test.event"]) == 1
    
    @pytest.mark.asyncio
    async def test_publish_event(self):
        """测试发布事件"""
        bus = EventBus()
        await bus.start()
        
        received_events = []
        
        async def handler(event):
            received_events.append(event)
        
        bus.register_handler("test.event", handler)
        
        event = Event("test.event", {"data": "test"})
        await bus.publish(event)
        
        # 等待事件处理
        await asyncio.sleep(0.1)
        
        assert len(received_events) == 1
        assert received_events[0]["event_type"] == "test.event"
        
        await bus.stop()


class TestEventSystem:
    """测试 EventSystem 类"""
    
    @pytest.mark.asyncio
    async def test_event_system_start_stop(self):
        """测试事件系统启动和停止"""
        event_system = EventSystem()
        
        await event_system.start()
        assert event_system.event_bus._running is True
        
        await event_system.stop()
        assert event_system.event_bus._running is False
    
    @pytest.mark.asyncio
    async def test_emit_event(self):
        """测试触发事件"""
        event_system = EventSystem()
        await event_system.start()
        
        await event_system.emit("test.event", {"key": "value"})
        
        # 等待事件处理
        await asyncio.sleep(0.1)
        
        history = event_system.get_event_history()
        assert len(history) == 1
        assert history[0]["event_type"] == "test.event"
        
        await event_system.stop()
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        event_system = EventSystem()
        stats = event_system.get_statistics()
        
        assert "registered_events" in stats
        assert "active_event_types" in stats
        assert "total_events_processed" in stats
        assert "timestamp" in stats


class TestEventType:
    """测试 EventType 枚举"""
    
    def test_event_type_values(self):
        """测试事件类型值"""
        assert EventType.SYSTEM_STARTUP.value == "system.startup"
        assert EventType.SYSTEM_SHUTDOWN.value == "system.shutdown"
        assert EventType.TASK_CREATED.value == "task.created"
        assert EventType.TASK_COMPLETED.value == "task.completed"
