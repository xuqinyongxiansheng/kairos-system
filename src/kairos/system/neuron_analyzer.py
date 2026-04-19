"""神经元节点分析模块 - 标记神经元节点并分析工作流"""

import os
import re
import json
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime

logger = logging.getLogger("NeuronAnalyzer")


class NeuronNode:
    """神经元节点类"""
    
    def __init__(self, node_id: str, node_type: str, name: str, properties: Dict[str, Any] = None):
        """初始化神经元节点"""
        self.node_id = node_id
        self.node_type = node_type
        self.name = name
        self.properties = properties or {}
        self.created_at = datetime.now().isoformat()
        self.connections: List[str] = []
    
    def add_connection(self, target_node_id: str):
        """添加节点连接"""
        if target_node_id not in self.connections:
            self.connections.append(target_node_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'node_id': self.node_id,
            'node_type': self.node_type,
            'name': self.name,
            'properties': self.properties,
            'connections': self.connections,
            'created_at': self.created_at
        }


class NeuronConnection:
    """神经元连接类"""
    
    def __init__(self, source_node_id: str, target_node_id: str, connection_type: str, properties: Dict[str, Any] = None):
        """初始化神经元连接"""
        self.source_node_id = source_node_id
        self.target_node_id = target_node_id
        self.connection_type = connection_type
        self.properties = properties or {}
        self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'source_node_id': self.source_node_id,
            'target_node_id': self.target_node_id,
            'connection_type': self.connection_type,
            'properties': self.properties,
            'created_at': self.created_at
        }


class NeuronWorkflow:
    """神经元工作流类"""
    
    def __init__(self, workflow_id: str, workflow_name: str, nodes: List[NeuronNode], connections: List[NeuronConnection]):
        """初始化神经元工作流"""
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.nodes = nodes
        self.connections = connections
        self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'workflow_id': self.workflow_id,
            'workflow_name': self.workflow_name,
            'nodes': [node.to_dict() for node in self.nodes],
            'connections': [conn.to_dict() for conn in self.connections],
            'created_at': self.created_at
        }


class NeuronAnalyzer:
    """神经元节点分析器"""
    
    def __init__(self):
        """初始化神经元分析器"""
        self.nodes: Dict[str, NeuronNode] = {}
        self.connections: List[NeuronConnection] = []
        self.workflows: Dict[str, NeuronWorkflow] = {}
    
    def create_node(self, node_type: str, name: str, properties: Dict[str, Any] = None) -> NeuronNode:
        """创建神经元节点"""
        node_id = f"neuron_{int(datetime.now().timestamp() * 1000)}"
        node = NeuronNode(node_id, node_type, name, properties)
        self.nodes[node_id] = node
        logger.info(f"创建神经元节点: {node_type} - {name}")
        return node
    
    def create_connection(self, source_node_id: str, target_node_id: str, connection_type: str, properties: Dict[str, Any] = None) -> Optional[NeuronConnection]:
        """创建神经元连接"""
        if source_node_id not in self.nodes or target_node_id not in self.nodes:
            logger.error("源节点或目标节点不存在")
            return None
        
        connection = NeuronConnection(source_node_id, target_node_id, connection_type, properties)
        self.connections.append(connection)
        
        source_node = self.nodes[source_node_id]
        source_node.add_connection(target_node_id)
        
        logger.info(f"创建神经元连接: {source_node_id} -> {target_node_id}")
        return connection
    
    def get_node(self, node_id: str) -> Optional[NeuronNode]:
        """获取神经元节点"""
        return self.nodes.get(node_id)
    
    def get_nodes_by_type(self, node_type: str) -> List[NeuronNode]:
        """根据类型获取神经元节点"""
        return [node for node in self.nodes.values() if node.node_type == node_type]
    
    def get_connections(self, source_node_id: Optional[str] = None, target_node_id: Optional[str] = None) -> List[NeuronConnection]:
        """获取神经元连接"""
        connections = self.connections
        if source_node_id:
            connections = [conn for conn in connections if conn.source_node_id == source_node_id]
        if target_node_id:
            connections = [conn for conn in connections if conn.target_node_id == target_node_id]
        return connections
    
    def analyze_workflow(self, workflow_name: str) -> NeuronWorkflow:
        """分析神经元节点之间的工作流"""
        workflow_id = f"workflow_{int(datetime.now().timestamp() * 1000)}"
        
        workflow_nodes = list(self.nodes.values())
        workflow_connections = self.connections.copy()
        
        workflow = NeuronWorkflow(workflow_id, workflow_name, workflow_nodes, workflow_connections)
        self.workflows[workflow_id] = workflow
        
        logger.info(f"创建神经元工作流: {workflow_name}")
        return workflow
    
    def find_paths(self, start_node_id: str, end_node_id: str) -> List[List[str]]:
        """查找两个节点之间的路径"""
        paths = []
        
        def dfs(current_node_id: str, visited: Set[str], path: List[str]):
            if current_node_id == end_node_id:
                paths.append(path.copy())
                return
            
            visited.add(current_node_id)
            current_node = self.nodes.get(current_node_id)
            
            if current_node:
                for connection in self.connections:
                    if connection.source_node_id == current_node_id and connection.target_node_id not in visited:
                        path.append(connection.target_node_id)
                        dfs(connection.target_node_id, visited, path)
                        path.pop()
            
            visited.remove(current_node_id)
        
        if start_node_id in self.nodes and end_node_id in self.nodes:
            dfs(start_node_id, set(), [start_node_id])
        
        return paths
    
    def analyze_node_interactions(self, node_id: str) -> Optional[Dict[str, Any]]:
        """分析节点的交互情况"""
        node = self.get_node(node_id)
        if not node:
            return None
        
        incoming_connections = self.get_connections(target_node_id=node_id)
        outgoing_connections = self.get_connections(source_node_id=node_id)
        
        return {
            'node_id': node_id,
            'node_type': node.node_type,
            'name': node.name,
            'incoming_count': len(incoming_connections),
            'outgoing_count': len(outgoing_connections),
            'incoming_connections': [conn.to_dict() for conn in incoming_connections],
            'outgoing_connections': [conn.to_dict() for conn in outgoing_connections],
            'properties': node.properties
        }
    
    def export_workflows(self, export_path: str) -> bool:
        """导出工作流数据"""
        try:
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'nodes': [node.to_dict() for node in self.nodes.values()],
                'connections': [conn.to_dict() for conn in self.connections],
                'workflows': [workflow.to_dict() for workflow in self.workflows.values()]
            }
            
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功导出神经元工作流到 {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出神经元工作流失败: {e}")
            return False
    
    def import_workflows(self, import_path: str) -> bool:
        """导入工作流数据"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            for node_data in import_data.get('nodes', []):
                node = NeuronNode(
                    node_id=node_data['node_id'],
                    node_type=node_data['node_type'],
                    name=node_data['name'],
                    properties=node_data['properties']
                )
                node.connections = node_data['connections']
                node.created_at = node_data['created_at']
                self.nodes[node.node_id] = node
            
            for conn_data in import_data.get('connections', []):
                connection = NeuronConnection(
                    source_node_id=conn_data['source_node_id'],
                    target_node_id=conn_data['target_node_id'],
                    connection_type=conn_data['connection_type'],
                    properties=conn_data['properties']
                )
                connection.created_at = conn_data['created_at']
                self.connections.append(connection)
            
            for workflow_data in import_data.get('workflows', []):
                nodes = []
                for node_data in workflow_data['nodes']:
                    node = NeuronNode(
                        node_id=node_data['node_id'],
                        node_type=node_data['node_type'],
                        name=node_data['name'],
                        properties=node_data['properties']
                    )
                    node.connections = node_data['connections']
                    node.created_at = node_data['created_at']
                    nodes.append(node)
                
                connections = []
                for conn_data in workflow_data['connections']:
                    connection = NeuronConnection(
                        source_node_id=conn_data['source_node_id'],
                        target_node_id=conn_data['target_node_id'],
                        connection_type=conn_data['connection_type'],
                        properties=conn_data['properties']
                    )
                    connection.created_at = conn_data['created_at']
                    connections.append(connection)
                
                workflow = NeuronWorkflow(
                    workflow_id=workflow_data['workflow_id'],
                    workflow_name=workflow_data['workflow_name'],
                    nodes=nodes,
                    connections=connections
                )
                workflow.created_at = workflow_data['created_at']
                self.workflows[workflow.workflow_id] = workflow
            
            logger.info(f"成功导入 {len(self.nodes)} 个节点和 {len(self.connections)} 个连接")
            return True
            
        except Exception as e:
            logger.error(f"导入神经元工作流失败: {e}")
            return False
    
    def get_network_statistics(self) -> Dict[str, Any]:
        """获取网络统计信息"""
        node_types = {}
        for node in self.nodes.values():
            node_types[node.node_type] = node_types.get(node.node_type, 0) + 1
        
        connection_types = {}
        for conn in self.connections:
            connection_types[conn.connection_type] = connection_types.get(conn.connection_type, 0) + 1
        
        return {
            'total_nodes': len(self.nodes),
            'total_connections': len(self.connections),
            'total_workflows': len(self.workflows),
            'node_types': node_types,
            'connection_types': connection_types
        }


neuron_analyzer = NeuronAnalyzer()


def get_neuron_analyzer() -> NeuronAnalyzer:
    """获取神经元分析器实例"""
    return neuron_analyzer
