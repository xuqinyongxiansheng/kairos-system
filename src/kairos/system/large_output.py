"""
大输出处理模块
借鉴 cc-haha-main 的大输出持久化模式：
超过阈值的输出自动持久化到磁盘，返回文件路径 + 前 N 字预览
"""

import os
import time
import hashlib
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger("LargeOutputHandler")

DEFAULT_SIZE_THRESHOLD = 10240
DEFAULT_PREVIEW_LENGTH = 200
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "large_outputs")


@dataclass
class ProcessedOutput:
    content: str
    is_truncated: bool
    preview: str
    file_path: Optional[str]
    total_size: int
    saved_size: int


class LargeOutputHandler:
    """大输出处理器"""

    def __init__(self, size_threshold: int = DEFAULT_SIZE_THRESHOLD,
                 preview_length: int = DEFAULT_PREVIEW_LENGTH,
                 output_dir: str = None):
        self.size_threshold = size_threshold
        self.preview_length = preview_length
        self.output_dir = output_dir or OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    def process(self, content: str, context: Dict[str, Any] = None) -> ProcessedOutput:
        """处理输出内容，大输出自动持久化到磁盘"""
        total_size = len(content.encode('utf-8'))

        if total_size <= self.size_threshold:
            return ProcessedOutput(
                content=content,
                is_truncated=False,
                preview=content[:self.preview_length],
                file_path=None,
                total_size=total_size,
                saved_size=0,
            )

        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:12]
        timestamp = int(time.time())
        context_suffix = ""
        if context and context.get("model"):
            context_suffix = f"_{context['model'].replace(':', '_')}"

        filename = f"output_{timestamp}_{content_hash}{context_suffix}.txt"
        file_path = os.path.join(self.output_dir, filename)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"大输出已持久化: {file_path} ({total_size} 字节)")

            preview = content[:self.preview_length]
            truncation_notice = (
                f"\n\n[输出过大，已保存到文件: {file_path}]"
                f"\n[总大小: {total_size:,} 字节，预览前 {self.preview_length} 字符]"
            )

            return ProcessedOutput(
                content=preview + truncation_notice,
                is_truncated=True,
                preview=preview,
                file_path=file_path,
                total_size=total_size,
                saved_size=total_size,
            )
        except Exception as e:
            logger.error(f"大输出持久化失败: {e}")
            return ProcessedOutput(
                content=content[:self.size_threshold] + "\n\n[输出截断，持久化失败]",
                is_truncated=True,
                preview=content[:self.preview_length],
                file_path=None,
                total_size=total_size,
                saved_size=0,
            )

    def read_full_output(self, file_path: str) -> Optional[str]:
        """从磁盘读取完整输出"""
        if not file_path or not os.path.exists(file_path):
            return None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"读取大输出文件失败: {e}")
            return None

    def cleanup_old_outputs(self, max_age_hours: int = 24):
        """清理过期的大输出文件"""
        if not os.path.exists(self.output_dir):
            return 0

        now = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned = 0

        for filename in os.listdir(self.output_dir):
            if not filename.startswith("output_") or not filename.endswith(".txt"):
                continue
            file_path = os.path.join(self.output_dir, filename)
            try:
                if now - os.path.getmtime(file_path) > max_age_seconds:
                    os.remove(file_path)
                    cleaned += 1
            except Exception:
                pass

        if cleaned > 0:
            logger.info(f"清理过期大输出文件: {cleaned} 个")

        return cleaned


_large_output_handler: Optional[LargeOutputHandler] = None


def get_large_output_handler() -> LargeOutputHandler:
    """获取大输出处理器单例"""
    global _large_output_handler
    if _large_output_handler is None:
        _large_output_handler = LargeOutputHandler()
    return _large_output_handler
