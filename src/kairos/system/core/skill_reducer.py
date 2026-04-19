# -*- coding: utf-8 -*-
"""
SkillReducer 统一技能系统
基于 SkillReducer 论文 (arXiv:2603.29919) 的双阶段优化框架:
  阶段一: 路由层优化 — 描述压缩 + 缺失描述生成 + 对抗性增量调试
  阶段二: 主体重构 — 分类学分类 + 渐进式披露 + 忠实度校验 + 自纠正反馈环

统一6种技能数据结构为 UnifiedSkillDefinition，融合:
  - skill_system.py 的 SkillMetadata (注册/执行)
  - skill_auto_creator.py 的 SkillDefinition (自动创建)
  - skill_definition_parser.py 的条件激活/YAML解析
  - skill_evolution_pipeline.py 的进化闭环
  - unified_skill_system.py 的缓存/依赖/权限
"""

import os
import json
import time
import hashlib
import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from kairos.system.core.enums import (
    SkillCategory, SkillStatus, SkillLevel, SkillSource,
    SkillExecutionMode, SkillActivationType, SkillEvolutionStage,
    SkillContext
)

logger = logging.getLogger("SkillReducer")


class DisclosureLevel(Enum):
    L0_ROUTE = "l0_route"
    L1_CORE = "l1_core"
    L2_SUPPLEMENTARY = "l2_supplementary"


@dataclass
class SkillActivation:
    condition_type: str = "manual"
    pattern: str = ""
    command: str = ""
    keyword: str = ""

    def matches(self, context: str) -> bool:
        if self.condition_type == "manual":
            return False
        if self.condition_type == "keyword" and self.keyword:
            return self.keyword.lower() in context.lower()
        if self.condition_type == "command" and self.command:
            return context.strip().startswith(self.command)
        if self.condition_type == "pattern" and self.pattern:
            import re
            return bool(re.search(self.pattern, context))
        return False


@dataclass
class UnifiedSkillDefinition:
    id: str = ""
    name: str = ""
    route_description: str = ""
    category: str = SkillCategory.ANALYSIS.value
    triggers: List[str] = field(default_factory=list)
    activation: Optional[SkillActivation] = None
    core_rules: List[str] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    success_patterns: List[str] = field(default_factory=list)
    failure_patterns: List[str] = field(default_factory=list)
    supplementary: Dict[str, Any] = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)
    reference_docs: List[str] = field(default_factory=list)
    extended_description: str = ""
    source: str = SkillSource.MANUAL.value
    status: str = SkillStatus.DRAFT.value
    version: int = 1
    confidence: float = 0.5
    embedding: Optional[List[float]] = None
    execution_fn: Optional[Callable] = None
    dependencies: List[str] = field(default_factory=list)
    security_level: str = "low"
    tags: List[str] = field(default_factory=list)
    timeout: int = 30
    cache_enabled: bool = False
    cache_ttl: int = 300
    created_at: str = ""
    updated_at: str = ""
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    evolution_stage: str = SkillEvolutionStage.CREATION.value

    def __post_init__(self):
        if not self.id:
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            h = hashlib.md5(self.name.encode()).hexdigest()[:8]
            self.id = f"skill_{ts}_{h}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self, level: DisclosureLevel = DisclosureLevel.L1_CORE) -> Dict[str, Any]:
        base = {
            "id": self.id,
            "name": self.name,
            "route_description": self.route_description,
            "category": self.category,
            "status": self.status,
            "version": self.version,
            "tags": self.tags,
        }
        if level in (DisclosureLevel.L1_CORE, DisclosureLevel.L2_SUPPLEMENTARY):
            base.update({
                "core_rules": self.core_rules,
                "steps": self.steps,
                "parameters": self.parameters,
                "success_patterns": self.success_patterns,
                "failure_patterns": self.failure_patterns,
                "triggers": self.triggers,
                "source": self.source,
                "confidence": self.confidence,
                "usage_count": self.usage_count,
                "success_rate": self.success_rate,
                "evolution_stage": self.evolution_stage,
            })
        if level == DisclosureLevel.L2_SUPPLEMENTARY:
            base.update({
                "supplementary": self.supplementary,
                "examples": self.examples,
                "reference_docs": self.reference_docs,
                "extended_description": self.extended_description,
                "dependencies": self.dependencies,
                "security_level": self.security_level,
                "timeout": self.timeout,
                "cache_enabled": self.cache_enabled,
                "cache_ttl": self.cache_ttl,
            })
        return base

    def to_route_context(self) -> str:
        parts = [f"技能: {self.name}"]
        if self.route_description:
            parts.append(self.route_description)
        if self.triggers:
            parts.append(f"触发: {', '.join(self.triggers[:3])}")
        return "\n".join(parts)

    def to_core_context(self) -> str:
        parts = [self.to_route_context()]
        if self.core_rules:
            parts.append("核心规则:")
            for rule in self.core_rules:
                parts.append(f"  - {rule}")
        if self.steps:
            parts.append("执行步骤:")
            for i, step in enumerate(self.steps, 1):
                action = step.get("action", "")
                desc = step.get("description", "")
                parts.append(f"  {i}. {action}: {desc}")
        return "\n".join(parts)

    def to_full_context(self) -> str:
        parts = [self.to_core_context()]
        if self.examples:
            parts.append("示例:")
            for ex in self.examples[:2]:
                parts.append(f"  - {ex}")
        if self.extended_description:
            parts.append(f"详细说明: {self.extended_description}")
        return "\n".join(parts)

    def update_usage_stats(self, success: bool, execution_time: float = 0):
        self.usage_count += 1
        self.updated_at = datetime.now().isoformat()
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        if self.usage_count > 0:
            self.success_rate = self.success_count / self.usage_count

    def to_save_dict(self) -> Dict[str, Any]:
        d = self.to_dict(DisclosureLevel.L2_SUPPLEMENTARY)
        d["activation"] = {
            "condition_type": self.activation.condition_type,
            "pattern": self.activation.pattern,
            "command": self.activation.command,
            "keyword": self.activation.keyword,
        } if self.activation else None
        d["created_at"] = self.created_at
        d["updated_at"] = self.updated_at
        d["usage_count"] = self.usage_count
        d["success_count"] = self.success_count
        d["failure_count"] = self.failure_count
        d["success_rate"] = self.success_rate
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UnifiedSkillDefinition":
        act_data = data.pop("activation", None)
        activation = None
        if act_data and isinstance(act_data, dict):
            activation = SkillActivation(**act_data)
        return cls(activation=activation, **data)


class SkillCache:
    def __init__(self, default_ttl: int = 300, max_size: int = 100):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            value, expire_at = self._cache[key]
            if time.time() < expire_at:
                self._hits += 1
                return value
            del self._cache[key]
        self._misses += 1
        return None

    def set(self, key: str, value: Any, ttl: int = None):
        if len(self._cache) >= self._max_size:
            oldest = min(self._cache, key=lambda k: self._cache[k][1])
            del self._cache[oldest]
        self._cache[key] = (value, time.time() + (ttl or self._default_ttl))

    def invalidate(self, key: str):
        self._cache.pop(key, None)

    def clear(self):
        self._cache.clear()

    @property
    def stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
        }


class SkillDependencyResolver:
    def __init__(self):
        self._graph: Dict[str, List[str]] = defaultdict(list)

    def add_dependency(self, skill_id: str, depends_on: str):
        if depends_on not in self._graph[skill_id]:
            self._graph[skill_id].append(depends_on)

    def resolve_order(self, skill_ids: List[str]) -> List[str]:
        visited = set()
        order = []
        visiting = set()

        def visit(sid: str):
            if sid in visited:
                return
            if sid in visiting:
                raise ValueError(f"循环依赖: {sid}")
            visiting.add(sid)
            for dep in self._graph.get(sid, []):
                if dep in skill_ids:
                    visit(dep)
            visiting.discard(sid)
            visited.add(sid)
            order.append(sid)

        for sid in skill_ids:
            visit(sid)
        return order

    def get_dependencies(self, skill_id: str) -> List[str]:
        return list(self._graph.get(skill_id, []))


class RouteOptimizer:
    def __init__(self, embedding_fn: Optional[Callable] = None):
        self._embedding_fn = embedding_fn
        self._route_embeddings: Dict[str, List[float]] = {}

    async def compress_description(self, description: str,
                                    max_ratio: float = 0.52) -> str:
        if not description or len(description) < 20:
            return description
        sentences = self._split_sentences(description)
        current = description
        for sent in sentences:
            if len(current) / max(len(description), 1) <= max_ratio:
                break
            candidate = current.replace(sent, "").strip()
            candidate = " ".join(candidate.split())
            if len(candidate) >= 10:
                current = candidate
        return current

    async def generate_route_description(self, skill: UnifiedSkillDefinition) -> str:
        try:
            from kairos.system.core.llm_wiki_compat import ollama_generate
            prompt = (
                f"为以下技能生成简洁的路由描述(不超过50字)，只保留核心行动指令:\n"
                f"名称: {skill.name}\n"
                f"核心规则: {skill.core_rules}\n"
                f"步骤: {[s.get('action','') for s in skill.steps]}"
            )
            result = await ollama_generate(prompt)
            return result.strip()[:100] if result else skill.name
        except Exception as e:
            logger.debug(f"生成路由描述失败: {e}")
            return skill.name

    async def semantic_match(self, query: str,
                              skills: Dict[str, UnifiedSkillDefinition],
                              top_k: int = 3) -> List[Tuple[float, UnifiedSkillDefinition]]:
        if not self._embedding_fn:
            return self._keyword_match(query, skills, top_k)
        try:
            q_emb = self._embedding_fn(query)
            if asyncio.iscoroutine(q_emb):
                q_emb = await q_emb
        except Exception:
            return self._keyword_match(query, skills, top_k)

        candidates = []
        for sid, skill in skills.items():
            if skill.status not in (SkillStatus.ACTIVE.value, SkillStatus.DRAFT.value):
                continue
            if skill.embedding is None:
                try:
                    emb = self._embedding_fn(skill.route_description or skill.name)
                    if asyncio.iscoroutine(emb):
                        emb = await emb
                    skill.embedding = emb
                except Exception:
                    continue
            if skill.embedding:
                sim = self._cosine_similarity(q_emb, skill.embedding)
                candidates.append((sim, skill))

        candidates.sort(key=lambda x: -x[0])
        return candidates[:top_k]

    def _keyword_match(self, query: str,
                        skills: Dict[str, UnifiedSkillDefinition],
                        top_k: int) -> List[Tuple[float, UnifiedSkillDefinition]]:
        q_lower = query.lower()
        candidates = []
        for sid, skill in skills.items():
            if skill.status not in (SkillStatus.ACTIVE.value, SkillStatus.DRAFT.value):
                continue
            score = 0.0
            for trigger in skill.triggers:
                if trigger.lower() in q_lower:
                    score += 1.0
            for tag in skill.tags:
                if tag.lower() in q_lower:
                    score += 0.5
            if skill.route_description and skill.route_description.lower() in q_lower:
                score += 0.8
            score *= (0.5 + skill.success_rate * 0.5)
            if score > 0:
                candidates.append((score, skill))
        candidates.sort(key=lambda x: -x[0])
        return candidates[:top_k]

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        import re
        parts = re.split(r'[。.！!？?；;\n]', text)
        return [p.strip() for p in parts if len(p.strip()) > 3]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)


class AdversarialDeltaDebugger:
    """对抗性增量调试器 — SkillReducer阶段一核心组件
    
    逐步删除描述中的句子/片段，每次删除后验证匹配结果是否保持不变。
    找到最小充分描述(最少Token但匹配结果不变)。
    """

    def __init__(self, route_optimizer: RouteOptimizer, max_iterations: int = 10):
        self._optimizer = route_optimizer
        self._max_iterations = max_iterations

    async def debug_compress(self, skill: UnifiedSkillDefinition,
                              test_queries: List[str],
                              skills_registry: Dict[str, UnifiedSkillDefinition]) -> Dict[str, Any]:
        original_desc = skill.route_description or skill.extended_description or skill.name
        if not original_desc or len(original_desc) < 20:
            return {"status": "skipped", "reason": "描述过短"}

        original_matches = {}
        for q in test_queries:
            matches = await self._optimizer.semantic_match(q, skills_registry, top_k=3)
            original_matches[q] = [s.id for _, s in matches]

        current_desc = original_desc
        sentences = self._split_into_fragments(current_desc)
        removed = []

        for sent in sentences:
            if len(current_desc) < 15:
                break
            candidate = current_desc.replace(sent, "").strip()
            candidate = " ".join(candidate.split())
            if len(candidate) < 10:
                continue

            skill.route_description = candidate
            preserved = True
            for q in test_queries:
                matches = await self._optimizer.semantic_match(q, skills_registry, top_k=3)
                new_ids = [s.id for _, s in matches]
                if skill.id in original_matches.get(q, []) and skill.id not in new_ids:
                    preserved = False
                    break
                if skill.id not in original_matches.get(q, []) and skill.id in new_ids:
                    pass

            if preserved:
                removed.append(sent)
                current_desc = candidate
            else:
                skill.route_description = current_desc

        skill.route_description = current_desc
        compression = 1.0 - (len(current_desc) / max(len(original_desc), 1))
        return {
            "status": "success",
            "original_length": len(original_desc),
            "compressed_length": len(current_desc),
            "compression_ratio": round(compression, 3),
            "fragments_removed": len(removed),
        }

    @staticmethod
    def _split_into_fragments(text: str) -> List[str]:
        import re
        fragments = []
        for sent in re.split(r'[。.！!？?；;\n]', text):
            sent = sent.strip()
            if len(sent) > 3:
                fragments.append(sent)
        for clause in re.split(r'[，,、：:]', text):
            clause = clause.strip()
            if 3 < len(clause) < len(text) and clause not in fragments:
                fragments.append(clause)
        return fragments


class TokenEstimator:
    """Token估算器 — 评估渐进式披露的Token效率"""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        if not text:
            return 0
        cn_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        en_words = len(text.split()) - cn_chars
        return int(cn_chars * 1.5 + en_words * 1.3)

    @staticmethod
    def estimate_skill_tokens(skill: UnifiedSkillDefinition,
                               level: DisclosureLevel) -> int:
        if level == DisclosureLevel.L0_ROUTE:
            return TokenEstimator.estimate_tokens(skill.to_route_context())
        elif level == DisclosureLevel.L1_CORE:
            return TokenEstimator.estimate_tokens(skill.to_core_context())
        else:
            return TokenEstimator.estimate_tokens(skill.to_full_context())

    @staticmethod
    def compare_disclosure_levels(skill: UnifiedSkillDefinition) -> Dict[str, Any]:
        l0 = TokenEstimator.estimate_skill_tokens(skill, DisclosureLevel.L0_ROUTE)
        l1 = TokenEstimator.estimate_skill_tokens(skill, DisclosureLevel.L1_CORE)
        l2 = TokenEstimator.estimate_skill_tokens(skill, DisclosureLevel.L2_SUPPLEMENTARY)
        return {
            "l0_route_tokens": l0,
            "l1_core_tokens": l1,
            "l2_supplementary_tokens": l2,
            "savings_l1_vs_l2": round(1 - l1 / max(l2, 1), 3),
            "savings_l0_vs_l2": round(1 - l0 / max(l2, 1), 3),
        }


class BodyRestructurer:
    async def classify_content(self, skill_body: str) -> Tuple[List[str], Dict[str, Any]]:
        if not skill_body:
            return [], {}
        try:
            from kairos.system.core.llm_wiki_compat import ollama_generate
            prompt = (
                f"将以下技能内容分类为核心规则(必须的行动指令)和补充内容(示例/解释/边缘情况)。\n"
                f"输出JSON: {{\"core_rules\": [\"规则1\", ...], \"supplementary\": {{\"examples\": [...], \"notes\": [...]}}}}\n\n"
                f"技能内容:\n{skill_body[:2000]}"
            )
            result = await ollama_generate(prompt)
            if result:
                import re
                m = re.search(r'\{[\s\S]*\}', result)
                if m:
                    data = json.loads(m.group())
                    return data.get("core_rules", []), data.get("supplementary", {})
        except Exception as e:
            logger.debug(f"分类学分类失败: {e}")
        return [skill_body[:200]], {}

    async def verify_faithfulness(self, original: UnifiedSkillDefinition,
                                   compressed: UnifiedSkillDefinition) -> bool:
        if original.core_rules and not compressed.core_rules:
            return False
        if len(original.steps) > 0 and len(compressed.steps) == 0:
            return False
        if original.success_patterns and not compressed.success_patterns:
            return False
        return True

    async def restructure(self, skill: UnifiedSkillDefinition,
                           max_retries: int = 2) -> UnifiedSkillDefinition:
        body_text = "\n".join(skill.core_rules + [s.get("description", "") for s in skill.steps])
        if not body_text:
            return skill
        original_rules = list(skill.core_rules)
        original_steps = list(skill.steps)
        for attempt in range(max_retries + 1):
            core_rules, supplementary = await self.classify_content(body_text)
            if core_rules:
                skill.core_rules = core_rules
            if supplementary:
                existing = skill.supplementary or {}
                existing.update(supplementary)
                skill.supplementary = existing
            if skill.extended_description and not skill.route_description:
                skill.route_description = skill.extended_description[:100]
            temp_skill = UnifiedSkillDefinition(
                name=skill.name, core_rules=skill.core_rules,
                steps=skill.steps, success_patterns=skill.success_patterns
            )
            original_skill = UnifiedSkillDefinition(
                name=skill.name, core_rules=original_rules,
                steps=original_steps, success_patterns=skill.success_patterns
            )
            faithful = await self.verify_faithfulness(original_skill, temp_skill)
            if faithful:
                break
            else:
                logger.debug(f"忠实度校验失败(尝试{attempt+1})，回退并重试")
                skill.core_rules = original_rules
                skill.steps = original_steps
                if attempt == max_retries - 1:
                    break
        return skill


class UnifiedSkillSystem:
    def __init__(self, skills_dir: str = "./data/skills",
                 embedding_fn: Optional[Callable] = None,
                 max_workers: int = 3):
        self.skills_dir = skills_dir
        self._skills: Dict[str, UnifiedSkillDefinition] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._cache = SkillCache(default_ttl=300, max_size=50)
        self._dep_resolver = SkillDependencyResolver()
        self._route_optimizer = RouteOptimizer(embedding_fn)
        self._body_restructurer = BodyRestructurer()
        self._delta_debugger = AdversarialDeltaDebugger(self._route_optimizer)
        self._token_estimator = TokenEstimator()
        self._stats = {
            "registered": 0,
            "executed": 0,
            "cache_hits": 0,
            "route_optimizations": 0,
            "body_restructures": 0,
            "delta_debug_runs": 0,
            "tokens_saved": 0,
        }
        os.makedirs(skills_dir, exist_ok=True)
        self._load_skills()

    def _load_skills(self):
        try:
            for fn in os.listdir(self.skills_dir):
                if fn.endswith(".json"):
                    fp = os.path.join(self.skills_dir, fn)
                    with open(fp, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    skill = UnifiedSkillDefinition.from_dict(data)
                    self._skills[skill.id] = skill
            logger.info(f"已加载 {len(self._skills)} 个统一技能")
        except Exception as e:
            logger.error(f"加载技能失败: {e}")

    def _save_skill(self, skill: UnifiedSkillDefinition):
        try:
            fp = os.path.join(self.skills_dir, f"{skill.id}.json")
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(skill.to_save_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存技能失败: {e}")

    def register_skill(self, skill: UnifiedSkillDefinition) -> Dict[str, Any]:
        if skill.id in self._skills:
            return {"status": "error", "error": f"技能已存在: {skill.id}"}
        if skill.status == SkillStatus.DRAFT.value:
            skill.status = SkillStatus.ACTIVE.value
        self._skills[skill.id] = skill
        self._save_skill(skill)
        self._stats["registered"] += 1
        self._cache.invalidate(skill.id)
        logger.info(f"技能已注册: {skill.id} ({skill.name})")
        return {"status": "success", "skill_id": skill.id}

    def register_callable(self, name: str, function: Callable,
                           description: str = "", category: str = SkillCategory.ANALYSIS.value,
                           **kwargs) -> Dict[str, Any]:
        skill = UnifiedSkillDefinition(
            name=name,
            route_description=description[:100] if description else name,
            category=category,
            execution_fn=function,
            source=SkillSource.MANUAL.value,
            status=SkillStatus.ACTIVE.value,
            **kwargs
        )
        return self.register_skill(skill)

    async def execute_skill(self, skill_id: str,
                             parameters: Optional[Dict[str, Any]] = None,
                             disclosure_level: DisclosureLevel = DisclosureLevel.L1_CORE,
                             user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if skill_id not in self._skills:
            return {"status": "error", "error": f"技能不存在: {skill_id}"}
        skill = self._skills[skill_id]
        if skill.cache_enabled:
            cache_key = f"{skill_id}:{hashlib.md5(json.dumps(parameters or {}).encode()).hexdigest()}"
            cached = self._cache.get(cache_key)
            if cached is not None:
                self._stats["cache_hits"] += 1
                return cached
        start_time = time.time()
        try:
            if skill.execution_fn:
                if asyncio.iscoroutinefunction(skill.execution_fn):
                    result = await asyncio.wait_for(
                        skill.execution_fn(**(parameters or {})),
                        timeout=skill.timeout
                    )
                else:
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(
                            self._executor,
                            lambda: skill.execution_fn(**(parameters or {}))
                        ),
                        timeout=skill.timeout
                    )
            else:
                result = await self._execute_via_llm(skill, parameters, disclosure_level)
            exec_time = time.time() - start_time
            skill.update_usage_stats(True, exec_time)
            self._stats["executed"] += 1
            self._save_skill(skill)
            response = {"status": "success", "result": result, "execution_time": exec_time}
            if skill.cache_enabled:
                self._cache.set(cache_key, response, skill.cache_ttl)
            return response
        except asyncio.TimeoutError:
            skill.update_usage_stats(False, skill.timeout)
            return {"status": "error", "error": f"超时 ({skill.timeout}s)"}
        except Exception as e:
            skill.update_usage_stats(False, 0)
            logger.error(f"执行技能失败: {e}")
            return {"status": "error", "error": str(e)}

    async def _execute_via_llm(self, skill: UnifiedSkillDefinition,
                                parameters: Optional[Dict[str, Any]],
                                level: DisclosureLevel) -> Any:
        try:
            from kairos.system.core.llm_wiki_compat import ollama_generate
            if level == DisclosureLevel.L0_ROUTE:
                context = skill.to_route_context()
            elif level == DisclosureLevel.L1_CORE:
                context = skill.to_core_context()
            else:
                context = skill.to_full_context()
            params_str = json.dumps(parameters or {}, ensure_ascii=False)
            prompt = f"{context}\n\n参数: {params_str}\n\n请执行上述技能:"
            return await ollama_generate(prompt)
        except Exception as e:
            logger.error(f"LLM执行技能失败: {e}")
            return None

    async def find_skill(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        matches = await self._route_optimizer.semantic_match(query, self._skills, top_k)
        results = []
        for score, skill in matches:
            results.append({
                "id": skill.id,
                "name": skill.name,
                "route_description": skill.route_description,
                "match_score": round(score, 3),
                "success_rate": skill.success_rate,
            })
        return results

    async def optimize_route(self, skill_id: str) -> Dict[str, Any]:
        if skill_id not in self._skills:
            return {"status": "error", "error": f"技能不存在: {skill_id}"}
        skill = self._skills[skill_id]
        original_desc = skill.route_description or skill.extended_description or skill.name
        if not skill.route_description:
            skill.route_description = await self._route_optimizer.generate_route_description(skill)
        else:
            compressed = await self._route_optimizer.compress_description(original_desc)
            if compressed and len(compressed) < len(original_desc):
                skill.route_description = compressed
        skill.updated_at = datetime.now().isoformat()
        self._save_skill(skill)
        self._stats["route_optimizations"] += 1
        return {
            "status": "success",
            "skill_id": skill_id,
            "original_length": len(original_desc),
            "optimized_length": len(skill.route_description),
            "compression_ratio": round(len(skill.route_description) / max(len(original_desc), 1), 2),
        }

    async def restructure_body(self, skill_id: str) -> Dict[str, Any]:
        if skill_id not in self._skills:
            return {"status": "error", "error": f"技能不存在: {skill_id}"}
        skill = self._skills[skill_id]
        original_rules_count = len(skill.core_rules)
        skill = await self._body_restructurer.restructure(skill)
        skill.evolution_stage = SkillEvolutionStage.REFINEMENT.value
        skill.version += 1
        skill.updated_at = datetime.now().isoformat()
        self._save_skill(skill)
        self._stats["body_restructures"] += 1
        return {
            "status": "success",
            "skill_id": skill_id,
            "original_rules_count": original_rules_count,
            "restructured_rules_count": len(skill.core_rules),
            "has_supplementary": bool(skill.supplementary),
        }

    async def delta_debug_compress(self, skill_id: str,
                                    test_queries: List[str]) -> Dict[str, Any]:
        if skill_id not in self._skills:
            return {"status": "error", "error": f"技能不存在: {skill_id}"}
        skill = self._skills[skill_id]
        original_len = len(skill.route_description or "")
        result = await self._delta_debugger.debug_compress(
            skill, test_queries, self._skills
        )
        skill.updated_at = datetime.now().isoformat()
        self._save_skill(skill)
        self._stats["delta_debug_runs"] += 1
        if result.get("compression_ratio", 0) > 0:
            saved = original_len - len(skill.route_description or "")
            self._stats["tokens_saved"] += int(saved * 1.5)
        return result

    async def batch_optimize_routes(self, skill_ids: List[str] = None) -> Dict[str, Any]:
        targets = skill_ids or list(self._skills.keys())
        results = {"total": len(targets), "optimized": 0, "skipped": 0, "details": []}
        for sid in targets:
            if sid not in self._skills:
                results["skipped"] += 1
                continue
            skill = self._skills[sid]
            if not skill.route_description:
                desc = await self._route_optimizer.generate_route_description(skill)
                skill.route_description = desc
                self._save_skill(skill)
                results["optimized"] += 1
                results["details"].append({"skill_id": sid, "action": "generated"})
            else:
                r = await self.optimize_route(sid)
                if r.get("compression_ratio", 1.0) < 1.0:
                    results["optimized"] += 1
                    results["details"].append({"skill_id": sid, "action": "compressed", **r})
                else:
                    results["skipped"] += 1
        return results

    async def batch_restructure_bodies(self, skill_ids: List[str] = None) -> Dict[str, Any]:
        targets = skill_ids or list(self._skills.keys())
        results = {"total": len(targets), "restructured": 0, "skipped": 0, "details": []}
        for sid in targets:
            if sid not in self._skills:
                results["skipped"] += 1
                continue
            skill = self._skills[sid]
            if not skill.core_rules and not skill.steps:
                results["skipped"] += 1
                continue
            r = await self.restructure_body(sid)
            if r.get("status") == "success":
                results["restructured"] += 1
                results["details"].append(r)
            else:
                results["skipped"] += 1
        return results

    def estimate_skill_tokens(self, skill_id: str) -> Dict[str, Any]:
        if skill_id not in self._skills:
            return {"status": "error", "error": f"技能不存在: {skill_id}"}
        skill = self._skills[skill_id]
        return TokenEstimator.compare_disclosure_levels(skill)

    def get_token_savings_report(self) -> Dict[str, Any]:
        total_l0 = 0
        total_l1 = 0
        total_l2 = 0
        for skill in self._skills.values():
            total_l0 += TokenEstimator.estimate_skill_tokens(skill, DisclosureLevel.L0_ROUTE)
            total_l1 += TokenEstimator.estimate_skill_tokens(skill, DisclosureLevel.L1_CORE)
            total_l2 += TokenEstimator.estimate_skill_tokens(skill, DisclosureLevel.L2_SUPPLEMENTARY)
        return {
            "total_skills": len(self._skills),
            "tokens_l0_route": total_l0,
            "tokens_l1_core": total_l1,
            "tokens_l2_supplementary": total_l2,
            "savings_l1_vs_l2": round(1 - total_l1 / max(total_l2, 1), 3),
            "savings_l0_vs_l2": round(1 - total_l0 / max(total_l2, 1), 3),
            "cumulative_tokens_saved": self._stats.get("tokens_saved", 0),
        }

    def get_skill(self, skill_id: str, level: DisclosureLevel = DisclosureLevel.L1_CORE) -> Optional[Dict[str, Any]]:
        skill = self._skills.get(skill_id)
        if not skill:
            return None
        return skill.to_dict(level)

    def list_skills(self, category: str = None, status: str = None,
                     tag: str = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        skills = list(self._skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        if status:
            skills = [s for s in skills if s.status == status]
        if tag:
            skills = [s for s in skills if tag in s.tags]
        skills.sort(key=lambda s: -s.usage_count)
        return [s.to_dict(DisclosureLevel.L0_ROUTE) for s in skills[offset:offset + limit]]

    def delete_skill(self, skill_id: str) -> Dict[str, Any]:
        skill = self._skills.get(skill_id)
        if not skill:
            return {"status": "error", "error": f"技能不存在: {skill_id}"}
        skill.status = SkillStatus.ARCHIVED.value
        skill.updated_at = datetime.now().isoformat()
        self._save_skill(skill)
        del self._skills[skill_id]
        self._cache.invalidate(skill_id)
        return {"status": "success", "skill_id": skill_id}

    def get_statistics(self) -> Dict[str, Any]:
        by_category = defaultdict(int)
        by_status = defaultdict(int)
        by_source = defaultdict(int)
        for s in self._skills.values():
            by_category[s.category] += 1
            by_status[s.status] += 1
            by_source[s.source] += 1
        return {
            "total_skills": len(self._skills),
            "by_category": dict(by_category),
            "by_status": dict(by_status),
            "by_source": dict(by_source),
            "cache": self._cache.stats,
            "operations": self._stats,
        }

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "skills_count": len(self._skills),
            "cache_stats": self._cache.stats,
            "operations": self._stats,
        }

    def shutdown(self):
        self._executor.shutdown(wait=True)
        self._cache.clear()


_unified_skill_system: Optional[UnifiedSkillSystem] = None


def get_unified_skill_system(**kwargs) -> UnifiedSkillSystem:
    global _unified_skill_system
    if _unified_skill_system is None:
        _unified_skill_system = UnifiedSkillSystem(**kwargs)
    return _unified_skill_system
