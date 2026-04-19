# -*- coding: utf-8 -*-
"""
统一枚举定义模块
消除全系统重复枚举，提供单一事实来源
所有模块应从此处导入枚举，而非各自定义
"""

from enum import Enum


# ============================================================
# 第一组: 系统状态枚举
# ============================================================

class HeartStatus(Enum):
    """心脏模块状态"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class ServiceStatus(Enum):
    """服务状态"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class LoopStatus(Enum):
    """循环状态"""
    IDLE = "idle"
    PROCESSING = "processing"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SessionState(Enum):
    """会话状态"""
    CREATED = "created"
    ACTIVE = "active"
    IDLE = "idle"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class FlowStatus(Enum):
    """流程状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CommandStatus(Enum):
    """命令状态"""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolStatus(Enum):
    """工具状态"""
    AVAILABLE = "available"
    BUSY = "busy"
    ERROR = "error"
    DISABLED = "disabled"


class ChangeStatus(Enum):
    """变更状态"""
    PENDING = "pending"
    APPLIED = "applied"
    REVERTED = "reverted"
    FAILED = "failed"


# ============================================================
# 第二组: 优先级/严重程度枚举
# ============================================================

class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContextPriority(Enum):
    """上下文优先级"""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


class EventPriority(Enum):
    """事件优先级"""
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


class IssueSeverity(Enum):
    """问题严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ViolationSeverity(Enum):
    """违规严重程度"""
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


class RiskLevel(Enum):
    """风险级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NudgePriority(Enum):
    """推动优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================
# 第三组: 错误/恢复枚举
# ============================================================

class ErrorCategory(Enum):
    """错误类别"""
    NETWORK = "network"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    LLM = "llm"
    TOOL = "tool"
    VALIDATION = "validation"
    PERMISSION = "permission"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """恢复策略"""
    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    ABORT = "abort"
    ESCALATE = "escalate"


class VerificationStatus(Enum):
    """验证状态"""
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"
    PARTIAL = "partial"


# ============================================================
# 第四组: 记忆枚举
# ============================================================

class MemoryType(Enum):
    """记忆类型"""
    WORKING = "working"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryPriority(Enum):
    """记忆优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MemoryStatus(Enum):
    """记忆状态"""
    ACTIVE = "active"
    CONSOLIDATING = "consolidating"
    ARCHIVED = "archived"
    FORGOTTEN = "forgotten"


# ============================================================
# 第五组: 技能枚举
# ============================================================

class SkillCategory(Enum):
    """技能类别"""
    ANALYSIS = "analysis"
    EXECUTION = "execution"
    COMMUNICATION = "communication"
    LEARNING = "learning"
    REASONING = "reasoning"
    PERCEPTION = "perception"
    CREATIVITY = "creativity"
    MANAGEMENT = "management"


class SkillStatus(Enum):
    """技能状态"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    EVOLVING = "evolving"


class SkillLevel(Enum):
    """技能等级"""
    NOVICE = 1
    BEGINNER = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5


class SecurityLevel(Enum):
    """安全级别"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


# ============================================================
# 第六组: 执行模式枚举
# ============================================================

class ExecutionMode(Enum):
    """执行模式"""
    AUTOMATIC = "automatic"
    INTERACTIVE = "interactive"
    HYBRID = "hybrid"
    AUTONOMOUS = "autonomous"
    SUPERVISED = "supervised"


class TaskComplexity(Enum):
    """任务复杂度"""
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXTREME = "extreme"


class TaskType(Enum):
    """任务类型"""
    ANALYSIS = "analysis"
    EXECUTION = "execution"
    LEARNING = "learning"
    COMMUNICATION = "communication"
    MONITORING = "monitoring"
    MAINTENANCE = "maintenance"


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================
# 第七组: 认知/推理枚举
# ============================================================

class CognitiveLayerType(Enum):
    """认知层类型"""
    PERCEPTION = "perception"
    INTEGRATION = "integration"
    DECISION = "decision"
    EXECUTION = "execution"
    EVALUATION = "evaluation"
    FEEDBACK = "feedback"


class FeedbackType(Enum):
    """反馈类型"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    CORRECTIVE = "corrective"
    SUGGESTIVE = "suggestive"


class CausalRelationType(Enum):
    """因果关系类型"""
    DIRECT = "direct"
    INDIRECT = "indirect"
    CONTRIBUTING = "contributing"
    NECESSARY = "necessary"
    SUFFICIENT = "sufficient"


class NodeType(Enum):
    """节点类型"""
    CAUSE = "cause"
    EFFECT = "effect"
    MEDIATOR = "mediator"
    MODERATOR = "moderator"
    CONFOUNDER = "confounder"


class PhysicalLawType(Enum):
    """物理定律类型"""
    ENERGY_CONSERVATION = "energy_conservation"
    MOMENTUM_CONSERVATION = "momentum_conservation"
    ENTROPY = "entropy"
    HEAT_FLOW = "heat_flow"
    TEMPORAL_ORDER = "temporal_order"


class ConfounderType(Enum):
    """混淆因素类型"""
    SELECTION_BIAS = "selection_bias"
    MEASUREMENT_ERROR = "measurement_error"
    OMITTED_VARIABLE = "omitted_variable"
    REVERSE_CAUSALITY = "reverse_causality"
    SPURIOUS_CORRELATION = "spurious_correlation"


# ============================================================
# 第八组: 感知枚举
# ============================================================

class ContextType(Enum):
    """上下文类型"""
    TASK = "task"
    ENVIRONMENT = "environment"
    USER = "user"
    SYSTEM = "system"
    CONVERSATION = "conversation"
    TEMPORAL = "temporal"
    SOCIAL = "social"
    EMOTIONAL = "emotional"


class EmotionalState(Enum):
    """情绪状态"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    ANXIOUS = "anxious"
    CONFUSED = "confused"
    EXCITED = "excited"
    FRUSTRATED = "frustrated"


class CognitiveLoadLevel(Enum):
    """认知负荷级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    OVERLOADED = "overloaded"


class EngagementLevel(Enum):
    """参与度级别"""
    DISENGAGED = "disengaged"
    PASSIVE = "passive"
    ACTIVE = "active"
    HIGHLY_ENGAGED = "highly_engaged"


class ContentType(Enum):
    """内容类型"""
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DATA = "data"
    COMMAND = "command"


# ============================================================
# 第九组: 注意力枚举
# ============================================================

class AttentionType(Enum):
    """注意力类型"""
    SWA = "swa"
    DSWA = "dswa"
    GLA = "gla"
    HYBRID = "hybrid"


# ============================================================
# 第十组: 进化/学习枚举
# ============================================================

class EvolutionPhase(Enum):
    """进化阶段"""
    INITIALIZATION = "initialization"
    EXPLORATION = "exploration"
    ADAPTATION = "adaptation"
    OPTIMIZATION = "optimization"
    STABILIZATION = "stabilization"


class AdaptationType(Enum):
    """适应类型"""
    PARAMETER = "parameter"
    STRATEGY = "strategy"
    STRUCTURAL = "structural"
    BEHAVIORAL = "behavioral"


class KnowledgeType(Enum):
    """知识类型"""
    FACTUAL = "factual"
    PROCEDURAL = "procedural"
    CONCEPTUAL = "conceptual"
    METACOGNITIVE = "metacognitive"
    EXPERIENTIAL = "experiential"


class DistillationPhase(Enum):
    """蒸馏阶段"""
    INGESTION = "ingestion"
    EXTRACTION = "extraction"
    COMPRESSION = "compression"
    GENERALIZATION = "generalization"
    VALIDATION = "validation"


class KnowledgeStatus(Enum):
    """知识状态"""
    RAW = "raw"
    EXTRACTED = "extracted"
    COMPRESSED = "compressed"
    GENERALIZED = "generalized"
    VALIDATED = "validated"


class LearningStage(Enum):
    """学习阶段"""
    ACQUISITION = "acquisition"
    CONSOLIDATION = "consolidation"
    RETRIEVAL = "retrieval"
    APPLICATION = "application"
    REFLECTION = "reflection"


class LearningStatus(Enum):
    """学习状态"""
    IDLE = "idle"
    LEARNING = "learning"
    PRACTICING = "practicing"
    MASTERED = "mastered"
    DORMANT = "dormant"


class LearningPhase(Enum):
    """学习阶段(增强版)"""
    OBSERVATION = "observation"
    IMITATION = "imitation"
    PRACTICE = "practice"
    REFLECTION = "reflection"
    INNOVATION = "innovation"


class ImprovementType(Enum):
    """改进类型"""
    SPEED = "speed"
    ACCURACY = "accuracy"
    EFFICIENCY = "efficiency"
    ROBUSTNESS = "robustness"
    ADAPTABILITY = "adaptability"


class SkillContext(Enum):
    """技能上下文"""
    GENERAL = "general"
    CODING = "coding"
    ANALYSIS = "analysis"
    COMMUNICATION = "communication"
    PROBLEM_SOLVING = "problem_solving"


# ============================================================
# 第十一组: Kairos决策枚举
# ============================================================

class KairosMode(Enum):
    """Kairos模式"""
    OBSERVE = "observe"
    THINK = "think"
    ACT = "act"
    REFLECT = "reflect"
    EVOLVE = "evolve"


class KairosStrategy(Enum):
    """Kairos策略"""
    IMMEDIATE = "immediate"
    DEFERRED = "deferred"
    BATCHED = "batched"
    INTERACTIVE = "interactive"
    AUTONOMOUS = "autonomous"
    CONSERVATIVE = "conservative"


class KairosMemoryType(Enum):
    """Kairos记忆类型"""
    USER = "user"
    FEEDBACK = "feedback"
    PROJECT = "project"
    REFERENCE = "reference"


class KairosUrgency(Enum):
    """Kairos紧急程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================
# 第十二组: 工具/平台枚举
# ============================================================

class ToolCategory(Enum):
    """工具类别"""
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    SYSTEM = "system"
    DEVELOPMENT = "development"
    DATA = "data"
    COMMUNICATION = "communication"
    AUTOMATION = "automation"


class PlatformType(Enum):
    """平台类型"""
    WECHAT = "wechat"
    EMAIL = "email"
    SLACK = "slack"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WEBHOOK = "webhook"


class GitOperation(Enum):
    """Git操作"""
    COMMIT = "commit"
    PUSH = "push"
    PULL = "pull"
    MERGE = "merge"
    REBASE = "rebase"
    CHECKOUT = "checkout"
    BRANCH = "branch"
    TAG = "tag"


class BranchType(Enum):
    """分支类型"""
    MAIN = "main"
    DEVELOP = "develop"
    FEATURE = "feature"
    RELEASE = "release"
    HOTFIX = "hotfix"


class ChangeType(Enum):
    """变更类型"""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    MOVED = "moved"


# ============================================================
# 第十三组: 神经系统枚举
# ============================================================

class NeuronType(Enum):
    """神经元类型"""
    SENSORY = "sensory"
    INTERNEURON = "interneuron"
    MOTOR = "motor"
    MODULATORY = "modulatory"


class SynapseType(Enum):
    """突触类型"""
    EXCITATORY = "excitatory"
    INHIBITORY = "inhibitory"
    MODULATORY = "modulatory"


class PlasticityType(Enum):
    """可塑性类型"""
    LTP = "ltp"
    LTD = "ltd"
    STDP = "stdp"
    HEBBIAN = "hebbian"


# ============================================================
# 第十四组: 推动系统枚举
# ============================================================

class NudgeType(Enum):
    """推动类型"""
    REMINDER = "reminder"
    SUGGESTION = "suggestion"
    CORRECTION = "correction"
    ENCOURAGEMENT = "encouragement"
    WARNING = "warning"


class NudgeStatus(Enum):
    """推动状态"""
    PENDING = "pending"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


# ============================================================
# 第十五组: 技能进化枚举
# ============================================================

class SkillEvolutionStage(Enum):
    """技能进化阶段"""
    CREATION = "creation"
    REFINEMENT = "refinement"
    OPTIMIZATION = "optimization"
    GENERALIZATION = "generalization"
    RETIREMENT = "retirement"


class ExperienceType(Enum):
    """经验类型"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    LEARNED = "learned"


class SkillSource(Enum):
    """技能来源"""
    MANUAL = "manual"
    AUTO_CREATED = "auto_created"
    EVOLVED = "evolved"
    IMPORTED = "imported"
    DISTILLED = "distilled"


class SkillExecutionMode(Enum):
    """技能执行模式"""
    SYNC = "sync"
    ASYNC = "async"
    STREAMING = "streaming"
    BATCH = "batch"


class SkillActivationType(Enum):
    """技能激活类型"""
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    CONDITIONAL = "conditional"
    SCHEDULED = "scheduled"


# ============================================================
# 第十六组: 注册/缓存枚举
# ============================================================

class CacheStrategy(Enum):
    """缓存策略"""
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"
    ADAPTIVE = "adaptive"


class RegistrySource(Enum):
    """注册来源"""
    LOCAL = "local"
    REMOTE = "remote"
    DISCOVERED = "discovered"
    INJECTED = "injected"


class CommandCategory(Enum):
    """命令类别"""
    SYSTEM = "system"
    TASK = "task"
    QUERY = "query"
    CONFIGURATION = "configuration"
    MAINTENANCE = "maintenance"


# ============================================================
# 第十七组: 服务生命周期枚举
# ============================================================

class ServiceLifetime(Enum):
    """服务生命周期"""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


# ============================================================
# 第十八组: 事件类型枚举
# ============================================================

class EventType(Enum):
    """事件类型"""
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_PAUSED = "task_paused"
    TASK_RESUMED = "task_resumed"
    SKILL_CREATED = "skill_created"
    SKILL_EXECUTED = "skill_executed"
    SKILL_IMPROVED = "skill_improved"
    SKILL_DEPRECATED = "skill_deprecated"
    KNOWLEDGE_ADDED = "knowledge_added"
    LEARNING_STARTED = "learning_started"
    LEARNING_COMPLETED = "learning_completed"
    EVOLUTION_EVENT = "evolution_event"
    MILESTONE_REACHED = "milestone_reached"
    CAPABILITY_IMPROVED = "capability_improved"
    USER_INTERACTION = "user_interaction"
    USER_FEEDBACK = "user_feedback"
    USER_CORRECTION = "user_correction"
    METACOGNITION_TRIGGERED = "metacognition_triggered"
    SELF_ASSESSMENT = "self_assessment"
    REFLECTION_COMPLETED = "reflection_completed"
    SYSTEM_STARTED = "system_started"
    SYSTEM_STOPPED = "system_stopped"
    ERROR_OCCURRED = "error_occurred"
    WARNING_RAISED = "warning_raised"
    TOOL_CALLED = "tool_called"
    TOOL_COMPLETED = "tool_completed"
    TOOL_FAILED = "tool_failed"
    BROWSER_NAVIGATED = "browser_navigated"
    BROWSER_ACTION = "browser_action"
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    SYNAPTIC_MESSAGE_SENT = "synaptic_message_sent"
    SYNAPTIC_MESSAGE_RECEIVED = "synaptic_message_received"
    AGENT_ACTIVATED = "agent_activated"
    AGENT_DEACTIVATED = "agent_deactivated"
    CIRCUIT_EXECUTED = "circuit_executed"
    DECISION_TRACED = "decision_traced"


# ============================================================
# 第十九组: 流程阶段枚举
# ============================================================

class FlowPhase(Enum):
    """流程阶段"""
    PLANNING = "planning"
    EXECUTION = "execution"
    EVALUATION = "evaluation"
    REFINEMENT = "refinement"


class HistoryAction(Enum):
    """历史动作"""
    CREATED = "created"
    MODIFIED = "modified"
    ACCESSED = "accessed"
    DELETED = "deleted"


# ============================================================
# 第二十组: 测试枚举
# ============================================================

class TestType(Enum):
    """测试类型"""
    UNIT = "unit"
    INTEGRATION = "integration"
    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    REGRESSION = "regression"


class TestFramework(Enum):
    """测试框架"""
    PYTEST = "pytest"
    UNITTEST = "unittest"
    NOSE = "nose"


# ============================================================
# 第二十一组: Agent类型枚举 (新增)
# ============================================================

class AgentType(Enum):
    """Agent类型"""
    REFLEX = "reflex"
    DELIBERATIVE = "deliberative"
    LEARNING = "learning"
    COORDINATOR = "coordinator"


class AgentState(Enum):
    """Agent状态"""
    IDLE = "idle"
    ACTIVE = "active"
    PROCESSING = "processing"
    WAITING = "waiting"
    ERROR = "error"
    EVOLVING = "evolving"


# ============================================================
# 第二十二组: 突触总线枚举 (新增)
# ============================================================

class MessagePriority(Enum):
    """消息优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3
    CRITICAL = 4


class RoutingStrategy(Enum):
    """路由策略"""
    CONFIDENCE_BASED = "confidence_based"
    PRIORITY_BASED = "priority_based"
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    ADAPTIVE = "adaptive"


class DeliveryStatus(Enum):
    """投递状态"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    TIMEOUT = "timeout"
    FALLBACK = "fallback"
