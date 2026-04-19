# -*- coding: utf-8 -*-
"""
记忆分类体系

四类型记忆分类法，确保只保存不可从当前项目状态推导的信息：
  user     → 用户角色、目标、偏好、知识水平
  feedback → 用户指导（避免什么、继续什么），含成功和失败记录
  project  → 项目状态、决策、约束（非代码可推导的部分）
  reference→ 外部系统指针（追踪系统、文档位置等）

核心原则：
  "不保存可推导信息" — 代码模式、架构、git历史、文件结构均可推导，
  不应保存为记忆。

参考: Claude Code memoryTypes.ts
"""

import re
import logging
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class MemoryCategory(Enum):
    USER = "user"
    FEEDBACK = "feedback"
    PROJECT = "project"
    REFERENCE = "reference"


MEMORY_TYPES = [MemoryCategory.USER, MemoryCategory.FEEDBACK,
                MemoryCategory.PROJECT, MemoryCategory.REFERENCE]

MEMORY_TYPE_NAMES = [t.value for t in MEMORY_TYPES]


@dataclass
class MemoryTypeSpec:
    name: str
    description: str
    when_to_save: str
    how_to_use: str
    body_structure: Optional[str] = None
    examples: List[Tuple[str, str]] = field(default_factory=list)


MEMORY_TYPE_SPECS: Dict[MemoryCategory, MemoryTypeSpec] = {
    MemoryCategory.USER: MemoryTypeSpec(
        name="user",
        description=(
            "包含用户角色、目标、职责和知识水平的信息。"
            "优秀的用户记忆帮助系统针对用户偏好和视角定制行为。"
            "目标是建立对用户是谁以及如何最有帮助的理解。"
            "避免保存可能被视为负面评价或与当前工作无关的记忆。"
        ),
        when_to_save="当了解到用户的角色、偏好、职责或知识水平时",
        how_to_use=(
            "当工作应基于用户画像或视角时使用。"
            "例如，解释代码时应针对用户会最重视的具体细节。"
        ),
        examples=[
            ("我是数据科学家，正在调查日志系统", "保存用户记忆：用户是数据科学家，当前关注可观测性/日志"),
            ("我写了十年Go，但第一次接触React", "保存用户记忆：深度Go专长，React新手——用后端类比解释前端"),
        ],
    ),
    MemoryCategory.FEEDBACK: MemoryTypeSpec(
        name="feedback",
        description=(
            "用户给出的工作指导——包括避免什么和继续什么。"
            "这是非常重要的记忆类型，使系统保持连贯和响应。"
            "记录失败和成功：仅保存纠正会避免过去错误，"
            "但会偏离已验证的方法，可能变得过于谨慎。"
        ),
        when_to_save=(
            "用户纠正方法（'不要那样'、'停止做X'）或确认非显而易见方法有效时。"
            "纠正容易注意到；确认更安静——注意观察。"
            "包含原因以便后续判断边缘情况。"
        ),
        how_to_use="让这些记忆指导行为，使用户无需重复提供相同指导。",
        body_structure="以规则本身开头，然后**原因：**行（用户给出的理由），然后**如何应用：**行（何时/何地适用）",
        examples=[
            (
                "这些测试不要mock数据库——上次mock测试通过了但生产迁移失败了",
                "保存反馈记忆：集成测试必须使用真实数据库，不要mock。原因：之前mock/生产不一致掩盖了迁移问题",
            ),
            (
                "别在每次响应后总结你做了什么，我能看diff",
                "保存反馈记忆：用户需要简洁响应，不需要尾部总结",
            ),
        ],
    ),
    MemoryCategory.PROJECT: MemoryTypeSpec(
        name="project",
        description=(
            "关于项目中的进行中工作、目标、计划、缺陷或事件的信息，"
            "这些信息不能从代码或git历史推导。"
            "项目记忆帮助理解用户请求背后的更广泛上下文和动机。"
        ),
        when_to_save=(
            "当了解到谁在做什么、为什么、何时完成时。"
            "这些状态变化较快，保持更新。"
            "保存时将相对日期转换为绝对日期（如'周四'→'2026-03-05'）。"
        ),
        how_to_use="使用这些记忆更充分理解用户请求的细节和细微差别，做出更明智的建议。",
        body_structure="以事实或决策开头，然后**原因：**行（动机），然后**如何应用：**行（如何影响建议）",
        examples=[
            (
                "周四后冻结所有非关键合并——移动团队正在切发布分支",
                "保存项目记忆：合并冻结从2026-03-05开始，为移动发布切分支。标记该日期后的非关键PR工作",
            ),
        ],
    ),
    MemoryCategory.REFERENCE: MemoryTypeSpec(
        name="reference",
        description=(
            "存储外部系统中信息位置的指针。"
            "这些记忆使系统能记住在项目目录之外哪里可以找到最新信息。"
        ),
        when_to_save="当了解到外部系统中的资源及其用途时。",
        how_to_use="当用户引用外部系统或信息可能在外部系统中时。",
        examples=[
            (
                "查看Linear项目'INGEST'获取这些工单的上下文",
                "保存引用记忆：管道缺陷在Linear项目'INGEST'中追踪",
            ),
        ],
    ),
}


DERIVABLE_PATTERNS = [
    re.compile(r'(代码模式|架构|文件路径|项目结构)', re.IGNORECASE),
    re.compile(r'(git\s*(历史|记录|变更|log|blame))', re.IGNORECASE),
    re.compile(r'(调试方案|修复方案|fix|debug\s*solution)', re.IGNORECASE),
    re.compile(r'(CLAUDE\.md|README|文档中已有)', re.IGNORECASE),
    re.compile(r'(临时任务|进行中工作|当前对话)', re.IGNORECASE),
    re.compile(r'(代码约定|命名规范|目录结构)', re.IGNORECASE),
]

DERIVABLE_EXPLANATIONS = {
    0: "代码模式、架构、文件路径和项目结构可通过阅读当前项目状态推导",
    1: "Git历史、最近变更可通过 git log / git blame 获取",
    2: "调试方案和修复已在代码中，提交消息包含上下文",
    3: "已在文档中记录的内容不需要重复保存",
    4: "临时任务细节和进行中工作属于瞬时状态",
    5: "代码约定和命名规范可从代码推导",
}


@dataclass
class MemorySaveDecision:
    should_save: bool
    category: Optional[MemoryCategory]
    reason: str
    derivable_issue: Optional[str] = None
    suggested_content: Optional[str] = None


class MemoryClassifier:
    """
    记忆分类器，决定信息是否应保存为记忆以及如何分类。

    核心逻辑：
    1. 检查是否为可推导信息（不应保存）
    2. 基于内容特征分类到四种类型
    3. 生成结构化的保存建议
    """

    _USER_KEYWORDS = [
        "我是", "我的角色", "我负责", "我的专长", "我偏好", "我习惯",
        "我擅长", "我不熟悉", "我的经验", "我使用", "我的背景",
        "我从事", "我的工作", "我是新", "我第一次",
    ]
    _FEEDBACK_KEYWORDS = [
        "不要", "别", "停止", "避免", "不要做", "不要那样",
        "继续", "保持", "很好", "完美", "正确", "就是这样",
        "不对", "错了", "应该", "不应该", "必须", "禁止",
    ]
    _PROJECT_KEYWORDS = [
        "项目", "计划", "截止", "冻结", "发布", "迁移",
        "重构", "团队", "里程碑", "sprint", "版本", "上线",
        "合规", "法律", "安全审查", "变更",
    ]
    _REFERENCE_KEYWORDS = [
        "查看", "参考", "追踪", "监控", "看板", "仪表盘",
        "slack", "jira", "linear", "grafana", "文档在",
        "记录在", "配置在", "wiki",
    ]

    def classify(self, content: str, context: str = "") -> MemorySaveDecision:
        """
        分类内容，决定是否保存以及如何分类。

        Args:
            content: 待分类的内容
            context: 额外上下文（如对话历史）

        Returns:
            MemorySaveDecision 包含保存决策和分类结果
        """
        derivable_issue = self._check_derivable(content)
        if derivable_issue:
            return MemorySaveDecision(
                should_save=False,
                category=None,
                reason="信息可从当前状态推导，不需要保存为记忆",
                derivable_issue=derivable_issue,
            )

        category = self._classify_category(content, context)
        suggested = self._generate_suggestion(content, category)

        return MemorySaveDecision(
            should_save=True,
            category=category,
            reason=f"信息属于{category.value}类型记忆，值得保存",
            suggested_content=suggested,
        )

    def _check_derivable(self, content: str) -> Optional[str]:
        """检查内容是否为可推导信息"""
        for i, pattern in enumerate(DERIVABLE_PATTERNS):
            if pattern.search(content):
                return DERIVABLE_EXPLANATIONS.get(i, "信息可从当前状态推导")
        return None

    def _classify_category(self, content: str, context: str) -> MemoryCategory:
        """基于关键词和上下文分类"""
        combined = f"{content} {context}".lower()
        scores: Dict[MemoryCategory, float] = {cat: 0.0 for cat in MEMORY_TYPES}

        for kw in self._USER_KEYWORDS:
            if kw in combined:
                scores[MemoryCategory.USER] += 2.0

        for kw in self._FEEDBACK_KEYWORDS:
            if kw in combined:
                scores[MemoryCategory.FEEDBACK] += 2.0

        for kw in self._PROJECT_KEYWORDS:
            if kw in combined:
                scores[MemoryCategory.PROJECT] += 2.0

        for kw in self._REFERENCE_KEYWORDS:
            if kw in combined:
                scores[MemoryCategory.REFERENCE] += 2.0

        if any(kw in combined for kw in ["我", "我的"]):
            scores[MemoryCategory.USER] += 1.0

        if any(kw in combined for kw in ["不对", "错了", "不要"]):
            scores[MemoryCategory.FEEDBACK] += 1.5

        if any(kw in combined for kw in ["团队", "项目", "发布"]):
            scores[MemoryCategory.PROJECT] += 1.0

        if not any(scores.values()):
            return MemoryCategory.PROJECT

        return max(scores, key=lambda k: scores[k])

    def _generate_suggestion(self, content: str, category: MemoryCategory) -> str:
        """生成结构化的保存建议"""
        spec = MEMORY_TYPE_SPECS[category]

        if category == MemoryCategory.FEEDBACK:
            return f"{content}\n**原因：** [请补充原因]\n**如何应用：** [请补充适用场景]"
        elif category == MemoryCategory.PROJECT:
            return f"{content}\n**原因：** [请补充动机]\n**如何应用：** [请补充影响范围]"
        else:
            return content

    def get_type_spec(self, category: MemoryCategory) -> MemoryTypeSpec:
        """获取类型规范"""
        return MEMORY_TYPE_SPECS[category]

    def parse_category(self, raw: str) -> Optional[MemoryCategory]:
        """解析类型字符串"""
        try:
            return MemoryCategory(raw.lower())
        except ValueError:
            return None


@dataclass
class MemoryEntry:
    """结构化记忆条目"""
    name: str
    description: str
    category: MemoryCategory
    content: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "content": self.content,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_frontmatter(self) -> str:
        """生成frontmatter格式的记忆文件"""
        return (
            f"---\n"
            f"name: {self.name}\n"
            f"description: {self.description}\n"
            f"type: {self.category.value}\n"
            f"---\n\n"
            f"{self.content}"
        )

    @classmethod
    def from_dict(cls, data: dict) -> 'MemoryEntry':
        return cls(
            name=data["name"],
            description=data["description"],
            category=MemoryCategory(data["category"]),
            content=data["content"],
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )


class MemoryTaxonomyEngine:
    """
    记忆分类引擎，整合分类器与存储。

    提供：
    - 智能分类（自动判断是否保存及类型）
    - 结构化模板生成
    - 不保存规则执行
    - 记忆新鲜度追踪
    """

    def __init__(self):
        self._classifier = MemoryClassifier()
        self._entries: Dict[str, MemoryEntry] = {}
        self._stats = {
            "classified": 0,
            "saved": 0,
            "rejected_derivable": 0,
            "by_category": {cat.value: 0 for cat in MEMORY_TYPES},
        }

    def evaluate(self, content: str, context: str = "") -> MemorySaveDecision:
        """评估内容是否应保存为记忆"""
        self._stats["classified"] += 1
        decision = self._classifier.classify(content, context)

        if decision.should_save:
            self._stats["saved"] += 1
            if decision.category:
                self._stats["by_category"][decision.category.value] += 1
        else:
            if decision.derivable_issue:
                self._stats["rejected_derivable"] += 1

        return decision

    def save(self, name: str, description: str, category: MemoryCategory,
             content: str) -> MemoryEntry:
        """保存记忆条目"""
        entry = MemoryEntry(
            name=name,
            description=description,
            category=category,
            content=content,
        )
        self._entries[name] = entry
        return entry

    def get(self, name: str) -> Optional[MemoryEntry]:
        """获取记忆条目"""
        return self._entries.get(name)

    def search(self, query: str, category: Optional[MemoryCategory] = None) -> List[MemoryEntry]:
        """搜索记忆"""
        results = []
        query_lower = query.lower()
        for entry in self._entries.values():
            if category and entry.category != category:
                continue
            if (query_lower in entry.name.lower() or
                    query_lower in entry.description.lower() or
                    query_lower in entry.content.lower()):
                results.append(entry)
        return results

    def list_by_category(self, category: MemoryCategory) -> List[MemoryEntry]:
        """按类型列出记忆"""
        return [e for e in self._entries.values() if e.category == category]

    def delete(self, name: str) -> bool:
        """删除记忆"""
        if name in self._entries:
            del self._entries[name]
            return True
        return False

    def get_type_spec(self, category: MemoryCategory) -> MemoryTypeSpec:
        """获取类型规范"""
        return self._classifier.get_type_spec(category)

    def get_all_type_specs(self) -> Dict[MemoryCategory, MemoryTypeSpec]:
        """获取所有类型规范"""
        return MEMORY_TYPE_SPECS.copy()

    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            **self._stats,
            "total_entries": len(self._entries),
        }


_taxonomy_engine: Optional[MemoryTaxonomyEngine] = None


def get_memory_taxonomy() -> MemoryTaxonomyEngine:
    """获取记忆分类引擎单例"""
    global _taxonomy_engine
    if _taxonomy_engine is None:
        _taxonomy_engine = MemoryTaxonomyEngine()
    return _taxonomy_engine
