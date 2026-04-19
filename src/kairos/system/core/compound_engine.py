# -*- coding: utf-8 -*-
"""
复利引擎 (Compound Interest Engine)

基于"摄取-消化-输出-迭代"复利闭环方法论，将每次开发经验沉淀为可复用资产，
实现系统自动化能力的指数级增长。

四阶段复利闭环:
- 摄取(Ingest): 代码资产+错误日志+技术文档+工具链配置的自动采集
- 消化(Digest): 知识原子化+关联图谱+经验提炼+模式抽象
- 输出(Output): 代码模板+技能封装+规范生成+自动化脚本
- 迭代(Iterate): 需求驱动+问题驱动+工具链迭代+资产淘汰

与项目现有模块的映射:
- 摄取 → LearningModule(多源采集) + BackgroundService(定时触发) + TaskAutomation(数据采集)
- 消化 → KnowledgeDistillation(蒸馏流水线) + UnifiedStorage(统一存储)
- 输出 → SkillAutoCreator(技能生成) + SkillSystem(技能注册) + AutonomousEngine(OTAC执行)
- 迭代 → DualLoopEngine(双循环) + EvolutionTracker(进化追踪) + SelfEvolutionEngine(自我进化)

复利公式: Value(n) = Value(0) × (1 + r)^n
其中 r = 每次循环的知识增量率，n = 循环次数
"""

import time
import json
import os
import logging
import hashlib
import asyncio
import threading
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger("CompoundInterestEngine")


class CompoundPhase(Enum):
    INGEST = "ingest"
    DIGEST = "digest"
    OUTPUT = "output"
    ITERATE = "iterate"


class AssetType(Enum):
    CODE_MODULE = "code_module"
    ERROR_SOLUTION = "error_solution"
    ARCHITECTURE_PATTERN = "architecture_pattern"
    DEBUG_TECHNIQUE = "debug_technique"
    TOOL_CONFIG = "tool_config"
    CODE_TEMPLATE = "code_template"
    SKILL_DEFINITION = "skill_definition"
    DEVELOPMENT_SPEC = "development_spec"
    AUTOMATION_SCRIPT = "automation_script"


class AssetStatus(Enum):
    RAW = "raw"
    ATOMIZED = "atomized"
    STRUCTURED = "structured"
    VALIDATED = "validated"
    DEPLOYED = "deployed"
    DEPRECATED = "deprecated"


@dataclass
class KnowledgeAsset:
    id: str
    asset_type: AssetType
    phase: CompoundPhase
    status: AssetStatus
    content: str
    title: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    confidence: float = 0.5
    reuse_count: int = 0
    compound_value: float = 1.0
    parent_ids: List[str] = field(default_factory=list)
    child_ids: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "asset_type": self.asset_type.value,
            "phase": self.phase.value,
            "status": self.status.value,
            "content": self.content,
            "title": self.title,
            "tags": self.tags,
            "metadata": self.metadata,
            "source": self.source,
            "confidence": self.confidence,
            "reuse_count": self.reuse_count,
            "compound_value": self.compound_value,
            "parent_ids": self.parent_ids,
            "child_ids": self.child_ids,
            "created_at": self.created_at,
            "last_used_at": self.last_used_at
        }

    def apply_compound(self, rate: float = 0.1):
        self.compound_value *= (1 + rate)
        self.reuse_count += 1
        self.last_used_at = time.time()


class IngestPipeline:
    """
    摄取层: 全面捕获开发场景的"原料"

    数据源:
    - 代码资产: 任务执行记录、技能调用日志
    - 错误与解决方案: 执行失败记录、异常堆栈
    - 技术文档: 学习模块采集的知识
    - 工具链配置: 系统配置、环境信息
    """

    def __init__(self, core_ref=None):
        self.core = core_ref
        self._collected_assets: List[KnowledgeAsset] = []
        self._stats = {"code_collected": 0, "errors_collected": 0,
                       "docs_collected": 0, "configs_collected": 0}

    async def collect_from_execution(self, task_desc: str, actions: List[Dict],
                                      result: Dict[str, Any]) -> List[KnowledgeAsset]:
        assets = []
        task_id = hashlib.sha256(f"exec_{task_desc}_{time.time()}".encode()).hexdigest()[:16]
        asset = KnowledgeAsset(
            id=task_id, asset_type=AssetType.CODE_MODULE,
            phase=CompoundPhase.INGEST, status=AssetStatus.RAW,
            content=json.dumps({"task": task_desc, "actions": actions, "result": result},
                               ensure_ascii=False),
            title=f"执行记录: {task_desc[:50]}",
            tags=["execution", "auto_collected"],
            source="autonomous_engine",
            confidence=0.7 if result.get("success") else 0.3,
            metadata={"success": result.get("success", False)}
        )
        assets.append(asset)
        self._stats["code_collected"] += 1

        if not result.get("success", False):
            error_id = hashlib.sha256(f"err_{task_desc}_{time.time()}".encode()).hexdigest()[:16]
            error_asset = KnowledgeAsset(
                id=error_id, asset_type=AssetType.ERROR_SOLUTION,
                phase=CompoundPhase.INGEST, status=AssetStatus.RAW,
                content=json.dumps({
                    "problem": task_desc,
                    "error": result.get("error", "未知错误"),
                    "context": actions
                }, ensure_ascii=False),
                title=f"错误记录: {task_desc[:50]}",
                tags=["error", "auto_collected"],
                source="autonomous_engine",
                confidence=0.2,
                metadata={"resolved": False}
            )
            assets.append(error_asset)
            self._stats["errors_collected"] += 1

        self._collected_assets.extend(assets)
        return assets

    async def collect_from_learning(self, topic: str, insights: List[Dict]) -> List[KnowledgeAsset]:
        assets = []
        for insight in insights:
            doc_id = hashlib.sha256(f"doc_{insight.get('title', '')}_{time.time()}".encode()).hexdigest()[:16]
            asset = KnowledgeAsset(
                id=doc_id, asset_type=AssetType.ARCHITECTURE_PATTERN,
                phase=CompoundPhase.INGEST, status=AssetStatus.RAW,
                content=json.dumps(insight, ensure_ascii=False),
                title=insight.get("title", f"学习: {topic}"),
                tags=["learning", topic, "auto_collected"],
                source="learning_module",
                confidence=insight.get("confidence", 0.5)
            )
            assets.append(asset)
        self._stats["docs_collected"] += len(assets)
        self._collected_assets.extend(assets)
        return assets

    async def collect_from_error(self, error_type: str, error_msg: str,
                                  solution: str = "", context: Dict = None) -> KnowledgeAsset:
        err_id = hashlib.sha256(f"err_{error_type}_{time.time()}".encode()).hexdigest()[:16]
        asset = KnowledgeAsset(
            id=err_id, asset_type=AssetType.ERROR_SOLUTION,
            phase=CompoundPhase.INGEST, status=AssetStatus.RAW,
            content=json.dumps({
                "problem": error_msg,
                "error_type": error_type,
                "solution": solution,
                "context": context or {}
            }, ensure_ascii=False),
            title=f"错误: {error_type}",
            tags=["error", error_type, "auto_collected"],
            source="error_handler",
            confidence=0.8 if solution else 0.2,
            metadata={"resolved": bool(solution)}
        )
        self._stats["errors_collected"] += 1
        self._collected_assets.append(asset)
        return asset

    async def collect_config(self, config_type: str, config_data: Dict) -> KnowledgeAsset:
        cfg_id = hashlib.sha256(f"cfg_{config_type}_{time.time()}".encode()).hexdigest()[:16]
        asset = KnowledgeAsset(
            id=cfg_id, asset_type=AssetType.TOOL_CONFIG,
            phase=CompoundPhase.INGEST, status=AssetStatus.RAW,
            content=json.dumps(config_data, ensure_ascii=False),
            title=f"配置: {config_type}",
            tags=["config", config_type, "auto_collected"],
            source="system_config",
            confidence=0.9
        )
        self._stats["configs_collected"] += 1
        self._collected_assets.append(asset)
        return asset

    def get_pending_assets(self) -> List[KnowledgeAsset]:
        return [a for a in self._collected_assets if a.status == AssetStatus.RAW]

    def drain_assets(self) -> List[KnowledgeAsset]:
        assets = self._collected_assets[:]
        self._collected_assets.clear()
        return assets

    def get_stats(self) -> Dict[str, Any]:
        return {**self._stats, "pending_count": len(self._collected_assets)}


class DigestPipeline:
    """
    消化层: 把"原料"炼成可复用的"知识原子"

    处理步骤:
    - 代码模块拆解: 标注输入-输出-依赖
    - 架构模式抽象: 提炼场景-优势-局限
    - 调试经验提炼: 转化为可执行Checklist
    - 知识关联构建: 建立知识图谱连接
    """

    def __init__(self, core_ref=None):
        self.core = core_ref
        self._atomized_assets: Dict[str, KnowledgeAsset] = {}
        self._relation_graph: Dict[str, Set[str]] = defaultdict(set)
        self._stats = {"atomized": 0, "patterns_found": 0,
                       "relations_built": 0, "checklists_created": 0}

    async def atomize(self, assets: List[KnowledgeAsset]) -> List[KnowledgeAsset]:
        results = []
        for asset in assets:
            atomized = await self._atomize_single(asset)
            if atomized:
                results.append(atomized)
                self._atomized_assets[atomized.id] = atomized
        self._stats["atomized"] += len(results)
        await self._build_relations(results)
        return results

    async def _atomize_single(self, asset: KnowledgeAsset) -> Optional[KnowledgeAsset]:
        try:
            content_data = json.loads(asset.content) if isinstance(asset.content, str) else asset.content
        except (json.JSONDecodeError, TypeError):
            content_data = {"raw": asset.content}

        if asset.asset_type == AssetType.CODE_MODULE:
            atomized = self._atomize_code_module(asset, content_data)
        elif asset.asset_type == AssetType.ERROR_SOLUTION:
            atomized = self._atomize_error_solution(asset, content_data)
        elif asset.asset_type == AssetType.ARCHITECTURE_PATTERN:
            atomized = self._atomize_pattern(asset, content_data)
        elif asset.asset_type == AssetType.TOOL_CONFIG:
            atomized = self._atomize_config(asset, content_data)
        else:
            atomized = asset
            atomized.status = AssetStatus.ATOMIZED

        return atomized

    def _atomize_code_module(self, asset: KnowledgeAsset,
                              content_data: Dict) -> KnowledgeAsset:
        task = content_data.get("task", "")
        actions = content_data.get("actions", [])
        result = content_data.get("result", {})

        inputs = []
        outputs = []
        dependencies = []
        for action in actions:
            tool = action.get("tool", action.get("name", "unknown"))
            dependencies.append(tool)
            if "input" in action or "parameters" in action:
                inputs.append({"tool": tool, "params": action.get("parameters", {})})
            if "output" in action or "result" in action:
                outputs.append({"tool": tool, "result": action.get("result", {})})

        asset.metadata.update({
            "inputs": inputs,
            "outputs": outputs,
            "dependencies": dependencies,
            "success": result.get("success", False)
        })
        asset.status = AssetStatus.ATOMIZED
        asset.tags.extend(["atomized", "code_module"])
        if task:
            for word in task.split()[:5]:
                if len(word) > 2:
                    asset.tags.append(word.lower())
        return asset

    def _atomize_error_solution(self, asset: KnowledgeAsset,
                                 content_data: Dict) -> KnowledgeAsset:
        problem = content_data.get("problem", "")
        error_type = content_data.get("error_type", "unknown")
        solution = content_data.get("solution", "")

        asset.metadata.update({
            "problem_summary": problem[:200] if problem else "",
            "error_type": error_type,
            "has_solution": bool(solution),
            "triple": {
                "problem": problem,
                "cause": error_type,
                "solution": solution or "待解决"
            }
        })
        asset.status = AssetStatus.ATOMIZED
        asset.tags.extend(["atomized", "error_solution", error_type])
        if solution:
            asset.confidence = min(asset.confidence + 0.3, 1.0)
            self._stats["checklists_created"] += 1
        return asset

    def _atomize_pattern(self, asset: KnowledgeAsset,
                          content_data: Dict) -> KnowledgeAsset:
        asset.metadata.update({
            "scenario": content_data.get("scenario", ""),
            "advantages": content_data.get("advantages", []),
            "limitations": content_data.get("limitations", []),
            "pattern_type": content_data.get("pattern_type", "unknown")
        })
        asset.status = AssetStatus.ATOMIZED
        asset.tags.extend(["atomized", "pattern"])
        self._stats["patterns_found"] += 1
        return asset

    def _atomize_config(self, asset: KnowledgeAsset,
                         content_data: Dict) -> KnowledgeAsset:
        asset.metadata.update({
            "config_keys": list(content_data.keys()) if isinstance(content_data, dict) else [],
            "config_type": asset.title.replace("配置: ", "")
        })
        asset.status = AssetStatus.ATOMIZED
        asset.tags.extend(["atomized", "config"])
        return asset

    async def _build_relations(self, new_assets: List[KnowledgeAsset]):
        for asset in new_assets:
            for other_id, other in self._atomized_assets.items():
                if other_id == asset.id:
                    continue
                common_tags = set(asset.tags) & set(other.tags)
                if len(common_tags) >= 2:
                    self._relation_graph[asset.id].add(other_id)
                    self._relation_graph[other_id].add(asset.id)
                    asset.parent_ids.append(other_id)
                    other.child_ids.append(asset.id)
        self._stats["relations_built"] += sum(
            len(v) for v in self._relation_graph.values()
        ) // 2

    def get_related(self, asset_id: str, depth: int = 1) -> List[str]:
        related = set()
        current = {asset_id}
        for _ in range(depth):
            next_level = set()
            for aid in current:
                for rid in self._relation_graph.get(aid, set()):
                    if rid not in related and rid != asset_id:
                        related.add(rid)
                        next_level.add(rid)
            current = next_level
        return list(related)

    def get_stats(self) -> Dict[str, Any]:
        return {**self._stats, "total_atomized": len(self._atomized_assets),
                "relation_count": sum(len(v) for v in self._relation_graph.values()) // 2}


class OutputPipeline:
    """
    输出层: 让知识资产直接赋能开发效率

    输出类型:
    - 代码模板库: 封装通用模块为可复用模板
    - AI辅助编码技能: 封装为SkillSystem可执行技能
    - 开发规范与Checklist: 自动生成校验规则
    - 自动化工具脚本: 生成可执行自动化流程
    """

    def __init__(self, core_ref=None):
        self.core = core_ref
        self._templates: Dict[str, Dict] = {}
        self._skills_generated: List[Dict] = []
        self._specs_generated: List[Dict] = []
        self._scripts_generated: List[Dict] = []
        self._stats = {"templates": 0, "skills": 0, "specs": 0, "scripts": 0}

    async def generate_template(self, asset: KnowledgeAsset) -> Optional[Dict]:
        if asset.asset_type not in (AssetType.CODE_MODULE, AssetType.ARCHITECTURE_PATTERN):
            return None
        template_id = f"tpl_{asset.id}"
        template = {
            "id": template_id,
            "source_asset": asset.id,
            "title": asset.title,
            "type": asset.asset_type.value,
            "inputs": asset.metadata.get("inputs", []),
            "outputs": asset.metadata.get("outputs", []),
            "dependencies": asset.metadata.get("dependencies", []),
            "tags": asset.tags,
            "content_template": self._extract_template_pattern(asset),
            "confidence": asset.confidence
        }
        self._templates[template_id] = template
        asset.status = AssetStatus.STRUCTURED
        asset.apply_compound(0.15)
        self._stats["templates"] += 1
        return template

    async def generate_skill(self, asset: KnowledgeAsset) -> Optional[Dict]:
        if asset.asset_type not in (AssetType.CODE_MODULE, AssetType.DEBUG_TECHNIQUE):
            return None
        skill_id = f"skill_{asset.id}"
        skill_def = {
            "id": skill_id,
            "source_asset": asset.id,
            "name": asset.title.replace("执行记录: ", "").replace("错误: ", "修复_"),
            "trigger_conditions": asset.tags[:3],
            "steps": self._extract_steps(asset),
            "success_patterns": asset.metadata.get("success_patterns", []),
            "failure_patterns": asset.metadata.get("failure_patterns", []),
            "confidence": asset.confidence
        }
        self._skills_generated.append(skill_def)
        asset.status = AssetStatus.STRUCTURED
        asset.apply_compound(0.2)
        self._stats["skills"] += 1

        if self.core:
            try:
                self.core.skill_system.register_skill(
                    skill_def["name"],
                    lambda **kw: skill_def,
                    description=f"复利引擎自动生成: {asset.title}",
                    category="auto_generated"
                )
            except Exception as e:
                logger.debug(f"技能注册失败: {e}")

        return skill_def

    async def generate_spec(self, asset: KnowledgeAsset) -> Optional[Dict]:
        if asset.asset_type not in (AssetType.ERROR_SOLUTION, AssetType.DEBUG_TECHNIQUE):
            return None
        spec_id = f"spec_{asset.id}"
        triple = asset.metadata.get("triple", {})
        spec = {
            "id": spec_id,
            "source_asset": asset.id,
            "title": f"规范: {asset.title}",
            "type": "checklist",
            "items": self._generate_checklist(triple),
            "tags": asset.tags,
            "confidence": asset.confidence
        }
        self._specs_generated.append(spec)
        asset.status = AssetStatus.STRUCTURED
        asset.apply_compound(0.1)
        self._stats["specs"] += 1
        return spec

    async def generate_script(self, asset: KnowledgeAsset) -> Optional[Dict]:
        if asset.asset_type not in (AssetType.TOOL_CONFIG, AssetType.AUTOMATION_SCRIPT):
            return None
        script_id = f"script_{asset.id}"
        script = {
            "id": script_id,
            "source_asset": asset.id,
            "title": f"脚本: {asset.title}",
            "config_type": asset.metadata.get("config_type", ""),
            "automation_steps": self._extract_automation_steps(asset),
            "tags": asset.tags
        }
        self._scripts_generated.append(script)
        asset.status = AssetStatus.STRUCTURED
        asset.apply_compound(0.12)
        self._stats["scripts"] += 1
        return script

    async def process_asset(self, asset: KnowledgeAsset) -> List[Dict]:
        outputs = []
        tpl = await self.generate_template(asset)
        if tpl:
            outputs.append(tpl)
        skill = await self.generate_skill(asset)
        if skill:
            outputs.append(skill)
        spec = await self.generate_spec(asset)
        if spec:
            outputs.append(spec)
        script = await self.generate_script(asset)
        if script:
            outputs.append(script)
        return outputs

    def _extract_template_pattern(self, asset: KnowledgeAsset) -> str:
        try:
            data = json.loads(asset.content) if isinstance(asset.content, str) else asset.content
            if isinstance(data, dict):
                return json.dumps({k: f"{{{{{k}}}}}" for k in data.keys()}, ensure_ascii=False)
        except Exception:
            pass
        return asset.content[:200]

    def _extract_steps(self, asset: KnowledgeAsset) -> List[Dict]:
        try:
            data = json.loads(asset.content) if isinstance(asset.content, str) else asset.content
            if isinstance(data, dict) and "actions" in data:
                return [{"tool": a.get("tool", ""), "params": a.get("parameters", {})}
                        for a in data["actions"]]
        except Exception:
            pass
        return [{"step": 1, "action": "execute", "description": asset.title}]

    def _generate_checklist(self, triple: Dict) -> List[Dict]:
        items = []
        problem = triple.get("problem", "")
        cause = triple.get("cause", "")
        solution = triple.get("solution", "")
        if problem:
            items.append({"check": f"确认问题: {problem[:100]}", "type": "verify"})
        if cause:
            items.append({"check": f"排查原因: {cause}", "type": "diagnose"})
        if solution:
            items.append({"check": f"执行方案: {solution[:100]}", "type": "fix"})
        if not items:
            items.append({"check": "审查原始记录", "type": "review"})
        return items

    def _extract_automation_steps(self, asset: KnowledgeAsset) -> List[Dict]:
        return [{"step": i+1, "action": "configure", "target": asset.title}
                for i in range(len(asset.metadata.get("config_keys", [])))]

    def search_templates(self, query: str, limit: int = 5) -> List[Dict]:
        results = []
        q = query.lower()
        for tpl in self._templates.values():
            score = 0
            if q in tpl.get("title", "").lower():
                score += 0.5
            for tag in tpl.get("tags", []):
                if q in tag.lower():
                    score += 0.3
            if score > 0:
                results.append((tpl, score))
        results.sort(key=lambda x: -x[1])
        return [r[0] for r in results[:limit]]

    def get_stats(self) -> Dict[str, Any]:
        return {**self._stats, "total_templates": len(self._templates)}


class IteratePipeline:
    """
    迭代层: 让闭环持续生长

    驱动模式:
    - 需求驱动: 新需求检索知识库→调用资产→优化→反哺
    - 问题驱动: 新Bug检索历史方案→AI分析→解决→反哺
    - 工具链迭代: 评估资产使用率→淘汰冗余→优化高频
    """

    def __init__(self, core_ref=None):
        self.core = core_ref
        self._iteration_history: List[Dict] = []
        self._stats = {"demand_driven": 0, "problem_driven": 0,
                       "tool_iterated": 0, "assets_deprecated": 0}

    async def demand_driven_iterate(self, requirement: str,
                                     available_assets: List[KnowledgeAsset]) -> Dict[str, Any]:
        matched = self._match_assets(requirement, available_assets)
        self._stats["demand_driven"] += 1

        iteration = {
            "type": "demand_driven",
            "requirement": requirement,
            "matched_assets": len(matched),
            "top_matches": [a.to_dict() for a in matched[:3]],
            "suggested_approach": self._suggest_approach(requirement, matched),
            "timestamp": time.time()
        }
        self._iteration_history.append(iteration)
        return iteration

    async def problem_driven_iterate(self, problem: str,
                                      available_assets: List[KnowledgeAsset]) -> Dict[str, Any]:
        matched = self._match_assets(problem, available_assets)
        self._stats["problem_driven"] += 1

        solution_found = any(
            a.asset_type == AssetType.ERROR_SOLUTION and a.metadata.get("resolved")
            for a in matched
        )

        iteration = {
            "type": "problem_driven",
            "problem": problem,
            "matched_assets": len(matched),
            "solution_found": solution_found,
            "top_matches": [a.to_dict() for a in matched[:3]],
            "suggested_fix": self._suggest_fix(problem, matched),
            "timestamp": time.time()
        }
        self._iteration_history.append(iteration)
        return iteration

    async def tool_chain_iterate(self, all_assets: List[KnowledgeAsset],
                                  min_reuse: int = 2,
                                  max_deprecated_value: float = 0.3) -> Dict[str, Any]:
        deprecated = []
        optimized = []
        for asset in all_assets:
            if asset.reuse_count == 0 and asset.compound_value < max_deprecated_value:
                asset.status = AssetStatus.DEPLOYED
                deprecated.append(asset.id)
            elif asset.reuse_count >= min_reuse:
                asset.apply_compound(0.05)
                optimized.append(asset.id)

        self._stats["tool_iterated"] += 1
        self._stats["assets_deprecated"] += len(deprecated)

        iteration = {
            "type": "tool_chain",
            "deprecated_count": len(deprecated),
            "optimized_count": len(optimized),
            "deprecated_ids": deprecated[:10],
            "optimized_ids": optimized[:10],
            "timestamp": time.time()
        }
        self._iteration_history.append(iteration)
        return iteration

    def _match_assets(self, query: str, assets: List[KnowledgeAsset]) -> List[KnowledgeAsset]:
        scored = []
        q_words = set(query.lower().split())
        q_lower = query.lower()
        for asset in assets:
            score = 0
            title_words = set(asset.title.lower().split())
            tag_overlap = q_words & set(t.lower() for t in asset.tags)
            title_overlap = q_words & title_words
            score += len(tag_overlap) * 0.3
            score += len(title_overlap) * 0.5
            if q_lower in asset.title.lower():
                score += 0.4
            for tag in asset.tags:
                if q_lower in tag.lower() or tag.lower() in q_lower:
                    score += 0.2
            score += asset.confidence * 0.2
            score += min(asset.reuse_count * 0.05, 0.3)
            if score > 0.1:
                scored.append((asset, score))
        scored.sort(key=lambda x: -x[1])
        return [a for a, _ in scored]

    def _suggest_approach(self, requirement: str,
                           matched: List[KnowledgeAsset]) -> str:
        if not matched:
            return f"无历史资产匹配'{requirement}'，建议从零开始并记录过程"
        top = matched[0]
        return f"参考资产'{top.title}'(置信度={top.confidence:.1f})，复用其模式并定制"

    def _suggest_fix(self, problem: str,
                      matched: List[KnowledgeAsset]) -> str:
        resolved = [a for a in matched
                    if a.asset_type == AssetType.ERROR_SOLUTION and a.metadata.get("resolved")]
        if resolved:
            return f"找到{len(resolved)}个已解决方案，优先参考最高置信度方案"
        return f"无已解决匹配，建议分析问题后创建新的错误解决方案资产"

    def get_stats(self) -> Dict[str, Any]:
        return {**self._stats, "total_iterations": len(self._iteration_history)}


class CompoundInterestEngine:
    """
    复利引擎 - 闭环学习+知识库存储复利工程的核心协调器

    复利闭环: 摄取 → 消化 → 输出 → 迭代 → (反馈到摄取)

    复利公式: V(n) = V(0) × (1 + r)^n
    - V(0): 初始知识资产价值
    - r: 每次循环的知识增量率 (由消化质量和输出复用率决定)
    - n: 循环次数

    与双循环架构的协同:
    - 内循环: 摄取→消化 (高频，每次任务执行触发)
    - 外循环: 输出→迭代 (低频，批量处理和优化)
    - 桥接: 内循环产出传递给外循环进行资产优化
    """

    def __init__(self, core_ref=None):
        self.core = core_ref
        self.ingest = IngestPipeline(core_ref)
        self.digest = DigestPipeline(core_ref)
        self.output = OutputPipeline(core_ref)
        self.iterate = IteratePipeline(core_ref)

        self._all_assets: Dict[str, KnowledgeAsset] = {}
        self._cycle_count = 0
        self._compound_rate = 0.1
        self._running = False
        self._history: List[Dict] = []

    async def run_cycle(self) -> Dict[str, Any]:
        self._cycle_count += 1
        start_time = time.time()

        raw_assets = self.ingest.drain_assets()
        for asset in raw_assets:
            self._all_assets[asset.id] = asset

        atomized = await self.digest.atomize(raw_assets) if raw_assets else []

        outputs = []
        for asset in atomized:
            asset_outputs = await self.output.process_asset(asset)
            outputs.extend(asset_outputs)

        all_asset_list = list(self._all_assets.values())
        iteration_result = await self.iterate.tool_chain_iterate(all_asset_list)

        total_value = sum(a.compound_value for a in all_asset_list)
        avg_confidence = (sum(a.confidence for a in all_asset_list) / len(all_asset_list)
                          if all_asset_list else 0)

        cycle_result = {
            "cycle": self._cycle_count,
            "ingested": len(raw_assets),
            "atomized": len(atomized),
            "outputs_generated": len(outputs),
            "deprecated": iteration_result.get("deprecated_count", 0),
            "optimized": iteration_result.get("optimized_count", 0),
            "total_assets": len(self._all_assets),
            "total_compound_value": round(total_value, 2),
            "avg_confidence": round(avg_confidence, 3),
            "compound_rate": self._compound_rate,
            "elapsed_ms": round((time.time() - start_time) * 1000, 1)
        }

        self._history.append(cycle_result)
        if len(self._history) > 200:
            self._history = self._history[-200:]

        return cycle_result

    async def ingest_execution(self, task_desc: str, actions: List[Dict],
                                result: Dict) -> List[KnowledgeAsset]:
        assets = await self.ingest.collect_from_execution(task_desc, actions, result)
        for a in assets:
            self._all_assets[a.id] = a
        return assets

    async def ingest_learning(self, topic: str, insights: List[Dict]) -> List[KnowledgeAsset]:
        assets = await self.ingest.collect_from_learning(topic, insights)
        for a in assets:
            self._all_assets[a.id] = a
        return assets

    async def ingest_error(self, error_type: str, error_msg: str,
                            solution: str = "", context: Dict = None) -> KnowledgeAsset:
        asset = await self.ingest.collect_from_error(error_type, error_msg, solution, context)
        self._all_assets[asset.id] = asset
        return asset

    async def ingest_config(self, config_type: str, config_data: Dict) -> KnowledgeAsset:
        asset = await self.ingest.collect_config(config_type, config_data)
        self._all_assets[asset.id] = asset
        return asset

    async def search_assets(self, query: str, asset_type: Optional[AssetType] = None,
                             limit: int = 10) -> List[Dict]:
        results = []
        q = query.lower()
        for asset in self._all_assets.values():
            if asset_type and asset.asset_type != asset_type:
                continue
            score = 0
            if q in asset.title.lower():
                score += 0.4
            tag_match = sum(1 for t in asset.tags if q in t.lower())
            score += tag_match * 0.2
            score += asset.confidence * 0.2
            score += min(asset.reuse_count * 0.05, 0.2)
            if score > 0.1:
                results.append((asset, score))
        results.sort(key=lambda x: -x[1])
        return [a.to_dict() for a, _ in results[:limit]]

    async def demand_query(self, requirement: str) -> Dict[str, Any]:
        return await self.iterate.demand_driven_iterate(
            requirement, list(self._all_assets.values())
        )

    async def problem_query(self, problem: str) -> Dict[str, Any]:
        return await self.iterate.problem_driven_iterate(
            problem, list(self._all_assets.values())
        )

    def get_compound_value(self) -> float:
        return sum(a.compound_value for a in self._all_assets.values())

    def get_statistics(self) -> Dict[str, Any]:
        by_type = defaultdict(int)
        by_status = defaultdict(int)
        for asset in self._all_assets.values():
            by_type[asset.asset_type.value] += 1
            by_status[asset.status.value] += 1

        return {
            "cycle_count": self._cycle_count,
            "total_assets": len(self._all_assets),
            "compound_value": round(self.get_compound_value(), 2),
            "compound_rate": self._compound_rate,
            "by_type": dict(by_type),
            "by_status": dict(by_status),
            "ingest": self.ingest.get_stats(),
            "digest": self.digest.get_stats(),
            "output": self.output.get_stats(),
            "iterate": self.iterate.get_stats()
        }

    def get_trajectory(self, last_n: int = 10) -> List[Dict]:
        return self._history[-last_n:]


_compound_engine: Optional[CompoundInterestEngine] = None


def get_compound_engine(core_ref=None) -> CompoundInterestEngine:
    global _compound_engine
    if _compound_engine is None:
        _compound_engine = CompoundInterestEngine(core_ref)
    return _compound_engine
