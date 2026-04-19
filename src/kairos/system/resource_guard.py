#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鸿蒙小雨资源阈值监控系统
设定CPU和内存使用阈值，超限时自动降级或保护

核心功能：
1. CPU使用率监控（阈值80%）
2. 内存使用率监控（阈值90%）
3. 资源超限自动保护
4. 资源状态报告
5. 与核心身份系统集成
"""

import os
import time
import logging
import threading
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger("ResourceGuard")


class ResourceLevel(Enum):
    """资源状态等级"""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class ProtectionAction(Enum):
    """保护动作"""
    NONE = "none"
    THROTTLE = "throttle"
    DEFER = "defer"
    REJECT = "reject"
    SHUTDOWN = "shutdown"


@dataclass
class ResourceThreshold:
    """资源阈值配置 - 适配 i5-7500/16GB"""
    cpu_warning: float = 65.0
    cpu_critical: float = 80.0
    cpu_emergency: float = 92.0
    memory_warning: float = 70.0
    memory_critical: float = 85.0
    memory_emergency: float = 95.0
    check_interval: float = 10.0
    cooldown_seconds: float = 30.0


@dataclass
class ResourceStatus:
    """资源状态"""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_gb: float = 0.0
    memory_total_gb: float = 0.0
    cpu_level: ResourceLevel = ResourceLevel.NORMAL
    memory_level: ResourceLevel = ResourceLevel.NORMAL
    overall_level: ResourceLevel = ResourceLevel.NORMAL
    action: ProtectionAction = ProtectionAction.NONE
    timestamp: str = ""


class ResourceGuard:
    """鸿蒙小雨资源守护者"""
    
    def __init__(self, threshold: ResourceThreshold = None):
        self.threshold = threshold or ResourceThreshold()
        self._status = ResourceStatus()
        self._monitor_thread = None
        self._running = False
        self._callbacks: Dict[ResourceLevel, List[Callable]] = {
            ResourceLevel.WARNING: [],
            ResourceLevel.CRITICAL: [],
            ResourceLevel.EMERGENCY: []
        }
        self._last_action_time = 0.0
        self._psutil_available = False
        
        self._check_psutil()
        
        logger.info(
            f"资源守护者初始化完成 - "
            f"CPU阈值: {self.threshold.cpu_critical}%, "
            f"内存阈值: {self.threshold.memory_critical}%"
        )
    
    def _check_psutil(self):
        """检查psutil是否可用"""
        try:
            import psutil
            self._psutil_available = True
            logger.info("psutil可用，启用精确资源监控")
        except ImportError:
            self._psutil_available = False
            logger.warning("psutil不可用，使用基础资源监控")
    
    def get_cpu_percent(self) -> float:
        """获取CPU使用率"""
        if self._psutil_available:
            import psutil
            return psutil.cpu_percent(interval=1)
        else:
            try:
                import subprocess
                if os.name == 'nt':
                    result = subprocess.run(
                        ['wmic', 'cpu', 'get', 'loadpercentage'],
                        capture_output=True, text=True, timeout=5
                    )
                    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
                    if len(lines) > 1:
                        return float(lines[1])
                return 0.0
            except Exception:
                return 0.0
    
    def get_memory_percent(self) -> tuple:
        """获取内存使用率和详细信息"""
        if self._psutil_available:
            import psutil
            mem = psutil.virtual_memory()
            return mem.percent, mem.used / (1024**3), mem.total / (1024**3)
        else:
            try:
                import subprocess
                if os.name == 'nt':
                    result = subprocess.run(
                        ['wmic', 'OS', 'get', 'FreePhysicalMemory,TotalVisibleMemorySize'],
                        capture_output=True, text=True, timeout=5
                    )
                    lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
                    if len(lines) > 1:
                        parts = lines[1].split()
                        if len(parts) >= 2:
                            total_kb = int(parts[1])
                            free_kb = int(parts[0])
                            used_kb = total_kb - free_kb
                            percent = (used_kb / total_kb * 100) if total_kb > 0 else 0
                            return percent, used_kb / (1024**2), total_kb / (1024**2)
                return 0.0, 0.0, 0.0
            except Exception:
                return 0.0, 0.0, 0.0
    
    def check_resources(self) -> ResourceStatus:
        """检查资源状态"""
        cpu_percent = self.get_cpu_percent()
        memory_percent, memory_used_gb, memory_total_gb = self.get_memory_percent()
        
        # 判断CPU等级
        if cpu_percent >= self.threshold.cpu_emergency:
            cpu_level = ResourceLevel.EMERGENCY
        elif cpu_percent >= self.threshold.cpu_critical:
            cpu_level = ResourceLevel.CRITICAL
        elif cpu_percent >= self.threshold.cpu_warning:
            cpu_level = ResourceLevel.WARNING
        else:
            cpu_level = ResourceLevel.NORMAL
        
        # 判断内存等级
        if memory_percent >= self.threshold.memory_emergency:
            memory_level = ResourceLevel.EMERGENCY
        elif memory_percent >= self.threshold.memory_critical:
            memory_level = ResourceLevel.CRITICAL
        elif memory_percent >= self.threshold.memory_warning:
            memory_level = ResourceLevel.WARNING
        else:
            memory_level = ResourceLevel.NORMAL
        
        # 综合等级
        level_order = {
            ResourceLevel.NORMAL: 0,
            ResourceLevel.WARNING: 1,
            ResourceLevel.CRITICAL: 2,
            ResourceLevel.EMERGENCY: 3
        }
        overall_level = max(
            [cpu_level, memory_level],
            key=lambda x: level_order[x]
        )
        
        # 决定保护动作
        action = self._determine_action(overall_level)
        
        self._status = ResourceStatus(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_gb=memory_used_gb,
            memory_total_gb=memory_total_gb,
            cpu_level=cpu_level,
            memory_level=memory_level,
            overall_level=overall_level,
            action=action,
            timestamp=datetime.now().isoformat()
        )
        
        return self._status
    
    def _determine_action(self, level: ResourceLevel) -> ProtectionAction:
        """根据资源等级决定保护动作"""
        now = time.time()
        
        if now - self._last_action_time < self.threshold.cooldown_seconds:
            return self._status.action if self._status else ProtectionAction.NONE
        
        if level == ResourceLevel.EMERGENCY:
            self._last_action_time = now
            return ProtectionAction.REJECT
        elif level == ResourceLevel.CRITICAL:
            self._last_action_time = now
            return ProtectionAction.DEFER
        elif level == ResourceLevel.WARNING:
            self._last_action_time = now
            return ProtectionAction.THROTTLE
        else:
            return ProtectionAction.NONE
    
    def can_proceed(self, task_priority: str = "normal") -> tuple:
        """判断任务是否可以继续执行
        
        Args:
            task_priority: 任务优先级 (high/normal/low)
        
        Returns:
            (can_proceed, reason)
        """
        status = self.check_resources()
        
        if status.action == ProtectionAction.NONE:
            return True, "资源正常"
        
        if status.action == ProtectionAction.THROTTLE:
            if task_priority == "high":
                return True, "高优先级任务允许执行（节流模式）"
            return True, "节流模式执行"
        
        if status.action == ProtectionAction.DEFER:
            if task_priority == "high":
                return True, "高优先级任务允许执行（资源紧张）"
            return False, f"资源紧张，延迟执行 (CPU:{status.cpu_percent:.1f}%, MEM:{status.memory_percent:.1f}%)"
        
        if status.action == ProtectionAction.REJECT:
            if task_priority == "high":
                return True, "高优先级任务强制执行（资源紧急）"
            return False, f"资源紧急，拒绝执行 (CPU:{status.cpu_percent:.1f}%, MEM:{status.memory_percent:.1f}%)"
        
        return True, "默认允许"
    
    def register_callback(self, level: ResourceLevel, callback: Callable):
        """注册资源等级回调"""
        if level in self._callbacks:
            self._callbacks[level].append(callback)
    
    def start_monitor(self):
        """启动后台监控"""
        if self._running:
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ResourceGuard-Monitor"
        )
        self._monitor_thread.start()
        logger.info("资源监控已启动")
    
    def stop_monitor(self):
        """停止后台监控"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)
        logger.info("资源监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                status = self.check_resources()
                
                if status.overall_level != ResourceLevel.NORMAL:
                    logger.warning(
                        f"资源告警 - CPU:{status.cpu_percent:.1f}%({status.cpu_level.value}) "
                        f"MEM:{status.memory_percent:.1f}%({status.memory_level.value}) "
                        f"动作:{status.action.value}"
                    )
                    
                    for callback in self._callbacks.get(status.overall_level, []):
                        try:
                            callback(status)
                        except Exception as e:
                            logger.error(f"资源回调执行失败: {e}")
                
                time.sleep(self.threshold.check_interval)
                
            except Exception as e:
                logger.error(f"资源监控异常: {e}")
                time.sleep(self.threshold.check_interval)
    
    def get_status(self) -> Dict[str, Any]:
        """获取资源状态"""
        status = self.check_resources()
        return {
            "cpu_percent": round(status.cpu_percent, 1),
            "memory_percent": round(status.memory_percent, 1),
            "memory_used_gb": round(status.memory_used_gb, 2),
            "memory_total_gb": round(status.memory_total_gb, 2),
            "cpu_level": status.cpu_level.value,
            "memory_level": status.memory_level.value,
            "overall_level": status.overall_level.value,
            "action": status.action.value,
            "thresholds": {
                "cpu_critical": self.threshold.cpu_critical,
                "memory_critical": self.threshold.memory_critical
            },
            "timestamp": status.timestamp
        }
    
    def get_report(self) -> str:
        """获取资源报告"""
        status = self.check_resources()
        
        report = f"""【鸿蒙小雨资源状态报告】
时间: {status.timestamp}
CPU使用率: {status.cpu_percent:.1f}% (阈值: {self.threshold.cpu_critical}%)
内存使用率: {status.memory_percent:.1f}% (阈值: {self.threshold.memory_critical}%)
内存使用: {status.memory_used_gb:.2f}GB / {status.memory_total_gb:.2f}GB
CPU等级: {status.cpu_level.value}
内存等级: {status.memory_level.value}
综合等级: {status.overall_level.value}
保护动作: {status.action.value}
"""
        return report


_resource_guard = None


def get_resource_guard() -> ResourceGuard:
    """获取资源守护者实例"""
    global _resource_guard
    
    if _resource_guard is None:
        threshold = ResourceThreshold(
            cpu_warning=65.0,
            cpu_critical=80.0,
            cpu_emergency=92.0,
            memory_warning=70.0,
            memory_critical=85.0,
            memory_emergency=95.0,
            check_interval=10.0,
            cooldown_seconds=30.0
        )
        _resource_guard = ResourceGuard(threshold)
    
    return _resource_guard
