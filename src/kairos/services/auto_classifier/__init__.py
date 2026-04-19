"""
自动模式分类器（Auto Mode Classifier）
借鉴 cc-haha-main 的 yoloClassifier.ts（1495行）：
1. 两阶段 XML 分类器：Stage1 快速判断 → Stage2 深度推理
2. Transcript 构建（对话历史压缩为紧凑格式）
3. 权限模板系统（allow/soft_deny/environment 三类规则）
4. 拒绝追踪（记录最近被拒绝的操作）
5. 熔断器（防止配置被远程禁用后继续运行）
"""

import os
import re
import time
import json
import logging
import asyncio
from enum import Enum
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger("AutoClassifier")

MAX_DENIALS_TRACKED = 20
STAGE1_MAX_TOKENS = 64
STAGE2_MAX_TOKENS = 4096


class ClassificationResult(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class RuleType(Enum):
    ALLOW = "allow"
    SOFT_DENY = "soft_deny"
    ENVIRONMENT = "environment"


@dataclass
class ClassificationRule:
    pattern: str
    rule_type: RuleType
    description: str = ""
    tool_name: Optional[str] = None
    compiled_pattern: Optional[re.Pattern] = None

    def __post_init__(self):
        try:
            self.compiled_pattern = re.compile(self.pattern, re.IGNORECASE)
        except re.error:
            self.compiled_pattern = None

    def matches(self, tool_name: str, tool_input: str) -> bool:
        if self.tool_name and self.tool_name != tool_name:
            return False
        if self.compiled_pattern:
            return bool(self.compiled_pattern.search(tool_input))
        return False


@dataclass
class ClassificationDecision:
    result: ClassificationResult
    reason: str
    stage: int = 1
    confidence: float = 0.0
    rule_matched: Optional[str] = None
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class DenialTracker:
    """拒绝追踪器"""

    def __init__(self, max_tracked: int = MAX_DENIALS_TRACKED):
        self._denials: deque = deque(maxlen=max_tracked)

    def record(self, tool_name: str, tool_input: str, reason: str):
        self._denials.append({
            "tool_name": tool_name,
            "tool_input": tool_input[:200],
            "reason": reason,
            "timestamp": time.time(),
        })

    def get_recent(self, count: int = 10) -> List[Dict[str, Any]]:
        return list(self._denials)[-count:]

    def get_count(self) -> int:
        return len(self._denials)

    def clear(self):
        self._denials.clear()


class CircuitBreaker:
    """熔断器"""

    def __init__(self):
        self._broken = False
        self._broken_at: Optional[float] = None
        self._reason = ""

    def trip(self, reason: str = ""):
        self._broken = True
        self._broken_at = time.time()
        self._reason = reason
        logger.warning(f"自动分类器熔断: {reason}")

    def reset(self):
        self._broken = False
        self._broken_at = None
        self._reason = ""

    @property
    def is_broken(self) -> bool:
        return self._broken

    @property
    def status(self) -> Dict[str, Any]:
        return {
            "broken": self._broken,
            "broken_at": self._broken_at,
            "reason": self._reason,
            "duration_seconds": time.time() - self._broken_at if self._broken_at else 0,
        }


class AutoModeClassifier:
    """自动模式分类器 - LLM 驱动的权限决策"""

    def __init__(self, ollama_chat_fn=None):
        self._chat_fn = ollama_chat_fn
        self._rules: List[ClassificationRule] = []
        self._denial_tracker = DenialTracker()
        self._circuit_breaker = CircuitBreaker()
        self._classification_count = 0
        self._stage1_count = 0
        self._stage2_count = 0
        self._allow_count = 0
        self._deny_count = 0
        self._ask_count = 0
        self._load_default_rules()

    def _load_default_rules(self):
        """加载默认权限规则"""
        default_rules = [
            ClassificationRule(
                pattern=r"^(ls|dir|cat|type|head|tail|pwd|echo|whoami|date|uname)",
                rule_type=RuleType.ALLOW,
                description="只读命令允许执行",
                tool_name="bash",
            ),
            ClassificationRule(
                pattern=r"^(rm|del|rmdir|format|mkfs|dd|shutdown|reboot)",
                rule_type=RuleType.SOFT_DENY,
                description="危险命令需要确认",
                tool_name="bash",
            ),
            ClassificationRule(
                pattern=r"(password|secret|token|api.key|private.key|credential)",
                rule_type=RuleType.SOFT_DENY,
                description="涉及敏感信息的操作需要确认",
            ),
            ClassificationRule(
                pattern=r"\.(env|pem|key|p12|pfx|jks)$",
                rule_type=RuleType.SOFT_DENY,
                description="敏感文件扩展名需要确认",
            ),
            ClassificationRule(
                pattern=r"^(git status|git log|git diff|git branch|git remote)",
                rule_type=RuleType.ALLOW,
                description="Git 只读命令允许执行",
                tool_name="bash",
            ),
            ClassificationRule(
                pattern=r"^(git push|git push|git reset --hard|git clean -f)",
                rule_type=RuleType.SOFT_DENY,
                description="Git 危险操作需要确认",
                tool_name="bash",
            ),
            ClassificationRule(
                pattern=r"^(pip install|npm install|cargo install)",
                rule_type=RuleType.ENVIRONMENT,
                description="环境变更操作需要确认",
                tool_name="bash",
            ),
            ClassificationRule(
                pattern=r".*",
                rule_type=RuleType.ALLOW,
                description="文件读取默认允许",
                tool_name="file_read",
            ),
            ClassificationRule(
                pattern=r".*",
                rule_type=RuleType.ALLOW,
                description="搜索工具默认允许",
                tool_name="grep",
            ),
            ClassificationRule(
                pattern=r".*",
                rule_type=RuleType.ALLOW,
                description="Glob 工具默认允许",
                tool_name="glob",
            ),
        ]
        self._rules.extend(default_rules)

    def add_rule(self, rule: ClassificationRule):
        self._rules.append(rule)

    def remove_rule(self, pattern: str) -> bool:
        for i, rule in enumerate(self._rules):
            if rule.pattern == pattern:
                self._rules.pop(i)
                return True
        return False

    def _build_transcript(self, messages: List[Dict[str, str]], max_length: int = 4000) -> str:
        """将对话历史压缩为紧凑格式供分类器使用"""
        lines = []
        total_len = 0
        for msg in reversed(messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "user":
                prefix = "User"
            elif role == "assistant":
                prefix = "Asst"
            elif role in ("tool", "tool_result"):
                prefix = "Tool"
            else:
                prefix = "Sys"
            line = f"{prefix}: {content[:200]}"
            if total_len + len(line) > max_length:
                break
            lines.insert(0, line)
            total_len += len(line)
        return "\n".join(lines)

    def _check_rules(self, tool_name: str, tool_input: str) -> Optional[ClassificationDecision]:
        """检查规则匹配"""
        soft_deny_match = None
        for rule in self._rules:
            if rule.matches(tool_name, tool_input):
                if rule.rule_type == RuleType.ALLOW:
                    return ClassificationDecision(
                        result=ClassificationResult.ALLOW,
                        reason=f"规则匹配: {rule.description}",
                        rule_matched=rule.pattern,
                    )
                elif rule.rule_type == RuleType.SOFT_DENY:
                    if soft_deny_match is None:
                        soft_deny_match = ClassificationDecision(
                            result=ClassificationResult.ASK,
                            reason=f"软拒绝规则: {rule.description}",
                            rule_matched=rule.pattern,
                        )
                elif rule.rule_type == RuleType.ENVIRONMENT:
                    if soft_deny_match is None:
                        soft_deny_match = ClassificationDecision(
                            result=ClassificationResult.ASK,
                            reason=f"环境变更规则: {rule.description}",
                            rule_matched=rule.pattern,
                        )
        return soft_deny_match

    async def _stage1_classify(self, tool_name: str, tool_input: str,
                               transcript: str) -> Optional[ClassificationResult]:
        """Stage 1: 快速判断（max_tokens=64）"""
        if not self._chat_fn:
            return None

        prompt = f"""判断以下工具调用是否安全，只回答 YES 或 NO：
工具: {tool_name}
输入: {tool_input[:500]}
对话上下文:
{transcript[:2000]}
回答:"""

        try:
            response = await asyncio.wait_for(self._chat_fn(prompt), timeout=10.0)
            response = response.strip().upper()
            if "YES" in response or "是" in response or "安全" in response:
                return ClassificationResult.ALLOW
            if "NO" in response or "否" in response or "危险" in response:
                return ClassificationResult.DENY
            return None
        except asyncio.TimeoutError:
            logger.warning("Stage1 分类超时，回退规则匹配")
            return None
        except Exception as e:
            logger.debug(f"Stage1 分类失败: {e}")
            return None

    async def _stage2_classify(self, tool_name: str, tool_input: str,
                               transcript: str) -> ClassificationDecision:
        """Stage 2: 深度推理（max_tokens=4096）"""
        if not self._chat_fn:
            return ClassificationDecision(
                result=ClassificationResult.ASK,
                reason="无 LLM 可用，默认需要确认",
                stage=2,
            )

        prompt = f"""请详细分析以下工具调用的安全性：

工具名称: {tool_name}
工具输入: {tool_input[:1000]}

对话历史:
{transcript[:3000]}

请分析：
1. 这个操作是否可能造成数据丢失？
2. 是否涉及敏感信息？
3. 是否是不可逆的操作？
4. 是否影响系统环境？

最终判断: ALLOW（允许）/ DENY（拒绝）/ ASK（需要确认）
原因:"""

        try:
            response = await asyncio.wait_for(self._chat_fn(prompt), timeout=15.0)
            response_upper = response.strip().upper()

            if "ALLOW" in response_upper or "允许" in response:
                return ClassificationDecision(
                    result=ClassificationResult.ALLOW,
                    reason=response.strip()[:500],
                    stage=2,
                    confidence=0.8,
                )
            elif "DENY" in response_upper or "拒绝" in response:
                return ClassificationDecision(
                    result=ClassificationResult.DENY,
                    reason=response.strip()[:500],
                    stage=2,
                    confidence=0.8,
                )
            else:
                return ClassificationDecision(
                    result=ClassificationResult.ASK,
                    reason=response.strip()[:500],
                    stage=2,
                    confidence=0.6,
                )
        except asyncio.TimeoutError:
            logger.warning("Stage2 分类超时，回退规则匹配")
            return ClassificationDecision(
                result=ClassificationResult.ASK,
                reason="LLM 分类超时，默认需要确认",
                stage=2,
            )
        except Exception as e:
            logger.debug(f"Stage2 分类失败: {e}")
            return ClassificationDecision(
                result=ClassificationResult.ASK,
                reason=f"分类器异常: {str(e)}",
                stage=2,
            )

    async def classify(self, tool_name: str, tool_input: str,
                       messages: List[Dict[str, str]] = None) -> ClassificationDecision:
        """分类工具调用的权限"""
        if self._circuit_breaker.is_broken:
            return ClassificationDecision(
                result=ClassificationResult.ASK,
                reason="熔断器已触发，所有操作需要确认",
            )

        self._classification_count += 1

        rule_decision = self._check_rules(tool_name, tool_input)
        if rule_decision and rule_decision.result == ClassificationResult.ALLOW:
            self._allow_count += 1
            return rule_decision

        transcript = self._build_transcript(messages or [])

        stage1_result = await self._stage1_classify(tool_name, tool_input, transcript)
        self._stage1_count += 1

        if stage1_result == ClassificationResult.ALLOW:
            self._allow_count += 1
            return ClassificationDecision(
                result=ClassificationResult.ALLOW,
                reason="Stage1 分类: 允许",
                stage=1,
                confidence=0.7,
            )

        if stage1_result == ClassificationResult.DENY:
            stage2_decision = await self._stage2_classify(tool_name, tool_input, transcript)
            self._stage2_count += 1

            if stage2_decision.result == ClassificationResult.DENY:
                self._deny_count += 1
                self._denial_tracker.record(tool_name, tool_input, stage2_decision.reason)
                return stage2_decision

            self._allow_count += 1 if stage2_decision.result == ClassificationResult.ALLOW else 0
            self._ask_count += 1 if stage2_decision.result == ClassificationResult.ASK else 0
            return stage2_decision

        if rule_decision:
            if rule_decision.result == ClassificationResult.ASK:
                self._ask_count += 1
            elif rule_decision.result == ClassificationResult.DENY:
                self._deny_count += 1
                self._denial_tracker.record(tool_name, tool_input, rule_decision.reason)
            return rule_decision

        self._ask_count += 1
        return ClassificationDecision(
            result=ClassificationResult.ASK,
            reason="无匹配规则，默认需要确认",
        )

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_classifications": self._classification_count,
            "stage1_count": self._stage1_count,
            "stage2_count": self._stage2_count,
            "allow_count": self._allow_count,
            "deny_count": self._deny_count,
            "ask_count": self._ask_count,
            "rules_count": len(self._rules),
            "circuit_breaker": self._circuit_breaker.status,
            "recent_denials": self._denial_tracker.get_recent(5),
            "denial_count": self._denial_tracker.get_count(),
        }


_auto_classifier: Optional[AutoModeClassifier] = None


def get_auto_classifier() -> AutoModeClassifier:
    global _auto_classifier
    if _auto_classifier is None:
        _auto_classifier = AutoModeClassifier()
    return _auto_classifier
