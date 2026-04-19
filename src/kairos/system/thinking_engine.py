#!/usr/bin/env python3
"""
类人深度思考引擎 v1.0
实现四段式强制思考链路：假设→验证→修正→结论
每一步强制留痕、可回溯、可校验，杜绝直觉式输出

设计理念来自增强型设计开发.md：
- 固定四段式强制思考链路
- 强制三元话术：明确知道 / 合理不确定 / 完全不知道
- 未知内容禁止编造，自动标注「信息缺失」
- 所有复杂问题自动拆分多步推理
"""

import time
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger("ThinkingEngine")


class CertaintyLevel(str, Enum):
    """三元话术：置信度级别"""
    KNOWN = "明确知道"
    UNCERTAIN = "合理不确定"
    UNKNOWN = "完全不知道"


class ThinkingPhase(str, Enum):
    """思考阶段"""
    HYPOTHESIS = "假设"
    VERIFICATION = "验证"
    CORRECTION = "修正"
    CONCLUSION = "结论"


@dataclass
class ThinkingStep:
    """思考步骤记录"""
    phase: str
    content: str
    confidence: float
    certainty: str
    evidence: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ThinkingResult:
    """思考结果"""
    query: str
    steps: List[ThinkingStep] = field(default_factory=list)
    conclusion: str = ""
    certainty: str = CertaintyLevel.UNCERTAIN
    confidence: float = 0.0
    reasoning_chain: str = ""
    total_duration_ms: float = 0.0
    needs_more_info: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "conclusion": self.conclusion,
            "certainty": self.certainty,
            "confidence": self.confidence,
            "reasoning_chain": self.reasoning_chain,
            "needs_more_info": self.needs_more_info,
            "total_duration_ms": self.total_duration_ms,
            "steps": [s.to_dict() for s in self.steps]
        }


class ThinkingEngine:
    """类人深度思考引擎

    四段式思考链路:
    1. 假设：基于意图、记忆、现有信息，生成多版本初步猜想
    2. 验证：联动事实核查、工具调用、知识库交叉校验
    3. 修正：剔除错误假设、补充缺失信息、修正逻辑漏洞
    4. 结论：输出最终答案，记录推理链路、置信度、不确定点
    """

    HYPOTHESIS_PROMPT = """你是一个严谨的思考者。针对以下问题，生成多个可能的假设（至少2个，至多5个）。
对每个假设给出初步置信度(0-1)。

问题：{query}
上下文：{context}

请用JSON格式输出：
{{
    "hypotheses": [
        {{"id": 1, "content": "假设内容", "confidence": 0.7, "basis": "依据"}},
        {{"id": 2, "content": "假设内容", "confidence": 0.3, "basis": "依据"}}
    ],
    "key_unknowns": ["不确定的点1", "不确定的点2"]
}}"""

    VERIFICATION_PROMPT = """你是一个严格的事实核查员。请逐一验证以下假设，给出每个假设的验证结果。

原始问题：{query}
假设列表：{hypotheses}

验证规则：
1. 逻辑自洽性检查
2. 常识一致性检查
3. 如有矛盾必须指出

请用JSON格式输出：
{{
    "verification_results": [
        {{"id": 1, "passed": true/false, "issues": ["问题1"], "confidence_adjusted": 0.8}}
    ],
    "conflicts": ["发现的矛盾1"]
}}"""

    CORRECTION_PROMPT = """你是一个逻辑修正专家。基于验证结果，修正假设中的错误。

原始问题：{query}
验证结果：{verification}
原始假设：{hypotheses}

修正规则：
1. 剔除已证伪的假设
2. 补充缺失的关键信息
3. 修正逻辑漏洞
4. 标注仍不确定的点

请用JSON格式输出：
{{
    "corrected_hypotheses": [
        {{"id": 1, "content": "修正后内容", "confidence": 0.85, "corrections": ["修正1"]}}
    ],
    "remaining_unknowns": ["仍不确定的点"],
    "info_needed": ["需要补充的信息"]
}}"""

    CONCLUSION_PROMPT = """你是一个结论生成专家。基于修正后的假设，生成最终结论。

原始问题：{query}
修正后假设：{corrected}

输出规则：
1. 必须使用三元话术之一标注确定性：明确知道 / 合理不确定 / 完全不知道
2. 给出最终置信度(0-1)
3. 列出推理链路（关键步骤）
4. 如有不确定点，标注"信息缺失，需补充检索/调研"

请用JSON格式输出：
{{
    "conclusion": "最终结论",
    "certainty": "明确知道/合理不确定/完全不知道",
    "confidence": 0.85,
    "reasoning_chain": "步骤1→步骤2→步骤3",
    "needs_more_info": true/false,
    "caveats": ["注意事项1"]
}}"""

    def __init__(self, llm_client=None):
        """初始化思考引擎

        Args:
            llm_client: LLM客户端（OllamaClient实例）
        """
        self.llm = llm_client
        self._history: List[ThinkingResult] = []
        logger.info("类人思考引擎初始化完成")

    async def think(self, query: str, context: str = "") -> ThinkingResult:
        """执行完整的四段式思考链路

        Args:
            query: 用户问题
            context: 上下文信息

        Returns:
            ThinkingResult: 完整思考结果
        """
        start_time = time.time()
        result = ThinkingResult(query=query)

        try:
            # 阶段1：假设生成
            step1 = await self._hypothesize(query, context)
            result.steps.append(step1)

            # 阶段2：验证
            hypotheses_str = step1.content
            step2 = await self._verify(query, hypotheses_str)
            result.steps.append(step2)

            # 阶段3：修正
            verification_str = step2.content
            step3 = await self._correct(query, verification_str, hypotheses_str)
            result.steps.append(step3)

            # 阶段4：结论
            corrected_str = step3.content
            step4 = await self._conclude(query, corrected_str)
            result.steps.append(step4)

            # 汇总结果
            result.conclusion = self._extract_field(step4.content, "conclusion", step4.content)
            result.certainty = self._extract_field(step4.content, "certainty", CertaintyLevel.UNCERTAIN)
            result.confidence = float(self._extract_field(step4.content, "confidence", 0.5))
            result.reasoning_chain = self._extract_field(step4.content, "reasoning_chain", "")
            result.needs_more_info = bool(self._extract_field(step4.content, "needs_more_info", False))

        except Exception as e:
            logger.error("思考链路异常: %s", e, exc_info=True)
            result.conclusion = f"思考过程出错: {str(e)}"
            result.certainty = CertaintyLevel.UNKNOWN
            result.confidence = 0.0

        result.total_duration_ms = (time.time() - start_time) * 1000
        self._history.append(result)
        return result

    async def _hypothesize(self, query: str, context: str) -> ThinkingStep:
        """阶段1：假设生成"""
        start = time.time()
        prompt = self.HYPOTHESIS_PROMPT.format(query=query, context=context or "无")
        content = await self._call_llm(prompt)
        confidence = float(self._extract_field(content, "confidence", 0.5))
        certainty = self._judge_certainty(confidence)

        return ThinkingStep(
            phase=ThinkingPhase.HYPOTHESIS,
            content=content,
            confidence=confidence,
            certainty=certainty,
            duration_ms=(time.time() - start) * 1000
        )

    async def _verify(self, query: str, hypotheses: str) -> ThinkingStep:
        """阶段2：验证假设"""
        start = time.time()
        prompt = self.VERIFICATION_PROMPT.format(query=query, hypotheses=hypotheses)
        content = await self._call_llm(prompt)
        confidence = float(self._extract_field(content, "confidence_adjusted", 0.5))
        certainty = self._judge_certainty(confidence)

        return ThinkingStep(
            phase=ThinkingPhase.VERIFICATION,
            content=content,
            confidence=confidence,
            certainty=certainty,
            duration_ms=(time.time() - start) * 1000
        )

    async def _correct(self, query: str, verification: str, hypotheses: str) -> ThinkingStep:
        """阶段3：修正"""
        start = time.time()
        prompt = self.CORRECTION_PROMPT.format(
            query=query, verification=verification, hypotheses=hypotheses
        )
        content = await self._call_llm(prompt)
        confidence = float(self._extract_field(content, "confidence", 0.6))
        certainty = self._judge_certainty(confidence)

        return ThinkingStep(
            phase=ThinkingPhase.CORRECTION,
            content=content,
            confidence=confidence,
            certainty=certainty,
            duration_ms=(time.time() - start) * 1000
        )

    async def _conclude(self, query: str, corrected: str) -> ThinkingStep:
        """阶段4：结论"""
        start = time.time()
        prompt = self.CONCLUSION_PROMPT.format(query=query, corrected=corrected)
        content = await self._call_llm(prompt)
        confidence = float(self._extract_field(content, "confidence", 0.7))
        certainty = self._judge_certainty(confidence)

        return ThinkingStep(
            phase=ThinkingPhase.CONCLUSION,
            content=content,
            confidence=confidence,
            certainty=certainty,
            duration_ms=(time.time() - start) * 1000
        )

    async def _call_llm(self, prompt: str) -> str:
        """调用LLM推理

        Args:
            prompt: 提示词

        Returns:
            LLM响应文本
        """
        if self.llm is None:
            try:
                from kairos.system.llm_reasoning import OllamaClient
                self.llm = OllamaClient()
            except Exception:
                return '{"error": "LLM不可用"}'

        try:
            result = await self.llm.chat(prompt)
            return result
        except Exception as e:
            logger.error("LLM调用失败: %s", e)
            return f'{{"error": "LLM调用失败: {e}"}}'

    @staticmethod
    def _judge_certainty(confidence: float) -> str:
        """根据置信度判断三元话术"""
        if confidence >= 0.8:
            return CertaintyLevel.KNOWN
        elif confidence >= 0.4:
            return CertaintyLevel.UNCERTAIN
        else:
            return CertaintyLevel.UNKNOWN

    @staticmethod
    def _extract_field(json_str: str, field_name: str, default: Any = None) -> Any:
        """从LLM输出中提取JSON字段"""
        try:
            text = json_str.strip()
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                text = text[start:end].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                text = text[start:end].strip()

            json_start = text.find("{")
            json_end = text.rfind("}")
            if json_start != -1 and json_end > json_start:
                text = text[json_start:json_end + 1]

            data = json.loads(text)
            return data.get(field_name, default)
        except (json.JSONDecodeError, ValueError):
            return default

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取思考历史"""
        return [r.to_dict() for r in self._history[-limit:]]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self._history:
            return {"total_thinks": 0}

        confidences = [r.confidence for r in self._history]
        avg_conf = sum(confidences) / len(confidences)
        certainty_dist = {}
        for r in self._history:
            certainty_dist[r.certainty] = certainty_dist.get(r.certainty, 0) + 1

        return {
            "total_thinks": len(self._history),
            "avg_confidence": round(avg_conf, 3),
            "certainty_distribution": certainty_dist,
            "avg_duration_ms": round(sum(r.total_duration_ms for r in self._history) / len(self._history), 1)
        }


_engine_instance: Optional[ThinkingEngine] = None


def get_thinking_engine() -> ThinkingEngine:
    """获取思考引擎单例"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = ThinkingEngine()
    return _engine_instance
