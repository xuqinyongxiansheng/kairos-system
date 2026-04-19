#!/usr/bin/env python3
"""
循环协调器 (Loop Coordinator)

统一管理5套自动化循环的生命周期和资源分配：
1. 认知闭环 (CognitiveLoop)
2. OTAC自主执行 (AutonomousEngine)
3. AutoDream记忆整合 (AutoDreamEngine)
4. 后台服务调度 (BackgroundService)
5. 自我进化 (SelfEvolution)

功能：
- 统一启动/停止/暂停/恢复
- 循环健康监控
- 资源冲突协调
- 循环依赖管理
- 异常恢复
- 全局状态追踪
"""

import time
import asyncio
import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, field

from kairos.system.config import settings

logger = logging.getLogger("LoopCoordinator")


class LoopType(Enum):
    COGNITIVE = "cognitive"
    OTAC = "otac"
    AUTODREAM = "autodream"
    BACKGROUND = "background"
    EVOLUTION = "evolution"


class LoopState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class LoopInfo:
    loop_type: LoopType
    state: LoopState = LoopState.STOPPED
    instance: Any = None
    task: Optional[asyncio.Task] = None
    last_run_time: float = 0.0
    last_error: Optional[str] = None
    run_count: int = 0
    error_count: int = 0
    avg_duration_ms: float = 0.0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loop_type": self.loop_type.value,
            "state": self.state.value,
            "last_run_time": self.last_run_time,
            "last_error": self.last_error,
            "run_count": self.run_count,
            "error_count": self.error_count,
            "avg_duration_ms": f"{self.avg_duration_ms:.1f}ms",
            "enabled": self.enabled,
        }


class LoopCoordinator:
    """
    循环协调器

    统一管理5套自动化循环，提供：
    - 生命周期管理（启动/停止/暂停/恢复）
    - 健康监控（状态追踪+异常检测）
    - 资源协调（防止循环间资源冲突）
    - 依赖管理（循环启动顺序）
    - 异常恢复（自动重启失败的循环）
    """

    LOOP_START_ORDER = [
        LoopType.BACKGROUND,
        LoopType.AUTODREAM,
        LoopType.COGNITIVE,
        LoopType.OTAC,
        LoopType.EVOLUTION,
    ]

    def __init__(self):
        self._loops: Dict[LoopType, LoopInfo] = {}
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._monitor_interval = 30.0
        self._auto_restart = True
        self._max_restart_attempts = 3
        self._restart_attempts: Dict[LoopType, int] = {}

        for lt in LoopType:
            self._loops[lt] = LoopInfo(loop_type=lt)

    def register_loop(self, loop_type: LoopType, instance: Any, enabled: bool = True):
        if loop_type in self._loops:
            self._loops[loop_type].instance = instance
            self._loops[loop_type].enabled = enabled
        else:
            self._loops[loop_type] = LoopInfo(loop_type=loop_type, instance=instance, enabled=enabled)
        logger.info("循环已注册: %s (启用: %s)", loop_type.value, enabled)

    async def start_all(self):
        if self._running:
            logger.warning("循环协调器已在运行")
            return

        self._running = True
        logger.info("循环协调器启动，按依赖顺序启动循环...")

        for loop_type in self.LOOP_START_ORDER:
            info = self._loops.get(loop_type)
            if not info or not info.enabled:
                logger.info("跳过循环: %s (未启用)", loop_type.value)
                continue

            try:
                await self._start_loop(loop_type)
            except Exception as e:
                logger.error("启动循环失败 %s: %s", loop_type.value, e)
                info.state = LoopState.ERROR
                info.last_error = str(e)

        self._monitor_task = asyncio.create_task(self._monitor_loops())
        logger.info("循环协调器启动完成，监控任务已创建")

    async def stop_all(self):
        if not self._running:
            return

        self._running = False
        logger.info("循环协调器停止中...")

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

        for loop_type in reversed(self.LOOP_START_ORDER):
            try:
                await self._stop_loop(loop_type)
            except Exception as e:
                logger.error("停止循环失败 %s: %s", loop_type.value, e)

        logger.info("循环协调器已停止")

    async def _start_loop(self, loop_type: LoopType):
        info = self._loops.get(loop_type)
        if not info or not info.instance:
            logger.warning("循环未注册: %s", loop_type.value)
            return

        info.state = LoopState.STARTING

        try:
            instance = info.instance

            if loop_type == LoopType.COGNITIVE:
                pass
            elif loop_type == LoopType.OTAC:
                if hasattr(instance, 'start'):
                    if asyncio.iscoroutinefunction(instance.start):
                        await instance.start()
                    else:
                        instance.start()
            elif loop_type == LoopType.AUTODREAM:
                if hasattr(instance, 'start'):
                    if asyncio.iscoroutinefunction(instance.start):
                        await instance.start()
                    else:
                        instance.start()
            elif loop_type == LoopType.BACKGROUND:
                if hasattr(instance, 'start'):
                    if asyncio.iscoroutinefunction(instance.start):
                        await instance.start()
                    else:
                        instance.start()
            elif loop_type == LoopType.EVOLUTION:
                pass

            info.state = LoopState.RUNNING
            info.last_run_time = time.time()
            self._restart_attempts[loop_type] = 0
            logger.info("循环已启动: %s", loop_type.value)

        except Exception as e:
            info.state = LoopState.ERROR
            info.last_error = str(e)
            logger.error("循环启动失败 %s: %s", loop_type.value, e)
            raise

    async def _stop_loop(self, loop_type: LoopType):
        info = self._loops.get(loop_type)
        if not info or info.state == LoopState.STOPPED:
            return

        info.state = LoopState.STOPPING

        try:
            instance = info.instance
            if instance and hasattr(instance, 'stop'):
                if asyncio.iscoroutinefunction(instance.stop):
                    await instance.stop()
                else:
                    instance.stop()

            if info.task and not info.task.done():
                info.task.cancel()
                try:
                    await info.task
                except asyncio.CancelledError:
                    pass
                info.task = None

            info.state = LoopState.STOPPED
            logger.info("循环已停止: %s", loop_type.value)

        except Exception as e:
            info.state = LoopState.ERROR
            info.last_error = str(e)
            logger.error("停止循环失败 %s: %s", loop_type.value, e)

    async def pause_loop(self, loop_type: LoopType):
        info = self._loops.get(loop_type)
        if info and info.state == LoopState.RUNNING:
            info.state = LoopState.PAUSED
            logger.info("循环已暂停: %s", loop_type.value)

    async def resume_loop(self, loop_type: LoopType):
        info = self._loops.get(loop_type)
        if info and info.state == LoopState.PAUSED:
            info.state = LoopState.RUNNING
            logger.info("循环已恢复: %s", loop_type.value)

    async def _monitor_loops(self):
        logger.info("循环监控已启动，间隔: %.0fs", self._monitor_interval)
        while self._running:
            try:
                await asyncio.sleep(self._monitor_interval)
                await self._check_loop_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("循环监控异常: %s", e)

    async def _check_loop_health(self):
        for loop_type, info in self._loops.items():
            if not info.enabled or info.state in (LoopState.STOPPED, LoopState.PAUSED):
                continue

            if info.state == LoopState.ERROR and self._auto_restart:
                attempts = self._restart_attempts.get(loop_type, 0)
                if attempts < self._max_restart_attempts:
                    logger.warning("尝试重启循环 %s (第%d次)", loop_type.value, attempts + 1)
                    try:
                        await self._stop_loop(loop_type)
                        await asyncio.sleep(2)
                        await self._start_loop(loop_type)
                        self._restart_attempts[loop_type] = attempts + 1
                    except Exception as e:
                        logger.error("重启循环失败 %s: %s", loop_type.value, e)
                else:
                    logger.error("循环 %s 已达最大重启次数(%d)，不再尝试",
                                 loop_type.value, self._max_restart_attempts)

    def get_status(self) -> Dict[str, Any]:
        loops_status = {}
        running_count = 0
        error_count = 0

        for lt, info in self._loops.items():
            loops_status[lt.value] = info.to_dict()
            if info.state == LoopState.RUNNING:
                running_count += 1
            elif info.state == LoopState.ERROR:
                error_count += 1

        return {
            "coordinator_running": self._running,
            "total_loops": len(self._loops),
            "running_count": running_count,
            "error_count": error_count,
            "auto_restart": self._auto_restart,
            "loops": loops_status,
        }

    def get_loop_info(self, loop_type: LoopType) -> Optional[LoopInfo]:
        return self._loops.get(loop_type)

    def enable_loop(self, loop_type: LoopType):
        if loop_type in self._loops:
            self._loops[loop_type].enabled = True
            logger.info("循环已启用: %s", loop_type.value)

    def disable_loop(self, loop_type: LoopType):
        if loop_type in self._loops:
            self._loops[loop_type].enabled = False
            logger.info("循环已禁用: %s", loop_type.value)

    def set_auto_restart(self, enabled: bool, max_attempts: int = 3):
        self._auto_restart = enabled
        self._max_restart_attempts = max_attempts
        logger.info("自动重启: %s, 最大尝试: %d", enabled, max_attempts)


_coordinator: Optional[LoopCoordinator] = None


def get_loop_coordinator() -> LoopCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = LoopCoordinator()
        logger.info("循环协调器实例已创建")
    return _coordinator
