#!/usr/bin/env python3
"""
Agent团队模块 - 包含Planner、Generator、Evaluator三个核心Agent
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("AgentTeam")


class PlannerAgent:
    """任务规划代理"""
    
    def __init__(self):
        """初始化任务规划代理"""
        self.skill_registry = self._load_skills()
        self.logger = logging.getLogger(__name__)
        self.logger.info("任务规划代理初始化完成")
    
    def _load_skills(self) -> Dict:
        """加载可用技能"""
        skills = {
            "ai_chat": {"name": "AI聊天", "description": "提供自然语言交互功能", "capabilities": ["聊天", "问答", "对话"]},
            "web_search": {"name": "网络搜索", "description": "获取外部信息", "capabilities": ["搜索", "信息获取"]},
            "knowledge_base": {"name": "知识库", "description": "管理和检索知识", "capabilities": ["知识检索", "知识管理"]},
            "voice": {"name": "语音", "description": "语音识别和合成", "capabilities": ["语音识别", "语音合成"]},
            "file": {"name": "文件操作", "description": "文件管理", "capabilities": ["文件读写", "文件管理"]},
            "system": {"name": "系统管理", "description": "系统监控和管理", "capabilities": ["系统监控", "系统管理"]},
            "code": {"name": "代码处理", "description": "代码分析和生成", "capabilities": ["代码分析", "代码生成"]},
            "task": {"name": "任务调度", "description": "任务计划和执行", "capabilities": ["任务调度", "任务管理"]}
        }
        return skills
    
    async def analyze_task(self, task: Dict) -> Dict:
        """分析用户任务"""
        task_content = task.get('content', '')
        task_type = task.get('type', 'general')
        
        if any(keyword in task_content for keyword in ['搜索', '查找', '获取信息']):
            task_type = 'search'
        elif any(keyword in task_content for keyword in ['聊天', '对话', '问答']):
            task_type = 'chat'
        elif any(keyword in task_content for keyword in ['文件', '读写', '保存']):
            task_type = 'file'
        elif any(keyword in task_content for keyword in ['代码', '编程', '函数']):
            task_type = 'code'
        
        return {
            "type": task_type,
            "content": task_content,
            "requirements": self._extract_requirements(task_content)
        }
    
    def _extract_requirements(self, task_content: str) -> List[str]:
        """提取任务需求"""
        requirements = []
        
        if '搜索' in task_content or '查找' in task_content:
            requirements.append('web_search')
        if '聊天' in task_content or '对话' in task_content:
            requirements.append('ai_chat')
        if '文件' in task_content or '保存' in task_content:
            requirements.append('file')
        if '代码' in task_content or '编程' in task_content:
            requirements.append('code')
        
        return requirements
    
    async def create_plan(self, task_analysis: Dict) -> Dict:
        """创建执行计划"""
        task_type = task_analysis.get('type')
        task_content = task_analysis.get('content')
        requirements = task_analysis.get('requirements', [])
        
        skills = self._select_skills(task_type, requirements)
        steps = self._create_execution_steps(task_type, task_content, skills)
        
        return {
            "task_type": task_type,
            "skills": skills,
            "steps": steps,
            "estimated_time": self._estimate_execution_time(steps)
        }
    
    def _select_skills(self, task_type: str, requirements: List[str]) -> List[str]:
        """选择合适的技能"""
        skills = []
        
        if task_type == 'search' or 'web_search' in requirements:
            skills.append('web_search')
        if task_type == 'chat' or 'ai_chat' in requirements:
            skills.append('ai_chat')
        if task_type == 'file' or 'file' in requirements:
            skills.append('file')
        if task_type == 'code' or 'code' in requirements:
            skills.append('code')
        
        if not skills:
            skills.append('ai_chat')
        
        return skills
    
    def _create_execution_steps(self, task_type: str, task_content: str, skills: List[str]) -> List[Dict]:
        """创建执行步骤"""
        steps = []
        step_id = 1
        
        if 'web_search' in skills:
            steps.append({
                "id": step_id,
                "skill": "web_search",
                "action": "search",
                "parameters": {"query": task_content, "max_results": 5},
                "description": "搜索相关信息"
            })
            step_id += 1
        
        if 'ai_chat' in skills:
            steps.append({
                "id": step_id,
                "skill": "ai_chat",
                "action": "chat",
                "parameters": {"prompt": task_content},
                "description": "与AI对话获取答案"
            })
            step_id += 1
        
        if 'file' in skills:
            steps.append({
                "id": step_id,
                "skill": "file",
                "action": "save",
                "parameters": {"content": "{{previous_result}}", "filename": f"task_result_{task_type}.txt"},
                "description": "保存任务结果"
            })
            step_id += 1
        
        if 'code' in skills:
            steps.append({
                "id": step_id,
                "skill": "code",
                "action": "analyze",
                "parameters": {"content": task_content},
                "description": "分析和处理代码"
            })
        
        return steps
    
    def _estimate_execution_time(self, steps: List[Dict]) -> float:
        """估计执行时间"""
        time_per_step = {"web_search": 3.0, "ai_chat": 5.0, "file": 1.0, "code": 4.0}
        
        total_time = 0.0
        for step in steps:
            skill = step.get('skill')
            total_time += time_per_step.get(skill, 2.0)
        
        return total_time
    
    async def adjust_plan(self, plan: Dict, evaluation: Dict) -> Dict:
        """调整执行计划"""
        feedback = evaluation.get('feedback', {})
        
        adjusted_skills = self._adjust_skills(plan['skills'], feedback)
        adjusted_steps = self._adjust_execution_steps(plan['steps'], feedback)
        
        return {
            **plan,
            "skills": adjusted_skills,
            "steps": adjusted_steps,
            "adjustments": feedback
        }
    
    def _adjust_skills(self, skills: List[str], feedback: Dict) -> List[str]:
        """调整技能选择"""
        if feedback.get('missing_skills'):
            skills.extend(feedback['missing_skills'])
        return list(set(skills))
    
    def _adjust_execution_steps(self, steps: List[Dict], feedback: Dict) -> List[Dict]:
        """调整执行步骤"""
        if feedback.get('adjust_steps'):
            for adjustment in feedback['adjust_steps']:
                step_id = adjustment.get('step_id')
                new_parameters = adjustment.get('parameters')
                
                for step in steps:
                    if step.get('id') == step_id:
                        step['parameters'].update(new_parameters)
        
        return steps


class GeneratorAgent:
    """任务执行代理"""
    
    def __init__(self):
        """初始化任务执行代理"""
        self.skill_registry = self._load_skills()
        self.logger = logging.getLogger(__name__)
        self.logger.info("任务执行代理初始化完成")
    
    def _load_skills(self) -> Dict:
        """加载可用技能"""
        return {
            "ai_chat": {"module": "system.gemma4_brain", "class": "Gemma4Brain"},
            "web_search": {"module": "system.knowledge_base", "class": "KnowledgeBase"},
            "file": {"module": "builtins", "class": "open"},
            "code": {"module": "system.code_repair", "class": "CodeRepairModule"}
        }
    
    async def execute_plan(self, plan: Dict) -> Dict:
        """执行计划"""
        steps = plan.get('steps', [])
        results = []
        execution_time = 0.0
        
        for step in steps:
            start_time = asyncio.get_event_loop().time()
            
            skill_name = step.get('skill')
            action = step.get('action')
            parameters = step.get('parameters', {})
            
            try:
                result = await self._execute_skill(skill_name, action, parameters)
                success = True
            except Exception as e:
                result = {"error": str(e)}
                success = False
            
            end_time = asyncio.get_event_loop().time()
            step_execution_time = end_time - start_time
            execution_time += step_execution_time
            
            results.append({
                "step": step,
                "result": result,
                "success": success,
                "execution_time": step_execution_time
            })
        
        final_result = self._combine_results(results)
        
        return {
            "steps": results,
            "final_result": final_result,
            "execution_time": execution_time,
            "success": all(step.get('success') for step in results)
        }
    
    async def _execute_skill(self, skill_name: str, action: str, parameters: Dict) -> Dict:
        """执行技能"""
        try:
            if skill_name == 'ai_chat':
                return {"result": f"AI处理完成: {parameters.get('prompt', '')[:50]}"}
            elif skill_name == 'web_search':
                return {"result": f"搜索完成: {parameters.get('query', '')[:50]}"}
            elif skill_name == 'file':
                return {"result": f"文件操作完成: {parameters.get('filename', 'unknown')}"}
            elif skill_name == 'code':
                return {"result": f"代码分析完成"}
            else:
                return {"result": f"技能 {skill_name} 执行完成"}
        except Exception as e:
            return {"error": str(e)}
    
    def _combine_results(self, step_results: List[Dict]) -> Dict:
        """合并步骤结果"""
        combined = {"results": [], "errors": []}
        
        for step_result in step_results:
            if step_result.get('success'):
                combined['results'].append(step_result.get('result'))
            else:
                combined['errors'].append(step_result.get('result'))
        
        if combined['errors']:
            return {"status": "error", "errors": combined['errors']}
        
        return {"status": "success", "results": combined['results']}
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {"status": "active", "skills": list(self.skill_registry.keys())}


class EvaluatorAgent:
    """结果评估代理"""
    
    def __init__(self):
        """初始化结果评估代理"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("结果评估代理初始化完成")
    
    async def evaluate_result(self, result: Dict, task: Dict) -> Dict:
        """评估任务结果"""
        final_result = result.get('final_result')
        task_type = task.get('type', 'general')
        
        quality_score = self._evaluate_quality(final_result, task)
        efficiency_score = self._evaluate_efficiency(result.get('execution_time', 0))
        completeness_score = self._evaluate_completeness(final_result, task)
        
        overall_score = (quality_score * 0.5 + efficiency_score * 0.2 + completeness_score * 0.3)
        
        success = overall_score >= 0.7
        
        return {
            "success": success,
            "scores": {
                "quality": quality_score,
                "efficiency": efficiency_score,
                "completeness": completeness_score,
                "overall": overall_score
            },
            "feedback": self._generate_feedback(success, quality_score, efficiency_score, completeness_score),
            "suggestions": self._generate_suggestions(task, result)
        }
    
    def _evaluate_quality(self, final_result: Dict, task: Dict) -> float:
        """评估结果质量"""
        if not final_result:
            return 0.0
        
        status = final_result.get('status')
        if status != 'success':
            return 0.3
        
        results = final_result.get('results', [])
        if not results:
            return 0.5
        
        return min(1.0, len(results) / 3)
    
    def _evaluate_efficiency(self, execution_time: float) -> float:
        """评估执行效率"""
        if execution_time <= 1.0:
            return 1.0
        elif execution_time <= 5.0:
            return 0.8
        elif execution_time <= 10.0:
            return 0.6
        elif execution_time <= 30.0:
            return 0.4
        else:
            return 0.2
    
    def _evaluate_completeness(self, final_result: Dict, task: Dict) -> float:
        """评估完整性"""
        if not final_result:
            return 0.0
        
        status = final_result.get('status')
        if status != 'success':
            return 0.3
        
        return 1.0
    
    def _generate_feedback(self, success: bool, quality_score: float, efficiency_score: float, completeness_score: float) -> Dict:
        """生成反馈"""
        feedback = {}
        
        if not success:
            feedback['message'] = "任务执行失败，请检查执行过程"
        else:
            feedback['message'] = "任务执行成功"
        
        if quality_score < 0.5:
            feedback['quality_feedback'] = "结果质量较低"
        elif quality_score < 0.8:
            feedback['quality_feedback'] = "结果质量一般"
        else:
            feedback['quality_feedback'] = "结果质量良好"
        
        if efficiency_score < 0.5:
            feedback['efficiency_feedback'] = "执行效率较低"
        else:
            feedback['efficiency_feedback'] = "执行效率良好"
        
        if completeness_score < 0.5:
            feedback['completeness_feedback'] = "结果完整性不足"
        else:
            feedback['completeness_feedback'] = "结果完整性良好"
        
        return feedback
    
    def _generate_suggestions(self, task: Dict, result: Dict) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        task_type = task.get('type', 'general')
        execution_time = result.get('execution_time', 0)
        
        if task_type == 'search':
            suggestions.append("可以尝试使用更精确的搜索关键词")
        elif task_type == 'chat':
            suggestions.append("可以提供更详细的问题描述")
        elif task_type == 'code':
            suggestions.append("可以提供更完整的代码上下文")
        
        if execution_time > 10.0:
            suggestions.append("执行时间较长，考虑优化执行步骤")
        
        return suggestions
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {"status": "active"}


class AgentTeam:
    """Agent团队协调器"""
    
    def __init__(self):
        """初始化Agent团队"""
        self.planner = PlannerAgent()
        self.generator = GeneratorAgent()
        self.evaluator = EvaluatorAgent()
        self.logger = logging.getLogger(__name__)
        self.logger.info("Agent团队初始化完成")
    
    async def process_task(self, task: Dict) -> Dict:
        """处理任务"""
        self.logger.info(f"处理任务: {task.get('content', '')[:50]}")
        
        task_analysis = await self.planner.analyze_task(task)
        plan = await self.planner.create_plan(task_analysis)
        
        result = await self.generator.execute_plan(plan)
        
        evaluation = await self.evaluator.evaluate_result(result, task)
        
        if not evaluation.get('success'):
            self.logger.info("任务失败，调整计划")
            adjusted_plan = await self.planner.adjust_plan(plan, evaluation)
            result = await self.generator.execute_plan(adjusted_plan)
            evaluation = await self.evaluator.evaluate_result(result, task)
        
        return {
            "task": task,
            "analysis": task_analysis,
            "plan": plan,
            "result": result,
            "evaluation": evaluation,
            "success": evaluation.get('success', False)
        }
    
    def get_status(self) -> Dict[str, Any]:
        """获取团队状态"""
        return {
            "status": "active",
            "agents": {
                "planner": self.planner.skill_registry.keys() if hasattr(self.planner, 'skill_registry') else [],
                "generator": self.generator.get_status() if hasattr(self.generator, 'get_status') else {},
                "evaluator": self.evaluator.get_status() if hasattr(self.evaluator, 'get_status') else {}
            }
        }


_agent_team = None


def get_agent_team() -> AgentTeam:
    """获取Agent团队实例"""
    global _agent_team
    
    if _agent_team is None:
        _agent_team = AgentTeam()
    
    return _agent_team
