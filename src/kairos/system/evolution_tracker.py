#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
进化追踪模块

核心功能：
1. 进化事件记录（记录系统成长历程中的重要事件）
2. 能力提升跟踪（跟踪各技能领域的能力变化）
3. 里程碑管理（设定和追踪重要的进化里程碑）
4. 进化趋势分析（分析系统成长趋势和模式）
5. 成长轨迹可视化（生成成长轨迹数据）
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import os
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger("EvolutionTracker")


class EventType(Enum):
    """事件类型"""
    CAPABILITY_IMPROVEMENT = "capability_improvement"
    SKILL_ACQUIRED = "skill_acquired"
    PROJECT_COMPLETED = "project_completed"
    KNOWLEDGE_ADDED = "knowledge_added"
    LEARNING_GOAL_ACHIEVED = "learning_goal_achieved"
    MILESTONE_REACHED = "milestone_reached"
    SYSTEM_UPGRADE = "system_upgrade"
    PERFORMANCE_IMPROVED = "performance_improved"


class MilestoneType(Enum):
    """里程碑类型"""
    CAPABILITY = "capability"
    SKILL = "skill"
    KNOWLEDGE = "knowledge"
    PROJECT = "project"
    LEARNING = "learning"
    SYSTEM = "system"


class GrowthMetric(Enum):
    """成长指标类型"""
    CAPABILITY_SCORE = "capability_score"
    SKILL_LEVEL = "skill_level"
    KNOWLEDGE_VOLUME = "knowledge_volume"
    PROJECT_COMPLETIONS = "project_completions"
    LEARNING_HOURS = "learning_hours"
    SYSTEM_PERFORMANCE = "system_performance"


@dataclass
class EvolutionEvent:
    """进化事件数据类"""
    id: str
    event_type: EventType
    title: str
    description: str
    timestamp: str
    metrics: Dict[str, float]
    related_entities: List[str]
    tags: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "title": self.title,
            "description": self.description,
            "timestamp": self.timestamp,
            "metrics": self.metrics,
            "related_entities": self.related_entities,
            "tags": self.tags
        }


@dataclass
class EvolutionMilestone:
    """进化里程碑数据类"""
    id: str
    name: str
    description: str
    milestone_type: MilestoneType
    target_value: float
    current_value: float
    deadline: str
    status: str
    created_at: str
    achieved_at: Optional[str] = None
    related_events: List[str] = None
    
    def __post_init__(self):
        if self.related_events is None:
            self.related_events = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "milestone_type": self.milestone_type.value,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "deadline": self.deadline,
            "status": self.status,
            "created_at": self.created_at,
            "achieved_at": self.achieved_at,
            "related_events": self.related_events
        }


@dataclass
class GrowthRecord:
    """成长记录数据类"""
    metric_type: GrowthMetric
    timestamp: str
    value: float
    event_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "metric_type": self.metric_type.value,
            "timestamp": self.timestamp,
            "value": self.value,
            "event_id": self.event_id
        }


class EvolutionTracker:
    """进化追踪模块"""
    
    def __init__(self, config: Dict = None, agent = None):
        """初始化进化追踪模块"""
        self.config = config or {}
        self.agent = agent
        
        self.events: Dict[str, EvolutionEvent] = {}
        self.milestones: Dict[str, EvolutionMilestone] = {}
        self.growth_records: Dict[str, List[GrowthRecord]] = {}
        
        data_dir = self.config.get("data_dir", "./data/evolution")
        self.events_file = os.path.join(data_dir, "evolution_events.json")
        self.milestones_file = os.path.join(data_dir, "evolution_milestones.json")
        self.growth_file = os.path.join(data_dir, "growth_records.json")
        
        self._load_data()
        
        logger.info("进化追踪模块初始化完成")
    
    def _load_data(self):
        """加载进化数据"""
        try:
            if os.path.exists(self.events_file):
                with open(self.events_file, "r", encoding="utf-8") as f:
                    events_data = json.load(f)
                    for event_id, event_data in events_data.items():
                        self.events[event_id] = EvolutionEvent(
                            id=event_data["id"],
                            event_type=EventType(event_data["event_type"]),
                            title=event_data["title"],
                            description=event_data["description"],
                            timestamp=event_data["timestamp"],
                            metrics=event_data["metrics"],
                            related_entities=event_data["related_entities"],
                            tags=event_data["tags"]
                        )
            
            if os.path.exists(self.milestones_file):
                with open(self.milestones_file, "r", encoding="utf-8") as f:
                    milestones_data = json.load(f)
                    for milestone_id, milestone_data in milestones_data.items():
                        self.milestones[milestone_id] = EvolutionMilestone(
                            id=milestone_data["id"],
                            name=milestone_data["name"],
                            description=milestone_data["description"],
                            milestone_type=MilestoneType(milestone_data["milestone_type"]),
                            target_value=milestone_data["target_value"],
                            current_value=milestone_data["current_value"],
                            deadline=milestone_data["deadline"],
                            status=milestone_data["status"],
                            created_at=milestone_data["created_at"],
                            achieved_at=milestone_data["achieved_at"],
                            related_events=milestone_data["related_events"]
                        )
            
            if os.path.exists(self.growth_file):
                with open(self.growth_file, "r", encoding="utf-8") as f:
                    growth_data = json.load(f)
                    for metric_type, records in growth_data.items():
                        self.growth_records[metric_type] = [
                            GrowthRecord(
                                metric_type=GrowthMetric(record["metric_type"]),
                                timestamp=record["timestamp"],
                                value=record["value"],
                                event_id=record["event_id"]
                            )
                            for record in records
                        ]
        
        except Exception as e:
            logger.error(f"加载进化数据失败: {e}")
    
    def _save_data(self):
        """保存进化数据"""
        try:
            os.makedirs(os.path.dirname(self.events_file), exist_ok=True)
            
            events_data = {event_id: event.to_dict() for event_id, event in self.events.items()}
            with open(self.events_file, "w", encoding="utf-8") as f:
                json.dump(events_data, f, ensure_ascii=False, indent=2)
            
            milestones_data = {mid: milestone.to_dict() for mid, milestone in self.milestones.items()}
            with open(self.milestones_file, "w", encoding="utf-8") as f:
                json.dump(milestones_data, f, ensure_ascii=False, indent=2)
            
            growth_data = {}
            for metric_type, records in self.growth_records.items():
                growth_data[metric_type] = [record.to_dict() for record in records]
            with open(self.growth_file, "w", encoding="utf-8") as f:
                json.dump(growth_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"保存进化数据失败: {e}")
    
    async def record_evolution_event(self, event_data: Dict[str, Any]) -> EvolutionEvent:
        """记录进化事件"""
        try:
            event_id = f"event_{int(datetime.now().timestamp())}"
            
            event = EvolutionEvent(
                id=event_id,
                event_type=EventType(event_data.get("event_type", EventType.CAPABILITY_IMPROVEMENT.value)),
                title=event_data.get("title", f"进化事件-{event_id}"),
                description=event_data.get("description", ""),
                timestamp=datetime.now().isoformat(),
                metrics=event_data.get("metrics", {}),
                related_entities=event_data.get("related_entities", []),
                tags=event_data.get("tags", [])
            )
            
            self.events[event_id] = event
            
            await self._update_milestones(event)
            await self._add_growth_records(event)
            
            self._save_data()
            
            return event
            
        except Exception as e:
            logger.error(f"记录进化事件失败: {e}")
            raise
    
    async def _update_milestones(self, event: EvolutionEvent):
        """更新相关里程碑"""
        for milestone_id, milestone in self.milestones.items():
            if milestone.status in ["pending", "in_progress"]:
                if any(entity in milestone.id for entity in event.related_entities):
                    if event.event_type == EventType.CAPABILITY_IMPROVEMENT:
                        if "capability_score" in event.metrics:
                            milestone.current_value = event.metrics["capability_score"]
                    elif event.event_type == EventType.SKILL_ACQUIRED:
                        if "skill_level" in event.metrics:
                            milestone.current_value = event.metrics["skill_level"]
                    
                    if milestone.current_value >= milestone.target_value:
                        milestone.status = "achieved"
                        milestone.achieved_at = datetime.now().isoformat()
                        milestone.related_events.append(event.id)
    
    async def _add_growth_records(self, event: EvolutionEvent):
        """添加成长记录"""
        for metric_name, value in event.metrics.items():
            metric_type = None
            
            if "capability" in metric_name.lower():
                metric_type = GrowthMetric.CAPABILITY_SCORE
            elif "skill" in metric_name.lower():
                metric_type = GrowthMetric.SKILL_LEVEL
            elif "knowledge" in metric_name.lower():
                metric_type = GrowthMetric.KNOWLEDGE_VOLUME
            elif "project" in metric_name.lower():
                metric_type = GrowthMetric.PROJECT_COMPLETIONS
            elif "learning" in metric_name.lower():
                metric_type = GrowthMetric.LEARNING_HOURS
            elif "performance" in metric_name.lower():
                metric_type = GrowthMetric.SYSTEM_PERFORMANCE
            
            if metric_type:
                record = GrowthRecord(
                    metric_type=metric_type,
                    timestamp=event.timestamp,
                    value=value,
                    event_id=event.id
                )
                
                metric_key = metric_type.value
                if metric_key not in self.growth_records:
                    self.growth_records[metric_key] = []
                self.growth_records[metric_key].append(record)
    
    async def add_milestone(self, milestone_data: Dict[str, Any]) -> EvolutionMilestone:
        """添加进化里程碑"""
        try:
            milestone_id = f"milestone_{int(datetime.now().timestamp())}"
            
            milestone = EvolutionMilestone(
                id=milestone_id,
                name=milestone_data.get("name", f"里程碑-{milestone_id}"),
                description=milestone_data.get("description", ""),
                milestone_type=MilestoneType(milestone_data.get("milestone_type", MilestoneType.CAPABILITY.value)),
                target_value=milestone_data.get("target_value", 0.0),
                current_value=milestone_data.get("current_value", 0.0),
                deadline=milestone_data.get("deadline", (datetime.now() + timedelta(days=30)).isoformat()),
                status="pending",
                created_at=datetime.now().isoformat()
            )
            
            self.milestones[milestone_id] = milestone
            self._save_data()
            
            return milestone
            
        except Exception as e:
            logger.error(f"添加进化里程碑失败: {e}")
            raise
    
    async def update_milestone(self, milestone_id: str, updates: Dict[str, Any]) -> EvolutionMilestone:
        """更新进化里程碑"""
        milestone = self.milestones.get(milestone_id)
        if not milestone:
            raise ValueError(f"进化里程碑不存在: {milestone_id}")
        
        if "name" in updates:
            milestone.name = updates["name"]
        if "description" in updates:
            milestone.description = updates["description"]
        if "target_value" in updates:
            milestone.target_value = updates["target_value"]
        if "current_value" in updates:
            milestone.current_value = updates["current_value"]
        if "deadline" in updates:
            milestone.deadline = updates["deadline"]
        if "status" in updates:
            milestone.status = updates["status"]
        
        if milestone.current_value >= milestone.target_value and milestone.status == "pending":
            milestone.status = "achieved"
            milestone.achieved_at = datetime.now().isoformat()
        
        self._save_data()
        return milestone
    
    async def get_event(self, event_id: str) -> Optional[EvolutionEvent]:
        """获取进化事件"""
        return self.events.get(event_id)
    
    async def get_milestone(self, milestone_id: str) -> Optional[EvolutionMilestone]:
        """获取进化里程碑"""
        return self.milestones.get(milestone_id)
    
    async def list_events(self, filters: Dict = None) -> List[EvolutionEvent]:
        """列出进化事件"""
        filters = filters or {}
        
        events = list(self.events.values())
        
        if "event_type" in filters:
            events = [e for e in events if e.event_type == EventType(filters["event_type"])]
        
        if "tags" in filters:
            tag_filters = filters["tags"]
            events = [e for e in events if any(tag in tag_filters for tag in e.tags)]
        
        if "start_date" in filters:
            start_date = datetime.fromisoformat(filters["start_date"])
            events = [e for e in events if datetime.fromisoformat(e.timestamp) >= start_date]
        
        if "end_date" in filters:
            end_date = datetime.fromisoformat(filters["end_date"])
            events = [e for e in events if datetime.fromisoformat(e.timestamp) <= end_date]
        
        events.sort(key=lambda x: x.timestamp, reverse=True)
        
        return events
    
    async def list_milestones(self, filters: Dict = None) -> List[EvolutionMilestone]:
        """列出进化里程碑"""
        filters = filters or {}
        
        milestones = list(self.milestones.values())
        
        if "milestone_type" in filters:
            milestones = [m for m in milestones if m.milestone_type == MilestoneType(filters["milestone_type"])]
        
        if "status" in filters:
            milestones = [m for m in milestones if m.status == filters["status"]]
        
        milestones.sort(key=lambda x: (x.status, x.deadline))
        
        return milestones
    
    async def get_growth_data(self, metric_type: GrowthMetric, 
                            start_date: Optional[str] = None, 
                            end_date: Optional[str] = None) -> List[GrowthRecord]:
        """获取成长数据"""
        metric_key = metric_type.value
        if metric_key not in self.growth_records:
            return []
        
        records = self.growth_records[metric_key]
        
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            records = [r for r in records if datetime.fromisoformat(r.timestamp) >= start_dt]
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            records = [r for r in records if datetime.fromisoformat(r.timestamp) <= end_dt]
        
        records.sort(key=lambda x: x.timestamp)
        
        return records
    
    async def analyze_growth_trend(self, metric_type: GrowthMetric, 
                                period: str = "month") -> Dict[str, Any]:
        """分析成长趋势"""
        records = await self.get_growth_data(metric_type)
        
        if not records:
            return {"error": "没有足够的成长数据"}
        
        values = [r.value for r in records]
        
        trend_data = {
            "metric_type": metric_type.value,
            "data_points": len(records),
            "time_range": {
                "start": records[0].timestamp,
                "end": records[-1].timestamp
            },
            "statistics": {
                "min": min(values),
                "max": max(values),
                "average": sum(values) / len(values),
                "total_change": values[-1] - values[0],
                "percentage_change": ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0
            }
        }
        
        return trend_data
    
    async def generate_evolution_report(self, period: str = "all") -> Dict[str, Any]:
        """生成进化报告"""
        end_date = datetime.now()
        if period == "week":
            start_date = end_date - timedelta(days=7)
        elif period == "month":
            start_date = end_date - timedelta(days=30)
        elif period == "quarter":
            start_date = end_date - timedelta(days=90)
        else:
            start_date = datetime(2000, 1, 1)
        
        events = await self.list_events({
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        })
        
        milestones = await self.list_milestones()
        achieved_milestones = [m for m in milestones if m.status == "achieved"]
        
        return {
            "report_period": period,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_events": len(events),
                "total_milestones": len(milestones),
                "achieved_milestones": len(achieved_milestones)
            },
            "recent_events": [e.to_dict() for e in events[:10]]
        }
    
    async def get_evolution_timeline(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取进化时间线"""
        events = await self.list_events()
        
        timeline = []
        for event in events[:limit]:
            timeline.append({
                "timestamp": event.timestamp,
                "type": event.event_type.value,
                "title": event.title,
                "description": event.description,
                "metrics": event.metrics,
                "tags": event.tags
            })
        
        return timeline


_evolution_tracker_instance = None


def get_evolution_tracker(config: Dict = None, agent = None) -> EvolutionTracker:
    """获取进化追踪模块实例"""
    global _evolution_tracker_instance
    
    if _evolution_tracker_instance is None:
        _evolution_tracker_instance = EvolutionTracker(config=config, agent=agent)
    
    return _evolution_tracker_instance
