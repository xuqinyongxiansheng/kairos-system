#!/usr/bin/env python3
"""
工作流学习系统 - 为Agent提供工作流学习和评估能力
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("WorkflowLearningSystem")


class EnhancedWorkflowSystem:
    """增强工作流系统 - 提供工作流管理功能"""
    
    def __init__(self):
        """初始化工作流系统"""
        self.workflows = {}
        self._initialize_default_workflows()
        logger.info("EnhancedWorkflowSystem initialized")
    
    def _initialize_default_workflows(self):
        """初始化默认工作流"""
        default_workflows = [
            {
                "id": "workflow_001",
                "name": "代码开发工作流",
                "description": "完整的代码开发流程，包括需求分析、设计、编码、测试和部署",
                "tags": ["开发", "编程", "软件"],
                "steps": [
                    {"name": "需求分析", "action": "analyze", "condition": None},
                    {"name": "架构设计", "action": "design", "condition": None},
                    {"name": "代码实现", "action": "code", "condition": None},
                    {"name": "单元测试", "action": "test", "condition": None},
                    {"name": "集成测试", "action": "integration", "condition": None},
                    {"name": "部署上线", "action": "deploy", "condition": None}
                ],
                "variables": [
                    {"name": "project_name", "type": "string"},
                    {"name": "tech_stack", "type": "string"},
                    {"name": "deadline", "type": "date"}
                ]
            },
            {
                "id": "workflow_002",
                "name": "需求分析工作流",
                "description": "系统的需求分析流程，从用户调研到需求文档生成",
                "tags": ["需求", "分析", "文档"],
                "steps": [
                    {"name": "用户调研", "action": "research", "condition": None},
                    {"name": "需求收集", "action": "collect", "condition": None},
                    {"name": "需求分析", "action": "analyze", "condition": None},
                    {"name": "需求建模", "action": "model", "condition": None},
                    {"name": "需求文档编写", "action": "document", "condition": None},
                    {"name": "需求评审", "action": "review", "condition": None}
                ],
                "variables": [
                    {"name": "user_stories", "type": "list"},
                    {"name": "business_requirements", "type": "list"},
                    {"name": "acceptance_criteria", "type": "list"}
                ]
            },
            {
                "id": "workflow_003",
                "name": "测试工作流",
                "description": "软件测试流程，包括测试计划、执行和报告",
                "tags": ["测试", "质量", "验证"],
                "steps": [
                    {"name": "测试计划", "action": "plan", "condition": None},
                    {"name": "测试用例设计", "action": "design", "condition": None},
                    {"name": "测试环境准备", "action": "prepare", "condition": None},
                    {"name": "测试执行", "action": "execute", "condition": None},
                    {"name": "缺陷管理", "action": "manage", "condition": None},
                    {"name": "测试报告", "action": "report", "condition": None}
                ],
                "variables": [
                    {"name": "test_cases", "type": "list"},
                    {"name": "test_environment", "type": "string"},
                    {"name": "defect_tracker", "type": "string"}
                ]
            }
        ]
        
        for workflow in default_workflows:
            self.workflows[workflow["id"]] = workflow
    
    async def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流"""
        return self.workflows.get(workflow_id)
    
    async def get_all_workflows(self) -> List[Dict[str, Any]]:
        """获取所有工作流"""
        return list(self.workflows.values())
    
    async def create_workflow(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """创建工作流"""
        workflow_id = workflow.get("id", f"workflow_{len(self.workflows) + 1}")
        self.workflows[workflow_id] = workflow
        return {"success": True, "workflow_id": workflow_id}
    
    async def update_workflow(self, workflow_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新工作流"""
        if workflow_id not in self.workflows:
            return {"success": False, "error": "工作流不存在"}
        
        self.workflows[workflow_id].update(updates)
        return {"success": True}
    
    async def delete_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """删除工作流"""
        if workflow_id not in self.workflows:
            return {"success": False, "error": "工作流不存在"}
        
        del self.workflows[workflow_id]
        return {"success": True}


class WorkflowLearningSystem:
    """工作流学习系统 - 提供工作流学习和评估功能"""
    
    def __init__(self):
        """初始化工作流学习系统"""
        self.workflow_system = EnhancedWorkflowSystem()
        self.learning_records: Dict[str, Dict[str, Any]] = {}
        self.assessment_results: Dict[str, Dict[str, Any]] = {}
        
        logger.info("WorkflowLearningSystem initialized")
    
    async def learn_workflow(self, agent_name: str, workflow_id: str) -> Dict[str, Any]:
        """学习工作流"""
        try:
            logger.info(f"{agent_name}开始学习工作流: {workflow_id}")
            
            workflow = await self.workflow_system.get_workflow(workflow_id)
            if not workflow:
                return {
                    "success": False,
                    "error": f"工作流 {workflow_id} 不存在"
                }
            
            learning_record = {
                "agent_name": agent_name,
                "workflow_id": workflow_id,
                "workflow_name": workflow.get("name"),
                "learning_start_time": datetime.now().isoformat(),
                "learning_status": "in_progress",
                "knowledge_points": [],
                "confidence_level": 0.0
            }
            
            await self._learn_workflow_structure(learning_record, workflow)
            await self._learn_workflow_logic(learning_record, workflow)
            await self._learn_workflow_parameters(learning_record, workflow)
            
            learning_record["learning_end_time"] = datetime.now().isoformat()
            learning_record["learning_status"] = "completed"
            learning_record["confidence_level"] = self._calculate_confidence(learning_record)
            
            self.learning_records[f"{agent_name}_{workflow_id}"] = learning_record
            
            logger.info(f"{agent_name}工作流学习完成: {workflow.get('name')}")
            return {
                "success": True,
                "workflow_id": workflow_id,
                "workflow_name": workflow.get("name"),
                "learning_record": learning_record,
                "confidence_level": learning_record["confidence_level"]
            }
            
        except Exception as e:
            logger.error(f"{agent_name}学习工作流失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _learn_workflow_structure(self, learning_record: Dict[str, Any], workflow: Dict[str, Any]):
        """学习工作流结构"""
        steps = workflow.get("steps", [])
        learning_record["knowledge_points"].append({
            "type": "structure",
            "content": f"工作流包含 {len(steps)} 个步骤",
            "timestamp": datetime.now().isoformat()
        })
        
        step_types = {}
        for step in steps:
            action_type = step.get("action", "unknown")
            step_types[action_type] = step_types.get(action_type, 0) + 1
        
        learning_record["knowledge_points"].append({
            "type": "step_types",
            "content": f"步骤类型分布: {step_types}",
            "timestamp": datetime.now().isoformat()
        })
    
    async def _learn_workflow_logic(self, learning_record: Dict[str, Any], workflow: Dict[str, Any]):
        """学习工作流逻辑"""
        steps = workflow.get("steps", [])
        
        has_conditions = any(step.get("condition") for step in steps)
        has_parallel = any(step.get("parallel", False) for step in steps)
        
        logic_info = []
        if has_conditions:
            logic_info.append("包含条件分支")
        if has_parallel:
            logic_info.append("包含并行执行")
        
        if logic_info:
            learning_record["knowledge_points"].append({
                "type": "logic_structure",
                "content": f"工作流逻辑结构: {', '.join(logic_info)}",
                "timestamp": datetime.now().isoformat()
            })
    
    async def _learn_workflow_parameters(self, learning_record: Dict[str, Any], workflow: Dict[str, Any]):
        """学习工作流参数"""
        variables = workflow.get("variables", [])
        if variables:
            variable_info = [f"{var['name']} ({var['type']})" for var in variables]
            learning_record["knowledge_points"].append({
                "type": "parameters",
                "content": f"工作流参数: {', '.join(variable_info)}",
                "timestamp": datetime.now().isoformat()
            })
    
    def _calculate_confidence(self, learning_record: Dict[str, Any]) -> float:
        """计算学习置信度"""
        knowledge_points = learning_record.get("knowledge_points", [])
        if not knowledge_points:
            return 0.0
        
        confidence = 0.0
        for point in knowledge_points:
            if point["type"] == "structure":
                confidence += 0.3
            elif point["type"] == "logic_structure":
                confidence += 0.4
            elif point["type"] == "parameters":
                confidence += 0.3
        
        return min(confidence, 1.0)
    
    async def assess_workflow_understanding(self, agent_name: str, workflow_id: str, assessment_type: str = "comprehensive") -> Dict[str, Any]:
        """评估工作流理解程度"""
        try:
            logger.info(f"{agent_name}工作流理解评估: {workflow_id}")
            
            workflow = await self.workflow_system.get_workflow(workflow_id)
            if not workflow:
                return {
                    "success": False,
                    "error": f"工作流 {workflow_id} 不存在"
                }
            
            learning_key = f"{agent_name}_{workflow_id}"
            learning_record = self.learning_records.get(learning_key)
            
            if not learning_record:
                return {
                    "success": False,
                    "error": f"{agent_name}尚未学习工作流 {workflow_id}"
                }
            
            assessment_result = {
                "agent_name": agent_name,
                "workflow_id": workflow_id,
                "workflow_name": workflow.get("name"),
                "assessment_type": assessment_type,
                "assessment_time": datetime.now().isoformat(),
                "scores": {},
                "overall_score": 0.0,
                "passed": False
            }
            
            if assessment_type == "comprehensive" or assessment_type == "structure":
                assessment_result["scores"]["structure"] = await self._assess_structure_understanding(workflow)
            
            if assessment_type == "comprehensive" or assessment_type == "logic":
                assessment_result["scores"]["logic"] = await self._assess_logic_understanding(workflow)
            
            if assessment_type == "comprehensive" or assessment_type == "parameters":
                assessment_result["scores"]["parameters"] = await self._assess_parameters_understanding(workflow)
            
            if assessment_result["scores"]:
                assessment_result["overall_score"] = sum(assessment_result["scores"].values()) / len(assessment_result["scores"])
                assessment_result["passed"] = assessment_result["overall_score"] >= 0.7
            
            self.assessment_results[f"{agent_name}_{workflow_id}_{assessment_type}"] = assessment_result
            
            logger.info(f"{agent_name}工作流评估完成，得分: {assessment_result['overall_score']}")
            return {
                "success": True,
                "assessment_result": assessment_result,
                "passed": assessment_result["passed"]
            }
            
        except Exception as e:
            logger.error(f"{agent_name}工作流评估失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _assess_structure_understanding(self, workflow: Dict[str, Any]) -> float:
        """评估结构理解"""
        steps = workflow.get("steps", [])
        if not steps:
            return 0.0
        
        score = 0.5
        
        if 1 <= len(steps) <= 20:
            score += 0.2
        
        valid_step_names = sum(1 for step in steps if step.get("name") and len(step["name"]) >= 3)
        name_score = valid_step_names / len(steps) if steps else 0
        score += name_score * 0.3
        
        return min(score, 1.0)
    
    async def _assess_logic_understanding(self, workflow: Dict[str, Any]) -> float:
        """评估逻辑理解"""
        steps = workflow.get("steps", [])
        
        score = 0.4
        
        has_conditions = any(step.get("condition") for step in steps)
        has_next_steps = any(step.get("next_steps") for step in steps)
        
        if has_conditions or has_next_steps:
            score += 0.2
        
        complex_logic_count = sum(1 for step in steps if step.get("condition") or step.get("parallel"))
        if complex_logic_count > 0:
            score += min(complex_logic_count * 0.1, 0.4)
        
        return min(score, 1.0)
    
    async def _assess_parameters_understanding(self, workflow: Dict[str, Any]) -> float:
        """评估参数理解"""
        variables = workflow.get("variables", [])
        
        if not variables:
            return 0.5
        
        valid_variables = sum(1 for var in variables if var.get("name") and var.get("type"))
        var_score = valid_variables / len(variables) if variables else 0
        
        return var_score
    
    async def get_workflow_recommendation(self, agent_name: str, task_description: str) -> Dict[str, Any]:
        """根据任务描述推荐适合的工作流"""
        try:
            logger.info(f"{agent_name}获取工作流推荐: {task_description[:50]}...")
            
            all_workflows = await self.workflow_system.get_all_workflows()
            
            recommendations = []
            for workflow in all_workflows:
                match_score = self._calculate_workflow_match(workflow, task_description)
                if match_score > 0.3:
                    recommendations.append({
                        "workflow_id": workflow["id"],
                        "workflow_name": workflow["name"],
                        "match_score": match_score,
                        "description": workflow.get("description", "")
                    })
            
            recommendations.sort(key=lambda x: x["match_score"], reverse=True)
            
            logger.info(f"{agent_name}工作流推荐完成，找到 {len(recommendations)} 个匹配的工作流")
            return {
                "success": True,
                "recommendations": recommendations[:5],
                "total_matches": len(recommendations)
            }
            
        except Exception as e:
            logger.error(f"{agent_name}获取工作流推荐失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_workflow_match(self, workflow: Dict[str, Any], task_description: str) -> float:
        """计算工作流与任务描述的匹配度"""
        match_score = 0.0
        
        workflow_name = workflow.get("name", "").lower()
        task_lower = task_description.lower()
        
        if workflow_name in task_lower:
            match_score += 0.3
        
        workflow_description = workflow.get("description", "").lower()
        if workflow_description:
            for word in task_lower.split():
                if word in workflow_description:
                    match_score += 0.1
        
        tags = workflow.get("tags", [])
        for tag in tags:
            if tag.lower() in task_lower:
                match_score += 0.15
        
        steps = workflow.get("steps", [])
        step_names = [step.get("name", "").lower() for step in steps]
        for step_name in step_names:
            if step_name in task_lower:
                match_score += 0.1
        
        return min(match_score, 1.0)
    
    async def get_learning_status(self, agent_name: str = None) -> Dict[str, Any]:
        """获取学习状态"""
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "learning_records": [],
                "assessment_results": []
            }
            
            for key, record in self.learning_records.items():
                if agent_name is None or record["agent_name"] == agent_name:
                    status["learning_records"].append(record)
            
            for key, result in self.assessment_results.items():
                if agent_name is None or result["agent_name"] == agent_name:
                    status["assessment_results"].append(result)
            
            return status
            
        except Exception as e:
            logger.error(f"获取学习状态失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_workflow_learning_report(self, agent_name: str) -> Dict[str, Any]:
        """生成工作流学习报告"""
        try:
            logger.info(f"生成 {agent_name} 的工作流学习报告")
            
            status = await self.get_learning_status(agent_name)
            
            total_workflows = len(status["learning_records"])
            completed_learnings = sum(1 for record in status["learning_records"] if record["learning_status"] == "completed")
            passed_assessments = sum(1 for result in status["assessment_results"] if result["passed"])
            
            confidences = [record["confidence_level"] for record in status["learning_records"]]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            scores = [result["overall_score"] for result in status["assessment_results"]]
            avg_score = sum(scores) / len(scores) if scores else 0.0
            
            report = {
                "agent_name": agent_name,
                "report_time": datetime.now().isoformat(),
                "statistics": {
                    "total_workflows_learned": total_workflows,
                    "completed_learnings": completed_learnings,
                    "passed_assessments": passed_assessments,
                    "avg_confidence_level": avg_confidence,
                    "avg_assessment_score": avg_score
                },
                "learning_records": status["learning_records"],
                "assessment_results": status["assessment_results"]
            }
            
            return {
                "success": True,
                "report": report
            }
            
        except Exception as e:
            logger.error(f"生成工作流学习报告失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }


_global_workflow_learning_system = None


def get_workflow_learning_system() -> WorkflowLearningSystem:
    """获取全局工作流学习系统实例"""
    global _global_workflow_learning_system
    
    if _global_workflow_learning_system is None:
        _global_workflow_learning_system = WorkflowLearningSystem()
    
    return _global_workflow_learning_system


async def initialize_workflow_learning_system():
    """初始化工作流学习系统"""
    system = get_workflow_learning_system()
    logger.info("Workflow learning system initialized")
    return system
