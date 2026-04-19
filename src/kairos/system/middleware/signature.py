#!/usr/bin/env python3
"""
签名验证中间件
从main.py拆分，HMAC-SHA256请求签名验证
支持Nonce防重放、签名生成
"""

import hmac
import hashlib
import time
import secrets
import threading
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import Request


class SignatureVerifier:
    """HMAC-SHA256请求签名验证器"""

    def __init__(self, secret: str = "", max_skew: int = 300):
        self._secret: bytes = secret.encode() if secret else b""
        self._max_skew: int = max_skew
        self._nonces: defaultdict = defaultdict(float)
        self._lock = threading.Lock()
        self._max_nonces: int = 10000

    @property
    def enabled(self) -> bool:
        """签名验证是否启用"""
        return bool(self._secret)

    def verify(self, request: Request, body: bytes = b"") -> Tuple[bool, str]:
        """验证请求签名

        Args:
            request: FastAPI请求对象
            body: 请求体字节

        Returns:
            (是否验证通过, 原因说明)
        """
        if not self._secret:
            return True, "签名未配置"

        signature = request.headers.get("X-Signature", "")
        timestamp = request.headers.get("X-Timestamp", "")
        nonce = request.headers.get("X-Nonce", "")

        if not all([signature, timestamp, nonce]):
            return False, "缺少签名参数"

        try:
            ts = int(timestamp)
        except ValueError:
            return False, "时间戳格式无效"

        now = int(time.time())
        if abs(now - ts) > self._max_skew:
            return False, "请求已过期"

        with self._lock:
            if nonce in self._nonces:
                return False, "请求已被使用"
            self._nonces[nonce] = now
            self._cleanup_nonces(now)

        expected = self._compute_signature(
            method=request.method,
            path=request.url.path,
            timestamp=timestamp,
            nonce=nonce,
            body=body
        )

        if not hmac.compare_digest(signature, expected):
            return False, "签名验证失败"

        return True, ""

    def verify_raw(self, signature: str, timestamp: str, body: str) -> Tuple[bool, str]:
        """验证原始签名（不依赖Request对象）

        Args:
            signature: 签名字符串
            timestamp: 时间戳字符串
            body: 请求体字符串

        Returns:
            (是否验证通过, 原因说明)
        """
        if not self._secret:
            return True, "签名验证未启用"

        if not signature or not timestamp:
            return False, "缺少签名或时间戳"

        try:
            request_time = float(timestamp)
            if abs(time.time() - request_time) > self._max_skew:
                return False, "请求时间戳过期"
        except (ValueError, TypeError):
            return False, "时间戳格式无效"

        expected = hmac.new(
            self._secret,
            f"{timestamp}.{body}".encode(),
            hashlib.sha256
        ).hexdigest()

        if hmac.compare_digest(signature, expected):
            return True, "签名验证通过"
        return False, "签名验证失败"

    def _compute_signature(
        self,
        method: str,
        path: str,
        timestamp: str,
        nonce: str,
        body: bytes
    ) -> str:
        """计算签名"""
        message = f"{method.upper()}:{path}:{timestamp}:{nonce}:{body.hex() if body else ''}"
        return hmac.new(self._secret, message.encode(), hashlib.sha256).hexdigest()

    def _cleanup_nonces(self, now: int):
        """清理过期的Nonce"""
        expire = now - self._max_skew * 2
        expired = [n for n, t in self._nonces.items() if t < expire]
        for n in expired:
            del self._nonces[n]
        if len(self._nonces) > self._max_nonces:
            sorted_nonces = sorted(self._nonces.items(), key=lambda x: x[1])
            for n, _ in sorted_nonces[:len(sorted_nonces) - self._max_nonces // 2]:
                del self._nonces[n]

    def generate_signature(
        self,
        method: str,
        path: str,
        body: bytes = b""
    ) -> Dict[str, str]:
        """生成请求签名

        Args:
            method: HTTP方法
            path: 请求路径
            body: 请求体字节

        Returns:
            包含签名头的字典
        """
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(16)
        signature = self._compute_signature(method, path, timestamp, nonce, body)
        return {
            "X-Signature": signature,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce
        }
