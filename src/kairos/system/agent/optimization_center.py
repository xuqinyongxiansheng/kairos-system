# -*- coding: utf-8 -*-
"""
统一优化中心

整合所有优化模块的统一入口，提供：
- 性能监控：统一指标收集、聚合、告警
- 错误恢复：集中式错误处理、降级策略、熔断器
- 配置中心：统一配置管理、热更新、环境适配

将P0/P1/P2各优化模块整合为协同工作的整体。
"""

import time
import logging
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass
class MetricPoint:
    name: str
    value: float
    metric_type: MetricType
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlertRule:
    name: str
    metric_name: str
    threshold: float
    comparison: str  # "gt", "lt", "gte", "lte"
    cooldown_s: float = 60.0
    last_fired: float = 0.0
    enabled: bool = True


class MetricsCollector:
    """
    统一指标收集器。

    支持：
    - 计数器（counter）：递增统计
    - 仪表盘（gauge）：当前值
    - 直方图（histogram）：分布统计
    - 标签维度：按标签分组
    - 告警规则：阈值触发
    """

    def __init__(self, max_points: int = 10000):
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._alerts: Dict[str, AlertRule] = {}
        self._alert_callbacks: List[Callable[[str, float, str], None]] = []
        self._lock = threading.Lock()
        self._max_points = max_points

    def increment(self, name: str, value: float = 1.0,
                  tags: Optional[Dict] = None) -> None:
        """递增计数器"""
        key = self._make_key(name, tags)
        with self._lock:
            self._counters[key] += value
        self._check_alerts(name, self._counters[key])

    def gauge(self, name: str, value: float,
              tags: Optional[Dict] = None) -> None:
        """设置仪表盘值"""
        key = self._make_key(name, tags)
        with self._lock:
            self._gauges[key] = value
        self._check_alerts(name, value)

    def observe(self, name: str, value: float,
                tags: Optional[Dict] = None) -> None:
        """记录直方图观测值"""
        key = self._make_key(name, tags)
        with self._lock:
            hist = self._histograms[key]
            hist.append(value)
            if len(hist) > self._max_points:
                self._histograms[key] = hist[-self._max_points:]

    def get_counter(self, name: str, tags: Optional[Dict] = None) -> float:
        """获取计数器值"""
        key = self._make_key(name, tags)
        with self._lock:
            return self._counters.get(key, 0.0)

    def get_gauge(self, name: str, tags: Optional[Dict] = None) -> Optional[float]:
        """获取仪表盘值"""
        key = self._make_key(name, tags)
        with self._lock:
            return self._gauges.get(key)

    def get_histogram_stats(self, name: str,
                            tags: Optional[Dict] = None) -> Dict:
        """获取直方图统计"""
        key = self._make_key(name, tags)
        with self._lock:
            hist = self._histograms.get(key, [])
            if not hist:
                return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
            sorted_hist = sorted(hist)
            n = len(sorted_hist)
            return {
                "count": n,
                "min": sorted_hist[0],
                "max": sorted_hist[-1],
                "avg": sum(sorted_hist) / n,
                "p50": sorted_hist[int(n * 0.5)],
                "p95": sorted_hist[int(n * 0.95)] if n > 1 else sorted_hist[-1],
                "p99": sorted_hist[int(n * 0.99)] if n > 1 else sorted_hist[-1],
            }

    def add_alert(self, rule: AlertRule) -> None:
        """添加告警规则"""
        with self._lock:
            self._alerts[rule.name] = rule

    def on_alert(self, callback: Callable[[str, float, str], None]) -> None:
        """注册告警回调"""
        self._alert_callbacks.append(callback)

    def _check_alerts(self, metric_name: str, value: float) -> None:
        """检查告警规则"""
        now = time.time()
        for rule in self._alerts.values():
            if not rule.enabled or rule.metric_name != metric_name:
                continue
            if now - rule.last_fired < rule.cooldown_s:
                continue

            triggered = False
            if rule.comparison == "gt" and value > rule.threshold:
                triggered = True
            elif rule.comparison == "lt" and value < rule.threshold:
                triggered = True
            elif rule.comparison == "gte" and value >= rule.threshold:
                triggered = True
            elif rule.comparison == "lte" and value <= rule.threshold:
                triggered = True

            if triggered:
                rule.last_fired = now
                msg = f"告警 [{rule.name}]: {metric_name}={value} {rule.comparison} {rule.threshold}"
                logger.warning(msg)
                for cb in self._alert_callbacks:
                    try:
                        cb(rule.name, value, msg)
                    except Exception as e:
                        logger.warning("告警回调异常: %s", e)

    @staticmethod
    def _make_key(name: str, tags: Optional[Dict] = None) -> str:
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}{{{tag_str}}}"

    def get_all_metrics(self) -> Dict:
        """获取所有指标"""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {k: len(v) for k, v in self._histograms.items()},
                "alerts": {k: {"enabled": v.enabled, "threshold": v.threshold}
                           for k, v in self._alerts.items()},
            }


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitConfig:
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_s: float = 30.0
    half_open_max_calls: int = 1


class CircuitBreaker:
    """
    熔断器，防止级联故障。

    三状态：
    - CLOSED: 正常，请求通过
    - OPEN: 熔断，请求被拒绝
    - HALF_OPEN: 半开，允许少量请求测试恢复

    当失败次数超过阈值时熔断，超时后进入半开状态，
    连续成功后恢复。
    """

    def __init__(self, name: str, config: Optional[CircuitConfig] = None):
        self._name = name
        self._config = config or CircuitConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time >= self._config.timeout_s:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self._success_count = 0
            return self._state

    @property
    def name(self) -> str:
        return self._name

    def allow_request(self) -> bool:
        """是否允许请求通过"""
        state = self.state
        with self._lock:
            if state == CircuitState.CLOSED:
                return True
            elif state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self._config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
            else:
                return False

    def record_success(self) -> None:
        """记录成功"""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self) -> None:
        """记录失败"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self._config.failure_threshold:
                    self._state = CircuitState.OPEN

    def get_info(self) -> dict:
        """获取熔断器信息"""
        with self._lock:
            return {
                "name": self._name,
                "state": self.state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "last_failure_time": self._last_failure_time,
            }


class OptimizationConfig:
    """
    优化配置中心，统一管理所有优化模块的配置。

    支持：
    - 分层配置（默认 → 环境变量 → 运行时覆盖）
    - 热更新（运行时修改配置）
    - 配置验证
    - 配置快照
    """

    _DEFAULTS = {
        "query_guard.enabled": True,
        "query_guard.max_channels": 10,
        "memory_taxonomy.enabled": True,
        "memory_taxonomy.auto_classify": True,
        "memory_truncation.max_lines": 200,
        "memory_truncation.max_bytes": 25000,
        "memory_truncation.stale_days": 30.0,
        "memory_drift.enabled": True,
        "memory_drift.warning_days": 7.0,
        "enterprise_retry.max_retries": 3,
        "enterprise_retry.base_delay_ms": 1000,
        "enterprise_retry.max_delay_ms": 60000,
        "enterprise_retry.jitter_range": 0.25,
        "circular_buffer.default_capacity": 100,
        "context_isolation.enabled": True,
        "abort_controller.enabled": True,
        "activity_manager.enabled": True,
        "activity_manager.user_timeout_s": 5.0,
        "metrics.enabled": True,
        "metrics.max_points": 10000,
        "circuit_breaker.failure_threshold": 5,
        "circuit_breaker.timeout_s": 30.0,
    }

    def __init__(self):
        self._config: Dict[str, Any] = dict(self._DEFAULTS)
        self._overrides: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._change_callbacks: List[Callable[[str, Any, Any], None]] = []

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        with self._lock:
            if key in self._overrides:
                return self._overrides[key]
            return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置配置值（运行时覆盖）"""
        with self._lock:
            old = self._overrides.get(key)
            self._overrides[key] = value
        for cb in self._change_callbacks:
            try:
                cb(key, old, value)
            except Exception as e:
                logger.warning("配置变更回调异常: %s", e)

    def reset(self, key: str) -> None:
        """重置配置值到默认"""
        with self._lock:
            self._overrides.pop(key, None)

    def reset_all(self) -> None:
        """重置所有覆盖"""
        with self._lock:
            self._overrides.clear()

    def on_change(self, callback: Callable[[str, Any, Any], None]) -> None:
        """注册配置变更回调"""
        self._change_callbacks.append(callback)

    def snapshot(self) -> Dict[str, Any]:
        """创建配置快照"""
        with self._lock:
            result = dict(self._config)
            result.update(self._overrides)
            return result

    def get_defaults(self) -> Dict[str, Any]:
        """获取默认配置"""
        return dict(self._DEFAULTS)

    def get_overrides(self) -> Dict[str, Any]:
        """获取覆盖配置"""
        with self._lock:
            return dict(self._overrides)

    def validate(self, key: str, value: Any) -> bool:
        """验证配置值"""
        numeric_keys = {
            "query_guard.max_channels",
            "memory_truncation.max_lines",
            "memory_truncation.max_bytes",
            "memory_truncation.stale_days",
            "enterprise_retry.max_retries",
            "enterprise_retry.base_delay_ms",
            "enterprise_retry.max_delay_ms",
            "circular_buffer.default_capacity",
            "activity_manager.user_timeout_s",
            "metrics.max_points",
            "circuit_breaker.failure_threshold",
            "circuit_breaker.timeout_s",
        }
        bool_keys = {
            "query_guard.enabled",
            "memory_taxonomy.enabled",
            "memory_taxonomy.auto_classify",
            "memory_drift.enabled",
            "context_isolation.enabled",
            "abort_controller.enabled",
            "activity_manager.enabled",
            "metrics.enabled",
        }

        if key in numeric_keys:
            return isinstance(value, (int, float)) and value >= 0
        if key in bool_keys:
            return isinstance(value, bool)
        return True


class OptimizationCenter:
    """
    优化中心，整合所有优化模块的统一入口。

    提供：
    - 统一初始化
    - 性能监控集成
    - 熔断器管理
    - 配置管理
    - 健康检查
    - 统计聚合
    """

    def __init__(self):
        self._metrics = MetricsCollector()
        self._config = OptimizationConfig()
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._initialized = False
        self._init_time: Optional[float] = None
        self._lock = threading.Lock()

    def initialize(self) -> None:
        """初始化优化中心"""
        if self._initialized:
            return

        self._init_time = time.time()
        self._metrics.increment("optimization.center.initialized")

        self._metrics.add_alert(AlertRule(
            name="high_error_rate",
            metric_name="errors.total",
            threshold=100,
            comparison="gt",
            cooldown_s=300.0,
        ))

        self._metrics.add_alert(AlertRule(
            name="slow_response",
            metric_name="response.time_ms",
            threshold=5000,
            comparison="gt",
            cooldown_s=60.0,
        ))

        self._initialized = True
        logger.info("优化中心初始化完成")

    @property
    def metrics(self) -> MetricsCollector:
        return self._metrics

    @property
    def config(self) -> OptimizationConfig:
        return self._config

    def get_circuit_breaker(self, name: str,
                            config: Optional[CircuitConfig] = None) -> CircuitBreaker:
        """获取或创建熔断器"""
        with self._lock:
            if name not in self._circuit_breakers:
                self._circuit_breakers[name] = CircuitBreaker(name, config)
            return self._circuit_breakers[name]

    def health_check(self) -> Dict:
        """健康检查"""
        uptime = time.time() - self._init_time if self._init_time else 0

        circuit_health = {}
        for name, cb in self._circuit_breakers.items():
            info = cb.get_info()
            circuit_health[name] = info["state"]

        open_circuits = sum(1 for s in circuit_health.values() if s == "open")

        status = "healthy"
        if open_circuits > 0:
            status = "degraded"
        if open_circuits > 3:
            status = "unhealthy"

        return {
            "status": status,
            "uptime_s": round(uptime, 2),
            "initialized": self._initialized,
            "circuit_breakers": circuit_health,
            "open_circuits": open_circuits,
            "config_overrides": len(self._config.get_overrides()),
        }

    def get_full_statistics(self) -> Dict:
        """获取完整统计"""
        return {
            "health": self.health_check(),
            "metrics": self._metrics.get_all_metrics(),
            "config": {
                "defaults_count": len(self._config.get_defaults()),
                "overrides_count": len(self._config.get_overrides()),
            },
            "circuit_breakers": {
                name: cb.get_info()
                for name, cb in self._circuit_breakers.items()
            },
        }


_optimization_center: Optional[OptimizationCenter] = None


def get_optimization_center() -> OptimizationCenter:
    """获取优化中心单例"""
    global _optimization_center
    if _optimization_center is None:
        _optimization_center = OptimizationCenter()
        _optimization_center.initialize()
    return _optimization_center
