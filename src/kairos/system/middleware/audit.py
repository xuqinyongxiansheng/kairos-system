#!/usr/bin/env python3
"""
审计日志中间件
从main.py拆分，API请求和认证事件的审计记录
"""

import json
import os
import threading
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import Request

logger = logging.getLogger(__name__)


class AuditLogger:
    """API审计日志记录器"""

    def __init__(self, log_file: str, enabled: bool = True):
        self.enabled = enabled
        self.log_file = log_file
        self._lock = threading.Lock()

        if enabled:
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)

    def log(self, event: Dict[str, Any]):
        """记录审计事件"""
        if not self.enabled:
            return

        event["timestamp"] = datetime.now(timezone.utc).isoformat()

        with self._lock:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event, ensure_ascii=False) + "\n")
            except Exception as e:
                logger.error("审计日志写入失败: %s", e)

    def log_request(self, request: Request, user_id: str = None, status_code: int = 200):
        """记录API请求"""
        self.log({
            "type": "api_request",
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params),
            "client_ip": self._get_client_ip(request),
            "user_id": user_id,
            "user_agent": request.headers.get("user-agent", ""),
            "status_code": status_code
        })

    def log_auth_event(
        self,
        event_type: str,
        user_id: str,
        client_ip: str,
        success: bool,
        detail: str = ""
    ):
        """记录认证事件"""
        self.log({
            "type": "auth_event",
            "event_type": event_type,
            "user_id": user_id,
            "client_ip": client_ip,
            "success": success,
            "detail": detail
        })

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """获取客户端真实IP"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
