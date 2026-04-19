#!/usr/bin/env python3
"""
内容创作Agent
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List

from .base_agent import ProfessionalAgent

logger = logging.getLogger(__name__)


class ContentAgent(ProfessionalAgent):
    """内容创作Agent"""
    
    def __init__(self, agent_id: str = "content_agent"):
        super().__init__(
            agent_id=agent_id,
            name="内容创作Agent",
            description="专注于内容创作、文案生成和创意写作的专业Agent"
        )
        
        # 添加技能
        self.add_skill("article_writing")
        self.add_skill("copywriting")
        self.add_skill("creative_writing")
        self.add_skill("content_editing")
        self.add_skill("social_media_content")
        
        # 添加能力
        self.add_capability("blog_posts")
        self.add_capability("marketing_copy")
        self.add_capability("creative_stories")
        self.add_capability("social_media_posts")
        self.add_capability("email_campaigns")
    
    async def process_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理内容创作相关任务"""
        try:
            # 分析任务类型
            task_lower = task.lower()
            
            if "文章" in task_lower or "article" in task_lower:
                return await self._write_article(task, context)
            elif "文案" in task_lower or "copy" in task_lower:
                return await self._write_copy(task, context)
            elif "创意" in task_lower or "creative" in task_lower:
                return await self._write_creative(task, context)
            elif "编辑" in task_lower or "edit" in task_lower:
                return await self._edit_content(task, context)
            elif "社交媒体" in task_lower or "social media" in task_lower:
                return await self._write_social_media(task, context)
            else:
                return await self._handle_generic_content_task(task, context)
        except Exception as e:
            logger.error(f"处理内容创作任务失败: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _write_article(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """写文章"""
        topic = context.get("topic", task) if context else task
        word_count = context.get("word_count", 500) if context else 500
        tone = context.get("tone", "professional") if context else "professional"
        
        # 生成文章
        article = f"""# {topic}

## 引言
这是一篇关于{topic}的文章。在当今快速发展的时代，{topic}已经成为我们生活中不可或缺的一部分。

## 主要内容

### 第一部分
{topic}的重要性体现在多个方面。首先，它影响着我们的日常生活，改变了我们的工作方式和生活习惯。其次，它在行业发展中扮演着重要角色，推动着技术创新和社会进步。

### 第二部分
在未来，{topic}将继续发挥重要作用。随着技术的不断发展，我们可以期待{topic}在更多领域得到应用，为人类社会带来更多福祉。

## 结论
总之，{topic}是一个值得我们深入研究和关注的话题。通过了解{topic}的发展趋势和应用前景，我们可以更好地把握未来的发展方向。
"""
        
        return {
            "status": "success",
            "article": article,
            "word_count": len(article.split()),
            "tone": tone,
            "structure": ["引言", "主要内容", "结论"]
        }
    
    async def _write_copy(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """写文案"""
        product = context.get("product", "产品") if context else "产品"
        target_audience = context.get("target_audience", "消费者") if context else "消费者"
        key_features = context.get("key_features", ["高质量", "性价比高"]) if context else ["高质量", "性价比高"]
        
        # 生成文案
        copy = f"""{product} - 为{target_audience}打造的理想选择

🌟 为什么选择{product}？

{"\n".join([f"• {feature}" for feature in key_features])}

🔥 限时优惠
现在购买{product}，享受超值优惠！

立即行动，体验{product}带来的卓越体验！
"""
        
        return {
            "status": "success",
            "copy": copy,
            "product": product,
            "target_audience": target_audience,
            "key_features": key_features
        }
    
    async def _write_creative(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创意写作"""
        genre = context.get("genre", "故事") if context else "故事"
        theme = context.get("theme", "友情") if context else "友情"
        length = context.get("length", "短篇") if context else "短篇"
        
        # 生成创意内容
        creative_content = f"""# {theme}的故事

从前，在一个遥远的地方，有两个好朋友，他们一起经历了许多冒险。

一天，他们遇到了一个挑战，需要共同面对。在困难面前，他们相互支持，最终克服了困难。

这个故事告诉我们，{theme}的力量是无穷的，它可以帮助我们度过难关，走向成功。
"""
        
        return {
            "status": "success",
            "creative_content": creative_content,
            "genre": genre,
            "theme": theme,
            "length": length
        }
    
    async def _edit_content(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """编辑内容"""
        content = context.get("content", "") if context else ""
        
        if not content:
            return {
                "status": "error",
                "error": "未提供内容"
            }
        
        # 编辑内容
        edited_content = content
        
        # 简单的编辑示例
        if "非常好" in edited_content:
            edited_content = edited_content.replace("非常好", "非常优秀")
        if "但是" in edited_content:
            edited_content = edited_content.replace("但是", "然而")
        
        return {
            "status": "success",
            "original_content": content,
            "edited_content": edited_content,
            "editing_suggestions": ["用词优化", "语句流畅度提升"]
        }
    
    async def _write_social_media(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """写社交媒体内容"""
        platform = context.get("platform", "微信") if context else "微信"
        content_type = context.get("content_type", "图文") if context else "图文"
        topic = context.get("topic", "日常分享") if context else "日常分享"
        
        # 生成社交媒体内容
        social_content = f"""【{topic}】

今天想和大家分享一下{topic}的一些心得。

✨ 要点一：保持积极心态
✨ 要点二：坚持学习
✨ 要点三：与人为善

希望这些内容对大家有所帮助！

#生活感悟 #正能量 #分享
"""
        
        return {
            "status": "success",
            "social_content": social_content,
            "platform": platform,
            "content_type": content_type,
            "topic": topic
        }
    
    async def _handle_generic_content_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理通用内容任务"""
        return {
            "status": "success",
            "response": f"内容创作Agent正在处理任务: {task}",
            "agent_id": self.agent_id
        }


# 全局内容创作Agent实例
_content_agent = None

def get_content_agent() -> ContentAgent:
    """获取内容创作Agent实例"""
    global _content_agent
    if _content_agent is None:
        _content_agent = ContentAgent()
    return _content_agent