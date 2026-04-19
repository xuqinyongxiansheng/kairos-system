#!/usr/bin/env python3
"""
语音识别与视觉VoLo技能路由器
提供统一的 API 接口
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/skills", tags=["skills-stv"])


class STTRequest(BaseModel):
    audio_path: str = Field(..., description="音频文件路径")
    engine: Optional[str] = Field(None, description="引擎: vosk, faster_whisper, local_llm")
    language: Optional[str] = Field(None, description="语言代码: zh, en, ja 等")
    task: Optional[str] = Field("default", description="任务类型: default, realtime, transcription")


class STTStreamRequest(BaseModel):
    engine: Optional[str] = Field("vosk", description="流式识别引擎")
    sample_rate: Optional[int] = Field(16000, description="采样率")


class ImageClassifyRequest(BaseModel):
    image_path: str = Field(..., description="图片文件路径")
    top_k: Optional[int] = Field(5, description="返回Top-K结果")
    engine: Optional[str] = Field("auto", description="引擎: auto, volo, ollama")


class ImageDescribeRequest(BaseModel):
    image_path: str = Field(..., description="图片文件路径")
    prompt: Optional[str] = Field(None, description="描述提示词")


class ImageAnalyzeRequest(BaseModel):
    image_path: str = Field(..., description="图片文件路径")
    top_k: Optional[int] = Field(5, description="分类Top-K")


@router.post("/stt/recognize")
async def speech_recognize(request: STTRequest):
    """语音识别：将音频转换为文字"""
    from ..agent_enhance.integrations.speech_recognition import get_speech_recognition_adapter

    adapter = get_speech_recognition_adapter()
    result = await adapter.recognize(
        audio_path=request.audio_path,
        engine=request.engine,
        language=request.language,
        task=request.task
    )

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "识别失败"))

    return result


@router.post("/stt/upload")
async def speech_recognize_upload(
    file: UploadFile = File(...),
    engine: Optional[str] = Form(None),
    language: Optional[str] = Form(None)
):
    """语音识别：上传音频文件"""
    import os
    import tempfile

    suffix = os.path.splitext(file.filename or ".wav")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        from ..agent_enhance.integrations.speech_recognition import get_speech_recognition_adapter

        adapter = get_speech_recognition_adapter()
        result = await adapter.recognize(
            audio_path=tmp_path,
            engine=engine,
            language=language
        )
        return result
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@router.get("/stt/engines")
async def stt_engine_status():
    """语音识别引擎状态"""
    from ..agent_enhance.integrations.speech_recognition import get_speech_recognition_adapter

    adapter = get_speech_recognition_adapter()
    return {
        "engines": adapter.get_engine_status(),
        "skills": adapter.list_skills()
    }


@router.post("/vision/classify")
async def vision_classify(request: ImageClassifyRequest):
    """图像分类：使用 VoLo 模型分类"""
    from ..agent_enhance.integrations.vision_volo import get_vision_volo_adapter

    adapter = get_vision_volo_adapter()
    result = await adapter.classify(request.image_path, request.top_k, request.engine)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "分类失败"))

    return result


@router.post("/vision/describe")
async def vision_describe(request: ImageDescribeRequest):
    """图像描述：使用 Ollama 描述图片"""
    from ..agent_enhance.integrations.vision_volo import get_vision_volo_adapter

    adapter = get_vision_volo_adapter()
    result = await adapter.describe(request.image_path, request.prompt)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "描述失败"))

    return result


@router.post("/vision/analyze")
async def vision_analyze(request: ImageAnalyzeRequest):
    """视觉分析：综合分类+描述"""
    from ..agent_enhance.integrations.vision_volo import get_vision_volo_adapter

    adapter = get_vision_volo_adapter()
    result = await adapter.analyze(request.image_path, request.top_k)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "分析失败"))

    return result


@router.post("/vision/upload")
async def vision_upload_classify(
    file: UploadFile = File(...),
    top_k: Optional[int] = Form(5),
    engine: Optional[str] = Form("auto")
):
    """图像分类：上传图片文件"""
    import os
    import tempfile

    suffix = os.path.splitext(file.filename or ".jpg")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        from ..agent_enhance.integrations.vision_volo import get_vision_volo_adapter

        adapter = get_vision_volo_adapter()
        result = await adapter.classify(tmp_path, top_k, engine)
        return result
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@router.get("/vision/engines")
async def vision_engine_status():
    """视觉引擎状态"""
    from ..agent_enhance.integrations.vision_volo import get_vision_volo_adapter

    adapter = get_vision_volo_adapter()
    return {
        "engines": adapter.get_engine_status(),
        "skills": adapter.list_skills(),
        "model_info": adapter.get_model_info()
    }


@router.get("/stv/status")
async def stv_combined_status():
    """语音+视觉联合状态"""
    from ..agent_enhance.integrations.speech_recognition import get_speech_recognition_adapter
    from ..agent_enhance.integrations.vision_volo import get_vision_volo_adapter

    stt = get_speech_recognition_adapter()
    vis = get_vision_volo_adapter()

    return {
        "speech_recognition": {
            "engines": stt.get_engine_status(),
            "skills": stt.list_skills()
        },
        "vision_volo": {
            "engines": vis.get_engine_status(),
            "skills": vis.list_skills(),
            "model_info": vis.get_model_info()
        },
        "collaboration": {
            "audio_visual_analysis": True,
            "description": "支持语音+视觉联合分析：语音识别结果可作为视觉分析输入"
        }
    }
