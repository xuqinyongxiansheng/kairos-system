#!/usr/bin/env python3
"""
ClawBot 微信通道 API 路由
提供微信消息通道的HTTP管理接口
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("clawbot_router")

router = APIRouter(prefix="/api/skills/clawbot", tags=["clawbot"])


class ConnectRequest(BaseModel):
    mode: str = Field(default="channel", description="连接模式: channel/gateway")
    base_url: Optional[str] = Field(default="https://ilinkai.weixin.qq.com", description="iLink API地址")
    token: Optional[str] = Field(default=None, description="Bot Token")
    gateway_url: Optional[str] = Field(default="http://localhost:8765", description="网关地址")
    endpoint_id: Optional[str] = Field(default="hmyx", description="网关端点ID")


class ReplyRequest(BaseModel):
    sender_id: str = Field(description="接收者ID")
    text: str = Field(description="回复内容")
    context_token: Optional[str] = Field(default=None, description="上下文Token")


class SendMessageRequest(BaseModel):
    sender_id: str = Field(description="接收者ID")
    text: str = Field(description="消息内容")


@router.get("/status")
async def get_clawbot_status():
    """获取ClawBot通道状态"""
    try:
        from kairos.skills.agent_enhance.integrations.clawbot_adapter import get_clawbot_adapter
        adapter = get_clawbot_adapter()
        return {"status": "success", "data": adapter.get_status()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/connect")
async def connect_clawbot(req: ConnectRequest):
    """连接ClawBot通道"""
    try:
        from kairos.skills.agent_enhance.integrations.clawbot_adapter import get_clawbot_adapter
        adapter = get_clawbot_adapter(mode=req.mode,
                                       base_url=req.base_url,
                                       token=req.token,
                                       gateway_url=req.gateway_url,
                                       endpoint_id=req.endpoint_id)
        success = await adapter.connect()
        if success:
            return {"status": "success", "message": f"ClawBot {req.mode}模式连接成功"}
        raise HTTPException(status_code=500, detail="连接失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_listening():
    """开始监听微信消息"""
    try:
        from kairos.skills.agent_enhance.integrations.clawbot_adapter import (
            get_clawbot_adapter, get_clawbot_bridge
        )
        adapter = get_clawbot_adapter()
        bridge = get_clawbot_bridge(adapter=adapter)
        await adapter.start_listening(message_handler=bridge.handle_message)
        return {"status": "success", "message": "消息监听已启动"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_listening():
    """停止监听微信消息"""
    try:
        from kairos.skills.agent_enhance.integrations.clawbot_adapter import get_clawbot_adapter
        adapter = get_clawbot_adapter()
        await adapter.stop_listening()
        return {"status": "success", "message": "消息监听已停止"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reply")
async def reply_message(req: ReplyRequest):
    """回复微信消息"""
    try:
        from kairos.skills.agent_enhance.integrations.clawbot_adapter import get_clawbot_adapter
        adapter = get_clawbot_adapter()
        success = await adapter.reply(req.sender_id, req.text, req.context_token)
        if success:
            return {"status": "success", "message": "回复已发送"}
        raise HTTPException(status_code=500, detail="回复失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send")
async def send_message(req: SendMessageRequest):
    """主动发送微信消息"""
    try:
        from kairos.skills.agent_enhance.integrations.clawbot_adapter import get_clawbot_adapter
        adapter = get_clawbot_adapter()
        success = await adapter.reply(req.sender_id, req.text)
        if success:
            return {"status": "success", "message": "消息已发送"}
        raise HTTPException(status_code=500, detail="发送失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/skills")
async def list_clawbot_skills():
    """列出ClawBot技能"""
    try:
        from kairos.skills.agent_enhance.integrations.clawbot_adapter import get_clawbot_adapter
        adapter = get_clawbot_adapter()
        return {"status": "success", "skills": adapter.list_skills()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/info")
async def get_clawbot_info():
    """获取ClawBot集成信息"""
    return {
        "status": "success",
        "data": {
            "name": "wechat-clawbot",
            "version": "0.4.0",
            "description": "微信 iLink Bot SDK，支持 Claude Code / Codex / 自定义机器人",
            "modes": ["channel", "gateway"],
            "features": [
                "iLink API 长轮询",
                "二维码扫码登录",
                "AES-128-ECB 加密 CDN",
                "Context Token 持久化",
                "SILK 语音转码",
                "Claude Code MCP 桥接",
                "多用户多端点网关",
                "SDK WebSocket 客户端",
            ],
            "integration_points": {
                "text": "文本消息 → LLM推理 → 微信回复",
                "voice": "语音消息 → Vosk/FasterWhisper → LLM → 微信回复",
                "image": "图片消息 → VoLo分类/Ollama描述 → LLM → 微信回复",
                "file": "文件消息 → 文件处理 → LLM → 微信回复",
            },
            "vendor_path": "project/vendor/wechat-clawbot/",
        }
    }
