"""
自我学习增强模块 - 整合 OpenClaw 和 Hermes Agent 机制

设计理念:
- OpenClaw: 递归式技能进化、自我改进循环、实时权重更新
- Hermes Agent: 四阶段学习、闭环学习循环、Atropos强化学习

核心能力:
1. 任务执行 → 结果分析 → 改进识别 → 代码生成 → 测试部署
2. 经验抽象 → 技能沉淀 → 版本管理 → 进化追踪
3. 性能监控 → 自动分类 → 优化排序 → 持续改进
"""

import json
import os
import re
import time
import hashlib
import threading
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class LearningPhase(Enum):
    """学习阶段 - 整合 Hermes 四阶段"""
    EXECUTION = "execution"
    EVALUATION = "evaluation"
    ABSTRACTION = "abstraction"
    STORAGE = "storage"


class ImprovementType(Enum):
    """改进类型 - 整合 OpenClaw 自我改进"""
    SKILL_NEW = "skill_new"
    SKILL_ENHANCE = "skill_enhance"
    PROMPT_OPTIMIZE = "prompt_optimize"
    TOOL_ADD = "tool_add"
    CODE_FIX = "code_fix"
    KNOWLEDGE_UPDATE = "knowledge_update"


class FeedbackType(Enum):
    """反馈类型"""
    EXPLICIT_POSITIVE = "explicit_positive"
    EXPLICIT_NEGATIVE = "explicit_negative"
    IMPLICIT_ACCEPT = "implicit_accept"
    IMPLICIT_CORRECT = "implicit_correct"
    ERROR_RECOVERY = "error_recovery"


@dataclass
class ExecutionRecord:
    """执行记录 - OpenClaw 风格"""
    id: str
    task: str
    actions: List[Dict[str, Any]]
    result: str
    success: bool
    duration: float
    tools_used: List[str]
    errors: List[str] = field(default_factory=list)
    feedback: Optional[FeedbackType] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task": self.task,
            "result": self.result[:500],
            "success": self.success,
            "duration": self.duration,
            "tools_used": self.tools_used,
            "errors": self.errors,
            "feedback": self.feedback.value if self.feedback else None,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class SkillDocument:
    """技能文档 - Hermes SKILL.md 格式"""
    id: str
    name: str
    description: str
    trigger_patterns: List[str]
    execution_steps: List[Dict[str, Any]]
    success_rate: float
    usage_count: int
    version: str
    created_from: str
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_markdown(self) -> str:
        """生成 SKILL.md 格式"""
        return f"""# {self.name}

## 描述
{self.description}

## 触发模式
{chr(10).join(f'- {p}' for p in self.trigger_patterns)}

## 执行步骤
{chr(10).join(f'{i+1}. {s.get("action", "")}' for i, s in enumerate(self.execution_steps))}

## 统计
- 成功率: {self.success_rate:.2%}
- 使用次数: {self.usage_count}
- 版本: {self.version}

## 来源
{self.created_from}

## 更新时间
{self.last_updated.isoformat()}
"""


@dataclass
class ImprovementCandidate:
    """改进候选 - OpenClaw 自我改进"""
    id: str
    type: ImprovementType
    description: str
    impact_score: float
    frequency: int
    priority: float
    code_changes: Optional[str] = None
    test_results: Optional[Dict[str, Any]] = None
    status: str = "pending"


class SelfLearningEnhancer:
    """自我学习增强器 - 整合 OpenClaw + Hermes"""
    
    def __init__(self, data_dir: str = "./data/learning"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.skills_dir = self.data_dir / "skills"
        self.skills_dir.mkdir(exist_ok=True)
        
        self.records_dir = self.data_dir / "records"
        self.records_dir.mkdir(exist_ok=True)
        
        self.execution_history: List[ExecutionRecord] = []
        self.skills: Dict[str, SkillDocument] = {}
        self.improvement_queue: List[ImprovementCandidate] = []
        
        self.performance_metrics = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "skills_created": 0,
            "improvements_applied": 0
        }
        
        self._load_skills()
        
        self._learning_thread = None
        self._running = False
        
        logger.info("自我学习增强器初始化完成")
    
    def _load_skills(self):
        """加载已有技能"""
        for skill_file in self.skills_dir.glob("*.json"):
            try:
                with open(skill_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    skill = SkillDocument(
                        id=data['id'],
                        name=data['name'],
                        description=data['description'],
                        trigger_patterns=data['trigger_patterns'],
                        execution_steps=data['execution_steps'],
                        success_rate=data['success_rate'],
                        usage_count=data['usage_count'],
                        version=data['version'],
                        created_from=data['created_from']
                    )
                    self.skills[skill.id] = skill
            except Exception as e:
                logger.warning(f"加载技能失败: {skill_file}: {e}")
    
    def record_execution(self, task: str, actions: List[Dict], result: str, 
                         success: bool, tools: List[str], errors: List[str] = None) -> ExecutionRecord:
        """记录执行 - OpenClaw 风格"""
        record = ExecutionRecord(
            id=self._generate_id("exec"),
            task=task,
            actions=actions,
            result=result,
            success=success,
            duration=0.0,
            tools_used=tools,
            errors=errors or []
        )
        
        self.execution_history.append(record)
        self.performance_metrics["total_tasks"] += 1
        if success:
            self.performance_metrics["successful_tasks"] += 1
        
        self._save_record(record)
        
        if len(self.execution_history) % 15 == 0:
            self._trigger_review()
        
        return record
    
    def add_feedback(self, record_id: str, feedback: FeedbackType):
        """添加反馈 - Hermes 闭环学习"""
        for record in self.execution_history:
            if record.id == record_id:
                record.feedback = feedback
                break
    
    def _trigger_review(self):
        """触发自动复盘 - Hermes 机制"""
        logger.info("触发自动复盘...")
        
        recent_records = self.execution_history[-15:]
        
        success_rate = sum(1 for r in recent_records if r.success) / len(recent_records)
        
        error_patterns = self._analyze_errors(recent_records)
        
        success_patterns = self._analyze_successes(recent_records)
        
        for pattern in success_patterns:
            if pattern['frequency'] >= 3:
                self._create_skill_candidate(pattern)
        
        for error in error_patterns:
            self._create_improvement_candidate(error)
    
    def _analyze_errors(self, records: List[ExecutionRecord]) -> List[Dict]:
        """分析错误模式"""
        error_patterns = {}
        
        for record in records:
            if not record.success:
                for error in record.errors:
                    key = hashlib.md5(error.encode()).hexdigest()[:8]
                    if key not in error_patterns:
                        error_patterns[key] = {
                            'error': error,
                            'frequency': 0,
                            'contexts': []
                        }
                    error_patterns[key]['frequency'] += 1
                    error_patterns[key]['contexts'].append(record.task)
        
        return list(error_patterns.values())
    
    def _analyze_successes(self, records: List[ExecutionRecord]) -> List[Dict]:
        """分析成功模式"""
        success_patterns = {}
        
        for record in records:
            if record.success:
                key = hashlib.md5(record.task.encode()).hexdigest()[:8]
                if key not in success_patterns:
                    success_patterns[key] = {
                        'task_pattern': record.task,
                        'actions': record.actions,
                        'tools': record.tools_used,
                        'frequency': 0
                    }
                success_patterns[key]['frequency'] += 1
        
        return list(success_patterns.values())
    
    def _create_skill_candidate(self, pattern: Dict):
        """创建技能候选 - Hermes 技能沉淀"""
        skill_id = self._generate_id("skill")
        skill = SkillDocument(
            id=skill_id,
            name=f"auto_skill_{skill_id[:6]}",
            description=f"自动生成技能: {pattern['task_pattern'][:50]}",
            trigger_patterns=[pattern['task_pattern']],
            execution_steps=pattern['actions'],
            success_rate=1.0,
            usage_count=pattern['frequency'],
            version="1.0.0",
            created_from="auto_generation"
        )
        
        self.skills[skill_id] = skill
        self._save_skill(skill)
        self.performance_metrics["skills_created"] += 1
        
        logger.info(f"创建新技能: {skill.name}")
    
    def _create_improvement_candidate(self, error_pattern: Dict):
        """创建改进候选 - OpenClaw 自我改进"""
        improvement = ImprovementCandidate(
            id=self._generate_id("improve"),
            type=ImprovementType.CODE_FIX,
            description=f"修复错误: {error_pattern['error'][:100]}",
            impact_score=error_pattern['frequency'] * 0.5,
            frequency=error_pattern['frequency'],
            priority=error_pattern['frequency'] * 0.5
        )
        
        self.improvement_queue.append(improvement)
        self.improvement_queue.sort(key=lambda x: x.priority, reverse=True)
    
    def get_skill_for_task(self, task: str) -> Optional[SkillDocument]:
        """获取适用于任务的技能"""
        for skill in self.skills.values():
            for pattern in skill.trigger_patterns:
                if pattern.lower() in task.lower():
                    return skill
        return None
    
    def get_improvement_suggestions(self) -> List[Dict]:
        """获取改进建议"""
        return [
            {
                "id": imp.id,
                "type": imp.type.value,
                "description": imp.description,
                "priority": imp.priority,
                "status": imp.status
            }
            for imp in self.improvement_queue[:10]
        ]
    
    def _save_skill(self, skill: SkillDocument):
        """保存技能"""
        skill_file = self.skills_dir / f"{skill.id}.json"
        with open(skill_file, 'w', encoding='utf-8') as f:
            json.dump({
                'id': skill.id,
                'name': skill.name,
                'description': skill.description,
                'trigger_patterns': skill.trigger_patterns,
                'execution_steps': skill.execution_steps,
                'success_rate': skill.success_rate,
                'usage_count': skill.usage_count,
                'version': skill.version,
                'created_from': skill.created_from
            }, f, ensure_ascii=False, indent=2)
        
        md_file = self.skills_dir / f"{skill.name}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(skill.to_markdown())
    
    def _save_record(self, record: ExecutionRecord):
        """保存执行记录"""
        record_file = self.records_dir / f"{record.id}.json"
        with open(record_file, 'w', encoding='utf-8') as f:
            json.dump(record.to_dict(), f, ensure_ascii=False, indent=2)
    
    def _generate_id(self, prefix: str) -> str:
        """生成ID"""
        content = f"{prefix}:{time.time()}:{len(self.execution_history)}"
        return f"{prefix}_{hashlib.md5(content.encode()).hexdigest()[:12]}"
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "performance": self.performance_metrics,
            "skills_count": len(self.skills),
            "improvement_queue_size": len(self.improvement_queue),
            "recent_success_rate": (
                sum(1 for r in self.execution_history[-15:] if r.success) / 15
                if len(self.execution_history) >= 15 else 0
            )
        }


_learning_enhancer = None


def get_learning_enhancer() -> SelfLearningEnhancer:
    """获取自我学习增强器单例"""
    global _learning_enhancer
    if _learning_enhancer is None:
        _learning_enhancer = SelfLearningEnhancer()
    return _learning_enhancer
