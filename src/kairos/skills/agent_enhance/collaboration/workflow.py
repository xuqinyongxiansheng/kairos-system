#!/usr/bin/env python3
"""
工作流管理
定义和执行复杂的Agent协作工作流
"""

import json
import os
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class WorkflowNode(BaseModel):
    """工作流节点"""
    node_id: str
    name: str
    agent_id: str
    task_description: str
    inputs: List[str] = []
    outputs: List[str] = []
    dependencies: List[str] = []
    parameters: Dict[str, Any] = {}


class Workflow(BaseModel):
    """工作流"""
    workflow_id: str
    name: str
    description: str
    nodes: List[WorkflowNode]
    start_nodes: List[str] = []
    end_nodes: List[str] = []
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


class WorkflowInstance(BaseModel):
    """工作流实例"""
    instance_id: str
    workflow_id: str
    status: str = "pending"  # pending, running, completed, failed
    node_status: Dict[str, str] = {}
    results: Dict[str, Any] = {}
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_time: Optional[float] = None


class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self, storage_path: str = "data/workflows"):
        self.storage_path = storage_path
        self.workflows: Dict[str, Workflow] = {}
        self.instances: Dict[str, WorkflowInstance] = {}
        self._load_workflows()
    
    def _load_workflows(self):
        """加载工作流"""
        try:
            if os.path.exists(self.storage_path):
                for filename in os.listdir(self.storage_path):
                    if filename.endswith(".json"):
                        with open(os.path.join(self.storage_path, filename), 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            workflow = Workflow(**data)
                            self.workflows[workflow.workflow_id] = workflow
        except Exception as e:
            logger.error(f"加载工作流失败: {e}")
    
    def _save_workflow(self, workflow: Workflow):
        """保存工作流"""
        try:
            os.makedirs(self.storage_path, exist_ok=True)
            filename = f"{workflow.workflow_id}.json"
            with open(os.path.join(self.storage_path, filename), 'w', encoding='utf-8') as f:
                json.dump(workflow.model_dump(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存工作流失败: {e}")
    
    def create_workflow(self, name: str, description: str, nodes: List[WorkflowNode],
                      start_nodes: List[str] = None, end_nodes: List[str] = None) -> Workflow:
        """创建工作流"""
        workflow_id = str(uuid.uuid4())
        workflow = Workflow(
            workflow_id=workflow_id,
            name=name,
            description=description,
            nodes=nodes,
            start_nodes=start_nodes or [],
            end_nodes=end_nodes or []
        )
        self.workflows[workflow_id] = workflow
        self._save_workflow(workflow)
        logger.info(f"创建工作流: {workflow_id} - {name}")
        return workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """获取工作流"""
        return self.workflows.get(workflow_id)
    
    def list_workflows(self) -> List[Workflow]:
        """列出工作流"""
        return list(self.workflows.values())
    
    def update_workflow(self, workflow_id: str, **kwargs) -> Optional[Workflow]:
        """更新工作流"""
        if workflow_id in self.workflows:
            workflow = self.workflows[workflow_id]
            for key, value in kwargs.items():
                if hasattr(workflow, key):
                    setattr(workflow, key, value)
            workflow.updated_at = datetime.now()
            self._save_workflow(workflow)
            logger.info(f"更新工作流: {workflow_id}")
            return workflow
        return None
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """删除工作流"""
        if workflow_id in self.workflows:
            del self.workflows[workflow_id]
            # 删除文件
            filename = f"{workflow_id}.json"
            file_path = os.path.join(self.storage_path, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            logger.info(f"删除工作流: {workflow_id}")
            return True
        return False
    
    async def execute_workflow(self, workflow_id: str, context: Dict[str, Any] = None) -> str:
        """执行工作流"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"工作流 {workflow_id} 不存在")
        
        # 创建工作流实例
        instance_id = str(uuid.uuid4())
        instance = WorkflowInstance(
            instance_id=instance_id,
            workflow_id=workflow_id,
            node_status={node.node_id: "pending" for node in workflow.nodes},
            start_time=datetime.now()
        )
        self.instances[instance_id] = instance
        
        logger.info(f"开始执行工作流: {workflow_id} - 实例: {instance_id}")
        
        # 执行工作流
        asyncio.create_task(self._execute_workflow_instance(instance))
        
        return instance_id
    
    async def _execute_workflow_instance(self, instance: WorkflowInstance):
        """执行工作流实例"""
        workflow = self.get_workflow(instance.workflow_id)
        if not workflow:
            instance.status = "failed"
            instance.end_time = datetime.now()
            return
        
        instance.status = "running"
        
        # 拓扑排序
        sorted_nodes = self._topological_sort(workflow)
        
        # 执行节点
        for node in sorted_nodes:
            instance.node_status[node.node_id] = "in_progress"
            
            try:
                # 这里应该调用Agent执行任务
                # 简化示例
                result = {
                    "status": "success",
                    "message": f"执行节点 {node.name} 成功"
                }
                
                instance.results[node.node_id] = result
                instance.node_status[node.node_id] = "completed"
                
                logger.info(f"节点执行完成: {node.name}")
                
            except Exception as e:
                instance.results[node.node_id] = {
                    "status": "error",
                    "error": str(e)
                }
                instance.node_status[node.node_id] = "failed"
                instance.status = "failed"
                logger.error(f"节点执行失败: {node.name} - {e}")
                break
        
        # 完成工作流
        if instance.status == "running":
            instance.status = "completed"
        
        instance.end_time = datetime.now()
        instance.total_time = (instance.end_time - instance.start_time).total_seconds()
        
        logger.info(f"工作流执行完成: {instance.instance_id}, 状态: {instance.status}, 耗时: {instance.total_time:.2f}秒")
    
    def _topological_sort(self, workflow: Workflow) -> List[WorkflowNode]:
        """拓扑排序"""
        # 构建依赖图
        dependencies = {node.node_id: node.dependencies for node in workflow.nodes}
        
        # 计算入度
        in_degree = {node.node_id: 0 for node in workflow.nodes}
        for node_id, deps in dependencies.items():
            for dep in deps:
                in_degree[dep] += 1
        
        # 初始化队列
        queue = [node for node in workflow.nodes if in_degree[node.node_id] == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            # 减少依赖节点的入度
            for dep in node.dependencies:
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    # 找到对应的节点
                    for n in workflow.nodes:
                        if n.node_id == dep:
                            queue.append(n)
                            break
        
        return result
    
    def get_instance(self, instance_id: str) -> Optional[WorkflowInstance]:
        """获取工作流实例"""
        return self.instances.get(instance_id)
    
    def list_instances(self, workflow_id: Optional[str] = None) -> List[WorkflowInstance]:
        """列出工作流实例"""
        if workflow_id:
            return [instance for instance in self.instances.values() 
                   if instance.workflow_id == workflow_id]
        return list(self.instances.values())
    
    def cancel_instance(self, instance_id: str) -> bool:
        """取消工作流实例"""
        if instance_id in self.instances:
            self.instances[instance_id].status = "cancelled"
            self.instances[instance_id].end_time = datetime.now()
            logger.info(f"取消工作流实例: {instance_id}")
            return True
        return False
    
    def cleanup_instances(self) -> int:
        """清理已完成的工作流实例"""
        completed = []
        for instance_id, instance in self.instances.items():
            if instance.status in ["completed", "failed", "cancelled"]:
                completed.append(instance_id)
        
        for instance_id in completed:
            del self.instances[instance_id]
        
        logger.info(f"清理了 {len(completed)} 个工作流实例")
        return len(completed)


# 全局工作流引擎实例
_workflow_engine = None

def get_workflow_engine() -> WorkflowEngine:
    """获取工作流引擎实例"""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
    return _workflow_engine


if __name__ == "__main__":
    # 测试
    import asyncio
    
    async def test_workflow():
        engine = get_workflow_engine()
        
        # 创建工作流
        nodes = [
            WorkflowNode(
                node_id="node1",
                name="数据收集",
                agent_id="data_agent",
                task_description="收集销售数据",
                outputs=["sales_data"]
            ),
            WorkflowNode(
                node_id="node2",
                name="数据分析",
                agent_id="data_agent",
                task_description="分析销售数据",
                inputs=["sales_data"],
                outputs=["analysis_result"],
                dependencies=["node1"]
            ),
            WorkflowNode(
                node_id="node3",
                name="生成报告",
                agent_id="content_agent",
                task_description="生成销售报告",
                inputs=["analysis_result"],
                dependencies=["node2"]
            )
        ]
        
        workflow = engine.create_workflow(
            name="销售数据分析",
            description="分析销售数据并生成报告",
            nodes=nodes,
            start_nodes=["node1"],
            end_nodes=["node3"]
        )
        
        print(f"创建工作流: {workflow.workflow_id}")
        
        # 执行工作流
        instance_id = await engine.execute_workflow(workflow.workflow_id)
        print(f"执行工作流实例: {instance_id}")
        
        # 等待执行完成
        await asyncio.sleep(3)
        
        # 获取实例状态
        instance = engine.get_instance(instance_id)
        if instance:
            print(f"工作流状态: {instance.status}")
            print(f"节点状态: {instance.node_status}")
            print(f"执行结果: {instance.results}")
    
    asyncio.run(test_workflow())