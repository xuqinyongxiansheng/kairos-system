# -*- coding: utf-8 -*-
"""
Agent智能体模块
包含上下文压缩、渐进式披露、提供者故障转移、可中断调用、插件化架构
Claude Code优化：查询守卫、记忆分类、记忆截断、企业级重试、环形缓冲区+上下文隔离、中止控制器+活动管理器、优化中心
MaxKB优化：DAG工作流引擎、三模式混合检索、模型供应商注册表、性能基础设施、功能增强
"""

from .context_compressor import ContextCompressor, CompressionResult
from .progressive_disclosure import ProgressiveDisclosureEngine, DisclosableItem, DisclosureLevel
from .provider_fallback import ProviderFallbackChain, ProviderEndpoint, FallbackResult, get_provider_chain
from .interruptible_call import InterruptibleAPICall, CallResult
from .plugin_architecture import (
    PluginRegistry, BasePlugin, MemoryProviderPlugin, ContextEnginePlugin,
    PluginType, get_plugin_registry, register_plugin
)
from .query_guard import QueryGuard, QueryState, QueryGuardSnapshot, QueryGuardManager, get_query_guard_manager
from .memory_taxonomy import (
    MemoryCategory, MemoryTypeSpec, MemoryClassifier, MemorySaveDecision,
    MemoryEntry, MemoryTaxonomyEngine, get_memory_taxonomy,
    MEMORY_TYPES, MEMORY_TYPE_NAMES, MEMORY_TYPE_SPECS
)
from .memory_truncation import (
    MemoryTruncator, MemoryDriftDetector, MemoryTruncationEngine,
    TruncationResult, TruncationReason, DriftReport, get_truncation_engine
)
from .enterprise_retry import (
    EnterpriseRetry, RetryConfig, RetryResult, RetryMode, ErrorCategory,
    ErrorClassifier, calculate_retry_delay, parse_retry_after, get_enterprise_retry
)
from .circular_buffer import (
    CircularBuffer, ContextIsolator, AgentContext, AgentContextManager,
    get_agent_context_manager
)
from .abort_activity import (
    AbortController, AbortControllerManager, AbortState, AbortInfo, get_abort_manager,
    ActivityManager, ActivityType, ActivityState, get_activity_manager
)
from .optimization_center import (
    OptimizationCenter, MetricsCollector, CircuitBreaker, CircuitState,
    CircuitConfig, OptimizationConfig, AlertRule, MetricType, get_optimization_center
)
from .workflow_engine import (
    Workflow, WorkflowManage, WorkflowBuilder, WorkflowMode, WorkflowContext,
    Node, Edge, NodeProperties, NodeResult, NodeChunk, NodeChunkManage,
    INode, StartNode, AIChatNode, SearchKnowledgeNode, ConditionNode,
    ReplyNode, ToolNode, LoopNode, FunctionNode, VariableAssignNode,
    RerankerNode, IntentNode, NodeType, register_node_type,
)
from .hybrid_search import (
    HybridSearchEngine, SearchMode, SearchQuery, SearchResult,
    KeywordsSearchStrategy, EmbeddingSearchStrategy, BlendSearchStrategy,
    get_hybrid_search_engine,
)
from .model_provider import (
    ModelProviderRegistry, BaseModelProvider, ModelType, ModelInfo,
    ModelCredential, ModelCache, OllamaProvider, OpenAIProvider,
    DeepSeekProvider, SiliconCloudProvider, get_model_registry,
)
from .perf_infra import (
    MemCache, DistributedLock, MemoryGuard,
    get_mem_cache, get_distributed_lock, get_memory_guard,
)
from .enhancement import (
    SandboxExecutor, SandboxMode, SandboxResult,
    EventDrivenMemory, MemoryEvent, MemoryEventType,
    OpenAICompatAPI, ChatCompletionRequest, ChatCompletionResponse,
    ChatMessage, ChatCompletionChoice,
    get_sandbox, get_event_memory, get_openai_api,
)

__all__ = [
    'ContextCompressor', 'CompressionResult',
    'ProgressiveDisclosureEngine', 'DisclosableItem', 'DisclosureLevel',
    'ProviderFallbackChain', 'ProviderEndpoint', 'FallbackResult', 'get_provider_chain',
    'InterruptibleAPICall', 'CallResult',
    'PluginRegistry', 'BasePlugin', 'MemoryProviderPlugin', 'ContextEnginePlugin',
    'PluginType', 'get_plugin_registry', 'register_plugin',
    'QueryGuard', 'QueryState', 'QueryGuardSnapshot', 'QueryGuardManager', 'get_query_guard_manager',
    'MemoryCategory', 'MemoryTypeSpec', 'MemoryClassifier', 'MemorySaveDecision',
    'MemoryEntry', 'MemoryTaxonomyEngine', 'get_memory_taxonomy',
    'MEMORY_TYPES', 'MEMORY_TYPE_NAMES', 'MEMORY_TYPE_SPECS',
    'MemoryTruncator', 'MemoryDriftDetector', 'MemoryTruncationEngine',
    'TruncationResult', 'TruncationReason', 'DriftReport', 'get_truncation_engine',
    'EnterpriseRetry', 'RetryConfig', 'RetryResult', 'RetryMode', 'ErrorCategory',
    'ErrorClassifier', 'calculate_retry_delay', 'parse_retry_after', 'get_enterprise_retry',
    'CircularBuffer', 'ContextIsolator', 'AgentContext', 'AgentContextManager',
    'get_agent_context_manager',
    'AbortController', 'AbortControllerManager', 'AbortState', 'AbortInfo', 'get_abort_manager',
    'ActivityManager', 'ActivityType', 'ActivityState', 'get_activity_manager',
    'OptimizationCenter', 'MetricsCollector', 'CircuitBreaker', 'CircuitState',
    'CircuitConfig', 'OptimizationConfig', 'AlertRule', 'MetricType', 'get_optimization_center',
    'Workflow', 'WorkflowManage', 'WorkflowBuilder', 'WorkflowMode', 'WorkflowContext',
    'Node', 'Edge', 'NodeProperties', 'NodeResult', 'NodeChunk', 'NodeChunkManage',
    'INode', 'StartNode', 'AIChatNode', 'SearchKnowledgeNode', 'ConditionNode',
    'ReplyNode', 'ToolNode', 'LoopNode', 'FunctionNode', 'VariableAssignNode',
    'RerankerNode', 'IntentNode', 'NodeType', 'register_node_type',
    'HybridSearchEngine', 'SearchMode', 'SearchQuery', 'SearchResult',
    'KeywordsSearchStrategy', 'EmbeddingSearchStrategy', 'BlendSearchStrategy',
    'get_hybrid_search_engine',
    'ModelProviderRegistry', 'BaseModelProvider', 'ModelType', 'ModelInfo',
    'ModelCredential', 'ModelCache', 'OllamaProvider', 'OpenAIProvider',
    'DeepSeekProvider', 'SiliconCloudProvider', 'get_model_registry',
    'MemCache', 'DistributedLock', 'MemoryGuard',
    'get_mem_cache', 'get_distributed_lock', 'get_memory_guard',
    'SandboxExecutor', 'SandboxMode', 'SandboxResult',
    'EventDrivenMemory', 'MemoryEvent', 'MemoryEventType',
    'OpenAICompatAPI', 'ChatCompletionRequest', 'ChatCompletionResponse',
    'ChatMessage', 'ChatCompletionChoice',
    'get_sandbox', 'get_event_memory', 'get_openai_api',
]
