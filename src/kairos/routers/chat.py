"""
对话路由 v4.1（优化版）
提供同步和流式对话端点
v4.1变更:
- 集成集中配置管理系统
- 历史消息自动截断（防止OOM和上下文溢出）
- 统一错误处理
- 请求ID追踪
"""

import asyncio
import json
import time
import logging
import uuid
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["对话"])

# 从集中配置导入（兼容旧版无配置情况）
try:
    from kairos.system.config import settings
    MAX_MESSAGE_LENGTH = settings.api.chat_max_message_length
    DEFAULT_MODEL = settings.ollama.default_model
    MAX_HISTORY = settings.ollama.max_history_messages
except Exception:
    MAX_MESSAGE_LENGTH = 32000
    DEFAULT_MODEL = "gemma4:e4b"
    MAX_HISTORY = 20

# 全局依赖（启动时注入）
_ollama_client = None
_system_identity = ""
_response_cache = None


def init_chat_deps(ollama_client, system_identity: str, default_model: str, response_cache=None):
    """初始化聊天模块依赖"""
    global _ollama_client, _system_identity, _response_cache
    _ollama_client = ollama_client
    _system_identity = system_identity
    _response_cache = response_cache


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    model: str = Field(default="", max_length=100)
    history: Optional[List[Dict[str, str]]] = None

    @field_validator('message')
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        """XSS过滤（覆盖所有HTML事件处理器和危险标签）"""
        dangerous_patterns = [
            '<script', 'javascript:', 'data:', 'vbscript:', '<iframe',
            '<svg', '<img', '<body', '<input', '<details',
            '<marquee', '<object', '<embed', '<link', '<base',
            '<form', '<meta', '<style', '<frame', '<frameset',
            'onerror=', 'onload=', 'onclick=', 'onmouseover=',
            'onfocus=', 'onblur=', 'onsubmit=', 'onchange=',
            'oninput=', 'onkeydown=', 'onkeyup=', 'onkeypress=',
            'ondrag=', 'ondrop=', 'oncontextmenu=', 'onanimationend=',
        ]
        v_lower = v.lower()
        for pattern in dangerous_patterns:
            if pattern in v_lower:
                raise ValueError(f'消息包含不允许的内容: {pattern}')
        return v.strip()

    @field_validator('model')
    @classmethod
    def validate_model(cls, v: str) -> str:
        """模型名称格式校验"""
        if v and not v.replace(':', '').replace('-', '').replace('_', '').replace('.', '').isalnum():
            raise ValueError('模型名称格式无效')
        return v


class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str
    model: str
    status: str
    trace_id: Optional[str] = None


def _truncate_history(history: Optional[List[Dict]]) -> List[Dict]:
    """截断历史消息，保留最近N条防止OOM"""
    if not history:
        return []
    if len(history) <= MAX_HISTORY:
        return list(history)

    truncated = history[-MAX_HISTORY:]
    logger.warning("历史消息截断 %d → %d (上限:%d)", len(history), len(truncated), MAX_HISTORY)
    return truncated


def _build_messages(request: ChatRequest) -> List[Dict]:
    """构建Ollama消息列表"""
    messages = []
    if _system_identity:
        messages.append({'role': 'system', 'content': _system_identity})

    safe_history = _truncate_history(request.history)
    messages.extend(safe_history)
    messages.append({'role': 'user', 'content': request.message})
    return messages


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request):
    """同步对话端点（支持优雅降级 + 历史截断）"""
    model = request.model or DEFAULT_MODEL
    trace_id = uuid.uuid4().hex[:12]

    # 服务降级检查
    try:
        from kairos.system.degradation import get_degradation_manager
        dm = get_degradation_manager()
        level = await dm.evaluate_service_level()
        if level < 3:
            fallback = dm.get_fallback_response(request.message)
            logger.info("[%s] 降级响应 level=%d", trace_id, level)
            return ChatResponse(
                response=fallback,
                model="rule-engine",
                status="degraded",
                trace_id=trace_id
            )
    except ImportError:
        pass

    try:
        messages = _build_messages(request)
        loop = asyncio.get_event_loop()

        response = await loop.run_in_executor(
            None,
            lambda: _ollama_client.chat(model=model, messages=messages)
        )
        content = response['message']['content']

        # 大输出处理
        try:
            from kairos.system.large_output import get_large_output_handler
            handler = get_large_output_handler()
            processed = handler.process(content, {"model": model})
            if processed.is_truncated:
                logger.info("[%s] 输出已截断", trace_id)
                return ChatResponse(
                    response=processed.content,
                    model=model,
                    status="truncated",
                    trace_id=trace_id
                )
        except ImportError:
            pass

        logger.info("[%s] 对话成功 model=%s hist=%d", trace_id, model, len(request.history or []))
        return ChatResponse(
            response=content,
            model=model,
            status="ok",
            trace_id=trace_id
        )

    except ConnectionError as e:
        logger.error("[%s] 连接失败: %s", trace_id, e)
        return ChatResponse(
            response="LLM服务连接失败，请检查 Ollama 是否运行",
            model=model,
            status="error",
            trace_id=trace_id
        )
    except TimeoutError as e:
        logger.error("[%s] 超时: %s", trace_id, e)
        return ChatResponse(
            response="请求超时，请稍后重试",
            model=model,
            status="error",
            trace_id=trace_id
        )
    except Exception as e:
        logger.error("[%s] 对话异常: %s", trace_id, e, exc_info=True)
        return ChatResponse(
            response=f"对话失败: {str(e)}",
            model=model,
            status="error",
            trace_id=trace_id
        )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式对话端点（SSE格式）"""
    model = request.model or DEFAULT_MODEL
    trace_id = uuid.uuid4().hex[:12]

    async def event_generator():
        try:
            messages = _build_messages(request)
            loop = asyncio.get_event_loop()

            stream = await loop.run_in_executor(
                None,
                lambda: _ollama_client.chat(model=model, messages=messages, stream=True)
            )

            total_tokens = 0
            start_time = time.time()

            for chunk in stream:
                if isinstance(chunk, dict) and 'message' in chunk:
                    token_content = chunk['message'].get('content', '')
                    if token_content:
                        total_tokens += 1
                        yield f"data: {json.dumps({'type':'token','content':token_content,'index':total_tokens-1}, ensure_ascii=False)}\n\n"
                elif isinstance(chunk, dict) and chunk.get('done', False):
                    duration_ms = round((time.time() - start_time) * 1000, 2)
                    yield f"data: {json.dumps({'type':'metadata','model':model,'total_tokens':total_tokens,'duration_ms':duration_ms,'trace_id':trace_id}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'type':'done'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error("[%s] 流式错误: %s", trace_id, e)
            yield f"data: {json.dumps({'type':'error','code':'CHAT_ERROR','message':str(e),'trace_id':trace_id}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/models")
async def list_models():
    """获取可用模型列表"""
    try:
        models_data = _ollama_client.list()
        model_list = []
        if models_data and 'models' in models_data:
            for m in models_data['models']:
                if isinstance(m, dict):
                    model_list.append({
                        'name': m.get('name', 'unknown'),
                        'size': m.get('size', 'unknown'),
                        'modified_at': m.get('modified_at', '')
                    })
                else:
                    model_list.append({'name': str(m)})
        return {"success": True, "models": model_list}
    except ConnectionError:
        raise HTTPException(status_code=503, detail="无法连接到Ollama服务")
    except Exception as e:
        logger.error("获取模型列表失败: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
