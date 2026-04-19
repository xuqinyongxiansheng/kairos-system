# -*- coding: utf-8 -*-
"""
LLM Wiki 兼容层 (LLM Wiki Compatibility Layer)

为项目系统提供与LLM Wiki类系统的标准化兼容接口，实现:
1. 知识摄取: 从Wiki/文档源自动采集结构化知识
2. 语义检索: 基于向量数据库的RAG检索增强生成
3. 知识管理: CRUD操作 + 版本控制 + 引用溯源
4. API服务: RESTful接口 + 事件驱动集成

与项目现有模块的映射:
- 知识摄取 → UnifiedStorage(四层存储) + CompoundEngine(复利摄取)
- 语义检索 → UnifiedStorage.VectorLayer(ChromaDB) + KnowledgeDistillation(蒸馏)
- 知识管理 → UnifiedStorage.RelationalLayer(SQLite) + FileLayer(JSON)
- API服务 → FastAPI + EventBus + MessagingGateway

兼容的LLM Wiki类系统特征:
- 向量数据库后端 (ChromaDB/FAISS/Pinecone)
- 文档分块与嵌入 (Chunking + Embedding)
- RAG检索增强生成 (Retrieval-Augmented Generation)
- 知识图谱关联 (Knowledge Graph)
- 多源摄取 (Wikipedia/MediaWiki/自定义文档)
"""

import json
import os
import time
import hashlib
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger("LLMWikiCompat")

_EMBEDDING_MODEL = os.environ.get("HMYX_EMBEDDING_MODEL", "nomic-embed-text")
_LLM_MODEL = os.environ.get("GEMMA4_MODEL", "gemma4:e4b")
_MEMORY_THRESHOLD_MB = int(os.environ.get("HMYX_MEMORY_THRESHOLD_MB", "500"))


def _check_memory() -> bool:
    try:
        import psutil
        available = psutil.virtual_memory().available / (1024 * 1024)
        if available < _MEMORY_THRESHOLD_MB:
            logger.warning(f"可用内存不足: {available:.0f}MB < {_MEMORY_THRESHOLD_MB}MB")
            return False
    except ImportError:
        pass
    return True


async def ollama_embed(text: str, model: str = _EMBEDDING_MODEL) -> List[float]:
    try:
        import ollama
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: ollama.embeddings(model=model, prompt=text)
        )
        return response.get("embedding", [])
    except Exception as e:
        logger.debug(f"Ollama嵌入失败: {e}，回退到hash嵌入")
        return _hash_embed(text)


async def ollama_generate(prompt: str, model: str = _LLM_MODEL) -> str:
    try:
        import ollama
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: ollama.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
        )
        return response.get("message", {}).get("content", "")
    except Exception as e:
        logger.error(f"Ollama生成失败: {e}")
        return ""


def _hash_embed(text: str) -> List[float]:
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return [int(h[i:i+2], 16) / 255.0 for i in range(0, min(len(h), 128), 2)]


class WikiSourceType(Enum):
    WIKIPEDIA = "wikipedia"
    MEDIAWIKI = "mediawiki"
    MARKDOWN = "markdown"
    JSON_DOC = "json_doc"
    WEB_PAGE = "web_page"
    PDF = "pdf"
    CUSTOM = "custom"


class ChunkStrategy(Enum):
    FIXED_SIZE = "fixed_size"
    PARAGRAPH = "paragraph"
    SEMANTIC = "semantic"
    SENTENCE = "sentence"


@dataclass
class WikiDocument:
    doc_id: str
    title: str
    content: str
    source: WikiSourceType
    source_url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "content": self.content,
            "source": self.source.value,
            "source_url": self.source_url,
            "metadata": self.metadata,
            "chunks_count": len(self.chunks),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version
        }


@dataclass
class SearchResult:
    doc_id: str
    chunk_id: str
    content: str
    relevance: float
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "chunk_id": self.chunk_id,
            "content": self.content,
            "relevance": round(self.relevance, 3),
            "source": self.source,
            "metadata": self.metadata
        }


class DocumentChunker:
    """文档分块器"""

    def __init__(self, chunk_size: int = 512, overlap: int = 50,
                 strategy: ChunkStrategy = ChunkStrategy.PARAGRAPH):
        self.chunk_size = max(chunk_size, 1)
        self.overlap = min(overlap, max(self.chunk_size - 1, 0))
        self.strategy = strategy

    def chunk(self, content: str, doc_id: str = "") -> List[Dict[str, Any]]:
        if self.strategy == ChunkStrategy.FIXED_SIZE:
            return self._fixed_chunk(content, doc_id)
        elif self.strategy == ChunkStrategy.PARAGRAPH:
            return self._paragraph_chunk(content, doc_id)
        elif self.strategy == ChunkStrategy.SENTENCE:
            return self._sentence_chunk(content, doc_id)
        else:
            return self._fixed_chunk(content, doc_id)

    def _fixed_chunk(self, content: str, doc_id: str) -> List[Dict[str, Any]]:
        chunks = []
        start = 0
        idx = 0
        step = max(self.chunk_size - self.overlap, 1)
        while start < len(content):
            end = min(start + self.chunk_size, len(content))
            chunk_content = content[start:end]
            chunk_id = hashlib.sha256(f"{doc_id}_{idx}".encode()).hexdigest()[:12]
            chunks.append({
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "content": chunk_content,
                "index": idx,
                "start_char": start,
                "end_char": end
            })
            start += step
            idx += 1
        return chunks

    def _paragraph_chunk(self, content: str, doc_id: str) -> List[Dict[str, Any]]:
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [content]
        chunks = []
        current = ""
        idx = 0
        for para in paragraphs:
            if len(current) + len(para) > self.chunk_size and current:
                chunk_id = hashlib.sha256(f"{doc_id}_{idx}".encode()).hexdigest()[:12]
                chunks.append({
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "content": current.strip(),
                    "index": idx
                })
                overlap_text = current[-self.overlap:] if self.overlap > 0 else ""
                current = overlap_text + para + "\n\n"
                idx += 1
            else:
                current += para + "\n\n"
        if current.strip():
            chunk_id = hashlib.sha256(f"{doc_id}_{idx}".encode()).hexdigest()[:12]
            chunks.append({
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "content": current.strip(),
                "index": idx
            })
        return chunks

    def _sentence_chunk(self, content: str, doc_id: str) -> List[Dict[str, Any]]:
        sentences = []
        for line in content.split("\n"):
            for sent in line.replace("。", "。\n").replace(".", ".\n").split("\n"):
                sent = sent.strip()
                if sent:
                    sentences.append(sent)
        chunks = []
        current = ""
        idx = 0
        for sent in sentences:
            if len(current) + len(sent) > self.chunk_size and current:
                chunk_id = hashlib.sha256(f"{doc_id}_{idx}".encode()).hexdigest()[:12]
                chunks.append({
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "content": current.strip(),
                    "index": idx
                })
                current = sent + " "
                idx += 1
            else:
                current += sent + " "
        if current.strip():
            chunk_id = hashlib.sha256(f"{doc_id}_{idx}".encode()).hexdigest()[:12]
            chunks.append({
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "content": current.strip(),
                "index": idx
            })
        return chunks


class LLMWikiCompatLayer:
    """
    LLM Wiki 兼容层

    提供与LLM Wiki类系统兼容的标准化接口，桥接项目现有模块:
    - UnifiedStorage: 四层存储 (缓存→关系→向量→文件)
    - CompoundEngine: 复利摄取 (摄取→消化→输出→迭代)
    - KnowledgeDistillation: 知识蒸馏 (提取→压缩→泛化→验证)
    - InteractionCompound: 交互学习 (用户反馈→技能提升)

    API接口兼容设计:
    - POST /api/v1/documents     → add_document()
    - GET  /api/v1/documents/:id → get_document()
    - POST /api/v1/query         → query()
    - GET  /api/v1/search        → search()
    - DELETE /api/v1/documents/:id → delete_document()
    - GET  /api/v1/health        → health_check()
    """

    def __init__(self, core_ref=None, chunk_size: int = 512,
                 chunk_overlap: int = 50,
                 chunk_strategy: ChunkStrategy = ChunkStrategy.PARAGRAPH,
                 embedding_fn: Optional[Callable] = None,
                 generation_fn: Optional[Callable] = None):
        self.core = core_ref
        self._chunker = DocumentChunker(chunk_size, chunk_overlap, chunk_strategy)
        self._documents: Dict[str, WikiDocument] = {}
        self._chunk_index: Dict[str, Dict[str, Any]] = {}
        self._embeddings: Dict[str, List[float]] = {}
        self._embedding_fn = embedding_fn
        self._generation_fn = generation_fn
        self._use_ollama_embed = embedding_fn is None
        self._use_ollama_generate = generation_fn is None
        self._stats = {
            "documents_added": 0,
            "documents_deleted": 0,
            "queries_processed": 0,
            "searches_performed": 0,
            "chunks_created": 0,
            "embeddings_generated": 0,
            "rag_generations": 0,
            "memory_warnings": 0
        }

    async def add_document(self, title: str, content: str,
                            source: WikiSourceType = WikiSourceType.CUSTOM,
                            source_url: str = "",
                            metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        if not _check_memory():
            self._stats["memory_warnings"] += 1
            logger.warning(f"内存不足，拒绝摄取文档: {title}")
            return {"doc_id": "", "title": title, "chunks_count": 0,
                    "source": source.value, "status": "rejected_low_memory"}

        doc_id = hashlib.sha256(f"{title}_{time.time()}".encode()).hexdigest()[:16]
        chunks = self._chunker.chunk(content, doc_id)

        doc = WikiDocument(
            doc_id=doc_id, title=title, content=content,
            source=source, source_url=source_url,
            metadata=metadata or {}, chunks=chunks
        )
        self._documents[doc_id] = doc

        for chunk in chunks:
            self._chunk_index[chunk["chunk_id"]] = {
                "doc_id": doc_id,
                "content": chunk["content"],
                "index": chunk["index"]
            }

        self._stats["documents_added"] += 1
        self._stats["chunks_created"] += len(chunks)

        await self._generate_embeddings(doc_id, chunks)

        if self.core:
            try:
                await self.core.storage_store(
                    content=content,
                    category="semantic",
                    priority=1,
                    tags=["wiki", source.value, title[:20]],
                    metadata={"doc_id": doc_id, "source": source.value, "chunks": len(chunks)}
                )
            except Exception as e:
                logger.debug(f"存储到统一存储层失败: {e}")

            try:
                await self.core.compound_ingest_execution(
                    f"Wiki文档摄取: {title}",
                    [{"tool": "llm_wiki_compat", "parameters": {"doc_id": doc_id}}],
                    {"success": True, "chunks": len(chunks)}
                )
            except Exception as e:
                logger.debug(f"摄取到复利引擎失败: {e}")

        return {
            "doc_id": doc_id,
            "title": title,
            "chunks_count": len(chunks),
            "source": source.value,
            "status": "indexed"
        }

    async def _generate_embeddings(self, doc_id: str,
                                    chunks: List[Dict[str, Any]]) -> int:
        count = 0
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id", "")
            content = chunk.get("content", "")
            if not content:
                continue
            try:
                if self._embedding_fn:
                    result = self._embedding_fn(content)
                    emb = await result if asyncio.iscoroutine(result) else result
                elif self._use_ollama_embed:
                    emb = await ollama_embed(content)
                else:
                    emb = _hash_embed(content)
                if emb:
                    self._embeddings[chunk_id] = emb
                    count += 1
            except Exception as e:
                logger.debug(f"嵌入生成失败 chunk={chunk_id}: {e}")
        self._stats["embeddings_generated"] += count
        return count

    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        doc = self._documents.get(doc_id)
        if not doc:
            return None
        return doc.to_dict()

    async def query(self, question: str, top_k: int = 5,
                     include_sources: bool = True,
                     generate_answer: bool = True) -> Dict[str, Any]:
        self._stats["queries_processed"] += 1
        results = await self.search(question, limit=top_k)

        context_parts = [r["content"] for r in results]
        context = "\n\n---\n\n".join(context_parts)

        sources = []
        if include_sources:
            for r in results:
                sources.append({
                    "doc_id": r["doc_id"],
                    "relevance": r["relevance"],
                    "source": r.get("source", "")
                })

        answer = ""
        if generate_answer and context:
            self._stats["rag_generations"] += 1
            answer = await self._rag_generate(question, context)

        return {
            "question": question,
            "answer": answer,
            "context": context if not answer else None,
            "sources": sources,
            "results_count": len(results),
            "top_results": results
        }

    async def _rag_generate(self, question: str, context: str) -> str:
        prompt = (
            f"基于以下参考资料回答问题。如果资料中没有相关信息，请说明。\n\n"
            f"参考资料:\n{context}\n\n"
            f"问题: {question}\n\n"
            f"回答:"
        )
        try:
            if self._generation_fn:
                result = self._generation_fn(prompt)
                return await result if asyncio.iscoroutine(result) else result
            elif self._use_ollama_generate:
                return await ollama_generate(prompt)
        except Exception as e:
            logger.error(f"RAG生成失败: {e}")
        return ""

    async def search(self, query: str, limit: int = 10,
                      source_type: Optional[WikiSourceType] = None) -> List[Dict[str, Any]]:
        self._stats["searches_performed"] += 1
        results = []

        if self.core:
            try:
                storage_results = await self.core.storage_search(
                    query, category="semantic", limit=limit
                )
                for sr in storage_results:
                    results.append(SearchResult(
                        doc_id=sr.get("id", ""),
                        chunk_id="",
                        content=sr.get("content", ""),
                        relevance=sr.get("relevance", 0.5),
                        source=sr.get("metadata", {}).get("source", ""),
                        metadata=sr.get("metadata", {})
                    ).to_dict())
            except Exception as e:
                logger.debug(f"统一存储层搜索失败: {e}")

        query_embedding = None
        if self._embeddings:
            try:
                if self._embedding_fn:
                    result = self._embedding_fn(query)
                    query_embedding = await result if asyncio.iscoroutine(result) else result
                elif self._use_ollama_embed:
                    query_embedding = await ollama_embed(query)
                else:
                    query_embedding = _hash_embed(query)
            except Exception:
                query_embedding = _hash_embed(query)

        q_lower = query.lower()
        scored_chunks = []
        for chunk_id, chunk_data in self._chunk_index.items():
            if source_type:
                doc = self._documents.get(chunk_data["doc_id"])
                if doc and doc.source != source_type:
                    continue
            score = 0.0
            if q_lower in chunk_data["content"].lower():
                score += 0.5
            for word in q_lower.split():
                if word in chunk_data["content"].lower():
                    score += 0.2
            if query_embedding and chunk_id in self._embeddings:
                sim = self._cosine_similarity(query_embedding, self._embeddings[chunk_id])
                score = max(score, sim)
            if score > 0:
                doc = self._documents.get(chunk_data["doc_id"])
                scored_chunks.append((score, chunk_id, chunk_data, doc))

        scored_chunks.sort(key=lambda x: -x[0])
        for score, chunk_id, chunk_data, doc in scored_chunks:
            results.append(SearchResult(
                doc_id=chunk_data["doc_id"],
                chunk_id=chunk_id,
                content=chunk_data["content"][:200],
                relevance=min(score, 1.0),
                source=doc.source.value if doc else "",
                metadata={"index": chunk_data["index"]}
            ).to_dict())

        seen = set()
        unique = []
        for r in results:
            key = r.get("chunk_id") or r.get("doc_id")
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique[:limit]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    async def delete_document(self, doc_id: str) -> bool:
        doc = self._documents.get(doc_id)
        if not doc:
            return False
        for chunk in doc.chunks:
            chunk_id = chunk.get("chunk_id", "")
            self._chunk_index.pop(chunk_id, None)
            self._embeddings.pop(chunk_id, None)
        del self._documents[doc_id]
        self._stats["documents_deleted"] += 1
        return True

    async def update_document(self, doc_id: str, content: str = None,
                               title: str = None, metadata: Dict = None) -> Optional[Dict]:
        doc = self._documents.get(doc_id)
        if not doc:
            return None
        if content is not None:
            for chunk in doc.chunks:
                self._chunk_index.pop(chunk.get("chunk_id", ""), None)
            new_chunks = self._chunker.chunk(content, doc_id)
            doc.content = content
            doc.chunks = new_chunks
            doc.version += 1
            doc.updated_at = time.time()
            for chunk in new_chunks:
                self._chunk_index[chunk["chunk_id"]] = {
                    "doc_id": doc_id,
                    "content": chunk["content"],
                    "index": chunk["index"]
                }
            self._stats["chunks_created"] += len(new_chunks)
        if title is not None:
            doc.title = title
        if metadata is not None:
            doc.metadata.update(metadata)
        return doc.to_dict()

    def health_check(self) -> Dict[str, Any]:
        mem_info = {}
        try:
            import psutil
            vm = psutil.virtual_memory()
            mem_info = {
                "total_mb": round(vm.total / (1024 * 1024)),
                "available_mb": round(vm.available / (1024 * 1024)),
                "percent": vm.percent
            }
        except ImportError:
            pass
        return {
            "status": "healthy",
            "documents_count": len(self._documents),
            "chunks_count": len(self._chunk_index),
            "embeddings_count": len(self._embeddings),
            "embedding_mode": "ollama" if self._use_ollama_embed else ("custom" if self._embedding_fn else "hash"),
            "generation_mode": "ollama" if self._use_ollama_generate else ("custom" if self._generation_fn else "none"),
            "memory": mem_info,
            "stats": self._stats
        }

    def list_documents(self, source_type: Optional[WikiSourceType] = None,
                        limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        docs = list(self._documents.values())
        if source_type:
            docs = [d for d in docs if d.source == source_type]
        docs.sort(key=lambda d: -d.updated_at)
        return [d.to_dict() for d in docs[offset:offset + limit]]

    def get_statistics(self) -> Dict[str, Any]:
        by_source = defaultdict(int)
        for doc in self._documents.values():
            by_source[doc.source.value] += 1
        return {
            "total_documents": len(self._documents),
            "total_chunks": len(self._chunk_index),
            "by_source": dict(by_source),
            "chunker": {
                "chunk_size": self._chunker.chunk_size,
                "overlap": self._chunker.overlap,
                "strategy": self._chunker.strategy.value
            },
            "stats": self._stats
        }


_llm_wiki_compat: Optional[LLMWikiCompatLayer] = None


def get_llm_wiki_compat(core_ref=None, **kwargs) -> LLMWikiCompatLayer:
    global _llm_wiki_compat
    if _llm_wiki_compat is None:
        _llm_wiki_compat = LLMWikiCompatLayer(core_ref, **kwargs)
    return _llm_wiki_compat
