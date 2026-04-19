"""
浏览器自动化模块
基于 Playwright 实现网页自动化操作
支持：打开浏览器、导航、点击、输入、截图、提取内容等
"""

import asyncio
import logging
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class BrowserAction(Enum):
    """浏览器操作类型"""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCREENSHOT = "screenshot"
    EXTRACT = "extract"
    SCROLL = "scroll"
    WAIT = "wait"
    FILL = "fill"
    SELECT = "select"
    HOVER = "hover"
    PRESS = "press"
    GO_BACK = "go_back"
    GO_FORWARD = "go_forward"
    REFRESH = "refresh"
    CLOSE = "close"


@dataclass
class BrowserState:
    """浏览器状态"""
    url: str = ""
    title: str = ""
    is_active: bool = False
    last_action: str = ""
    last_action_time: str = ""


class BrowserAutomation:
    """浏览器自动化类"""
    
    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self.browser = None
        self.context = None
        self.page = None
        self.state = BrowserState()
        self.action_history = []
        self._playwright = None
        
        logger.info(f"浏览器自动化模块初始化 (headless={headless})")
    
    async def initialize(self) -> Dict[str, Any]:
        """初始化浏览器"""
        try:
            from playwright.async_api import async_playwright
            
            self._playwright = await async_playwright().start()
            self.browser = await self._playwright.chromium.launch(headless=self.headless)
            self.context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            self.page = await self.context.new_page()
            self.state.is_active = True
            
            logger.info("浏览器初始化成功")
            return {"status": "success", "message": "浏览器初始化成功"}
            
        except ImportError:
            logger.warning("Playwright未安装，使用模拟模式")
            self.state.is_active = True
            return {"status": "success", "message": "浏览器模拟模式启动"}
        except Exception as e:
            logger.error(f"浏览器初始化失败: {e}")
            return {"status": "error", "error": str(e)}
    
    async def navigate(self, url: str) -> Dict[str, Any]:
        """导航到URL"""
        action_record = {
            "action": "navigate",
            "url": url,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            if self.page:
                await self.page.goto(url, timeout=self.timeout)
                self.state.url = url
                self.state.title = await self.page.title()
            else:
                self.state.url = url
                self.state.title = "模拟页面"
            
            self.state.last_action = "navigate"
            self.state.last_action_time = datetime.now().isoformat()
            self.action_history.append(action_record)
            
            logger.info(f"导航成功: {url}")
            return {
                "status": "success",
                "url": url,
                "title": self.state.title
            }
            
        except Exception as e:
            action_record["error"] = str(e)
            self.action_history.append(action_record)
            logger.error(f"导航失败: {e}")
            return {"status": "error", "error": str(e)}
    
    async def click(self, selector: str) -> Dict[str, Any]:
        """点击元素"""
        action_record = {
            "action": "click",
            "selector": selector,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            if self.page:
                await self.page.click(selector, timeout=self.timeout)
            
            self.state.last_action = "click"
            self.state.last_action_time = datetime.now().isoformat()
            self.action_history.append(action_record)
            
            logger.info(f"点击成功: {selector}")
            return {"status": "success", "selector": selector}
            
        except Exception as e:
            action_record["error"] = str(e)
            self.action_history.append(action_record)
            logger.error(f"点击失败: {e}")
            return {"status": "error", "error": str(e)}
    
    async def type_text(self, selector: str, text: str, delay: int = 50) -> Dict[str, Any]:
        """输入文本"""
        action_record = {
            "action": "type",
            "selector": selector,
            "text": text[:50] + "..." if len(text) > 50 else text,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            if self.page:
                await self.page.type(selector, text, delay=delay)
            
            self.state.last_action = "type"
            self.state.last_action_time = datetime.now().isoformat()
            self.action_history.append(action_record)
            
            logger.info(f"输入成功: {selector}")
            return {"status": "success", "selector": selector, "text_length": len(text)}
            
        except Exception as e:
            action_record["error"] = str(e)
            self.action_history.append(action_record)
            logger.error(f"输入失败: {e}")
            return {"status": "error", "error": str(e)}
    
    async def fill(self, selector: str, value: str) -> Dict[str, Any]:
        """填充表单字段"""
        action_record = {
            "action": "fill",
            "selector": selector,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            if self.page:
                await self.page.fill(selector, value)
            
            self.state.last_action = "fill"
            self.state.last_action_time = datetime.now().isoformat()
            self.action_history.append(action_record)
            
            logger.info(f"填充成功: {selector}")
            return {"status": "success", "selector": selector}
            
        except Exception as e:
            action_record["error"] = str(e)
            self.action_history.append(action_record)
            logger.error(f"填充失败: {e}")
            return {"status": "error", "error": str(e)}
    
    async def screenshot(self, path: str = None) -> Dict[str, Any]:
        """截图"""
        if path is None:
            path = f"./logs/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        action_record = {
            "action": "screenshot",
            "path": path,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            if self.page:
                await self.page.screenshot(path=path)
            
            self.state.last_action = "screenshot"
            self.state.last_action_time = datetime.now().isoformat()
            self.action_history.append(action_record)
            
            logger.info(f"截图成功: {path}")
            return {"status": "success", "path": path}
            
        except Exception as e:
            action_record["error"] = str(e)
            self.action_history.append(action_record)
            logger.error(f"截图失败: {e}")
            return {"status": "error", "error": str(e)}
    
    async def extract_text(self, selector: str = "body") -> Dict[str, Any]:
        """提取页面文本"""
        action_record = {
            "action": "extract_text",
            "selector": selector,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            text = ""
            if self.page:
                element = await self.page.query_selector(selector)
                if element:
                    text = await element.inner_text()
            
            self.state.last_action = "extract_text"
            self.state.last_action_time = datetime.now().isoformat()
            self.action_history.append(action_record)
            
            logger.info(f"提取文本成功: {len(text)}字符")
            return {"status": "success", "text": text, "length": len(text)}
            
        except Exception as e:
            action_record["error"] = str(e)
            self.action_history.append(action_record)
            logger.error(f"提取文本失败: {e}")
            return {"status": "error", "error": str(e)}
    
    async def extract_links(self) -> Dict[str, Any]:
        """提取页面链接"""
        action_record = {
            "action": "extract_links",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            links = []
            if self.page:
                elements = await self.page.query_selector_all("a[href]")
                for element in elements:
                    href = await element.get_attribute("href")
                    text = await element.inner_text()
                    if href:
                        links.append({"href": href, "text": text.strip()})
            
            self.state.last_action = "extract_links"
            self.state.last_action_time = datetime.now().isoformat()
            self.action_history.append(action_record)
            
            logger.info(f"提取链接成功: {len(links)}个")
            return {"status": "success", "links": links, "count": len(links)}
            
        except Exception as e:
            action_record["error"] = str(e)
            self.action_history.append(action_record)
            logger.error(f"提取链接失败: {e}")
            return {"status": "error", "error": str(e)}
    
    async def wait_for_selector(self, selector: str, timeout: int = None) -> Dict[str, Any]:
        """等待元素出现"""
        timeout = timeout or self.timeout
        
        try:
            if self.page:
                await self.page.wait_for_selector(selector, timeout=timeout)
            
            logger.info(f"等待元素成功: {selector}")
            return {"status": "success", "selector": selector}
            
        except Exception as e:
            logger.error(f"等待元素失败: {e}")
            return {"status": "error", "error": str(e)}
    
    async def scroll(self, direction: str = "down", distance: int = 500) -> Dict[str, Any]:
        """滚动页面"""
        try:
            if self.page:
                if direction == "down":
                    await self.page.evaluate(f"window.scrollBy(0, {distance})")
                else:
                    await self.page.evaluate(f"window.scrollBy(0, -{distance})")
            
            logger.info(f"滚动成功: {direction}")
            return {"status": "success", "direction": direction, "distance": distance}
            
        except Exception as e:
            logger.error(f"滚动失败: {e}")
            return {"status": "error", "error": str(e)}
    
    async def execute_script(self, script: str) -> Dict[str, Any]:
        """执行JavaScript脚本"""
        try:
            result = None
            if self.page:
                result = await self.page.evaluate(script)
            
            logger.info("脚本执行成功")
            return {"status": "success", "result": result}
            
        except Exception as e:
            logger.error(f"脚本执行失败: {e}")
            return {"status": "error", "error": str(e)}
    
    async def close(self) -> Dict[str, Any]:
        """关闭浏览器"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self._playwright:
                await self._playwright.stop()
            
            self.state.is_active = False
            self.state.last_action = "close"
            self.state.last_action_time = datetime.now().isoformat()
            
            logger.info("浏览器已关闭")
            return {"status": "success", "message": "浏览器已关闭"}
            
        except Exception as e:
            logger.error(f"关闭浏览器失败: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_state(self) -> Dict[str, Any]:
        """获取浏览器状态"""
        return {
            "status": "success",
            "state": {
                "url": self.state.url,
                "title": self.state.title,
                "is_active": self.state.is_active,
                "last_action": self.state.last_action,
                "last_action_time": self.state.last_action_time
            },
            "action_count": len(self.action_history)
        }
    
    def get_history(self, limit: int = 20) -> Dict[str, Any]:
        """获取操作历史"""
        return {
            "status": "success",
            "history": self.action_history[-limit:],
            "total": len(self.action_history)
        }


browser_automation = BrowserAutomation()
