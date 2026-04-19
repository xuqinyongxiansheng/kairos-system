#!/usr/bin/env python3
"""
工作流编辑器
实现可视化工作流编辑器，支持复杂业务流程定义
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime


class WorkflowNodeType:
    """工作流节点类型"""
    START = "start"
    END = "end"
    ACTION = "action"
    DECISION = "decision"
    LOOP = "loop"
    PARALLEL = "parallel"


class WorkflowNode:
    """工作流节点"""
    
    def __init__(self, node_id: str, node_type: str, name: str, 
                 properties: Dict[str, Any] = None, 
                 next_nodes: List[str] = None):
        self.node_id = node_id
        self.node_type = node_type
        self.name = name
        self.properties = properties or {}
        self.next_nodes = next_nodes or []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "name": self.name,
            "properties": self.properties,
            "next_nodes": self.next_nodes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowNode":
        """从字典创建"""
        return cls(
            node_id=data["node_id"],
            node_type=data["node_type"],
            name=data["name"],
            properties=data.get("properties", {}),
            next_nodes=data.get("next_nodes", [])
        )


class Workflow:
    """工作流"""
    
    def __init__(self, workflow_id: str, name: str, description: str = "",
                 nodes: List[WorkflowNode] = None, 
                 start_node: str = None):
        self.workflow_id = workflow_id
        self.name = name
        self.description = description
        self.nodes = nodes or []
        self.start_node = start_node
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "nodes": [node.to_dict() for node in self.nodes],
            "start_node": self.start_node,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workflow":
        """从字典创建"""
        workflow = cls(
            workflow_id=data["workflow_id"],
            name=data["name"],
            description=data.get("description", ""),
            nodes=[WorkflowNode.from_dict(node) for node in data.get("nodes", [])],
            start_node=data.get("start_node")
        )
        if "created_at" in data:
            workflow.created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            workflow.updated_at = datetime.fromisoformat(data["updated_at"])
        return workflow
    
    def add_node(self, node: WorkflowNode):
        """添加节点"""
        self.nodes.append(node)
        self.updated_at = datetime.now()
    
    def remove_node(self, node_id: str):
        """移除节点"""
        self.nodes = [node for node in self.nodes if node.node_id != node_id]
        # 更新其他节点的next_nodes
        for node in self.nodes:
            node.next_nodes = [nid for nid in node.next_nodes if nid != node_id]
        self.updated_at = datetime.now()
    
    def update_node(self, node_id: str, **kwargs):
        """更新节点"""
        for node in self.nodes:
            if node.node_id == node_id:
                if "name" in kwargs:
                    node.name = kwargs["name"]
                if "properties" in kwargs:
                    node.properties = kwargs["properties"]
                if "next_nodes" in kwargs:
                    node.next_nodes = kwargs["next_nodes"]
                self.updated_at = datetime.now()
                return True
        return False
    
    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        """获取节点"""
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None
    
    def validate(self) -> Dict[str, Any]:
        """验证工作流"""
        errors = []
        
        # 检查是否有开始节点
        if not self.start_node:
            errors.append("工作流必须有开始节点")
        
        # 检查开始节点是否存在
        if self.start_node:
            if not self.get_node(self.start_node):
                errors.append(f"开始节点 {self.start_node} 不存在")
        
        # 检查所有节点的next_nodes是否存在
        for node in self.nodes:
            for next_node_id in node.next_nodes:
                if not self.get_node(next_node_id):
                    errors.append(f"节点 {node.node_id} 的下一节点 {next_node_id} 不存在")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }


class WorkflowEditor:
    """工作流编辑器"""
    
    def __init__(self, storage_path: str = "data/workflows"):
        self.storage_path = storage_path
        self.workflows: Dict[str, Workflow] = {}
        self._load_workflows()
        os.makedirs(self.storage_path, exist_ok=True)
    
    def _load_workflows(self):
        """加载工作流"""
        try:
            if os.path.exists(self.storage_path):
                for filename in os.listdir(self.storage_path):
                    if filename.endswith(".json"):
                        file_path = os.path.join(self.storage_path, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            workflow = Workflow.from_dict(data)
                            self.workflows[workflow.workflow_id] = workflow
        except Exception as e:
            print(f"加载工作流失败: {e}")
    
    def create_workflow(self, name: str, description: str = "") -> Workflow:
        """创建工作流"""
        workflow_id = f"workflow_{int(datetime.now().timestamp() * 1000)}"
        workflow = Workflow(
            workflow_id=workflow_id,
            name=name,
            description=description
        )
        self.workflows[workflow_id] = workflow
        self._save_workflow(workflow)
        return workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """获取工作流"""
        return self.workflows.get(workflow_id)
    
    def list_workflows(self) -> List[Workflow]:
        """列出工作流"""
        return list(self.workflows.values())
    
    def update_workflow(self, workflow_id: str, **kwargs) -> bool:
        """更新工作流"""
        if workflow_id not in self.workflows:
            return False
        
        workflow = self.workflows[workflow_id]
        if "name" in kwargs:
            workflow.name = kwargs["name"]
        if "description" in kwargs:
            workflow.description = kwargs["description"]
        if "start_node" in kwargs:
            workflow.start_node = kwargs["start_node"]
        workflow.updated_at = datetime.now()
        
        self._save_workflow(workflow)
        return True
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """删除工作流"""
        if workflow_id not in self.workflows:
            return False
        
        # 删除文件
        file_path = os.path.join(self.storage_path, f"{workflow_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
        
        del self.workflows[workflow_id]
        return True
    
    def add_node(self, workflow_id: str, node: WorkflowNode) -> bool:
        """添加节点"""
        if workflow_id not in self.workflows:
            return False
        
        workflow = self.workflows[workflow_id]
        workflow.add_node(node)
        self._save_workflow(workflow)
        return True
    
    def remove_node(self, workflow_id: str, node_id: str) -> bool:
        """移除节点"""
        if workflow_id not in self.workflows:
            return False
        
        workflow = self.workflows[workflow_id]
        workflow.remove_node(node_id)
        self._save_workflow(workflow)
        return True
    
    def update_node(self, workflow_id: str, node_id: str, **kwargs) -> bool:
        """更新节点"""
        if workflow_id not in self.workflows:
            return False
        
        workflow = self.workflows[workflow_id]
        result = workflow.update_node(node_id, **kwargs)
        if result:
            self._save_workflow(workflow)
        return result
    
    def validate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """验证工作流"""
        if workflow_id not in self.workflows:
            return {"valid": False, "errors": ["工作流不存在"]}
        
        workflow = self.workflows[workflow_id]
        return workflow.validate()
    
    def _save_workflow(self, workflow: Workflow):
        """保存工作流"""
        try:
            file_path = os.path.join(self.storage_path, f"{workflow.workflow_id}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(workflow.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存工作流失败: {e}")


# 全局工作流编辑器实例
_workflow_editor = None

def get_workflow_editor() -> WorkflowEditor:
    """获取工作流编辑器实例"""
    global _workflow_editor
    if _workflow_editor is None:
        _workflow_editor = WorkflowEditor()
    return _workflow_editor


if __name__ == "__main__":
    # 测试
    editor = get_workflow_editor()
    
    # 创建工作流
    workflow = editor.create_workflow("测试工作流", "这是一个测试工作流")
    print(f"创建工作流: {workflow.workflow_id}")
    
    # 添加节点
    start_node = WorkflowNode(
        node_id="start",
        node_type=WorkflowNodeType.START,
        name="开始",
        next_nodes=["action1"]
    )
    action_node = WorkflowNode(
        node_id="action1",
        node_type=WorkflowNodeType.ACTION,
        name="执行操作",
        properties={"action": "print('Hello')"},
        next_nodes=["end"]
    )
    end_node = WorkflowNode(
        node_id="end",
        node_type=WorkflowNodeType.END,
        name="结束"
    )
    
    editor.add_node(workflow.workflow_id, start_node)
    editor.add_node(workflow.workflow_id, action_node)
    editor.add_node(workflow.workflow_id, end_node)
    
    # 设置开始节点
    editor.update_workflow(workflow.workflow_id, start_node="start")
    
    # 验证工作流
    validation = editor.validate_workflow(workflow.workflow_id)
    print(f"工作流验证: {validation}")
    
    # 列出工作流
    workflows = editor.list_workflows()
    print(f"工作流列表: {[w.name for w in workflows]}")