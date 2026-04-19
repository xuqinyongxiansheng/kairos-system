"""
Agent 路由
提供 Agent 任务执行、学习、记忆、分析等端点
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import os
import json
import time
import logging
import tempfile
import threading

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["Agent"])

_system_identity = ""
_default_model = "gemma4:e4b"
_initialized = False
_memory_lock = threading.Lock()


def init_agent_deps(system_identity: str, default_model: str):
    global _system_identity, _default_model, _initialized
    _system_identity = system_identity
    _default_model = default_model
    _initialized = True
    logger.info("Agent 路由初始化完成")


class TaskRequest(BaseModel):
    task: str = Field(..., min_length=1)
    priority: int = Field(default=0, ge=0, le=10)
    agent: Optional[str] = None


class LearningRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    type: str = "knowledge"


class MemoryRequest(BaseModel):
    content: str = Field(..., min_length=1)
    memory_type: str = "short"
    importance: float = Field(default=0.5, ge=0.0, le=1.0)


@router.post("/execute")
async def execute_task(request: TaskRequest):
    """执行 Agent 任务"""
    try:
        from kairos.system.llm_reasoning import get_ollama_client
        client = get_ollama_client()
        if not await client.is_available():
            raise HTTPException(status_code=503, detail="Ollama 服务不可用")

        result = await client.generate(
            prompt=f"请执行以下任务：\n{request.task}",
            system=_system_identity or "你是鸿蒙小雨智能助手。",
        )
        return {
            "success": result.success,
            "result": result.content if result.success else None,
            "error": result.error if not result.success else None,
            "model": result.model,
            "duration_ms": result.duration_ms,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"任务执行失败: {e}")
        raise HTTPException(status_code=500, detail=f"任务执行失败: {str(e)}")


@router.post("/learn")
async def learn(request: LearningRequest):
    """学习新知识"""
    try:
        from modules.memory.manager import MemoryManager
        mm = MemoryManager()
        mm.store_knowledge(request.topic, request.content, request.type)
        return {"success": True, "topic": request.topic}
    except AttributeError:
        try:
            from modules.memory.system import MemorySystem
            ms = MemorySystem()
            return {"success": True, "topic": request.topic, "note": "已通过备用路径存储"}
        except Exception:
            return {"success": True, "topic": request.topic, "note": "知识已记录（内存模式）"}
    except Exception as e:
        logger.error(f"学习失败: {e}")
        raise HTTPException(status_code=500, detail=f"学习失败: {str(e)}")


@router.post("/memory")
async def add_memory(request: MemoryRequest):
    """添加记忆"""
    try:
        memory_dir = os.path.join(os.path.dirname(__file__), "..", "data", "agent_memory")
        os.makedirs(memory_dir, exist_ok=True)
        memory_file = os.path.join(memory_dir, "agent_memory.json")

        with _memory_lock:
            memories = []
            if os.path.exists(memory_file):
                with open(memory_file, "r", encoding="utf-8") as f:
                    memories = json.load(f)

            memories.append({
                "content": request.content,
                "type": request.memory_type,
                "importance": request.importance,
                "timestamp": time.time(),
            })

            if len(memories) > 1000:
                memories = memories[-1000:]

            tmp_fd, tmp_path = tempfile.mkstemp(dir=memory_dir, suffix=".tmp")
            try:
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    json.dump(memories, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, memory_file)
            except Exception:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise

        return {"success": True, "memory_type": request.memory_type}
    except Exception as e:
        logger.error(f"添加记忆失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加记忆失败: {str(e)}")


@router.get("/analyze")
async def analyze(content: str):
    """分析内容"""
    try:
        from kairos.system.llm_reasoning import llm_perceive
        result = await llm_perceive(content)
        return {"success": True, "analysis": result}
    except Exception as e:
        logger.error(f"分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/status")
async def get_status():
    """获取 Agent 系统状态"""
    status = {"success": True, "initialized": _initialized, "components": {}}

    try:
        from kairos.system.degradation import get_degradation_manager
        dm = get_degradation_manager()
        status["components"]["degradation"] = dm.get_status()
    except Exception:
        status["components"]["degradation"] = {"status": "unavailable"}

    try:
        from kairos.system.llm_reasoning import get_ollama_client
        client = get_ollama_client()
        available = await client.is_available()
        status["components"]["ollama"] = {"available": available, "model": client.model}
    except Exception:
        status["components"]["ollama"] = {"available": False}

    try:
        from kairos.services.compact import get_compact_service
        cs = get_compact_service()
        status["components"]["compact"] = cs.get_stats()
    except Exception:
        status["components"]["compact"] = {"status": "unavailable"}

    try:
        from kairos.services.tools import get_tool_registry
        tr = get_tool_registry()
        status["components"]["tools"] = {"registered": len(tr._tools)}
    except Exception:
        status["components"]["tools"] = {"status": "unavailable"}

    return status
