# -*- coding: utf-8 -*-
"""
工作记忆区 (Working Memory)
专门用于存储和管理与客户的所有交互记录

核心功能:
- 交互记录存储 (时间戳/对话内容/客户需求/系统响应/跟进事项)
- 经验提取与规则转化 (从交互数据中提取可复用规则)
- 快速检索 (关键词/标签/时间范围/客户ID)
- 自动分类 (主题/情感/紧急度/状态)
- 数据持久化 (SQLite + JSON备份)
- 定期备份 (增量备份 + 全量备份)
"""

import json
import os
import re
import math
import uuid
import sqlite3
import logging
import threading
import shutil
import hashlib
import time
import random
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("WorkingMemory")


class InteractionCategory(Enum):
    """交互分类"""
    CONSULTATION = "consultation"
    COMPLAINT = "complaint"
    TECHNICAL_SUPPORT = "technical_support"
    SERVICE_REQUEST = "service_request"
    FEEDBACK = "feedback"
    INQUIRY = "inquiry"
    COMPLAINT_RESOLVE = "complaint_resolve"
    FOLLOW_UP = "follow_up"
    GENERAL = "general"


class InteractionSentiment(Enum):
    """交互情感"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    URGENT = "urgent"
    FRUSTRATED = "frustrated"
    SATISFIED = "satisfied"


class InteractionStatus(Enum):
    """交互状态"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"


class RuleType(Enum):
    """规则类型"""
    RESPONSE_PATTERN = "response_pattern"
    RESOLUTION_STRATEGY = "resolution_strategy"
    ESCALATION_CONDITION = "escalation_condition"
    CLASSIFICATION_RULE = "classification_rule"
    SENTIMENT_RULE = "sentiment_rule"
    FOLLOW_UP_RULE = "follow_up_rule"


class RuleStatus(Enum):
    """规则状态"""
    DRAFT = "draft"
    VALIDATING = "validating"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


@dataclass
class FollowUpItem:
    """跟进事项"""
    item_id: str
    description: str
    assignee: str = ""
    due_date: str = ""
    priority: int = 2
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "description": self.description,
            "assignee": self.assignee,
            "due_date": self.due_date,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }


@dataclass
class InteractionRecord:
    """交互记录"""
    record_id: str
    timestamp: str
    customer_id: str
    session_id: str
    dialogue_content: str
    customer_needs: str
    system_response: str
    follow_ups: List[FollowUpItem] = field(default_factory=list)
    category: InteractionCategory = InteractionCategory.GENERAL
    sentiment: InteractionSentiment = InteractionSentiment.NEUTRAL
    status: InteractionStatus = InteractionStatus.OPEN
    tags: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    resolution_time_ms: float = 0.0
    satisfaction_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp,
            "customer_id": self.customer_id,
            "session_id": self.session_id,
            "dialogue_content": self.dialogue_content,
            "customer_needs": self.customer_needs,
            "system_response": self.system_response,
            "follow_ups": [fu.to_dict() for fu in self.follow_ups],
            "category": self.category.value,
            "sentiment": self.sentiment.value,
            "status": self.status.value,
            "tags": self.tags,
            "keywords": self.keywords,
            "resolution_time_ms": self.resolution_time_ms,
            "satisfaction_score": self.satisfaction_score,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


@dataclass
class ExperienceRule:
    """经验规则"""
    rule_id: str
    rule_type: RuleType
    name: str
    description: str
    conditions: List[str]
    actions: List[str]
    confidence: float = 0.0
    support_count: int = 0
    apply_count: int = 0
    success_count: int = 0
    source_records: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    status: RuleStatus = RuleStatus.DRAFT
    priority: int = 2
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        total = self.success_count + (self.apply_count - self.success_count)
        return self.success_count / max(total, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_type": self.rule_type.value,
            "name": self.name,
            "description": self.description,
            "conditions": self.conditions,
            "actions": self.actions,
            "confidence": round(self.confidence, 3),
            "support_count": self.support_count,
            "apply_count": self.apply_count,
            "success_count": self.success_count,
            "success_rate": round(self.success_rate, 3),
            "source_records": self.source_records,
            "tags": self.tags,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata
        }


class InteractionClassifier:
    """交互自动分类器"""

    CATEGORY_KEYWORDS: Dict[InteractionCategory, List[str]] = {
        InteractionCategory.CONSULTATION: [
            "咨询", "了解", "请问", "想知道", "如何", "怎么", "能否", "是否"
        ],
        InteractionCategory.COMPLAINT: [
            "投诉", "不满", "差", "太差", "糟糕", "退款", "赔偿", "欺骗", "虚假"
        ],
        InteractionCategory.TECHNICAL_SUPPORT: [
            "故障", "报错", "无法", "崩溃", "卡顿", "出错", "异常", "bug", "错误"
        ],
        InteractionCategory.SERVICE_REQUEST: [
            "申请", "开通", "办理", "预约", "变更", "升级", "续费", "订购"
        ],
        InteractionCategory.FEEDBACK: [
            "建议", "反馈", "希望", "改进", "优化", "体验", "感受", "评价"
        ],
        InteractionCategory.INQUIRY: [
            "查询", "进度", "状态", "结果", "账单", "明细", "记录"
        ],
        InteractionCategory.COMPLAINT_RESOLVE: [
            "解决", "处理", "满意", "感谢", "好了", "修好", "正常"
        ],
        InteractionCategory.FOLLOW_UP: [
            "跟进", "回访", "确认", "提醒", "后续", "再来", "继续"
        ]
    }

    SENTIMENT_KEYWORDS: Dict[InteractionSentiment, List[str]] = {
        InteractionSentiment.POSITIVE: [
            "好", "棒", "满意", "感谢", "不错", "喜欢", "优秀", "赞"
        ],
        InteractionSentiment.NEGATIVE: [
            "差", "不满", "失望", "愤怒", "讨厌", "垃圾", "骗人", "坑"
        ],
        InteractionSentiment.URGENT: [
            "急", "紧急", "马上", "立刻", "赶紧", "尽快", "加急", "十万火急"
        ],
        InteractionSentiment.FRUSTRATED: [
            "烦", "受不了", "无语", "崩溃", "多次", "反复", "一直", "总是"
        ],
        InteractionSentiment.SATISFIED: [
            "解决", "好了", "谢谢", "满意", "可以了", "没问题了", "辛苦"
        ]
    }

    @classmethod
    def classify_category(cls, text: str) -> InteractionCategory:
        scores: Dict[InteractionCategory, float] = {}
        text_lower = text.lower()
        for cat, keywords in cls.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            scores[cat] = score
        if not scores or max(scores.values()) == 0:
            return InteractionCategory.GENERAL
        return max(scores, key=scores.get)

    @classmethod
    def classify_sentiment(cls, text: str) -> InteractionSentiment:
        scores: Dict[InteractionSentiment, float] = {}
        text_lower = text.lower()
        for sent, keywords in cls.SENTIMENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            scores[sent] = score
        if not scores or max(scores.values()) == 0:
            return InteractionSentiment.NEUTRAL
        return max(scores, key=scores.get)

    @classmethod
    def extract_keywords(cls, text: str, max_keywords: int = 8) -> List[str]:
        stop_words = {
            "的", "了", "是", "在", "我", "有", "和", "就", "不", "人",
            "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
            "你", "会", "着", "没有", "看", "好", "自己", "这", "他", "她",
            "它", "吗", "吧", "啊", "呢", "哦", "嗯", "那", "什么", "怎么",
            "如何", "可以", "能", "请", "谢谢", "多", "少", "些", "这个",
            "那个", "但是", "因为", "所以", "如果", "虽然", "而且", "或者",
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "can", "shall", "to", "of",
            "in", "for", "on", "with", "at", "by", "from", "as", "into"
        }
        words = re.findall(r'[\u4e00-\u9fff]{2,4}|[a-zA-Z]{2,}', text)
        word_freq = Counter(w for w in words if w.lower() not in stop_words)
        return [w for w, _ in word_freq.most_common(max_keywords)]


class ExperienceExtractor:
    """经验提取器 - 从交互记录中提取可复用的经验和规则"""

    def __init__(self, min_support: int = 3, min_confidence: float = 0.6):
        self._min_support = min_support
        self._min_confidence = min_confidence

    def extract_response_patterns(
        self, records: List[InteractionRecord]
    ) -> List[ExperienceRule]:
        if len(records) < self._min_support:
            return []

        pattern_map: Dict[str, List[str]] = defaultdict(list)
        need_response_pairs: Dict[str, Tuple[List[str], str]] = {}

        for record in records:
            if record.status != InteractionStatus.RESOLVED:
                continue
            need_key = self._normalize_text(record.customer_needs)
            if not need_key:
                continue
            pattern_map[need_key].append(record.record_id)
            need_response_pairs[record.record_id] = (
                self._extract_need_keywords(record.customer_needs),
                record.system_response
            )

        rules = []
        for need_key, record_ids in pattern_map.items():
            if len(record_ids) < self._min_support:
                continue

            pairs = [need_response_pairs[rid] for rid in record_ids if rid in need_response_pairs]
            if not pairs:
                continue

            response_clusters = self._cluster_responses(pairs)
            for cluster_keywords, cluster_responses, cluster_records in response_clusters:
                if len(cluster_records) < self._min_support:
                    continue
                confidence = len(cluster_records) / len(record_ids)
                if confidence < self._min_confidence:
                    continue

                rule = ExperienceRule(
                    rule_id="rule_" + uuid.uuid4().hex[:12],
                    rule_type=RuleType.RESPONSE_PATTERN,
                    name="响应模式_" + need_key[:20],
                    description="当客户需求包含[" + ",".join(cluster_keywords[:5]) + "]时，推荐使用特定响应模式",
                    conditions=cluster_keywords[:5],
                    actions=[r[:100] for r in cluster_responses[:3]],
                    confidence=confidence,
                    support_count=len(cluster_records),
                    source_records=cluster_records,
                    status=RuleStatus.VALIDATING
                )
                rules.append(rule)

        return rules

    def extract_resolution_strategies(
        self, records: List[InteractionRecord]
    ) -> List[ExperienceRule]:
        resolved = [r for r in records if r.status == InteractionStatus.RESOLVED]
        if len(resolved) < self._min_support:
            return []

        category_strategies: Dict[InteractionCategory, List[InteractionRecord]] = defaultdict(list)
        for record in resolved:
            category_strategies[record.category].append(record)

        rules = []
        for category, cat_records in category_strategies.items():
            if len(cat_records) < self._min_support:
                continue

            avg_time = sum(r.resolution_time_ms for r in cat_records) / len(cat_records)
            avg_satisfaction = sum(r.satisfaction_score for r in cat_records if r.satisfaction_score > 0) / max(
                sum(1 for r in cat_records if r.satisfaction_score > 0), 1
            )

            fast_records = [r for r in cat_records if r.resolution_time_ms > 0 and r.resolution_time_ms < avg_time]
            if not fast_records:
                fast_records = cat_records[:self._min_support]

            common_keywords: Set[str] = set()
            for r in fast_records:
                common_keywords.update(r.keywords)

            rule = ExperienceRule(
                rule_id="rule_" + uuid.uuid4().hex[:12],
                rule_type=RuleType.RESOLUTION_STRATEGY,
                name="解决策略_" + category.value,
                description="针对[" + category.value + "]类交互，平均解决时间" + str(round(avg_time)) + "ms，满意度" + str(round(avg_satisfaction, 2)),
                conditions=["category==" + category.value],
                actions=[r.system_response[:100] for r in fast_records[:3]],
                confidence=min(avg_satisfaction / 5.0, 1.0) if avg_satisfaction > 0 else 0.5,
                support_count=len(cat_records),
                source_records=[r.record_id for r in fast_records],
                tags=list(common_keywords)[:10],
                status=RuleStatus.VALIDATING
            )
            rules.append(rule)

        return rules

    def extract_escalation_conditions(
        self, records: List[InteractionRecord]
    ) -> List[ExperienceRule]:
        escalated = [r for r in records if r.status == InteractionStatus.ESCALATED]
        if len(escalated) < 2:
            return []

        escalation_signals: Dict[str, int] = Counter()
        for record in escalated:
            for kw in record.keywords:
                escalation_signals[kw] += 1
            if record.sentiment in (InteractionSentiment.NEGATIVE, InteractionSentiment.FRUSTRATED):
                escalation_signals["sentiment==" + record.sentiment.value] += 1
            if record.follow_ups and len(record.follow_ups) > 2:
                escalation_signals["multiple_follow_ups"] += 1

        significant_signals = {
            k: v for k, v in escalation_signals.items()
            if v >= max(2, len(escalated) * 0.3)
        }

        if not significant_signals:
            return []

        rule = ExperienceRule(
            rule_id="rule_" + uuid.uuid4().hex[:12],
            rule_type=RuleType.ESCALATION_CONDITION,
            name="升级条件_自动检测",
            description="当交互中出现[" + ",".join(list(significant_signals.keys())[:5]) + "]信号时，建议升级处理",
            conditions=list(significant_signals.keys())[:8],
            actions=["escalate_to_human", "priority_boost", "supervisor_notify"],
            confidence=min(sum(significant_signals.values()) / (len(escalated) * 5), 1.0),
            support_count=len(escalated),
            source_records=[r.record_id for r in escalated],
            status=RuleStatus.VALIDATING
        )
        return [rule]

    def _normalize_text(self, text: str) -> str:
        text = re.sub(r'[^\u4e00-\u9fff\w\s]', '', text)
        return text.strip().lower()[:100]

    def _extract_need_keywords(self, text: str) -> List[str]:
        return InteractionClassifier.extract_keywords(text, max_keywords=5)

    def _cluster_responses(
        self, pairs: List[Tuple[List[str], str]]
    ) -> List[Tuple[List[str], List[str], List[str]]]:
        clusters: Dict[str, Tuple[List[str], List[str], List[str]]] = {}
        for keywords, response in pairs:
            key = "|".join(sorted(keywords[:3]))
            if key not in clusters:
                clusters[key] = ([], [], [])
            cluster_kw, cluster_resp, cluster_ids = clusters[key]
            cluster_kw.extend(keywords)
            cluster_resp.append(response)

        result = []
        for key, (kws, resps, _) in clusters.items():
            kw_counter = Counter(kws)
            top_kws = [k for k, _ in kw_counter.most_common(8)]
            result.append((top_kws, resps, []))

        return result


class WorkingMemoryStorage:
    """
    工作记忆持久化存储 - SQLite + FTS5 + JSON备份
    
    优化特性（源自Hermes Agent架构分析）:
    - FTS5全文检索虚拟表 + 自动同步触发器
    - 应用层写竞争重试 + 随机抖动（消除convoy效应）
    - Schema版本化迁移（幂等ALTER TABLE）
    - BEGIN IMMEDIATE事务（提前暴露锁竞争）
    - WAL检查点定期执行
    """

    _WRITE_MAX_RETRIES = 15
    _WRITE_RETRY_MIN_S = 0.020
    _WRITE_RETRY_MAX_S = 0.150
    _CHECKPOINT_EVERY_N_WRITES = 50
    _SCHEMA_VERSION = 2

    def __init__(self, db_path: str = "./data/working_memory/working_memory.db",
                 backup_dir: str = "./data/working_memory/backups"):
        self.db_path = db_path
        self.backup_dir = backup_dir
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        os.makedirs(backup_dir, exist_ok=True)
        self._local = threading.local()
        self._write_lock = threading.Lock()
        self._write_count = 0
        self._initialize()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path, check_same_thread=False, timeout=1.0
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA cache_size=-32000")
            self._local.conn.execute("PRAGMA busy_timeout=1000")
            self._local.conn.execute("PRAGMA temp_store=MEMORY")
        return self._local.conn

    def _write_with_retry(self, operation):
        for attempt in range(self._WRITE_MAX_RETRIES):
            try:
                conn = self._get_conn()
                conn.execute("BEGIN IMMEDIATE")
                result = operation(conn)
                conn.commit()
                self._write_count += 1
                if self._write_count % self._CHECKPOINT_EVERY_N_WRITES == 0:
                    try:
                        conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
                    except Exception:
                        pass
                return result
            except sqlite3.OperationalError as e:
                try:
                    conn = self._get_conn()
                    conn.rollback()
                except Exception:
                    pass
                if "locked" in str(e).lower() or "busy" in str(e).lower():
                    if attempt < self._WRITE_MAX_RETRIES - 1:
                        jitter = random.uniform(self._WRITE_RETRY_MIN_S, self._WRITE_RETRY_MAX_S)
                        time.sleep(jitter)
                        continue
                raise
            except Exception as e:
                try:
                    conn = self._get_conn()
                    conn.rollback()
                except Exception:
                    pass
                raise

    def _get_schema_version(self, conn) -> int:
        try:
            row = conn.execute(
                "SELECT version FROM schema_version LIMIT 1"
            ).fetchone()
            return row["version"] if row else 0
        except sqlite3.OperationalError:
            return 0

    def _set_schema_version(self, conn, version: int):
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"
        )
        conn.execute("DELETE FROM schema_version")
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))

    def _run_migrations(self, conn):
        current_version = self._get_schema_version(conn)

        if current_version < 1:
            logger.info("执行Schema迁移 v1: FTS5全文检索 + 触发器")
            try:
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS interaction_records_fts USING fts5(
                        dialogue_content,
                        customer_needs,
                        system_response,
                        content=interaction_records,
                        content_rowid=rowid,
                        tokenize="unicode61"
                    )
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS records_fts_insert
                    AFTER INSERT ON interaction_records BEGIN
                        INSERT INTO interaction_records_fts(rowid, dialogue_content, customer_needs, system_response)
                        VALUES (new.rowid, new.dialogue_content, new.customer_needs, new.system_response);
                    END
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS records_fts_delete
                    AFTER DELETE ON interaction_records BEGIN
                        INSERT INTO interaction_records_fts(interaction_records_fts, rowid, dialogue_content, customer_needs, system_response)
                        VALUES('delete', old.rowid, old.dialogue_content, old.customer_needs, old.system_response);
                    END
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS records_fts_update
                    AFTER UPDATE ON interaction_records BEGIN
                        INSERT INTO interaction_records_fts(interaction_records_fts, rowid, dialogue_content, customer_needs, system_response)
                        VALUES('delete', old.rowid, old.dialogue_content, old.customer_needs, old.system_response);
                        INSERT INTO interaction_records_fts(rowid, dialogue_content, customer_needs, system_response)
                        VALUES (new.rowid, new.dialogue_content, new.customer_needs, new.system_response);
                    END
                """)
            except sqlite3.OperationalError as e:
                logger.warning("FTS5迁移警告(可能已存在): %s", e)

            try:
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS experience_rules_fts USING fts5(
                        name,
                        description,
                        content=experience_rules,
                        content_rowid=rowid,
                        tokenize="unicode61"
                    )
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS rules_fts_insert
                    AFTER INSERT ON experience_rules BEGIN
                        INSERT INTO experience_rules_fts(rowid, name, description)
                        VALUES (new.rowid, new.name, new.description);
                    END
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS rules_fts_delete
                    AFTER DELETE ON experience_rules BEGIN
                        INSERT INTO experience_rules_fts(experience_rules_fts, rowid, name, description)
                        VALUES('delete', old.rowid, old.name, old.description);
                    END
                """)
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS rules_fts_update
                    AFTER UPDATE ON experience_rules BEGIN
                        INSERT INTO experience_rules_fts(experience_rules_fts, rowid, name, description)
                        VALUES('delete', old.rowid, old.name, old.description);
                        INSERT INTO experience_rules_fts(rowid, name, description)
                        VALUES (new.rowid, new.name, new.description);
                    END
                """)
            except sqlite3.OperationalError as e:
                logger.warning("规则FTS5迁移警告: %s", e)

            self._set_schema_version(conn, 1)
            current_version = 1

        if current_version < 2:
            logger.info("执行Schema迁移 v2: 会话世系追踪字段")
            migrations_v2 = [
                "ALTER TABLE interaction_records ADD COLUMN parent_session_id TEXT DEFAULT ''",
                "ALTER TABLE interaction_records ADD COLUMN compression_count INTEGER DEFAULT 0",
                "ALTER TABLE interaction_records ADD COLUMN token_count INTEGER DEFAULT 0",
            ]
            for sql in migrations_v2:
                try:
                    conn.execute(sql)
                except sqlite3.OperationalError:
                    pass
            self._set_schema_version(conn, 2)
            current_version = 2

    def _initialize(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS interaction_records (
                record_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                dialogue_content TEXT NOT NULL,
                customer_needs TEXT NOT NULL,
                system_response TEXT NOT NULL,
                follow_ups TEXT DEFAULT '[]',
                category TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                status TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                keywords TEXT DEFAULT '[]',
                resolution_time_ms REAL DEFAULT 0.0,
                satisfaction_score REAL DEFAULT 0.0,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS experience_rules (
                rule_id TEXT PRIMARY KEY,
                rule_type TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                conditions TEXT DEFAULT '[]',
                actions TEXT DEFAULT '[]',
                confidence REAL DEFAULT 0.0,
                support_count INTEGER DEFAULT 0,
                apply_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                source_records TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',
                status TEXT NOT NULL,
                priority INTEGER DEFAULT 2,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_records_timestamp ON interaction_records(timestamp);
            CREATE INDEX IF NOT EXISTS idx_records_customer ON interaction_records(customer_id);
            CREATE INDEX IF NOT EXISTS idx_records_session ON interaction_records(session_id);
            CREATE INDEX IF NOT EXISTS idx_records_category ON interaction_records(category);
            CREATE INDEX IF NOT EXISTS idx_records_sentiment ON interaction_records(sentiment);
            CREATE INDEX IF NOT EXISTS idx_records_status ON interaction_records(status);
            CREATE INDEX IF NOT EXISTS idx_rules_type ON experience_rules(rule_type);
            CREATE INDEX IF NOT EXISTS idx_rules_status ON experience_rules(status);
            CREATE INDEX IF NOT EXISTS idx_rules_confidence ON experience_rules(confidence);
        """)
        conn.commit()
        self._run_migrations(conn)
        conn.commit()

    def _rebuild_fts_index(self):
        conn = self._get_conn()
        try:
            conn.execute("INSERT INTO interaction_records_fts(interaction_records_fts) VALUES('rebuild')")
            conn.execute("INSERT INTO experience_rules_fts(experience_rules_fts) VALUES('rebuild')")
            conn.commit()
            logger.info("FTS5索引重建完成")
        except Exception as e:
            logger.warning("FTS5索引重建失败(可能不支持): %s", e)

    def store_record(self, record: InteractionRecord) -> bool:
        def _operation(conn):
            conn.execute("""
                INSERT OR REPLACE INTO interaction_records
                (record_id, timestamp, customer_id, session_id,
                 dialogue_content, customer_needs, system_response, follow_ups,
                 category, sentiment, status, tags, keywords,
                 resolution_time_ms, satisfaction_score, metadata,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.record_id, record.timestamp, record.customer_id,
                record.session_id, record.dialogue_content, record.customer_needs,
                record.system_response,
                json.dumps([fu.to_dict() for fu in record.follow_ups], ensure_ascii=False),
                record.category.value, record.sentiment.value, record.status.value,
                json.dumps(record.tags, ensure_ascii=False),
                json.dumps(record.keywords, ensure_ascii=False),
                record.resolution_time_ms, record.satisfaction_score,
                json.dumps(record.metadata, ensure_ascii=False),
                record.created_at, record.updated_at
            ))
            return True

        try:
            return self._write_with_retry(_operation)
        except Exception as e:
            logger.error("交互记录存储失败: %s", e)
            return False

    def retrieve_record(self, record_id: str) -> Optional[InteractionRecord]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM interaction_records WHERE record_id = ?", (record_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_record(row)
        except Exception as e:
            logger.error("交互记录检索失败: %s", e)
            return None

    def search_records(self, query: str = None, customer_id: str = None,
                       category: str = None, sentiment: str = None,
                       status: str = None, start_time: str = None,
                       end_time: str = None, tags: List[str] = None,
                       limit: int = 20, offset: int = 0,
                       use_fts: bool = True) -> List[InteractionRecord]:
        conn = self._get_conn()
        try:
            if query and use_fts:
                return self._search_records_fts(
                    conn, query, customer_id, category, sentiment,
                    status, start_time, end_time, tags, limit, offset
                )

            conditions = []
            params: list = []

            if query:
                conditions.append("(dialogue_content LIKE ? OR customer_needs LIKE ? OR system_response LIKE ?)")
                params.extend(["%" + query + "%"] * 3)
            if customer_id:
                conditions.append("customer_id = ?")
                params.append(customer_id)
            if category:
                conditions.append("category = ?")
                params.append(category)
            if sentiment:
                conditions.append("sentiment = ?")
                params.append(sentiment)
            if status:
                conditions.append("status = ?")
                params.append(status)
            if start_time:
                conditions.append("timestamp >= ?")
                params.append(start_time)
            if end_time:
                conditions.append("timestamp <= ?")
                params.append(end_time)
            if tags:
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append("tags LIKE ?")
                    params.append("%" + tag + "%")
                conditions.append("(" + " OR ".join(tag_conditions) + ")")

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            sql = "SELECT * FROM interaction_records WHERE " + where_clause + " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_record(r) for r in rows]
        except Exception as e:
            logger.error("交互记录搜索失败: %s", e)
            return []

    def _search_records_fts(self, conn, query: str, customer_id: str = None,
                            category: str = None, sentiment: str = None,
                            status: str = None, start_time: str = None,
                            end_time: str = None, tags: List[str] = None,
                            limit: int = 20, offset: int = 0) -> List[InteractionRecord]:
        sanitized_query = self._sanitize_fts_query(query)
        if not sanitized_query:
            return self.search_records(
                query=None, customer_id=customer_id, category=category,
                sentiment=sentiment, status=status, start_time=start_time,
                end_time=end_time, tags=tags, limit=limit, offset=offset,
                use_fts=False
            )

        conditions = []
        params: list = []

        if customer_id:
            conditions.append("r.customer_id = ?")
            params.append(customer_id)
        if category:
            conditions.append("r.category = ?")
            params.append(category)
        if sentiment:
            conditions.append("r.sentiment = ?")
            params.append(sentiment)
        if status:
            conditions.append("r.status = ?")
            params.append(status)
        if start_time:
            conditions.append("r.timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("r.timestamp <= ?")
            params.append(end_time)

        where_extra = ""
        if conditions:
            where_extra = " AND " + " AND ".join(conditions)

        try:
            sql = """
                SELECT r.*, fts.rank as fts_rank
                FROM interaction_records_fts fts
                JOIN interaction_records r ON r.rowid = fts.rowid
                WHERE interaction_records_fts MATCH ?
            """ + where_extra + """
                ORDER BY fts.rank
                LIMIT ? OFFSET ?
            """
            params = [sanitized_query] + params + [limit, offset]
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_record(r) for r in rows]
        except sqlite3.OperationalError as e:
            logger.warning("FTS5搜索失败，回退到LIKE: %s", e)
            return self.search_records(
                query=query, customer_id=customer_id, category=category,
                sentiment=sentiment, status=status, start_time=start_time,
                end_time=end_time, tags=tags, limit=limit, offset=offset,
                use_fts=False
            )

    def _sanitize_fts_query(self, query: str) -> str:
        if not query or not query.strip():
            return ""
        query = query.strip()
        query = re.sub(r'[^\w\s\u4e00-\u9fff*"]', ' ', query)
        query = re.sub(r'\s+', ' ', query).strip()
        if not query:
            return ""
        words = query.split()
        sanitized = []
        for w in words:
            if w.upper() in ("AND", "OR", "NOT"):
                sanitized.append(w.upper())
            elif re.match(r'^[\u4e00-\u9fff]+$', w):
                sanitized.append(w + "*")
            else:
                sanitized.append(w + "*")
        result = " ".join(sanitized)
        return result if result else ""

    def count_records(self, customer_id: str = None, category: str = None,
                      status: str = None, start_time: str = None,
                      end_time: str = None) -> int:
        conn = self._get_conn()
        try:
            conditions = []
            params: list = []
            if customer_id:
                conditions.append("customer_id = ?")
                params.append(customer_id)
            if category:
                conditions.append("category = ?")
                params.append(category)
            if status:
                conditions.append("status = ?")
                params.append(status)
            if start_time:
                conditions.append("timestamp >= ?")
                params.append(start_time)
            if end_time:
                conditions.append("timestamp <= ?")
                params.append(end_time)

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            result = conn.execute(
                "SELECT COUNT(*) FROM interaction_records WHERE " + where_clause, params
            ).fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error("记录计数失败: %s", e)
            return 0

    def update_record_status(self, record_id: str, status: str,
                             satisfaction_score: float = 0.0,
                             resolution_time_ms: float = 0.0) -> bool:
        def _operation(conn):
            updates = ["status = ?", "updated_at = ?"]
            params: list = [status, datetime.now().isoformat()]
            if satisfaction_score > 0:
                updates.append("satisfaction_score = ?")
                params.append(satisfaction_score)
            if resolution_time_ms > 0:
                updates.append("resolution_time_ms = ?")
                params.append(resolution_time_ms)
            params.append(record_id)
            sql = "UPDATE interaction_records SET " + ", ".join(updates) + " WHERE record_id = ?"
            conn.execute(sql, params)
            return True

        try:
            return self._write_with_retry(_operation)
        except Exception as e:
            logger.error("记录状态更新失败: %s", e)
            return False

    def delete_record(self, record_id: str) -> bool:
        def _operation(conn):
            conn.execute("DELETE FROM interaction_records WHERE record_id = ?", (record_id,))
            return True

        try:
            return self._write_with_retry(_operation)
        except Exception as e:
            logger.error("记录删除失败: %s", e)
            return False

    def store_rule(self, rule: ExperienceRule) -> bool:
        def _operation(conn):
            conn.execute("""
                INSERT OR REPLACE INTO experience_rules
                (rule_id, rule_type, name, description, conditions, actions,
                 confidence, support_count, apply_count, success_count,
                 source_records, tags, status, priority,
                 created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rule.rule_id, rule.rule_type.value, rule.name, rule.description,
                json.dumps(rule.conditions, ensure_ascii=False),
                json.dumps(rule.actions, ensure_ascii=False),
                rule.confidence, rule.support_count, rule.apply_count,
                rule.success_count,
                json.dumps(rule.source_records, ensure_ascii=False),
                json.dumps(rule.tags, ensure_ascii=False),
                rule.status.value, rule.priority,
                rule.created_at, rule.updated_at,
                json.dumps(rule.metadata, ensure_ascii=False)
            ))
            return True

        try:
            return self._write_with_retry(_operation)
        except Exception as e:
            logger.error("经验规则存储失败: %s", e)
            return False

    def retrieve_rule(self, rule_id: str) -> Optional[ExperienceRule]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM experience_rules WHERE rule_id = ?", (rule_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_rule(row)
        except Exception as e:
            logger.error("经验规则检索失败: %s", e)
            return None

    def search_rules(self, rule_type: str = None, status: str = None,
                     min_confidence: float = 0.0, tags: List[str] = None,
                     query: str = None, limit: int = 20) -> List[ExperienceRule]:
        conn = self._get_conn()
        try:
            if query:
                return self._search_rules_fts(
                    conn, query, rule_type, status, min_confidence, tags, limit
                )

            conditions = []
            params: list = []
            if rule_type:
                conditions.append("rule_type = ?")
                params.append(rule_type)
            if status:
                conditions.append("status = ?")
                params.append(status)
            if min_confidence > 0:
                conditions.append("confidence >= ?")
                params.append(min_confidence)
            if tags:
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append("tags LIKE ?")
                    params.append("%" + tag + "%")
                conditions.append("(" + " OR ".join(tag_conditions) + ")")

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            sql = "SELECT * FROM experience_rules WHERE " + where_clause + " ORDER BY confidence DESC, support_count DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_rule(r) for r in rows]
        except Exception as e:
            logger.error("经验规则搜索失败: %s", e)
            return []

    def _search_rules_fts(self, conn, query: str, rule_type: str = None,
                          status: str = None, min_confidence: float = 0.0,
                          tags: List[str] = None, limit: int = 20) -> List[ExperienceRule]:
        sanitized_query = self._sanitize_fts_query(query)
        if not sanitized_query:
            return self.search_rules(
                rule_type=rule_type, status=status,
                min_confidence=min_confidence, tags=tags, limit=limit
            )

        conditions = []
        params: list = []

        if rule_type:
            conditions.append("r.rule_type = ?")
            params.append(rule_type)
        if status:
            conditions.append("r.status = ?")
            params.append(status)
        if min_confidence > 0:
            conditions.append("r.confidence >= ?")
            params.append(min_confidence)

        where_extra = ""
        if conditions:
            where_extra = " AND " + " AND ".join(conditions)

        try:
            sql = """
                SELECT r.*, fts.rank as fts_rank
                FROM experience_rules_fts fts
                JOIN experience_rules r ON r.rowid = fts.rowid
                WHERE experience_rules_fts MATCH ?
            """ + where_extra + """
                ORDER BY fts.rank
                LIMIT ?
            """
            params = [sanitized_query] + params + [limit]
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_rule(r) for r in rows]
        except sqlite3.OperationalError as e:
            logger.warning("规则FTS5搜索失败，回退: %s", e)
            return self.search_rules(
                rule_type=rule_type, status=status,
                min_confidence=min_confidence, tags=tags, limit=limit
            )

    def update_rule_status(self, rule_id: str, status: str) -> bool:
        def _operation(conn):
            conn.execute(
                "UPDATE experience_rules SET status = ?, updated_at = ? WHERE rule_id = ?",
                (status, datetime.now().isoformat(), rule_id)
            )
            return True

        try:
            return self._write_with_retry(_operation)
        except Exception as e:
            logger.error("规则状态更新失败: %s", e)
            return False

    def record_rule_application(self, rule_id: str, success: bool) -> bool:
        def _operation(conn):
            if success:
                conn.execute(
                    "UPDATE experience_rules SET apply_count = apply_count + 1, success_count = success_count + 1, updated_at = ? WHERE rule_id = ?",
                    (datetime.now().isoformat(), rule_id)
                )
            else:
                conn.execute(
                    "UPDATE experience_rules SET apply_count = apply_count + 1, updated_at = ? WHERE rule_id = ?",
                    (datetime.now().isoformat(), rule_id)
                )
            return True

        try:
            return self._write_with_retry(_operation)
        except Exception as e:
            logger.error("规则应用记录失败: %s", e)
            return False

    def delete_rule(self, rule_id: str) -> bool:
        def _operation(conn):
            conn.execute("DELETE FROM experience_rules WHERE rule_id = ?", (rule_id,))
            return True

        try:
            return self._write_with_retry(_operation)
        except Exception as e:
            logger.error("规则删除失败: %s", e)
            return False

    def get_records_for_extraction(self, since: str = None,
                                   limit: int = 1000) -> List[InteractionRecord]:
        conn = self._get_conn()
        try:
            if since:
                rows = conn.execute(
                    "SELECT * FROM interaction_records WHERE created_at >= ? ORDER BY timestamp DESC LIMIT ?",
                    (since, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM interaction_records ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [self._row_to_record(r) for r in rows]
        except Exception as e:
            logger.error("获取提取数据失败: %s", e)
            return []

    def get_statistics(self) -> Dict[str, Any]:
        conn = self._get_conn()
        try:
            total_records = conn.execute("SELECT COUNT(*) FROM interaction_records").fetchone()[0]
            total_rules = conn.execute("SELECT COUNT(*) FROM experience_rules").fetchone()[0]

            by_category = {}
            for row in conn.execute(
                "SELECT category, COUNT(*) as cnt FROM interaction_records GROUP BY category"
            ).fetchall():
                by_category[row["category"]] = row["cnt"]

            by_sentiment = {}
            for row in conn.execute(
                "SELECT sentiment, COUNT(*) as cnt FROM interaction_records GROUP BY sentiment"
            ).fetchall():
                by_sentiment[row["sentiment"]] = row["cnt"]

            by_status = {}
            for row in conn.execute(
                "SELECT status, COUNT(*) as cnt FROM interaction_records GROUP BY status"
            ).fetchall():
                by_status[row["status"]] = row["cnt"]

            by_rule_type = {}
            for row in conn.execute(
                "SELECT rule_type, COUNT(*) as cnt FROM experience_rules GROUP BY rule_type"
            ).fetchall():
                by_rule_type[row["rule_type"]] = row["cnt"]

            avg_satisfaction = conn.execute(
                "SELECT AVG(satisfaction_score) FROM interaction_records WHERE satisfaction_score > 0"
            ).fetchone()[0] or 0.0

            avg_resolution = conn.execute(
                "SELECT AVG(resolution_time_ms) FROM interaction_records WHERE resolution_time_ms > 0"
            ).fetchone()[0] or 0.0

            return {
                "total_records": total_records,
                "total_rules": total_rules,
                "records_by_category": by_category,
                "records_by_sentiment": by_sentiment,
                "records_by_status": by_status,
                "rules_by_type": by_rule_type,
                "avg_satisfaction": round(avg_satisfaction, 2),
                "avg_resolution_time_ms": round(avg_resolution, 2)
            }
        except Exception as e:
            logger.error("统计查询失败: %s", e)
            return {"error": str(e)}

    def create_backup(self, backup_type: str = "full") -> Dict[str, Any]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = "wm_backup_" + backup_type + "_" + timestamp
        backup_path = os.path.join(self.backup_dir, backup_name)
        os.makedirs(backup_path, exist_ok=True)

        try:
            if backup_type == "full":
                db_backup = os.path.join(backup_path, "working_memory.db")
                shutil.copy2(self.db_path, db_backup)
            elif backup_type == "incremental":
                conn = self._get_conn()
                last_backup_file = os.path.join(self.backup_dir, ".last_backup_time")
                since = None
                if os.path.exists(last_backup_file):
                    with open(last_backup_file, "r") as f:
                        since = f.read().strip()

                records = self.get_records_for_extraction(since=since, limit=100000)
                rules = self.search_rules(limit=100000)

                data = {
                    "records": [r.to_dict() for r in records],
                    "rules": [r.to_dict() for r in rules],
                    "backup_time": datetime.now().isoformat()
                }
                json_path = os.path.join(backup_path, "incremental_data.json")
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

            with open(os.path.join(self.backup_dir, ".last_backup_time"), "w") as f:
                f.write(datetime.now().isoformat())

            backup_size = 0
            for dirpath, _, filenames in os.walk(backup_path):
                for fn in filenames:
                    fp = os.path.join(dirpath, fn)
                    backup_size += os.path.getsize(fp)

            logger.info("备份创建成功: %s (类型=%s, 大小=%d字节)", backup_name, backup_type, backup_size)
            return {
                "success": True,
                "backup_name": backup_name,
                "backup_path": backup_path,
                "backup_type": backup_type,
                "backup_size_bytes": backup_size,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error("备份创建失败: %s", e)
            return {"success": False, "error": str(e)}

    def restore_from_backup(self, backup_name: str) -> Dict[str, Any]:
        backup_path = os.path.join(self.backup_dir, backup_name)
        if not os.path.exists(backup_path):
            return {"success": False, "error": "备份不存在: " + backup_name}

        try:
            db_backup = os.path.join(backup_path, "working_memory.db")
            if os.path.exists(db_backup):
                if hasattr(self._local, "conn") and self._local.conn:
                    self._local.conn.close()
                    self._local.conn = None
                shutil.copy2(db_backup, self.db_path)
                logger.info("从备份恢复数据库: %s", backup_name)
                return {"success": True, "backup_name": backup_name, "method": "database"}

            json_backup = os.path.join(backup_path, "incremental_data.json")
            if os.path.exists(json_backup):
                with open(json_backup, "r", encoding="utf-8") as f:
                    data = json.load(f)
                restored_records = 0
                restored_rules = 0
                for rd in data.get("records", []):
                    record = self._dict_to_record(rd)
                    if record and self.store_record(record):
                        restored_records += 1
                for rd in data.get("rules", []):
                    rule = self._dict_to_rule(rd)
                    if rule and self.store_rule(rule):
                        restored_rules += 1
                logger.info("从增量备份恢复: %d条记录, %d条规则", restored_records, restored_rules)
                return {
                    "success": True,
                    "backup_name": backup_name,
                    "method": "incremental",
                    "restored_records": restored_records,
                    "restored_rules": restored_rules
                }

            return {"success": False, "error": "备份中未找到可恢复数据"}
        except Exception as e:
            logger.error("备份恢复失败: %s", e)
            return {"success": False, "error": str(e)}

    def list_backups(self) -> List[Dict[str, Any]]:
        backups = []
        if not os.path.exists(self.backup_dir):
            return backups
        for name in sorted(os.listdir(self.backup_dir), reverse=True):
            path = os.path.join(self.backup_dir, name)
            if not os.path.isdir(path):
                continue
            backup_info = {"name": name, "path": path}
            db_file = os.path.join(path, "working_memory.db")
            json_file = os.path.join(path, "incremental_data.json")
            if os.path.exists(db_file):
                backup_info["type"] = "full"
                backup_info["size_bytes"] = os.path.getsize(db_file)
            elif os.path.exists(json_file):
                backup_info["type"] = "incremental"
                backup_info["size_bytes"] = os.path.getsize(json_file)
            else:
                continue
            backup_info["created_at"] = datetime.fromtimestamp(
                os.path.getctime(path)
            ).isoformat()
            backups.append(backup_info)
        return backups[:50]

    def _row_to_record(self, row: sqlite3.Row) -> InteractionRecord:
        follow_ups_data = json.loads(row["follow_ups"]) if row["follow_ups"] else []
        follow_ups = [
            FollowUpItem(
                item_id=fu.get("item_id", ""),
                description=fu.get("description", ""),
                assignee=fu.get("assignee", ""),
                due_date=fu.get("due_date", ""),
                priority=fu.get("priority", 2),
                status=fu.get("status", "pending"),
                created_at=fu.get("created_at", ""),
                completed_at=fu.get("completed_at", "")
            ) for fu in follow_ups_data
        ]
        return InteractionRecord(
            record_id=row["record_id"],
            timestamp=row["timestamp"],
            customer_id=row["customer_id"],
            session_id=row["session_id"],
            dialogue_content=row["dialogue_content"],
            customer_needs=row["customer_needs"],
            system_response=row["system_response"],
            follow_ups=follow_ups,
            category=InteractionCategory(row["category"]),
            sentiment=InteractionSentiment(row["sentiment"]),
            status=InteractionStatus(row["status"]),
            tags=json.loads(row["tags"]) if row["tags"] else [],
            keywords=json.loads(row["keywords"]) if row["keywords"] else [],
            resolution_time_ms=row["resolution_time_ms"],
            satisfaction_score=row["satisfaction_score"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    def _row_to_rule(self, row: sqlite3.Row) -> ExperienceRule:
        return ExperienceRule(
            rule_id=row["rule_id"],
            rule_type=RuleType(row["rule_type"]),
            name=row["name"],
            description=row["description"],
            conditions=json.loads(row["conditions"]) if row["conditions"] else [],
            actions=json.loads(row["actions"]) if row["actions"] else [],
            confidence=row["confidence"],
            support_count=row["support_count"],
            apply_count=row["apply_count"],
            success_count=row["success_count"],
            source_records=json.loads(row["source_records"]) if row["source_records"] else [],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            status=RuleStatus(row["status"]),
            priority=row["priority"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {}
        )

    def _dict_to_record(self, data: Dict[str, Any]) -> Optional[InteractionRecord]:
        try:
            follow_ups = [
                FollowUpItem(
                    item_id=fu.get("item_id", ""),
                    description=fu.get("description", ""),
                    assignee=fu.get("assignee", ""),
                    due_date=fu.get("due_date", ""),
                    priority=fu.get("priority", 2),
                    status=fu.get("status", "pending"),
                    created_at=fu.get("created_at", ""),
                    completed_at=fu.get("completed_at", "")
                ) for fu in data.get("follow_ups", [])
            ]
            return InteractionRecord(
                record_id=data.get("record_id", ""),
                timestamp=data.get("timestamp", ""),
                customer_id=data.get("customer_id", ""),
                session_id=data.get("session_id", ""),
                dialogue_content=data.get("dialogue_content", ""),
                customer_needs=data.get("customer_needs", ""),
                system_response=data.get("system_response", ""),
                follow_ups=follow_ups,
                category=InteractionCategory(data.get("category", "general")),
                sentiment=InteractionSentiment(data.get("sentiment", "neutral")),
                status=InteractionStatus(data.get("status", "open")),
                tags=data.get("tags", []),
                keywords=data.get("keywords", []),
                resolution_time_ms=data.get("resolution_time_ms", 0.0),
                satisfaction_score=data.get("satisfaction_score", 0.0),
                metadata=data.get("metadata", {}),
                created_at=data.get("created_at", ""),
                updated_at=data.get("updated_at", "")
            )
        except Exception as e:
            logger.error("字典转记录失败: %s", e)
            return None

    def _dict_to_rule(self, data: Dict[str, Any]) -> Optional[ExperienceRule]:
        try:
            return ExperienceRule(
                rule_id=data.get("rule_id", ""),
                rule_type=RuleType(data.get("rule_type", "response_pattern")),
                name=data.get("name", ""),
                description=data.get("description", ""),
                conditions=data.get("conditions", []),
                actions=data.get("actions", []),
                confidence=data.get("confidence", 0.0),
                support_count=data.get("support_count", 0),
                apply_count=data.get("apply_count", 0),
                success_count=data.get("success_count", 0),
                source_records=data.get("source_records", []),
                tags=data.get("tags", []),
                status=RuleStatus(data.get("status", "draft")),
                priority=data.get("priority", 2),
                created_at=data.get("created_at", ""),
                updated_at=data.get("updated_at", ""),
                metadata=data.get("metadata", {})
            )
        except Exception as e:
            logger.error("字典转规则失败: %s", e)
            return None

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


class WorkingMemory:
    """
    工作记忆区 - 客户交互记录管理与经验提取引擎

    核心能力:
    - 交互记录全生命周期管理 (创建/查询/更新/删除)
    - 自动分类 (主题/情感/紧急度)
    - 经验提取 (响应模式/解决策略/升级条件)
    - 规则转化与验证 (经验→可应用规则)
    - 快速检索 (多维度/多条件)
    - 数据持久化 (SQLite + JSON备份)
    - 定期备份 (增量/全量)
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        base_dir = self.config.get("base_dir", "./data/working_memory")

        self._storage = WorkingMemoryStorage(
            db_path=os.path.join(base_dir, "working_memory.db"),
            backup_dir=os.path.join(base_dir, "backups")
        )
        self._classifier = InteractionClassifier()
        self._extractor = ExperienceExtractor(
            min_support=self.config.get("min_support", 3),
            min_confidence=self.config.get("min_confidence", 0.6)
        )

        self._record_cache: Dict[str, InteractionRecord] = {}
        self._rule_cache: Dict[str, ExperienceRule] = {}
        self._cache_lock = threading.RLock()
        self._max_cache_size = self.config.get("cache_size", 500)

        self._backup_running = False
        self._backup_thread = None
        self._extraction_running = False
        self._extraction_thread = None
        self._executor = ThreadPoolExecutor(max_workers=2)

        logger.info("工作记忆区初始化完成")

    def create_record(self, customer_id: str, session_id: str,
                      dialogue_content: str, customer_needs: str,
                      system_response: str,
                      follow_ups: List[Dict[str, Any]] = None,
                      category: str = None, sentiment: str = None,
                      tags: List[str] = None,
                      metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        combined_text = dialogue_content + " " + customer_needs

        auto_category = InteractionCategory(category) if category else self._classifier.classify_category(combined_text)
        auto_sentiment = InteractionSentiment(sentiment) if sentiment else self._classifier.classify_sentiment(combined_text)
        auto_keywords = self._classifier.extract_keywords(combined_text)
        auto_tags = list(set((tags or []) + [auto_category.value, auto_sentiment.value]))

        follow_up_items = []
        if follow_ups:
            for fu in follow_ups:
                follow_up_items.append(FollowUpItem(
                    item_id="fu_" + uuid.uuid4().hex[:8],
                    description=fu.get("description", ""),
                    assignee=fu.get("assignee", ""),
                    due_date=fu.get("due_date", ""),
                    priority=fu.get("priority", 2),
                    status=fu.get("status", "pending")
                ))

        record = InteractionRecord(
            record_id="rec_" + uuid.uuid4().hex[:12],
            timestamp=datetime.now().isoformat(),
            customer_id=customer_id,
            session_id=session_id,
            dialogue_content=dialogue_content,
            customer_needs=customer_needs,
            system_response=system_response,
            follow_ups=follow_up_items,
            category=auto_category,
            sentiment=auto_sentiment,
            tags=auto_tags,
            keywords=auto_keywords,
            metadata=metadata or {}
        )

        success = self._storage.store_record(record)
        if success:
            with self._cache_lock:
                self._record_cache[record.record_id] = record
                if len(self._record_cache) > self._max_cache_size:
                    oldest_key = min(self._record_cache, key=lambda k: self._record_cache[k].timestamp)
                    del self._record_cache[oldest_key]

        return {
            "success": success,
            "record_id": record.record_id if success else None,
            "category": auto_category.value,
            "sentiment": auto_sentiment.value,
            "keywords": auto_keywords,
            "tags": auto_tags
        }

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        with self._cache_lock:
            if record_id in self._record_cache:
                record = self._record_cache[record_id]
                return record.to_dict()

        record = self._storage.retrieve_record(record_id)
        if record:
            with self._cache_lock:
                self._record_cache[record_id] = record
            return record.to_dict()
        return None

    def search_records(self, query: str = None, customer_id: str = None,
                       category: str = None, sentiment: str = None,
                       status: str = None, start_time: str = None,
                       end_time: str = None, tags: List[str] = None,
                       limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        records = self._storage.search_records(
            query=query, customer_id=customer_id,
            category=category, sentiment=sentiment,
            status=status, start_time=start_time,
            end_time=end_time, tags=tags,
            limit=limit, offset=offset
        )
        total = self._storage.count_records(
            customer_id=customer_id, category=category,
            status=status, start_time=start_time,
            end_time=end_time
        )
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "records": [r.to_dict() for r in records]
        }

    def update_record(self, record_id: str, status: str = None,
                      satisfaction_score: float = None,
                      resolution_time_ms: float = None,
                      follow_ups: List[Dict[str, Any]] = None,
                      tags: List[str] = None,
                      metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        record = self._storage.retrieve_record(record_id)
        if not record:
            return {"success": False, "error": "记录不存在"}

        if status:
            record.status = InteractionStatus(status)
        if satisfaction_score is not None:
            record.satisfaction_score = satisfaction_score
        if resolution_time_ms is not None:
            record.resolution_time_ms = resolution_time_ms
        if follow_ups is not None:
            record.follow_ups = [
                FollowUpItem(
                    item_id=fu.get("item_id", "fu_" + uuid.uuid4().hex[:8]),
                    description=fu.get("description", ""),
                    assignee=fu.get("assignee", ""),
                    due_date=fu.get("due_date", ""),
                    priority=fu.get("priority", 2),
                    status=fu.get("status", "pending"),
                    created_at=fu.get("created_at", datetime.now().isoformat()),
                    completed_at=fu.get("completed_at", "")
                ) for fu in follow_ups
            ]
        if tags is not None:
            record.tags = tags
        if metadata is not None:
            record.metadata.update(metadata)

        record.updated_at = datetime.now().isoformat()
        success = self._storage.store_record(record)

        if success:
            with self._cache_lock:
                self._record_cache[record_id] = record

        return {"success": success, "record_id": record_id}

    def delete_record(self, record_id: str) -> Dict[str, Any]:
        success = self._storage.delete_record(record_id)
        if success:
            with self._cache_lock:
                self._record_cache.pop(record_id, None)
        return {"success": success, "record_id": record_id}

    def extract_experience(self, since: str = None,
                           rule_types: List[str] = None) -> Dict[str, Any]:
        records = self._storage.get_records_for_extraction(since=since, limit=10000)
        if len(records) < 3:
            return {
                "success": False,
                "message": "交互记录不足，至少需要3条已解决的记录才能提取经验",
                "record_count": len(records)
            }

        all_rules = []
        types = rule_types or [rt.value for rt in RuleType]

        if RuleType.RESPONSE_PATTERN.value in types:
            pattern_rules = self._extractor.extract_response_patterns(records)
            all_rules.extend(pattern_rules)
            logger.info("提取响应模式规则: %d条", len(pattern_rules))

        if RuleType.RESOLUTION_STRATEGY.value in types:
            strategy_rules = self._extractor.extract_resolution_strategies(records)
            all_rules.extend(strategy_rules)
            logger.info("提取解决策略规则: %d条", len(strategy_rules))

        if RuleType.ESCALATION_CONDITION.value in types:
            escalation_rules = self._extractor.extract_escalation_conditions(records)
            all_rules.extend(escalation_rules)
            logger.info("提取升级条件规则: %d条", len(escalation_rules))

        stored_count = 0
        for rule in all_rules:
            if self._storage.store_rule(rule):
                stored_count += 1
                with self._cache_lock:
                    self._rule_cache[rule.rule_id] = rule

        return {
            "success": True,
            "total_extracted": len(all_rules),
            "stored": stored_count,
            "by_type": {
                rt.value: sum(1 for r in all_rules if r.rule_type == rt)
                for rt in RuleType
            },
            "source_records": len(records)
        }

    def get_rules(self, rule_type: str = None, status: str = None,
                  min_confidence: float = 0.0, tags: List[str] = None,
                  limit: int = 20) -> Dict[str, Any]:
        rules = self._storage.search_rules(
            rule_type=rule_type, status=status,
            min_confidence=min_confidence, tags=tags,
            limit=limit
        )
        return {
            "total": len(rules),
            "rules": [r.to_dict() for r in rules]
        }

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        with self._cache_lock:
            if rule_id in self._rule_cache:
                return self._rule_cache[rule_id].to_dict()

        rule = self._storage.retrieve_rule(rule_id)
        if rule:
            with self._cache_lock:
                self._rule_cache[rule_id] = rule
            return rule.to_dict()
        return None

    def apply_rule(self, rule_id: str, success: bool) -> Dict[str, Any]:
        rule = self._storage.retrieve_rule(rule_id)
        if not rule:
            return {"success": False, "error": "规则不存在"}

        self._storage.record_rule_application(rule_id, success)

        rule.apply_count += 1
        if success:
            rule.success_count += 1

        if rule.apply_count >= 5 and rule.success_rate >= 0.7:
            self._storage.update_rule_status(rule_id, RuleStatus.ACTIVE.value)
            rule.status = RuleStatus.ACTIVE
        elif rule.apply_count >= 10 and rule.success_rate < 0.4:
            self._storage.update_rule_status(rule_id, RuleStatus.DEPRECATED.value)
            rule.status = RuleStatus.DEPRECATED

        with self._cache_lock:
            self._rule_cache[rule_id] = rule

        return {
            "success": True,
            "rule_id": rule_id,
            "apply_count": rule.apply_count,
            "success_rate": round(rule.success_rate, 3),
            "status": rule.status.value
        }

    def update_rule(self, rule_id: str, status: str = None,
                    priority: int = None, tags: List[str] = None) -> Dict[str, Any]:
        rule = self._storage.retrieve_rule(rule_id)
        if not rule:
            return {"success": False, "error": "规则不存在"}

        if status:
            self._storage.update_rule_status(rule_id, status)
            rule.status = RuleStatus(status)
        if priority is not None:
            rule.priority = priority
        if tags is not None:
            rule.tags = tags

        rule.updated_at = datetime.now().isoformat()
        self._storage.store_rule(rule)

        with self._cache_lock:
            self._rule_cache[rule_id] = rule

        return {"success": True, "rule_id": rule_id}

    def delete_rule(self, rule_id: str) -> Dict[str, Any]:
        success = self._storage.delete_rule(rule_id)
        if success:
            with self._cache_lock:
                self._rule_cache.pop(rule_id, None)
        return {"success": success, "rule_id": rule_id}

    def match_rules(self, customer_needs: str, category: str = None,
                    sentiment: str = None, limit: int = 5) -> Dict[str, Any]:
        active_rules = self._storage.search_rules(
            status=RuleStatus.ACTIVE.value, min_confidence=0.5, limit=100
        )

        scored_rules = []
        needs_keywords = set(self._classifier.extract_keywords(customer_needs))

        for rule in active_rules:
            score = rule.confidence

            if category and "category==" + category in rule.conditions:
                score += 0.3

            if sentiment:
                for cond in rule.conditions:
                    if "sentiment==" in cond and sentiment in cond:
                        score += 0.2

            rule_keyword_set = set(rule.tags + rule.conditions)
            overlap = needs_keywords & rule_keyword_set
            if overlap:
                score += len(overlap) * 0.1

            score += min(rule.success_rate, 1.0) * 0.2

            scored_rules.append((rule, score))

        scored_rules.sort(key=lambda x: x[1], reverse=True)
        top_rules = scored_rules[:limit]

        return {
            "total_matched": len(top_rules),
            "rules": [
                {
                    "rule": r.to_dict(),
                    "match_score": round(s, 3),
                    "applicable_actions": r.actions[:3]
                } for r, s in top_rules
            ]
        }

    def create_backup(self, backup_type: str = "full") -> Dict[str, Any]:
        return self._storage.create_backup(backup_type)

    def restore_backup(self, backup_name: str) -> Dict[str, Any]:
        return self._storage.restore_from_backup(backup_name)

    def list_backups(self) -> Dict[str, Any]:
        backups = self._storage.list_backups()
        return {"total": len(backups), "backups": backups}

    def start_auto_backup(self, interval_hours: int = 24,
                          backup_type: str = "incremental"):
        if self._backup_running:
            return {"status": "already_running"}

        self._backup_running = True

        def _backup_loop():
            while self._backup_running:
                time.sleep(interval_hours * 3600)
                try:
                    result = self._storage.create_backup(backup_type)
                    logger.info("自动备份完成: %s", result.get("backup_name", "unknown"))
                except Exception as e:
                    logger.error("自动备份失败: %s", e)

        self._backup_thread = threading.Thread(target=_backup_loop, daemon=True)
        self._backup_thread.start()
        logger.info("自动备份启动 (间隔=%d小时, 类型=%s)", interval_hours, backup_type)
        return {"status": "started", "interval_hours": interval_hours, "backup_type": backup_type}

    def stop_auto_backup(self):
        self._backup_running = False
        return {"status": "stopped"}

    def start_auto_extraction(self, interval_hours: int = 6):
        if self._extraction_running:
            return {"status": "already_running"}

        self._extraction_running = True

        def _extraction_loop():
            while self._extraction_running:
                time.sleep(interval_hours * 3600)
                try:
                    result = self.extract_experience()
                    logger.info("自动经验提取完成: %s", str(result))
                except Exception as e:
                    logger.error("自动经验提取失败: %s", e)

        self._extraction_thread = threading.Thread(target=_extraction_loop, daemon=True)
        self._extraction_thread.start()
        logger.info("自动经验提取启动 (间隔=%d小时)", interval_hours)
        return {"status": "started", "interval_hours": interval_hours}

    def stop_auto_extraction(self):
        self._extraction_running = False
        return {"status": "stopped"}

    def get_customer_history(self, customer_id: str, limit: int = 50) -> Dict[str, Any]:
        records = self._storage.search_records(customer_id=customer_id, limit=limit)
        total = self._storage.count_records(customer_id=customer_id)

        categories: Dict[str, int] = Counter(r.category.value for r in records)
        sentiments: Dict[str, int] = Counter(r.sentiment.value for r in records)
        statuses: Dict[str, int] = Counter(r.status.value for r in records)

        avg_satisfaction = 0.0
        scored = [r.satisfaction_score for r in records if r.satisfaction_score > 0]
        if scored:
            avg_satisfaction = sum(scored) / len(scored)

        pending_follow_ups = []
        for r in records:
            for fu in r.follow_ups:
                if fu.status == "pending":
                    pending_follow_ups.append(fu.to_dict())

        return {
            "customer_id": customer_id,
            "total_interactions": total,
            "recent_records": [r.to_dict() for r in records[:10]],
            "category_distribution": dict(categories),
            "sentiment_distribution": dict(sentiments),
            "status_distribution": dict(statuses),
            "avg_satisfaction": round(avg_satisfaction, 2),
            "pending_follow_ups": pending_follow_ups
        }

    def get_statistics(self) -> Dict[str, Any]:
        stats = self._storage.get_statistics()
        with self._cache_lock:
            stats["cache_size"] = len(self._record_cache)
            stats["rule_cache_size"] = len(self._rule_cache)
        stats["auto_backup_running"] = self._backup_running
        stats["auto_extraction_running"] = self._extraction_running
        return stats

    def close(self):
        self._backup_running = False
        self._extraction_running = False
        self._storage.close()
        self._executor.shutdown(wait=False)
        logger.info("工作记忆区关闭")


_working_memory: Optional[WorkingMemory] = None
_lock = threading.Lock()


def get_working_memory(config: Dict[str, Any] = None) -> WorkingMemory:
    """获取全局工作记忆区实例（线程安全单例）"""
    global _working_memory
    if _working_memory is None:
        with _lock:
            if _working_memory is None:
                _working_memory = WorkingMemory(config)
    return _working_memory
