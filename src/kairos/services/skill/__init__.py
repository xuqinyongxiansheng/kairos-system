"""
技能系统
借鉴 cc-haha-main 的 SkillTool + loadSkillsDir 架构：
- SKILL.md 文件格式加载
- 技能发现与注册
- inline 模式执行（注入消息）
- fork 模式执行（子代理执行）

完全重写实现
"""

import os
import re
import json
import time
import logging
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger("SkillSystem")

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "skills")


@dataclass
class SkillDef:
    name: str
    description: str = ""
    when_to_use: str = ""
    allowed_tools: List[str] = field(default_factory=list)
    model: str = ""
    context: str = "inline"
    prompt_template: str = ""
    source: str = "user"
    file_path: str = ""
    aliases: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "when_to_use": self.when_to_use,
            "allowed_tools": self.allowed_tools,
            "model": self.model,
            "context": self.context,
            "source": self.source,
            "aliases": self.aliases,
        }


class SkillManager:
    """技能管理器"""

    def __init__(self, skills_dir: str = None):
        self.skills_dir = skills_dir or SKILLS_DIR
        self._skills: Dict[str, SkillDef] = {}
        self._load_builtin_skills()

    def _load_builtin_skills(self):
        """加载内置技能"""
        builtins = [
            SkillDef(
                name="code-review",
                description="代码审查技能",
                when_to_use="当需要审查代码质量、发现潜在问题时使用",
                context="inline",
                prompt_template="请对以下代码进行全面审查，关注：1.代码质量 2.潜在Bug 3.性能问题 4.安全风险 5.可维护性。使用中文回答。\n\n{args}",
                source="bundled",
            ),
            SkillDef(
                name="explain-code",
                description="代码解释技能",
                when_to_use="当需要理解某段代码的功能和逻辑时使用",
                context="inline",
                prompt_template="请详细解释以下代码的功能、逻辑和设计思路，使用中文回答：\n\n{args}",
                source="bundled",
            ),
            SkillDef(
                name="write-test",
                description="编写测试技能",
                when_to_use="当需要为代码编写单元测试时使用",
                context="inline",
                prompt_template="请为以下代码编写完整的单元测试，包含正常用例和边界用例，使用中文注释：\n\n{args}",
                source="bundled",
            ),
            SkillDef(
                name="debug",
                description="调试技能",
                when_to_use="当代码出现错误需要调试时使用",
                context="inline",
                prompt_template="请分析以下错误信息，找出根本原因并提供修复方案：\n\n{args}",
                source="bundled",
            ),
            SkillDef(
                name="refactor",
                description="重构技能",
                when_to_use="当需要改善代码结构和可读性时使用",
                context="fork",
                prompt_template="请重构以下代码，提升可读性、性能和可维护性，保持功能不变，使用中文注释：\n\n{args}",
                source="bundled",
            ),
            SkillDef(
                name="document",
                description="文档生成技能",
                when_to_use="当需要为代码生成文档时使用",
                context="inline",
                prompt_template="请为以下代码生成完整的中文文档，包含功能描述、参数说明、返回值、使用示例：\n\n{args}",
                source="bundled",
            ),
        ]
        for skill in builtins:
            self._skills[skill.name] = skill

    def load_skills_from_dir(self, directory: str = None) -> int:
        """从目录加载技能"""
        target_dir = directory or self.skills_dir
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
            return 0

        count = 0
        for entry in os.listdir(target_dir):
            skill_dir = os.path.join(target_dir, entry)
            if not os.path.isdir(skill_dir):
                continue

            skill_file = os.path.join(skill_dir, "SKILL.md")
            if not os.path.exists(skill_file):
                continue

            try:
                skill = self._parse_skill_file(skill_file, entry)
                if skill:
                    self._skills[skill.name] = skill
                    count += 1
            except Exception as e:
                logger.error(f"加载技能失败 [{entry}]: {e}")

        return count

    def _parse_skill_file(self, file_path: str, default_name: str) -> Optional[SkillDef]:
        """解析 SKILL.md 文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            frontmatter = {}
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    fm_text = parts[1].strip()
                    for line in fm_text.split("\n"):
                        if ":" in line:
                            key, _, value = line.partition(":")
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            frontmatter[key] = value
                    prompt = parts[2].strip()
                else:
                    prompt = content
            else:
                prompt = content

            return SkillDef(
                name=frontmatter.get("name", default_name),
                description=frontmatter.get("description", ""),
                when_to_use=frontmatter.get("whenToUse", ""),
                allowed_tools=frontmatter.get("allowedTools", "").split(",") if frontmatter.get("allowedTools") else [],
                model=frontmatter.get("model", ""),
                context=frontmatter.get("context", "inline"),
                prompt_template=prompt,
                source="skills",
                file_path=file_path,
                aliases=frontmatter.get("aliases", "").split(",") if frontmatter.get("aliases") else [],
            )
        except Exception as e:
            logger.error(f"解析技能文件失败: {e}")
            return None

    def get_skill(self, name: str) -> Optional[SkillDef]:
        if name in self._skills:
            return self._skills[name]
        for skill in self._skills.values():
            if name in skill.aliases:
                return skill
        return None

    def list_skills(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in sorted(self._skills.values(), key=lambda s: s.name)]

    async def execute_skill(self, name: str, args: str = "") -> Dict[str, Any]:
        """执行技能"""
        skill = self.get_skill(name)
        if not skill:
            return {"success": False, "error": f"技能不存在: {name}"}

        prompt = skill.prompt_template
        if "{args}" in prompt:
            prompt = prompt.replace("{args}", args)
        elif args:
            prompt = f"{prompt}\n\n{args}"

        if skill.context == "fork":
            try:
                from kairos.services.sub_agent import get_sub_agent_runner
                runner = get_sub_agent_runner()
                task = runner.create_task(
                    prompt=prompt,
                    name=f"skill_{skill.name}",
                    description=skill.description,
                    model=skill.model or "gemma4:e4b",
                    allowed_tools=skill.allowed_tools,
                )
                result = await runner.run_sync(task)
                return {
                    "success": result.status.value == "completed",
                    "output": result.result,
                    "error": result.error,
                    "context": "fork",
                    "task_id": result.id,
                }
            except Exception as e:
                return {"success": False, "error": f"Fork模式执行失败: {e}"}
        else:
            try:
                from kairos.system.llm_reasoning import get_ollama_client
                client = get_ollama_client()
                if not await client.is_available():
                    return {"success": False, "error": "Ollama 服务不可用"}

                result = await client.generate(
                    prompt=prompt,
                    system=f"你是技能 '{skill.name}' 的执行者。{skill.description}",
                    model=skill.model or None,
                )
                return {
                    "success": result.success,
                    "output": result.content if result.success else "",
                    "error": result.error if not result.success else "",
                    "context": "inline",
                }
            except Exception as e:
                return {"success": False, "error": f"Inline模式执行失败: {e}"}

    def get_stats(self) -> Dict[str, Any]:
        by_source = {}
        for s in self._skills.values():
            by_source[s.source] = by_source.get(s.source, 0) + 1
        return {
            "total_skills": len(self._skills),
            "by_source": by_source,
            "skills_dir": self.skills_dir,
        }


_skill_manager: Optional[SkillManager] = None


def get_skill_manager() -> SkillManager:
    global _skill_manager
    if _skill_manager is None:
        _skill_manager = SkillManager()
        _skill_manager.load_skills_from_dir()
    return _skill_manager
