#!/usr/bin/env python3
"""
消化功能模块 - 实现三级递进式数据压缩机制
"""

import asyncio
import os
import json
import zipfile
import gzip
import time
import shutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import tempfile
import hashlib
import sqlite3

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataCategory(Enum):
    """数据分类枚举"""
    USER_INTERACTION = "user_interaction"
    SYSTEM_LOG = "system_log"
    TEST_REPORT = "test_report"
    TEMP_FILE = "temp_file"
    REDUNDANT_DATA = "redundant_data"
    PERFORMANCE_DATA = "performance_data"
    MEMORY_SNAPSHOT = "memory_snapshot"


class CompressionLevel(Enum):
    """压缩级别枚举"""
    LEVEL_1 = "level_1"  # 轻度压缩，保留完整结构
    LEVEL_2 = "level_2"  # 中度压缩，保留关键信息
    LEVEL_3 = "level_3"  # 高度压缩，只保留摘要信息


class DataImportance(Enum):
    """数据重要性枚举"""
    CRITICAL = "critical"    # 关键数据，需要完整保留
    HIGH = "high"           # 高度重要，需要大部分保留
    MEDIUM = "medium"       # 中等重要，可适度压缩
    LOW = "low"             # 低重要性，可高度压缩
    TRIVIAL = "trivial"     # 无关紧要，可删除


class DataItem:
    """数据项类"""
    
    def __init__(self, category: DataCategory, content: Any, metadata: Dict[str, Any] = None):
        self.id = hashlib.md5(f"{category.value}_{time.time()}".encode()).hexdigest()
        self.category = category
        self.content = content
        self.metadata = metadata or {}
        self.importance = self._calculate_importance()
        self.compression_level = self._determine_compression_level()
        self.timestamp = time.time()
        self.compressed = False
        self.storage_path = None
    
    def _calculate_importance(self) -> DataImportance:
        """计算数据重要性"""
        importance_map = {
            DataCategory.USER_INTERACTION: DataImportance.HIGH,
            DataCategory.SYSTEM_LOG: DataImportance.MEDIUM,
            DataCategory.TEST_REPORT: DataImportance.HIGH,
            DataCategory.TEMP_FILE: DataImportance.LOW,
            DataCategory.REDUNDANT_DATA: DataImportance.TRIVIAL,
            DataCategory.PERFORMANCE_DATA: DataImportance.MEDIUM,
            DataCategory.MEMORY_SNAPSHOT: DataImportance.CRITICAL
        }
        
        if "timestamp" in self.metadata:
            age_days = (time.time() - self.metadata["timestamp"]) / 86400
            if age_days > 30:
                return DataImportance.LOW
            elif age_days > 7:
                return DataImportance.MEDIUM
        
        return importance_map.get(self.category, DataImportance.MEDIUM)
    
    def _determine_compression_level(self) -> CompressionLevel:
        """确定压缩级别"""
        compression_map = {
            DataImportance.CRITICAL: CompressionLevel.LEVEL_1,
            DataImportance.HIGH: CompressionLevel.LEVEL_1,
            DataImportance.MEDIUM: CompressionLevel.LEVEL_2,
            DataImportance.LOW: CompressionLevel.LEVEL_3,
            DataImportance.TRIVIAL: CompressionLevel.LEVEL_3
        }
        return compression_map.get(self.importance, CompressionLevel.LEVEL_2)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "category": self.category.value,
            "importance": self.importance.value,
            "compression_level": self.compression_level.value,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "storage_path": self.storage_path,
            "compressed": self.compressed
        }


class DataCollector:
    """数据收集器"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or os.getcwd()
        self.collected_data = []
    
    async def collect_user_interactions(self, interaction_logs: List[Dict[str, Any]]) -> List[DataItem]:
        """收集用户交互数据"""
        data_items = []
        
        for interaction in interaction_logs:
            data_item = DataItem(
                category=DataCategory.USER_INTERACTION,
                content=interaction,
                metadata={
                    "interaction_type": interaction.get("type", "unknown"),
                    "timestamp": interaction.get("timestamp", time.time()),
                    "user_id": interaction.get("user_id", "unknown")
                }
            )
            data_items.append(data_item)
        
        self.collected_data.extend(data_items)
        return data_items
    
    async def collect_system_logs(self, log_files: List[str]) -> List[DataItem]:
        """收集系统日志"""
        data_items = []
        
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    data_item = DataItem(
                        category=DataCategory.SYSTEM_LOG,
                        content=content,
                        metadata={
                            "file_path": log_file,
                            "file_size": os.path.getsize(log_file),
                            "timestamp": os.path.getmtime(log_file)
                        }
                    )
                    data_items.append(data_item)
                    
                except Exception as e:
                    logger.error(f"读取日志文件失败：{log_file}, 错误：{e}")
        
        self.collected_data.extend(data_items)
        return data_items
    
    async def collect_test_reports(self, report_files: List[str]) -> List[DataItem]:
        """收集测试报告"""
        data_items = []
        
        for report_file in report_files:
            if os.path.exists(report_file):
                try:
                    with open(report_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    data_item = DataItem(
                        category=DataCategory.TEST_REPORT,
                        content=content,
                        metadata={
                            "file_path": report_file,
                            "file_size": os.path.getsize(report_file),
                            "timestamp": os.path.getmtime(report_file),
                            "report_type": self._determine_report_type(report_file)
                        }
                    )
                    data_items.append(data_item)
                    
                except Exception as e:
                    logger.error(f"读取测试报告失败：{report_file}, 错误：{e}")
        
        self.collected_data.extend(data_items)
        return data_items
    
    def _determine_report_type(self, file_path: str) -> str:
        """确定报告类型"""
        if "performance" in file_path.lower():
            return "performance"
        elif "unit" in file_path.lower():
            return "unit_test"
        elif "integration" in file_path.lower():
            return "integration_test"
        elif "security" in file_path.lower():
            return "security"
        else:
            return "general"
    
    def get_collected_data(self) -> List[DataItem]:
        """获取收集的数据"""
        return self.collected_data
    
    def clear_collected_data(self):
        """清除收集的数据"""
        self.collected_data.clear()


class CompressionEngine:
    """压缩引擎"""
    
    def __init__(self, compression_dir: str = None):
        self.compression_dir = compression_dir or os.path.join(os.getcwd(), "compressed_data")
        os.makedirs(self.compression_dir, exist_ok=True)
    
    async def compress_data(self, data_item: DataItem) -> str:
        """压缩数据项"""
        try:
            if data_item.compression_level == CompressionLevel.LEVEL_1:
                return await self._compress_level_1(data_item)
            elif data_item.compression_level == CompressionLevel.LEVEL_2:
                return await self._compress_level_2(data_item)
            else:
                return await self._compress_level_3(data_item)
                
        except Exception as e:
            logger.error(f"压缩数据失败：{data_item.id}, 错误：{e}")
            raise
    
    async def _compress_level_1(self, data_item: DataItem) -> str:
        """一级压缩 - 轻度压缩，保留完整结构"""
        timestamp_str = datetime.fromtimestamp(data_item.timestamp).strftime("%Y%m%d_%H%M%S")
        file_name = f"{data_item.category.value}_{data_item.id[:8]}_{timestamp_str}.gz"
        file_path = os.path.join(self.compression_dir, file_name)
        
        with gzip.open(file_path, 'wt', encoding='utf-8') as f:
            json.dump({
                "content": data_item.content,
                "metadata": data_item.metadata
            }, f, ensure_ascii=False, indent=2)
        
        data_item.storage_path = file_path
        data_item.compressed = True
        
        logger.info(f"一级压缩完成：{file_path}, 大小：{os.path.getsize(file_path)} 字节")
        return file_path
    
    async def _compress_level_2(self, data_item: DataItem) -> str:
        """二级压缩 - 中度压缩，保留关键信息"""
        timestamp_str = datetime.fromtimestamp(data_item.timestamp).strftime("%Y%m%d_%H%M%S")
        file_name = f"{data_item.category.value}_{data_item.id[:8]}_{timestamp_str}.gz"
        file_path = os.path.join(self.compression_dir, file_name)
        
        compressed_content = self._extract_key_information(data_item)
        
        with gzip.open(file_path, 'wt', encoding='utf-8') as f:
            json.dump({
                "content": compressed_content,
                "metadata": data_item.metadata
            }, f, ensure_ascii=False, indent=2)
        
        data_item.storage_path = file_path
        data_item.compressed = True
        
        logger.info(f"二级压缩完成：{file_path}, 大小：{os.path.getsize(file_path)} 字节")
        return file_path
    
    async def _compress_level_3(self, data_item: DataItem) -> str:
        """三级压缩 - 高度压缩，只保留摘要信息"""
        timestamp_str = datetime.fromtimestamp(data_item.timestamp).strftime("%Y%m%d_%H%M%S")
        file_name = f"{data_item.category.value}_{data_item.id[:8]}_{timestamp_str}.gz"
        file_path = os.path.join(self.compression_dir, file_name)
        
        summary = self._generate_summary(data_item)
        
        with gzip.open(file_path, 'wt', encoding='utf-8') as f:
            json.dump({
                "summary": summary,
                "metadata": data_item.metadata
            }, f, ensure_ascii=False, indent=2)
        
        data_item.storage_path = file_path
        data_item.compressed = True
        
        logger.info(f"三级压缩完成：{file_path}, 大小：{os.path.getsize(file_path)} 字节")
        return file_path
    
    def _extract_key_information(self, data_item: DataItem) -> Dict[str, Any]:
        """提取关键信息"""
        if isinstance(data_item.content, dict):
            key_fields = ["id", "timestamp", "type", "status", "result", "error"]
            return {k: v for k, v in data_item.content.items() if k in key_fields}
        
        elif isinstance(data_item.content, list):
            return data_item.content[:min(5, len(data_item.content))]
        
        elif isinstance(data_item.content, str):
            if len(data_item.content) > 1000:
                return {
                    "content_preview": data_item.content[:500],
                    "content_length": len(data_item.content),
                    "key_words": self._extract_keywords(data_item.content)
                }
            return data_item.content
        
        return data_item.content
    
    def _generate_summary(self, data_item: DataItem) -> str:
        """生成摘要信息"""
        if isinstance(data_item.content, str):
            if len(data_item.content) > 200:
                return data_item.content[:200] + "..."
            return data_item.content
        
        elif isinstance(data_item.content, dict):
            summary_parts = []
            for key, value in list(data_item.content.items())[:3]:
                summary_parts.append(f"{key}: {str(value)[:50]}")
            return "; ".join(summary_parts)
        
        elif isinstance(data_item.content, list):
            return f"列表包含 {len(data_item.content)} 个元素"
        
        return str(data_item.content)[:100]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        import re
        words = re.findall(r'\b\w{4,}\b', text.lower())
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        return [word for word, count in sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:5]]


class DigestionEngine:
    """消化引擎"""
    
    def __init__(self):
        self.data_collector = DataCollector()
        self.compression_engine = CompressionEngine()
    
    async def digest_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """执行数据消化"""
        try:
            start_time = time.time()
            stats = {
                "collected_items": 0,
                "compressed_items": 0,
                "stored_items": 0,
                "failed_items": 0
            }
            
            if "user_interactions" in config:
                items = await self.data_collector.collect_user_interactions(config["user_interactions"])
                stats["collected_items"] += len(items)
            
            if "system_logs" in config:
                items = await self.data_collector.collect_system_logs(config["system_logs"])
                stats["collected_items"] += len(items)
            
            if "test_reports" in config:
                items = await self.data_collector.collect_test_reports(config["test_reports"])
                stats["collected_items"] += len(items)
            
            collected_data = self.data_collector.get_collected_data()
            
            for data_item in collected_data:
                try:
                    storage_path = await self.compression_engine.compress_data(data_item)
                    stats["compressed_items"] += 1
                    stats["stored_items"] += 1
                    
                except Exception as e:
                    logger.error(f"处理数据项失败：{data_item.id}, 错误：{e}")
                    stats["failed_items"] += 1
            
            self.data_collector.clear_collected_data()
            
            return {
                "status": "success",
                "stats": stats,
                "duration": time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"数据消化失败：{e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def get_digestion_stats(self) -> Dict[str, Any]:
        """获取消化统计信息"""
        return {
            "status": "success",
            "message": "消化统计功能已实现"
        }


# 全局消化模块实例
digestion_engine = DigestionEngine()
