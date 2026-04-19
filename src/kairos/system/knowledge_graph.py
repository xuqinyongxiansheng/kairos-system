"""
知识图谱系统
基于 NetworkX 实现知识存储和关联学习
整合 002/AAagent 的优秀实现
"""

import networkx as nx
import json
import os
import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """节点类型枚举"""
    AGENT = "agent"
    TOOL = "tool"
    LEARNING = "learning"
    REPOSITORY = "repository"
    KNOWLEDGE = "knowledge"
    CONCEPT = "concept"
    SKILL = "skill"
    SYSTEM = "system"


class RelationshipType(Enum):
    """关系类型枚举"""
    PERFORMED_BY = "performed_by"
    PRODUCED = "produced"
    SOURCED_FROM = "sourced_from"
    RELATED_TO = "related_to"
    PART_OF = "part_of"
    USES = "uses"
    LEARNED_FROM = "learned_from"
    HOSTED_ON = "hosted_on"
    DEPENDS_ON = "depends_on"
    EXTENDS = "extends"


@dataclass
class KnowledgeNode:
    """知识节点数据类"""
    id: str
    type: NodeType
    name: str
    description: str
    attributes: Dict[str, Any]
    created_at: datetime.datetime


@dataclass
class KnowledgeRelationship:
    """知识关系数据类"""
    source_id: str
    target_id: str
    type: RelationshipType
    weight: float
    attributes: Dict[str, Any]
    created_at: datetime.datetime


class KnowledgeGraph:
    """知识图谱主类"""
    
    def __init__(self, graph_file: str = "./data/knowledge_graph.json"):
        self.graph_file = graph_file
        self.graph = self._init_graph()
        self.node_counter = 0
        self._dirty = False
        self._save_interval = 5
        self._operation_count = 0
        
        os.makedirs(os.path.dirname(graph_file) if os.path.dirname(graph_file) else ".", exist_ok=True)
        
        self._load_graph()
        self._add_initial_nodes()
        self._flush_save()
        
        logger.info("知识图谱初始化完成")
    
    def _init_graph(self) -> nx.DiGraph:
        return nx.DiGraph()
    
    def _graph_to_json(self) -> Dict[str, Any]:
        """将图转换为JSON可序列化格式"""
        nodes = []
        for node_id, node_data in self.graph.nodes(data=True):
            node_entry = {"id": node_id}
            node_entry.update(node_data)
            nodes.append(node_entry)
        
        edges = []
        for u, v, edge_data in self.graph.edges(data=True):
            edge_entry = {"source": u, "target": v}
            edge_entry.update(edge_data)
            edges.append(edge_entry)
        
        return {
            "nodes": nodes,
            "edges": edges,
            "node_counter": self.node_counter
        }
    
    def _json_to_graph(self, data: Dict[str, Any]):
        """从JSON数据恢复图"""
        self.graph.clear()
        self.node_counter = data.get("node_counter", 0)
        
        for node in data.get("nodes", []):
            node_id = node.pop("id")
            self.graph.add_node(node_id, **node)
        
        for edge in data.get("edges", []):
            source = edge.pop("source")
            target = edge.pop("target")
            self.graph.add_edge(source, target, **edge)
    
    def _load_graph(self):
        """从文件加载知识图谱"""
        json_file = self.graph_file.replace('.pkl', '.json') if self.graph_file.endswith('.pkl') else self.graph_file
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._json_to_graph(data)
                logger.info(f"知识图谱加载成功，节点数：{len(self.graph.nodes)}, 边数：{len(self.graph.edges)}")
            except Exception as e:
                logger.error(f"加载知识图谱失败：{e}")
    
    def _save_graph(self):
        self._dirty = True
        self._operation_count += 1
        if self._operation_count >= self._save_interval:
            self._flush_save()
    
    def _flush_save(self):
        if not self._dirty:
            return
        try:
            json_file = self.graph_file.replace('.pkl', '.json') if self.graph_file.endswith('.pkl') else self.graph_file
            os.makedirs(os.path.dirname(json_file) if os.path.dirname(json_file) else ".", exist_ok=True)
            data = self._graph_to_json()
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._dirty = False
            self._operation_count = 0
            logger.debug("知识图谱已保存")
        except Exception as e:
            logger.error(f"保存知识图谱失败：{e}")
    
    def _add_initial_nodes(self):
        """添加初始节点"""
        if "system_core" not in self.graph.nodes:
            self.add_node(
                node_type=NodeType.SYSTEM,
                name="系统核心",
                description="系统核心模块",
                attributes={"version": "1.0", "type": "core"}
            )
    
    def add_node(self, node_type: NodeType, name: str, description: str, 
                 attributes: Dict[str, Any] = None) -> str:
        existing = self.find_node_by_name_and_type(name, node_type)
        if existing:
            return existing
        
        node_id = f"{node_type.value}_{self.node_counter}"
        self.node_counter += 1
        
        node_data = {
            "type": node_type.value,
            "name": name,
            "description": description,
            "attributes": attributes or {},
            "created_at": datetime.datetime.now().isoformat()
        }
        
        self.graph.add_node(node_id, **node_data)
        self._save_graph()
        
        logger.info(f"添加节点：{name} ({node_id})")
        return node_id
    
    def find_node_by_name_and_type(self, name: str, node_type: NodeType) -> Optional[str]:
        for node_id, data in self.graph.nodes(data=True):
            if data.get("name") == name and data.get("type") == node_type.value:
                return node_id
        return None
    
    def add_relationship(self, source_id: str, target_id: str, 
                        relationship_type: RelationshipType, 
                        weight: float = 1.0, attributes: Dict[str, Any] = None) -> bool:
        """添加知识关系"""
        if source_id in self.graph.nodes and target_id in self.graph.nodes:
            edge_data = {
                "type": relationship_type.value,
                "weight": weight,
                "attributes": attributes or {},
                "created_at": datetime.datetime.now().isoformat()
            }
            
            self.graph.add_edge(source_id, target_id, **edge_data)
            self._save_graph()
            
            logger.info(f"添加关系：{source_id} -> {target_id} ({relationship_type.value})")
            return True
        
        logger.warning(f"添加关系失败：节点不存在")
        return False
    
    def add_learning_experience(self, experience: Dict[str, Any]):
        """添加学习经验到知识图谱"""
        learning_id = self.add_node(
            node_type=NodeType.LEARNING,
            name=f"学习_{experience.get('need_description', '未知')[:20]}",
            description=experience.get("need_description", ""),
            attributes={
                "success_rate": experience.get("success_rate", 0),
                "timestamp": experience.get("timestamp", "")
            }
        )
        
        system_node = self.get_node_by_name("系统核心", NodeType.SYSTEM)
        if system_node:
            self.add_relationship(
                source_id=learning_id,
                target_id=system_node,
                relationship_type=RelationshipType.PERFORMED_BY,
                weight=1.0
            )
        
        for tool_data in experience.get("learned_tools", []):
            tool_name = tool_data.get("tool_name", "unknown")
            source_repo = tool_data.get("source_repo", "unknown")
            
            tool_id = self.add_node(
                node_type=NodeType.TOOL,
                name=tool_name,
                description=tool_data.get("description", ""),
                attributes={
                    "source": source_repo,
                    "version": tool_data.get("version", "1.0")
                }
            )
            
            self.add_relationship(
                source_id=learning_id,
                target_id=tool_id,
                relationship_type=RelationshipType.PRODUCED,
                weight=0.8
            )
            
            if source_repo != "unknown":
                repo_id = self.add_node(
                    node_type=NodeType.REPOSITORY,
                    name=source_repo,
                    description=f"GitHub 仓库：{source_repo}",
                    attributes={"type": "github"}
                )
                
                self.add_relationship(
                    source_id=tool_id,
                    target_id=repo_id,
                    relationship_type=RelationshipType.SOURCED_FROM,
                    weight=0.9
                )
    
    def query_related_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """查询相关知识"""
        related_nodes = []
        
        for node_id, node_data in self.graph.nodes(data=True):
            search_text = f"{node_data.get('name', '')} {node_data.get('description', '')}".lower()
            
            if query.lower() in search_text:
                neighbors = []
                for neighbor_id in self.graph.neighbors(node_id):
                    edge_data = self.graph.get_edge_data(node_id, neighbor_id)
                    neighbors.append({
                        "node_id": neighbor_id,
                        "node_data": self.graph.nodes[neighbor_id],
                        "relationship": edge_data
                    })
                
                related_nodes.append({
                    "node_id": node_id,
                    "node_data": node_data,
                    "neighbors": neighbors
                })
        
        return related_nodes
    
    def search_by_type(self, node_type: NodeType) -> List[Dict[str, Any]]:
        """按类型搜索节点"""
        nodes = []
        
        for node_id, node_data in self.graph.nodes(data=True):
            if node_data.get("type") == node_type.value:
                nodes.append({
                    "node_id": node_id,
                    "node_data": node_data
                })
        
        return nodes
    
    def find_path_between(self, source_id: str, target_id: str) -> Optional[List[str]]:
        """查找两个节点之间的路径"""
        try:
            path = nx.shortest_path(self.graph, source=source_id, target=target_id)
            return path
        except nx.NetworkXNoPath:
            return None
    
    def suggest_learning_path(self, current_need: str) -> List[str]:
        """建议学习路径"""
        suggestions = []
        
        learning_nodes = self.search_by_type(NodeType.LEARNING)
        keywords = self._extract_keywords(current_need)
        
        related_tools = []
        for keyword in keywords:
            related = self.query_related_knowledge(keyword)
            for item in related:
                if item["node_data"].get("type") == NodeType.TOOL.value:
                    related_tools.append(item)
        
        if related_tools:
            suggestions.append(f"1. 搜索与'{current_need}'相关的 Python 库")
            for i, tool in enumerate(related_tools[:3], 2):
                tool_name = tool["node_data"].get("name", "未知工具")
                suggestions.append(f"{i}. 学习使用工具：{tool_name}")
            suggestions.append(f"{len(suggestions) + 1}. 将新工具集成到系统")
            suggestions.append(f"{len(suggestions) + 1}. 记录学习经验到知识图谱")
        else:
            suggestions = [
                f"1. 搜索与'{current_need}'相关的 Python 库",
                "2. 分析代码结构和功能",
                "3. 测试核心功能的正确性",
                "4. 集成到系统中",
                "5. 记录学习经验到知识图谱"
            ]
        
        return suggestions
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        import re
        words = re.findall(r'[\u4e00-\u9fa5]+|\w+', text)
        stop_words = {"的", "了", "和", "是", "在", "有", "我", "你", "他", "这", "那"}
        keywords = [word for word in words if len(word) > 1 and word not in stop_words]
        return list(set(keywords))[:5]
    
    def get_node_by_name(self, name: str, node_type: Optional[NodeType] = None) -> Optional[str]:
        """根据名称查找节点"""
        for node_id, node_data in self.graph.nodes(data=True):
            if node_data.get("name") == name:
                if node_type is None or node_data.get("type") == node_type.value:
                    return node_id
        return None
    
    def get_node_neighbors(self, node_id: str, relationship_type: Optional[RelationshipType] = None) -> List[Dict[str, Any]]:
        """获取节点的邻居"""
        neighbors = []
        
        if node_id in self.graph.nodes:
            for neighbor_id in self.graph.neighbors(node_id):
                edge_data = self.graph.get_edge_data(node_id, neighbor_id)
                
                if relationship_type is None or edge_data.get("type") == relationship_type.value:
                    neighbors.append({
                        "node_id": neighbor_id,
                        "node_data": self.graph.nodes[neighbor_id],
                        "relationship": edge_data
                    })
        
        return neighbors
    
    def calculate_node_importance(self, node_id: str) -> float:
        """计算节点重要性"""
        if node_id not in self.graph.nodes:
            return 0.0
        
        importance = 0.0
        degree = self.graph.degree(node_id)
        importance += degree * 0.5
        
        for neighbor_id in self.graph.neighbors(node_id):
            edge_data = self.graph.get_edge_data(node_id, neighbor_id)
            importance += edge_data.get("weight", 1.0) * 0.5
        
        return importance
    
    def get_most_important_nodes(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """获取最重要的节点"""
        node_importance = []
        
        for node_id in self.graph.nodes:
            importance = self.calculate_node_importance(node_id)
            node_importance.append({
                "node_id": node_id,
                "node_data": self.graph.nodes[node_id],
                "importance": importance
            })
        
        node_importance.sort(key=lambda x: x["importance"], reverse=True)
        return node_importance[:top_n]
    
    def generate_knowledge_summary(self) -> Dict[str, Any]:
        """生成知识图谱总结"""
        node_types = {}
        for node_id, node_data in self.graph.nodes(data=True):
            node_type = node_data.get("type")
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        relationship_types = {}
        for u, v, edge_data in self.graph.edges(data=True):
            rel_type = edge_data.get("type")
            relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1
        
        important_nodes = self.get_most_important_nodes(5)
        
        summary = {
            "total_nodes": len(self.graph.nodes),
            "total_edges": len(self.graph.edges),
            "node_types": node_types,
            "relationship_types": relationship_types,
            "important_nodes": important_nodes,
            "density": nx.density(self.graph),
            "average_clustering": nx.average_clustering(self.graph)
        }
        
        return summary
    
    def export_graph(self, format: str = "json") -> Any:
        """导出知识图谱"""
        if format == "json":
            graph_data = {"nodes": [], "edges": []}
            
            for node_id, node_data in self.graph.nodes(data=True):
                graph_data["nodes"].append({"id": node_id, **node_data})
            
            for u, v, edge_data in self.graph.edges(data=True):
                graph_data["edges"].append({"source": u, "target": v, **edge_data})
            
            return graph_data
        
        elif format == "gexf":
            nx.write_gexf(self.graph, "knowledge_graph.gexf")
            return {"message": "知识图谱已导出为 knowledge_graph.gexf"}
        
        return {"error": "不支持的导出格式"}
    
    def clear_graph(self):
        """清空知识图谱"""
        self.graph.clear()
        self.node_counter = 0
        self._add_initial_nodes()
        self._save_graph()
    
    def merge_graph(self, other_graph: 'KnowledgeGraph'):
        """合并另一个知识图谱"""
        for node_id, node_data in other_graph.graph.nodes(data=True):
            if node_id not in self.graph.nodes:
                self.graph.add_node(node_id, **node_data)
        
        for u, v, edge_data in other_graph.graph.edges(data=True):
            if not self.graph.has_edge(u, v):
                self.graph.add_edge(u, v, **edge_data)
        
        self.node_counter = max(self.node_counter, other_graph.node_counter)
        self._save_graph()


knowledge_graph = KnowledgeGraph()
