"""
自我学习增强模块 V2 - 整合 ClaudeCode 核心学习机制

整合来源:
1. ClaudeCode (cc-haha-main):
   - Memory Types Taxonomy: user/feedback/project/reference 四类内存
   - Skillify Pattern: 4轮面试流程生成技能
   - Remember Pattern: 跨层内存审查和提升
   - MEMORY.md Index: 索引文件管理(200行/25KB限制)
   - Batch Skill: 并行工作编排
   - Loop Skill: 定时任务调度

2. OpenClaw:
   - 递归式技能进化
   - 自我改进循环
   - 实时权重更新

3. Hermes Agent:
   - 四阶段学习(Execution→Evaluation→Abstraction→Storage)
   - 闭环学习循环
   - Atropos强化学习

核心能力:
1. 结构化内存管理 - 四类内存分类存储
2. 智能技能捕获 - 4轮面试生成SKILL.md
3. 跨层内存提升 - 自动审查和提升
4. 并行任务编排 - 多工作单元并行执行
5. 定时学习任务 - 周期性复盘和优化
"""

import json
import os
import re
import time
import hashlib
import threading
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import logging
import shutil

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """内存类型分类 - ClaudeCode Taxonomy"""
    USER = "user"
    FEEDBACK = "feedback"
    PROJECT = "project"
    REFERENCE = "reference"


class LearningPhase(Enum):
    """学习阶段 - Hermes 四阶段"""
    EXECUTION = "execution"
    EVALUATION = "evaluation"
    ABSTRACTION = "abstraction"
    STORAGE = "storage"


class ImprovementType(Enum):
    """改进类型 - OpenClaw 自我改进"""
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


class SkillContext(Enum):
    """技能执行上下文"""
    INLINE = "inline"
    FORK = "fork"


@dataclass
class MemoryEntry:
    """内存条目 - ClaudeCode 格式"""
    id: str
    name: str
    description: str
    memory_type: MemoryType
    content: str
    why: str = ""
    how_to_apply: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    scope: str = "private"
    
    def to_frontmatter(self) -> str:
        """生成 frontmatter 格式"""
        return f"""---
name: {self.name}
description: {self.description}
type: {self.memory_type.value}
scope: {self.scope}
created: {self.created_at.isoformat()}
updated: {self.updated_at.isoformat()}
---

{self.content}

**Why:** {self.why}
**How to apply:** {self.how_to_apply}
"""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "memory_type": self.memory_type.value,
            "content": self.content[:500],
            "why": self.why,
            "how_to_apply": self.how_to_apply,
            "scope": self.scope,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


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
    memory_entries: List[str] = field(default_factory=list)
    
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
            "timestamp": self.timestamp.isoformat(),
            "memory_entries": self.memory_entries
        }


@dataclass
class SkillStep:
    """技能步骤 - ClaudeCode SKILL.md 格式"""
    name: str
    action: str
    success_criteria: str
    execution_type: str = "Direct"
    artifacts: List[str] = field(default_factory=list)
    human_checkpoint: bool = False
    rules: List[str] = field(default_factory=list)
    
    def to_markdown(self, index: int) -> str:
        lines = [f"### {index}. {self.name}", "", self.action, ""]
        lines.append(f"**Success criteria:** {self.success_criteria}")
        if self.execution_type != "Direct":
            lines.append(f"**Execution:** {self.execution_type}")
        if self.artifacts:
            lines.append(f"**Artifacts:** {', '.join(self.artifacts)}")
        if self.human_checkpoint:
            lines.append("**Human checkpoint:** Pause and ask user before proceeding")
        if self.rules:
            for rule in self.rules:
                lines.append(f"**Rule:** {rule}")
        return "\n".join(lines)


@dataclass
class SkillDocument:
    """技能文档 - ClaudeCode SKILL.md 格式"""
    id: str
    name: str
    description: str
    trigger_patterns: List[str]
    steps: List[SkillStep]
    allowed_tools: List[str]
    arguments: List[str]
    context: SkillContext
    success_rate: float
    usage_count: int
    version: str
    created_from: str
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_markdown(self) -> str:
        """生成 SKILL.md 格式"""
        frontmatter = f"""---
name: {self.name}
description: {self.description}
allowed-tools:
  - {chr(10).join(f'  - {t}' for t in self.allowed_tools)}
when_to_use: {self.trigger_patterns[0] if self.trigger_patterns else 'Manual invocation'}
arguments:
  - {chr(10).join(f'  - {a}' for a in self.arguments)}
context: {self.context.value}
---

"""
        content = f"# {self.name}\n\n{self.description}\n\n"
        
        if self.arguments:
            content += "## Inputs\n"
            for arg in self.arguments:
                content += f"- `${arg}`: 输入参数\n"
            content += "\n"
        
        content += "## Goal\n自动生成的技能目标\n\n"
        
        content += "## Steps\n\n"
        for i, step in enumerate(self.steps, 1):
            content += step.to_markdown(i) + "\n\n"
        
        content += f"""## Statistics
- Success rate: {self.success_rate:.2%}
- Usage count: {self.usage_count}
- Version: {self.version}

## Source
{self.created_from}

## Last Updated
{self.last_updated.isoformat()}
"""
        return frontmatter + content
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "trigger_patterns": self.trigger_patterns,
            "steps": [{"name": s.name, "action": s.action, "success_criteria": s.success_criteria} for s in self.steps],
            "allowed_tools": self.allowed_tools,
            "arguments": self.arguments,
            "context": self.context.value,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "version": self.version,
            "created_from": self.created_from
        }


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


@dataclass
class ScheduledTask:
    """定时任务 - ClaudeCode Loop Skill"""
    id: str
    prompt: str
    cron_expression: str
    interval_seconds: int
    recurring: bool
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True


class MemoryIndex:
    """内存索引管理 - ClaudeCode MEMORY.md 模式"""
    
    MAX_LINES = 200
    MAX_BYTES = 25000
    
    def __init__(self, index_path: Path):
        self.index_path = index_path
        self.entries: List[Tuple[str, str, str]] = []
        self._load()
    
    def _load(self):
        """加载索引"""
        if self.index_path.exists():
            try:
                content = self.index_path.read_text(encoding='utf-8')
                for line in content.split('\n'):
                    match = re.match(r'- \[(.+?)\]\((.+?)\) — (.+)', line)
                    if match:
                        self.entries.append((match.group(1), match.group(2), match.group(3)))
            except Exception as e:
                logger.warning(f"加载内存索引失败: {e}")
    
    def add_entry(self, title: str, file_path: str, hook: str) -> bool:
        """添加条目"""
        entry_line = f"- [{title}]({file_path}) — {hook}"
        if len(entry_line) > 200:
            hook = hook[:150] + "..."
            entry_line = f"- [{title}]({file_path}) — {hook}"
        
        self.entries.append((title, file_path, hook))
        return self._save()
    
    def remove_entry(self, file_path: str) -> bool:
        """移除条目"""
        self.entries = [(t, f, h) for t, f, h in self.entries if f != file_path]
        return self._save()
    
    def _save(self) -> bool:
        """保存索引"""
        lines = ["# Memory Index\n", ""]
        lines.extend(f"- [{t}]({f}) — {h}" for t, f, h in self.entries)
        
        content = '\n'.join(lines)
        
        if len(content.split('\n')) > self.MAX_LINES:
            content = '\n'.join(content.split('\n')[:self.MAX_LINES])
            content += f"\n\n> WARNING: MEMORY.md 超过 {self.MAX_LINES} 行限制，已截断"
        
        if len(content.encode('utf-8')) > self.MAX_BYTES:
            cut_at = content.rfind('\n', 0, self.MAX_BYTES)
            content = content[:cut_at] + f"\n\n> WARNING: MEMORY.md 超过 {self.MAX_BYTES // 1024}KB 限制，已截断"
        
        try:
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            self.index_path.write_text(content, encoding='utf-8')
            return True
        except Exception as e:
            logger.error(f"保存内存索引失败: {e}")
            return False
    
    def search(self, query: str) -> List[Tuple[str, str, str]]:
        """搜索条目"""
        query_lower = query.lower()
        return [(t, f, h) for t, f, h in self.entries 
                if query_lower in t.lower() or query_lower in h.lower()]


class SelfLearningEnhancerV2:
    """自我学习增强器 V2 - 整合 ClaudeCode + OpenClaw + Hermes"""
    
    def __init__(self, data_dir: str = "./data/learning"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.skills_dir = self.data_dir / "skills"
        self.skills_dir.mkdir(exist_ok=True)
        
        self.records_dir = self.data_dir / "records"
        self.records_dir.mkdir(exist_ok=True)
        
        self.memory_dir = self.data_dir / "memory"
        self.memory_dir.mkdir(exist_ok=True)
        
        self.memory_index = MemoryIndex(self.memory_dir / "MEMORY.md")
        
        self.execution_history: List[ExecutionRecord] = []
        self.skills: Dict[str, SkillDocument] = {}
        self.improvement_queue: List[ImprovementCandidate] = []
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.memories: Dict[str, MemoryEntry] = {}
        
        self.performance_metrics = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "skills_created": 0,
            "improvements_applied": 0,
            "memories_saved": 0
        }
        
        self._load_skills()
        self._load_memories()
        self._load_scheduled_tasks()
        
        self._scheduler_thread = None
        self._running = False
        
        logger.info("自我学习增强器 V2 初始化完成")
    
    def _load_skills(self):
        """加载已有技能"""
        for skill_file in self.skills_dir.glob("*.json"):
            try:
                with open(skill_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    steps = [SkillStep(
                        name=s.get('name', ''),
                        action=s.get('action', ''),
                        success_criteria=s.get('success_criteria', '')
                    ) for s in data.get('steps', [])]
                    
                    skill = SkillDocument(
                        id=data['id'],
                        name=data['name'],
                        description=data['description'],
                        trigger_patterns=data.get('trigger_patterns', []),
                        steps=steps,
                        allowed_tools=data.get('allowed_tools', []),
                        arguments=data.get('arguments', []),
                        context=SkillContext(data.get('context', 'inline')),
                        success_rate=data.get('success_rate', 0.0),
                        usage_count=data.get('usage_count', 0),
                        version=data.get('version', '1.0.0'),
                        created_from=data.get('created_from', 'unknown')
                    )
                    self.skills[skill.id] = skill
            except Exception as e:
                logger.warning(f"加载技能失败: {skill_file}: {e}")
    
    def _load_memories(self):
        """加载内存条目"""
        for mem_file in self.memory_dir.glob("*.md"):
            if mem_file.name == "MEMORY.md":
                continue
            try:
                content = mem_file.read_text(encoding='utf-8')
                frontmatter = self._parse_frontmatter(content)
                if frontmatter:
                    mem = MemoryEntry(
                        id=mem_file.stem,
                        name=frontmatter.get('name', mem_file.stem),
                        description=frontmatter.get('description', ''),
                        memory_type=MemoryType(frontmatter.get('type', 'user')),
                        content=self._extract_content(content),
                        scope=frontmatter.get('scope', 'private')
                    )
                    self.memories[mem.id] = mem
            except Exception as e:
                logger.warning(f"加载内存失败: {mem_file}: {e}")
    
    def _load_scheduled_tasks(self):
        """加载定时任务"""
        tasks_file = self.data_dir / "scheduled_tasks.json"
        if tasks_file.exists():
            try:
                with open(tasks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for task_data in data.get('tasks', []):
                        task = ScheduledTask(
                            id=task_data['id'],
                            prompt=task_data['prompt'],
                            cron_expression=task_data['cron_expression'],
                            interval_seconds=task_data['interval_seconds'],
                            recurring=task_data['recurring'],
                            enabled=task_data.get('enabled', True)
                        )
                        if task_data.get('last_run'):
                            task.last_run = datetime.fromisoformat(task_data['last_run'])
                        self.scheduled_tasks[task.id] = task
            except Exception as e:
                logger.warning(f"加载定时任务失败: {e}")
    
    def _parse_frontmatter(self, content: str) -> Optional[Dict]:
        """解析 frontmatter"""
        match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if match:
            fm_content = match.group(1)
            result = {}
            for line in fm_content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    result[key.strip()] = value.strip()
            return result
        return None
    
    def _extract_content(self, content: str) -> str:
        """提取正文内容"""
        match = re.search(r'^---\n.*?\n---\n(.*)', content, re.DOTALL)
        return match.group(1).strip() if match else content
    
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
    
    def save_memory(self, name: str, description: str, memory_type: MemoryType,
                    content: str, why: str = "", how_to_apply: str = "") -> MemoryEntry:
        """保存内存 - ClaudeCode Memory Types"""
        mem_id = self._generate_id("mem")
        mem = MemoryEntry(
            id=mem_id,
            name=name,
            description=description,
            memory_type=memory_type,
            content=content,
            why=why,
            how_to_apply=how_to_apply
        )
        
        self.memories[mem_id] = mem
        
        mem_file = self.memory_dir / f"{mem_id}.md"
        mem_file.write_text(mem.to_frontmatter(), encoding='utf-8')
        
        self.memory_index.add_entry(name, f"{mem_id}.md", description[:100])
        
        self.performance_metrics["memories_saved"] += 1
        logger.info(f"保存内存: {name} ({memory_type.value})")
        
        return mem
    
    def search_memories(self, query: str, memory_type: MemoryType = None) -> List[MemoryEntry]:
        """搜索内存"""
        results = []
        query_lower = query.lower()
        
        for mem in self.memories.values():
            if memory_type and mem.memory_type != memory_type:
                continue
            if query_lower in mem.name.lower() or query_lower in mem.content.lower():
                results.append(mem)
        
        return results
    
    def get_relevant_memories(self, task: str) -> List[MemoryEntry]:
        """获取与任务相关的内存"""
        relevant = []
        
        for mem in self.memories.values():
            if mem.memory_type == MemoryType.USER:
                relevant.append(mem)
            elif mem.memory_type == MemoryType.FEEDBACK:
                relevant.append(mem)
            elif mem.memory_type == MemoryType.PROJECT:
                if any(kw in task.lower() for kw in mem.content.lower().split()[:5]):
                    relevant.append(mem)
        
        return relevant[:10]
    
    def create_skill_from_session(self, session_records: List[ExecutionRecord],
                                   name: str = None, description: str = None) -> SkillDocument:
        """从会话创建技能 - ClaudeCode Skillify Pattern"""
        if not session_records:
            raise ValueError("无会话记录可转换为技能")
        
        skill_id = self._generate_id("skill")
        skill_name = name or f"auto_skill_{skill_id[:6]}"
        
        steps = []
        for i, record in enumerate(session_records):
            step = SkillStep(
                name=f"Step {i+1}",
                action=record.task,
                success_criteria="任务成功完成" if record.success else "需要验证",
                execution_type="Direct",
                human_checkpoint=False,
                rules=[]
            )
            steps.append(step)
        
        trigger_patterns = [session_records[0].task[:100]] if session_records else []
        
        skill = SkillDocument(
            id=skill_id,
            name=skill_name,
            description=description or f"自动生成技能: {trigger_patterns[0] if trigger_patterns else 'Unknown'}",
            trigger_patterns=trigger_patterns,
            steps=steps,
            allowed_tools=list(set(tool for r in session_records for tool in r.tools_used)),
            arguments=[],
            context=SkillContext.INLINE,
            success_rate=sum(1 for r in session_records if r.success) / len(session_records),
            usage_count=1,
            version="1.0.0",
            created_from="session_conversion"
        )
        
        self.skills[skill_id] = skill
        self._save_skill(skill)
        self.performance_metrics["skills_created"] += 1
        
        logger.info(f"从会话创建技能: {skill_name}")
        return skill
    
    def review_memories(self) -> Dict[str, List[Dict]]:
        """审查内存 - ClaudeCode Remember Pattern"""
        result = {
            "promotions": [],
            "cleanup": [],
            "ambiguous": [],
            "no_action": []
        }
        
        for mem in self.memories.values():
            if mem.memory_type == MemoryType.USER:
                if mem.scope == "private":
                    result["no_action"].append({
                        "id": mem.id,
                        "name": mem.name,
                        "reason": "用户内存保持私有"
                    })
            
            elif mem.memory_type == MemoryType.FEEDBACK:
                if mem.scope == "team":
                    result["promotions"].append({
                        "id": mem.id,
                        "name": mem.name,
                        "destination": "CLAUDE.md",
                        "reason": "团队范围的反馈应提升到项目配置"
                    })
            
            elif mem.memory_type == MemoryType.PROJECT:
                if mem.updated_at < datetime.now(timezone.utc) - timedelta(days=30):
                    result["cleanup"].append({
                        "id": mem.id,
                        "name": mem.name,
                        "reason": "项目内存超过30天未更新，可能已过时"
                    })
            
            elif mem.memory_type == MemoryType.REFERENCE:
                result["no_action"].append({
                    "id": mem.id,
                    "name": mem.name,
                    "reason": "引用内存保持原位"
                })
        
        return result
    
    def schedule_task(self, prompt: str, interval_seconds: int, recurring: bool = True) -> ScheduledTask:
        """创建定时任务 - ClaudeCode Loop Skill"""
        task_id = self._generate_id("task")
        
        cron_expr = self._interval_to_cron(interval_seconds)
        
        task = ScheduledTask(
            id=task_id,
            prompt=prompt,
            cron_expression=cron_expr,
            interval_seconds=interval_seconds,
            recurring=recurring,
            next_run=datetime.now(timezone.utc) + timedelta(seconds=interval_seconds)
        )
        
        self.scheduled_tasks[task_id] = task
        self._save_scheduled_tasks()
        
        logger.info(f"创建定时任务: {task_id} (间隔: {interval_seconds}秒)")
        return task
    
    def _interval_to_cron(self, seconds: int) -> str:
        """将间隔秒数转换为 cron 表达式"""
        if seconds < 60:
            return "* * * * *"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"*/{minutes} * * * *"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"0 */{hours} * * *"
        else:
            days = seconds // 86400
            return f"0 0 */{days} * *"
    
    def start_scheduler(self):
        """启动定时任务调度器"""
        if self._running:
            return
        
        self._running = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        logger.info("定时任务调度器已启动")
    
    def stop_scheduler(self):
        """停止定时任务调度器"""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        logger.info("定时任务调度器已停止")
    
    def _scheduler_loop(self):
        """调度器主循环"""
        while self._running:
            now = datetime.now(timezone.utc)
            
            for task in self.scheduled_tasks.values():
                if task.enabled and task.next_run and task.next_run <= now:
                    self._execute_scheduled_task(task)
                    
                    if task.recurring:
                        task.next_run = now + timedelta(seconds=task.interval_seconds)
                    else:
                        task.enabled = False
            
            self._save_scheduled_tasks()
            time.sleep(60)
    
    def _execute_scheduled_task(self, task: ScheduledTask):
        """执行定时任务"""
        logger.info(f"执行定时任务: {task.id}")
        task.last_run = datetime.now(timezone.utc)
        
        self.record_execution(
            task=f"[Scheduled] {task.prompt}",
            actions=[{"type": "scheduled", "prompt": task.prompt}],
            result="定时任务执行完成",
            success=True,
            tools=["scheduler"]
        )
    
    def add_feedback(self, record_id: str, feedback: FeedbackType):
        """添加反馈 - Hermes 闭环学习"""
        for record in self.execution_history:
            if record.id == record_id:
                record.feedback = feedback
                
                if feedback in [FeedbackType.EXPLICIT_POSITIVE, FeedbackType.IMPLICIT_ACCEPT]:
                    self._save_memory_from_feedback(record)
                break
    
    def _save_memory_from_feedback(self, record: ExecutionRecord):
        """从反馈保存内存"""
        if record.success:
            self.save_memory(
                name=f"成功模式: {record.task[:30]}",
                description=f"成功执行的任务模式",
                memory_type=MemoryType.FEEDBACK,
                content=f"任务: {record.task}\n结果: {record.result[:200]}",
                why="用户确认此方法有效",
                how_to_apply="类似任务可参考此执行方式"
            )
    
    def _trigger_review(self):
        """触发自动复盘 - Hermes 机制"""
        logger.info("触发自动复盘...")
        
        recent_records = self.execution_history[-15:]
        
        success_rate = sum(1 for r in recent_records if r.success) / len(recent_records) if recent_records else 0
        
        error_patterns = self._analyze_errors(recent_records)
        
        success_patterns = self._analyze_successes(recent_records)
        
        for pattern in success_patterns:
            if pattern['frequency'] >= 3:
                self._create_skill_candidate(pattern)
        
        for error in error_patterns:
            self._create_improvement_candidate(error)
        
        memory_review = self.review_memories()
        if memory_review["cleanup"]:
            logger.info(f"内存审查发现 {len(memory_review['cleanup'])} 个需要清理的条目")
    
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
        
        steps = [SkillStep(
            name=f"执行: {pattern['task_pattern'][:30]}",
            action=str(pattern['actions']),
            success_criteria="任务成功完成"
        )]
        
        skill = SkillDocument(
            id=skill_id,
            name=f"auto_skill_{skill_id[:6]}",
            description=f"自动生成技能: {pattern['task_pattern'][:50]}",
            trigger_patterns=[pattern['task_pattern']],
            steps=steps,
            allowed_tools=pattern['tools'],
            arguments=[],
            context=SkillContext.INLINE,
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
        best_match = None
        best_score = 0
        
        for skill in self.skills.values():
            for pattern in skill.trigger_patterns:
                if pattern.lower() in task.lower():
                    score = len(pattern) / 100 + skill.success_rate
                    if score > best_score:
                        best_score = score
                        best_match = skill
        
        if best_match:
            best_match.usage_count += 1
            self._save_skill(best_match)
        
        return best_match
    
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
            json.dump(skill.to_dict(), f, ensure_ascii=False, indent=2)
        
        md_file = self.skills_dir / f"{skill.name}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(skill.to_markdown())
    
    def _save_record(self, record: ExecutionRecord):
        """保存执行记录"""
        record_file = self.records_dir / f"{record.id}.json"
        with open(record_file, 'w', encoding='utf-8') as f:
            json.dump(record.to_dict(), f, ensure_ascii=False, indent=2)
    
    def _save_scheduled_tasks(self):
        """保存定时任务"""
        tasks_file = self.data_dir / "scheduled_tasks.json"
        data = {
            "tasks": [
                {
                    "id": t.id,
                    "prompt": t.prompt,
                    "cron_expression": t.cron_expression,
                    "interval_seconds": t.interval_seconds,
                    "recurring": t.recurring,
                    "enabled": t.enabled,
                    "last_run": t.last_run.isoformat() if t.last_run else None
                }
                for t in self.scheduled_tasks.values()
            ]
        }
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _generate_id(self, prefix: str) -> str:
        """生成ID"""
        content = f"{prefix}:{time.time()}:{len(self.execution_history)}"
        return f"{prefix}_{hashlib.md5(content.encode()).hexdigest()[:12]}"
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "performance": self.performance_metrics,
            "skills_count": len(self.skills),
            "memories_count": len(self.memories),
            "memory_types": {
                mt.value: sum(1 for m in self.memories.values() if m.memory_type == mt)
                for mt in MemoryType
            },
            "improvement_queue_size": len(self.improvement_queue),
            "scheduled_tasks_count": len(self.scheduled_tasks),
            "recent_success_rate": (
                sum(1 for r in self.execution_history[-15:] if r.success) / 15
                if len(self.execution_history) >= 15 else 0
            ),
            "memory_index_entries": len(self.memory_index.entries)
        }
    
    def export_learning_state(self) -> Dict[str, Any]:
        """导出学习状态"""
        return {
            "version": "2.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "performance_metrics": self.performance_metrics,
            "skills": {k: v.to_dict() for k, v in self.skills.items()},
            "memories": {k: v.to_dict() for k, v in self.memories.items()},
            "improvement_queue": [
                {"id": i.id, "type": i.type.value, "description": i.description}
                for i in self.improvement_queue
            ]
        }


_learning_enhancer_v2 = None


def get_learning_enhancer() -> SelfLearningEnhancerV2:
    """获取自我学习增强器单例"""
    global _learning_enhancer_v2
    if _learning_enhancer_v2 is None:
        _learning_enhancer_v2 = SelfLearningEnhancerV2()
    return _learning_enhancer_v2
