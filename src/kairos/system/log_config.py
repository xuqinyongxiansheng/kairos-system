#!/usr/bin/env python3
"""
鸿蒙小雨 v4.1 结构化日志配置
统一日志格式、多输出目标、动态级别调整

使用方式:
    from kairos.system.log_config import setup_logging
    setup_logging()
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Optional

try:
    from kairos.system.config import settings
except Exception:
    settings = None


class ColorFormatter(logging.Formatter):
    """终端彩色日志格式化器"""

    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{color}{record.levelname:<8}{self.RESET}"
        return super().format(record)


class JsonFormatter(logging.Formatter):
    """JSON结构化日志格式化器（适合生产环境/ELK）"""

    def format(self, record):
        import json
        from datetime import datetime

        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info and record.exc_info[0] is not None:
            log_obj["exception"] = self.formatException(record.exc_info)

        extra = {
            k: v for k, v in record.__dict__.items()
            if k not in (
                'name', 'msg', 'args', 'created', 'filename',
                'funcName', 'levelname', 'levelno', 'module',
                'pathname', 'process', 'processName',
                'thread', 'threadName', 'exc_info', 'exc_text',
                'stack_info', 'message'
            )
        }
        if extra:
            log_obj["extra"] = extra

        return json.dumps(log_obj, ensure_ascii=False, default=str)


# 统一日志格式模板
CONSOLE_FORMAT = "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s"
FILE_FORMAT = "%(asctime)s | %(name)-20s | %(levelname)-8s | %(module)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    console: bool = True,
    json_output: bool = False
):
    """初始化全局日志系统

    Args:
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
        log_file: 日志文件路径
        console: 是否输出到控制台
        json_output: 是否使用JSON格式（生产环境推荐）
    """
    root_logger = logging.getLogger()

    # 从配置读取默认值
    if settings is not None:
        default_level = settings.logging.level.upper()
        default_file = settings.logging.file_path
        use_console = settings.logging.console_output
        max_size = settings.logging.max_size_mb * 1024 * 1024
        backup_count = settings.logging.backup_count
    else:
        default_level = "INFO"
        default_file = "./log/hmyx.log"
        use_console = True
        max_size = 50 * 1024 * 1024
        backup_count = 5

    log_level = level or default_level
    file_path = log_file or default_file

    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # 清除已有处理器（避免重复）
    root_logger.handlers.clear()

    # 控制台处理器
    if console and use_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        if json_output:
            console_handler.setFormatter(JsonFormatter())
        else:
            console_handler.setFormatter(ColorFormatter(CONSOLE_FORMAT, datefmt=DATE_FORMAT))
        root_logger.addHandler(console_handler)

    # 文件处理器
    if file_path:
        log_dir = Path(file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            filename=file_path,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(FILE_FORMAT, datefmt=DATE_FORMAT))
        root_logger.addHandler(file_handler)

    # 降低第三方库日志级别
    for noisy in ["uvicorn.access", "uvicorn.error", "httpx", "httpcore"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "日志系统初始化完成 | 级别:%s | 文件:%s | 控制台:%s",
        log_level, file_path, console
    )


def get_logger(name: str) -> logging.Logger:
    """获取命名日志器

    Args:
        name: 模块名称（通常用__name__）

    Returns:
        Logger实例
    """
    return logging.getLogger(name)
