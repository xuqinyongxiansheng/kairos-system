"""
自动梦境服务（Auto Dream）
借鉴 cc-haha-main 的 autoDream 架构：
1. 空闲检测与自动触发 — 基于活动监控的智能调度
2. 知识整合闭环 — 记忆提取→梦境分析→洞察回写
3. 四阶段梦境周期 — 浅扫描/深整合/创造性REM/觉醒整理
4. 洞察审批机制 — 产出洞察需评估后回写长期记忆

完全重写实现
"""

import os
import json
import time
import logging
import asyncio
import threading
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field, asdict
from collections import deque

logger = logging.getLogger("AutoDream")

DREAM_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "dreams")
MAX_DREAM_HISTORY = 100


class DreamPhase(Enum):
    LIGHT_SCAN = "light_scan"
    DEEP_CONSOLIDATE = "deep_consolidate"
    CREATIVE_REM = "creative_rem"
    AWAKENING = "awakening"


@dataclass
class DreamInsight:
    insight_id: str = ""
    insight_type: str = "pattern"
    content: str = ""
    confidence: float = 0.5
    source_memories: List[str] = field(default_factory=list)
    source_dream_id: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    approved: bool = False

    def __post_init__(self):
        if not self.insight_id:
            self.insight_id = f"ins_{int(time.time() * 1000)}_{hash(self.content[:50].encode()) % 10000:04d}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DreamReport:
    dream_id: str = ""
    phase: str = "light_scan"
    duration_seconds: float = 0.0
    memories_processed: int = 0
    insights_produced: List[Dict[str, Any]] = field(default_factory=list)
    associations_built: int = 0
    memories_consolidated: int = 0
    emotional_summary: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["phase"] = self.phase
        return d


@dataclass
class IdleState:
    is_idle: bool = False
    idle_duration_seconds: float = 0.0
    last_activity_time: float = field(default_factory=time.time)
    pending_task_count: int = 0
    memory_load: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DreamSchedule:
    min_idle_seconds: float = 300.0
    max_dream_duration_seconds: float = 600.0
    interval_seconds: float = 1800.0
    memory_threshold: float = 0.6
    enable_deep_consolidate: bool = True
    enable_creative_rem: bool = True
    max_insights_per_dream: int = 10

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class IdleDetector:
    """空闲检测器"""

    def __init__(self):
        self._last_activity_time = time.time()
        self._lock = threading.Lock()
        self._activity_count = 0

    def record_activity(self):
        """记录活动事件"""
        with self._lock:
            self._last_activity_time = time.time()
            self._activity_count += 1

    async def get_idle_state(self) -> IdleState:
        """获取当前空闲状态"""
        with self._lock:
            now = time.time()
            idle_duration = now - self._last_activity_time
            return IdleState(
                is_idle=idle_duration > 60,
                idle_duration_seconds=idle_duration,
                last_activity_time=self._last_activity_time,
                pending_task_count=0,
                memory_load=min(1.0, self._activity_count / 1000.0),
            )


class DreamScheduler:
    """梦境调度器"""

    def __init__(self, schedule: DreamSchedule = None):
        self.schedule = schedule or DreamSchedule()
        self.idle_detector = IdleDetector()
        self._is_running = False
        self._dream_history: deque = deque(maxlen=MAX_DREAM_HISTORY)
        self._pending_insights: Dict[str, DreamInsight] = {}
        self._lock = threading.RLock()
        self._chat_fn = None
        os.makedirs(DREAM_DATA_DIR, exist_ok=True)
        self._load_history()

    def _load_history(self):
        """加载历史梦境记录"""
        history_file = os.path.join(DREAM_DATA_DIR, "history.jsonl")
        if not os.path.exists(history_file):
            return
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            report = DreamReport(**json.loads(line))
                            self._dream_history.append(report)
                        except Exception:
                            pass
        except Exception:
            pass

    def _save_report(self, report: DreamReport):
        """追加写入梦境报告"""
        history_file = os.path.join(DREAM_DATA_DIR, "history.jsonl")
        try:
            with open(history_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(report.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"保存梦境报告失败: {e}")

    def set_chat_fn(self, chat_fn: Callable[[str], Any]):
        """设置LLM聊天函数"""
        self._chat_fn = chat_fn

    def _should_dream(self, idle_state: IdleState) -> bool:
        """判断是否应该进入梦境"""
        if not self.schedule.enable_deep_consolidate and not self.schedule.enable_creative_rem:
            return False
        return (
            idle_state.is_idle and
            idle_state.idle_duration_seconds >= self.schedule.min_idle_seconds and
            idle_state.memory_load >= self.schedule.memory_threshold * 0.3
        )

    async def _call_llm(self, prompt: str, timeout: float = 30.0) -> str:
        """调用LLM，带超时保护"""
        if not self._chat_fn:
            return ""
        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: self._chat_fn(prompt)),
                timeout=timeout,
            )
            return str(result) if result else ""
        except asyncio.TimeoutError:
            logger.warning("LLM调用超时")
            return ""
        except Exception as e:
            logger.debug(f"LLM调用失败: {e}")
            return ""

    async def _light_scan_phase(self) -> List[DreamInsight]:
        """浅扫描阶段：快速浏览工作记忆，提取高频模式"""
        insights = []
        try:
            from kairos.services.memory_extract import get_memory_extractor
            me = get_memory_extractor()
            memories = me.load_memories(None)[:20]
            
            if not memories:
                return insights
            
            content_samples = [m.get("content", "")[:200] for m in memories[:10]]
            combined = "\n".join(content_samples)
            
            prompt = f"""分析以下记忆片段中的高频模式和主题：
{combined}
请输出2-3个关键模式发现，每行一个，格式：[类型] 描述。类型可选：pattern/association/metaphor/prediction"""
            
            response = await self._call_llm(prompt, timeout=15.0)
            if response:
                for line in response.split("\n"):
                    line = line.strip()
                    if line.startswith("["):
                        insight_type = "pattern"
                        if "[association]" in line.lower():
                            insight_type = "association"
                        elif "[metaphor]" in line.lower():
                            insight_type = "metaphor"
                        elif "[prediction]" in line.lower():
                            insight_type = "prediction"
                        content = re.sub(r'^\[\w+\]\s*', '', line).strip()
                        if content:
                            insights.append(DreamInsight(
                                insight_type=insight_type,
                                content=content,
                                confidence=0.6,
                                source_memories=[m.get("id", "") for m in memories[:5]],
                                tags=["light_scan", insight_type],
                            ))
        except Exception as e:
            logger.debug(f"浅扫描阶段失败: {e}")
        
        return insights[:self.schedule.max_insights_per_dream]

    async def _deep_consolidate_phase(self) -> List[DreamInsight]:
        """深整合阶段：深度关联长期记忆"""
        insights = []
        if not self.schedule.enable_deep_consolidate:
            return insights
        
        try:
            from kairos.services.memory_extract import get_memory_extractor
            me = get_memory_extractor()
            all_memories = me.load_memories(None)
            
            if len(all_memories) < 5:
                return insights
            
            topics = set()
            for m in all_memories[:30]:
                tags = m.get("tags", [])
                topics.update(tags[:3])
            
            topic_list = list(topics)[:8]
            if topic_list:
                prompt = f"""基于以下主题列表，分析可能的跨领域知识关联：
主题: {', '.join(topic_list)}
请输出1-2个跨领域关联发现，格式：[关联] 主题A <-> 主题B : 关联原因"""
                
                response = await self._call_llm(prompt, timeout=15.0)
                if response:
                    for line in response.split("\n"):
                        line = line.strip()
                        if line.startswith("[关联]") or line.startswith("[association]"):
                            content = re.sub(r'^\[\w+\]\s*', '', line).strip()
                            if content:
                                insights.append(DreamInsight(
                                    insight_type="association",
                                    content=f"跨领域关联: {content}",
                                    confidence=0.7,
                                    tags=["deep_consolidate", "cross_domain"],
                                ))
        except Exception as e:
            logger.debug(f"深整合阶段失败: {e}")
        
        return insights[:3]

    async def _creative_rem_phase(self) -> List[DreamInsight]:
        """创造性REM阶段：生成创新组合和新视角"""
        insights = []
        if not self.schedule.enable_creative_rem:
            return insights
        
        try:
            from kairos.services.bootstrap import get_bootstrap_state
            bs = get_bootstrap_state()
            state = bs.get_full_state()
            mode = state.get("mode", "default")
            interaction_count = state.get("interaction_count", 0)
            
            prompt = f"""作为鸿蒙小雨智能系统，当前运行模式为{mode}，已完成{interaction_count}次交互。
请基于此状态，提出1-2个可能的能力提升方向或新功能创意。
格式：[创意] 简短描述。每个创意不超过50字。"""
            
            response = await self._call_llm(prompt, timeout=20.0)
            if response:
                for line in response.split("\n"):
                    line = line.strip()
                    if line.startswith("[创意]") or line.startswith("[creativity]") or line.startswith("[idea]"):
                        content = re.sub(r'^\[\w+\]\s*', '', line).strip()
                        if content:
                            insights.append(DreamInsight(
                                insight_type="prediction",
                                content=f"创新视角: {content}",
                                confidence=0.5,
                                tags=["creative_rem", "innovation"],
                            ))
        except Exception as e:
            logger.debug(f"创造性REM阶段失败: {e}")
        
        return insights[:3]

    async def _awakening_phase(self, all_insights: List[DreamInsight]) -> DreamReport:
        """觉醒阶段：整理产出并生成报告"""
        dream_id = f"dream_{int(time.time())}"
        
        approved_insights = []
        for insight in all_insights:
            if insight.confidence >= 0.7:
                insight.approved = True
                approved_insights.append(insight)
                self._pending_insights[insight.insight_id] = insight
            else:
                self._pending_insights[insight.insight_id] = insight
        
        total_confidence = sum(i.confidence for i in all_insights) / max(len(all_insights), 1)
        if total_confidence > 0.65:
            emotional_summary = "积极整合"
        elif total_confidence > 0.4:
            emotional_summary = "中性整理"
        else:
            emotional_summary = "需要更多素材"

        report = DreamReport(
            dream_id=dream_id,
            phase="awakening",
            duration_seconds=0.0,
            memories_processed=len(all_insights),
            insights_produced=[i.to_dict() for i in all_insights],
            associations_built=sum(1 for i in all_insights if i.insight_type == "association"),
            memories_consolidated=sum(1 for i in all_insights if i.confidence >= 0.7),
            emotional_summary=emotional_summary,
        )
        
        with self._lock:
            self._dream_history.append(report)
            self._save_report(report)
        
        return report

    async def execute_dream_cycle(self) -> Optional[DreamReport]:
        """执行完整梦境周期"""
        start_time = time.time()
        logger.info("开始执行梦境周期")
        
        all_insights = []
        
        stage1 = await self._light_scan_phase()
        all_insights.extend(stage1)
        logger.info(f"浅扫描阶段: {len(stage1)} 个洞察")
        
        stage2 = await self._deep_consolidate_phase()
        all_insights.extend(stage2)
        logger.info(f"深整合阶段: {len(stage2)} 个洞察")
        
        stage3 = await self._creative_rem_phase()
        all_insights.extend(stage3)
        logger.info(f"创造性REM阶段: {len(stage3)} 个洞察")
        
        report = await self._awakening_phase(all_insights)
        report.duration_seconds = time.time() - start_time
        logger.info(f"梦境周期完成: {report.duration_seconds:.1f}s, {len(all_insights)} 个洞察")
        
        return report

    async def force_dream(self) -> Optional[DreamReport]:
        """强制触发一次梦境"""
        return await self.execute_dream_cycle()

    async def run_loop(self):
        """调度主循环"""
        self._is_running = True
        logger.info(f"自动梦境服务启动 (最小空闲={self.schedule.min_idle_seconds}s, 间隔={self.schedule.interval_seconds}s)")
        
        while self._is_running:
            try:
                idle_state = await self.idle_detector.get_idle_state()
                
                if self._should_dream(idle_state):
                    logger.info(f"空闲 {idle_state.idle_duration_seconds:.0f}s, 触发梦境周期")
                    await self.execute_dream_cycle()
                
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"梦境调度循环异常: {e}")
                await asyncio.sleep(120)
        
        self._is_running = False
        logger.info("自动梦境服务已停止")

    def stop(self):
        """停止调度"""
        self._is_running = False

    async def get_idle_state(self) -> IdleState:
        """获取当前空闲状态"""
        return await self.idle_detector.get_idle_state()

    def get_dream_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取梦境历史"""
        with self._lock:
            history = list(reversed(self._dream_history))
            return [r.to_dict() for r in history[:limit]]

    def get_pending_insights(self) -> List[Dict[str, Any]]:
        """获取待处理的洞察"""
        with self._lock:
            return [i.to_dict() for i in self._pending_insights.values()]

    def approve_insight(self, insight_id: str) -> bool:
        """批准洞察"""
        with self._lock:
            insight = self._pending_insights.get(insight_id)
            if insight:
                insight.approved = True
                try:
                    from kairos.services.memory_extract import get_memory_extractor
                    me = get_memory_extractor()
                    me.extract([{"role": "system", "content": f"[梦境洞察] {insight.content}"}])
                except Exception:
                    pass
                return True
            return False

    def reject_insight(self, insight_id: str) -> bool:
        """拒绝洞察"""
        with self._lock:
            if insight_id in self._pending_insights:
                del self._pending_insights[insight_id]
                return True
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取梦境统计"""
        with self._lock:
            return {
                "is_running": self._is_running,
                "total_dreams": len(self._dream_history),
                "pending_insights": len(self._pending_insights),
                "approved_insights": sum(1 for i in self._pending_insights.values() if i.approved),
                "schedule": self.schedule.to_dict(),
                "idle_state": {"idle_duration": time.time() - self.idle_detector._last_activity_time},
            }


_auto_dream_service: Optional[DreamScheduler] = None


def get_auto_dream_service() -> DreamScheduler:
    global _auto_dream_service
    if _auto_dream_service is None:
        _auto_dream_service = DreamScheduler()
    return _auto_dream_service
