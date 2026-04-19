"""
LLM 推理服务
为六层架构和 Agent 系统提供统一的 Ollama 推理接口
替代硬编码关键词匹配，实现真正的智能决策
"""

import os
import json
import time
import logging
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger("LLMReasoning")

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("GEMMA4_MODEL", "gemma4:e4b")
REQUEST_TIMEOUT = int(os.environ.get("GEMMA4_LLM_TIMEOUT", "30"))


@dataclass
class LLMResult:
    content: str
    model: str
    duration_ms: float
    success: bool
    error: str = ""


class OllamaClient:
    """Ollama API 客户端"""

    def __init__(self, host: str = None, model: str = None):
        self.host = host or OLLAMA_HOST
        self.model = model or DEFAULT_MODEL
        self._available: Optional[bool] = None
        self._last_check = 0

    async def is_available(self) -> bool:
        """检查 Ollama 是否可用"""
        now = time.time()
        if self._available is not None and now - self._last_check < 30:
            return self._available

        try:
            import urllib.request
            url = f"{self.host}/api/tags"
            req = urllib.request.Request(url, method="GET")
            req.add_header("Connection", "close")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=5)
            )
            self._available = True
        except Exception:
            self._available = False

        self._last_check = now
        return self._available

    async def generate(self, prompt: str, system: str = "", model: str = None) -> LLMResult:
        """生成推理结果"""
        model = model or self.model
        start = time.time()

        try:
            import urllib.request
            url = f"{self.host}/api/chat"
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            payload = json.dumps({
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 256}
            }).encode('utf-8')

            req = urllib.request.Request(url, data=payload, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("Connection", "close")

            loop = asyncio.get_event_loop()
            resp_data = await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT)
            )
            result = json.loads(resp_data.read().decode('utf-8'))
            content = result.get('message', {}).get('content', '')
            duration = (time.time() - start) * 1000

            return LLMResult(
                content=content.strip(),
                model=model,
                duration_ms=duration,
                success=True
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            logger.error(f"LLM 推理失败: {e}")
            return LLMResult(
                content="",
                model=model,
                duration_ms=duration,
                success=False,
                error=str(e)
            )


_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """获取 Ollama 客户端单例"""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client


# ==================== 六层架构推理接口 ====================

PERCEPTION_SYSTEM = """你是鸿蒙小雨系统的感知层分析器。分析用户输入，返回JSON格式的分析结果。
必须返回以下JSON结构（不要包含其他文字）：
{"priority": "high/medium/low", "category": "问题类型", "sentiment": "positive/neutral/negative", "urgency": 0.0到1.0的数值, "key_entities": ["实体1", "实体2"]}"""

INTEGRATION_SYSTEM = """你是鸿蒙小雨系统的整合层分析器。分析多源数据，返回JSON格式的整合结果。
必须返回以下JSON结构（不要包含其他文字）：
{"conflicts": [], "relations": [], "merged_summary": "整合摘要", "confidence": 0.0到1.0的数值}"""

DECISION_SYSTEM = """你是鸿蒙小雨系统的决策层分析器。基于分析结果做出决策，返回JSON格式的决策。
必须返回以下JSON结构（不要包含其他文字）：
{"action": "执行的动作", "reasoning": "决策理由", "confidence": 0.0到1.0的数值, "requires_tools": true/false, "tool_suggestion": "建议使用的工具或空字符串"}"""

FEEDBACK_SYSTEM = """你是鸿蒙小雨系统的反馈层分析器。评估执行结果，返回JSON格式的反馈。
必须返回以下JSON结构（不要包含其他文字）：
{"satisfaction": 0.0到1.0的数值, "improvement_suggestions": ["建议1"], "should_retry": true/false, "feedback_type": "positive/negative/neutral"}"""

EVALUATION_SYSTEM = """你是鸿蒙小雨系统的评估层分析器。评估整体表现，返回JSON格式的评估。
必须返回以下JSON结构（不要包含其他文字）：
{"overall_score": 0.0到1.0的数值, "strengths": ["优点1"], "weaknesses": ["不足1"], "recommendations": ["建议1"]}"""


async def llm_perceive(input_text: str) -> Dict[str, Any]:
    """感知层 LLM 推理"""
    client = get_ollama_client()
    if not await client.is_available():
        return _fallback_perceive(input_text)

    result = await client.generate(
        prompt=f"分析以下用户输入：\n{input_text}",
        system=PERCEPTION_SYSTEM
    )

    if result.success:
        try:
            return _parse_json_result(result.content)
        except Exception:
            pass

    return _fallback_perceive(input_text)


async def llm_integrate(data: Dict[str, Any]) -> Dict[str, Any]:
    """整合层 LLM 推理"""
    client = get_ollama_client()
    if not await client.is_available():
        return _fallback_integrate(data)

    result = await client.generate(
        prompt=f"整合以下数据：\n{json.dumps(data, ensure_ascii=False)}",
        system=INTEGRATION_SYSTEM
    )

    if result.success:
        try:
            return _parse_json_result(result.content)
        except Exception:
            pass

    return _fallback_integrate(data)


async def llm_decide(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """决策层 LLM 推理"""
    client = get_ollama_client()
    if not await client.is_available():
        return _fallback_decide(analysis)

    result = await client.generate(
        prompt=f"基于以下分析做出决策：\n{json.dumps(analysis, ensure_ascii=False)}",
        system=DECISION_SYSTEM
    )

    if result.success:
        try:
            return _parse_json_result(result.content)
        except Exception:
            pass

    return _fallback_decide(analysis)


async def llm_feedback(execution_result: Dict[str, Any]) -> Dict[str, Any]:
    """反馈层 LLM 推理"""
    client = get_ollama_client()
    if not await client.is_available():
        return _fallback_feedback(execution_result)

    result = await client.generate(
        prompt=f"评估以下执行结果：\n{json.dumps(execution_result, ensure_ascii=False)}",
        system=FEEDBACK_SYSTEM
    )

    if result.success:
        try:
            return _parse_json_result(result.content)
        except Exception:
            pass

    return _fallback_feedback(execution_result)


async def llm_evaluate(performance: Dict[str, Any]) -> Dict[str, Any]:
    """评估层 LLM 推理"""
    client = get_ollama_client()
    if not await client.is_available():
        return _fallback_evaluate(performance)

    result = await client.generate(
        prompt=f"评估以下表现数据：\n{json.dumps(performance, ensure_ascii=False)}",
        system=EVALUATION_SYSTEM
    )

    if result.success:
        try:
            return _parse_json_result(result.content)
        except Exception:
            pass

    return _fallback_evaluate(performance)


# ==================== 关键词回退（Ollama不可用时） ====================

def _parse_json_result(content: str) -> Dict[str, Any]:
    """解析 LLM 返回的 JSON"""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
    start = content.find("{")
    end = content.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(content[start:end])
    raise ValueError("无有效JSON")


def _fallback_perceive(text: str) -> Dict[str, Any]:
    """感知层关键词回退"""
    text_lower = text.lower()
    urgent = any(kw in text_lower for kw in ["紧急", "急", "urgent", "asap", "错误", "崩溃"])
    return {
        "priority": "high" if urgent else "medium",
        "category": "问题" if "？" in text or "?" in text else "陈述",
        "sentiment": "negative" if any(kw in text_lower for kw in ["不好", "差", "错"]) else "neutral",
        "urgency": 0.8 if urgent else 0.3,
        "key_entities": [w for w in text.split() if len(w) > 2][:5],
    }


def _fallback_integrate(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"conflicts": [], "relations": [], "merged_summary": str(data)[:100], "confidence": 0.5}


def _fallback_decide(analysis: Dict[str, Any]) -> Dict[str, Any]:
    return {"action": "对话响应", "reasoning": "Ollama不可用，使用默认决策", "confidence": 0.3, "requires_tools": False, "tool_suggestion": ""}


def _fallback_feedback(result: Dict[str, Any]) -> Dict[str, Any]:
    return {"satisfaction": 0.5, "improvement_suggestions": [], "should_retry": False, "feedback_type": "neutral"}


def _fallback_evaluate(performance: Dict[str, Any]) -> Dict[str, Any]:
    return {"overall_score": 0.5, "strengths": [], "weaknesses": ["Ollama不可用，使用关键词回退"], "recommendations": ["启动Ollama以获得智能推理"]}
