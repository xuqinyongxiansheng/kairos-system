"""
技能定义格式解析器 - Markdown + YAML Frontmatter

设计理念来源:
- cc-haha-main/docs/skills/01-usage-guide.md
- 技能定义格式：Markdown文件 + YAML frontmatter

核心特性:
1. YAML Frontmatter解析
2. 技能元数据提取
3. 工具权限控制
4. 模型切换支持
5. Fork模式执行隔离
6. 条件激活机制
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import yaml


class SkillSource(Enum):
    """技能来源"""
    BUNDLED = "bundled"
    MANAGED = "managed"
    USER = "user"
    PROJECT = "project"
    PLUGIN = "plugin"
    MCP = "mcp"


class SkillExecutionMode(Enum):
    """技能执行模式"""
    INLINE = "inline"
    FORK = "fork"
    ISOLATED = "isolated"


class SkillActivationType(Enum):
    """技能激活类型"""
    MANUAL = "manual"
    AUTO = "auto"
    CONDITIONAL = "conditional"


@dataclass
class SkillActivation:
    """技能激活条件"""
    type: SkillActivationType = SkillActivationType.MANUAL
    file_patterns: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    
    def should_activate(
        self, 
        context: Dict[str, Any]
    ) -> bool:
        """判断是否应该激活"""
        if self.type == SkillActivationType.MANUAL:
            return False
        
        if self.type == SkillActivationType.AUTO:
            return True
        
        current_file = context.get("current_file", "")
        current_command = context.get("current_command", "")
        current_content = context.get("current_content", "")
        
        for pattern in self.file_patterns:
            if re.match(pattern, current_file):
                return True
        
        if current_command in self.commands:
            return True
        
        for keyword in self.keywords:
            if keyword.lower() in current_content.lower():
                return True
        
        return False


@dataclass
class SkillHook:
    """技能钩子"""
    event: str
    action: str
    condition: Optional[str] = None


@dataclass
class SkillDefinition:
    """
    技能定义
    
    从Markdown + YAML Frontmatter解析的完整技能定义
    """
    name: str
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    source: SkillSource = SkillSource.USER
    tools: List[str] = field(default_factory=list)
    model: Optional[str] = None
    execution_mode: SkillExecutionMode = SkillExecutionMode.INLINE
    timeout: float = 300.0
    max_tokens: int = 4096
    temperature: float = 0.7
    activation: SkillActivation = field(default_factory=SkillActivation)
    hooks: List[SkillHook] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    prompt: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    file_path: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "source": self.source.value,
            "tools": self.tools,
            "model": self.model,
            "execution_mode": self.execution_mode.value,
            "timeout": self.timeout,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "activation": {
                "type": self.activation.type.value,
                "file_patterns": self.activation.file_patterns,
                "commands": self.activation.commands,
                "keywords": self.activation.keywords
            },
            "hooks": [
                {"event": h.event, "action": h.action, "condition": h.condition}
                for h in self.hooks
            ],
            "dependencies": self.dependencies,
            "examples": self.examples,
            "prompt": self.prompt[:500] + "..." if len(self.prompt) > 500 else self.prompt,
            "metadata": self.metadata,
            "file_path": self.file_path,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def get_id(self) -> str:
        """获取技能ID"""
        content = f"{self.name}:{self.version}:{self.source.value}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def has_tool(self, tool_name: str) -> bool:
        """检查是否允许使用工具"""
        if not self.tools:
            return True
        return tool_name in self.tools


class SkillParser:
    """
    技能解析器
    
    解析Markdown + YAML Frontmatter格式的技能定义
    """
    
    FRONTMATTER_PATTERN = re.compile(
        r'^---\s*\n(.*?)\n---\s*\n(.*)$',
        re.DOTALL
    )
    
    def __init__(self):
        self._parse_errors: List[Dict[str, Any]] = []
    
    def parse(
        self, 
        content: str, 
        source: SkillSource = SkillSource.USER,
        file_path: Optional[str] = None
    ) -> Optional[SkillDefinition]:
        """
        解析技能定义
        
        Args:
            content: Markdown内容
            source: 技能来源
            file_path: 文件路径
            
        Returns:
            SkillDefinition对象
        """
        try:
            frontmatter, prompt = self._extract_frontmatter(content)
            
            if frontmatter is None:
                self._parse_errors.append({
                    "error": "未找到YAML frontmatter",
                    "file_path": file_path
                })
                return self._create_default_skill(content, source, file_path)
            
            metadata = yaml.safe_load(frontmatter)
            
            if not metadata or not isinstance(metadata, dict):
                self._parse_errors.append({
                    "error": "YAML frontmatter格式错误",
                    "file_path": file_path
                })
                return self._create_default_skill(content, source, file_path)
            
            name = metadata.get("name", "")
            if not name:
                name = self._extract_name_from_path(file_path)
            
            activation = self._parse_activation(metadata.get("activation", {}))
            hooks = self._parse_hooks(metadata.get("hooks", []))
            
            return SkillDefinition(
                name=name,
                description=metadata.get("description", ""),
                version=metadata.get("version", "1.0.0"),
                author=metadata.get("author", ""),
                source=source,
                tools=metadata.get("tools", []),
                model=metadata.get("model"),
                execution_mode=SkillExecutionMode(
                    metadata.get("execution_mode", "inline")
                ),
                timeout=float(metadata.get("timeout", 300)),
                max_tokens=int(metadata.get("max_tokens", 4096)),
                temperature=float(metadata.get("temperature", 0.7)),
                activation=activation,
                hooks=hooks,
                dependencies=metadata.get("dependencies", []),
                examples=metadata.get("examples", []),
                prompt=prompt.strip(),
                metadata=metadata.get("metadata", {}),
                file_path=file_path
            )
            
        except Exception as e:
            self._parse_errors.append({
                "error": str(e),
                "file_path": file_path
            })
            return None
    
    def parse_file(
        self, 
        file_path: Union[str, Path],
        source: SkillSource = SkillSource.USER
    ) -> Optional[SkillDefinition]:
        """解析技能文件"""
        path = Path(file_path)
        
        if not path.exists():
            self._parse_errors.append({
                "error": f"文件不存在: {file_path}",
                "file_path": str(file_path)
            })
            return None
        
        try:
            content = path.read_text(encoding='utf-8')
            return self.parse(content, source, str(path))
        except Exception as e:
            self._parse_errors.append({
                "error": str(e),
                "file_path": str(file_path)
            })
            return None
    
    def parse_directory(
        self, 
        directory: Union[str, Path],
        source: SkillSource = SkillSource.USER,
        recursive: bool = True
    ) -> List[SkillDefinition]:
        """解析目录中的所有技能"""
        skills = []
        dir_path = Path(directory)
        
        if not dir_path.exists():
            return skills
        
        pattern = "**/SKILL.md" if recursive else "*/SKILL.md"
        
        for skill_file in dir_path.glob(pattern):
            skill = self.parse_file(skill_file, source)
            if skill:
                skills.append(skill)
        
        return skills
    
    def _extract_frontmatter(
        self, 
        content: str
    ) -> Tuple[Optional[str], str]:
        """提取YAML frontmatter"""
        match = self.FRONTMATTER_PATTERN.match(content)
        
        if match:
            return match.group(1), match.group(2)
        
        return None, content
    
    def _parse_activation(
        self, 
        data: Dict[str, Any]
    ) -> SkillActivation:
        """解析激活条件"""
        if not data:
            return SkillActivation()
        
        activation_type = SkillActivationType(
            data.get("type", "manual")
        )
        
        return SkillActivation(
            type=activation_type,
            file_patterns=data.get("file_patterns", []),
            commands=data.get("commands", []),
            keywords=data.get("keywords", [])
        )
    
    def _parse_hooks(
        self, 
        data: List[Dict[str, Any]]
    ) -> List[SkillHook]:
        """解析钩子"""
        hooks = []
        
        for hook_data in data:
            hook = SkillHook(
                event=hook_data.get("event", ""),
                action=hook_data.get("action", ""),
                condition=hook_data.get("condition")
            )
            hooks.append(hook)
        
        return hooks
    
    def _create_default_skill(
        self, 
        content: str, 
        source: SkillSource,
        file_path: Optional[str]
    ) -> SkillDefinition:
        """创建默认技能定义"""
        name = self._extract_name_from_path(file_path)
        
        lines = content.split('\n')
        description = ""
        for line in lines[:5]:
            if line.startswith('#'):
                description = line.lstrip('#').strip()
                break
        
        return SkillDefinition(
            name=name,
            description=description,
            source=source,
            prompt=content,
            file_path=file_path
        )
    
    def _extract_name_from_path(
        self, 
        file_path: Optional[str]
    ) -> str:
        """从路径提取名称"""
        if not file_path:
            return f"skill_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"
        
        path = Path(file_path)
        return path.parent.name if path.parent.name else path.stem
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """获取解析错误"""
        return self._parse_errors.copy()
    
    def clear_errors(self) -> None:
        """清除错误"""
        self._parse_errors.clear()


class SkillRegistry:
    """
    技能注册表
    
    管理所有已注册的技能
    """
    
    def __init__(self):
        self._skills: Dict[str, SkillDefinition] = {}
        self._by_name: Dict[str, List[str]] = {}
        self._by_source: Dict[SkillSource, List[str]] = {}
        self._parser = SkillParser()
        self._lock = None
    
    def register(
        self, 
        skill: SkillDefinition
    ) -> str:
        """注册技能"""
        skill_id = skill.get_id()
        
        self._skills[skill_id] = skill
        
        if skill.name not in self._by_name:
            self._by_name[skill.name] = []
        self._by_name[skill.name].append(skill_id)
        
        if skill.source not in self._by_source:
            self._by_source[skill.source] = []
        self._by_source[skill.source].append(skill_id)
        
        return skill_id
    
    def unregister(
        self, 
        skill_id: str
    ) -> bool:
        """注销技能"""
        if skill_id not in self._skills:
            return False
        
        skill = self._skills.pop(skill_id)
        
        if skill.name in self._by_name:
            self._by_name[skill.name] = [
                sid for sid in self._by_name[skill.name] 
                if sid != skill_id
            ]
        
        if skill.source in self._by_source:
            self._by_source[skill.source] = [
                sid for sid in self._by_source[skill.source] 
                if sid != skill_id
            ]
        
        return True
    
    def get(
        self, 
        skill_id: str
    ) -> Optional[SkillDefinition]:
        """获取技能"""
        return self._skills.get(skill_id)
    
    def get_by_name(
        self, 
        name: str
    ) -> Optional[SkillDefinition]:
        """按名称获取技能"""
        ids = self._by_name.get(name, [])
        if ids:
            return self._skills.get(ids[0])
        return None
    
    def list_all(self) -> List[SkillDefinition]:
        """列出所有技能"""
        return list(self._skills.values())
    
    def list_by_source(
        self, 
        source: SkillSource
    ) -> List[SkillDefinition]:
        """按来源列出技能"""
        ids = self._by_source.get(source, [])
        return [self._skills[sid] for sid in ids if sid in self._skills]
    
    def search(
        self, 
        query: str
    ) -> List[SkillDefinition]:
        """搜索技能"""
        results = []
        query_lower = query.lower()
        
        for skill in self._skills.values():
            if query_lower in skill.name.lower():
                results.append(skill)
            elif query_lower in skill.description.lower():
                results.append(skill)
            elif any(query_lower in kw.lower() for kw in skill.activation.keywords):
                results.append(skill)
        
        return results
    
    def load_from_directory(
        self, 
        directory: Union[str, Path],
        source: SkillSource = SkillSource.USER
    ) -> int:
        """从目录加载技能"""
        skills = self._parser.parse_directory(directory, source)
        
        count = 0
        for skill in skills:
            self.register(skill)
            count += 1
        
        return count
    
    def load_from_file(
        self, 
        file_path: Union[str, Path],
        source: SkillSource = SkillSource.USER
    ) -> Optional[str]:
        """从文件加载技能"""
        skill = self._parser.parse_file(file_path, source)
        
        if skill:
            return self.register(skill)
        
        return None
    
    def get_activation_candidates(
        self, 
        context: Dict[str, Any]
    ) -> List[SkillDefinition]:
        """获取应激活的技能"""
        candidates = []
        
        for skill in self._skills.values():
            if skill.activation.should_activate(context):
                candidates.append(skill)
        
        return candidates
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_skills": len(self._skills),
            "by_source": {
                source.value: len(ids)
                for source, ids in self._by_source.items()
            },
            "parse_errors": len(self._parser.get_errors())
        }


def create_skill_template(
    name: str,
    description: str = "",
    tools: Optional[List[str]] = None,
    prompt: str = ""
) -> str:
    """创建技能模板"""
    template = f'''---
name: {name}
description: {description or "技能描述"}
version: "1.0.0"
author: ""
tools:
{yaml.dump(tools or [], default_flow_style=False).strip()}
model: null
execution_mode: inline
timeout: 300
max_tokens: 4096
temperature: 0.7
activation:
  type: manual
  file_patterns: []
  commands: []
  keywords: []
hooks: []
dependencies: []
examples: []
---

# {name}

{prompt or "在此编写技能提示词..."}

## 使用方式

描述如何使用此技能。

## 示例

提供使用示例。
'''
    return template


def save_skill(
    skill: SkillDefinition,
    directory: Union[str, Path]
) -> str:
    """保存技能到文件"""
    dir_path = Path(directory) / skill.name
    dir_path.mkdir(parents=True, exist_ok=True)
    
    file_path = dir_path / "SKILL.md"
    
    frontmatter = {
        "name": skill.name,
        "description": skill.description,
        "version": skill.version,
        "author": skill.author,
        "tools": skill.tools,
        "model": skill.model,
        "execution_mode": skill.execution_mode.value,
        "timeout": skill.timeout,
        "max_tokens": skill.max_tokens,
        "temperature": skill.temperature,
        "activation": {
            "type": skill.activation.type.value,
            "file_patterns": skill.activation.file_patterns,
            "commands": skill.activation.commands,
            "keywords": skill.activation.keywords
        },
        "hooks": [
            {"event": h.event, "action": h.action, "condition": h.condition}
            for h in skill.hooks
        ],
        "dependencies": skill.dependencies,
        "examples": skill.examples
    }
    
    content = f"---\n{yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)}---\n\n{skill.prompt}"
    
    file_path.write_text(content, encoding='utf-8')
    
    return str(file_path)
