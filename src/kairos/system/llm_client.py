#!/usr/bin/env python3
"""
LLM 客户端兼容层

已迁移到 system/unified_llm_client.py
此文件保留以维持向后兼容性，所有调用自动委托到统一客户端

使用方式（不变）：
    from kairos.system.llm_client import get_llm_client
    client = get_llm_client()
    response = await client.chat(model="gemma4:e4b", messages=[...])
"""

from kairos.system.unified_llm_client import (
    UnifiedLLMClient,
    CircuitBreaker,
    CircuitState,
    CircuitConfig,
    RetryConfig,
    LRUCache,
    ModelSelector,
    get_llm_client,
    get_unified_client,
    close_unified_client,
)

import logging

logger = logging.getLogger(__name__)

logger.info("llm_client.py 已委托到 unified_llm_client.py，向后兼容")
