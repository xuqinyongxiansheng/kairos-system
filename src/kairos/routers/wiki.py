"""
Wiki 路由
提供文档 CRUD、查询、搜索等端点
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Wiki"])

MAX_CONTENT_LENGTH = 500000
MAX_QUESTION_LENGTH = 2000
MAX_QUERY_LENGTH = 500
ALLOWED_SOURCES = ["custom", "wiki", "document", "web", "markdown", "code"]

_wiki_instance = None

def init_wiki_deps(wiki_instance):
    global _wiki_instance
    _wiki_instance = wiki_instance

def _get_wiki():
    global _wiki_instance
    if _wiki_instance is None:
        try:
            from kairos.system.core.llm_wiki_compat import LLMWikiCompatLayer
            _wiki_instance = LLMWikiCompatLayer(chunk_size=256, chunk_overlap=30)
        except Exception as e:
            logger.error(f"Wiki 初始化失败: {e}")
            return None
    return _wiki_instance

class WikiAddRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1, max_length=MAX_CONTENT_LENGTH)
    source: str = "custom"
    source_url: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('source')
    @classmethod
    def validate_source(cls, v):
        if v not in ALLOWED_SOURCES:
            raise ValueError(f'无效的来源类型，允许: {", ".join(ALLOWED_SOURCES)}')
        return v

    @field_validator('source_url')
    @classmethod
    def validate_url(cls, v):
        if v and not (v.startswith('http://') or v.startswith('https://') or v.startswith('file://')):
            raise ValueError('URL必须以http://、https://或file://开头')
        return v

class WikiQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=MAX_QUESTION_LENGTH)
    top_k: int = Field(default=5, ge=1, le=20)
    generate_answer: bool = True

    @field_validator('question')
    @classmethod
    def sanitize_question(cls, v):
        return v.strip()

class WikiSearchRequest(BaseModel):
    q: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH)
    limit: int = Field(default=5, ge=1, le=50)
    source_type: Optional[str] = None

    @field_validator('source_type')
    @classmethod
    def validate_source_type(cls, v):
        if v and v not in ALLOWED_SOURCES:
            raise ValueError('无效的来源类型')
        return v

@router.post("/v1/documents")
async def wiki_add_document(request: WikiAddRequest):
    """添加文档"""
    wiki = _get_wiki()
    if not wiki:
        raise HTTPException(status_code=503, detail="Wiki 服务不可用")
    try:
        from kairos.system.core.llm_wiki_compat import WikiSourceType
        try:
            source = WikiSourceType(request.source)
        except ValueError:
            source = WikiSourceType.CUSTOM
        result = await wiki.add_document(
            title=request.title,
            content=request.content,
            source=source,
            source_url=request.source_url,
            metadata=request.metadata
        )
        if result.get("status") == "rejected_low_memory":
            raise HTTPException(status_code=503, detail="内存不足，无法摄取文档")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/v1/documents/{doc_id}")
async def wiki_get_document(doc_id: str):
    """获取文档"""
    wiki = _get_wiki()
    if not wiki:
        raise HTTPException(status_code=503, detail="Wiki 服务不可用")
    result = await wiki.get_document(doc_id)
    if not result:
        raise HTTPException(status_code=404, detail="文档不存在")
    return result

@router.get("/v1/documents")
async def wiki_list_documents(source_type: Optional[str] = None,
                               limit: int = 20, offset: int = 0):
    """列出文档"""
    wiki = _get_wiki()
    if not wiki:
        raise HTTPException(status_code=503, detail="Wiki 服务不可用")
    st = None
    if source_type:
        try:
            from kairos.system.core.llm_wiki_compat import WikiSourceType
            st = WikiSourceType(source_type)
        except ValueError:
            pass
    return wiki.list_documents(source_type=st, limit=limit, offset=offset)

@router.post("/v1/query")
async def wiki_query(request: WikiQueryRequest):
    """查询 Wiki"""
    wiki = _get_wiki()
    if not wiki:
        raise HTTPException(status_code=503, detail="Wiki 服务不可用")
    return await wiki.query(
        question=request.question,
        top_k=request.top_k,
        generate_answer=request.generate_answer
    )

@router.get("/v1/search")
async def wiki_search(q: str, limit: int = 5, source_type: Optional[str] = None):
    """搜索 Wiki"""
    wiki = _get_wiki()
    if not wiki:
        raise HTTPException(status_code=503, detail="Wiki 服务不可用")
    st = None
    if source_type:
        try:
            from kairos.system.core.llm_wiki_compat import WikiSourceType
            st = WikiSourceType(source_type)
        except ValueError:
            pass
    return await wiki.search(query=q, limit=limit, source_type=st)

@router.delete("/v1/documents/{doc_id}")
async def wiki_delete_document(doc_id: str):
    """删除文档"""
    wiki = _get_wiki()
    if not wiki:
        raise HTTPException(status_code=503, detail="Wiki 服务不可用")
    success = await wiki.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"status": "deleted", "doc_id": doc_id}

@router.get("/v1/health")
async def wiki_health():
    """Wiki 健康检查"""
    wiki = _get_wiki()
    if not wiki:
        return {"status": "unavailable"}
    return wiki.health_check()
