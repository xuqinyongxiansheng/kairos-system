"""
Pytest 配置文件
提供测试固件和共享配置
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
import sys
import os

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session")
def event_loop():
    """提供事件循环固件"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def async_client():
    """提供异步HTTP客户端固件"""
    from httpx import AsyncClient
    from main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="session")
def test_config():
    """提供测试配置固件"""
    return {
        "test_model": "gemma4:e4b",
        "test_timeout": 30,
        "test_db": ":memory:"
    }


@pytest.fixture(scope="function")
def mock_llm_response():
    """提供模拟LLM响应固件"""
    return {
        "response": "这是一个测试响应",
        "model": "gemma4:e4b",
        "tokens": {"prompt": 10, "completion": 20}
    }


@pytest.fixture(scope="function")
def event_system():
    """提供事件系统固件"""
    from kairos.system.event_system import get_event_system
    
    event_sys = get_event_system()
    return event_sys


@pytest.fixture(scope="function")
def temp_memory():
    """提供临时内存存储固件"""
    from kairos.system.memory_system import MemorySystem
    
    ms = MemorySystem()
    yield ms
    # 清理
    ms._storage = {}


@pytest.fixture(scope="session")
def test_data_dir():
    """提供测试数据目录固件"""
    test_dir = os.path.join(os.path.dirname(__file__), "test_data")
    os.makedirs(test_dir, exist_ok=True)
    return test_dir


# 标记慢测试
pytest.register_assert_rewrite("system")

def pytest_configure(config):
    """配置pytest"""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


def pytest_collection_modifyitems(config, items):
    """修改测试项"""
    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "unit" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        else:
            item.add_marker(pytest.mark.unit)
