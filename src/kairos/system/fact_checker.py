#!/usr/bin/env python3
"""
实时事实核查引擎 v1.0
对LLM输出进行嵌入式校验，评估可信度，识别冲突信息

设计理念来自增强型设计开发.md：
- 推理中嵌入式校验：模型每生成关键结论，自动触发校验
- 可信度打分机制：0-100分置信度标注
- 冲突信息自动比对：多源信息矛盾时，罗列差异
- 强制标注风险：低分内容强制标注
"""

import time
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger("FactChecker")


class ConfidenceLevel(str, Enum):
    """可信度等级"""
    VERIFIED = "已验证"
    LIKELY = "较可信"
    UNCERTAIN = "不确定"
    DISPUTED = "有争议"
    FALSE = "不可信"


class SourceType(str, Enum):
    """信息源类型"""
    INTERNAL_KB = "内部知识库"
    LLM_GENERATED = "LLM生成"
    RULE_ENGINE = "规则引擎"
    USER_PROVIDED = "用户提供"
    EXTERNAL_API = "外部接口"


@dataclass
class VerificationSource:
    """校验来源"""
    source_type: str
    source_name: str
    content: str
    confidence: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationResult:
    """核查结果"""
    claim: str
    confidence_score: float
    confidence_level: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)
    verification_id: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def is_reliable(self) -> bool:
        return self.confidence_score >= 60.0


class FactChecker:
    """事实核查引擎

    核心能力：
    1. 对声明进行可信度评估（0-100分）
    2. 多源交叉验证
    3. 冲突信息识别
    4. 风险标注
    """

    # 可信度阈值
    THRESHOLD_VERIFIED = 80.0
    THRESHOLD_LIKELY = 60.0
    THRESHOLD_UNCERTAIN = 40.0
    THRESHOLD_DISPUTED = 20.0

    # 风险关键词（触发自动标注）
    RISK_PATTERNS = [
        "据传", "据说", "可能", "也许", "大概",
        "有人称", "网传", "未经证实", "待验证",
        "据说", "传闻", "小道消息", "内部消息"
    ]

    # 事实性关键词（提升可信度）
    FACTUAL_PATTERNS = [
        "根据数据", "统计显示", "研究证明", "实验表明",
        "官方公布", "法律规定", "标准规定", "文档记载"
    ]

    def __init__(self, llm_client=None):
        """初始化事实核查引擎

        Args:
            llm_client: LLM客户端（用于深度验证，可选）
        """
        self.llm_client = llm_client
        self._verification_history: List[VerificationResult] = []
        self._knowledge_base: Dict[str, str] = {}
        self._stats = {
            "total_verifications": 0,
            "avg_confidence": 0.0,
            "conflict_count": 0,
            "risk_flag_count": 0
        }

    def load_knowledge(self, facts: Dict[str, str]):
        """加载已知事实到知识库

        Args:
            facts: 键值对形式的已知事实
        """
        self._knowledge_base.update(facts)
        logger.info("加载已知事实 %d 条", len(facts))

    async def verify(self, claim: str, context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        """核查一条声明

        Args:
            claim: 待核查的声明文本
            context: 可选的上下文信息

        Returns:
            VerificationResult 核查结果
        """
        start_time = time.time()
        verification_id = f"vc_{int(start_time * 1000)}"

        logger.info("开始核查: %s", claim[:80])

        # 第1步：规则引擎快速评估
        rule_score, rule_sources = self._rule_based_verify(claim)

        # 第2步：知识库匹配
        kb_score, kb_sources = self._knowledge_base_verify(claim)

        # 第3步：LLM深度验证（如果可用）
        llm_score = 50.0
        llm_sources = []
        if self.llm_client:
            llm_score, llm_sources = await self._llm_verify(claim, context)

        # 合并所有来源
        all_sources = rule_sources + kb_sources + llm_sources

        # 加权计算综合可信度
        weights = {"rule": 0.3, "kb": 0.4, "llm": 0.3}
        if not self.llm_client:
            weights = {"rule": 0.4, "kb": 0.6, "llm": 0.0}

        confidence_score = (
            rule_score * weights["rule"] +
            kb_score * weights["kb"] +
            llm_score * weights["llm"]
        )

        # 识别冲突信息
        conflicts = self._detect_conflicts(all_sources)

        # 风险标注
        risk_flags = self._flag_risks(claim, confidence_score)

        # 确定可信度等级
        confidence_level = self._score_to_level(confidence_score)

        duration_ms = (time.time() - start_time) * 1000

        result = VerificationResult(
            claim=claim,
            confidence_score=round(confidence_score, 1),
            confidence_level=confidence_level,
            sources=[s.to_dict() if hasattr(s, 'to_dict') else s for s in all_sources],
            conflicts=conflicts,
            risk_flags=risk_flags,
            verification_id=verification_id,
            duration_ms=round(duration_ms, 1)
        )

        self._verification_history.append(result)
        self._update_stats(result)

        logger.info(
            "核查完成: %s → %.1f分(%s) 耗时%.1fms",
            claim[:40], confidence_score, confidence_level, duration_ms
        )

        return result

    async def verify_batch(self, claims: List[str], context: Optional[Dict] = None) -> List[VerificationResult]:
        """批量核查多条声明"""
        results = []
        for claim in claims:
            result = await self.verify(claim, context)
            results.append(result)
        return results

    def _rule_based_verify(self, claim: str) -> Tuple[float, List[VerificationSource]]:
        """基于规则的可信度评估

        Returns:
            (score, sources) 分数和来源列表
        """
        score = 50.0
        sources = []

        # 风险关键词降分
        risk_count = sum(1 for p in self.RISK_PATTERNS if p in claim)
        if risk_count > 0:
            score -= risk_count * 10
            sources.append(VerificationSource(
                source_type=SourceType.RULE_ENGINE,
                source_name="风险关键词检测",
                content=f"检测到{risk_count}个风险关键词",
                confidence=max(0, 100 - risk_count * 20)
            ))

        # 事实性关键词加分
        factual_count = sum(1 for p in self.FACTUAL_PATTERNS if p in claim)
        if factual_count > 0:
            score += factual_count * 8
            sources.append(VerificationSource(
                source_type=SourceType.RULE_ENGINE,
                source_name="事实性关键词检测",
                content=f"检测到{factual_count}个事实性关键词",
                confidence=min(100, 60 + factual_count * 15)
            ))

        # 数值/日期/专有名词加分
        import re
        if re.search(r'\d{4}年|\d+月|\d+日|\d+%', claim):
            score += 5
        if re.search(r'[\u4e00-\u9fff]{2,}(省|市|区|县|部|局|院|校)', claim):
            score += 5

        score = max(0, min(100, score))
        return score, sources

    def _knowledge_base_verify(self, claim: str) -> Tuple[float, List[VerificationSource]]:
        """基于知识库的验证

        Returns:
            (score, sources) 分数和来源列表
        """
        if not self._knowledge_base:
            return 50.0, []

        score = 50.0
        sources = []

        for key, value in self._knowledge_base.items():
            if key in claim or claim in key:
                score = max(score, 85.0)
                sources.append(VerificationSource(
                    source_type=SourceType.INTERNAL_KB,
                    source_name="内部知识库",
                    content=f"匹配到已知事实: {key}",
                    confidence=85.0
                ))
                break

            # 语义近似匹配（简单词重叠）
            claim_words = set(claim)
            key_words = set(key)
            overlap = len(claim_words & key_words)
            if overlap > 2:
                similarity = overlap / max(len(claim_words), len(key_words))
                if similarity > 0.3:
                    match_score = 50 + similarity * 40
                    score = max(score, match_score)
                    sources.append(VerificationSource(
                        source_type=SourceType.INTERNAL_KB,
                        source_name="内部知识库(近似)",
                        content=f"近似匹配: {key} (相似度:{similarity:.2f})",
                        confidence=match_score
                    ))

        return score, sources

    async def _llm_verify(self, claim: str, context: Optional[Dict] = None) -> Tuple[float, List[VerificationSource]]:
        """基于LLM的深度验证

        Returns:
            (score, sources) 分数和来源列表
        """
        if not self.llm_client:
            return 50.0, []

        try:
            prompt = (
                "你是一个事实核查专家。请评估以下声明的可信度。\n"
                "返回JSON格式：{\"score\": 0-100, \"reason\": \"评估理由\", "
                "\"certainty\": \"明确知道/合理不确定/完全不知道\"}\n\n"
                f"声明：{claim}"
            )

            if hasattr(self.llm_client, 'chat'):
                response = await asyncio.to_thread(
                    self.llm_client.chat,
                    prompt,
                    "你是事实核查专家，只返回JSON格式。"
                )
            elif hasattr(self.llm_client, 'call_llm'):
                result = await self.llm_client.call_llm(
                    user_prompt=prompt,
                    system_prompt="你是事实核查专家，只返回JSON格式。"
                )
                response = result.get("message", {}).get("content", "")
            else:
                return 50.0, []

            score = self._extract_score(response)
            reason = self._extract_field(response, "reason", "LLM评估")

            sources = [VerificationSource(
                source_type=SourceType.LLM_GENERATED,
                source_name="LLM深度验证",
                content=reason,
                confidence=score
            )]

            return score, sources

        except Exception as e:
            logger.warning("LLM验证失败: %s", e)
            return 50.0, []

    def _detect_conflicts(self, sources: List) -> List[Dict[str, Any]]:
        """检测来源间的冲突"""
        conflicts = []
        if len(sources) < 2:
            return conflicts

        confidences = []
        for s in sources:
            if isinstance(s, VerificationSource):
                confidences.append(s.confidence)
            elif isinstance(s, dict):
                confidences.append(s.get("confidence", 50))

        if len(confidences) >= 2:
            max_conf = max(confidences)
            min_conf = min(confidences)
            if max_conf - min_conf > 30:
                conflicts.append({
                    "type": "confidence_gap",
                    "description": f"来源可信度差异过大: {min_conf:.0f} vs {max_conf:.0f}",
                    "severity": "high" if (max_conf - min_conf) > 50 else "medium"
                })

        return conflicts

    def _flag_risks(self, claim: str, score: float) -> List[str]:
        """风险标注"""
        flags = []

        if score < self.THRESHOLD_UNCERTAIN:
            flags.append("⚠️ 低可信度：该声明可信度较低，请谨慎参考")

        if score < self.THRESHOLD_DISPUTED:
            flags.append("🚫 不可信：该声明缺乏可靠依据，不建议采信")

        for pattern in self.RISK_PATTERNS:
            if pattern in claim:
                flags.append(f"⚠️ 含不确定表述：「{pattern}」")

        if not flags and score >= self.THRESHOLD_LIKELY:
            flags.append("✅ 信息可信度较高")

        return flags

    def _score_to_level(self, score: float) -> str:
        """分数转可信度等级"""
        if score >= self.THRESHOLD_VERIFIED:
            return ConfidenceLevel.VERIFIED
        elif score >= self.THRESHOLD_LIKELY:
            return ConfidenceLevel.LIKELY
        elif score >= self.THRESHOLD_UNCERTAIN:
            return ConfidenceLevel.UNCERTAIN
        elif score >= self.THRESHOLD_DISPUTED:
            return ConfidenceLevel.DISPUTED
        else:
            return ConfidenceLevel.FALSE

    @staticmethod
    def _extract_score(text: str) -> float:
        """从LLM输出中提取分数"""
        try:
            data = json.loads(text.strip())
            if isinstance(data, dict) and "score" in data:
                return float(data["score"])
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        import re
        match = re.search(r'"score"\s*:\s*(\d+(?:\.\d+)?)', text)
        if match:
            return float(match.group(1))

        return 50.0

    @staticmethod
    def _extract_field(text: str, field_name: str, default: Any = None) -> Any:
        """从LLM输出中提取JSON字段"""
        try:
            t = text.strip()
            if "```json" in t:
                start = t.find("```json") + 7
                end = t.find("```", start)
                t = t[start:end].strip()
            json_start = t.find("{")
            json_end = t.rfind("}")
            if json_start != -1 and json_end > json_start:
                data = json.loads(t[json_start:json_end + 1])
                return data.get(field_name, default)
        except (json.JSONDecodeError, ValueError):
            pass
        return default

    def _update_stats(self, result: VerificationResult):
        """更新统计信息"""
        self._stats["total_verifications"] += 1
        total = self._stats["total_verifications"]
        old_avg = self._stats["avg_confidence"]
        self._stats["avg_confidence"] = round(
            (old_avg * (total - 1) + result.confidence_score) / total, 1
        )
        if result.conflicts:
            self._stats["conflict_count"] += 1
        if result.risk_flags:
            self._stats["risk_flag_count"] += 1

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return dict(self._stats)

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取核查历史"""
        return [r.to_dict() for r in self._verification_history[-limit:]]


_checker_instance: Optional[FactChecker] = None


def get_fact_checker() -> FactChecker:
    """获取事实核查引擎单例"""
    global _checker_instance
    if _checker_instance is None:
        _checker_instance = FactChecker()
    return _checker_instance
