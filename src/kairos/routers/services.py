"""
服务路由
将命令系统、工具系统、MCP、压缩、LSP 服务暴露为 API 端点
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/services", tags=["服务"])


class CommandRequest(BaseModel):
    input: str = Field(..., min_length=1, max_length=10000)

    @field_validator('input')
    @classmethod
    def sanitize_input(cls, v):
        return v.strip()


class ToolExecuteRequest(BaseModel):
    tool_name: str = Field(..., min_length=1, max_length=200)
    params: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)


class CompactRequest(BaseModel):
    messages: List[Dict[str, str]] = Field(..., min_length=1)
    level: Optional[str] = None


class McpConnectRequest(BaseModel):
    server_name: str = Field(..., min_length=1, max_length=200)


class McpCallToolRequest(BaseModel):
    tool_name: str = Field(..., min_length=1, max_length=500)
    arguments: Dict[str, Any] = Field(default_factory=dict)


class LspStartRequest(BaseModel):
    server_name: str = Field(..., min_length=1, max_length=200)
    root_path: str = ""


class LspRequest(BaseModel):
    file_path: str = Field(..., min_length=1, max_length=1000)
    line: int = Field(default=0, ge=0)
    column: int = Field(default=0, ge=0)


_registry = None
_dispatcher = None
_tool_registry = None


def init_service_deps(registry, dispatcher, tool_registry):
    global _registry, _dispatcher, _tool_registry
    _registry = registry
    _dispatcher = dispatcher
    _tool_registry = tool_registry


@router.get("/commands")
async def list_commands(query: str = ""):
    """列出可用命令"""
    if not _registry:
        raise HTTPException(status_code=503, detail="命令系统未初始化")
    if query:
        cmds = _registry.search(query)
    else:
        cmds = _registry.list_commands()
    return {
        "success": True,
        "commands": [
            {
                "name": c.name,
                "type": c.type.value,
                "description": c.description,
                "aliases": c.aliases,
                "usage": c.usage,
                "category": c.category,
                "requires_llm": c.requires_llm,
            }
            for c in cmds
        ]
    }


@router.post("/commands/execute")
async def execute_command(request: CommandRequest):
    """执行命令"""
    if not _dispatcher:
        raise HTTPException(status_code=503, detail="命令调度器未初始化")

    import asyncio
    result = await _dispatcher.dispatch(request.input)
    return {
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "command_name": result.command_name,
        "duration_ms": result.duration_ms,
        "data": result.data,
    }


@router.get("/commands/stats")
async def command_stats():
    """命令执行统计"""
    if not _registry:
        raise HTTPException(status_code=503, detail="命令系统未初始化")
    return {"success": True, "stats": _registry.get_stats()}


@router.get("/tools")
async def list_tools(category: str = ""):
    """列出可用工具"""
    if not _tool_registry:
        raise HTTPException(status_code=503, detail="工具系统未初始化")
    if category:
        by_cat = _tool_registry.list_by_category()
        tools = by_cat.get(category, [])
    else:
        tools = _tool_registry.list_tools()
    return {"success": True, "tools": tools}


@router.post("/tools/execute")
async def execute_tool(request: ToolExecuteRequest):
    """执行工具"""
    if not _tool_registry:
        raise HTTPException(status_code=503, detail="工具系统未初始化")

    result = await _tool_registry.execute(
        request.tool_name, request.params, request.context
    )
    return {
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "tool_name": result.tool_name,
        "duration_ms": result.duration_ms,
        "data": result.data,
    }


@router.get("/tools/stats")
async def tool_stats():
    """工具执行统计"""
    if not _tool_registry:
        raise HTTPException(status_code=503, detail="工具系统未初始化")
    return {"success": True, "stats": _tool_registry.get_stats()}


@router.post("/compact")
async def compact_messages(request: CompactRequest):
    """压缩对话历史"""
    try:
        from kairos.services.compact import get_compact_service, CompactLevel
        cs = get_compact_service()

        level = None
        if request.level:
            try:
                level = CompactLevel[request.level.upper()]
            except KeyError:
                pass

        result = await cs.compact(request.messages, level)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 代理引擎端点 ====================

class AgentRunRequest(BaseModel):
    message: str = Field(..., min_length=1)
    model: str = ""
    system_prompt: str = ""
    max_turns: int = 10


class HookRegisterRequest(BaseModel):
    event: str = Field(..., min_length=1)
    tool_name: str = ""
    timeout: int = 30


@router.get("/agent/status")
async def get_agent_status():
    """获取代理引擎状态"""
    try:
        from kairos.services.agent_engine import get_agent_engine
        engine = get_agent_engine()
        return {"success": True, "status": engine.get_stats()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/run")
async def run_agent(request: AgentRunRequest):
    """运行代理循环（每次请求独立引擎实例）"""
    try:
        from kairos.services.agent_engine import AgentEngine, LoopState
        max_turns = min(request.max_turns or 50, 50)
        engine = AgentEngine(
            max_turns=max_turns,
        )
        if request.system_prompt:
            engine._system_prompt = request.system_prompt[:4000]
        if request.model:
            engine._model = request.model

        response = await engine.run(request.message)
        return {
            "success": True,
            "response": response,
            "turn_count": engine.turn_count,
            "state": engine.state.value,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/hooks")
async def list_hooks():
    """列出所有钩子"""
    try:
        from kairos.services.agent_engine import get_agent_engine
        engine = get_agent_engine()
        return {"success": True, "hooks": engine.hook_manager.list_hooks()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 子代理端点 ====================

class SubAgentRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    name: str = ""
    description: str = ""
    model: str = "gemma4:e4b"
    max_turns: int = 10
    run_async: bool = False


@router.get("/subagent/tasks")
async def list_subagent_tasks():
    """列出子代理任务"""
    try:
        from kairos.services.sub_agent import get_sub_agent_runner
        runner = get_sub_agent_runner()
        return {"success": True, "tasks": runner.list_tasks()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subagent/stats")
async def subagent_stats():
    """子代理统计"""
    try:
        from kairos.services.sub_agent import get_sub_agent_runner
        runner = get_sub_agent_runner()
        return {"success": True, "stats": runner.get_stats()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subagent/run")
async def run_subagent(request: SubAgentRequest):
    """运行子代理"""
    try:
        from kairos.services.sub_agent import get_sub_agent_runner
        runner = get_sub_agent_runner()
        task = runner.create_task(
            prompt=request.prompt,
            name=request.name,
            description=request.description,
            model=request.model,
            max_turns=request.max_turns,
        )
        if request.run_async:
            await runner.run_async(task)
            return {"success": True, "task_id": task.id, "status": "async_launched"}
        else:
            result = await runner.run_sync(task)
            return {"success": result.status.value == "completed", "task_id": result.id,
                    "result": result.result, "error": result.error}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subagent/tasks/{task_id}")
async def get_subagent_task(task_id: str):
    """获取子代理任务详情"""
    try:
        from kairos.services.sub_agent import get_sub_agent_runner
        runner = get_sub_agent_runner()
        task = runner.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        return {"success": True, "task": task.to_dict()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 技能端点 ====================

class SkillExecuteRequest(BaseModel):
    name: str = Field(..., min_length=1)
    args: str = ""


@router.get("/skills")
async def list_skills():
    """列出所有技能"""
    try:
        from kairos.services.skill import get_skill_manager
        sm = get_skill_manager()
        return {"success": True, "skills": sm.list_skills()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/skills/execute")
async def execute_skill(request: SkillExecuteRequest):
    """执行技能"""
    try:
        from kairos.services.skill import get_skill_manager
        sm = get_skill_manager()
        result = await sm.execute_skill(request.name, request.args)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/skills/stats")
async def skill_stats():
    """技能统计"""
    try:
        from kairos.services.skill import get_skill_manager
        sm = get_skill_manager()
        return {"success": True, "stats": sm.get_stats()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 待办端点 ====================

class TodoUpdateRequest(BaseModel):
    key: str = "default"
    todos: List[Dict[str, Any]] = Field(default_factory=list)


class TodoAddRequest(BaseModel):
    key: str = "default"
    content: str = Field(..., min_length=1)
    priority: int = 0


class TodoStatusRequest(BaseModel):
    key: str = "default"
    todo_id: str = Field(..., min_length=1)
    status: str = Field(..., min_length=1)


@router.get("/todos/stats")
async def todo_stats(key: str = ""):
    """待办统计"""
    try:
        from kairos.services.todo import get_todo_manager
        tm = get_todo_manager()
        return {"success": True, "stats": tm.get_stats(key or None)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/todos/{key}")
async def get_todos(key: str = "default"):
    """获取待办列表"""
    try:
        from kairos.services.todo import get_todo_manager
        tm = get_todo_manager()
        return {"success": True, "todos": tm.get_todos(key)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/todos/update")
async def update_todos(request: TodoUpdateRequest):
    """更新待办列表"""
    try:
        from kairos.services.todo import get_todo_manager
        tm = get_todo_manager()
        result = tm.update_todos(request.key, request.todos)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/todos/add")
async def add_todo(request: TodoAddRequest):
    """添加待办项"""
    try:
        from kairos.services.todo import get_todo_manager
        tm = get_todo_manager()
        result = tm.add_todo(request.key, request.content, request.priority)
        return {"success": True, "id": result.get("id", "")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/todos/status")
async def update_todo_status(request: TodoStatusRequest):
    """更新待办状态"""
    try:
        from kairos.services.todo import get_todo_manager
        tm = get_todo_manager()
        result = tm.update_status(request.key, request.todo_id, request.status)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 会话管理端点 ====================

class SessionCreateRequest(BaseModel):
    title: str = ""
    model: str = "gemma4:e4b"


class SessionMessageRequest(BaseModel):
    session_id: str = ""
    role: str = "user"
    content: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.get("/sessions")
async def list_sessions():
    """列出所有会话"""
    try:
        from kairos.services.session import get_session_manager
        sm = get_session_manager()
        return {"success": True, "sessions": sm.list_sessions()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/create")
async def create_session(request: SessionCreateRequest):
    """创建新会话"""
    try:
        from kairos.services.session import get_session_manager
        sm = get_session_manager()
        session = sm.create_session(title=request.title, model=request.model)
        return {"success": True, "session": session.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """获取会话详情"""
    try:
        from kairos.services.session import get_session_manager
        sm = get_session_manager()
        session = sm.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        return {"success": True, "session": session.to_dict()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/message")
async def add_session_message(request: SessionMessageRequest):
    """添加会话消息"""
    try:
        from kairos.services.session import get_session_manager
        sm = get_session_manager()
        msg = sm.add_message(
            role=request.role,
            content=request.content,
            session_id=request.session_id or None,
            metadata=request.metadata,
        )
        return {"success": True, "message": msg.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    try:
        from kairos.services.session import get_session_manager
        sm = get_session_manager()
        deleted = sm.delete_session(session_id)
        return {"success": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 权限管理端点 ====================

class PermissionRuleRequest(BaseModel):
    tool_name: str = Field(..., min_length=1)
    behavior: str = "ask"
    rule_content: str = ""
    source: str = "user"


class PermissionModeRequest(BaseModel):
    mode: str = Field(..., min_length=1)


@router.get("/permissions/rules")
async def list_permission_rules():
    """列出权限规则"""
    try:
        from kairos.services.permission import get_permission_checker
        pc = get_permission_checker()
        return {"success": True, "rules": pc.list_rules(), "status": pc.get_status()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/permissions/rules")
async def add_permission_rule(request: PermissionRuleRequest):
    """添加权限规则"""
    try:
        from kairos.services.permission import get_permission_checker, RuleBehavior, PermissionRule
        pc = get_permission_checker()
        behavior = RuleBehavior(request.behavior)
        rule = PermissionRule(
            tool_name=request.tool_name,
            behavior=behavior,
            rule_content=request.rule_content,
            source=request.source,
        )
        pc.add_rule(rule)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/permissions/mode")
async def set_permission_mode(request: PermissionModeRequest):
    """设置权限模式"""
    try:
        from kairos.services.permission import get_permission_checker, PermissionMode
        pc = get_permission_checker()
        mode = PermissionMode(request.mode)
        pc.set_mode(mode)
        return {"success": True, "mode": mode.value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/permissions/check")
async def check_permission(request: PermissionRuleRequest):
    """检查权限"""
    try:
        from kairos.services.permission import get_permission_checker
        pc = get_permission_checker()
        result = pc.check_permission(request.tool_name, request.rule_content)
        return {
            "success": True,
            "allowed": result.allowed,
            "behavior": result.behavior.value,
            "reason": result.reason,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compact/stats")
async def compact_stats():
    """压缩服务统计"""
    try:
        from kairos.services.compact import get_compact_service
        cs = get_compact_service()
        return {"success": True, "stats": cs.get_stats()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mcp/servers")
async def list_mcp_servers():
    """列出 MCP 服务器"""
    try:
        from kairos.services.mcp import get_mcp_manager
        mm = get_mcp_manager()
        return {"success": True, "servers": mm.list_servers()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mcp/connect")
async def connect_mcp_server(request: McpConnectRequest):
    """连接 MCP 服务器"""
    try:
        from kairos.services.mcp import get_mcp_manager
        mm = get_mcp_manager()
        success = await mm.connect_server(request.server_name)
        return {"success": success, "server": request.server_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mcp/disconnect")
async def disconnect_mcp_server(request: McpConnectRequest):
    """断开 MCP 服务器"""
    try:
        from kairos.services.mcp import get_mcp_manager
        mm = get_mcp_manager()
        await mm.disconnect_server(request.server_name)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mcp/tools")
async def list_mcp_tools(server_name: str = ""):
    """列出 MCP 工具"""
    try:
        from kairos.services.mcp import get_mcp_manager
        mm = get_mcp_manager()
        return {"success": True, "tools": mm.list_tools(server_name or None)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mcp/call-tool")
async def call_mcp_tool(request: McpCallToolRequest):
    """调用 MCP 工具"""
    try:
        from kairos.services.mcp import get_mcp_manager
        mm = get_mcp_manager()
        result = await mm.call_tool(request.tool_name, request.arguments)
        return {"success": "error" not in result, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lsp/servers")
async def list_lsp_servers():
    """列出 LSP 服务器"""
    try:
        from kairos.services.lsp import get_lsp_manager
        lm = get_lsp_manager()
        return {"success": True, "servers": lm.list_servers()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lsp/start")
async def start_lsp_server(request: LspStartRequest):
    """启动 LSP 服务器"""
    try:
        from kairos.services.lsp import get_lsp_manager
        lm = get_lsp_manager()
        success = await lm.start_server(request.server_name, request.root_path)
        return {"success": success, "server": request.server_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lsp/diagnostics")
async def get_lsp_diagnostics(request: LspRequest):
    """获取文件诊断"""
    try:
        from kairos.services.lsp import get_lsp_manager
        lm = get_lsp_manager()
        diags = await lm.get_diagnostics(request.file_path)
        return {
            "success": True,
            "diagnostics": [
                {
                    "line": d.line,
                    "column": d.column,
                    "severity": d.severity,
                    "message": d.message,
                    "source": d.source,
                    "code": d.code,
                }
                for d in diags
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lsp/definition")
async def get_lsp_definition(request: LspRequest):
    """获取定义位置"""
    try:
        from kairos.services.lsp import get_lsp_manager
        lm = get_lsp_manager()
        locations = await lm.get_definition(request.file_path, request.line, request.column)
        return {
            "success": True,
            "locations": [
                {"file_path": l.file_path, "line": l.line, "column": l.column}
                for l in locations
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lsp/hover")
async def get_lsp_hover(request: LspRequest):
    """获取悬停信息"""
    try:
        from kairos.services.lsp import get_lsp_manager
        lm = get_lsp_manager()
        hover = await lm.get_hover(request.file_path, request.line, request.column)
        if hover:
            return {"success": True, "contents": hover.contents}
        return {"success": True, "contents": ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lsp/references")
async def get_lsp_references(request: LspRequest):
    """获取引用位置"""
    try:
        from kairos.services.lsp import get_lsp_manager
        lm = get_lsp_manager()
        locations = await lm.get_references(request.file_path, request.line, request.column)
        return {
            "success": True,
            "locations": [
                {"file_path": l.file_path, "line": l.line, "column": l.column}
                for l in locations
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lsp/symbols")
async def get_lsp_symbols(request: LspRequest):
    """获取文档符号"""
    try:
        from kairos.services.lsp import get_lsp_manager
        lm = get_lsp_manager()
        symbols = await lm.get_document_symbols(request.file_path)
        return {
            "success": True,
            "symbols": [
                {"name": s.name, "kind": s.kind, "line": s.line, "container": s.container_name}
                for s in symbols
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Token 追踪端点 ====================

class TokenRecordRequest(BaseModel):
    model: str = Field(..., min_length=1)
    input_tokens: int = Field(..., ge=0)
    output_tokens: int = Field(..., ge=0)
    cache_read: int = 0
    cache_creation: int = 0


@router.get("/tokens/stats")
async def token_stats():
    """获取 Token 使用统计"""
    try:
        from kairos.services.token_tracker import get_token_tracker
        tt = get_token_tracker()
        return {"success": True, "stats": tt.get_stats()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tokens/record")
async def record_token_usage(request: TokenRecordRequest):
    """记录 Token 使用"""
    try:
        from kairos.services.token_tracker import get_token_tracker
        tt = get_token_tracker()
        usage = tt.record_usage(
            model=request.model,
            input_tokens=request.input_tokens,
            output_tokens=request.output_tokens,
            cache_read=request.cache_read,
            cache_creation=request.cache_creation,
        )
        return {"success": True, "total_tokens": usage.total_tokens}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tokens/budget")
async def check_token_budget():
    """检查 Token 预算"""
    try:
        from kairos.services.token_tracker import get_token_tracker
        tt = get_token_tracker()
        decision = tt.check_budget()
        return {
            "success": True,
            "should_continue": decision.should_continue,
            "reason": decision.reason,
            "usage_percent": round(decision.usage_percent, 3),
            "remaining_tokens": decision.remaining_tokens,
            "diminishing_returns": decision.diminishing_returns,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tokens/model-usage")
async def token_model_usage(model: str = ""):
    """获取模型 Token 使用"""
    try:
        from kairos.services.token_tracker import get_token_tracker
        tt = get_token_tracker()
        return {"success": True, "usage": tt.get_model_usage(model or None)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 全局状态端点 ====================

class BootstrapModeRequest(BaseModel):
    mode: str = Field(..., min_length=1)


class BootstrapHookRequest(BaseModel):
    event_type: str = Field(..., min_length=1)
    config: Dict[str, Any] = Field(default_factory=dict)


@router.get("/bootstrap/state")
async def get_bootstrap_state():
    """获取全局状态"""
    try:
        from kairos.services.bootstrap import get_bootstrap_state
        bs = get_bootstrap_state()
        return {"success": True, "state": bs.get_full_state()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bootstrap/mode")
async def set_bootstrap_mode(request: BootstrapModeRequest):
    """设置代理模式"""
    try:
        from kairos.services.bootstrap import get_bootstrap_state, AgentMode
        bs = get_bootstrap_state()
        mode = AgentMode(request.mode)
        success = bs.set_mode(mode)
        return {"success": success, "mode": bs.mode.value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bootstrap/hook")
async def register_bootstrap_hook(request: BootstrapHookRequest):
    """注册 Hook"""
    try:
        from kairos.services.bootstrap import get_bootstrap_state
        bs = get_bootstrap_state()
        bs.register_hook(request.event_type, request.config)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bootstrap/hooks")
async def list_bootstrap_hooks(event_type: str = ""):
    """列出已注册的 Hook"""
    try:
        from kairos.services.bootstrap import get_bootstrap_state
        bs = get_bootstrap_state()
        return {"success": True, "hooks": bs.get_hooks(event_type or None)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bootstrap/save")
async def save_bootstrap_state():
    """持久化全局状态"""
    try:
        from kairos.services.bootstrap import get_bootstrap_state
        bs = get_bootstrap_state()
        bs.save_to_disk()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 上下文窗口端点 ====================

class ContextAnalyzeRequest(BaseModel):
    messages: List[Dict[str, str]] = Field(default_factory=list)


@router.get("/context/stats")
async def context_stats():
    """获取上下文窗口统计"""
    try:
        from kairos.services.context_window import get_context_window_manager
        cwm = get_context_window_manager()
        return {"success": True, "stats": cwm.get_stats()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/context/analyze")
async def analyze_context(request: ContextAnalyzeRequest):
    """分析上下文 Token 分布"""
    try:
        from kairos.services.context_window import get_context_window_manager
        cwm = get_context_window_manager()
        analysis = cwm.analyze_context(request.messages)
        return {
            "success": True,
            "analysis": {
                "total_tokens": analysis.total_tokens,
                "context_window": analysis.context_window,
                "usage_percent": round(analysis.usage_percent, 3),
                "remaining_tokens": analysis.remaining_tokens,
                "is_near_limit": analysis.is_near_limit,
                "by_category": analysis.by_category,
                "by_role": analysis.by_role,
                "duplicate_file_reads": analysis.duplicate_file_reads,
                "suggestions": analysis.suggestions,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context/upgrade-check")
async def check_context_upgrade():
    """检查上下文窗口升级"""
    try:
        from kairos.services.context_window import get_context_window_manager
        cwm = get_context_window_manager()
        check = cwm.check_upgrade()
        return {
            "success": True,
            "current_window": check.current_window,
            "available_windows": check.available_windows,
            "can_upgrade": check.can_upgrade,
            "upgrade_model": check.upgrade_model,
            "reason": check.reason,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/context/invalidate")
async def invalidate_context_cache():
    """使上下文缓存失效"""
    try:
        from kairos.services.context_window import get_context_window_manager
        cwm = get_context_window_manager()
        cwm.invalidate_cache()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 自动分类器端点 ====================

class ClassifyRequest(BaseModel):
    tool_name: str = Field(..., min_length=1)
    tool_input: str = Field(..., min_length=1)
    messages: List[Dict[str, str]] = Field(default_factory=list)


class ClassifierRuleRequest(BaseModel):
    pattern: str = Field(..., min_length=1)
    rule_type: str = "allow"
    description: str = ""
    tool_name: str = ""


@router.post("/classifier/classify")
async def classify_tool_call(request: ClassifyRequest):
    """分类工具调用权限"""
    try:
        from kairos.services.auto_classifier import get_auto_classifier
        ac = get_auto_classifier()
        decision = await ac.classify(request.tool_name, request.tool_input, request.messages)
        return {
            "success": True,
            "result": decision.result.value,
            "reason": decision.reason,
            "stage": decision.stage,
            "confidence": decision.confidence,
            "rule_matched": decision.rule_matched,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/classifier/stats")
async def classifier_stats():
    """获取分类器统计"""
    try:
        from kairos.services.auto_classifier import get_auto_classifier
        ac = get_auto_classifier()
        return {"success": True, "stats": ac.get_stats()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classifier/rules")
async def add_classifier_rule(request: ClassifierRuleRequest):
    """添加分类器规则"""
    try:
        from kairos.services.auto_classifier import get_auto_classifier, ClassificationRule, RuleType
        ac = get_auto_classifier()
        rule = ClassificationRule(
            pattern=request.pattern,
            rule_type=RuleType(request.rule_type),
            description=request.description,
            tool_name=request.tool_name or None,
        )
        ac.add_rule(rule)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 成本追踪端点 ====================

class CostRecordRequest(BaseModel):
    model: str = Field(..., min_length=1)
    input_tokens: int = Field(..., ge=0)
    output_tokens: int = Field(..., ge=0)
    cache_read: int = 0
    cache_creation: int = 0


@router.get("/cost/total")
async def get_total_cost():
    """获取总成本"""
    try:
        from kairos.services.cost_tracker import get_cost_tracker
        ct = get_cost_tracker()
        return {"success": True, "cost": ct.get_total_cost()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cost/record")
async def record_cost(request: CostRecordRequest):
    """记录成本"""
    try:
        from kairos.services.cost_tracker import get_cost_tracker
        ct = get_cost_tracker()
        ct.record_usage(
            model=request.model,
            input_tokens=request.input_tokens,
            output_tokens=request.output_tokens,
            cache_read=request.cache_read,
            cache_creation=request.cache_creation,
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost/report")
async def get_cost_report():
    """获取成本报告"""
    try:
        from kairos.services.cost_tracker import get_cost_tracker
        ct = get_cost_tracker()
        return {"success": True, "report": ct.format_cost_report()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost/model/{model}")
async def get_model_cost(model: str):
    """获取模型成本"""
    try:
        from kairos.services.cost_tracker import get_cost_tracker
        ct = get_cost_tracker()
        return {"success": True, "cost": ct.get_model_cost(model)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Hook 生命周期端点 ====================

class HookRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1)
    event: str = Field(..., min_length=1)
    hook_type: str = "command"
    source: str = "builtin"
    matcher: str = ""
    command: str = ""
    prompt: str = ""
    url: str = ""
    timeout: float = 30.0


@router.get("/hooks/list")
async def list_hooks(event: str = ""):
    """列出所有 Hook"""
    try:
        from kairos.services.hooks import get_hook_registry
        registry = get_hook_registry()
        hooks = registry.list_all_hooks()
        if event:
            hooks = {k: v for k, v in hooks.items() if k == event}
        return {"success": True, "hooks": hooks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hooks/register")
async def register_hook(request: HookRegisterRequest):
    """注册 Hook"""
    try:
        from kairos.services.hooks import (
            get_hook_registry, HookDefinition, HookEvent, HookType, HookSource,
        )
        registry = get_hook_registry()
        hook = HookDefinition(
            name=request.name,
            event=HookEvent(request.event),
            hook_type=HookType(request.hook_type),
            source=HookSource(request.source),
            matcher=request.matcher,
            command=request.command,
            prompt_text=request.prompt,
            url=request.url,
            timeout=request.timeout,
        )
        registry.register(hook)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hooks/fire")
async def fire_hook(event: str, context: Dict[str, Any] = Body(default={})):
    """触发 Hook"""
    try:
        from kairos.services.hooks import get_hook_registry, HookEvent
        registry = get_hook_registry()
        result = await registry.fire(HookEvent(event), context)
        return {
            "success": True,
            "allowed": result.allowed,
            "reason": result.reason,
            "source_hook": result.source_hook,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/hooks/{name}")
async def unregister_hook(name: str):
    """取消注册 Hook"""
    try:
        from kairos.services.hooks import get_hook_registry
        registry = get_hook_registry()
        success = registry.unregister(name)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 记忆提取端点 ====================

class MemoryExtractRequest(BaseModel):
    messages: List[Dict[str, str]] = Field(default_factory=list)


class MemorySearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    category: str = ""
    limit: int = 10


@router.get("/memory/stats")
async def memory_stats():
    """获取记忆提取统计"""
    try:
        from kairos.services.memory_extract import get_memory_extractor
        me = get_memory_extractor()
        return {"success": True, "stats": me.get_stats()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/extract")
async def extract_memory(request: MemoryExtractRequest):
    """手动触发记忆提取"""
    try:
        from kairos.services.memory_extract import get_memory_extractor
        me = get_memory_extractor()
        memories = await me.extract(request.messages)
        return {
            "success": True,
            "count": len(memories),
            "memories": [m.to_dict() for m in memories],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/search")
async def search_memory(request: MemorySearchRequest):
    """搜索记忆"""
    try:
        from kairos.services.memory_extract import get_memory_extractor
        me = get_memory_extractor()
        results = me.search_memories(request.query, request.category or None, request.limit)
        return {
            "success": True,
            "count": len(results),
            "memories": [m.to_dict() for m in results],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/list")
async def list_memory(category: str = ""):
    """列出记忆"""
    try:
        from kairos.services.memory_extract import get_memory_extractor
        me = get_memory_extractor()
        memories = me.load_memories(category or None)
        return {
            "success": True,
            "count": len(memories),
            "memories": [m.to_dict() for m in memories[:50]],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 团队记忆同步端点 ====================

class TeamMemoryShareRequest(BaseModel):
    key: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    visibility: str = "team"
    merge_strategy: str = "last_write_wins"
    tags: List[str] = Field(default_factory=list)


class TeamMemoryQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)
    visibility: str = ""
    limit: int = Field(default=10, ge=1, le=50)


class TeamMemoryConflictRequest(BaseModel):
    key: str = Field(..., min_length=1)
    resolution: str = Field(default="local")
    merged_content: str = ""


@router.get("/team-memory/keys")
async def list_team_memory_keys():
    """获取团队记忆所有键"""
    try:
        from kairos.services.team_memory import get_team_memory_service
        tms = get_team_memory_service()
        return {"success": True, "keys": tms.get_all_keys()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/team-memory/share")
async def share_team_memory(request: TeamMemoryShareRequest):
    """共享记忆到团队"""
    try:
        from kairos.services.team_memory import get_team_memory_service, AgentIdentity, MemoryVisibility, MergeStrategy
        tms = get_team_memory_service()
        vis_enum = MemoryVisibility(request.visibility) if request.visibility else MemoryVisibility.TEAM
        ms_enum = MergeStrategy(request.merge_strategy) if request.merge_strategy else MergeStrategy.LAST_WRITE_WINS
        entry = await tms.share_memory(
            key=request.key,
            content=request.content,
            visibility=vis_enum,
            merge_strategy=ms_enum,
            tags=request.tags,
        )
        return {"success": True, "entry_id": entry.entry_id, "version": entry.version}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/team-memory/query")
async def query_team_memory(request: TeamMemoryQueryRequest):
    """查询团队记忆"""
    try:
        from kairos.services.team_memory import get_team_memory_service, MemoryVisibility
        tms = get_team_memory_service()
        vis = None
        if request.visibility:
            try:
                vis = MemoryVisibility(request.visibility)
            except ValueError:
                pass
        entries = await tms.query_team_memory(
            query=request.query,
            tags=request.tags or None,
            visibility=vis,
            limit=request.limit,
        )
        return {"success": True, "count": len(entries), "entries": [e.to_dict() for e in entries]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/team-memory/{key}")
async def get_team_memory(key: str):
    """按key获取团队记忆"""
    try:
        from kairos.services.team_memory import get_team_memory_service
        tms = get_team_memory_service()
        entries = await tms.get_memory_by_key(key)
        return {"success": True, "key": key, "entries": [e.to_dict() for e in entries]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/team-memory/{key}")
async def delete_team_memory(key: str):
    """删除团队记忆"""
    try:
        from kairos.services.team_memory import get_team_memory_service
        tms = get_team_memory_service()
        deleted = await tms.delete_memory(key=key)
        return {"success": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/team-memory/conflict/resolve")
async def resolve_conflict(request: TeamMemoryConflictRequest):
    """解决记忆冲突"""
    try:
        from kairos.services.team_memory import get_team_memory_service
        tms = get_team_memory_service()
        entry = await tms.resolve_conflict(
            key=request.key,
            resolution=request.resolution,
            merged_content=request.merged_content or None,
        )
        if entry:
            return {"success": True, "entry": entry.to_dict()}
        return {"success": False, "error": "冲突不存在或已解决"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/team-memory/stats")
async def team_memory_stats():
    """团队记忆统计"""
    try:
        from kairos.services.team_memory import get_team_memory_service
        tms = get_team_memory_service()
        return {"success": True, "stats": tms.get_stats(), "conflicts": tms.get_conflicts()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/team-memory/export")
async def export_team_memory():
    """导出团队记忆"""
    try:
        from kairos.services.team_memory import get_team_memory_service
        tms = get_team_memory_service()
        path = tms.export_memories()
        return {"success": True, "export_path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 自动梦境端点 ====================

@router.get("/dream/status")
async def dream_status():
    """获取自动梦境状态"""
    try:
        from kairos.services.auto_dream import get_auto_dream_service
        ds = get_auto_dream_service()
        idle_state = await ds.get_idle_state()
        return {
            "success": True,
            "stats": ds.get_stats(),
            "idle_state": idle_state.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dream/force")
async def force_dream():
    """强制触发一次梦境"""
    try:
        from kairos.services.auto_dream import get_auto_dream_service
        ds = get_auto_dream_service()
        report = await ds.force_dream()
        if report:
            return {"success": True, "report": report.to_dict()}
        return {"success": False, "error": "梦境执行失败"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dream/history")
async def dream_history(limit: int = 10):
    """获取梦境历史"""
    try:
        from kairos.services.auto_dream import get_auto_dream_service
        ds = get_auto_dream_service()
        return {"success": True, "history": ds.get_dream_history(limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dream/insights/pending")
async def pending_insights():
    """获取待处理洞察"""
    try:
        from kairos.services.auto_dream import get_auto_dream_service
        ds = get_auto_dream_service()
        return {"success": True, "insights": ds.get_pending_insights()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dream/insights/{insight_id}/approve")
async def approve_insight(insight_id: str):
    """批准洞察"""
    try:
        from kairos.services.auto_dream import get_auto_dream_service
        ds = get_auto_dream_service()
        approved = ds.approve_insight(insight_id)
        return {"success": approved}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dream/insights/{insight_id}/reject")
async def reject_insight(insight_id: str):
    """拒绝洞察"""
    try:
        from kairos.services.auto_dream import get_auto_dream_service
        ds = get_auto_dream_service()
        rejected = ds.reject_insight(insight_id)
        return {"success": rejected}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 桥接系统端点 ====================

@router.get("/bridge/status")
async def bridge_status():
    """获取桥接系统状态"""
    try:
        from kairos.services.bridge_system import get_bridge_server
        bs = get_bridge_server()
        return {"success": True, "stats": bs.get_stats()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bridge/services")
async def list_bridge_services():
    """列出桥接服务"""
    try:
        from kairos.services.bridge_system import get_bridge_server
        bs = get_bridge_server()
        return {"success": True, "services": bs.get_services()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bridge/connections")
async def list_bridge_connections():
    """列出桥接连接"""
    try:
        from kairos.services.bridge_system import get_bridge_server
        bs = get_bridge_server()
        return {"success": True, "connections": bs.get_connections()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bridge/messages")
async def bridge_messages(limit: int = 50, message_type: str = ""):
    """获取桥接消息历史"""
    try:
        from kairos.services.bridge_system import get_bridge_server
        bs = get_bridge_server()
        return {"success": True, "messages": bs.get_message_history(limit, message_type)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bridge/send")
async def send_bridge_message(message_type: str = "", payload: Dict[str, Any] = Body(default={})):
    """发送桥接消息"""
    try:
        from kairos.services.bridge_system import get_bridge_server
        bs = get_bridge_server()
        result = await bs.send_message(message_type=message_type, payload=payload)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
