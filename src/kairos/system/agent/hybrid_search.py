# -*- coding: utf-8 -*-
"""
三模式混合检索引擎

支持三种搜索模式：
- embedding: 纯向量相似度搜索（余弦距离）
- keywords: 纯关键词全文检索（FTS5）
- blend: 向量+关键词混合检索（加权融合）

核心设计：
- 策略模式：三种搜索策略可插拔
- 统一接口：SearchResult统一返回格式
- 加权融合：blend模式通过RRF(Reciprocal Rank Fusion)合并结果
- 降级策略：向量搜索不可用时自动降级到关键词搜索

参考: MaxKB pg_vector.py 三种搜索模式
"""

import json
import math
import logging
import sqlite3
import threading
from abc import ABC, abstractmethod
from collections import defaultdict
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class SearchMode(Enum):
    EMBEDDING = "embedding"
    KEYWORDS = "keywords"
    BLEND = "blend"


@dataclass
class SearchResult:
    id: str
    content: str
    score: float
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    search_mode: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content[:200],
            "score": round(self.score, 4),
            "source": self.source,
            "metadata": self.metadata,
            "search_mode": self.search_mode,
        }


@dataclass
class SearchQuery:
    query: str
    mode: SearchMode = SearchMode.BLEND
    top_k: int = 5
    similarity_threshold: float = 0.6
    filters: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


class BaseSearchStrategy(ABC):
    """搜索策略基类"""

    @abstractmethod
    def search(self, query: SearchQuery) -> List[SearchResult]:
        pass

    @abstractmethod
    def index(self, doc_id: str, content: str,
              embedding: Optional[List[float]] = None,
              metadata: Optional[Dict] = None) -> bool:
        pass

    @abstractmethod
    def delete(self, doc_id: str) -> bool:
        pass


class KeywordsSearchStrategy(BaseSearchStrategy):
    """
    关键词全文检索策略。

    基于SQLite FTS5实现，支持：
    - unicode61分词器（中文支持）
    - BM25排序
    - 通配符搜索
    - LIKE降级
    """

    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._persistent_conn: Optional[sqlite3.Connection] = None
        if db_path == ":memory:":
            self._persistent_conn = sqlite3.connect(db_path, timeout=5.0)
            self._persistent_conn.execute("PRAGMA journal_mode=WAL")
            self._persistent_conn.execute("PRAGMA temp_store=MEMORY")
        self._init_db()

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_docs (
                    doc_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS search_docs_fts
                USING fts5(doc_id, content, tokenize='unicode61')
            """)

    def _get_conn(self) -> sqlite3.Connection:
        if self._persistent_conn is not None:
            return self._persistent_conn
        conn = sqlite3.connect(self._db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        return conn

    def search(self, query: SearchQuery) -> List[SearchResult]:
        sanitized = self._sanitize_query(query.query)
        results = []

        try:
            with self._get_conn() as conn:
                cursor = conn.execute("""
                    SELECT doc_id, content, metadata,
                           rank AS score
                    FROM search_docs_fts
                    WHERE search_docs_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (sanitized, query.top_k))

                for row in cursor:
                    score = max(0.0, 1.0 - abs(row[3]) / 10.0)
                    if score >= query.similarity_threshold:
                        results.append(SearchResult(
                            id=row[0],
                            content=row[1],
                            score=score,
                            metadata=self._parse_json(row[2]),
                            search_mode="keywords",
                        ))
        except sqlite3.OperationalError:
            results = self._fallback_like(query)

        return results

    def _fallback_like(self, query: SearchQuery) -> List[SearchResult]:
        """LIKE降级搜索"""
        results = []
        try:
            with self._get_conn() as conn:
                cursor = conn.execute("""
                    SELECT doc_id, content, metadata FROM search_docs
                    WHERE content LIKE ?
                    LIMIT ?
                """, (f"%{query.query}%", query.top_k))

                for row in cursor:
                    results.append(SearchResult(
                        id=row[0],
                        content=row[1],
                        score=0.5,
                        metadata=self._parse_json(row[2]),
                        search_mode="keywords_like",
                    ))
        except Exception as e:
            logger.error("LIKE降级搜索失败: %s", e)

        return results

    def index(self, doc_id: str, content: str,
              embedding: Optional[List[float]] = None,
              metadata: Optional[Dict] = None) -> bool:
        try:
            with self._lock:
                with self._get_conn() as conn:
                    conn.execute("""
                        DELETE FROM search_docs_fts WHERE doc_id = ?
                    """, (doc_id,))
                    conn.execute("""
                        INSERT OR REPLACE INTO search_docs(doc_id, content, metadata)
                        VALUES (?, ?, ?)
                    """, (doc_id, content, json.dumps(metadata or {})))
                    conn.execute("""
                        INSERT INTO search_docs_fts(doc_id, content)
                        VALUES (?, ?)
                    """, (doc_id, content))
            return True
        except Exception as e:
            logger.error("索引文档失败: %s", e)
            return False

    def delete(self, doc_id: str) -> bool:
        try:
            with self._lock:
                with self._get_conn() as conn:
                    conn.execute("""
                        DELETE FROM search_docs_fts WHERE doc_id = ?
                    """, (doc_id,))
                    conn.execute("DELETE FROM search_docs WHERE doc_id = ?", (doc_id,))
            return True
        except Exception as e:
            logger.error("删除文档失败: %s", e)
            return False

    @staticmethod
    def _sanitize_query(query: str) -> str:
        words = query.split()
        sanitized = []
        for word in words:
            clean = ''.join(c for c in word if c.isalnum() or '\u4e00' <= c <= '\u9fff')
            if clean:
                sanitized.append(f"{clean}*")
        return " ".join(sanitized) if sanitized else query

    @staticmethod
    def _parse_json(s: str) -> Dict:
        try:
            return json.loads(s)
        except Exception:
            return {}


class EmbeddingSearchStrategy(BaseSearchStrategy):
    """
    向量相似度搜索策略。

    基于余弦距离实现，支持：
    - 内存向量存储
    - 余弦相似度计算
    - TopK排序
    - 降级到关键词搜索
    """

    def __init__(self, keywords_strategy: Optional[KeywordsSearchStrategy] = None):
        self._vectors: Dict[str, Tuple[List[float], str, Dict]] = {}
        self._keywords_strategy = keywords_strategy
        self._lock = threading.Lock()

    def search(self, query: SearchQuery) -> List[SearchResult]:
        if query.embedding is None:
            if self._keywords_strategy:
                return self._keywords_strategy.search(query)
            return []

        query_vec = query.embedding
        scores: List[Tuple[str, float, str, Dict]] = []

        with self._lock:
            for doc_id, (vec, content, meta) in self._vectors.items():
                sim = self._cosine_similarity(query_vec, vec)
                if sim >= query.similarity_threshold:
                    scores.append((doc_id, sim, content, meta))

        scores.sort(key=lambda x: x[1], reverse=True)
        top_k = scores[:query.top_k]

        return [
            SearchResult(id=doc_id, content=content, score=score,
                         metadata=meta, search_mode="embedding")
            for doc_id, score, content, meta in top_k
        ]

    def index(self, doc_id: str, content: str,
              embedding: Optional[List[float]] = None,
              metadata: Optional[Dict] = None) -> bool:
        if embedding is None:
            if self._keywords_strategy:
                return self._keywords_strategy.index(doc_id, content, metadata=metadata)
            return False

        with self._lock:
            self._vectors[doc_id] = (embedding, content, metadata or {})
        return True

    def delete(self, doc_id: str) -> bool:
        with self._lock:
            return self._vectors.pop(doc_id, None) is not None

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class BlendSearchStrategy(BaseSearchStrategy):
    """
    混合检索策略。

    通过RRF(Reciprocal Rank Fusion)合并向量搜索和关键词搜索的结果：
    RRF_score = Σ 1/(k + rank_i)，其中k=60

    同时执行两种搜索，通过RRF公式融合排序，取最优结果。
    """

    RRF_K = 60

    def __init__(self, keywords_strategy: KeywordsSearchStrategy,
                 embedding_strategy: EmbeddingSearchStrategy):
        self._keywords = keywords_strategy
        self._embedding = embedding_strategy

    def search(self, query: SearchQuery) -> List[SearchResult]:
        kw_query = SearchQuery(
            query=query.query, mode=SearchMode.KEYWORDS,
            top_k=query.top_k * 2, similarity_threshold=query.similarity_threshold,
        )
        emb_query = SearchQuery(
            query=query.query, mode=SearchMode.EMBEDDING,
            top_k=query.top_k * 2, similarity_threshold=query.similarity_threshold,
            embedding=query.embedding,
        )

        kw_results = self._keywords.search(kw_query)
        emb_results = self._embedding.search(emb_query)

        rrf_scores: Dict[str, float] = defaultdict(float)
        result_map: Dict[str, SearchResult] = {}

        for rank, result in enumerate(kw_results, 1):
            rrf_scores[result.id] += 1.0 / (self.RRF_K + rank)
            if result.id not in result_map:
                result_map[result.id] = result

        for rank, result in enumerate(emb_results, 1):
            rrf_scores[result.id] += 1.0 / (self.RRF_K + rank)
            if result.id not in result_map:
                result_map[result.id] = result

        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        top_ids = sorted_ids[:query.top_k]

        results = []
        for doc_id in top_ids:
            result = result_map[doc_id]
            result.score = rrf_scores[doc_id]
            result.search_mode = "blend"
            results.append(result)

        return results

    def index(self, doc_id: str, content: str,
              embedding: Optional[List[float]] = None,
              metadata: Optional[Dict] = None) -> bool:
        kw_ok = self._keywords.index(doc_id, content, metadata=metadata)
        emb_ok = self._embedding.index(doc_id, content, embedding=embedding, metadata=metadata)
        return kw_ok or emb_ok

    def delete(self, doc_id: str) -> bool:
        kw_ok = self._keywords.delete(doc_id)
        emb_ok = self._embedding.delete(doc_id)
        return kw_ok or emb_ok


class HybridSearchEngine:
    """
    三模式混合检索引擎，整合三种搜索策略。

    提供：
    - 统一搜索接口（自动选择搜索模式）
    - 文档索引管理
    - 搜索统计
    - 降级策略
    """

    def __init__(self, db_path: str = ":memory:"):
        self._keywords = KeywordsSearchStrategy(db_path)
        self._embedding = EmbeddingSearchStrategy(self._keywords)
        self._blend = BlendSearchStrategy(self._keywords, self._embedding)
        self._strategies = {
            SearchMode.KEYWORDS: self._keywords,
            SearchMode.EMBEDDING: self._embedding,
            SearchMode.BLEND: self._blend,
        }
        self._stats = {
            "searches": 0,
            "by_mode": {m.value: 0 for m in SearchMode},
            "index_operations": 0,
            "delete_operations": 0,
        }
        self._lock = threading.Lock()

    def search(self, query: str, mode: str = "blend",
               top_k: int = 5, similarity: float = 0.6,
               embedding: Optional[List[float]] = None,
               filters: Optional[Dict] = None) -> List[SearchResult]:
        """统一搜索接口"""
        search_mode = SearchMode(mode)
        sq = SearchQuery(
            query=query, mode=search_mode, top_k=top_k,
            similarity_threshold=similarity, embedding=embedding,
            filters=filters or {},
        )

        strategy = self._strategies.get(search_mode)
        if strategy is None:
            strategy = self._blend

        with self._lock:
            self._stats["searches"] += 1
            self._stats["by_mode"][search_mode.value] += 1

        try:
            results = strategy.search(sq)
        except Exception as e:
            logger.error("搜索异常，降级到关键词搜索: %s", e)
            results = self._keywords.search(sq)

        return results

    def index(self, doc_id: str, content: str,
              embedding: Optional[List[float]] = None,
              metadata: Optional[Dict] = None) -> bool:
        """索引文档"""
        with self._lock:
            self._stats["index_operations"] += 1
        return self._blend.index(doc_id, content, embedding, metadata)

    def delete(self, doc_id: str) -> bool:
        """删除文档"""
        with self._lock:
            self._stats["delete_operations"] += 1
        return self._blend.delete(doc_id)

    def batch_index(self, documents: List[Dict]) -> int:
        """批量索引"""
        count = 0
        for doc in documents:
            if self.index(
                doc.get("id", ""),
                doc.get("content", ""),
                doc.get("embedding"),
                doc.get("metadata"),
            ):
                count += 1
        return count

    def get_statistics(self) -> dict:
        """获取统计"""
        with self._lock:
            return dict(self._stats)


_search_engine: Optional[HybridSearchEngine] = None


def get_hybrid_search_engine() -> HybridSearchEngine:
    """获取混合检索引擎单例"""
    global _search_engine
    if _search_engine is None:
        _search_engine = HybridSearchEngine()
    return _search_engine
