"""
技能自动创建模块
从对话和任务执行中自动生成可复用技能
"""

import os
import json
import logging
import hashlib
import ollama
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SkillType(Enum):
    """技能类型"""
    PROCEDURE = "procedure"
    WORKFLOW = "workflow"
    TEMPLATE = "template"
    COMPOSITE = "composite"


class SkillStatus(Enum):
    """技能状态"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class SkillDefinition:
    """技能定义"""
    id: str
    name: str
    description: str
    skill_type: str
    steps: List[Dict[str, Any]]
    parameters: Dict[str, Any]
    triggers: List[str]
    success_patterns: List[str]
    failure_patterns: List[str]
    usage_count: int
    success_rate: float
    created_at: str
    updated_at: str
    status: str
    source: str
    tags: List[str]


class SkillAutoCreator:
    """技能自动创建器"""
    
    def __init__(self, model: str = "gemma4:e4b", skills_dir: str = "./data/skills"):
        self.model = model
        self.skills_dir = skills_dir
        self.skills: Dict[str, SkillDefinition] = {}
        self.creation_history: List[Dict[str, Any]] = []
        
        os.makedirs(skills_dir, exist_ok=True)
        self._load_skills()
        
        logger.info(f"技能自动创建器初始化 (skills_dir={skills_dir})")
    
    def _load_skills(self):
        """加载已有技能"""
        try:
            for filename in os.listdir(self.skills_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(self.skills_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        skill = SkillDefinition(**data)
                        self.skills[skill.id] = skill
            logger.info(f"已加载 {len(self.skills)} 个技能")
        except Exception as e:
            logger.error(f"加载技能失败: {e}")
    
    def _save_skill(self, skill: SkillDefinition):
        """保存技能"""
        try:
            filepath = os.path.join(self.skills_dir, f"{skill.id}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    "id": skill.id,
                    "name": skill.name,
                    "description": skill.description,
                    "skill_type": skill.skill_type,
                    "steps": skill.steps,
                    "parameters": skill.parameters,
                    "triggers": skill.triggers,
                    "success_patterns": skill.success_patterns,
                    "failure_patterns": skill.failure_patterns,
                    "usage_count": skill.usage_count,
                    "success_rate": skill.success_rate,
                    "created_at": skill.created_at,
                    "updated_at": skill.updated_at,
                    "status": skill.status,
                    "source": skill.source,
                    "tags": skill.tags
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"技能已保存: {skill.id}")
        except Exception as e:
            logger.error(f"保存技能失败: {e}")
    
    def _generate_skill_id(self, name: str) -> str:
        """生成技能ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        hash_part = hashlib.md5(name.encode()).hexdigest()[:8]
        return f"skill_{timestamp}_{hash_part}"
    
    async def create_from_task(self, task_description: str, task_actions: List[Dict[str, Any]], 
                               task_result: Dict[str, Any]) -> Dict[str, Any]:
        """从任务执行创建技能"""
        try:
            # 使用LLM分析任务并提取技能模式
            prompt = f"""
分析以下任务执行过程，提取可复用的技能模式。

任务描述: {task_description}

执行步骤:
{json.dumps(task_actions, ensure_ascii=False, indent=2)}

执行结果: {json.dumps(task_result, ensure_ascii=False)}

请以JSON格式输出技能定义：
{{
    "name": "技能名称（简洁明了）",
    "description": "技能描述",
    "skill_type": "procedure/workflow/template",
    "steps": [
        {{"action": "工具名称", "parameters": {{}}, "description": "步骤描述"}}
    ],
    "parameters": {{"param1": "参数说明"}},
    "triggers": ["触发条件1", "触发条件2"],
    "success_patterns": ["成功模式1"],
    "failure_patterns": ["失败模式1"],
    "tags": ["标签1", "标签2"]
}}
"""
            
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response["message"]["content"]
            
            # 解析JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                skill_data = json.loads(json_match.group())
            else:
                return {"status": "error", "message": "无法解析技能定义"}
            
            # 创建技能
            skill_id = self._generate_skill_id(skill_data.get("name", "unnamed"))
            
            skill = SkillDefinition(
                id=skill_id,
                name=skill_data.get("name", "未命名技能"),
                description=skill_data.get("description", ""),
                skill_type=skill_data.get("skill_type", SkillType.PROCEDURE.value),
                steps=skill_data.get("steps", []),
                parameters=skill_data.get("parameters", {}),
                triggers=skill_data.get("triggers", []),
                success_patterns=skill_data.get("success_patterns", []),
                failure_patterns=skill_data.get("failure_patterns", []),
                usage_count=0,
                success_rate=0.0,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                status=SkillStatus.ACTIVE.value,
                source="auto_created_from_task",
                tags=skill_data.get("tags", [])
            )
            
            self.skills[skill_id] = skill
            self._save_skill(skill)
            
            creation_record = {
                "skill_id": skill_id,
                "source": "task",
                "task_description": task_description,
                "created_at": datetime.now().isoformat()
            }
            self.creation_history.append(creation_record)
            
            logger.info(f"从任务创建技能: {skill_id}")
            return {
                "status": "success",
                "skill_id": skill_id,
                "skill_name": skill.name,
                "skill": {
                    "id": skill.id,
                    "name": skill.name,
                    "description": skill.description,
                    "steps_count": len(skill.steps)
                }
            }
            
        except Exception as e:
            logger.error(f"从任务创建技能失败: {e}")
            return {"status": "error", "error": str(e)}
    
    async def create_from_conversation(self, conversation: List[Dict[str, str]], 
                                       outcome: str) -> Dict[str, Any]:
        """从对话创建技能"""
        try:
            # 提取对话中的关键信息
            conversation_text = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in conversation
            ])
            
            prompt = f"""
分析以下对话，提取用户常用的操作模式或偏好，创建可复用技能。

对话内容:
{conversation_text}

结果: {outcome}

请以JSON格式输出技能定义：
{{
    "name": "技能名称",
    "description": "技能描述",
    "skill_type": "procedure",
    "steps": [
        {{"action": "操作", "parameters": {{}}, "description": "描述"}}
    ],
    "triggers": ["触发条件"],
    "success_patterns": ["成功模式"],
    "tags": ["标签"]
}}
"""
            
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response["message"]["content"]
            
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                skill_data = json.loads(json_match.group())
            else:
                return {"status": "error", "message": "无法解析技能定义"}
            
            skill_id = self._generate_skill_id(skill_data.get("name", "unnamed"))
            
            skill = SkillDefinition(
                id=skill_id,
                name=skill_data.get("name", "未命名技能"),
                description=skill_data.get("description", ""),
                skill_type=skill_data.get("skill_type", SkillType.PROCEDURE.value),
                steps=skill_data.get("steps", []),
                parameters=skill_data.get("parameters", {}),
                triggers=skill_data.get("triggers", []),
                success_patterns=skill_data.get("success_patterns", []),
                failure_patterns=skill_data.get("failure_patterns", []),
                usage_count=0,
                success_rate=0.0,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                status=SkillStatus.ACTIVE.value,
                source="auto_created_from_conversation",
                tags=skill_data.get("tags", [])
            )
            
            self.skills[skill_id] = skill
            self._save_skill(skill)
            
            logger.info(f"从对话创建技能: {skill_id}")
            return {
                "status": "success",
                "skill_id": skill_id,
                "skill_name": skill.name
            }
            
        except Exception as e:
            logger.error(f"从对话创建技能失败: {e}")
            return {"status": "error", "error": str(e)}
    
    async def improve_skill(self, skill_id: str, execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """改进技能"""
        if skill_id not in self.skills:
            return {"status": "error", "message": f"技能不存在: {skill_id}"}
        
        skill = self.skills[skill_id]
        skill.usage_count += 1
        
        if execution_result.get("success", False):
            # 更新成功率
            skill.success_rate = (skill.success_rate * (skill.usage_count - 1) + 1) / skill.usage_count
            
            # 添加成功模式
            if "pattern" in execution_result:
                if execution_result["pattern"] not in skill.success_patterns:
                    skill.success_patterns.append(execution_result["pattern"])
        else:
            # 更新成功率
            skill.success_rate = (skill.success_rate * (skill.usage_count - 1)) / skill.usage_count
            
            # 添加失败模式
            if "error" in execution_result:
                if execution_result["error"] not in skill.failure_patterns:
                    skill.failure_patterns.append(execution_result["error"])
        
        skill.updated_at = datetime.now().isoformat()
        self._save_skill(skill)
        
        logger.info(f"技能已改进: {skill_id} (成功率: {skill.success_rate:.2%})")
        return {
            "status": "success",
            "skill_id": skill_id,
            "usage_count": skill.usage_count,
            "success_rate": skill.success_rate
        }
    
    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """获取技能"""
        if skill_id in self.skills:
            skill = self.skills[skill_id]
            return {
                "status": "success",
                "skill": {
                    "id": skill.id,
                    "name": skill.name,
                    "description": skill.description,
                    "skill_type": skill.skill_type,
                    "steps": skill.steps,
                    "parameters": skill.parameters,
                    "triggers": skill.triggers,
                    "success_patterns": skill.success_patterns,
                    "failure_patterns": skill.failure_patterns,
                    "usage_count": skill.usage_count,
                    "success_rate": skill.success_rate,
                    "status": skill.status,
                    "tags": skill.tags
                }
            }
        return {"status": "error", "message": f"技能不存在: {skill_id}"}
    
    def find_matching_skill(self, task_description: str) -> Optional[Dict[str, Any]]:
        """查找匹配的技能"""
        best_match = None
        best_score = 0
        
        for skill in self.skills.values():
            if skill.status != SkillStatus.ACTIVE.value:
                continue
            
            # 检查触发条件
            score = 0
            for trigger in skill.triggers:
                if trigger.lower() in task_description.lower():
                    score += 1
            
            # 检查标签
            for tag in skill.tags:
                if tag.lower() in task_description.lower():
                    score += 0.5
            
            # 考虑成功率
            score *= (0.5 + skill.success_rate * 0.5)
            
            if score > best_score:
                best_score = score
                best_match = skill
        
        if best_match:
            return {
                "status": "success",
                "skill": {
                    "id": best_match.id,
                    "name": best_match.name,
                    "description": best_match.description,
                    "steps": best_match.steps,
                    "match_score": best_score
                }
            }
        
        return {"status": "not_found", "message": "未找到匹配的技能"}
    
    def list_skills(self, status: str = None, tag: str = None) -> Dict[str, Any]:
        """列出技能"""
        skills = []
        for skill in self.skills.values():
            if status and skill.status != status:
                continue
            if tag and tag not in skill.tags:
                continue
            
            skills.append({
                "id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "skill_type": skill.skill_type,
                "usage_count": skill.usage_count,
                "success_rate": skill.success_rate,
                "status": skill.status,
                "tags": skill.tags
            })
        
        return {
            "status": "success",
            "skills": skills,
            "count": len(skills)
        }
    
    def delete_skill(self, skill_id: str) -> Dict[str, Any]:
        """删除技能"""
        if skill_id not in self.skills:
            return {"status": "error", "message": f"技能不存在: {skill_id}"}
        
        skill = self.skills[skill_id]
        skill.status = SkillStatus.ARCHIVED.value
        skill.updated_at = datetime.now().isoformat()
        self._save_skill(skill)
        
        del self.skills[skill_id]
        
        logger.info(f"技能已删除: {skill_id}")
        return {"status": "success", "message": f"技能已删除: {skill_id}"}


skill_auto_creator = SkillAutoCreator()
