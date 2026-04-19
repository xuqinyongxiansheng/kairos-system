"""
任务自动化模块
提供工作流编排、定时任务、数据采集、报告生成等功能
整合 002/AAagent 的优秀实现
"""

import json
import os
import time
import sqlite3
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """任务类型枚举"""
    WORKFLOW = "workflow"
    SCHEDULED = "scheduled"
    DATA_COLLECTION = "data_collection"
    REPORT_GENERATION = "report_generation"


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class WorkflowNode:
    """工作流节点数据类"""
    id: str
    name: str
    node_type: str
    parameters: Dict[str, Any]
    dependencies: List[str]
    outputs: List[str]


@dataclass
class Workflow:
    """工作流数据类"""
    id: str
    name: str
    description: str
    nodes: List[WorkflowNode]
    edges: List[Dict[str, str]]
    created_at: datetime
    updated_at: datetime
    status: str


@dataclass
class ScheduledTask:
    """定时任务数据类"""
    id: str
    name: str
    task_type: str
    schedule: str
    parameters: Dict[str, Any]
    created_at: datetime
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    status: str


class TaskAutomation:
    """任务自动化类"""
    
    def __init__(self, db_path: str = "./data/task_automation.db"):
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                nodes TEXT,
                edges TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                task_type TEXT NOT NULL,
                schedule TEXT NOT NULL,
                parameters TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_run TIMESTAMP,
                next_run TIMESTAMP,
                status TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                status TEXT NOT NULL,
                output TEXT,
                error TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_workflow(self, name: str, description: str = "",
                       nodes: List[WorkflowNode] = None,
                       edges: List[Dict[str, str]] = None) -> str:
        """创建工作流"""
        workflow_id = self._generate_id()
        
        workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description,
            nodes=nodes or [],
            edges=edges or [],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status=TaskStatus.PENDING.value
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO workflows (id, name, description, nodes, edges, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                workflow.id,
                workflow.name,
                workflow.description,
                json.dumps([node.__dict__ for node in workflow.nodes], ensure_ascii=False),
                json.dumps(workflow.edges, ensure_ascii=False),
                workflow.status
            ))
            
            conn.commit()
            logger.info(f"创建工作流成功：{workflow_id}")
            return workflow_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"创建工作流失败：{e}")
            raise Exception(f"创建工作流失败：{str(e)}")
        finally:
            conn.close()
    
    def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """执行工作流"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return {"success": False, "error": "工作流不存在"}
        
        self._update_workflow_status(workflow_id, TaskStatus.RUNNING.value)
        
        try:
            dependency_graph = self._build_dependency_graph(workflow)
            execution_order = self._topological_sort(dependency_graph)
            
            results = {}
            for node_id in execution_order:
                node = next((n for n in workflow.nodes if n.id == node_id), None)
                if node:
                    result = self._execute_node(node, results)
                    results[node_id] = result
            
            self._update_workflow_status(workflow_id, TaskStatus.COMPLETED.value)
            
            return {
                "success": True,
                "workflow_id": workflow_id,
                "results": results,
                "execution_order": execution_order
            }
            
        except Exception as e:
            self._update_workflow_status(workflow_id, TaskStatus.FAILED.value)
            return {"success": False, "error": str(e)}
    
    def create_scheduled_task(self, name: str, task_type: str, schedule: str,
                            parameters: Dict[str, Any] = None) -> str:
        """创建定时任务"""
        task_id = self._generate_id()
        next_run = self._calculate_next_run(schedule)
        
        task = ScheduledTask(
            id=task_id,
            name=name,
            task_type=task_type,
            schedule=schedule,
            parameters=parameters or {},
            created_at=datetime.now(),
            last_run=None,
            next_run=next_run,
            status=TaskStatus.PENDING.value
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO scheduled_tasks (id, name, task_type, schedule, parameters, next_run, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                task.id,
                task.name,
                task.task_type,
                task.schedule,
                json.dumps(task.parameters, ensure_ascii=False),
                task.next_run,
                task.status
            ))
            
            conn.commit()
            logger.info(f"创建定时任务成功：{task_id}")
            return task_id
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"创建定时任务失败：{str(e)}")
        finally:
            conn.close()
    
    def collect_data(self, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """数据采集"""
        results = {}
        
        for source in sources:
            source_type = source.get("type")
            source_id = source.get("id", f"source_{len(results)}")
            
            try:
                if source_type == "web":
                    result = self._collect_web_data(source)
                elif source_type == "database":
                    result = self._collect_database_data(source)
                elif source_type == "api":
                    result = self._collect_api_data(source)
                else:
                    result = {"success": False, "error": "未知数据源类型"}
                
                results[source_id] = result
                
            except Exception as e:
                results[source_id] = {"success": False, "error": str(e)}
        
        return results
    
    def generate_report(self, template_path: str, data: Dict[str, Any],
                       output_path: str) -> Dict[str, Any]:
        """生成报告"""
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            report_content = template_content
            for key, value in data.items():
                placeholder = f"{{{{{key}}}}}"
                if placeholder in report_content:
                    report_content = report_content.replace(placeholder, str(value))
            
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            logger.info(f"报告已生成：{output_path}")
            return {
                "success": True,
                "output_path": output_path,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"生成报告失败：{e}")
            return {"success": False, "error": str(e)}
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """获取工作流"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, name, description, nodes, edges, created_at, updated_at, status
                FROM workflows WHERE id = ?
            ''', (workflow_id,))
            
            row = cursor.fetchone()
            if row:
                nodes_data = json.loads(row[3])
                nodes = [WorkflowNode(**node) for node in nodes_data]
                
                return Workflow(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    nodes=nodes,
                    edges=json.loads(row[4]),
                    created_at=datetime.fromisoformat(row[5]),
                    updated_at=datetime.fromisoformat(row[6]),
                    status=row[7]
                )
            return None
            
        finally:
            conn.close()
    
    def get_scheduled_tasks(self, status: str = None) -> List[ScheduledTask]:
        """获取定时任务列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            sql = "SELECT id, name, task_type, schedule, parameters, created_at, last_run, next_run, status FROM scheduled_tasks"
            params = []
            
            if status:
                sql += " WHERE status = ?"
                params.append(status)
            
            cursor.execute(sql, params)
            
            tasks = []
            for row in cursor.fetchall():
                task = ScheduledTask(
                    id=row[0],
                    name=row[1],
                    task_type=row[2],
                    schedule=row[3],
                    parameters=json.loads(row[4]),
                    created_at=datetime.fromisoformat(row[5]),
                    last_run=datetime.fromisoformat(row[6]) if row[6] else None,
                    next_run=datetime.fromisoformat(row[7]) if row[7] else None,
                    status=row[8]
                )
                tasks.append(task)
            
            return tasks
            
        finally:
            conn.close()
    
    def _build_dependency_graph(self, workflow: Workflow) -> Dict[str, List[str]]:
        """构建依赖图"""
        graph = {}
        
        for node in workflow.nodes:
            graph[node.id] = node.dependencies.copy()
        
        for edge in workflow.edges:
            source = edge.get("source")
            target = edge.get("target")
            if source and target:
                if target not in graph:
                    graph[target] = []
                if source not in graph[target]:
                    graph[target].append(source)
        
        return graph
    
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """拓扑排序"""
        in_degree = {node: 0 for node in graph}
        for node in graph:
            for dependency in graph[node]:
                in_degree[dependency] += 1
        
        queue = [node for node in in_degree if in_degree[node] == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for dependent in graph:
                if node in graph[dependent]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        
        return result
    
    def _execute_node(self, node: WorkflowNode, previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """执行工作流节点"""
        node_type = node.node_type
        
        if node_type == "data_collection":
            return self.collect_data(node.parameters.get("sources", []))
        elif node_type == "report_generation":
            data = {}
            for dependency in node.dependencies:
                if dependency in previous_results:
                    data[dependency] = previous_results[dependency]
            
            return self.generate_report(
                node.parameters.get("template_path"),
                data,
                node.parameters.get("output_path")
            )
        elif node_type == "api_call":
            return self._call_api(node.parameters)
        else:
            return {"success": False, "error": f"未知节点类型：{node_type}"}
    
    def _collect_web_data(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """采集网页数据"""
        url = source.get("url")
        if not url:
            return {"success": False, "error": "缺少URL"}
        
        try:
            import requests
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            content = {}
            if source.get("extract_text", True):
                content["text"] = soup.get_text(separator='\n', strip=True)
            
            if source.get("extract_links", False):
                links = []
                for link in soup.find_all('a', href=True):
                    links.append({
                        "text": link.get_text(strip=True),
                        "href": link['href']
                    })
                content["links"] = links
            
            return {"success": True, "content": content}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _collect_database_data(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """采集数据库数据"""
        return {"success": False, "error": "数据库采集功能未实现"}
    
    def _collect_api_data(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """采集API数据"""
        api_url = source.get("url")
        method = source.get("method", "GET")
        headers = source.get("headers", {})
        data = source.get("data")
        
        try:
            import requests
            response = requests.request(method, api_url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            
            return {"success": True, "content": response.json()}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _call_api(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """调用API"""
        return self._collect_api_data(parameters)
    
    def _calculate_next_run(self, schedule: str) -> datetime:
        """计算下次运行时间"""
        if schedule.startswith("every "):
            parts = schedule.split()
            if len(parts) == 2:
                value = int(parts[1][:-1])
                unit = parts[1][-1]
                
                if unit == 'h':
                    return datetime.now() + timedelta(hours=value)
                elif unit == 'm':
                    return datetime.now() + timedelta(minutes=value)
                elif unit == 'd':
                    return datetime.now() + timedelta(days=value)
        
        return datetime.now() + timedelta(minutes=1)
    
    def _update_workflow_status(self, workflow_id: str, status: str):
        """更新工作流状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE workflows SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
            ''', (status, workflow_id))
            
            conn.commit()
            
        finally:
            conn.close()
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        return f"task_{int(time.time())}"
    
    def clear_data(self):
        """清空所有数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM workflows')
            cursor.execute('DELETE FROM scheduled_tasks')
            cursor.execute('DELETE FROM task_executions')
            conn.commit()
            return True
            
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()


task_automation = TaskAutomation()
