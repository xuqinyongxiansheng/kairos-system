"""
服务模块包
包含：命令系统、工具系统、MCP协议、上下文压缩、LSP客户端、会话管理、消息管道、权限系统、代理引擎
"""

_services_exports = {}

try:
    from kairos.services.commands import CommandRegistry, CommandDispatcher, CommandDef, CommandType, CommandResult
    _services_exports.update({
        "CommandRegistry": CommandRegistry, "CommandDispatcher": CommandDispatcher,
        "CommandDef": CommandDef, "CommandType": CommandType, "CommandResult": CommandResult,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"commands 模块加载失败: {e}")

try:
    from kairos.services.tools import ToolRegistry, ToolDef, ToolResult, build_tool, get_tool_registry, PermissionLevel
    _services_exports.update({
        "ToolRegistry": ToolRegistry, "ToolDef": ToolDef, "ToolResult": ToolResult,
        "build_tool": build_tool, "get_tool_registry": get_tool_registry, "PermissionLevel": PermissionLevel,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"tools 模块加载失败: {e}")

try:
    from kairos.services.compact import CompactService, CompactLevel, get_compact_service
    _services_exports.update({
        "CompactService": CompactService, "CompactLevel": CompactLevel, "get_compact_service": get_compact_service,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"compact 模块加载失败: {e}")

try:
    from kairos.services.mcp import McpManager, McpServerConfig, TransportType, get_mcp_manager
    _services_exports.update({
        "McpManager": McpManager, "McpServerConfig": McpServerConfig,
        "TransportType": TransportType, "get_mcp_manager": get_mcp_manager,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"mcp 模块加载失败: {e}")

try:
    from kairos.services.lsp import LSPManager, LSPServerConfig, get_lsp_manager
    _services_exports.update({
        "LSPManager": LSPManager, "LSPServerConfig": LSPServerConfig, "get_lsp_manager": get_lsp_manager,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"lsp 模块加载失败: {e}")

try:
    from kairos.services.session import SessionManager, Session, Message, get_session_manager
    _services_exports.update({
        "SessionManager": SessionManager, "Session": Session,
        "Message": Message, "get_session_manager": get_session_manager,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"session 模块加载失败: {e}")

try:
    from kairos.services.pipeline import (
        normalize_messages, ensure_tool_result_pairing, inject_context,
        create_compact_boundary, get_messages_after_boundary, estimate_message_tokens,
    )
    _services_exports.update({
        "normalize_messages": normalize_messages, "ensure_tool_result_pairing": ensure_tool_result_pairing,
        "inject_context": inject_context, "create_compact_boundary": create_compact_boundary,
        "get_messages_after_boundary": get_messages_after_boundary, "estimate_message_tokens": estimate_message_tokens,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"pipeline 模块加载失败: {e}")

try:
    from kairos.services.permission import (
        PermissionChecker, PermissionMode, PermissionRule, RuleBehavior,
        PermissionResult, get_permission_checker,
    )
    _services_exports.update({
        "PermissionChecker": PermissionChecker, "PermissionMode": PermissionMode,
        "PermissionRule": PermissionRule, "RuleBehavior": RuleBehavior,
        "PermissionResult": PermissionResult, "get_permission_checker": get_permission_checker,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"permission 模块加载失败: {e}")

try:
    from kairos.services.agent_engine import (
        AgentEngine, LoopState, HookEvent, HookManager, HookDef, HookResult,
        ToolCall, ToolCallResult, ToolOrchestrator, get_agent_engine,
    )
    _services_exports.update({
        "AgentEngine": AgentEngine, "LoopState": LoopState, "HookEvent": HookEvent,
        "HookManager": HookManager, "HookDef": HookDef, "HookResult": HookResult,
        "ToolCall": ToolCall, "ToolCallResult": ToolCallResult,
        "ToolOrchestrator": ToolOrchestrator, "get_agent_engine": get_agent_engine,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"agent_engine 模块加载失败: {e}")

try:
    from kairos.services.sub_agent import SubAgentRunner, AgentTask, AgentStatus, get_sub_agent_runner
    _services_exports.update({
        "SubAgentRunner": SubAgentRunner, "AgentTask": AgentTask,
        "AgentStatus": AgentStatus, "get_sub_agent_runner": get_sub_agent_runner,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"sub_agent 模块加载失败: {e}")

try:
    from kairos.services.skill import SkillManager, SkillDef, get_skill_manager
    _services_exports.update({
        "SkillManager": SkillManager, "SkillDef": SkillDef, "get_skill_manager": get_skill_manager,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"skill 模块加载失败: {e}")

try:
    from kairos.services.todo import TodoManager, TodoItem, TodoStatus, get_todo_manager
    _services_exports.update({
        "TodoManager": TodoManager, "TodoItem": TodoItem,
        "TodoStatus": TodoStatus, "get_todo_manager": get_todo_manager,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"todo 模块加载失败: {e}")

try:
    from kairos.services.token_tracker import TokenTracker, BudgetTracker, BudgetDecision, TokenUsage, get_token_tracker
    _services_exports.update({
        "TokenTracker": TokenTracker, "BudgetTracker": BudgetTracker,
        "BudgetDecision": BudgetDecision, "TokenUsage": TokenUsage,
        "get_token_tracker": get_token_tracker,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"token_tracker 模块加载失败: {e}")

try:
    from kairos.services.bootstrap import BootstrapState, AgentMode, SessionState, ModeLatch, get_bootstrap_state
    _services_exports.update({
        "BootstrapState": BootstrapState, "AgentMode": AgentMode,
        "SessionState": SessionState, "ModeLatch": ModeLatch,
        "get_bootstrap_state": get_bootstrap_state,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"bootstrap 模块加载失败: {e}")

try:
    from kairos.services.context_window import ContextWindowManager, ContextAnalysis, GitContext, get_context_window_manager
    _services_exports.update({
        "ContextWindowManager": ContextWindowManager, "ContextAnalysis": ContextAnalysis,
        "GitContext": GitContext, "get_context_window_manager": get_context_window_manager,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"context_window 模块加载失败: {e}")

try:
    from kairos.services.auto_classifier import AutoModeClassifier, ClassificationResult, ClassificationDecision, get_auto_classifier
    _services_exports.update({
        "AutoModeClassifier": AutoModeClassifier, "ClassificationResult": ClassificationResult,
        "ClassificationDecision": ClassificationDecision, "get_auto_classifier": get_auto_classifier,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"auto_classifier 模块加载失败: {e}")

try:
    from kairos.services.cost_tracker import CostTracker, get_cost_tracker
    _services_exports.update({
        "CostTracker": CostTracker, "get_cost_tracker": get_cost_tracker,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"cost_tracker 模块加载失败: {e}")

try:
    from kairos.services.hooks import (
        AsyncHookRegistry, HookDefinition, HookEvent, HookType,
        HookSource, HookResult, get_hook_registry, get_hook_config_manager,
    )
    _services_exports.update({
        "AsyncHookRegistry": AsyncHookRegistry, "HookDefinition": HookDefinition,
        "HookEvent": HookEvent, "HookType": HookType,
        "HookSource": HookSource, "HookResult": HookResult,
        "get_hook_registry": get_hook_registry, "get_hook_config_manager": get_hook_config_manager,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"hooks 模块加载失败: {e}")

try:
    from kairos.services.memory_extract import (
        MemoryExtractor, ExtractedMemory, MemorySandbox,
        get_memory_extractor,
    )
    _services_exports.update({
        "MemoryExtractor": MemoryExtractor, "ExtractedMemory": ExtractedMemory,
        "MemorySandbox": MemorySandbox, "get_memory_extractor": get_memory_extractor,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"memory_extract 模块加载失败: {e}")

try:
    from kairos.services.team_memory import (
        TeamMemorySyncService, TeamMemoryEntry, AgentIdentity,
        MemoryVisibility, MergeStrategy, ConflictInfo,
        get_team_memory_service,
    )
    _services_exports.update({
        "TeamMemorySyncService": TeamMemorySyncService, "TeamMemoryEntry": TeamMemoryEntry,
        "AgentIdentity": AgentIdentity, "MemoryVisibility": MemoryVisibility,
        "MergeStrategy": MergeStrategy, "ConflictInfo": ConflictInfo,
        "get_team_memory_service": get_team_memory_service,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"team_memory 模块加载失败: {e}")

try:
    from kairos.services.auto_dream import (
        DreamScheduler, DreamReport, DreamInsight, DreamPhase,
        IdleDetector, DreamSchedule, get_auto_dream_service,
    )
    _services_exports.update({
        "DreamScheduler": DreamScheduler, "DreamReport": DreamReport,
        "DreamInsight": DreamInsight, "DreamPhase": DreamPhase,
        "IdleDetector": IdleDetector, "DreamSchedule": DreamSchedule,
        "get_auto_dream_service": get_auto_dream_service,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"auto_dream 模块加载失败: {e}")

try:
    from kairos.services.bridge_system import (
        PythonBridgeServer, BridgeMessage, BridgeEndpoint,
        ServiceRegistration, BridgeMessageType, get_bridge_server,
    )
    _services_exports.update({
        "PythonBridgeServer": PythonBridgeServer, "BridgeMessage": BridgeMessage,
        "BridgeEndpoint": BridgeEndpoint, "ServiceRegistration": ServiceRegistration,
        "BridgeMessageType": BridgeMessageType, "get_bridge_server": get_bridge_server,
    })
except ImportError as e:
    import logging as _log
    _log.getLogger("services").warning(f"bridge_system 模块加载失败: {e}")
