"""
技能管理器
管理所有技能的注册和执行
"""

import logging
from typing import Dict, Any, List, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class SkillManager:
    """技能管理器 - 注册和管理技能"""
    
    def __init__(self):
        self.skills = {}
        self.skill_categories = {}
        self.execution_history = []
    
    async def register_skill(self, name: str, skill_func: Callable, 
                            category: str = 'general',
                            description: str = ''):
        """
        注册技能
        
        Args:
            name: 技能名称
            skill_func: 技能函数
            category: 技能类别
            description: 技能描述
        """
        self.skills[name] = {
            'func': skill_func,
            'category': category,
            'description': description,
            'registered_at': datetime.now().isoformat(),
            'call_count': 0
        }
        
        if category not in self.skill_categories:
            self.skill_categories[category] = []
        self.skill_categories[category].append(name)
        
        logger.info(f"技能注册：{name} ({category})")
        return {'status': 'success', 'skill': name}
    
    async def execute_skill(self, skill_name: str, 
                           **kwargs) -> Dict[str, Any]:
        """
        执行技能
        
        Args:
            skill_name: 技能名称
            **kwargs: 技能参数
            
        Returns:
            执行结果
        """
        try:
            logger.info(f"执行技能：{skill_name}")
            
            if skill_name not in self.skills:
                return {
                    'status': 'error',
                    'error': f'技能不存在：{skill_name}'
                }
            
            skill = self.skills[skill_name]
            func = skill['func']
            
            result = await func(**kwargs) if self._is_async(func) else func(**kwargs)
            
            skill['call_count'] += 1
            self.execution_history.append({
                'skill': skill_name,
                'timestamp': datetime.now().isoformat(),
                'result_status': result.get('status', 'unknown')
            })
            
            logger.info(f"技能执行完成：{skill_name}")
            return result
            
        except Exception as e:
            logger.error(f"技能执行失败：{e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _is_async(self, func: Callable) -> bool:
        """判断函数是否为异步"""
        import asyncio
        return asyncio.iscoroutinefunction(func)
    
    async def list_skills(self, category: str = None) -> Dict[str, Any]:
        """列出技能"""
        if category:
            skills = [
                name for name, skill in self.skills.items()
                if skill['category'] == category
            ]
        else:
            skills = list(self.skills.keys())
        
        return {
            'status': 'success',
            'skills': skills,
            'count': len(skills)
        }
    
    async def get_skill_info(self, skill_name: str) -> Dict[str, Any]:
        """获取技能信息"""
        if skill_name not in self.skills:
            return {
                'status': 'not_found',
                'message': f'技能不存在：{skill_name}'
            }
        
        skill = self.skills[skill_name]
        return {
            'status': 'success',
            'name': skill_name,
            'category': skill['category'],
            'description': skill['description'],
            'call_count': skill['call_count']
        }
    
    async def get_summary(self) -> Dict[str, Any]:
        """获取技能摘要"""
        return {
            'status': 'success',
            'total_skills': len(self.skills),
            'categories': list(self.skill_categories.keys()),
            'total_executions': len(self.execution_history)
        }
