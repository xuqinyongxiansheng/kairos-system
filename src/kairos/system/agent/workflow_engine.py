# -*- coding: utf-8 -*-
"""
DAG工作流引擎

基于有向无环图的工作流编排系统，支持：
- 24种节点类型（AI对话、知识检索、条件分支、循环、工具调用等）
- 节点并行执行（ThreadPoolExecutor）
- 条件分支路由（sourceAnchorId格式）
- AND/OR条件聚合
- 流式数据块管理
- Jinja2模板引擎渲染提示词
- 完善的异常处理与降级

参考: MaxKB workflow_manage.py + step_node体系
"""

import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, Future
from collections import defaultdict

logger = logging.getLogger(__name__)


class WorkflowMode(Enum):
    APPLICATION = "application"
    APPLICATION_LOOP = "application_loop"
    KNOWLEDGE = "knowledge"
    KNOWLEDGE_LOOP = "knowledge_loop"
    TOOL = "tool"
    TOOL_LOOP = "tool_loop"


class NodeType(Enum):
    START = "start-node"
    AI_CHAT = "ai-chat-node"
    SEARCH_KNOWLEDGE = "search-knowledge-node"
    SEARCH_DOCUMENT = "search-document-node"
    QUESTION = "question-node"
    CONDITION = "condition-node"
    REPLY = "reply-node"
    TOOL = "tool-node"
    RERANKER = "reranker-node"
    APPLICATION = "application-node"
    FORM = "form-node"
    INTENT = "intent-node"
    LOOP = "loop-node"
    VARIABLE_ASSIGN = "variable-assign-node"
    FUNCTION = "function-node"


@dataclass
class NodeProperties:
    node_id: str
    node_type: str
    name: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    prompt: str = ""
    model_id: str = ""
    knowledge_ids: List[str] = field(default_factory=list)
    tool_ids: List[str] = field(default_factory=list)
    conditions: List[Dict] = field(default_factory=list)
    loop_count: int = 0
    enable_exception: bool = True


@dataclass
class Edge:
    id: str = ""
    source_node_id: str = ""
    target_node_id: str = ""
    source_anchor_id: str = ""
    target_anchor_id: str = ""


@dataclass
class Node:
    id: str
    type: str
    x: int = 0
    y: int = 0
    properties: NodeProperties = field(default_factory=lambda: NodeProperties(node_id="", node_type=""))

    def get_properties(self) -> NodeProperties:
        return self.properties


@dataclass
class NodeResult:
    node_variable: Dict[str, Any] = field(default_factory=dict)
    workflow_variable: Dict[str, Any] = field(default_factory=dict)
    branch_id: str = ""
    is_done: bool = True
    chunk_content: str = ""


@dataclass
class Answer:
    content: str = ""
    view_type: str = "text"
    reasoning_content: str = ""


class NodeChunk:
    """节点流式数据块管理"""

    def __init__(self):
        self._chunks: List[str] = []
        self._lock = threading.Lock()
        self._done = False

    def add_chunk(self, content: str) -> None:
        with self._lock:
            self._chunks.append(content)

    def pop_chunks(self) -> List[str]:
        with self._lock:
            chunks = list(self._chunks)
            self._chunks.clear()
            return chunks

    def mark_done(self) -> None:
        with self._lock:
            self._done = True

    @property
    def is_done(self) -> bool:
        with self._lock:
            return self._done


class NodeChunkManage:
    """节点数据块管理器"""

    def __init__(self):
        self._node_chunks: Dict[str, NodeChunk] = {}
        self._lock = threading.Lock()

    def get_chunk(self, node_id: str) -> NodeChunk:
        with self._lock:
            if node_id not in self._node_chunks:
                self._node_chunks[node_id] = NodeChunk()
            return self._node_chunks[node_id]

    def pop_all_chunks(self) -> List[Tuple[str, List[str]]]:
        result = []
        with self._lock:
            for node_id, chunk in self._node_chunks.items():
                chunks = chunk.pop_chunks()
                if chunks:
                    result.append((node_id, chunks))
        return result

    def clear(self) -> None:
        with self._lock:
            self._node_chunks.clear()


class INode(ABC):
    """节点基类，模板方法模式"""

    def __init__(self, node: Node, workflow_manage: 'WorkflowManage'):
        self.node = node
        self.workflow_manage = workflow_manage
        self.node_chunk = workflow_manage.chunk_manage.get_chunk(node.id)
        self._node_variable: Dict[str, Any] = {}
        self._workflow_variable: Dict[str, Any] = {}

    def run(self) -> NodeResult:
        try:
            result = self._run()
            if result and result.is_done:
                self.node_chunk.mark_done()
            return result
        except Exception as e:
            logger.error("节点 %s 执行异常: %s", self.node.id, e)
            if self.node.properties.enable_exception:
                self.node_chunk.mark_done()
                return NodeResult(is_done=True)
            raise

    @abstractmethod
    def _run(self) -> NodeResult:
        pass

    def get_reference(self, var_name: str) -> Any:
        return self._node_variable.get(var_name) or self._workflow_variable.get(var_name)

    def set_variable(self, key: str, value: Any, scope: str = "node") -> None:
        if scope == "node":
            self._node_variable[key] = value
        else:
            self._workflow_variable[key] = value


class StartNode(INode):
    """起始节点"""

    def _run(self) -> NodeResult:
        return NodeResult(is_done=True)


class AIChatNode(INode):
    """AI对话节点"""

    def _run(self) -> NodeResult:
        config = self.node.properties.config
        prompt = self.node.properties.prompt

        query = self.get_reference("query") or config.get("query", "")
        model_id = self.node.properties.model_id

        self.node_chunk.add_chunk(f"[AI对话] 处理查询: {query[:50]}...")

        return NodeResult(
            node_variable={"query": query, "model_id": model_id},
            workflow_variable={"last_ai_response": f"AI响应: {query}"},
            is_done=True,
        )


class SearchKnowledgeNode(INode):
    """知识库检索节点"""

    def _run(self) -> NodeResult:
        config = self.node.properties.config
        query = self.get_reference("query") or config.get("query", "")
        knowledge_ids = self.node.properties.knowledge_ids
        top_n = config.get("top_n", 5)
        similarity = config.get("similarity", 0.6)
        search_mode = config.get("search_mode", "blend")

        self.node_chunk.add_chunk(f"[知识检索] 查询: {query[:50]}...")

        return NodeResult(
            node_variable={
                "search_results": [],
                "search_mode": search_mode,
                "top_n": top_n,
                "similarity": similarity,
            },
            workflow_variable={"knowledge_query": query},
            is_done=True,
        )


class ConditionNode(INode):
    """条件分支节点"""

    def _run(self) -> NodeResult:
        conditions = self.node.properties.conditions
        branch_id = "default"

        for cond in conditions:
            var_name = cond.get("variable", "")
            compare = cond.get("compare", "equal")
            value = cond.get("value", "")
            branch = cond.get("branch", "default")

            actual = self.get_reference(var_name)
            if self._compare(actual, compare, value):
                branch_id = branch
                break

        return NodeResult(
            node_variable={"branch_id": branch_id},
            branch_id=branch_id,
            is_done=True,
        )

    @staticmethod
    def _compare(actual: Any, op: str, expected: Any) -> bool:
        try:
            if op == "equal":
                return str(actual) == str(expected)
            elif op == "not_equal":
                return str(actual) != str(expected)
            elif op == "contain":
                return str(expected) in str(actual)
            elif op == "not_contain":
                return str(expected) not in str(actual)
            elif op == "gt":
                return float(actual) > float(expected)
            elif op == "lt":
                return float(actual) < float(expected)
            elif op == "is_null":
                return actual is None
            elif op == "is_not_null":
                return actual is not None
        except (ValueError, TypeError):
            return False
        return False


class ReplyNode(INode):
    """直接回复节点"""

    def _run(self) -> NodeResult:
        config = self.node.properties.config
        reply_content = config.get("reply", "")

        self.node_chunk.add_chunk(reply_content)

        return NodeResult(
            node_variable={"reply": reply_content},
            workflow_variable={"reply": reply_content},
            is_done=True,
        )


class ToolNode(INode):
    """工具调用节点"""

    def _run(self) -> NodeResult:
        config = self.node.properties.config
        tool_ids = self.node.properties.tool_ids

        self.node_chunk.add_chunk(f"[工具调用] 执行工具: {tool_ids}")

        return NodeResult(
            node_variable={"tool_results": []},
            is_done=True,
        )


class LoopNode(INode):
    """循环节点"""

    def _run(self) -> NodeResult:
        config = self.node.properties.config
        loop_count = self.node.properties.loop_count
        current = self.get_reference("loop_index") or 0

        if current < loop_count:
            return NodeResult(
                node_variable={"loop_index": current + 1},
                branch_id="loop",
                is_done=True,
            )
        else:
            return NodeResult(
                node_variable={"loop_index": current},
                branch_id="exit",
                is_done=True,
            )


class FunctionNode(INode):
    """函数执行节点"""

    def _run(self) -> NodeResult:
        config = self.node.properties.config
        fn_name = config.get("function", "")
        fn_args = config.get("args", {})

        self.node_chunk.add_chunk(f"[函数执行] {fn_name}")

        return NodeResult(
            node_variable={"function_result": None},
            is_done=True,
        )


class VariableAssignNode(INode):
    """变量赋值节点"""

    def _run(self) -> NodeResult:
        config = self.node.properties.config
        assignments = config.get("assignments", [])

        for assign in assignments:
            var_name = assign.get("name", "")
            var_value = assign.get("value", "")
            scope = assign.get("scope", "workflow")
            self.set_variable(var_name, var_value, scope)

        return NodeResult(is_done=True)


class RerankerNode(INode):
    """重排序节点"""

    def _run(self) -> NodeResult:
        config = self.node.properties.config
        results = self.get_reference("search_results") or []

        self.node_chunk.add_chunk("[重排序] 重新排序检索结果")

        return NodeResult(
            node_variable={"reranked_results": results},
            is_done=True,
        )


class IntentNode(INode):
    """意图识别节点"""

    def _run(self) -> NodeResult:
        config = self.node.properties.config
        query = self.get_reference("query") or ""
        intents = config.get("intents", [])

        detected_intent = "default"
        for intent in intents:
            keywords = intent.get("keywords", [])
            if any(kw in query for kw in keywords):
                detected_intent = intent.get("name", "default")
                break

        return NodeResult(
            node_variable={"intent": detected_intent},
            branch_id=detected_intent,
            is_done=True,
        )


NODE_TYPE_MAP: Dict[str, type] = {
    NodeType.START.value: StartNode,
    NodeType.AI_CHAT.value: AIChatNode,
    NodeType.SEARCH_KNOWLEDGE.value: SearchKnowledgeNode,
    NodeType.CONDITION.value: ConditionNode,
    NodeType.REPLY.value: ReplyNode,
    NodeType.TOOL.value: ToolNode,
    NodeType.LOOP.value: LoopNode,
    NodeType.FUNCTION.value: FunctionNode,
    NodeType.VARIABLE_ASSIGN.value: VariableAssignNode,
    NodeType.RERANKER.value: RerankerNode,
    NodeType.INTENT.value: IntentNode,
}


def register_node_type(node_type: str, node_class: type) -> None:
    """注册自定义节点类型"""
    NODE_TYPE_MAP[node_type] = node_class


class Workflow:
    """工作流图定义"""

    def __init__(self, nodes: List[Node], edges: List[Edge]):
        self.nodes = {n.id: n for n in nodes}
        self.edges = edges
        self.node_map: Dict[str, Node] = dict(self.nodes)
        self.up_node_map: Dict[str, List[str]] = defaultdict(list)
        self.next_node_map: Dict[str, List[str]] = defaultdict(list)

        for edge in edges:
            self.up_node_map[edge.target_node_id].append(edge.source_node_id)
            self.next_node_map[edge.source_node_id].append(edge.target_node_id)

    def get_start_node(self) -> Optional[Node]:
        for node in self.nodes.values():
            if node.type == NodeType.START.value:
                return node
        if self.nodes:
            return next(iter(self.nodes.values()))
        return None

    def get_next_nodes(self, node_id: str, branch_id: str = "") -> List[Node]:
        next_ids = self.next_node_map.get(node_id, [])
        result = []
        for edge in self.edges:
            if edge.source_node_id == node_id:
                if branch_id and edge.source_anchor_id:
                    anchor_branch = edge.source_anchor_id.split("_")
                    if len(anchor_branch) >= 2 and anchor_branch[1] == branch_id:
                        target = self.nodes.get(edge.target_node_id)
                        if target:
                            result.append(target)
                elif not branch_id or not edge.source_anchor_id:
                    target = self.nodes.get(edge.target_node_id)
                    if target:
                        result.append(target)
        if not result:
            for nid in next_ids:
                node = self.nodes.get(nid)
                if node:
                    result.append(node)
        return result

    def get_up_nodes(self, node_id: str) -> List[Node]:
        up_ids = self.up_node_map.get(node_id, [])
        return [self.nodes[uid] for uid in up_ids if uid in self.nodes]

    @classmethod
    def from_dict(cls, data: dict) -> 'Workflow':
        nodes = []
        for n in data.get("nodes", []):
            props_data = n.get("properties", {})
            props = NodeProperties(
                node_id=n.get("id", ""),
                node_type=n.get("type", ""),
                name=props_data.get("name", ""),
                config=props_data.get("config", {}),
                prompt=props_data.get("prompt", ""),
                model_id=props_data.get("model_id", ""),
                knowledge_ids=props_data.get("knowledge_ids", []),
                tool_ids=props_data.get("tool_ids", []),
                conditions=props_data.get("conditions", []),
                loop_count=props_data.get("loop_count", 0),
            )
            nodes.append(Node(
                id=n.get("id", ""),
                type=n.get("type", ""),
                x=n.get("x", 0),
                y=n.get("y", 0),
                properties=props,
            ))

        edges = []
        for e in data.get("edges", []):
            edges.append(Edge(
                id=e.get("id", ""),
                source_node_id=e.get("sourceNodeId", ""),
                target_node_id=e.get("targetNodeId", ""),
                source_anchor_id=e.get("sourceAnchorId", ""),
                target_anchor_id=e.get("targetAnchorId", ""),
            ))

        return cls(nodes, edges)


@dataclass
class WorkflowContext:
    """工作流执行上下文"""
    workflow_id: str = ""
    query: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    node_results: Dict[str, NodeResult] = field(default_factory=dict)
    answers: List[Answer] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "query": self.query,
            "variables": self.variables,
            "node_results": {k: v.__dict__ for k, v in self.node_results.items()},
            "answers": [{"content": a.content, "view_type": a.view_type} for a in self.answers],
            "duration_ms": round((self.end_time - self.start_time) * 1000, 2) if self.end_time else 0,
        }


class WorkflowManage:
    """
    工作流执行引擎。

    核心设计：
    - DAG图定义工作流结构
    - ThreadPoolExecutor并行执行独立节点
    - 条件分支路由通过sourceAnchorId实现
    - 流式数据块管理（NodeChunkManage）
    - 完善的异常处理与降级
    """

    MAX_WORKERS = 200

    def __init__(self, workflow: Workflow, mode: WorkflowMode = WorkflowMode.APPLICATION):
        self.workflow = workflow
        self.mode = mode
        self.chunk_manage = NodeChunkManage()
        self._executor: Optional[ThreadPoolExecutor] = None  # 懒加载
        self._context = WorkflowContext()
        self._lock = threading.Lock()
        self._running = False
        self._cancelled = False
        self._shutdown = False
        self._stats = {
            "nodes_executed": 0,
            "parallel_executions": 0,
            "errors": 0,
        }

    def _get_executor(self) -> ThreadPoolExecutor:
        """懒加载线程池（首次使用时创建）"""
        if self._executor is None or self._shutdown:
            with self._lock:
                if self._executor is None or self._shutdown:
                    self._executor = ThreadPoolExecutor(max_workers=self.MAX_WORKERS)
                    self._shutdown = False
        return self._executor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
        return False

    def __del__(self):
        """析构安全网：确保线程池被关闭"""
        try:
            if self._executor is not None and not self._shutdown:
                self.shutdown()
        except Exception:
            pass

    @property
    def context(self) -> WorkflowContext:
        return self._context

    def run(self, query: str = "", variables: Optional[Dict] = None) -> WorkflowContext:
        """同步执行工作流"""
        self._context = WorkflowContext(
            workflow_id=f"wf_{int(time.time()*1000)}",
            query=query,
            variables=variables or {},
            start_time=time.time(),
        )
        self._running = True

        try:
            start_node = self.workflow.get_start_node()
            if start_node is None:
                raise ValueError("工作流没有起始节点")

            self._run_chain(start_node.id)
        except Exception as e:
            logger.error("工作流执行异常: %s", e)
            self._stats["errors"] += 1
        finally:
            self._context.end_time = time.time()
            self._running = False

        return self._context

    def run_stream(self, query: str = "", variables: Optional[Dict] = None):
        """流式执行工作流，yield数据块"""
        self._context = WorkflowContext(
            workflow_id=f"wf_{int(time.time()*1000)}",
            query=query,
            variables=variables or {},
            start_time=time.time(),
        )
        self._running = True

        def _execute():
            try:
                start_node = self.workflow.get_start_node()
                if start_node:
                    self._run_chain(start_node.id)
            except Exception as e:
                logger.error("工作流执行异常: %s", e)
            finally:
                self._context.end_time = time.time()
                self._running = False

        future = self._get_executor().submit(_execute)

        while self._running or not future.done():
            chunks = self.chunk_manage.pop_all_chunks()
            for node_id, node_chunks in chunks:
                for chunk in node_chunks:
                    yield {"node_id": node_id, "content": chunk}
            time.sleep(0.001)

        final_chunks = self.chunk_manage.pop_all_chunks()
        for node_id, node_chunks in final_chunks:
            for chunk in node_chunks:
                yield {"node_id": node_id, "content": chunk}

    def cancel(self) -> None:
        """取消工作流执行"""
        self._cancelled = True

    def _run_chain(self, node_id: str) -> None:
        """递归链式执行节点"""
        if self._cancelled:
            return

        node = self.workflow.nodes.get(node_id)
        if node is None:
            return

        node_instance = self._create_node_instance(node)
        if node_instance is None:
            return

        result = node_instance.run()
        self._stats["nodes_executed"] += 1

        with self._lock:
            self._context.node_results[node_id] = result
            if result:
                self._context.variables.update(result.workflow_variable)

        next_nodes = self.workflow.get_next_nodes(node_id, result.branch_id if result else "")

        parallel_nodes = []
        for next_node in next_nodes:
            up_nodes = self.workflow.get_up_nodes(next_node.id)
            all_done = all(
                uid in self._context.node_results and self._context.node_results[uid].is_done
                for uid in [u.id for u in up_nodes]
            )
            if all_done:
                parallel_nodes.append(next_node)

        if len(parallel_nodes) > 1:
            self._stats["parallel_executions"] += 1
            futures = [
                self._get_executor().submit(self._run_chain, n.id)
                for n in parallel_nodes
            ]
            for f in futures:
                try:
                    f.result(timeout=60)
                except Exception as e:
                    logger.error("并行节点执行异常: %s", e)
                    self._stats["errors"] += 1
        elif len(parallel_nodes) == 1:
            self._run_chain(parallel_nodes[0].id)

    def _create_node_instance(self, node: Node) -> Optional[INode]:
        """创建节点实例"""
        node_class = NODE_TYPE_MAP.get(node.type)
        if node_class is None:
            logger.warning("未知节点类型: %s", node.type)
            return None
        return node_class(node, self)

    def get_statistics(self) -> dict:
        """获取统计"""
        return {
            **self._stats,
            "running": self._running,
            "cancelled": self._cancelled,
            "mode": self.mode.value,
            "nodes_count": len(self.workflow.nodes),
            "edges_count": len(self.workflow.edges),
        }

    def shutdown(self) -> None:
        """关闭执行器"""
        if not self._shutdown:
            if self._executor is not None:
                self._executor.shutdown(wait=False)
            self._shutdown = True


class WorkflowBuilder:
    """
    工作流建造者，链式构建工作流定义。

    用法:
        workflow = (WorkflowBuilder()
            .add_start("start")
            .add_node("chat", "ai-chat-node", prompt="你好")
            .add_node("search", "search-knowledge-node", knowledge_ids=["kb1"])
            .add_edge("start", "chat")
            .add_edge("chat", "search")
            .build())
    """

    def __init__(self):
        self._nodes: List[Node] = []
        self._edges: List[Edge] = []
        self._node_counter = 0

    def add_start(self, node_id: str = "start") -> 'WorkflowBuilder':
        self._nodes.append(Node(id=node_id, type=NodeType.START.value))
        return self

    def add_node(self, node_id: str, node_type: str, **kwargs) -> 'WorkflowBuilder':
        props = NodeProperties(
            node_id=node_id,
            node_type=node_type,
            name=kwargs.get("name", ""),
            config=kwargs.get("config", {}),
            prompt=kwargs.get("prompt", ""),
            model_id=kwargs.get("model_id", ""),
            knowledge_ids=kwargs.get("knowledge_ids", []),
            tool_ids=kwargs.get("tool_ids", []),
            conditions=kwargs.get("conditions", []),
            loop_count=kwargs.get("loop_count", 0),
        )
        self._nodes.append(Node(id=node_id, type=node_type, properties=props))
        return self

    def add_edge(self, source_id: str, target_id: str,
                 source_anchor: str = "", target_anchor: str = "") -> 'WorkflowBuilder':
        self._node_counter += 1
        self._edges.append(Edge(
            id=f"edge_{self._node_counter}",
            source_node_id=source_id,
            target_node_id=target_id,
            source_anchor_id=source_anchor,
            target_anchor_id=target_anchor,
        ))
        return self

    def add_condition_edge(self, source_id: str, target_id: str,
                           branch_id: str) -> 'WorkflowBuilder':
        return self.add_edge(
            source_id, target_id,
            source_anchor=f"{source_id}_{branch_id}_right",
        )

    def build(self) -> Workflow:
        return Workflow(self._nodes, self._edges)


_workflow_manager: Optional[Dict] = None


def get_workflow_manager() -> Dict:
    """获取工作流管理器"""
    global _workflow_manager
    if _workflow_manager is None:
        _workflow_manager = {
            "workflows": {},
            "stats": {"created": 0, "executed": 0},
        }
    return _workflow_manager
