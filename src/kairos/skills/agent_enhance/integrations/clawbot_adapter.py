#!/usr/bin/env python3
"""
ClawBot 微信通道适配器

将 wechat-clawbot (微信 iLink Bot SDK) 集成到鸿蒙小雨项目
支持两种模式：
1. Channel Mode - 单用户单端点，直接连接微信 iLink API
2. Gateway Mode - 多用户多端点，通过网关路由

集成点：
- 微信消息 → 认知闭环感知层 → LLM推理 → 微信回复
- 微信语音 → 语音识别适配器 → 文本 → LLM
- 微信图片 → 视觉VoLo适配器 → 分类/描述 → LLM
- 微信文件 → 文件处理 → LLM
"""

import os
import sys
import json
import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("ClawBotAdapter")

VENDOR_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "vendor", "wechat-clawbot", "src")
VENDOR_PATH = os.path.normpath(VENDOR_PATH)
if VENDOR_PATH not in sys.path:
    sys.path.insert(0, VENDOR_PATH)


class ClawBotMode(Enum):
    CHANNEL = "channel"
    GATEWAY = "gateway"


class ClawBotStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    LISTENING = "listening"
    ERROR = "error"


@dataclass
class WeChatMessage:
    sender_id: str
    text: str
    message_type: str
    context_token: Optional[str] = None
    session_id: Optional[str] = None
    raw_message: Optional[Any] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None


@dataclass
class WeChatReply:
    sender_id: str
    text: str
    context_token: Optional[str] = None


class ClawBotChannelAdapter:
    """
    ClawBot单通道适配器

    直接连接微信 iLink API，将微信消息桥接到鸿蒙小雨认知闭环
    """

    def __init__(self, base_url: str = "https://ilinkai.weixin.qq.com",
                 token: str = None, config_path: str = None):
        self.base_url = base_url
        self.token = token
        self.config_path = config_path
        self.status = ClawBotStatus.DISCONNECTED
        self._api_opts = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        self._message_handlers: List[callable] = []
        self._stats = {
            "messages_received": 0,
            "messages_sent": 0,
            "errors": 0,
            "start_time": None,
        }

        self._skills = []
        self._agents = []
        self._init_skills()
        self._init_agents()

    def _init_skills(self):
        self._skills = [
            {"name": "wechat_listen", "description": "监听微信消息", "category": "communication"},
            {"name": "wechat_reply", "description": "回复微信消息", "category": "communication"},
            {"name": "wechat_send", "description": "主动发送微信消息", "category": "communication"},
            {"name": "wechat_typing", "description": "发送微信输入状态", "category": "communication"},
        ]

    def _init_agents(self):
        self._agents = [
            {"name": "wechat_agent", "skills": 4, "capabilities": 4,
             "description": "微信通道代理，处理消息收发和媒体处理"},
            {"name": "wechat_media_agent", "skills": 2, "capabilities": 3,
             "description": "微信媒体代理，处理图片/语音/文件"},
        ]

    async def _get_api(self):
        if self._api_opts is None:
            try:
                from wechat_clawbot.api.client import WeixinApiOptions
                self._api_opts = WeixinApiOptions(base_url=self.base_url, token=self.token)
            except ImportError:
                logger.error("wechat-clawbot 未安装，请将vendor路径加入sys.path")
                raise
        return self._api_opts

    async def connect(self) -> bool:
        self.status = ClawBotStatus.CONNECTING
        try:
            api_opts = await self._get_api()
            from wechat_clawbot.api.client import get_config
            config = await get_config(api_opts, ilink_user_id="system")
            self.status = ClawBotStatus.CONNECTED
            self._stats["start_time"] = time.time()
            logger.info("ClawBot通道连接成功")
            return True
        except Exception as e:
            self.status = ClawBotStatus.ERROR
            logger.error("ClawBot通道连接失败: %s", e)
            return False

    async def start_listening(self, message_handler: callable = None):
        if message_handler:
            self._message_handlers.append(message_handler)

        self._running = True
        self.status = ClawBotStatus.LISTENING

        self._monitor_task = asyncio.create_task(self._poll_loop())
        logger.info("ClawBot消息监听已启动")

    async def _poll_loop(self):
        from wechat_clawbot.api.client import get_updates
        from wechat_clawbot.api.types import MessageType

        api_opts = await self._get_api()
        get_updates_buf = ""

        while self._running:
            try:
                resp = await get_updates(
                    base_url=api_opts.base_url,
                    token=api_opts.token,
                    get_updates_buf=get_updates_buf,
                )

                if resp.msgs:
                    for msg in resp.msgs:
                        if msg.message_type == MessageType.USER:
                            wechat_msg = self._convert_message(msg)
                            self._stats["messages_received"] += 1
                            await self._dispatch_message(wechat_msg)

                get_updates_buf = resp.get_updates_buf or get_updates_buf

            except Exception as e:
                self._stats["errors"] += 1
                logger.error("消息轮询异常: %s", e)
                await asyncio.sleep(5)

    def _convert_message(self, raw_msg) -> WeChatMessage:
        text = ""
        media_url = None
        media_type = None

        if raw_msg.item_list:
            for item in raw_msg.item_list:
                if item.text_item and item.text_item.text:
                    text += item.text_item.text
                if item.image_item:
                    media_type = "image"
                    if item.image_item.media:
                        media_url = item.image_item.media.full_url or item.image_item.url
                if item.voice_item:
                    media_type = "voice"
                    if item.voice_item.media:
                        media_url = item.voice_item.media.full_url
                if item.file_item:
                    media_type = "file"
                    if item.file_item.media:
                        media_url = item.file_item.media.full_url

        return WeChatMessage(
            sender_id=raw_msg.from_user_id or "",
            text=text,
            message_type=media_type or "text",
            context_token=raw_msg.context_token,
            session_id=raw_msg.session_id,
            raw_message=raw_msg,
            media_url=media_url,
            media_type=media_type,
        )

    async def _dispatch_message(self, msg: WeChatMessage):
        for handler in self._message_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(msg)
                else:
                    handler(msg)
            except Exception as e:
                logger.error("消息处理器异常: %s", e)

    async def reply(self, sender_id: str, text: str, context_token: str = None) -> bool:
        try:
            from wechat_clawbot.api.client import send_message
            from wechat_clawbot.api.types import (
                SendMessageReq, WeixinMessage, MessageItem,
                MessageItemType, MessageType, MessageState, TextItem,
            )

            api_opts = await self._get_api()
            await send_message(api_opts, SendMessageReq(msg=WeixinMessage(
                to_user_id=sender_id,
                client_id="hmyx-clawbot",
                message_type=MessageType.BOT,
                message_state=MessageState.FINISH,
                item_list=[MessageItem(type=MessageItemType.TEXT, text_item=TextItem(text=text))],
                context_token=context_token,
            )))

            self._stats["messages_sent"] += 1
            logger.info("微信回复已发送: %s -> %s", sender_id[:10], text[:30])
            return True
        except Exception as e:
            self._stats["errors"] += 1
            logger.error("微信回复失败: %s", e)
            return False

    async def send_typing(self, sender_id: str, context_token: str = None) -> bool:
        try:
            from wechat_clawbot.api.client import send_typing, get_config
            from wechat_clawbot.api.types import SendTypingReq, TypingStatus

            api_opts = await self._get_api()
            config = await get_config(api_opts, ilink_user_id=sender_id, context_token=context_token)
            await send_typing(api_opts, SendTypingReq(
                ilink_user_id=sender_id,
                typing_ticket=config.typing_ticket,
                status=TypingStatus.TYPING,
            ))
            return True
        except Exception as e:
            logger.debug("发送输入状态失败: %s", e)
            return False

    async def stop_listening(self):
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        self.status = ClawBotStatus.DISCONNECTED
        logger.info("ClawBot消息监听已停止")

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "mode": ClawBotMode.CHANNEL.value,
            "base_url": self.base_url,
            "stats": dict(self._stats),
            "uptime_seconds": time.time() - self._stats["start_time"] if self._stats["start_time"] else 0,
        }

    def list_skills(self) -> List[str]:
        return [s["name"] for s in self._skills]

    def convert_to_professional_agent(self, agent_name: str):
        try:
            from kairos.skills.agent_enhance.professional_agents.base_agent import ProfessionalAgent, AgentCapability
            agent_map = {
                "wechat_agent": ProfessionalAgent(
                    name="wechat_agent", description="微信通道代理",
                    capabilities=[AgentCapability.CONVERSATION, AgentCapability.ANALYSIS,
                                  AgentCapability.CODE_GENERATION, AgentCapability.KNOWLEDGE_QUERY],
                ),
                "wechat_media_agent": ProfessionalAgent(
                    name="wechat_media_agent", description="微信媒体代理",
                    capabilities=[AgentCapability.ANALYSIS, AgentCapability.KNOWLEDGE_QUERY,
                                  AgentCapability.CONVERSATION],
                ),
            }
            return agent_map.get(agent_name)
        except ImportError:
            logger.warning("ProfessionalAgent基类不可用")
            return None

    def register_all_agents(self):
        for agent_def in self._agents:
            agent = self.convert_to_professional_agent(agent_def["name"])
            if agent:
                try:
                    from kairos.skills.agent_enhance.professional_agents.base_agent import AgentRegistry
                    AgentRegistry.register(agent)
                except Exception:
                    pass


class ClawBotGatewayAdapter:
    """
    ClawBot网关适配器

    通过WebSocket连接到ClawBot网关，支持多用户多端点路由
    """

    def __init__(self, gateway_url: str = "http://localhost:8765",
                 endpoint_id: str = "hmyx", token: str = "",
                 reconnect: bool = True):
        self.gateway_url = gateway_url
        self.endpoint_id = endpoint_id
        self.token = token
        self.reconnect = reconnect
        self.status = ClawBotStatus.DISCONNECTED
        self._client = None
        self._running = False
        self._message_handlers: List[callable] = []
        self._stats = {
            "messages_received": 0,
            "messages_sent": 0,
            "errors": 0,
            "start_time": None,
        }

        self._skills = [
            {"name": "wechat_gateway_listen", "description": "通过网关监听微信消息", "category": "communication"},
            {"name": "wechat_gateway_reply", "description": "通过网关回复微信消息", "category": "communication"},
        ]
        self._agents = [
            {"name": "wechat_gateway_agent", "skills": 2, "capabilities": 3,
             "description": "微信网关代理，通过网关路由处理消息"},
        ]

    async def connect(self) -> bool:
        self.status = ClawBotStatus.CONNECTING
        try:
            from wechat_clawbot.sdk import ClawBotClient
            self._client = ClawBotClient(
                gateway_url=self.gateway_url,
                endpoint_id=self.endpoint_id,
                token=self.token,
                reconnect=self.reconnect,
            )
            await self._client.connect()
            self.status = ClawBotStatus.CONNECTED
            self._stats["start_time"] = time.time()
            logger.info("ClawBot网关连接成功: %s", self.gateway_url)
            return True
        except ImportError:
            logger.error("wechat-clawbot[sdk] 未安装，请执行: pip install wechat-clawbot[sdk]")
            self.status = ClawBotStatus.ERROR
            return False
        except Exception as e:
            self.status = ClawBotStatus.ERROR
            logger.error("ClawBot网关连接失败: %s", e)
            return False

    async def start_listening(self, message_handler: callable = None):
        if message_handler:
            self._message_handlers.append(message_handler)

        self._running = True
        self.status = ClawBotStatus.LISTENING

        asyncio.create_task(self._gateway_listen_loop())
        logger.info("ClawBot网关监听已启动")

    async def _gateway_listen_loop(self):
        if not self._client:
            return

        try:
            async for sdk_msg in self._client.messages():
                if not self._running:
                    break

                wechat_msg = WeChatMessage(
                    sender_id=sdk_msg.sender_id,
                    text=sdk_msg.text,
                    message_type="text",
                    context_token=sdk_msg.context_token,
                )
                self._stats["messages_received"] += 1

                for handler in self._message_handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(wechat_msg)
                        else:
                            handler(wechat_msg)
                    except Exception as e:
                        logger.error("网关消息处理器异常: %s", e)
        except Exception as e:
            self._stats["errors"] += 1
            logger.error("网关监听异常: %s", e)

    async def reply(self, sender_id: str, text: str, context_token: str = None) -> bool:
        if not self._client:
            return False
        try:
            await self._client.reply(sender_id, text)
            self._stats["messages_sent"] += 1
            return True
        except Exception as e:
            self._stats["errors"] += 1
            logger.error("网关回复失败: %s", e)
            return False

    async def stop_listening(self):
        self._running = False
        if self._client:
            await self._client.close()
        self.status = ClawBotStatus.DISCONNECTED
        logger.info("ClawBot网关监听已停止")

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "mode": ClawBotMode.GATEWAY.value,
            "gateway_url": self.gateway_url,
            "endpoint_id": self.endpoint_id,
            "stats": dict(self._stats),
        }

    def list_skills(self) -> List[str]:
        return [s["name"] for s in self._skills]

    def convert_to_professional_agent(self, agent_name: str):
        try:
            from kairos.skills.agent_enhance.professional_agents.base_agent import ProfessionalAgent, AgentCapability
            return ProfessionalAgent(
                name="wechat_gateway_agent", description="微信网关代理",
                capabilities=[AgentCapability.CONVERSATION, AgentCapability.ANALYSIS,
                              AgentCapability.KNOWLEDGE_QUERY],
            )
        except ImportError:
            return None

    def register_all_agents(self):
        for agent_def in self._agents:
            agent = self.convert_to_professional_agent(agent_def["name"])
            if agent:
                try:
                    from kairos.skills.agent_enhance.professional_agents.base_agent import AgentRegistry
                    AgentRegistry.register(agent)
                except Exception:
                    pass


class ClawBotBridge:
    """
    ClawBot桥接器

    将微信消息桥接到鸿蒙小雨认知闭环：
    微信消息 → 感知层(知微) → LLM推理 → 微信回复

    支持：
    - 文本消息 → 直接LLM推理
    - 语音消息 → 语音识别 → LLM推理
    - 图片消息 → VoLo分类/描述 → LLM推理
    """

    def __init__(self, adapter=None):
        self._adapter = adapter
        self._llm_client = None
        self._stt_adapter = None
        self._vision_adapter = None
        self._memory = None

    async def _get_llm(self):
        if self._llm_client is None:
            from kairos.system.unified_llm_client import get_unified_client
            self._llm_client = get_unified_client()
        return self._llm_client

    async def _get_stt(self):
        if self._stt_adapter is None:
            try:
                from kairos.skills.agent_enhance.integrations.speech_recognition import get_speech_recognition_adapter
                self._stt_adapter = get_speech_recognition_adapter()
            except Exception:
                logger.info("语音识别适配器不可用")
        return self._stt_adapter

    async def _get_vision(self):
        if self._vision_adapter is None:
            try:
                from kairos.skills.agent_enhance.integrations.vision_volo import get_vision_volo_adapter
                self._vision_adapter = get_vision_volo_adapter()
            except Exception:
                logger.info("视觉VoLo适配器不可用")
        return self._vision_adapter

    async def _get_memory(self):
        if self._memory is None:
            try:
                from kairos.system.unified_memory_system_v2 import get_unified_memory, MemoryType
                self._memory = get_unified_memory()
            except Exception:
                logger.info("统一记忆系统不可用")
        return self._memory

    async def handle_message(self, msg: WeChatMessage):
        logger.info("处理微信消息: %s (%s) from %s", msg.text[:30] if msg.text else "", msg.message_type, msg.sender_id[:10])

        if self._adapter and hasattr(self._adapter, 'send_typing'):
            await self._adapter.send_typing(msg.sender_id, msg.context_token)

        response_text = ""

        if msg.message_type == "voice" and msg.media_url:
            response_text = await self._handle_voice(msg)
        elif msg.message_type == "image" and msg.media_url:
            response_text = await self._handle_image(msg)
        elif msg.message_type == "text" or msg.text:
            response_text = await self._handle_text(msg)
        else:
            response_text = "收到消息，但暂时无法处理此类型。"

        if response_text and self._adapter:
            await self._adapter.reply(msg.sender_id, response_text, msg.context_token)

        memory = await self._get_memory()
        if memory and msg.text:
            try:
                from kairos.system.unified_memory_system_v2 import MemoryType as MT
                mt = MT.EPISODIC
            except Exception:
                mt = None
            await memory.store(
                content=f"[微信] {msg.sender_id}: {msg.text[:200]}",
                memory_type=mt,
            )
            if response_text:
                await memory.store(
                    content=f"[回复] {response_text[:200]}",
                    memory_type=mt,
                )

    async def _handle_text(self, msg: WeChatMessage) -> str:
        try:
            client = await self._get_llm()
            result = await client.chat(
                user_prompt=msg.text,
                system_prompt="你是鸿蒙小雨，一个智能助手。请简洁专业地回答问题。",
                skill_type="minimax",
                use_cache=True,
            )
            if result.get("status") == "success":
                return result.get("response", "")
            return "抱歉，我暂时无法回答。"
        except Exception as e:
            logger.error("文本处理失败: %s", e)
            return f"处理出错: {str(e)[:50]}"

    async def _handle_voice(self, msg: WeChatMessage) -> str:
        stt = await self._get_stt()
        if not stt:
            return "语音识别功能暂不可用。"

        try:
            result = await stt.recognize(audio_path=msg.media_url, engine="auto")
            transcribed = result.get("text", "")
            if not transcribed:
                return "语音识别未能提取文字内容。"

            client = await self._get_llm()
            llm_result = await client.chat(
                user_prompt=f"[语音转文字] {transcribed}",
                system_prompt="用户通过语音输入了以下内容，请理解并回复：",
                skill_type="minimax",
            )
            return llm_result.get("response", "")
        except Exception as e:
            logger.error("语音处理失败: %s", e)
            return "语音处理出错。"

    async def _handle_image(self, msg: WeChatMessage) -> str:
        vision = await self._get_vision()
        if not vision:
            return "视觉分析功能暂不可用。"

        try:
            result = await vision.analyze(image_input=msg.media_url, top_k=3)
            classification = result.get("classification", {})
            description = result.get("description", "")

            client = await self._get_llm()
            llm_result = await client.chat(
                user_prompt=f"用户发送了一张图片。图片分析结果：分类={classification}，描述={description}。请根据分析结果回复用户。",
                system_prompt="你是鸿蒙小雨，用户发送了图片，请根据视觉分析结果回复。",
                skill_type="minimax",
            )
            return llm_result.get("response", f"图片分析：{description}")
        except Exception as e:
            logger.error("图片处理失败: %s", e)
            return "图片处理出错。"


_clawbot_adapter: Optional[ClawBotChannelAdapter] = None
_clawbot_gateway: Optional[ClawBotGatewayAdapter] = None
_clawbot_bridge: Optional[ClawBotBridge] = None


def get_clawbot_adapter(mode: str = "channel", **kwargs) -> Any:
    global _clawbot_adapter, _clawbot_gateway

    if mode == "gateway":
        if _clawbot_gateway is None:
            _clawbot_gateway = ClawBotGatewayAdapter(**kwargs)
        return _clawbot_gateway
    else:
        if _clawbot_adapter is None:
            _clawbot_adapter = ClawBotChannelAdapter(**kwargs)
        return _clawbot_adapter


def get_clawbot_bridge(adapter=None) -> ClawBotBridge:
    global _clawbot_bridge
    if _clawbot_bridge is None:
        _clawbot_bridge = ClawBotBridge(adapter=adapter)
    return _clawbot_bridge
