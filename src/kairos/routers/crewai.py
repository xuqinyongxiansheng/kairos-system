#!/usr/bin/env python3
"""
CrewAI 路由
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import asyncio

from kairos.services.crewai_service import get_crewai_service
from kairos.system.security import get_security_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agent/crewai", tags=["CrewAI"])


class CrewAIRequest(BaseModel):
    """CrewAI 请求"""
    task: str = Field(..., min_length=1, max_length=10000)
    agents: Optional[List[Dict[str, str]]] = None


class ModelExpertRequest(BaseModel):
    """模型专家请求"""
    task_type: str = Field(..., min_length=1, max_length=100)
    requirements: Optional[Dict[str, float]] = None


class ModelEvaluateRequest(BaseModel):
    """模型评估请求"""
    model_name: str = Field(..., min_length=1, max_length=100)
    task_type: str = Field(..., min_length=1, max_length=100)
    test_data: str = Field(..., min_length=1, max_length=10000)


@router.post("/create")
async def create_crew(request: CrewAIRequest):
    """创建代理团队"""
    try:
        security = get_security_manager()
        if not security.validate_input(request.task):
            raise HTTPException(status_code=400, detail="Invalid task content")
        
        service = get_crewai_service()
        coordinator = service.create_crew(request.task, request.agents)
        
        return {
            "success": True,
            "agents": coordinator.get_agent_info()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run")
async def run_task(request: CrewAIRequest):
    """运行任务"""
    try:
        security = get_security_manager()
        if not security.validate_input(request.task):
            raise HTTPException(status_code=400, detail="Invalid task content")
        
        service = get_crewai_service()
        result = await service.run_task(request.task, request.agents)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    service = get_crewai_service()
    status = service.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return status


@router.post("/cancel/{task_id}")
async def cancel_task(task_id: str):
    """取消任务"""
    service = get_crewai_service()
    success = service.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True}


@router.get("/tasks")
async def list_tasks():
    """列出任务"""
    service = get_crewai_service()
    tasks = service.list_tasks()
    return {"tasks": tasks}


@router.post("/model/recommend")
async def get_model_recommendation(request: ModelExpertRequest):
    """获取模型推荐"""
    try:
        service = get_crewai_service()
        recommendation = service.get_model_recommendation(request.task_type)
        return {
            "success": True,
            "recommendation": recommendation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/model/evaluate")
async def evaluate_model(request: ModelEvaluateRequest):
    """评估模型"""
    try:
        security = get_security_manager()
        if not security.validate_input(request.test_data):
            raise HTTPException(status_code=400, detail="Invalid test data")
        
        service = get_crewai_service()
        result = await service.expert_system.evaluate_model(
            request.model_name,
            request.task_type,
            request.test_data
        )
        return {
            "success": True,
            "result": result.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model/info/{model_name}")
async def get_model_info(model_name: str):
    """获取模型信息"""
    service = get_crewai_service()
    model_info = service.expert_system.get_model_info(model_name)
    if not model_info:
        raise HTTPException(status_code=404, detail="Model not found")
    return {
        "success": True,
        "model": model_info.model_dump()
    }


@router.get("/model/list")
async def list_models(capability: Optional[str] = None):
    """列出模型"""
    service = get_crewai_service()
    models = service.expert_system.list_models(capability)
    return {
        "success": True,
        "models": [model.model_dump() for model in models]
    }