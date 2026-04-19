"""
工作流系统
管理工作流的创建、保存和执行
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """工作流状态"""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPLETED = "completed"


@dataclass
class WorkflowStep:
    """工作流步骤"""
    name: str
    action: str
    parameters: Dict[str, Any] = None
    condition: Optional[str] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class Workflow:
    """工作流"""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    status: WorkflowStatus = WorkflowStatus.DRAFT
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'steps': [asdict(s) for s in self.steps],
            'status': self.status.value,
            'created_at': self.created_at
        }


class WorkflowManager:
    """工作流管理器"""
    
    def __init__(self):
        self.workflows = {}
        self.workflow_history = []
        self.next_id = 1
    
    async def create_workflow(self, name: str, description: str, 
                             steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建工作流"""
        workflow_id = f"workflow_{self.next_id}"
        self.next_id += 1
        
        workflow_steps = [
            WorkflowStep(
                name=step.get('name', ''),
                action=step.get('action', ''),
                parameters=step.get('parameters', {}),
                condition=step.get('condition')
            )
            for step in steps
        ]
        
        workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description,
            steps=workflow_steps
        )
        
        self.workflows[workflow_id] = workflow
        
        logger.info(f"工作流创建：{name}")
        
        return {
            'status': 'success',
            'workflow_id': workflow_id,
            'workflow': workflow.to_dict()
        }
    
    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """执行工作流"""
        if workflow_id not in self.workflows:
            return {
                'status': 'error',
                'error': f'工作流不存在：{workflow_id}'
            }
        
        workflow = self.workflows[workflow_id]
        results = []
        
        for step in workflow.steps:
            step_result = await self._execute_step(step)
            results.append(step_result)
            
            if not step_result.get('success', False):
                break
        
        workflow.status = WorkflowStatus.COMPLETED
        
        self.workflow_history.append({
            'workflow_id': workflow_id,
            'executed_at': datetime.now().isoformat(),
            'results': results
        })
        
        return {
            'status': 'success',
            'workflow_id': workflow_id,
            'results': results
        }
    
    async def _execute_step(self, step: WorkflowStep) -> Dict[str, Any]:
        """执行步骤"""
        logger.info(f"执行步骤：{step.name}")
        
        return {
            'step': step.name,
            'action': step.action,
            'success': True,
            'timestamp': datetime.now().isoformat()
        }
    
    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """获取工作流"""
        if workflow_id not in self.workflows:
            return {
                'status': 'not_found',
                'message': f'工作流不存在：{workflow_id}'
            }
        
        return {
            'status': 'success',
            'workflow': self.workflows[workflow_id].to_dict()
        }
    
    async def list_workflows(self) -> Dict[str, Any]:
        """列出工作流"""
        workflows = [
            wf.to_dict() for wf in self.workflows.values()
        ]
        
        return {
            'status': 'success',
            'workflows': workflows,
            'count': len(workflows)
        }
    
    async def get_workflow_summary(self) -> Dict[str, Any]:
        """获取工作流摘要"""
        return {
            'status': 'success',
            'total_workflows': len(self.workflows),
            'total_executions': len(self.workflow_history)
        }
