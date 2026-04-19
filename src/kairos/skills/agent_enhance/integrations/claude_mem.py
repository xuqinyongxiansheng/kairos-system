#!/usr/bin/env python3
"""
Claude Mem 适配器
深度集成 claude-mem 持久化记忆压缩系统
"""

import os
import json
import sqlite3
import hashlib
import logging
import subprocess
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..professional_agents.base_agent import ProfessionalAgent, get_agent_registry

logger = logging.getLogger(__name__)


class MemoryStore:
    """记忆存储"""
    
    def __init__(self, db_path: str = "data/claude_mem/memories.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                content TEXT NOT NULL,
                summary TEXT,
                category TEXT DEFAULT 'general',
                tags TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                tool_name TEXT,
                observation TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_session ON memories(session_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)
        """)
        conn.commit()
        conn.close()
    
    def store_memory(self, session_id: str, content: str, summary: str = None,
                     category: str = "general", tags: List[str] = None) -> int:
        """存储记忆"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO memories (session_id, content, summary, category, tags)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, content, summary, category, json.dumps(tags or [])))
        memory_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return memory_id
    
    def store_observation(self, session_id: str, tool_name: str, observation: str) -> int:
        """存储观察"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO observations (session_id, tool_name, observation)
            VALUES (?, ?, ?)
        """, (session_id, tool_name, observation))
        obs_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return obs_id
    
    def search_memories(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索记忆"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, session_id, content, summary, category, tags, created_at
            FROM memories
            WHERE content LIKE ? OR summary LIKE ?
            ORDER BY accessed_at DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "session_id": row[1],
                "content": row[2],
                "summary": row[3],
                "category": row[4],
                "tags": json.loads(row[5]) if row[5] else [],
                "created_at": row[6]
            })
        conn.close()
        return results
    
    def get_memory_timeline(self, session_id: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """获取记忆时间线"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if session_id:
            cursor.execute("""
                SELECT id, session_id, content, summary, category, created_at
                FROM memories
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (session_id, limit))
        else:
            cursor.execute("""
                SELECT id, session_id, content, summary, category, created_at
                FROM memories
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "session_id": row[1],
                "content": row[2],
                "summary": row[3],
                "category": row[4],
                "created_at": row[5]
            })
        conn.close()
        return results
    
    def get_observations(self, obs_ids: List[int]) -> List[Dict[str, Any]]:
        """获取观察详情"""
        if not obs_ids:
            return []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        placeholders = ",".join("?" * len(obs_ids))
        cursor.execute(f"""
            SELECT id, session_id, tool_name, observation, created_at
            FROM observations
            WHERE id IN ({placeholders})
        """, obs_ids)
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "session_id": row[1],
                "tool_name": row[2],
                "observation": row[3],
                "created_at": row[4]
            })
        conn.close()
        return results


class ClaudeMemAdapter:
    """Claude Mem 适配器 - 深度集成持久化记忆系统"""
    
    def __init__(self, claude_mem_dir: str = "project/vendor/claude-mem"):
        self.claude_mem_dir = claude_mem_dir
        self.memory_store = MemoryStore()
        self.agents = {}
        self._init_agents()
        self._check_claude_mem_installation()
    
    def _check_claude_mem_installation(self):
        """检查 claude-mem 安装状态"""
        self.claude_mem_installed = os.path.exists(self.claude_mem_dir)
        if self.claude_mem_installed:
            logger.info("claude-mem 仓库已就绪")
        else:
            logger.info("claude-mem 仓库未找到，使用内置记忆系统")
    
    def _init_agents(self):
        """初始化代理"""
        self.agents["memory_manager"] = {
            "name": "记忆管理代理",
            "description": "基于 Claude Mem 的持久化记忆管理代理，支持跨会话记忆保持和检索",
            "skills": ["memory_storage", "memory_retrieval", "memory_compression", "session_context"],
            "capabilities": ["persistent_memory", "semantic_search", "progressive_disclosure", "observation_capture"]
        }
        self.agents["context_agent"] = {
            "name": "上下文增强代理",
            "description": "基于 Claude Mem 的上下文增强代理，自动注入历史上下文到新会话",
            "skills": ["context_injection", "context_summarization", "context_filtering"],
            "capabilities": ["auto_context", "smart_summarization", "privacy_control"]
        }
    
    def store_memory(self, session_id: str, content: str, summary: str = None,
                     category: str = "general", tags: List[str] = None) -> Dict[str, Any]:
        """存储记忆"""
        memory_id = self.memory_store.store_memory(session_id, content, summary, category, tags)
        return {
            "status": "success",
            "memory_id": memory_id,
            "session_id": session_id,
            "message": f"记忆已存储，ID: {memory_id}"
        }
    
    def search_memories(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """搜索记忆"""
        results = self.memory_store.search_memories(query, limit)
        return {
            "status": "success",
            "query": query,
            "results": results,
            "count": len(results)
        }
    
    def get_timeline(self, session_id: str = None, limit: int = 20) -> Dict[str, Any]:
        """获取记忆时间线"""
        results = self.memory_store.get_memory_timeline(session_id, limit)
        return {
            "status": "success",
            "timeline": results,
            "count": len(results)
        }
    
    def store_observation(self, session_id: str, tool_name: str, observation: str) -> Dict[str, Any]:
        """存储观察"""
        obs_id = self.memory_store.store_observation(session_id, tool_name, observation)
        return {
            "status": "success",
            "observation_id": obs_id,
            "message": f"观察已存储，ID: {obs_id}"
        }
    
    def get_observations(self, obs_ids: List[int]) -> Dict[str, Any]:
        """获取观察详情"""
        results = self.memory_store.get_observations(obs_ids)
        return {
            "status": "success",
            "observations": results,
            "count": len(results)
        }
    
    def convert_to_professional_agent(self, agent_name: str) -> Optional[ProfessionalAgent]:
        """将 claude-mem agent 转换为专业代理"""
        agent_data = self.agents.get(agent_name)
        if not agent_data:
            return None
        
        adapter = self
        
        class ClaudeMemProfessionalAgent(ProfessionalAgent):
            def __init__(self, agent_data, adapter_ref):
                super().__init__(
                    agent_id=f"claude_mem_{agent_name}",
                    name=agent_data["name"],
                    description=agent_data["description"]
                )
                for skill in agent_data.get("skills", []):
                    self.add_skill(skill)
                for capability in agent_data.get("capabilities", []):
                    self.add_capability(capability)
                self._adapter = adapter_ref
            
            async def process_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
                """处理任务"""
                ctx = context or {}
                session_id = ctx.get("session_id", "default")
                
                if "存储" in task or "保存" in task or "store" in task.lower():
                    content = ctx.get("content", task)
                    summary = ctx.get("summary")
                    category = ctx.get("category", "general")
                    tags = ctx.get("tags", [])
                    return self._adapter.store_memory(session_id, content, summary, category, tags)
                
                elif "搜索" in task or "查找" in task or "search" in task.lower():
                    query = ctx.get("query", task)
                    limit = ctx.get("limit", 10)
                    return self._adapter.search_memories(query, limit)
                
                elif "时间线" in task or "timeline" in task.lower():
                    limit = ctx.get("limit", 20)
                    return self._adapter.get_timeline(session_id, limit)
                
                elif "观察" in task or "observation" in task.lower():
                    if "获取" in task or "get" in task.lower():
                        obs_ids = ctx.get("observation_ids", [])
                        return self._adapter.get_observations(obs_ids)
                    else:
                        tool_name = ctx.get("tool_name", "unknown")
                        observation = ctx.get("observation", task)
                        return self._adapter.store_observation(session_id, tool_name, observation)
                
                else:
                    return {
                        "status": "success",
                        "response": f"记忆代理已处理任务: {task}",
                        "agent_id": self.agent_id,
                        "available_operations": ["存储记忆", "搜索记忆", "获取时间线", "存储观察", "获取观察"]
                    }
        
        return ClaudeMemProfessionalAgent(agent_data, adapter)
    
    def register_all_agents(self):
        """注册所有 claude-mem agents"""
        agent_registry = get_agent_registry()
        for agent_name in self.agents:
            agent = self.convert_to_professional_agent(agent_name)
            if agent:
                agent_registry.register_agent(agent)
                logger.info(f"注册 Claude Mem Agent: {agent_name}")


_claude_mem_adapter = None

def get_claude_mem_adapter() -> ClaudeMemAdapter:
    """获取 Claude Mem 适配器实例"""
    global _claude_mem_adapter
    if _claude_mem_adapter is None:
        _claude_mem_adapter = ClaudeMemAdapter()
    return _claude_mem_adapter