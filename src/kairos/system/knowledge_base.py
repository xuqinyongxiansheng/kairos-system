"""
知识库模块
实现本地知识存储、检索、全文搜索功能
整合 002/AAagent 的优秀实现
"""

import json
import os
import sqlite3
import hashlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class KnowledgeType(Enum):
    """知识库类型枚举"""
    DOCUMENT = "document"
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    URL = "url"


class SearchType(Enum):
    """搜索类型枚举"""
    EXACT = "exact"
    FUZZY = "fuzzy"
    SEMANTIC = "semantic"
    TAG = "tag"


@dataclass
class KnowledgeItem:
    """知识条目数据类"""
    id: str
    title: str
    content: str
    type: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]


@dataclass
class SearchResult:
    """搜索结果数据类"""
    item_id: str
    title: str
    content: str
    type: str
    tags: List[str]
    relevance: float
    snippet: str


class KnowledgeBase:
    """知识库类"""
    
    def __init__(self, db_path: str = "./data/knowledge_base.db"):
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self.db_path = db_path
        self._init_database()
        logger.info("知识库初始化完成")
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_items (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                type TEXT NOT NULL,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        # 尝试创建全文检索表（如果支持）
        try:
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_search 
                USING fts5(title, content, tokenize='porter')
            ''')
            self.fts_enabled = True
        except Exception:
            self.fts_enabled = False
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_tags (
                item_id TEXT,
                tag TEXT,
                FOREIGN KEY (item_id) REFERENCES knowledge_items(id),
                UNIQUE(item_id, tag)
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge_items(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_knowledge_tags ON knowledge_tags(tag)')
        
        conn.commit()
        conn.close()
    
    def add_knowledge(self, title: str, content: str, knowledge_type: str = "text",
                     tags: List[str] = None, metadata: Dict[str, Any] = None) -> str:
        """添加知识条目"""
        if tags is None:
            tags = []
        if metadata is None:
            metadata = {}
        
        item_id = hashlib.md5(f"{title}{content}{datetime.now()}".encode()).hexdigest()
        
        tags_str = json.dumps(tags, ensure_ascii=False)
        metadata_str = json.dumps(metadata, ensure_ascii=False)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO knowledge_items (id, title, content, type, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (item_id, title, content, knowledge_type, tags_str, metadata_str))
            
            # 更新全文检索表
            if self.fts_enabled:
                try:
                    cursor.execute('''
                        INSERT INTO knowledge_search (rowid, title, content)
                        VALUES ((SELECT rowid FROM knowledge_items WHERE id = ?), ?, ?)
                    ''', (item_id, title, content))
                except Exception:
                    logger.debug(f"忽略异常: ", exc_info=True)
                    pass
            
            for tag in tags:
                cursor.execute('''
                    INSERT OR IGNORE INTO knowledge_tags (item_id, tag)
                    VALUES (?, ?)
                ''', (item_id, tag))
            
            conn.commit()
            logger.info(f"添加知识成功：{title} ({item_id[:8]}...)")
            return item_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"添加知识失败：{e}")
            raise Exception(f"添加知识失败：{str(e)}")
        finally:
            conn.close()
    
    def get_knowledge(self, item_id: str) -> Optional[KnowledgeItem]:
        """获取知识条目"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, title, content, type, tags, created_at, updated_at, metadata
                FROM knowledge_items WHERE id = ?
            ''', (item_id,))
            
            row = cursor.fetchone()
            if row:
                tags = json.loads(row[4]) if row[4] else []
                metadata = json.loads(row[7]) if row[7] else {}
                
                return KnowledgeItem(
                    id=row[0],
                    title=row[1],
                    content=row[2],
                    type=row[3],
                    tags=tags,
                    created_at=datetime.fromisoformat(row[5]),
                    updated_at=datetime.fromisoformat(row[6]),
                    metadata=metadata
                )
            return None
            
        finally:
            conn.close()
    
    def search(self, query: str, search_type: str = "fuzzy",
               knowledge_type: str = None, tags: List[str] = None,
               limit: int = 10) -> List[SearchResult]:
        """搜索知识"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if search_type == SearchType.EXACT.value:
                sql = '''
                    SELECT k.id, k.title, k.content, k.type, k.tags
                    FROM knowledge_items k
                    WHERE k.title LIKE ? OR k.content LIKE ?
                '''
                params = [f"%{query}%", f"%{query}%"]
            
            elif search_type == SearchType.FUZZY.value and self.fts_enabled:
                sql = '''
                    SELECT k.id, k.title, k.content, k.type, k.tags
                    FROM knowledge_items k
                    JOIN knowledge_search ks ON k.rowid = ks.rowid
                    WHERE knowledge_search MATCH ?
                    ORDER BY rank DESC
                '''
                params = [query]
            
            elif search_type == SearchType.SEMANTIC.value:
                sql = '''
                    SELECT k.id, k.title, k.content, k.type, k.tags
                    FROM knowledge_items k
                    WHERE k.title LIKE ? OR k.content LIKE ?
                    ORDER BY 
                        CASE WHEN k.title LIKE ? THEN 1 ELSE 0 END +
                        CASE WHEN k.content LIKE ? THEN 1 ELSE 0 END DESC
                '''
                params = [f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"]
            
            elif search_type == SearchType.TAG.value:
                sql = '''
                    SELECT k.id, k.title, k.content, k.type, k.tags
                    FROM knowledge_items k
                    JOIN knowledge_tags kt ON k.id = kt.item_id
                    WHERE kt.tag = ?
                '''
                params = [query]
            
            else:
                sql = '''
                    SELECT k.id, k.title, k.content, k.type, k.tags
                    FROM knowledge_items k
                    WHERE k.title LIKE ? OR k.content LIKE ?
                '''
                params = [f"%{query}%", f"%{query}%"]
            
            if knowledge_type:
                sql += " AND k.type = ?"
                params.append(knowledge_type)
            
            if tags:
                for tag in tags:
                    sql += " AND k.id IN (SELECT item_id FROM knowledge_tags WHERE tag = ?)"
                    params.append(tag)
            
            sql += " LIMIT ?"
            params.append(limit)
            
            cursor.execute(sql, params)
            results = []
            
            for row in cursor.fetchall():
                item_tags = json.loads(row[4]) if row[4] else []
                snippet = self._generate_snippet(row[2], query)
                relevance = self._calculate_relevance(row[1], row[2], query)
                
                results.append(SearchResult(
                    item_id=row[0],
                    title=row[1],
                    content=row[2],
                    type=row[3],
                    tags=item_tags,
                    relevance=relevance,
                    snippet=snippet
                ))
            
            return results
            
        finally:
            conn.close()
    
    def get_all_items(self, knowledge_type: str = None, limit: int = 100) -> List[KnowledgeItem]:
        """获取所有知识条目"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            sql = "SELECT id, title, content, type, tags, created_at, updated_at, metadata FROM knowledge_items"
            params = []
            
            if knowledge_type:
                sql += " WHERE type = ?"
                params.append(knowledge_type)
            
            sql += " LIMIT ?"
            params.append(limit)
            
            cursor.execute(sql, params)
            results = []
            
            for row in cursor.fetchall():
                item_tags = json.loads(row[4]) if row[4] else []
                metadata = json.loads(row[7]) if row[7] else {}
                
                results.append(KnowledgeItem(
                    id=row[0],
                    title=row[1],
                    content=row[2],
                    type=row[3],
                    tags=item_tags,
                    created_at=datetime.fromisoformat(row[5]),
                    updated_at=datetime.fromisoformat(row[6]),
                    metadata=metadata
                ))
            
            return results
            
        finally:
            conn.close()
    
    def get_tags(self) -> List[str]:
        """获取所有标签"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT DISTINCT tag FROM knowledge_tags ORDER BY tag')
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def delete_knowledge(self, item_id: str) -> bool:
        """删除知识条目"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM knowledge_tags WHERE item_id = ?', (item_id,))
            
            if self.fts_enabled:
                try:
                    cursor.execute('''
                        DELETE FROM knowledge_search
                        WHERE rowid = (SELECT rowid FROM knowledge_items WHERE id = ?)
                    ''', (item_id,))
                except Exception:
                    logger.debug(f"忽略异常: ", exc_info=True)
                    pass
            
            cursor.execute('DELETE FROM knowledge_items WHERE id = ?', (item_id,))
            
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT COUNT(*) FROM knowledge_items')
            total_items = cursor.fetchone()[0]
            
            cursor.execute('SELECT type, COUNT(*) FROM knowledge_items GROUP BY type')
            type_stats = {row[0]: row[1] for row in cursor.fetchall()}
            
            cursor.execute('SELECT tag, COUNT(*) FROM knowledge_tags GROUP BY tag ORDER BY COUNT(*) DESC LIMIT 10')
            top_tags = [{"tag": row[0], "count": row[1]} for row in cursor.fetchall()]
            
            return {
                "total_items": total_items,
                "type_statistics": type_stats,
                "top_tags": top_tags
            }
        finally:
            conn.close()
    
    def export_knowledge(self, export_path: str) -> bool:
        """导出知识库"""
        try:
            items = self.get_all_items(limit=1000)
            export_data = []
            
            for item in items:
                export_data.append({
                    "id": item.id,
                    "title": item.title,
                    "content": item.content,
                    "type": item.type,
                    "tags": item.tags,
                    "created_at": item.created_at.isoformat(),
                    "updated_at": item.updated_at.isoformat(),
                    "metadata": item.metadata
                })
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"知识库已导出到：{export_path}")
            return True
        except Exception as e:
            logger.error(f"导出失败：{e}")
            return False
    
    def import_knowledge(self, import_path: str) -> int:
        """导入知识库"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            imported_count = 0
            for item_data in import_data:
                self.add_knowledge(
                    title=item_data.get("title", ""),
                    content=item_data.get("content", ""),
                    knowledge_type=item_data.get("type", "text"),
                    tags=item_data.get("tags", []),
                    metadata=item_data.get("metadata", {})
                )
                imported_count += 1
            
            logger.info(f"导入完成，共 {imported_count} 条知识")
            return imported_count
        except Exception as e:
            logger.error(f"导入失败：{e}")
            return 0
    
    def _generate_snippet(self, content: str, query: str) -> str:
        """生成搜索摘要"""
        query_lower = query.lower()
        content_lower = content.lower()
        
        start_pos = content_lower.find(query_lower)
        if start_pos == -1:
            return content[:150] + "..." if len(content) > 150 else content
        
        snippet_start = max(0, start_pos - 50)
        snippet_end = min(len(content), start_pos + len(query) + 100)
        
        snippet = content[snippet_start:snippet_end]
        if snippet_start > 0:
            snippet = "..." + snippet
        if snippet_end < len(content):
            snippet = snippet + "..."
        
        return snippet
    
    def _calculate_relevance(self, title: str, content: str, query: str) -> float:
        """计算相关性分数"""
        query_words = set(query.lower().split())
        title_words = set(title.lower().split())
        content_words = set(content.lower().split())
        
        title_match = len(query_words.intersection(title_words)) / len(query_words) if query_words else 0
        content_match = len(query_words.intersection(content_words)) / len(query_words) if query_words else 0
        
        return (title_match * 0.5 + content_match * 0.5)


knowledge_base = KnowledgeBase()
