#!/usr/bin/env python3
"""
技能路由器
提供统一的技能服务 API 接口
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/skills", tags=["skills"])


class SkillRequest(BaseModel):
    """技能请求"""
    skill_type: str = Field(..., description="技能类型: claude_mem, agency_swarm, minimax")
    skill_name: str = Field(..., description="技能名称")
    input: str = Field(..., description="输入内容")
    context: Optional[str] = Field(None, description="上下文信息")
    model: Optional[str] = Field(None, description="指定模型")
    category: Optional[str] = Field("general", description="分类")
    tags: Optional[list] = Field(None, description="标签")
    session_id: Optional[str] = Field("default", description="会话ID")


class MemoryStoreRequest(BaseModel):
    """记忆存储请求"""
    content: str = Field(..., description="记忆内容")
    category: Optional[str] = Field("general", description="分类")
    tags: Optional[list] = Field(None, description="标签")
    session_id: Optional[str] = Field("default", description="会话ID")
    model: Optional[str] = Field(None, description="指定模型")


class MemorySearchRequest(BaseModel):
    """记忆搜索请求"""
    query: str = Field(..., description="搜索查询")
    limit: Optional[int] = Field(10, description="返回数量限制")
    model: Optional[str] = Field(None, description="指定模型")


class TaskDelegateRequest(BaseModel):
    """任务委派请求"""
    task: str = Field(..., description="任务描述")
    agent_type: Optional[str] = Field("executor", description="代理类型: coordinator, executor, analyst")
    context: Optional[dict] = Field(None, description="上下文信息")
    model: Optional[str] = Field(None, description="指定模型")


class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., description="消息内容")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    model: Optional[str] = Field(None, description="指定模型")


class CreativeRequest(BaseModel):
    """创意写作请求"""
    prompt: str = Field(..., description="写作提示")
    style: Optional[str] = Field("default", description="写作风格")
    model: Optional[str] = Field(None, description="指定模型")


class CodeRequest(BaseModel):
    """代码生成请求"""
    prompt: str = Field(..., description="代码需求描述")
    language: Optional[str] = Field("python", description="编程语言")
    model: Optional[str] = Field(None, description="指定模型")


@router.post("/execute")
async def execute_skill(request: SkillRequest):
    """执行技能"""
    from ..local_service.service import get_local_skill_service, SkillType
    
    service = get_local_skill_service()
    
    try:
        skill_type = SkillType(request.skill_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的技能类型: {request.skill_type}")
    
    result = await service.execute_skill(
        skill_type=skill_type,
        skill_name=request.skill_name,
        input_data={
            "input": request.input,
            "context": request.context or "",
            "category": request.category,
            "tags": request.tags or []
        },
        model=request.model
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "执行失败"))
    
    return result


@router.post("/claude-mem/store")
async def claude_mem_store(request: MemoryStoreRequest):
    """Claude Mem: 存储记忆"""
    from ..local_service.service import get_local_skill_service
    
    service = get_local_skill_service()
    result = await service.claude_mem_store(
        content=request.content,
        category=request.category,
        tags=request.tags,
        session_id=request.session_id,
        model=request.model
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "存储失败"))
    
    return result


@router.post("/claude-mem/search")
async def claude_mem_search(request: MemorySearchRequest):
    """Claude Mem: 搜索记忆"""
    from ..local_service.service import get_local_skill_service
    
    service = get_local_skill_service()
    result = await service.claude_mem_search(
        query=request.query,
        limit=request.limit,
        model=request.model
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "搜索失败"))
    
    return result


@router.post("/claude-mem/timeline")
async def claude_mem_timeline(session_id: Optional[str] = None, limit: int = 20):
    """Claude Mem: 获取记忆时间线"""
    from ..agent_enhance.integrations.claude_mem import get_claude_mem_adapter
    
    adapter = get_claude_mem_adapter()
    result = adapter.get_timeline(session_id, limit)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "获取时间线失败"))
    
    return result


@router.post("/agency/delegate")
async def agency_delegate(request: TaskDelegateRequest):
    """Agency Swarm: 委派任务"""
    from ..local_service.service import get_local_skill_service
    
    service = get_local_skill_service()
    result = await service.agency_delegate_task(
        task=request.task,
        agent_type=request.agent_type,
        context=request.context,
        model=request.model
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "委派失败"))
    
    return result


@router.get("/agency/agents")
async def agency_list_agents():
    """Agency Swarm: 列出可用代理"""
    from ..agent_enhance.integrations.agency_agents import get_agency_agent_adapter
    
    adapter = get_agency_agent_adapter()
    return {
        "agents": adapter.list_available_agents(),
        "agency_swarm_available": adapter.agency_swarm_available
    }


@router.post("/minimax/chat")
async def minimax_chat(request: ChatRequest):
    """Minimax: 对话"""
    from ..local_service.service import get_local_skill_service
    
    service = get_local_skill_service()
    result = await service.minimax_chat(
        message=request.message,
        system_prompt=request.system_prompt,
        model=request.model
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "对话失败"))
    
    return result


@router.post("/minimax/creative")
async def minimax_creative(request: CreativeRequest):
    """Minimax: 创意写作"""
    from ..local_service.service import get_local_skill_service
    
    service = get_local_skill_service()
    result = await service.minimax_creative(
        prompt=request.prompt,
        style=request.style,
        model=request.model
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "创意写作失败"))
    
    return result


@router.post("/minimax/code")
async def minimax_code(request: CodeRequest):
    """Minimax: 代码生成"""
    from ..local_service.service import get_local_skill_service
    
    service = get_local_skill_service()
    result = await service.minimax_code(
        prompt=request.prompt,
        language=request.language,
        model=request.model
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "代码生成失败"))
    
    return result


@router.get("/health")
async def skills_health():
    """技能服务健康检查"""
    from ..local_service.service import get_local_skill_service
    
    service = get_local_skill_service()
    return await service.health_check()


@router.get("/stats")
async def skills_stats():
    """技能服务统计信息"""
    from ..local_service.service import get_local_skill_service
    
    service = get_local_skill_service()
    return service.get_stats()


@router.get("/list")
async def skills_list():
    """列出所有可用技能"""
    return {
        "claude_mem": {
            "name": "Claude Mem 记忆系统",
            "skills": ["memory_storage", "memory_retrieval", "memory_compression", "context_injection"],
            "endpoints": ["/api/skills/claude-mem/store", "/api/skills/claude-mem/search", "/api/skills/claude-mem/timeline"]
        },
        "agency_swarm": {
            "name": "Agency Swarm 多代理系统",
            "skills": ["task_decomposition", "agent_coordination", "workflow_management"],
            "endpoints": ["/api/skills/agency/delegate", "/api/skills/agency/agents"]
        },
        "minimax": {
            "name": "Minimax AI 技能系统",
            "skills": ["conversation", "creative_writing", "code_generation"],
            "endpoints": ["/api/skills/minimax/chat", "/api/skills/minimax/creative", "/api/skills/minimax/code"]
        }
    }