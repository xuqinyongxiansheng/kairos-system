"""
权限系统
借鉴 cc-haha-main 的权限管道架构：
- 多级权限模式（default/acceptEdits/bypassPermissions/auto）
- 权限规则（allow/deny/ask）
- 工具权限检查管道
- MCP 工具命名空间规则

完全重写实现，适配本地大模型服务场景
"""

import os
import json
import time
import logging
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field

logger = logging.getLogger("PermissionSystem")


class PermissionMode(str, Enum):
    DEFAULT = "default"
    ACCEPT_EDITS = "acceptEdits"
    BYPASS = "bypassPermissions"
    AUTO = "auto"


class RuleBehavior(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass
class PermissionRule:
    tool_name: str
    behavior: RuleBehavior = RuleBehavior.ASK
    rule_content: str = ""
    source: str = "user"

    def matches(self, tool_name: str, content: str = "") -> bool:
        if self.tool_name == "*":
            return True
        if self.tool_name == tool_name:
            return True
        if self.tool_name.endswith(".*"):
            prefix = self.tool_name[:-1]
            if tool_name.startswith(prefix):
                return True
        if self.tool_name.startswith("mcp__"):
            parts = tool_name.split("__")
            rule_parts = self.tool_name.split("__")
            if len(rule_parts) >= 2 and len(parts) >= 2:
                if rule_parts[0] == parts[0] and rule_parts[1] == parts[1]:
                    if len(rule_parts) == 2 or rule_parts[2] == "*":
                        return True
        return False


@dataclass
class PermissionResult:
    allowed: bool
    behavior: RuleBehavior = RuleBehavior.ASK
    reason: str = ""
    rule: Optional[PermissionRule] = None


class PermissionChecker:
    """权限检查器"""

    def __init__(self):
        self._mode = PermissionMode.DEFAULT
        self._rules: List[PermissionRule] = []
        self._deny_count = 0
        self._max_consecutive_denies = 5
        self._auto_classifier: Optional[Callable] = None
        self._interaction_callback: Optional[Callable] = None
        self._load_default_rules()

    def _load_default_rules(self):
        self._rules.extend([
            PermissionRule("file_read", RuleBehavior.ALLOW, source="default"),
            PermissionRule("glob", RuleBehavior.ALLOW, source="default"),
            PermissionRule("grep", RuleBehavior.ALLOW, source="default"),
            PermissionRule("list_dir", RuleBehavior.ALLOW, source="default"),
            PermissionRule("web_fetch", RuleBehavior.ALLOW, source="default"),
            PermissionRule("file_edit", RuleBehavior.ASK, source="default"),
            PermissionRule("file_write", RuleBehavior.ASK, source="default"),
            PermissionRule("bash", RuleBehavior.ASK, source="default"),
            PermissionRule("workflow", RuleBehavior.ASK, source="default"),
        ])

    def set_mode(self, mode: PermissionMode):
        self._mode = mode
        logger.info(f"权限模式切换为: {mode.value}")

    def add_rule(self, rule: PermissionRule):
        self._rules.append(rule)

    def remove_rule(self, tool_name: str, behavior: RuleBehavior) -> bool:
        for i, r in enumerate(self._rules):
            if r.tool_name == tool_name and r.behavior == behavior:
                self._rules.pop(i)
                return True
        return False

    def set_interaction_callback(self, callback: Callable):
        self._interaction_callback = callback

    def set_auto_classifier(self, classifier: Callable):
        self._auto_classifier = classifier

    def check_permission(self, tool_name: str, content: str = "",
                         is_read_only: bool = False,
                         is_destructive: bool = False) -> PermissionResult:
        """检查工具执行权限"""
        if self._mode == PermissionMode.BYPASS:
            return PermissionResult(allowed=True, behavior=RuleBehavior.ALLOW,
                                    reason="绕过权限模式")

        deny_rule = self._find_rule(tool_name, content, RuleBehavior.DENY)
        if deny_rule:
            self._deny_count += 1
            return PermissionResult(allowed=False, behavior=RuleBehavior.DENY,
                                    reason=f"被拒绝规则阻止: {deny_rule.tool_name}",
                                    rule=deny_rule)

        if is_destructive:
            ask_rule = self._find_rule(tool_name, content, RuleBehavior.ASK)
            if ask_rule or self._mode == PermissionMode.DEFAULT:
                return PermissionResult(allowed=False, behavior=RuleBehavior.ASK,
                                        reason="破坏性操作需要确认")

        allow_rule = self._find_rule(tool_name, content, RuleBehavior.ALLOW)
        if allow_rule:
            self._deny_count = 0
            return PermissionResult(allowed=True, behavior=RuleBehavior.ALLOW,
                                    reason=f"被允许规则通过: {allow_rule.tool_name}",
                                    rule=allow_rule)

        if is_read_only:
            self._deny_count = 0
            return PermissionResult(allowed=True, behavior=RuleBehavior.ALLOW,
                                    reason="只读操作自动允许")

        if self._mode == PermissionMode.ACCEPT_EDITS and not is_destructive:
            self._deny_count = 0
            return PermissionResult(allowed=True, behavior=RuleBehavior.ALLOW,
                                    reason="接受编辑模式")

        if self._mode == PermissionMode.AUTO:
            return self._auto_classify(tool_name, content)

        self._deny_count = 0
        return PermissionResult(allowed=False, behavior=RuleBehavior.ASK,
                                reason="需要用户确认")

    def _find_rule(self, tool_name: str, content: str,
                   behavior: RuleBehavior) -> Optional[PermissionRule]:
        for rule in reversed(self._rules):
            if rule.behavior == behavior and rule.matches(tool_name, content):
                return rule
        return None

    def _auto_classify(self, tool_name: str, content: str) -> PermissionResult:
        if self._auto_classifier:
            try:
                result = self._auto_classifier(tool_name, content)
                if result:
                    self._deny_count = 0
                    return PermissionResult(allowed=True, behavior=RuleBehavior.ALLOW,
                                            reason="AI 分类器允许")
            except Exception as e:
                logger.error(f"AI 分类器异常: {e}")

        safe_tools = {"file_read", "glob", "grep", "list_dir", "web_fetch"}
        if tool_name in safe_tools:
            return PermissionResult(allowed=True, behavior=RuleBehavior.ALLOW,
                                    reason="安全工具白名单")

        return PermissionResult(allowed=False, behavior=RuleBehavior.ASK,
                                reason="自动模式需要确认")

    def list_rules(self) -> List[Dict[str, Any]]:
        return [
            {
                "tool_name": r.tool_name,
                "behavior": r.behavior.value,
                "rule_content": r.rule_content,
                "source": r.source,
            }
            for r in self._rules
        ]

    def get_status(self) -> Dict[str, Any]:
        return {
            "mode": self._mode.value,
            "rules_count": len(self._rules),
            "consecutive_denies": self._deny_count,
        }


_permission_checker: Optional[PermissionChecker] = None


def get_permission_checker() -> PermissionChecker:
    global _permission_checker
    if _permission_checker is None:
        _permission_checker = PermissionChecker()
    return _permission_checker
