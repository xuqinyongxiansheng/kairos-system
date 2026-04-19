"""
ChromaDB 向量记忆系统
基于 ChromaDB 实现语义记忆搜索能力
整合 CLI-Anything 和 002/AAagent 的优秀实现
"""

import chromadb
from chromadb.config import Settings
from typing import Dict, List, Any, Optional
import hashlib
import json
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)


class ChromaDBMemory:
    """ChromaDB 向量记忆系统 - 实现语义记忆搜索"""
    
    def __init__(self, config: Dict = None):
        """
        初始化 ChromaDB 记忆系统
        
        Args:
            config: 配置字典，可指定 vector_db_path 等参数
        """
        if config is None:
            config = {}
        
        self.config = config
        self.persist_directory = config.get("vector_db_path", "./data/chromadb")
        
        os.makedirs(self.persist_directory, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection = self.client.get_or_create_collection(
            name="system_memory",
            metadata={"description": "系统记忆存储"}
        )
        
        logger.info(f"ChromaDB 记忆系统初始化完成，存储路径：{self.persist_directory}")
    
    async def add_memory(self, 
                        content: str, 
                        memory_type: str = "conversation",
                        metadata: Dict = None) -> str:
        """
        添加记忆到向量数据库
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型 (conversation/knowledge/fact 等)
            metadata: 额外元数据
            
        Returns:
            记忆 ID
        """
        memory_id = hashlib.md5(
            f"{content}_{datetime.now().isoformat()}".encode()
        ).hexdigest()
        
        if metadata is None:
            metadata = {}
        
        full_metadata = {
            "type": memory_type,
            "timestamp": datetime.now().isoformat(),
            "content_preview": content[:100],
            **metadata
        }
        
        self.collection.add(
            documents=[content],
            metadatas=[full_metadata],
            ids=[memory_id]
        )
        
        logger.info(f"记忆已保存：{memory_id[:8]}... ({memory_type})")
        return memory_id
    
    async def search_memories(self, 
                            query: str, 
                            n_results: int = 5,
                            memory_type: Optional[str] = None,
                            min_similarity: float = 0.5) -> List[Dict[str, Any]]:
        """
        搜索相关记忆
        
        Args:
            query: 搜索查询文本
            n_results: 返回结果数量
            memory_type: 记忆类型过滤
            min_similarity: 最小相似度阈值
            
        Returns:
            记忆列表
        """
        where_filter = {}
        if memory_type:
            where_filter["type"] = memory_type
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter if where_filter else None,
                include=["documents", "metadatas", "distances"]
            )
            
            memories = []
            for i in range(len(results["ids"][0])):
                distance = results["distances"][0][i] if results["distances"] else 0
                relevance_score = 1.0 / (1.0 + distance) if distance > 0 else 1.0
                
                if relevance_score < min_similarity:
                    continue
                
                memories.append({
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "relevance_score": round(relevance_score, 3),
                    "distance": round(distance, 3)
                })
            
            logger.info(f"搜索找到 {len(memories)} 个相关记忆")
            return memories
            
        except Exception as e:
            logger.error(f"记忆搜索失败：{e}")
            return []
    
    async def get_similar_conversations(self, 
                                      current_input: str, 
                                      n_results: int = 3) -> List[Dict[str, Any]]:
        """获取相似的过往对话"""
        return await self.search_memories(
            query=current_input,
            n_results=n_results,
            memory_type="conversation"
        )
    
    async def get_related_knowledge(self, 
                                  topic: str, 
                                  n_results: int = 5) -> List[Dict[str, Any]]:
        """获取相关知识"""
        return await self.search_memories(
            query=topic,
            n_results=n_results,
            memory_type="knowledge"
        )
    
    async def add_conversation(self, 
                             user_input: str, 
                             assistant_reply: str,
                             importance: int = 1) -> str:
        """添加对话到记忆"""
        conversation_text = f"用户：{user_input}\n助手：{assistant_reply}"
        
        memory_id = await self.add_memory(
            content=conversation_text,
            memory_type="conversation",
            metadata={
                "importance": importance,
                "user_input": user_input,
                "assistant_reply": assistant_reply
            }
        )
        
        return memory_id
    
    async def add_fact(self, fact: str, source: str = "", confidence: float = 1.0) -> str:
        """添加事实到记忆"""
        memory_id = await self.add_memory(
            content=fact,
            memory_type="knowledge",
            metadata={
                "source": source,
                "confidence": confidence,
                "category": "fact"
            }
        )
        
        return memory_id
    
    async def get_memory_count(self) -> Dict[str, int]:
        """获取记忆统计"""
        all_memories = self.collection.get()
        
        type_counts = {}
        for metadata in all_memories["metadatas"]:
            memory_type = metadata.get("type", "unknown")
            type_counts[memory_type] = type_counts.get(memory_type, 0) + 1
        
        return {
            "total": len(all_memories["ids"]),
            "by_type": type_counts
        }
    
    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        try:
            self.collection.delete(ids=[memory_id])
            logger.info(f"记忆已删除：{memory_id[:8]}...")
            return True
        except Exception as e:
            logger.error(f"删除记忆失败：{e}")
            return False
    
    async def update_memory(self, memory_id: str, content: str = None, metadata: Dict = None) -> bool:
        """更新记忆"""
        try:
            existing = self.collection.get(ids=[memory_id])
            if not existing["ids"]:
                logger.warning(f"记忆不存在：{memory_id}")
                return False
            
            if content:
                self.collection.update(
                    ids=[memory_id],
                    documents=[content]
                )
            
            if metadata:
                existing_metadata = existing["metadatas"][0] if existing["metadatas"] else {}
                updated_metadata = {**existing_metadata, **metadata}
                self.collection.update(
                    ids=[memory_id],
                    metadatas=[updated_metadata]
                )
            
            logger.info(f"记忆已更新：{memory_id[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"更新记忆失败：{e}")
            return False
    
    async def get_recent_memories(self, memory_type: Optional[str] = None, n_results: int = 10) -> List[Dict[str, Any]]:
        """获取最近的记忆"""
        try:
            all_memories = self.collection.get()
            
            filtered_memories = []
            for i, metadata in enumerate(all_memories["metadatas"]):
                if memory_type and metadata.get("type") != memory_type:
                    continue
                
                filtered_memories.append({
                    "id": all_memories["ids"][i],
                    "content": all_memories["documents"][i],
                    "metadata": metadata
                })
            
            filtered_memories.sort(
                key=lambda x: x["metadata"].get("timestamp", ""),
                reverse=True
            )
            
            return filtered_memories[:n_results]
            
        except Exception as e:
            logger.error(f"获取最近记忆失败：{e}")
            return []
    
    async def export_memories(self, output_file: str, memory_type: Optional[str] = None) -> bool:
        """导出记忆到文件"""
        try:
            if memory_type:
                memories = await self.search_by_metadata({"type": memory_type})
            else:
                all_memories = self.collection.get()
                memories = []
                for i in range(len(all_memories["ids"])):
                    memories.append({
                        "id": all_memories["ids"][i],
                        "content": all_memories["documents"][i],
                        "metadata": all_memories["metadatas"][i]
                    })
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(memories, f, ensure_ascii=False, indent=2)
            
            logger.info(f"记忆已导出到：{output_file}")
            return True
            
        except Exception as e:
            logger.error(f"导出记忆失败：{e}")
            return False
    
    async def import_memories(self, input_file: str) -> int:
        """从文件导入记忆"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                memories = json.load(f)
            
            imported_count = 0
            for memory in memories:
                try:
                    existing = self.collection.get(ids=[memory["id"]])
                    if existing["ids"]:
                        continue
                    
                    self.collection.add(
                        documents=[memory["content"]],
                        metadatas=[memory["metadata"]],
                        ids=[memory["id"]]
                    )
                    imported_count += 1
                    
                except Exception as e:
                    logger.error(f"导入记忆失败 {memory['id']}: {e}")
            
            logger.info(f"成功导入 {imported_count} 条记忆")
            return imported_count
            
        except Exception as e:
            logger.error(f"导入记忆失败：{e}")
            return 0
    
    async def search_by_metadata(self, metadata_filter: Dict, n_results: int = 5) -> List[Dict[str, Any]]:
        """根据元数据搜索记忆"""
        try:
            results = self.collection.query(
                query_texts=[""],
                n_results=n_results,
                where=metadata_filter,
                include=["documents", "metadatas"]
            )
            
            memories = []
            for i in range(len(results["ids"][0])):
                memories.append({
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i]
                })
            
            return memories
            
        except Exception as e:
            logger.error(f"元数据搜索失败：{e}")
            return []
    
    async def clear_all_memories(self) -> bool:
        """清空所有记忆"""
        try:
            all_memories = self.collection.get()
            if all_memories["ids"]:
                self.collection.delete(ids=all_memories["ids"])
            logger.info("所有记忆已清空")
            return True
        except Exception as e:
            logger.error(f"清空记忆失败：{e}")
            return False


class ChromaDBBackend:
    """
    ChromaDB HTTP API 客户端（来自 CLI-Anything）
    用于连接远程 ChromaDB 服务器
    """
    
    def __init__(self, base_url: str = "http://localhost:8000",
                 tenant: str = "default_tenant",
                 database: str = "default_database"):
        self.base_url = base_url.rstrip("/")
        self.tenant = tenant
        self.database = database
        self._session = None
        
        try:
            import requests
            self._session = requests.Session()
            self._session.headers.update({"Content-Type": "application/json"})
        except ImportError:
            logger.warning("requests 库未安装，ChromaDB HTTP 客户端不可用")
    
    @property
    def _tenant_db_prefix(self) -> str:
        return f"{self.base_url}/api/v2/tenants/{self.tenant}/databases/{self.database}"
    
    def heartbeat(self) -> dict:
        """检查服务器健康状态"""
        if not self._session:
            return {"status": "unavailable"}
        r = self._session.get(f"{self.base_url}/api/v2/heartbeat")
        r.raise_for_status()
        return r.json()
    
    def version(self) -> str:
        """获取服务器版本"""
        if not self._session:
            return "unknown"
        r = self._session.get(f"{self.base_url}/api/v2/version")
        r.raise_for_status()
        return r.json()
    
    def list_collections(self) -> list:
        """列出所有集合"""
        if not self._session:
            return []
        r = self._session.get(f"{self._tenant_db_prefix}/collections")
        r.raise_for_status()
        return r.json()
    
    def create_collection(self, name: str, metadata: dict = None) -> dict:
        """创建新集合"""
        if not self._session:
            return {}
        body = {"name": name}
        if metadata:
            body["metadata"] = metadata
        r = self._session.post(
            f"{self._tenant_db_prefix}/collections",
            json=body,
        )
        r.raise_for_status()
        return r.json()
    
    def get_collection(self, name: str) -> dict:
        """获取集合信息"""
        if not self._session:
            return {}
        r = self._session.get(f"{self._tenant_db_prefix}/collections/{name}")
        r.raise_for_status()
        return r.json()
    
    def delete_collection(self, name: str) -> bool:
        """删除集合"""
        if not self._session:
            return False
        r = self._session.delete(f"{self._tenant_db_prefix}/collections/{name}")
        r.raise_for_status()
        return True


chromadb_memory = ChromaDBMemory()
chromadb_backend = ChromaDBBackend()
