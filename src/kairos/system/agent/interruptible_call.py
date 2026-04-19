# -*- coding: utf-8 -*-
"""
可中断API调用 (Interruptible API Call)
源自Hermes Agent可中断调用架构

核心设计:
- API请求在后台线程执行
- 主线程监控中断事件
- 用户可随时中断长时间推理
- 部分响应不注入对话历史
"""

import time
import logging
import threading
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from concurrent.futures import Future, ThreadPoolExecutor

logger = logging.getLogger("InterruptibleCall")


@dataclass
class CallResult:
    """调用结果"""
    success: bool
    response: Any = None
    error: str = ""
    latency_ms: float = 0.0
    interrupted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "error": self.error,
            "latency_ms": round(self.latency_ms, 1),
            "interrupted": self.interrupted
        }


class InterruptibleAPICall:
    """
    可中断API调用
    
    用法:
    1. call_with_interrupt() 执行可中断调用
    2. interrupt() 中断当前调用
    3. 支持超时和回调
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._default_timeout = self.config.get("default_timeout", 120.0)
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._interrupt_event = threading.Event()
        self._current_call_id: Optional[str] = None
        self._call_lock = threading.Lock()
        self._active_calls: Dict[str, threading.Event] = {}

    def call_with_interrupt(self, call_fn: Callable[[], Any],
                            timeout: float = None,
                            call_id: str = None,
                            on_progress: Callable = None) -> CallResult:
        call_timeout = timeout or self._default_timeout
        cid = call_id or ("call_" + str(int(time.time() * 1000)))

        interrupt_event = threading.Event()
        with self._call_lock:
            self._active_calls[cid] = interrupt_event
            self._current_call_id = cid

        result_holder = [None]
        error_holder = [None]
        start_time = time.time()

        def _worker():
            try:
                result_holder[0] = call_fn()
            except Exception as e:
                error_holder[0] = e

        worker_thread = threading.Thread(target=_worker, daemon=True)
        worker_thread.start()

        try:
            worker_thread.join(timeout=call_timeout)
        except Exception:
            pass

        elapsed_ms = (time.time() - start_time) * 1000
        was_interrupted = interrupt_event.is_set() or worker_thread.is_alive()

        with self._call_lock:
            self._active_calls.pop(cid, None)
            if self._current_call_id == cid:
                self._current_call_id = None

        if was_interrupted:
            logger.info("API调用 %s 已中断 (%.0fms)", cid, elapsed_ms)
            return CallResult(
                success=False,
                error="调用被中断",
                latency_ms=elapsed_ms,
                interrupted=True
            )

        if error_holder[0] is not None:
            return CallResult(
                success=False,
                error=str(error_holder[0]),
                latency_ms=elapsed_ms
            )

        return CallResult(
            success=True,
            response=result_holder[0],
            latency_ms=elapsed_ms
        )

    def interrupt(self, call_id: str = None) -> bool:
        with self._call_lock:
            if call_id:
                event = self._active_calls.get(call_id)
                if event:
                    event.set()
                    return True
            elif self._current_call_id:
                event = self._active_calls.get(self._current_call_id)
                if event:
                    event.set()
                    return True
        self._interrupt_event.set()
        return True

    def interrupt_all(self):
        with self._call_lock:
            for event in self._active_calls.values():
                event.set()
            self._active_calls.clear()
            self._current_call_id = None
        self._interrupt_event.set()

    def get_active_calls(self) -> List[str]:
        with self._call_lock:
            return list(self._active_calls.keys())

    def shutdown(self):
        self.interrupt_all()
        self._executor.shutdown(wait=False)
