#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
遗忘曲线数据库系统
将人类遗忘曲线理论与数据库存储机制结合
实现短期记忆压缩和长期记忆巩固

核心功能：
1. 遗忘曲线数据衰减（基于艾宾浩斯遗忘曲线）
2. 短期记忆压缩机制
3. 长期记忆巩固策略
4. 数据访问频率追踪
5. 自动数据生命周期管理
"""

import sqlite3
import os
import logging
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("ForgettingCurveDatabase")


class MemoryType(Enum):
    """记忆类型"""
    SENSORY = "sensory"        # 感觉记忆（毫秒级）
    SHORT_TERM = "short_term"  # 短期记忆（秒-分钟级）
    WORKING = "working"        # 工作记忆（分钟-小时级）
    LONG_TERM = "long_term"    # 长期记忆（天-年级）
    PERMANENT = "permanent"    # 永久记忆（不衰减）


class DataPriority(Enum):
    """数据优先级"""
    CRITICAL = 0    # 关键数据，永不删除
    HIGH = 1        # 高优先级，长期保留
    MEDIUM = 2      # 中等优先级，正常衰减
    LOW = 3         # 低优先级，快速衰减
    TEMPORARY = 4   # 临时数据，快速清理


@dataclass
class ForgettingCurveParams:
    """遗忘曲线参数（艾宾浩斯模型）"""
    # 艾宾浩斯遗忘曲线公式: R = e^(-t/S)
    # R = 记忆保持率, t = 时间, S = 记忆强度
    
    initial_strength: float = 1.0      # 初始记忆强度
    decay_rate: float = 0.3            # 衰减率（默认值，可调整）
    reinforcement_factor: float = 1.5  # 强化因子
    consolidation_threshold: float = 0.7  # 巩固阈值
    
    # 时间间隔参数（秒）
    review_intervals: List[int] = field(default_factory=lambda: [
        60,           # 1分钟后复习
        300,          # 5分钟后复习
        1800,         # 30分钟后复习
        3600,         # 1小时后复习
        86400,        # 1天后复习
        604800,       # 1周后复习
        2592000,      # 1个月后复习
    ])


@dataclass
class DataRecord:
    """数据记录"""
    id: str
    data_type: str
    content: str
    memory_type: str
    priority: int
    
    # 遗忘曲线相关
    strength: float = 1.0              # 当前记忆强度
    decay_rate: float = 0.3            # 个体衰减率
    
    # 访问统计
    access_count: int = 0              # 访问次数
    last_accessed: str = ""            # 最后访问时间
    last_reinforced: str = ""          # 最后强化时间
    
    # 时间戳
    created_at: str = ""
    updated_at: str = ""
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    # 压缩相关
    compressed: bool = False
    compressed_content: str = ""
    original_size: int = 0
    compressed_size: int = 0
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_accessed:
            self.last_accessed = self.created_at
        if not self.last_reinforced:
            self.last_reinforced = self.created_at
    
    def calculate_retention(self, current_time: datetime = None) -> float:
        """
        计算当前记忆保持率
        基于艾宾浩斯遗忘曲线: R = e^(-t/S)
        """
        if current_time is None:
            current_time = datetime.now()
        
        last_reinforced = datetime.fromisoformat(self.last_reinforced)
        time_elapsed = (current_time - last_reinforced).total_seconds()
        
        # 避免除零错误
        if self.strength <= 0:
            return 0.0
        
        # 艾宾浩斯遗忘曲线公式
        retention = math.exp(-time_elapsed / (self.strength * 3600))  # 转换为小时
        
        # 优先级调整
        priority_factor = 1.0 - (self.priority * 0.1)
        retention *= priority_factor
        
        return max(0.0, min(1.0, retention))
    
    def should_review(self, current_time: datetime = None) -> bool:
        """判断是否需要复习（强化）"""
        retention = self.calculate_retention(current_time)
        return retention < 0.7  # 保持率低于70%需要复习
    
    def reinforce(self, factor: float = 1.5):
        """强化记忆（复习后增强）"""
        self.strength *= factor
        self.access_count += 1
        self.last_accessed = datetime.now().isoformat()
        self.last_reinforced = datetime.now().isoformat()
    
    def decay(self, current_time: datetime = None) -> float:
        """执行衰减，返回新的保持率"""
        retention = self.calculate_retention(current_time)
        
        # 更新强度
        self.strength *= retention
        
        return retention


class ShortTermMemoryCompressor:
    """
    短期记忆压缩器
    模拟人类短期记忆的有限容量和信息压缩机制
    """
    
    def __init__(self, capacity: int = 7):
        """
        初始化压缩器
        
        Args:
            capacity: 短期记忆容量（人类约7±2）
        """
        self.capacity = capacity
        self.compression_strategies = {
            "chunking": self._chunk_compression,
            "summarization": self._summary_compression,
            "abstraction": self._abstraction_compression,
            "indexing": self._index_compression
        }
    
    def compress(self, content: str, strategy: str = "chunking") -> Tuple[str, Dict[str, Any]]:
        """
        压缩内容
        
        Args:
            content: 原始内容
            strategy: 压缩策略
        
        Returns:
            (压缩后内容, 压缩元数据)
        """
        if strategy not in self.compression_strategies:
            strategy = "chunking"
        
        return self.compression_strategies[strategy](content)
    
    def _chunk_compression(self, content: str) -> Tuple[str, Dict[str, Any]]:
        """分块压缩策略"""
        # 将长内容分成多个块
        chunk_size = 100
        chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
        
        # 只保留关键块（首块和尾块）
        if len(chunks) > 2:
            compressed = chunks[0] + "..." + chunks[-1]
            metadata = {
                "strategy": "chunking",
                "original_chunks": len(chunks),
                "retained_chunks": 2,
                "compression_ratio": len(compressed) / len(content)
            }
        else:
            compressed = content
            metadata = {"strategy": "chunking", "compression_ratio": 1.0}
        
        return compressed, metadata
    
    def _summary_compression(self, content: str) -> Tuple[str, Dict[str, Any]]:
        """摘要压缩策略"""
        # 提取关键信息
        words = content.split()
        
        if len(words) > 20:
            # 保留前20%和后10%的词
            front_count = int(len(words) * 0.2)
            back_count = int(len(words) * 0.1)
            
            compressed_words = words[:front_count] + ["..."] + words[-back_count:]
            compressed = " ".join(compressed_words)
            
            metadata = {
                "strategy": "summarization",
                "original_words": len(words),
                "retained_words": front_count + back_count,
                "compression_ratio": len(compressed) / len(content)
            }
        else:
            compressed = content
            metadata = {"strategy": "summarization", "compression_ratio": 1.0}
        
        return compressed, metadata
    
    def _abstraction_compression(self, content: str) -> Tuple[str, Dict[str, Any]]:
        """抽象压缩策略"""
        # 提取结构和模式
        lines = content.split('\n')
        
        if len(lines) > 5:
            # 保留结构信息
            compressed = f"[{len(lines)}行数据] {lines[0][:50]}... {lines[-1][:50]}"
            metadata = {
                "strategy": "abstraction",
                "original_lines": len(lines),
                "compression_ratio": len(compressed) / len(content)
            }
        else:
            compressed = content
            metadata = {"strategy": "abstraction", "compression_ratio": 1.0}
        
        return compressed, metadata
    
    def _index_compression(self, content: str) -> Tuple[str, Dict[str, Any]]:
        """索引压缩策略"""
        # 创建关键词索引
        words = content.split()
        unique_words = list(set(words))
        
        if len(unique_words) < len(words) * 0.5:
            # 有大量重复词，创建索引
            compressed = f"[索引:{len(unique_words)}唯一词] {' '.join(unique_words[:20])}"
            metadata = {
                "strategy": "indexing",
                "total_words": len(words),
                "unique_words": len(unique_words),
                "compression_ratio": len(compressed) / len(content)
            }
        else:
            compressed = content
            metadata = {"strategy": "indexing", "compression_ratio": 1.0}
        
        return compressed, metadata
    
    def decompress(self, compressed_content: str, metadata: Dict[str, Any], 
                  original_content: str = None) -> str:
        """
        解压缩内容（如果保留了原始内容）
        
        注意：某些压缩策略是有损的，无法完全还原
        """
        if original_content:
            return original_content
        
        # 无法完全还原，返回压缩内容
        return compressed_content


class ForgettingCurveDatabase:
    """
    遗忘曲线数据库
    将人类遗忘曲线理论与数据库存储机制结合
    """
    
    def __init__(self, db_path: str = "data/forgetting_curve.db", config: Dict = None):
        """初始化遗忘曲线数据库"""
        self.db_path = db_path
        self.config = config or {}
        
        # 遗忘曲线参数
        self.curve_params = ForgettingCurveParams()
        
        # 短期记忆压缩器
        self.compressor = ShortTermMemoryCompressor(
            capacity=self.config.get("short_term_capacity", 7)
        )
        
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        # 初始化数据库
        self._initialize_database()
        
        # 启动后台维护任务
        self._maintenance_running = True
        self._maintenance_thread = threading.Thread(target=self._maintenance_loop, daemon=True)
        self._maintenance_thread.start()
        
        logger.info(f"遗忘曲线数据库初始化完成: {db_path}")
    
    def _initialize_database(self):
        """初始化数据库表结构"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        self.connection = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        self.connection.row_factory = sqlite3.Row
        
        # 创建数据表
        self._create_tables()
    
    def _create_tables(self):
        """创建数据库表"""
        # 主数据表
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS memory_data (
                id TEXT PRIMARY KEY,
                data_type TEXT NOT NULL,
                content TEXT,
                memory_type TEXT DEFAULT 'short_term',
                priority INTEGER DEFAULT 2,
                
                -- 遗忘曲线字段
                strength REAL DEFAULT 1.0,
                decay_rate REAL DEFAULT 0.3,
                
                -- 访问统计
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP,
                last_reinforced TIMESTAMP,
                
                -- 时间戳
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- 元数据
                metadata TEXT,
                tags TEXT,
                
                -- 压缩相关
                compressed INTEGER DEFAULT 0,
                compressed_content TEXT,
                original_size INTEGER DEFAULT 0,
                compressed_size INTEGER DEFAULT 0
            )
        """)
        
        # 访问日志表
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_id TEXT NOT NULL,
                access_type TEXT NOT NULL,
                retention_before REAL,
                retention_after REAL,
                accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (data_id) REFERENCES memory_data(id)
            )
        """)
        
        # 强化记录表
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS reinforcement_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_id TEXT NOT NULL,
                strength_before REAL,
                strength_after REAL,
                reinforcement_type TEXT,
                reinforced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (data_id) REFERENCES memory_data(id)
            )
        """)
        
        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_data(memory_type)",
            "CREATE INDEX IF NOT EXISTS idx_priority ON memory_data(priority)",
            "CREATE INDEX IF NOT EXISTS idx_strength ON memory_data(strength)",
            "CREATE INDEX IF NOT EXISTS idx_last_accessed ON memory_data(last_accessed)",
            "CREATE INDEX IF NOT EXISTS idx_created_at ON memory_data(created_at)"
        ]
        
        for index_sql in indexes:
            self.connection.execute(index_sql)
        
        self.connection.commit()
        logger.info("数据库表创建完成")
    
    async def store(self, data_id: str, content: str, data_type: str = "general",
                   memory_type: str = "short_term", priority: int = 2,
                   metadata: Dict = None, tags: List[str] = None,
                   compress: bool = True) -> Dict[str, Any]:
        """
        存储数据
        
        Args:
            data_id: 数据ID
            content: 数据内容
            data_type: 数据类型
            memory_type: 记忆类型
            priority: 优先级
            metadata: 元数据
            tags: 标签
            compress: 是否压缩
        
        Returns:
            存储结果
        """
        try:
            now = datetime.now().isoformat()
            
            # 根据记忆类型决定是否压缩
            compressed = False
            compressed_content = None
            original_size = len(content)
            compressed_size = original_size
            
            if compress and memory_type == MemoryType.SHORT_TERM.value:
                compressed_content, compression_meta = self.compressor.compress(content)
                compressed = True
                compressed_size = len(compressed_content)
            
            # 插入数据
            self.connection.execute("""
                INSERT OR REPLACE INTO memory_data 
                (id, data_type, content, memory_type, priority, strength, decay_rate,
                 access_count, last_accessed, last_reinforced, created_at, updated_at,
                 metadata, tags, compressed, compressed_content, original_size, compressed_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data_id, data_type, content, memory_type, priority,
                self.curve_params.initial_strength,
                self.curve_params.decay_rate,
                0, now, now, now, now,
                json.dumps(metadata or {}, ensure_ascii=False),
                json.dumps(tags or [], ensure_ascii=False),
                1 if compressed else 0,
                compressed_content,
                original_size,
                compressed_size
            ))
            
            self.connection.commit()
            
            logger.info(f"数据存储成功: {data_id} ({memory_type})")
            
            return {
                "success": True,
                "data_id": data_id,
                "memory_type": memory_type,
                "compressed": compressed,
                "original_size": original_size,
                "compressed_size": compressed_size
            }
            
        except Exception as e:
            logger.error(f"数据存储失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def retrieve(self, data_id: str, reinforce: bool = True) -> Dict[str, Any]:
        """
        检索数据
        
        Args:
            data_id: 数据ID
            reinforce: 是否强化记忆
        
        Returns:
            数据内容
        """
        try:
            cursor = self.connection.execute(
                "SELECT * FROM memory_data WHERE id = ?", (data_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return {"success": False, "error": "数据不存在"}
            
            # 计算当前保持率
            record = self._row_to_record(row)
            retention = record.calculate_retention()
            
            # 记录访问日志
            self._log_access(data_id, "retrieve", retention, retention)
            
            if reinforce:
                # 强化记忆
                record.reinforce(self.curve_params.reinforcement_factor)
                
                # 更新数据库
                self.connection.execute("""
                    UPDATE memory_data 
                    SET strength = ?, access_count = ?, last_accessed = ?, last_reinforced = ?
                    WHERE id = ?
                """, (record.strength, record.access_count, record.last_accessed, 
                      record.last_reinforced, data_id))
                
                self.connection.commit()
                
                # 记录强化日志
                self._log_reinforcement(data_id, retention, record.strength, "access")
            
            # 处理压缩内容
            content = record.content
            if record.compressed and record.compressed_content:
                content = record.compressed_content
            
            return {
                "success": True,
                "data_id": data_id,
                "content": content,
                "retention": retention,
                "strength": record.strength,
                "memory_type": record.memory_type,
                "compressed": record.compressed
            }
            
        except Exception as e:
            logger.error(f"数据检索失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def search(self, query: str, memory_type: str = None,
                    min_retention: float = 0.0, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索数据
        
        Args:
            query: 搜索查询
            memory_type: 记忆类型过滤
            min_retention: 最小保持率过滤
            limit: 返回数量限制
        
        Returns:
            搜索结果列表
        """
        try:
            sql = "SELECT * FROM memory_data WHERE content LIKE ?"
            params = [f"%{query}%"]
            
            if memory_type:
                sql += " AND memory_type = ?"
                params.append(memory_type)
            
            sql += " ORDER BY strength DESC, last_accessed DESC LIMIT ?"
            params.append(limit)
            
            cursor = self.connection.execute(sql, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                record = self._row_to_record(row)
                retention = record.calculate_retention()
                
                if retention >= min_retention:
                    results.append({
                        "data_id": record.id,
                        "content": record.content[:200] + "..." if len(record.content) > 200 else record.content,
                        "memory_type": record.memory_type,
                        "retention": retention,
                        "strength": record.strength,
                        "access_count": record.access_count
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"数据搜索失败: {e}")
            return []
    
    async def consolidate_memories(self) -> Dict[str, Any]:
        """
        记忆巩固
        将高频访问的短期记忆转化为长期记忆
        """
        try:
            # 查找需要巩固的短期记忆
            cursor = self.connection.execute("""
                SELECT * FROM memory_data 
                WHERE memory_type = 'short_term' 
                AND access_count >= 3 
                AND strength >= ?
            """, (self.curve_params.consolidation_threshold,))
            
            rows = cursor.fetchall()
            consolidated_count = 0
            
            for row in rows:
                record = self._row_to_record(row)
                
                # 转化为长期记忆
                self.connection.execute("""
                    UPDATE memory_data 
                    SET memory_type = 'long_term', 
                        decay_rate = decay_rate * 0.5,
                        updated_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), record.id))
                
                consolidated_count += 1
            
            self.connection.commit()
            
            logger.info(f"记忆巩固完成，转化 {consolidated_count} 条短期记忆为长期记忆")
            
            return {
                "success": True,
                "consolidated_count": consolidated_count
            }
            
        except Exception as e:
            logger.error(f"记忆巩固失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def apply_forgetting_curve(self) -> Dict[str, Any]:
        """
        应用遗忘曲线
        对所有数据进行衰减处理
        """
        try:
            cursor = self.connection.execute(
                "SELECT * FROM memory_data WHERE memory_type != 'permanent'"
            )
            rows = cursor.fetchall()
            
            forgotten_count = 0
            updated_count = 0
            
            for row in rows:
                record = self._row_to_record(row)
                retention = record.decay()
                
                # 更新强度
                self.connection.execute("""
                    UPDATE memory_data SET strength = ? WHERE id = ?
                """, (record.strength, record.id))
                
                updated_count += 1
                
                # 检查是否需要遗忘
                if retention < 0.1 and record.priority > DataPriority.HIGH.value:
                    # 删除低保持率的低优先级数据
                    self.connection.execute("DELETE FROM memory_data WHERE id = ?", (record.id,))
                    forgotten_count += 1
            
            self.connection.commit()
            
            logger.info(f"遗忘曲线应用完成，更新 {updated_count} 条，遗忘 {forgotten_count} 条")
            
            return {
                "success": True,
                "updated_count": updated_count,
                "forgotten_count": forgotten_count
            }
            
        except Exception as e:
            logger.error(f"应用遗忘曲线失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _maintenance_loop(self):
        """后台维护循环"""
        import time
        
        while self._maintenance_running:
            try:
                # 每小时执行一次维护
                time.sleep(3600)
                
                # 应用遗忘曲线
                import asyncio
                asyncio.run(self.apply_forgetting_curve())
                
                # 执行记忆巩固
                asyncio.run(self.consolidate_memories())
                
            except Exception as e:
                logger.error(f"维护任务执行失败: {e}")
    
    def _row_to_record(self, row: sqlite3.Row) -> DataRecord:
        """将数据库行转换为记录对象"""
        return DataRecord(
            id=row["id"],
            data_type=row["data_type"],
            content=row["content"],
            memory_type=row["memory_type"],
            priority=row["priority"],
            strength=row["strength"],
            decay_rate=row["decay_rate"],
            access_count=row["access_count"],
            last_accessed=row["last_accessed"],
            last_reinforced=row["last_reinforced"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            tags=json.loads(row["tags"]) if row["tags"] else [],
            compressed=bool(row["compressed"]),
            compressed_content=row["compressed_content"],
            original_size=row["original_size"],
            compressed_size=row["compressed_size"]
        )
    
    def _log_access(self, data_id: str, access_type: str, 
                   retention_before: float, retention_after: float):
        """记录访问日志"""
        self.connection.execute("""
            INSERT INTO access_log (data_id, access_type, retention_before, retention_after)
            VALUES (?, ?, ?, ?)
        """, (data_id, access_type, retention_before, retention_after))
        self.connection.commit()
    
    def _log_reinforcement(self, data_id: str, strength_before: float,
                          strength_after: float, reinforcement_type: str):
        """记录强化日志"""
        self.connection.execute("""
            INSERT INTO reinforcement_log 
            (data_id, strength_before, strength_after, reinforcement_type)
            VALUES (?, ?, ?, ?)
        """, (data_id, strength_before, strength_after, reinforcement_type))
        self.connection.commit()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            # 总数据量
            cursor = self.connection.execute("SELECT COUNT(*) FROM memory_data")
            total_count = cursor.fetchone()[0]
            
            # 按记忆类型统计
            cursor = self.connection.execute("""
                SELECT memory_type, COUNT(*) as count 
                FROM memory_data GROUP BY memory_type
            """)
            by_type = {row["memory_type"]: row["count"] for row in cursor.fetchall()}
            
            # 平均保持率
            cursor = self.connection.execute("SELECT AVG(strength) FROM memory_data")
            avg_strength = cursor.fetchone()[0] or 0
            
            # 压缩统计
            cursor = self.connection.execute("""
                SELECT COUNT(*), SUM(original_size), SUM(compressed_size) 
                FROM memory_data WHERE compressed = 1
            """)
            row = cursor.fetchone()
            compressed_count = row[0] or 0
            total_original = row[1] or 0
            total_compressed = row[2] or 0
            
            compression_ratio = total_compressed / total_original if total_original > 0 else 1.0
            
            return {
                "total_records": total_count,
                "by_memory_type": by_type,
                "average_strength": round(avg_strength, 3),
                "compressed_records": compressed_count,
                "compression_ratio": round(compression_ratio, 3),
                "storage_saved": total_original - total_compressed
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"error": str(e)}
    
    def close(self):
        """关闭数据库"""
        self._maintenance_running = False
        if self.connection:
            self.connection.close()
            logger.info("遗忘曲线数据库已关闭")


# 全局实例
_forgetting_curve_db = None


def get_forgetting_curve_db(db_path: str = "data/forgetting_curve.db", 
                           config: Dict = None) -> ForgettingCurveDatabase:
    """获取遗忘曲线数据库实例"""
    global _forgetting_curve_db
    
    if _forgetting_curve_db is None:
        _forgetting_curve_db = ForgettingCurveDatabase(db_path, config)
    
    return _forgetting_curve_db
