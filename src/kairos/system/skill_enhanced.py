"""
增强技能系统
基于 ClaudeCode 的技能系统设计理念
"""

import logging
import importlib
import inspect
import os
import json
import re
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class SkillCategory(Enum):
    """技能分类"""
    UTILITY = "utility"
    WORKFLOW = "workflow"
    CUSTOM_MODULE = "custom_module"
    KNOWLEDGE = "knowledge"
    COMBINATION = "combination"


class SkillStatus(Enum):
    """技能状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    DEVELOPING = "developing"


@dataclass
class SkillMetadata:
    """技能元数据"""
    name: str
    category: str
    description: str
    version: str
    author: str
    parameters: Dict[str, Any]
    dependencies: List[str] = None
    status: str = "active"
    created_at: str = None
    execution_count: int = 0
    average_execution_time: float = 0.0
    skill_path: str = None
    summary: str = ""
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class EnhancedSkillManager:
    """增强技能管理器"""
    
    def __init__(self, max_workers: int = 10, skills_dir: str = "./skills"):
        self.skills: Dict[str, SkillMetadata] = {}
        self.category_index: Dict[str, List[str]] = {}
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.skills_dir = skills_dir
        
        os.makedirs(self.skills_dir, exist_ok=True)
        
        self._initialize_builtin_skills()
        self._load_skills_from_directory()
        
        logger.info("EnhancedSkillManager initialized")
    
    def _initialize_builtin_skills(self):
        """初始化内置技能"""
        def echo(message: str) -> Dict[str, Any]:
            return {'status': 'success', 'message': message}
        
        self.register_skill(
            skill_name='echo',
            skill_function=echo,
            description='Echoes back the input message',
            parameters={'message': 'The message to echo'},
            category='utility',
            version='1.0.0'
        )
        
        def help_skill(skill_name: str = None) -> Dict[str, Any]:
            """显示技能帮助信息"""
            if skill_name:
                return self.get_skill_info(skill_name)
            else:
                return self.get_skills()
        
        self.register_skill(
            skill_name='help',
            skill_function=help_skill,
            description='Show help information for skills',
            parameters={'skill_name': 'Optional skill name'},
            category='utility',
            version='1.0.0'
        )
    
    def _load_skills_from_directory(self):
        """从技能目录加载技能"""
        if not os.path.exists(self.skills_dir):
            return
        
        for skill_name in os.listdir(self.skills_dir):
            skill_path = os.path.join(self.skills_dir, skill_name)
            
            if os.path.isdir(skill_path):
                skill_md_path = os.path.join(skill_path, 'SKILL.md')
                
                if os.path.exists(skill_md_path):
                    try:
                        with open(skill_md_path, 'r', encoding='utf-8') as f:
                            skill_md_content = f.read()
                        
                        summary = self._extract_summary(skill_md_content)
                        
                        skill_info = SkillMetadata(
                            name=skill_name,
                            category='custom',
                            description=summary,
                            version='1.0.0',
                            author='system',
                            parameters={},
                            skill_path=skill_path,
                            summary=summary
                        )
                        
                        self.skills[skill_name] = skill_info
                        
                        if skill_info.category not in self.category_index:
                            self.category_index[skill_info.category] = []
                        self.category_index[skill_info.category].append(skill_name)
                        
                        logger.info(f"Skill loaded: {skill_name}")
                        
                    except Exception as e:
                        logger.error(f"Failed to load skill {skill_name}: {e}")
    
    def _extract_summary(self, content: str) -> str:
        """从 SKILL.md 提取摘要"""
        summary_match = re.search(r'# Summary\s+(.+?)(?=\n#|\Z)', content, re.DOTALL)
        if summary_match:
            return summary_match.group(1).strip()
        return content[:200]
    
    def register_skill(
        self,
        skill_name: str,
        skill_function: Callable,
        description: str,
        parameters: Dict[str, Any],
        category: str = "general",
        version: str = "1.0.0",
        author: str = "system",
        dependencies: List[str] = None
    ) -> Dict[str, Any]:
        """注册技能"""
        with self.lock:
            metadata = SkillMetadata(
                name=skill_name,
                category=category,
                description=description,
                version=version,
                author=author,
                parameters=parameters,
                dependencies=dependencies or []
            )
            
            self.skills[skill_name] = metadata
            
            if category not in self.category_index:
                self.category_index[category] = []
            self.category_index[category].append(skill_name)
            
            logger.info(f"Skill registered: {skill_name}")
            
            return {
                'status': 'success',
                'skill': metadata.to_dict()
            }
    
    async def execute_skill(self, skill_name: str, **kwargs) -> Dict[str, Any]:
        """执行技能"""
        if skill_name not in self.skills:
            return {
                'status': 'error',
                'error': f'Skill not found: {skill_name}'
            }
        
        skill = self.skills[skill_name]
        
        try:
            start_time = datetime.now()
            
            if skill.skill_path:
                result = await self._load_and_execute_skill(skill, **kwargs)
            else:
                result = {
                    'status': 'success',
                    'message': f'Skill {skill_name} executed'
                }
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            skill.execution_count += 1
            skill.average_execution_time = (
                (skill.average_execution_time * (skill.execution_count - 1) + execution_time)
                / skill.execution_count
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Skill execution failed: {skill_name} - {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def _load_and_execute_skill(self, skill: SkillMetadata, **kwargs) -> Dict[str, Any]:
        """加载并执行技能"""
        skill_file = os.path.join(skill.skill_path, 'skill.py')
        
        if not os.path.exists(skill_file):
            return {
                'status': 'error',
                'error': f'Skill file not found: {skill_file}'
            }
        
        spec = importlib.util.spec_from_file_location("skill_module", skill_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, 'execute'):
            if inspect.iscoroutinefunction(module.execute):
                return await module.execute(**kwargs)
            else:
                return module.execute(**kwargs)
        else:
            return {
                'status': 'error',
                'error': 'No execute function found in skill'
            }
    
    def get_skills(self) -> Dict[str, Any]:
        """获取所有技能"""
        return {
            'status': 'success',
            'skills': [s.to_dict() for s in self.skills.values()],
            'count': len(self.skills)
        }
    
    def get_skill_info(self, skill_name: str) -> Dict[str, Any]:
        """获取技能信息"""
        if skill_name not in self.skills:
            return {
                'status': 'not_found',
                'message': f'Skill not found: {skill_name}'
            }
        
        return {
            'status': 'success',
            'skill': self.skills[skill_name].to_dict()
        }
    
    def get_skills_by_category(self, category: str) -> Dict[str, Any]:
        """按分类获取技能"""
        if category not in self.category_index:
            return {
                'status': 'success',
                'skills': [],
                'count': 0
            }
        
        skills = [
            self.skills[name].to_dict()
            for name in self.category_index[category]
            if name in self.skills
        ]
        
        return {
            'status': 'success',
            'skills': skills,
            'count': len(skills)
        }
    
    async def get_skill_statistics(self) -> Dict[str, Any]:
        """获取技能统计"""
        total_executions = sum(s.execution_count for s in self.skills.values())
        active_skills = sum(1 for s in self.skills.values() if s.status == 'active')
        
        return {
            'status': 'success',
            'total_skills': len(self.skills),
            'active_skills': active_skills,
            'total_executions': total_executions,
            'categories': list(self.category_index.keys())
        }
