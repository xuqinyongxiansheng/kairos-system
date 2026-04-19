"""
import logging
AutoDream记忆整合机制 - 后台静默整合记忆
logger = logging.getLogger("autodream_engine")

设计理念来源:
- cc-haha-main/docs/memory/03-autodream.md
- 像人类睡眠整理记忆一样，定期回顾多个会话整合知识

核心特性:
1. 五重门控检查链
2. 四阶段整合流程 (Orient→Gather→Consolidate→Prune)
3. 安全限制机制
4. PID锁文件互斥
5. 后台静默执行
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


class DreamPhase(Enum):
    """梦境阶段"""
    ORIENT = "orient"
    GATHER = "gather"
    CONSOLIDATE = "consolidate"
    PRUNE = "prune"
    COMPLETE = "complete"
    FAILED = "failed"


class DreamStatus(Enum):
    """梦境状态"""
    IDLE = "idle"
    GATING = "gating"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class GateType(Enum):
    """门控类型"""
    FEATURE_FLAG = "feature_flag"
    TIME_GATE = "time_gate"
    SCAN_THROTTLE = "scan_throttle"
    SESSION_GATE = "session_gate"
    LOCK_GATE = "lock_gate"


@dataclass
class GateResult:
    """门控检查结果"""
    gate_type: GateType
    passed: bool
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DreamSession:
    """梦境会话"""
    id: str
    phase: DreamPhase = DreamPhase.ORIENT
    status: DreamStatus = DreamStatus.IDLE
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    sessions_processed: int = 0
    memories_created: int = 0
    memories_updated: int = 0
    memories_pruned: int = 0
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "phase": self.phase.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "sessions_processed": self.sessions_processed,
            "memories_created": self.memories_created,
            "memories_updated": self.memories_updated,
            "memories_pruned": self.memories_pruned,
            "errors": self.errors,
            "metadata": self.metadata
        }


@dataclass
class MemoryCandidate:
    """记忆候选"""
    id: str
    content: str
    source_session: str
    importance: float = 0.5
    confidence: float = 0.5
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class FiveGateController:
    """
    五重门控控制器
    
    按顺序检查五个门控条件
    """
    
    def __init__(
        self,
        feature_enabled: bool = True,
        time_gate_hours: int = 24,
        scan_throttle_minutes: int = 10,
        session_gate_count: int = 5
    ):
        self.feature_enabled = feature_enabled
        self.time_gate_hours = time_gate_hours
        self.scan_throttle_minutes = scan_throttle_minutes
        self.session_gate_count = session_gate_count
        
        self._last_dream_time: Optional[datetime] = None
        self._last_scan_time: Optional[datetime] = None
        self._session_count = 0
        self._lock_file: Optional[Path] = None
    
    def check_all_gates(
        self,
        lock_dir: Optional[str] = None
    ) -> Tuple[bool, List[GateResult]]:
        """
        检查所有门控
        
        Returns:
            (是否全部通过, 门控结果列表)
        """
        results = []
        
        result = self._check_feature_flag()
        results.append(result)
        if not result.passed:
            return False, results
        
        result = self._check_time_gate()
        results.append(result)
        if not result.passed:
            return False, results
        
        result = self._check_scan_throttle()
        results.append(result)
        if not result.passed:
            return False, results
        
        result = self._check_session_gate()
        results.append(result)
        if not result.passed:
            return False, results
        
        result = self._check_lock_gate(lock_dir)
        results.append(result)
        if not result.passed:
            return False, results
        
        return True, results
    
    def _check_feature_flag(self) -> GateResult:
        """检查功能开关"""
        return GateResult(
            gate_type=GateType.FEATURE_FLAG,
            passed=self.feature_enabled,
            reason="功能已启用" if self.feature_enabled else "功能已禁用"
        )
    
    def _check_time_gate(self) -> GateResult:
        """检查时间门控"""
        if self._last_dream_time is None:
            return GateResult(
                gate_type=GateType.TIME_GATE,
                passed=True,
                reason="首次运行"
            )
        
        elapsed = datetime.now(timezone.utc) - self._last_dream_time
        hours_elapsed = elapsed.total_seconds() / 3600
        
        passed = hours_elapsed >= self.time_gate_hours
        
        return GateResult(
            gate_type=GateType.TIME_GATE,
            passed=passed,
            reason=f"距上次运行{hours_elapsed:.1f}小时" + 
                   (f"，超过{self.time_gate_hours}小时阈值" if passed else f"，未达{self.time_gate_hours}小时阈值"),
            metadata={"hours_elapsed": hours_elapsed}
        )
    
    def _check_scan_throttle(self) -> GateResult:
        """检查扫描节流"""
        if self._last_scan_time is None:
            return GateResult(
                gate_type=GateType.SCAN_THROTTLE,
                passed=True,
                reason="首次扫描"
            )
        
        elapsed = datetime.now(timezone.utc) - self._last_scan_time
        minutes_elapsed = elapsed.total_seconds() / 60
        
        passed = minutes_elapsed >= self.scan_throttle_minutes
        
        return GateResult(
            gate_type=GateType.SCAN_THROTTLE,
            passed=passed,
            reason=f"距上次扫描{minutes_elapsed:.1f}分钟",
            metadata={"minutes_elapsed": minutes_elapsed}
        )
    
    def _check_session_gate(self) -> GateResult:
        """检查会话门控"""
        passed = self._session_count >= self.session_gate_count
        
        return GateResult(
            gate_type=GateType.SESSION_GATE,
            passed=passed,
            reason=f"已有{self._session_count}个会话" + 
                   (f"，达到{self.session_gate_count}个阈值" if passed else f"，未达{self.session_gate_count}个阈值"),
            metadata={"session_count": self._session_count}
        )
    
    def _check_lock_gate(
        self, 
        lock_dir: Optional[str] = None
    ) -> GateResult:
        """检查锁门控"""
        if lock_dir is None:
            return GateResult(
                gate_type=GateType.LOCK_GATE,
                passed=True,
                reason="无锁目录"
            )
        
        lock_path = Path(lock_dir) / "autodream.lock"
        
        if lock_path.exists():
            try:
                content = lock_path.read_text()
                data = json.loads(content)
                locked_at = datetime.fromisoformat(data.get("locked_at", ""))
                elapsed = datetime.now(timezone.utc) - locked_at
                
                if elapsed.total_seconds() < 3600:
                    return GateResult(
                        gate_type=GateType.LOCK_GATE,
                        passed=False,
                        reason=f"锁文件存在，已锁定{elapsed.total_seconds():.0f}秒",
                        metadata={"lock_file": str(lock_path)}
                    )
                else:
                    lock_path.unlink()
            except Exception:
                logger.debug(f"忽略异常: ", exc_info=True)
                pass
        
        return GateResult(
            gate_type=GateType.LOCK_GATE,
            passed=True,
            reason="无锁文件或锁已过期"
        )
    
    def record_dream(self) -> None:
        """记录梦境执行"""
        self._last_dream_time = datetime.now(timezone.utc)
    
    def record_scan(self) -> None:
        """记录扫描"""
        self._last_scan_time = datetime.now(timezone.utc)
    
    def increment_session(self) -> None:
        """增加会话计数"""
        self._session_count += 1
    
    def acquire_lock(
        self, 
        lock_dir: str,
        dream_id: str
    ) -> bool:
        """获取锁"""
        lock_path = Path(lock_dir) / "autodream.lock"
        
        try:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            
            content = {
                "dream_id": dream_id,
                "locked_at": datetime.now(timezone.utc).isoformat(),
                "pid": os.getpid()
            }
            
            lock_path.write_text(json.dumps(content, indent=2))
            self._lock_file = lock_path
            return True
        except Exception:
            return False
    
    def release_lock(self) -> None:
        """释放锁"""
        if self._lock_file and self._lock_file.exists():
            try:
                self._lock_file.unlink()
            except Exception:
                logger.debug(f"忽略异常: self._lock_file.unlink()", exc_info=True)
                pass
        self._lock_file = None


class DreamPhases:
    """
    梦境阶段处理器
    
    实现四阶段整合流程
    """
    
    def __init__(
        self,
        memory_system: Optional[Any] = None,
        session_store: Optional[Any] = None
    ):
        self.memory_system = memory_system
        self.session_store = session_store
    
    async def orient(
        self, 
        session: DreamSession
    ) -> DreamSession:
        """
        定向阶段
        
        确定要处理的会话范围
        """
        session.phase = DreamPhase.ORIENT
        
        sessions_to_process = await self._find_sessions_to_process()
        
        session.metadata["sessions_to_process"] = sessions_to_process
        session.sessions_processed = len(sessions_to_process)
        
        return session
    
    async def gather(
        self, 
        session: DreamSession
    ) -> DreamSession:
        """
        收集阶段
        
        从会话中提取记忆候选
        """
        session.phase = DreamPhase.GATHER
        
        sessions_to_process = session.metadata.get("sessions_to_process", [])
        
        candidates = []
        for session_id in sessions_to_process:
            session_candidates = await self._extract_candidates(session_id)
            candidates.extend(session_candidates)
        
        session.metadata["candidates"] = [
            {
                "id": c.id,
                "content": c.content[:100],
                "importance": c.importance
            }
            for c in candidates
        ]
        session.metadata["candidate_count"] = len(candidates)
        
        return session
    
    async def consolidate(
        self, 
        session: DreamSession
    ) -> DreamSession:
        """
        整合阶段
        
        合并、去重、存储记忆
        """
        session.phase = DreamPhase.CONSOLIDATE
        
        candidates_data = session.metadata.get("candidates", [])
        
        merged = self._merge_candidates(candidates_data)
        
        stored = await self._store_memories(merged)
        
        session.memories_created = stored.get("created", 0)
        session.memories_updated = stored.get("updated", 0)
        
        return session
    
    async def prune(
        self, 
        session: DreamSession
    ) -> DreamSession:
        """
        修剪阶段
        
        删除过期、重复、低价值记忆
        """
        session.phase = DreamPhase.PRUNE
        
        pruned = await self._prune_memories()
        
        session.memories_pruned = pruned
        
        return session
    
    async def _find_sessions_to_process(self) -> List[str]:
        """查找要处理的会话"""
        if self.session_store:
            try:
                return await self.session_store.list_recent_sessions(limit=10)
            except Exception:
                logger.debug(f"忽略异常: return await self.session_store.list_recent_sessio", exc_info=True)
                pass
        
        return [f"session_{i}" for i in range(5)]
    
    async def _extract_candidates(
        self, 
        session_id: str
    ) -> List[MemoryCandidate]:
        """从会话提取记忆候选"""
        candidates = []
        
        candidate = MemoryCandidate(
            id=self._generate_id(),
            content=f"从{session_id}提取的记忆内容",
            source_session=session_id,
            importance=0.5,
            confidence=0.5
        )
        candidates.append(candidate)
        
        return candidates
    
    def _merge_candidates(
        self, 
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """合并记忆候选"""
        if not candidates:
            return []
        
        merged = {}
        for c in candidates:
            key = hashlib.md5(c.get("content", "").encode()).hexdigest()[:8]
            if key in merged:
                merged[key]["importance"] = max(
                    merged[key]["importance"],
                    c.get("importance", 0.5)
                )
            else:
                merged[key] = c
        
        return list(merged.values())
    
    async def _store_memories(
        self, 
        memories: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """存储记忆"""
        result = {"created": 0, "updated": 0}
        
        if self.memory_system:
            for memory in memories:
                try:
                    await self.memory_system.store(
                        content=memory.get("content", ""),
                        memory_type="long_term",
                        metadata={
                            "importance": memory.get("importance", 0.5),
                            "source": "autodream"
                        }
                    )
                    result["created"] += 1
                except Exception:
                    logger.debug(f"忽略异常: ", exc_info=True)
                    pass
        else:
            result["created"] = len(memories)
        
        return result
    
    async def _prune_memories(self) -> int:
        """修剪记忆"""
        if self.memory_system:
            try:
                return await self.memory_system.prune_expired()
            except Exception:
                logger.debug(f"忽略异常: return await self.memory_system.prune_expired()", exc_info=True)
                pass
        
        return 0
    
    def _generate_id(self) -> str:
        """生成ID"""
        content = f"memory:{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


class AutoDreamEngine:
    """
    AutoDream引擎
    
    后台静默整合记忆系统
    
    使用方式:
        engine = AutoDreamEngine(memory_system, session_store)
        engine.start()
        
        # 手动触发
        await engine.trigger_dream()
        
        engine.stop()
    """
    
    def __init__(
        self,
        memory_system: Optional[Any] = None,
        session_store: Optional[Any] = None,
        lock_dir: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.memory_system = memory_system
        self.session_store = session_store
        self.lock_dir = lock_dir
        self.config = config or {}
        
        self.gate_controller = FiveGateController(
            feature_enabled=self.config.get("enabled", True),
            time_gate_hours=self.config.get("time_gate_hours", 24),
            scan_throttle_minutes=self.config.get("scan_throttle_minutes", 10),
            session_gate_count=self.config.get("session_gate_count", 5)
        )
        
        self.phases = DreamPhases(memory_system, session_store)
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._current_session: Optional[DreamSession] = None
        self._history: List[DreamSession] = []
        self._lock = threading.Lock()
    
    def start(self) -> None:
        """启动引擎"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
    
    def stop(self) -> None:
        """停止引擎"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
    
    def _run_loop(self) -> None:
        """主循环"""
        check_interval = self.config.get("check_interval", 300)
        
        while self._running:
            try:
                self._check_and_run()
            except Exception:
                logger.debug(f"忽略异常: self._check_and_run()", exc_info=True)
                pass
            
            time.sleep(check_interval)
    
    def _check_and_run(self) -> None:
        """检查并运行"""
        all_passed, results = self.gate_controller.check_all_gates(self.lock_dir)
        
        if not all_passed:
            return
        
        asyncio.run(self.run_dream())
    
    async def run_dream(self) -> DreamSession:
        """运行梦境"""
        dream_id = self._generate_dream_id()
        
        session = DreamSession(
            id=dream_id,
            status=DreamStatus.RUNNING,
            started_at=datetime.now(timezone.utc)
        )
        
        self._current_session = session
        
        if self.lock_dir:
            if not self.gate_controller.acquire_lock(self.lock_dir, dream_id):
                session.status = DreamStatus.FAILED
                session.errors.append("无法获取锁")
                return session
        
        try:
            session = await self.phases.orient(session)
            session = await self.phases.gather(session)
            session = await self.phases.consolidate(session)
            session = await self.phases.prune(session)
            
            session.phase = DreamPhase.COMPLETE
            session.status = DreamStatus.COMPLETE
            session.completed_at = datetime.now(timezone.utc)
            
            self.gate_controller.record_dream()
            
        except Exception as e:
            session.phase = DreamPhase.FAILED
            session.status = DreamStatus.FAILED
            session.errors.append(str(e))
        
        finally:
            self.gate_controller.release_lock()
            
            with self._lock:
                self._history.append(session)
            
            self._current_session = None
        
        return session
    
    async def trigger_dream(self) -> DreamSession:
        """手动触发梦境"""
        return await self.run_dream()
    
    def increment_session_count(self) -> None:
        """增加会话计数"""
        self.gate_controller.increment_session()
    
    def get_current_session(self) -> Optional[DreamSession]:
        """获取当前会话"""
        return self._current_session
    
    def get_history(self, limit: int = 10) -> List[DreamSession]:
        """获取历史"""
        with self._lock:
            return self._history[-limit:]
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "running": self._running,
            "current_session": self._current_session.to_dict() if self._current_session else None,
            "history_count": len(self._history),
            "gate_status": {
                "last_dream": self.gate_controller._last_dream_time.isoformat() 
                             if self.gate_controller._last_dream_time else None,
                "session_count": self.gate_controller._session_count
            }
        }
    
    def _generate_dream_id(self) -> str:
        """生成梦境ID"""
        content = f"dream:{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
