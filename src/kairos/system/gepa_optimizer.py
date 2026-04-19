"""
GEPA优化器 - 反思式提示进化引擎

设计理念来源:
- KEPA系统: 提示反向传播机制
- GEPA论文: Genetic-Pareto反射式提示进化
- DSPy框架: 自动提示优化

核心特性:
1. 反思-变异-接受循环
2. 多目标Pareto优化
3. 约束门控机制
4. 轨迹记录与分析
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar

T = TypeVar('T')


class OptimizationStrategy(Enum):
    """优化策略枚举"""
    REFLECTIVE = "reflective"
    RANDOM = "random"
    HYBRID = "hybrid"


class MutationType(Enum):
    """变异类型枚举"""
    INSTRUCTION = "instruction"
    FEW_SHOT = "few_shot"
    STRUCTURE = "structure"
    PARAMETER = "parameter"
    HYBRID = "hybrid"


class AcceptanceCriteria(Enum):
    """接受标准枚举"""
    IMPROVEMENT = "improvement"
    PARETO = "pareto"
    THRESHOLD = "threshold"
    DIVERSITY = "diversity"


@dataclass
class GEPAConfig:
    """GEPA优化器配置"""
    max_iterations: int = 100
    population_size: int = 10
    elite_size: int = 2
    mutation_rate: float = 0.3
    crossover_rate: float = 0.7
    strategy: OptimizationStrategy = OptimizationStrategy.HYBRID
    acceptance_criteria: AcceptanceCriteria = AcceptanceCriteria.PARETO
    convergence_threshold: float = 0.001
    max_stagnation: int = 10
    parallel_evaluation: bool = True
    log_dir: str = ""
    checkpoint_interval: int = 10


@dataclass
class Trajectory:
    """执行轨迹"""
    id: str
    inputs: List[Any] = field(default_factory=list)
    outputs: List[Any] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    reasoning: List[str] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    duration: float = 0.0
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "errors": self.errors,
            "reasoning": self.reasoning,
            "tool_calls": self.tool_calls,
            "duration": self.duration,
            "success": self.success,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class Reflection:
    """反思结果"""
    diagnosis: str
    root_causes: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Mutation:
    """变异记录"""
    type: MutationType
    description: str
    changes: Dict[str, Any]
    parent_id: str
    child_id: str
    fitness: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Program(Generic[T]):
    """可优化程序"""
    id: str
    instructions: str
    few_shot_examples: List[Dict[str, Any]] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    structure: Dict[str, Any] = field(default_factory=dict)
    code: str = ""
    fitness: float = 0.0
    generation: int = 0
    parent_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "instructions": self.instructions,
            "few_shot_examples": self.few_shot_examples,
            "parameters": self.parameters,
            "structure": self.structure,
            "code": self.code,
            "fitness": self.fitness,
            "generation": self.generation,
            "parent_ids": self.parent_ids,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Program':
        return cls(
            id=data.get("id", ""),
            instructions=data.get("instructions", ""),
            few_shot_examples=data.get("few_shot_examples", []),
            parameters=data.get("parameters", {}),
            structure=data.get("structure", {}),
            code=data.get("code", ""),
            fitness=data.get("fitness", 0.0),
            generation=data.get("generation", 0),
            parent_ids=data.get("parent_ids", []),
            metadata=data.get("metadata", {})
        )


class Reflector:
    """
    反思器 - 分析执行轨迹，诊断失败原因
    
    核心功能:
    1. 轨迹分析: 识别失败点和瓶颈
    2. 根因诊断: 定位问题根源
    3. 改进建议: 生成优化方向
    4. 经验提取: 总结可复用教训
    """
    
    def __init__(self, llm_client: Optional[Any] = None):
        self.llm_client = llm_client
        self._reflection_history: List[Reflection] = []
    
    def analyze(self, trajectory: Trajectory) -> Reflection:
        """分析执行轨迹"""
        diagnosis = self._diagnose(trajectory)
        root_causes = self._find_root_causes(trajectory)
        suggestions = self._generate_suggestions(trajectory, root_causes)
        lessons = self._extract_lessons(trajectory)
        confidence = self._calculate_confidence(trajectory)
        
        reflection = Reflection(
            diagnosis=diagnosis,
            root_causes=root_causes,
            improvement_suggestions=suggestions,
            lessons_learned=lessons,
            confidence=confidence
        )
        
        self._reflection_history.append(reflection)
        return reflection
    
    def analyze_batch(self, trajectories: List[Trajectory]) -> List[Reflection]:
        """批量分析轨迹"""
        return [self.analyze(t) for t in trajectories]
    
    def _diagnose(self, trajectory: Trajectory) -> str:
        """诊断问题"""
        if not trajectory.errors:
            return "执行成功，无明显问题"
        
        error_types = {}
        for error in trajectory.errors:
            error_type = self._classify_error(error)
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        main_issue = max(error_types.items(), key=lambda x: x[1])
        return f"主要问题: {main_issue[0]} (出现{main_issue[1]}次)"
    
    def _find_root_causes(self, trajectory: Trajectory) -> List[str]:
        """查找根本原因"""
        causes = []
        
        for i, error in enumerate(trajectory.errors):
            cause = self._trace_error_source(error, trajectory, i)
            if cause and cause not in causes:
                causes.append(cause)
        
        return causes
    
    def _generate_suggestions(
        self, 
        trajectory: Trajectory, 
        root_causes: List[str]
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        for cause in root_causes:
            suggestion = self._cause_to_suggestion(cause, trajectory)
            if suggestion:
                suggestions.append(suggestion)
        
        if trajectory.duration > 10.0:
            suggestions.append("考虑优化执行路径以提高效率")
        
        return suggestions
    
    def _extract_lessons(self, trajectory: Trajectory) -> List[str]:
        """提取经验教训"""
        lessons = []
        
        if trajectory.success:
            lessons.append(f"成功模式: {self._summarize_success_pattern(trajectory)}")
        
        for error in trajectory.errors:
            lesson = self._error_to_lesson(error)
            if lesson:
                lessons.append(lesson)
        
        return lessons
    
    def _calculate_confidence(self, trajectory: Trajectory) -> float:
        """计算反思置信度"""
        if not trajectory.errors:
            return 0.9
        
        error_ratio = len(trajectory.errors) / max(1, len(trajectory.outputs))
        return max(0.1, 1.0 - error_ratio)
    
    def _classify_error(self, error: str) -> str:
        """分类错误类型"""
        error_lower = error.lower()
        
        if "timeout" in error_lower:
            return "超时错误"
        elif "connection" in error_lower or "network" in error_lower:
            return "网络错误"
        elif "permission" in error_lower or "access" in error_lower:
            return "权限错误"
        elif "syntax" in error_lower or "parse" in error_lower:
            return "语法错误"
        elif "type" in error_lower:
            return "类型错误"
        elif "value" in error_lower:
            return "值错误"
        else:
            return "未知错误"
    
    def _trace_error_source(
        self, 
        error: str, 
        trajectory: Trajectory, 
        error_index: int
    ) -> Optional[str]:
        """追踪错误来源"""
        if error_index < len(trajectory.inputs):
            return f"输入问题: {str(trajectory.inputs[error_index])[:100]}"
        return None
    
    def _cause_to_suggestion(
        self, 
        cause: str, 
        trajectory: Trajectory
    ) -> Optional[str]:
        """将原因转换为建议"""
        if "输入问题" in cause:
            return "改进输入验证和预处理"
        return f"针对'{cause}'进行优化"
    
    def _summarize_success_pattern(self, trajectory: Trajectory) -> str:
        """总结成功模式"""
        if trajectory.tool_calls:
            tools_used = [tc.get("tool", "unknown") for tc in trajectory.tool_calls]
            return f"工具调用序列: {' -> '.join(tools_used[:5])}"
        return "直接执行成功"
    
    def _error_to_lesson(self, error: str) -> Optional[str]:
        """将错误转换为教训"""
        error_type = self._classify_error(error)
        return f"避免{error_type}: 添加相应检查和处理"


class Mutator:
    """
    变异器 - 基于反思生成改进候选
    
    核心功能:
    1. 反思变异: 基于失败分析生成改进
    2. 随机探索: 随机生成新候选
    3. 交叉重组: 组合优秀特性
    4. 约束满足: 确保变异有效性
    """
    
    def __init__(self, config: GEPAConfig):
        self.config = config
        self._mutation_history: List[Mutation] = []
        self._lesson_bank: List[str] = []
    
    def generate(
        self, 
        program: Program, 
        reflection: Reflection,
        strategy: OptimizationStrategy = OptimizationStrategy.HYBRID
    ) -> List[Program]:
        """生成变异候选"""
        candidates = []
        
        if strategy in [OptimizationStrategy.REFLECTIVE, OptimizationStrategy.HYBRID]:
            reflective_candidates = self._reflective_mutate(program, reflection)
            candidates.extend(reflective_candidates)
        
        if strategy in [OptimizationStrategy.RANDOM, OptimizationStrategy.HYBRID]:
            random_candidates = self._random_mutate(program)
            candidates.extend(random_candidates)
        
        for candidate in candidates:
            self._record_mutation(program, candidate)
        
        return candidates
    
    def crossover(self, parent1: Program, parent2: Program) -> List[Program]:
        """交叉重组"""
        children = []
        
        child1_instructions = self._blend_instructions(
            parent1.instructions, parent2.instructions
        )
        child1 = Program(
            id=self._generate_id(),
            instructions=child1_instructions,
            few_shot_examples=parent1.few_shot_examples[:2] + parent2.few_shot_examples[:2],
            parameters={**parent1.parameters, **parent2.parameters},
            generation=max(parent1.generation, parent2.generation) + 1,
            parent_ids=[parent1.id, parent2.id]
        )
        children.append(child1)
        
        return children
    
    def _reflective_mutate(
        self, 
        program: Program, 
        reflection: Reflection
    ) -> List[Program]:
        """反思式变异"""
        candidates = []
        
        for suggestion in reflection.improvement_suggestions[:3]:
            new_instructions = self._apply_suggestion(
                program.instructions, suggestion
            )
            
            candidate = Program(
                id=self._generate_id(),
                instructions=new_instructions,
                few_shot_examples=program.few_shot_examples.copy(),
                parameters=program.parameters.copy(),
                structure=program.structure.copy(),
                generation=program.generation + 1,
                parent_ids=[program.id],
                metadata={"mutation_type": "reflective", "suggestion": suggestion}
            )
            candidates.append(candidate)
        
        if reflection.lessons_learned:
            self._lesson_bank.extend(reflection.lessons_learned)
        
        return candidates
    
    def _random_mutate(self, program: Program) -> List[Program]:
        """随机变异"""
        candidates = []
        
        mutation_types = [
            MutationType.INSTRUCTION,
            MutationType.FEW_SHOT,
            MutationType.PARAMETER
        ]
        
        for mut_type in mutation_types:
            if mut_type == MutationType.INSTRUCTION:
                new_instructions = self._mutate_instructions(program.instructions)
                candidate = Program(
                    id=self._generate_id(),
                    instructions=new_instructions,
                    few_shot_examples=program.few_shot_examples.copy(),
                    parameters=program.parameters.copy(),
                    generation=program.generation + 1,
                    parent_ids=[program.id],
                    metadata={"mutation_type": "random_instruction"}
                )
            elif mut_type == MutationType.FEW_SHOT:
                new_examples = self._mutate_few_shot(program.few_shot_examples)
                candidate = Program(
                    id=self._generate_id(),
                    instructions=program.instructions,
                    few_shot_examples=new_examples,
                    parameters=program.parameters.copy(),
                    generation=program.generation + 1,
                    parent_ids=[program.id],
                    metadata={"mutation_type": "random_few_shot"}
                )
            else:
                new_params = self._mutate_parameters(program.parameters)
                candidate = Program(
                    id=self._generate_id(),
                    instructions=program.instructions,
                    few_shot_examples=program.few_shot_examples.copy(),
                    parameters=new_params,
                    generation=program.generation + 1,
                    parent_ids=[program.id],
                    metadata={"mutation_type": "random_parameter"}
                )
            
            candidates.append(candidate)
        
        return candidates
    
    def _apply_suggestion(self, instructions: str, suggestion: str) -> str:
        """应用改进建议"""
        if not instructions:
            return suggestion
        
        return f"{instructions}\n\n改进建议: {suggestion}"
    
    def _mutate_instructions(self, instructions: str) -> str:
        """变异指令"""
        mutations = [
            lambda x: x.replace("请", "务必"),
            lambda x: f"仔细执行: {x}",
            lambda x: f"{x}\n注意: 确保准确性",
            lambda x: x.replace("。", "，并验证结果。")
        ]
        
        import random
        mutation = random.choice(mutations)
        return mutation(instructions)
    
    def _mutate_few_shot(
        self, 
        examples: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """变异Few-shot示例"""
        if not examples:
            return examples
        
        import random
        new_examples = examples.copy()
        
        if random.random() < 0.5 and len(new_examples) > 0:
            idx = random.randint(0, len(new_examples) - 1)
            new_examples[idx] = {
                **new_examples[idx],
                "mutated": True
            }
        
        return new_examples
    
    def _mutate_parameters(
        self, 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """变异参数"""
        import random
        new_params = parameters.copy()
        
        for key, value in new_params.items():
            if isinstance(value, (int, float)):
                change = random.uniform(-0.1, 0.1)
                new_params[key] = value * (1 + change)
        
        return new_params
    
    def _blend_instructions(
        self, 
        inst1: str, 
        inst2: str
    ) -> str:
        """混合指令"""
        lines1 = inst1.split('\n')
        lines2 = inst2.split('\n')
        
        blended = []
        for i, (l1, l2) in enumerate(zip(lines1, lines2)):
            if i % 2 == 0:
                blended.append(l1)
            else:
                blended.append(l2)
        
        blended.extend(lines1[len(lines2):])
        blended.extend(lines2[len(lines1):])
        
        return '\n'.join(blended)
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        content = f"mutation:{time.time()}:{threading.get_ident()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _record_mutation(self, parent: Program, child: Program):
        """记录变异"""
        mutation = Mutation(
            type=MutationType.HYBRID,
            description=f"从{parent.id}变异到{child.id}",
            changes={"parent_fitness": parent.fitness},
            parent_id=parent.id,
            child_id=child.id
        )
        self._mutation_history.append(mutation)


class ParetoEvaluator:
    """
    Pareto评估器 - 多目标效率评估
    
    核心功能:
    1. 多目标评估: 同时考虑多个优化目标
    2. Pareto前沿: 识别非支配解
    3. 多样性保持: 维护种群多样性
    4. 精英保留: 保护优秀个体
    """
    
    def __init__(self, objectives: List[Callable[[Program], float]]):
        self.objectives = objectives
        self._evaluation_cache: Dict[str, List[float]] = {}
    
    def evaluate(
        self, 
        candidates: List[Program]
    ) -> List[Tuple[Program, List[float]]]:
        """评估候选程序"""
        results = []
        
        for candidate in candidates:
            if candidate.id in self._evaluation_cache:
                scores = self._evaluation_cache[candidate.id]
            else:
                scores = [obj(candidate) for obj in self.objectives]
                self._evaluation_cache[candidate.id] = scores
            
            results.append((candidate, scores))
        
        return results
    
    def find_pareto_front(
        self, 
        evaluated: List[Tuple[Program, List[float]]]
    ) -> List[Tuple[Program, List[float]]]:
        """找到Pareto前沿"""
        pareto_front = []
        
        for i, (prog_i, scores_i) in enumerate(evaluated):
            dominated = False
            
            for j, (prog_j, scores_j) in enumerate(evaluated):
                if i != j and self._dominates(scores_j, scores_i):
                    dominated = True
                    break
            
            if not dominated:
                pareto_front.append((prog_i, scores_i))
        
        return pareto_front
    
    def select(
        self, 
        evaluated: List[Tuple[Program, List[float]]],
        method: str = "crowding"
    ) -> Program:
        """从评估结果中选择"""
        pareto_front = self.find_pareto_front(evaluated)
        
        if not pareto_front:
            pareto_front = evaluated
        
        if method == "crowding":
            return self._crowding_selection(pareto_front)
        elif method == "random":
            import random
            return random.choice(pareto_front)[0]
        else:
            return self._best_selection(pareto_front)
    
    def _dominates(
        self, 
        scores1: List[float], 
        scores2: List[float]
    ) -> bool:
        """判断是否支配"""
        better_or_equal = all(s1 >= s2 for s1, s2 in zip(scores1, scores2))
        strictly_better = any(s1 > s2 for s1, s2 in zip(scores1, scores2))
        return better_or_equal and strictly_better
    
    def _crowding_selection(
        self, 
        front: List[Tuple[Program, List[float]]]
    ) -> Program:
        """拥挤度选择"""
        if len(front) == 1:
            return front[0][0]
        
        crowding_distances = self._calculate_crowding_distances(front)
        
        max_idx = max(range(len(front)), key=lambda i: crowding_distances[i])
        return front[max_idx][0]
    
    def _calculate_crowding_distances(
        self, 
        front: List[Tuple[Program, List[float]]]
    ) -> List[float]:
        """计算拥挤距离"""
        n = len(front)
        distances = [0.0] * n
        
        for obj_idx in range(len(self.objectives)):
            sorted_indices = sorted(
                range(n), 
                key=lambda i: front[i][1][obj_idx]
            )
            
            distances[sorted_indices[0]] = float('inf')
            distances[sorted_indices[-1]] = float('inf')
            
            for i in range(1, n - 1):
                prev_val = front[sorted_indices[i - 1]][1][obj_idx]
                next_val = front[sorted_indices[i + 1]][1][obj_idx]
                
                range_val = max(f[1][obj_idx] for f in front) - \
                           min(f[1][obj_idx] for f in front)
                
                if range_val > 0:
                    distances[sorted_indices[i]] += \
                        (next_val - prev_val) / range_val
        
        return distances
    
    def _best_selection(
        self, 
        front: List[Tuple[Program, List[float]]]
    ) -> Program:
        """选择最优"""
        return max(front, key=lambda x: sum(x[1]))[0]
    
    def clear_cache(self):
        """清除缓存"""
        self._evaluation_cache.clear()


class TrajectoryRecorder:
    """
    轨迹记录器 - 记录和分析执行轨迹
    
    核心功能:
    1. 轨迹捕获: 自动记录执行过程
    2. 持久化存储: 保存轨迹历史
    3. 统计分析: 轨迹统计和模式识别
    """
    
    def __init__(self, storage_dir: str = ""):
        self.storage_dir = Path(storage_dir) if storage_dir else None
        self._trajectories: Dict[str, Trajectory] = {}
        self._lock = threading.Lock()
    
    def start_recording(self, trajectory_id: str) -> Trajectory:
        """开始记录"""
        trajectory = Trajectory(id=trajectory_id)
        with self._lock:
            self._trajectories[trajectory_id] = trajectory
        return trajectory
    
    def record_input(
        self, 
        trajectory_id: str, 
        input_data: Any
    ):
        """记录输入"""
        with self._lock:
            if trajectory_id in self._trajectories:
                self._trajectories[trajectory_id].inputs.append(input_data)
    
    def record_output(
        self, 
        trajectory_id: str, 
        output_data: Any
    ):
        """记录输出"""
        with self._lock:
            if trajectory_id in self._trajectories:
                self._trajectories[trajectory_id].outputs.append(output_data)
    
    def record_error(
        self, 
        trajectory_id: str, 
        error: str
    ):
        """记录错误"""
        with self._lock:
            if trajectory_id in self._trajectories:
                self._trajectories[trajectory_id].errors.append(error)
                self._trajectories[trajectory_id].success = False
    
    def record_tool_call(
        self, 
        trajectory_id: str, 
        tool_name: str, 
        args: Dict[str, Any],
        result: Any = None
    ):
        """记录工具调用"""
        with self._lock:
            if trajectory_id in self._trajectories:
                self._trajectories[trajectory_id].tool_calls.append({
                    "tool": tool_name,
                    "args": args,
                    "result": result,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
    
    def finish_recording(
        self, 
        trajectory_id: str
    ) -> Optional[Trajectory]:
        """结束记录"""
        with self._lock:
            trajectory = self._trajectories.get(trajectory_id)
            if trajectory:
                trajectory.duration = time.time() - \
                    trajectory.timestamp.timestamp()
                
                if self.storage_dir:
                    self._save_trajectory(trajectory)
                
                return trajectory
        return None
    
    def get_trajectory(self, trajectory_id: str) -> Optional[Trajectory]:
        """获取轨迹"""
        return self._trajectories.get(trajectory_id)
    
    def get_all_trajectories(self) -> List[Trajectory]:
        """获取所有轨迹"""
        return list(self._trajectories.values())
    
    def _save_trajectory(self, trajectory: Trajectory):
        """保存轨迹"""
        if not self.storage_dir:
            return
        
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        filepath = self.storage_dir / f"{trajectory.id}.json"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(trajectory.to_dict(), f, indent=2, ensure_ascii=False)


class GEPAOptimizer:
    """
    GEPA优化器主类
    
    整合反思-变异-接受循环，实现提示和配置的自动进化
    
    使用方式:
        config = GEPAConfig(max_iterations=50)
        optimizer = GEPAOptimizer(config)
        
        def metric(program):
            return evaluate_program(program)
        
        best_program = optimizer.optimize(initial_program, metric)
    """
    
    def __init__(self, config: GEPAConfig):
        self.config = config
        self.reflector = Reflector()
        self.mutator = Mutator(config)
        self.evaluator: Optional[ParetoEvaluator] = None
        self.trajectory_recorder = TrajectoryRecorder(config.log_dir)
        
        self.population: List[Program] = []
        self.best_program: Optional[Program] = None
        self.best_score: float = float('-inf')
        self.history: List[Dict[str, Any]] = []
        self.generation: int = 0
        self.stagnation_count: int = 0
        
        self._lock = threading.Lock()
        self._constraint_gates: List[Callable[[Program], bool]] = []
    
    def set_objectives(self, objectives: List[Callable[[Program], float]]):
        """设置优化目标"""
        self.evaluator = ParetoEvaluator(objectives)
    
    def add_constraint_gate(self, gate: Callable[[Program], bool]):
        """添加约束门"""
        self._constraint_gates.append(gate)
    
    def optimize(
        self, 
        initial_program: Program, 
        metric: Callable[[Program], float],
        callback: Optional[Callable[[int, Program, float], None]] = None
    ) -> Program:
        """
        执行优化
        
        Args:
            initial_program: 初始程序
            metric: 评估指标函数
            callback: 迭代回调函数
            
        Returns:
            优化后的最佳程序
        """
        self.population = [initial_program]
        self.best_program = initial_program
        self.best_score = metric(initial_program)
        self.generation = 0
        self.stagnation_count = 0
        
        for iteration in range(self.config.max_iterations):
            self.generation = iteration
            
            trajectory_id = f"gen_{iteration}_prog_0"
            self.trajectory_recorder.start_recording(trajectory_id)
            
            current = self._select_parent()
            
            trajectory = self._execute_program(current, trajectory_id)
            reflection = self.reflector.analyze(trajectory)
            
            candidates = self.mutator.generate(
                current, reflection, self.config.strategy
            )
            
            valid_candidates = [
                c for c in candidates 
                if self._check_constraints(c)
            ]
            
            if not valid_candidates:
                continue
            
            for candidate in valid_candidates:
                score = metric(candidate)
                candidate.fitness = score
                
                if score > self.best_score:
                    self.best_score = score
                    self.best_program = candidate
                    self.stagnation_count = 0
                else:
                    self.stagnation_count += 1
            
            self._update_population(valid_candidates)
            
            if self.evaluator:
                evaluated = self.evaluator.evaluate(self.population)
                self.population = [
                    p for p, _ in self.evaluator.find_pareto_front(evaluated)
                ]
            
            self._record_history(iteration, current, self.best_score)
            
            if callback:
                callback(iteration, self.best_program, self.best_score)
            
            if self._check_convergence():
                break
            
            if iteration % self.config.checkpoint_interval == 0:
                self._save_checkpoint()
        
        return self.best_program
    
    def _select_parent(self) -> Program:
        """选择父代"""
        import random
        
        if len(self.population) == 1:
            return self.population[0]
        
        tournament_size = min(3, len(self.population))
        tournament = random.sample(self.population, tournament_size)
        
        return max(tournament, key=lambda p: p.fitness)
    
    def _execute_program(
        self, 
        program: Program, 
        trajectory_id: str
    ) -> Trajectory:
        """执行程序"""
        self.trajectory_recorder.record_input(
            trajectory_id, 
            {"program_id": program.id, "instructions": program.instructions}
        )
        
        try:
            if program.code:
                exec_result = self._safe_exec(program.code)
                self.trajectory_recorder.record_output(trajectory_id, exec_result)
            else:
                self.trajectory_recorder.record_output(
                    trajectory_id, 
                    {"status": "no_code", "instructions": program.instructions}
                )
        except Exception as e:
            self.trajectory_recorder.record_error(trajectory_id, str(e))
        
        return self.trajectory_recorder.finish_recording(trajectory_id)
    
    def _safe_exec(self, code: str) -> Dict[str, Any]:
        """安全执行代码"""
        try:
            local_vars = {}
            exec(code, {"__builtins__": {}}, local_vars)
            return {"success": True, "result": local_vars}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _check_constraints(self, program: Program) -> bool:
        """检查约束"""
        for gate in self._constraint_gates:
            if not gate(program):
                return False
        return True
    
    def _update_population(self, new_candidates: List[Program]):
        """更新种群"""
        self.population.extend(new_candidates)
        
        self.population.sort(key=lambda p: p.fitness, reverse=True)
        
        if len(self.population) > self.config.population_size:
            self.population = self.population[:self.config.population_size]
    
    def _record_history(
        self, 
        iteration: int, 
        current: Program, 
        best_score: float
    ):
        """记录历史"""
        self.history.append({
            "iteration": iteration,
            "current_id": current.id,
            "current_fitness": current.fitness,
            "best_score": best_score,
            "population_size": len(self.population),
            "stagnation_count": self.stagnation_count
        })
    
    def _check_convergence(self) -> bool:
        """检查收敛"""
        if self.stagnation_count >= self.config.max_stagnation:
            return True
        
        if len(self.history) >= 2:
            recent_improvement = abs(
                self.history[-1]["best_score"] - 
                self.history[-2]["best_score"]
            )
            if recent_improvement < self.config.convergence_threshold:
                return True
        
        return False
    
    def _save_checkpoint(self):
        """保存检查点"""
        if not self.config.log_dir:
            return
        
        checkpoint_dir = Path(self.config.log_dir)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        checkpoint = {
            "generation": self.generation,
            "best_program": self.best_program.to_dict() if self.best_program else None,
            "best_score": self.best_score,
            "population": [p.to_dict() for p in self.population],
            "history": self.history
        }
        
        filepath = checkpoint_dir / f"checkpoint_gen_{self.generation}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, indent=2, ensure_ascii=False)
    
    def load_checkpoint(self, filepath: str) -> bool:
        """加载检查点"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
            
            self.generation = checkpoint["generation"]
            self.best_score = checkpoint["best_score"]
            self.history = checkpoint["history"]
            
            if checkpoint["best_program"]:
                self.best_program = Program.from_dict(checkpoint["best_program"])
            
            self.population = [
                Program.from_dict(p) for p in checkpoint["population"]
            ]
            
            return True
        except Exception:
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "generation": self.generation,
            "best_score": self.best_score,
            "population_size": len(self.population),
            "stagnation_count": self.stagnation_count,
            "history_length": len(self.history),
            "average_fitness": sum(p.fitness for p in self.population) / 
                              max(1, len(self.population))
        }
