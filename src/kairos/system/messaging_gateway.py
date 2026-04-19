"""
消息平台网关
支持多平台消息收发：Telegram、Discord、Slack、微信等
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PlatformType(Enum):
    """平台类型"""
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    WECHAT = "wechat"
    DINGTALK = "dingtalk"
    FEISHU = "feishu"
    WEB = "web"
    CLI = "cli"


@dataclass
class Message:
    """消息数据类"""
    id: str
    platform: str
    sender: str
    content: str
    timestamp: str
    metadata: Dict[str, Any]


@dataclass
class PlatformConfig:
    """平台配置"""
    platform: str
    enabled: bool
    token: str = ""
    webhook_url: str = ""
    extra: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extra is None:
            self.extra = {}


class MessagingGateway:
    """消息平台网关"""
    
    def __init__(self):
        self.platforms: Dict[str, PlatformConfig] = {}
        self.message_handlers: List[Callable] = []
        self.message_history: List[Message] = []
        self.is_running = False
        
        self._init_default_platforms()
        logger.info("消息平台网关初始化")
    
    def _init_default_platforms(self):
        """初始化默认平台配置"""
        for platform in PlatformType:
            self.platforms[platform.value] = PlatformConfig(
                platform=platform.value,
                enabled=False
            )
    
    def configure_platform(self, platform: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """配置平台"""
        if platform not in self.platforms:
            self.platforms[platform] = PlatformConfig(
                platform=platform,
                enabled=config.get("enabled", False),
                token=config.get("token", ""),
                webhook_url=config.get("webhook_url", ""),
                extra=config.get("extra", {})
            )
        else:
            existing = self.platforms[platform]
            existing.enabled = config.get("enabled", existing.enabled)
            existing.token = config.get("token", existing.token)
            existing.webhook_url = config.get("webhook_url", existing.webhook_url)
            if "extra" in config:
                existing.extra = config["extra"]
        
        logger.info(f"平台配置更新: {platform}")
        return {"status": "success", "platform": platform}
    
    def register_handler(self, handler: Callable):
        """注册消息处理器"""
        self.message_handlers.append(handler)
        logger.info(f"消息处理器注册: {handler.__name__}")
    
    async def send_message(self, platform: str, recipient: str, 
                          content: str, **kwargs) -> Dict[str, Any]:
        """发送消息"""
        if platform not in self.platforms:
            return {"status": "error", "error": f"平台未配置: {platform}"}
        
        config = self.platforms[platform]
        if not config.enabled:
            return {"status": "error", "error": f"平台未启用: {platform}"}
        
        message = Message(
            id=f"msg_{int(datetime.now().timestamp())}",
            platform=platform,
            sender="system",
            content=content,
            timestamp=datetime.now().isoformat(),
            metadata={"recipient": recipient, **kwargs}
        )
        
        self.message_history.append(message)
        
        try:
            result = await self._send_to_platform(platform, recipient, content, config, **kwargs)
            logger.info(f"消息发送成功: {platform} -> {recipient}")
            return result
        except Exception as e:
            logger.error(f"消息发送失败: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _send_to_platform(self, platform: str, recipient: str, 
                                content: str, config: PlatformConfig, **kwargs) -> Dict[str, Any]:
        """发送到具体平台"""
        if platform == PlatformType.TELEGRAM.value:
            return await self._send_telegram(recipient, content, config)
        elif platform == PlatformType.DISCORD.value:
            return await self._send_discord(recipient, content, config)
        elif platform == PlatformType.SLACK.value:
            return await self._send_slack(recipient, content, config)
        elif platform == PlatformType.WEB.value:
            return {"status": "success", "message": "Web消息已发送", "content": content}
        elif platform == PlatformType.CLI.value:
            print(f"\n[消息] {content}\n")
            return {"status": "success", "message": "CLI消息已输出"}
        else:
            return {"status": "simulated", "message": f"模拟发送到 {platform}"}
    
    async def _send_telegram(self, chat_id: str, content: str, 
                            config: PlatformConfig) -> Dict[str, Any]:
        """发送Telegram消息"""
        try:
            import aiohttp
            
            if not config.token:
                return {"status": "error", "error": "Telegram token未配置"}
            
            url = f"https://api.telegram.org/bot{config.token}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": content,
                "parse_mode": "Markdown"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    result = await response.json()
                    if result.get("ok"):
                        return {"status": "success", "message_id": result["result"]["message_id"]}
                    else:
                        return {"status": "error", "error": result.get("description")}
                        
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _send_discord(self, channel_id: str, content: str, 
                           config: PlatformConfig) -> Dict[str, Any]:
        """发送Discord消息"""
        try:
            import aiohttp
            
            if not config.token:
                return {"status": "error", "error": "Discord token未配置"}
            
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            headers = {
                "Authorization": f"Bot {config.token}",
                "Content-Type": "application/json"
            }
            data = {"content": content}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {"status": "success", "message_id": result["id"]}
                    else:
                        return {"status": "error", "error": f"HTTP {response.status}"}
                        
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _send_slack(self, channel: str, content: str, 
                         config: PlatformConfig) -> Dict[str, Any]:
        """发送Slack消息"""
        try:
            import aiohttp
            
            if not config.token:
                return {"status": "error", "error": "Slack token未配置"}
            
            url = "https://slack.com/api/chat.postMessage"
            headers = {
                "Authorization": f"Bearer {config.token}",
                "Content-Type": "application/json"
            }
            data = {
                "channel": channel,
                "text": content
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    result = await response.json()
                    if result.get("ok"):
                        return {"status": "success", "ts": result["ts"]}
                    else:
                        return {"status": "error", "error": result.get("error")}
                        
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def receive_message(self, platform: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """接收消息"""
        message = Message(
            id=message_data.get("id", f"msg_{int(datetime.now().timestamp())}"),
            platform=platform,
            sender=message_data.get("sender", "unknown"),
            content=message_data.get("content", ""),
            timestamp=message_data.get("timestamp", datetime.now().isoformat()),
            metadata=message_data.get("metadata", {})
        )
        
        self.message_history.append(message)
        
        # 调用处理器
        for handler in self.message_handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"消息处理器错误: {e}")
        
        logger.info(f"消息接收: {platform} from {message.sender}")
        return {"status": "success", "message_id": message.id}
    
    async def broadcast(self, content: str, platforms: List[str] = None) -> Dict[str, Any]:
        """广播消息到多个平台"""
        results = {}
        target_platforms = platforms or [p for p, c in self.platforms.items() if c.enabled]
        
        for platform in target_platforms:
            result = await self.send_message(platform, "broadcast", content)
            results[platform] = result
        
        return {
            "status": "success",
            "broadcast_results": results,
            "platforms_count": len(target_platforms)
        }
    
    def get_platforms(self) -> Dict[str, Any]:
        """获取平台列表"""
        return {
            "status": "success",
            "platforms": {
                name: {
                    "enabled": config.enabled,
                    "configured": bool(config.token or config.webhook_url)
                }
                for name, config in self.platforms.items()
            }
        }
    
    def get_message_history(self, platform: str = None, limit: int = 50) -> Dict[str, Any]:
        """获取消息历史"""
        messages = self.message_history
        
        if platform:
            messages = [m for m in messages if m.platform == platform]
        
        return {
            "status": "success",
            "messages": [
                {
                    "id": m.id,
                    "platform": m.platform,
                    "sender": m.sender,
                    "content": m.content[:100] + "..." if len(m.content) > 100 else m.content,
                    "timestamp": m.timestamp
                }
                for m in messages[-limit:]
            ],
            "total": len(messages)
        }
    
    async def start(self):
        """启动网关"""
        self.is_running = True
        logger.info("消息平台网关已启动")
        return {"status": "success", "message": "网关已启动"}
    
    async def stop(self):
        """停止网关"""
        self.is_running = False
        logger.info("消息平台网关已停止")
        return {"status": "success", "message": "网关已停止"}


messaging_gateway = MessagingGateway()
