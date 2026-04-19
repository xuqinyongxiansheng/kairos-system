"""
import logging
技能进化管道 - 自动技能生成与改进系统
logger = logging.getLogger("skill_evolution_pipeline")

设计理念来源:
- Hermes Agent: 闭环学习机制
- ClaudeCode: 技能复用模式
- KEPA系统: 自我进化能力

核心特性:
1. 经验提取: 从执行轨迹中提取可复用经验
2. 技能生成: 自动生成技能候选
3. 技能验证: 验证技能有效性
4. 版本控制: 技能版本管理
5. 进化追踪: 记录技能进化历史
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar

T = TypeVar('T')


class SkillEvolutionStage(Enum):
    """技能进化阶段"""
    EXTRACTION = "extraction"
    GENERATION = "generation"
    VALIDATION = "validation"
    INTEGRATION = "integration"
    OPTIMIZATION = "optimization"


class SkillStatus(Enum):
    """技能状态"""
    DRAFT = "draft"
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ExperienceType(Enum):
    """经验类型"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    LEARNING = "learning"


@dataclass
class ExecutionStep:
    """执行步骤"""
    step_id: str
    action: str
    context: Dict[str, Any]
    result: Any
    success: bool
    duration: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionTrace:
    """执行轨迹"""
    id: str
    task: str
    steps: List[ExecutionStep] = field(default_factory=list)
    total_duration: float = 0.0
    success: bool = True
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task": self.task,
            "steps": [
                {
                    "step_id": s.step_id,
                    "action": s.action,
                    "context": s.context,
                    "result": str(s.result)[:500],
                    "success": s.success,
                    "duration": s.duration,
                    "error": s.error
                }
                for s in self.steps
            ],
            "total_duration": self.total_duration,
            "success": self.success,
            "context": self.context,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class Experience:
    """经验数据结构"""
    id: str
    type: ExperienceType
    context: str
    action: str
    result: str
    success: bool
    feedback: str = ""
    reusable: bool = False
    complexity: float = 0.0
    confidence: float = 0.0
    patterns: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "context": self.context,
            "action": self.action,
            "result": self.result,
            "success": self.success,
            "feedback": self.feedback,
            "reusable": self.reusable,
            "complexity": self.complexity,
            "confidence": self.confidence,
            "patterns": self.patterns,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class SkillCandidate:
    """技能候选"""
    id: str
    name: str
    description: str
    code: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    version: str = "1.0.0"
    parent_id: Optional[str] = None
    status: SkillStatus = SkillStatus.DRAFT
    confidence: float = 0.0
    usage_count: int = 0
    success_rate: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "code": self.code,
            "parameters": self.parameters,
            "dependencies": self.dependencies,
            "examples": self.examples,
            "version": self.version,
            "parent_id": self.parent_id,
            "status": self.status.value,
            "confidence": self.confidence,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkillCandidate':
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            code=data.get("code", ""),
            parameters=data.get("parameters", {}),
            dependencies=data.get("dependencies", []),
            examples=data.get("examples", []),
            version=data.get("version", "1.0.0"),
            parent_id=data.get("parent_id"),
            status=SkillStatus(data.get("status", "draft")),
            confidence=data.get("confidence", 0.0),
            usage_count=data.get("usage_count", 0),
            success_rate=data.get("success_rate", 0.0),
            created_at=datetime.fromisoformat(data["created_at"]) 
                     if data.get("created_at") else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(data["updated_at"]) 
                     if data.get("updated_at") else datetime.now(timezone.utc),
            metadata=data.get("metadata", {})
        )


@dataclass
class EvolutionRecord:
    """进化记录"""
    id: str
    skill_id: str
    stage: SkillEvolutionStage
    changes: Dict[str, Any]
    parent_id: Optional[str] = None
    fitness_before: float = 0.0
    fitness_after: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ExperienceExtractor:
    """
    经验提取器 - 从执行轨迹中提取可复用经验
    
    核心功能:
    1. 轨迹分析: 识别成功和失败模式
    2. 模式识别: 发现重复行为模式
    3. 复杂度评估: 评估经验复杂度
    4. 可复用性判断: 判断经验是否可复用
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._experience_cache: Dict[str, Experience] = {}
        self._pattern_library: Dict[str, int] = {}
    
    def extract(self, trace: ExecutionTrace) -> List[Experience]:
        """从执行轨迹提取经验"""
        experiences = []
        
        for step in trace.steps:
            if self._is_reusable(step, trace):
                experience = self._create_experience(step, trace)
                experiences.append(experience)
                self._experience_cache[experience.id] = experience
        
        grouped = self._group_similar_experiences(experiences)
        consolidated = self._consolidate_groups(grouped)
        
        return consolidated
    
    def extract_batch(
        self, 
        traces: List[ExecutionTrace]
    ) -> List[Experience]:
        """批量提取经验"""
        all_experiences = []
        for trace in traces:
            experiences = self.extract(trace)
            all_experiences.extend(experiences)
        return all_experiences
    
    def _is_reusable(
        self, 
        step: ExecutionStep, 
        trace: ExecutionTrace
    ) -> bool:
        """判断步骤是否可复用"""
        if not step.success:
            return False
        
        if step.duration < 0.1:
            return False
        
        complexity = self._calculate_complexity(step)
        if complexity < 0.3:
            return False
        
        return True
    
    def _create_experience(
        self, 
        step: ExecutionStep, 
        trace: ExecutionTrace
    ) -> Experience:
        """创建经验"""
        exp_id = self._generate_id()
        
        patterns = self._identify_patterns(step)
        for pattern in patterns:
            self._pattern_library[pattern] = \
                self._pattern_library.get(pattern, 0) + 1
        
        return Experience(
            id=exp_id,
            type=ExperienceType.SUCCESS if step.success else ExperienceType.FAILURE,
            context=self._extract_context(step, trace),
            action=step.action,
            result=str(step.result)[:500] if step.result else "",
            success=step.success,
            reusable=True,
            complexity=self._calculate_complexity(step),
            confidence=self._calculate_confidence(step, trace),
            patterns=patterns
        )
    
    def _calculate_complexity(self, step: ExecutionStep) -> float:
        """计算复杂度"""
        complexity = 0.0
        
        if step.context:
            complexity += min(0.3, len(str(step.context)) / 1000)
        
        if step.metadata:
            complexity += min(0.2, len(step.metadata) / 10)
        
        if step.duration > 1.0:
            complexity += min(0.3, step.duration / 10)
        
        return min(1.0, complexity)
    
    def _calculate_confidence(
        self, 
        step: ExecutionStep, 
        trace: ExecutionTrace
    ) -> float:
        """计算置信度"""
        base_confidence = 0.5
        
        if step.success:
            base_confidence += 0.2
        
        similar_steps = sum(
            1 for s in trace.steps 
            if s.action == step.action and s.success
        )
        base_confidence += min(0.2, similar_steps * 0.05)
        
        return min(1.0, base_confidence)
    
    def _identify_patterns(self, step: ExecutionStep) -> List[str]:
        """识别模式"""
        patterns = []
        
        action_lower = step.action.lower()
        
        if "read" in action_lower or "load" in action_lower:
            patterns.append("data_input")
        if "write" in action_lower or "save" in action_lower:
            patterns.append("data_output")
        if "process" in action_lower or "transform" in action_lower:
            patterns.append("data_processing")
        if "validate" in action_lower or "check" in action_lower:
            patterns.append("validation")
        if "search" in action_lower or "find" in action_lower:
            patterns.append("search")
        
        return patterns
    
    def _extract_context(
        self, 
        step: ExecutionStep, 
        trace: ExecutionTrace
    ) -> str:
        """提取上下文"""
        context_parts = []
        
        if trace.task:
            context_parts.append(f"任务: {trace.task[:100]}")
        
        if step.context:
            context_parts.append(f"步骤上下文: {str(step.context)[:200]}")
        
        return " | ".join(context_parts)
    
    def _group_similar_experiences(
        self, 
        experiences: List[Experience]
    ) -> Dict[str, List[Experience]]:
        """分组相似经验"""
        groups: Dict[str, List[Experience]] = {}
        
        for exp in experiences:
            key = self._get_similarity_key(exp)
            if key not in groups:
                groups[key] = []
            groups[key].append(exp)
        
        return groups
    
    def _get_similarity_key(self, exp: Experience) -> str:
        """获取相似性键"""
        action_words = exp.action.lower().split()[:3]
        return "_".join(action_words)
    
    def _consolidate_groups(
        self, 
        groups: Dict[str, List[Experience]]
    ) -> List[Experience]:
        """合并分组"""
        consolidated = []
        
        for key, group in groups.items():
            if len(group) >= 2:
                best = max(group, key=lambda e: e.confidence)
                best.metadata["group_size"] = len(group)
                consolidated.append(best)
            else:
                consolidated.extend(group)
        
        return consolidated
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        content = f"exp:{time.time()}:{threading.get_ident()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def get_pattern_statistics(self) -> Dict[str, int]:
        """获取模式统计"""
        return dict(self._pattern_library)


class SkillGenerator:
    """
    技能生成器 - 从经验生成技能候选
    
    核心功能:
    1. 模式综合: 从多个经验综合技能
    2. 代码生成: 生成可执行代码
    3. 参数提取: 提取技能参数
    4. 文档生成: 生成技能文档
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._skill_templates: Dict[str, str] = self._load_templates()
    
    def generate(
        self, 
        experiences: List[Experience]
    ) -> List[SkillCandidate]:
        """从经验生成技能候选"""
        candidates = []
        
        grouped = self._group_by_pattern(experiences)
        
        for pattern, exps in grouped.items():
            if len(exps) >= 2:
                candidate = self._synthesize_skill(pattern, exps)
                if candidate:
                    candidates.append(candidate)
        
        return candidates
    
    def improve(
        self, 
        existing_skill: SkillCandidate, 
        feedback: str,
        experiences: List[Experience]
    ) -> Optional[SkillCandidate]:
        """改进现有技能"""
        relevant_exps = [
            e for e in experiences 
            if self._is_relevant(e, existing_skill)
        ]
        
        if not relevant_exps:
            return None
        
        improved_code = self._improve_code(
            existing_skill.code, 
            feedback, 
            relevant_exps
        )
        
        new_version = self._increment_version(existing_skill.version)
        
        return SkillCandidate(
            id=self._generate_id(),
            name=existing_skill.name,
            description=self._improve_description(
                existing_skill.description, 
                feedback
            ),
            code=improved_code,
            parameters=existing_skill.parameters.copy(),
            dependencies=existing_skill.dependencies.copy(),
            examples=self._update_examples(
                existing_skill.examples, 
                relevant_exps
            ),
            version=new_version,
            parent_id=existing_skill.id,
            status=SkillStatus.CANDIDATE,
            confidence=existing_skill.confidence * 0.9 + 0.1,
            metadata={
                "improvement_type": "feedback_based",
                "feedback": feedback[:200]
            }
        )
    
    def _load_templates(self) -> Dict[str, str]:
        """加载技能模板"""
        return {
            "data_input": '''
def {name}(file_path: str, **kwargs) -> dict:
    """{description}"""
    import json
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
''',
            "data_output": '''
def {name}(data: dict, file_path: str, **kwargs) -> bool:
    """{description}"""
    import json
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True
''',
            "data_processing": '''
def {name}(data: dict, **kwargs) -> dict:
    """{description}"""
    result = {}
    for key, value in data.items():
        result[key] = value
    return result
''',
            "validation": '''
def {name}(data: dict, **kwargs) -> bool:
    """{description}"""
    required_keys = kwargs.get('required_keys', [])
    return all(k in data for k in required_keys)
''',
            "search": '''
def {name}(query: str, data: list, **kwargs) -> list:
    """{description}"""
    results = []
    for item in data:
        if query.lower() in str(item).lower():
            results.append(item)
    return results
''',
            "default": '''
def {name}(**kwargs) -> dict:
    """{description}"""
    return {{"status": "success", "data": kwargs}}
'''
        }
    
    def _group_by_pattern(
        self, 
        experiences: List[Experience]
    ) -> Dict[str, List[Experience]]:
        """按模式分组"""
        groups: Dict[str, List[Experience]] = {}
        
        for exp in experiences:
            for pattern in exp.patterns:
                if pattern not in groups:
                    groups[pattern] = []
                groups[pattern].append(exp)
        
        return groups
    
    def _synthesize_skill(
        self, 
        pattern: str, 
        experiences: List[Experience]
    ) -> Optional[SkillCandidate]:
        """综合生成技能"""
        if not experiences:
            return None
        
        name = self._generate_name(pattern, experiences)
        description = self._generate_description(experiences)
        code = self._generate_code(pattern, name, description)
        parameters = self._extract_parameters(experiences)
        examples = self._create_examples(experiences)
        
        return SkillCandidate(
            id=self._generate_id(),
            name=name,
            description=description,
            code=code,
            parameters=parameters,
            examples=examples,
            status=SkillStatus.CANDIDATE,
            confidence=sum(e.confidence for e in experiences) / len(experiences),
            metadata={
                "pattern": pattern,
                "experience_count": len(experiences),
                "source_experiences": [e.id for e in experiences[:5]]
            }
        )
    
    def _generate_name(
        self, 
        pattern: str, 
        experiences: List[Experience]
    ) -> str:
        """生成技能名称"""
        pattern_names = {
            "data_input": "load_data",
            "data_output": "save_data",
            "data_processing": "process_data",
            "validation": "validate_data",
            "search": "search_data"
        }
        
        base_name = pattern_names.get(pattern, "execute_task")
        
        if experiences:
            action_words = experiences[0].action.split()[:2]
            suffix = "_".join(w.lower() for w in action_words if w.isalpha())
            if suffix:
                return f"{base_name}_{suffix}"
        
        return base_name
    
    def _generate_description(
        self, 
        experiences: List[Experience]
    ) -> str:
        """生成技能描述"""
        if not experiences:
            return "自动生成的技能"
        
        contexts = [e.context[:50] for e in experiences[:3]]
        return f"基于{len(experiences)}次成功经验生成。场景: {'; '.join(contexts)}"
    
    def _generate_code(
        self, 
        pattern: str, 
        name: str, 
        description: str
    ) -> str:
        """生成代码"""
        template = self._skill_templates.get(
            pattern, 
            self._skill_templates["default"]
        )
        
        return template.format(
            name=name,
            description=description
        ).strip()
    
    def _extract_parameters(
        self, 
        experiences: List[Experience]
    ) -> Dict[str, Any]:
        """提取参数"""
        params = {}
        
        for exp in experiences:
            if exp.metadata.get("parameters"):
                for key, value in exp.metadata["parameters"].items():
                    if key not in params:
                        params[key] = value
        
        return params
    
    def _create_examples(
        self, 
        experiences: List[Experience]
    ) -> List[Dict[str, Any]]:
        """创建示例"""
        examples = []
        
        for exp in experiences[:3]:
            examples.append({
                "context": exp.context[:100],
                "action": exp.action,
                "result": exp.result[:100] if exp.result else ""
            })
        
        return examples
    
    def _is_relevant(
        self, 
        experience: Experience, 
        skill: SkillCandidate
    ) -> bool:
        """判断经验是否与技能相关"""
        skill_patterns = skill.metadata.get("pattern", "")
        return skill_patterns in experience.patterns
    
    def _improve_code(
        self, 
        existing_code: str, 
        feedback: str, 
        experiences: List[Experience]
    ) -> str:
        """改进代码"""
        improvements = []
        
        if "error" in feedback.lower():
            improvements.append("# 添加错误处理")
        
        if "slow" in feedback.lower():
            improvements.append("# 优化性能")
        
        if improvements:
            return existing_code + "\n\n" + "\n".join(improvements)
        
        return existing_code
    
    def _improve_description(
        self, 
        existing_desc: str, 
        feedback: str
    ) -> str:
        """改进描述"""
        return f"{existing_desc}\n改进说明: {feedback[:100]}"
    
    def _update_examples(
        self, 
        existing_examples: List[Dict[str, Any]], 
        experiences: List[Experience]
    ) -> List[Dict[str, Any]]:
        """更新示例"""
        new_examples = existing_examples.copy()
        
        for exp in experiences[:2]:
            new_examples.append({
                "context": exp.context[:100],
                "action": exp.action,
                "result": exp.result[:100] if exp.result else ""
            })
        
        return new_examples[-5:]
    
    def _increment_version(self, version: str) -> str:
        """增加版本号"""
        parts = version.split('.')
        if len(parts) >= 2:
            parts[-1] = str(int(parts[-1]) + 1)
            return '.'.join(parts)
        return f"{version}.1"
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        content = f"skill:{time.time()}:{threading.get_ident()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


class SkillValidator:
    """
    技能验证器 - 验证技能有效性
    
    核心功能:
    1. 语法验证: 检查代码语法
    2. 语义验证: 检查逻辑正确性
    3. 安全验证: 检查安全风险
    4. 功能测试: 运行测试用例
    """
    
    def __init__(
        self, 
        test_cases: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.test_cases = test_cases or []
        self.config = config or {}
        self._validation_history: List[Dict[str, Any]] = []
    
    def validate(
        self, 
        skill: SkillCandidate, 
        strict: bool = False
    ) -> Tuple[bool, List[str]]:
        """
        验证技能
        
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        if not self._validate_syntax(skill.code):
            errors.append("语法错误")
            if strict:
                return False, errors
        
        if not self._validate_structure(skill):
            errors.append("结构不完整")
        
        if not self._validate_security(skill):
            errors.append("存在安全风险")
        
        test_results = self._run_tests(skill)
        if not all(test_results):
            errors.append(f"测试未通过: {sum(test_results)}/{len(test_results)}")
        
        is_valid = len(errors) == 0 if strict else len(errors) < 2
        
        self._validation_history.append({
            "skill_id": skill.id,
            "is_valid": is_valid,
            "errors": errors,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return is_valid, errors
    
    def add_test_case(self, test_case: Dict[str, Any]):
        """添加测试用例"""
        self.test_cases.append(test_case)
    
    def _validate_syntax(self, code: str) -> bool:
        """验证语法"""
        if not code:
            return False
        
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError:
            return False
    
    def _validate_structure(self, skill: SkillCandidate) -> bool:
        """验证结构"""
        if not skill.name:
            return False
        
        if not skill.description:
            return False
        
        if not skill.code:
            return False
        
        return True
    
    def _validate_security(self, skill: SkillCandidate) -> bool:
        """验证安全"""
        dangerous_patterns = [
            r'eval\s*\(',
            r'exec\s*\(',
            r'__import__\s*\(',
            r'os\.system',
            r'subprocess\.call',
            r'open\s*\([^)]*[\'"]w[\'"]'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, skill.code):
                return False
        
        return True
    
    def _run_tests(self, skill: SkillCandidate) -> List[bool]:
        """运行测试"""
        results = []
        
        for case in self.test_cases:
            try:
                result = self._execute_skill_test(skill, case)
                expected = case.get('expected')
                results.append(result == expected)
            except Exception:
                results.append(False)
        
        if not self.test_cases:
            results.append(True)
        
        return results
    
    def _execute_skill_test(
        self, 
        skill: SkillCandidate, 
        case: Dict[str, Any]
    ) -> Any:
        """执行技能测试"""
        local_vars = {}
        
        try:
            exec(skill.code, {"__builtins__": {}}, local_vars)
        except Exception:
            return None
        
        func_name = skill.name
        if func_name in local_vars:
            func = local_vars[func_name]
            return func(**case.get('input', {}))
        
        return None
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """获取验证统计"""
        if not self._validation_history:
            return {}
        
        total = len(self._validation_history)
        valid = sum(1 for v in self._validation_history if v["is_valid"])
        
        return {
            "total_validations": total,
            "valid_count": valid,
            "invalid_count": total - valid,
            "valid_rate": valid / total if total > 0 else 0
        }


class SkillVersionControl:
    """
    技能版本控制器 - 管理技能版本
    
    核心功能:
    1. 版本管理: 跟踪技能版本历史
    2. 回滚支持: 支持版本回滚
    3. 差异比较: 比较版本差异
    4. 分支管理: 支持技能分支
    """
    
    def __init__(self, storage_dir: str = ""):
        self.storage_dir = Path(storage_dir) if storage_dir else None
        self._versions: Dict[str, List[SkillCandidate]] = {}
        self._branches: Dict[str, str] = {"main": "main"}
        self._lock = threading.Lock()
    
    def store(self, skill: SkillCandidate) -> str:
        """存储技能版本"""
        with self._lock:
            if skill.name not in self._versions:
                self._versions[skill.name] = []
            
            self._versions[skill.name].append(skill)
            
            if self.storage_dir:
                self._save_skill_version(skill)
            
            return skill.id
    
    def get_version(
        self, 
        name: str, 
        version: Optional[str] = None
    ) -> Optional[SkillCandidate]:
        """获取指定版本"""
        with self._lock:
            if name not in self._versions:
                return None
            
            versions = self._versions[name]
            
            if version:
                for v in versions:
                    if v.version == version:
                        return v
                return None
            
            return versions[-1] if versions else None
    
    def get_history(self, name: str) -> List[Dict[str, Any]]:
        """获取版本历史"""
        with self._lock:
            if name not in self._versions:
                return []
            
            return [
                {
                    "id": v.id,
                    "version": v.version,
                    "status": v.status.value,
                    "confidence": v.confidence,
                    "created_at": v.created_at.isoformat()
                }
                for v in self._versions[name]
            ]
    
    def rollback(
        self, 
        name: str, 
        target_version: str
    ) -> Optional[SkillCandidate]:
        """回滚到指定版本"""
        with self._lock:
            target = self.get_version(name, target_version)
            if not target:
                return None
            
            rollback_skill = SkillCandidate(
                id=self._generate_id(),
                name=target.name,
                description=target.description,
                code=target.code,
                parameters=target.parameters.copy(),
                dependencies=target.dependencies.copy(),
                examples=target.examples.copy(),
                version=self._increment_version(target.version),
                parent_id=target.id,
                status=SkillStatus.ACTIVE,
                metadata={"rollback_from": target.version}
            )
            
            self._versions[name].append(rollback_skill)
            return rollback_skill
    
    def compare(
        self, 
        name: str, 
        version1: str, 
        version2: str
    ) -> Dict[str, Any]:
        """比较两个版本"""
        v1 = self.get_version(name, version1)
        v2 = self.get_version(name, version2)
        
        if not v1 or not v2:
            return {"error": "版本不存在"}
        
        return {
            "version1": version1,
            "version2": version2,
            "code_diff": self._compute_diff(v1.code, v2.code),
            "confidence_diff": v2.confidence - v1.confidence,
            "time_diff": (
                v2.created_at - v1.created_at
            ).total_seconds()
        }
    
    def _save_skill_version(self, skill: SkillCandidate):
        """保存技能版本到文件"""
        if not self.storage_dir:
            return
        
        skill_dir = self.storage_dir / skill.name
        skill_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = skill_dir / f"v{skill.version}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(skill.to_dict(), f, indent=2, ensure_ascii=False)
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        content = f"skill_version:{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _increment_version(self, version: str) -> str:
        """增加版本号"""
        parts = version.split('.')
        if len(parts) >= 2:
            parts[-1] = str(int(parts[-1]) + 1)
            return '.'.join(parts)
        return f"{version}.1"
    
    def _compute_diff(self, code1: str, code2: str) -> Dict[str, Any]:
        """计算代码差异"""
        lines1 = code1.split('\n')
        lines2 = code2.split('\n')
        
        return {
            "added_lines": len(lines2) - len(lines1),
            "total_changes": abs(len(lines2) - len(lines1))
        }


class SkillEvolutionPipeline:
    """
    技能进化管道主类
    
    整合经验提取、技能生成、验证和版本控制
    
    使用方式:
        pipeline = SkillEvolutionPipeline(skill_system)
        
        # 从执行轨迹进化技能
        new_skill = pipeline.evolve(execution_trace)
        
        # 改进现有技能
        improved = pipeline.improve(skill_id, feedback, trace)
    """
    
    def __init__(
        self,
        skill_system: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.skill_system = skill_system
        self.config = config or {}
        
        self.extractor = ExperienceExtractor(config)
        self.generator = SkillGenerator(config)
        self.validator = SkillValidator(config.get("test_cases", []), config)
        self.version_control = SkillVersionControl(
            config.get("storage_dir", "")
        )
        
        self._evolution_history: List[EvolutionRecord] = []
        self._lock = threading.Lock()
    
    def evolve(
        self, 
        trace: ExecutionTrace,
        auto_apply: bool = False
    ) -> Optional[SkillCandidate]:
        """
        从执行轨迹进化技能
        
        Args:
            trace: 执行轨迹
            auto_apply: 是否自动应用
            
        Returns:
            新技能候选
        """
        experiences = self.extractor.extract(trace)
        
        if not experiences:
            return None
        
        candidates = self.generator.generate(experiences)
        
        for candidate in candidates:
            is_valid, errors = self.validator.validate(candidate)
            
            if is_valid:
                self._record_evolution(
                    candidate.id,
                    SkillEvolutionStage.VALIDATION,
                    {"errors": errors}
                )
                
                stored_id = self.version_control.store(candidate)
                
                if auto_apply and self.skill_system:
                    self._apply_skill(candidate)
                
                return candidate
        
        return None
    
    def improve(
        self, 
        skill_id: str, 
        feedback: str,
        trace: Optional[ExecutionTrace] = None
    ) -> Optional[SkillCandidate]:
        """
        改进现有技能
        
        Args:
            skill_id: 技能ID
            feedback: 改进反馈
            trace: 执行轨迹
            
        Returns:
            改进后的技能
        """
        current_skill = self._get_skill(skill_id)
        if not current_skill:
            return None
        
        experiences = []
        if trace:
            experiences = self.extractor.extract(trace)
        
        improved = self.generator.improve(
            current_skill, 
            feedback, 
            experiences
        )
        
        if not improved:
            return None
        
        is_valid, errors = self.validator.validate(improved)
        
        if is_valid:
            self._record_evolution(
                improved.id,
                SkillEvolutionStage.OPTIMIZATION,
                {
                    "parent_id": skill_id,
                    "feedback": feedback[:200],
                    "errors": errors
                }
            )
            
            self.version_control.store(improved)
            return improved
        
        return None
    
    def batch_evolve(
        self, 
        traces: List[ExecutionTrace]
    ) -> List[SkillCandidate]:
        """批量进化技能"""
        results = []
        
        for trace in traces:
            skill = self.evolve(trace)
            if skill:
                results.append(skill)
        
        return results
    
    def get_evolution_history(
        self, 
        skill_id: Optional[str] = None,
        limit: int = 20
    ) -> List[EvolutionRecord]:
        """获取进化历史"""
        with self._lock:
            history = self._evolution_history
            
            if skill_id:
                history = [r for r in history if r.skill_id == skill_id]
            
            return history[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_evolutions": len(self._evolution_history),
            "validation_stats": self.validator.get_validation_stats(),
            "pattern_stats": self.extractor.get_pattern_statistics()
        }
    
    def _get_skill(self, skill_id: str) -> Optional[SkillCandidate]:
        """获取技能"""
        if self.skill_system:
            return self.skill_system.get_skill(skill_id)
        return None
    
    def _apply_skill(self, skill: SkillCandidate):
        """应用技能"""
        if self.skill_system:
            try:
                self.skill_system.register_skill(skill)
            except Exception:
                logger.debug(f"忽略异常: self.skill_system.register_skill(skill)", exc_info=True)
                pass
    
    def _record_evolution(
        self, 
        skill_id: str, 
        stage: SkillEvolutionStage,
        changes: Dict[str, Any]
    ):
        """记录进化"""
        record = EvolutionRecord(
            id=self._generate_id(),
            skill_id=skill_id,
            stage=stage,
            changes=changes
        )
        
        with self._lock:
            self._evolution_history.append(record)
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        content = f"evolution:{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
