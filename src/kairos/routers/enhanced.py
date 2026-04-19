"""
增强功能路由 v1.0
提供类人思考、事实核查、任务规划、自进化的API端点
"""

import logging
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/enhanced", tags=["增强功能"])


# ===== 请求/响应模型 =====

class ThinkRequest(BaseModel):
    """思考请求"""
    query: str = Field(..., min_length=1, max_length=10000)
    context: Optional[Dict[str, Any]] = None
    depth: str = Field(default="standard", description="思考深度: quick/standard/deep")


class VerifyRequest(BaseModel):
    """核查请求"""
    claim: str = Field(..., min_length=1, max_length=5000)
    context: Optional[Dict[str, Any]] = None


class VerifyBatchRequest(BaseModel):
    """批量核查请求"""
    claims: List[str] = Field(..., min_length=1, max_length=20)


class PlanRequest(BaseModel):
    """规划请求"""
    goal: str = Field(..., min_length=1, max_length=5000)
    context: Optional[Dict[str, Any]] = None
    max_revisions: int = Field(default=2, ge=0, le=5)


class LearnRequest(BaseModel):
    """学习请求"""
    task: str = Field(..., min_length=1, max_length=5000)
    result: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None


class MemoryStoreRequest(BaseModel):
    """记忆存储请求"""
    content: str = Field(..., min_length=1, max_length=50000)
    layer: str = Field(default="auto", description="目标层: instant/working/long_term/permanent/auto")
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class MemorySearchRequest(BaseModel):
    """记忆检索请求"""
    query: str = Field(..., min_length=1, max_length=5000)
    layers: Optional[List[str]] = None
    limit: int = Field(default=10, ge=1, le=50)


# ===== 思考引擎端点 =====

@router.post("/think")
async def think(request: ThinkRequest):
    """类人深度思考：四段式思考链路（假设→验证→修正→结论）"""
    try:
        from kairos.system.thinking_engine import get_thinking_engine
        engine = get_thinking_engine()
        result = await engine.think(request.query, request.context)
        return {"success": True, "data": result.to_dict()}
    except Exception as e:
        logger.error("思考引擎错误: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/think/history")
async def think_history(limit: int = 20):
    """获取思考历史"""
    try:
        from kairos.system.thinking_engine import get_thinking_engine
        engine = get_thinking_engine()
        return {"success": True, "data": engine.get_history(limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/think/statistics")
async def think_statistics():
    """获取思考统计"""
    try:
        from kairos.system.thinking_engine import get_thinking_engine
        engine = get_thinking_engine()
        return {"success": True, "data": engine.get_statistics()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== 事实核查端点 =====

@router.post("/verify")
async def verify(request: VerifyRequest):
    """实时事实核查：可信度评估+风险标注"""
    try:
        from kairos.system.fact_checker import get_fact_checker
        checker = get_fact_checker()
        result = await checker.verify(request.claim, request.context)
        return {"success": True, "data": result.to_dict()}
    except Exception as e:
        logger.error("事实核查错误: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify/batch")
async def verify_batch(request: VerifyBatchRequest):
    """批量事实核查"""
    try:
        from kairos.system.fact_checker import get_fact_checker
        checker = get_fact_checker()
        results = await checker.verify_batch(request.claims)
        return {"success": True, "data": [r.to_dict() for r in results]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify/statistics")
async def verify_statistics():
    """获取核查统计"""
    try:
        from kairos.system.fact_checker import get_fact_checker
        checker = get_fact_checker()
        return {"success": True, "data": checker.get_statistics()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== 任务规划端点 =====

@router.post("/plan")
async def plan_and_execute(request: PlanRequest):
    """任务规划闭环：Plan→Do→Check→Act"""
    try:
        from kairos.system.task_planner import get_task_planner
        planner = get_task_planner()
        result = await planner.plan_and_execute(
            goal=request.goal,
            context=request.context,
            max_revisions=request.max_revisions
        )
        return {"success": True, "data": result.to_dict()}
    except Exception as e:
        logger.error("任务规划错误: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plan/history")
async def plan_history(limit: int = 20):
    """获取规划历史"""
    try:
        from kairos.system.task_planner import get_task_planner
        planner = get_task_planner()
        return {"success": True, "data": planner.get_history(limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plan/lessons")
async def plan_lessons(limit: int = 20):
    """获取经验教训"""
    try:
        from kairos.system.task_planner import get_task_planner
        planner = get_task_planner()
        return {"success": True, "data": planner.get_lessons(limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== 自进化端点 =====

@router.post("/evolution/learn")
async def evolution_learn(request: LearnRequest):
    """从经验中学习"""
    try:
        from kairos.system.evolution import get_evolution_engine
        engine = get_evolution_engine()
        result = await engine.learn_from_experience(
            task=request.task,
            result=request.result,
            context=request.context
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.error("自进化学习错误: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evolution/optimize")
async def evolution_optimize():
    """策略优化"""
    try:
        from kairos.system.evolution import get_evolution_engine
        engine = get_evolution_engine()
        result = await engine.optimize_strategy()
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evolution/capability")
async def evolution_capability():
    """获取能力评估报告"""
    try:
        from kairos.system.evolution import get_evolution_engine
        engine = get_evolution_engine()
        return {"success": True, "data": engine.get_capability_report()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evolution/summary")
async def evolution_summary():
    """获取自进化摘要"""
    try:
        from kairos.system.evolution import get_evolution_engine
        engine = get_evolution_engine()
        return {"success": True, "data": engine.get_evolution_summary()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evolution/rules")
async def evolution_rules(domain: str = None, limit: int = 20):
    """获取蒸馏规则"""
    try:
        from kairos.system.evolution import get_evolution_engine
        engine = get_evolution_engine()
        return {"success": True, "data": engine.get_distilled_rules(domain, limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== 四层记忆端点 =====

@router.post("/memory/store")
async def memory_store(request: MemoryStoreRequest):
    """存储记忆到指定层"""
    try:
        from kairos.system.memory_system import create_four_layer_memory_system
        mem = create_four_layer_memory_system()
        item_id = mem.store(
            content=request.content,
            layer=request.layer,
            tags=request.tags,
            metadata=request.metadata
        )
        return {"success": True, "data": {"item_id": item_id, "layer": request.layer}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/search")
async def memory_search(request: MemorySearchRequest):
    """跨层检索记忆"""
    try:
        from kairos.system.memory_system import create_four_layer_memory_system
        mem = create_four_layer_memory_system()
        results = mem.retrieve(
            query=request.query,
            layers=request.layers,
            limit=request.limit
        )
        return {"success": True, "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/statistics")
async def memory_statistics():
    """获取四层记忆统计"""
    try:
        from kairos.system.memory_system import create_four_layer_memory_system
        mem = create_four_layer_memory_system()
        return {"success": True, "data": mem.get_system_statistics()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== 系统总览端点 =====

@router.get("/overview")
async def enhanced_overview():
    """增强功能总览"""
    return {
        "success": True,
        "data": {
            "modules": {
                "thinking_engine": {
                    "name": "类人深度思考引擎",
                    "description": "四段式思考链路：假设→验证→修正→结论",
                    "endpoints": ["/api/enhanced/think", "/api/enhanced/think/history", "/api/enhanced/think/statistics"]
                },
                "fact_checker": {
                    "name": "实时事实核查",
                    "description": "可信度评估+风险标注+冲突检测",
                    "endpoints": ["/api/enhanced/verify", "/api/enhanced/verify/batch", "/api/enhanced/verify/statistics"]
                },
                "task_planner": {
                    "name": "任务规划闭环",
                    "description": "Plan→Do→Check→Act 反思迭代",
                    "endpoints": ["/api/enhanced/plan", "/api/enhanced/plan/history", "/api/enhanced/plan/lessons"]
                },
                "evolution": {
                    "name": "自进化系统",
                    "description": "经验提取+知识蒸馏+策略优化",
                    "endpoints": ["/api/enhanced/evolution/learn", "/api/enhanced/evolution/optimize",
                                  "/api/enhanced/evolution/capability", "/api/enhanced/evolution/summary"]
                },
                "four_layer_memory": {
                    "name": "四层分层记忆",
                    "description": "瞬时/工作/长期/永久记忆",
                    "endpoints": ["/api/enhanced/memory/store", "/api/enhanced/memory/search",
                                  "/api/enhanced/memory/statistics"]
                }
            },
            "total_endpoints": 18
        }
    }
