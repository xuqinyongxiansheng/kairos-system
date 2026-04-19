"""
自我学习系统
实现自主学习能力，从 GitHub 搜索相关代码、分析、测试和集成新功能
整合 002/AAagent 的优秀实现
"""

import asyncio
import json
import os
import time
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LearningStage(Enum):
    """学习阶段枚举"""
    REQUIREMENT_ANALYSIS = "requirement_analysis"
    RESOURCE_SEARCH = "resource_search"
    CODE_ANALYSIS = "code_analysis"
    TEST_VERIFICATION = "test_verification"
    INTEGRATION = "integration"
    KNOWLEDGE_RECORDING = "knowledge_recording"


class LearningStatus(Enum):
    """学习状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class LearningExperience:
    """学习经验数据类"""
    id: str
    need_description: str
    requirements: Dict[str, Any]
    learned_tools: List[Dict[str, Any]]
    success_rate: float
    timestamp: datetime
    metadata: Dict[str, Any]


class SelfLearningSystem:
    """自我学习系统核心类"""
    
    def __init__(self, agent=None):
        self.agent = agent
        self.github_explorer = GitHubExplorer(self)
        self.code_analyzer = CodeAnalyzer(self)
        self.test_runner = TestRunner(self)
        self.integration_manager = IntegrationManager(self)
        self.knowledge_graph = KnowledgeGraphLearning(self)
        self.learning_strategy = LearningStrategyOptimizer(self)
        
        self.learning_history: List[LearningExperience] = []
        self.current_learning = None
        
        logger.info("自我学习系统初始化完成")
    
    async def learn_new_capability(self, need_description: str) -> Dict[str, Any]:
        """学习新能力的完整流程"""
        start_time = datetime.now()
        
        try:
            requirements = await self.analyze_requirements(need_description)
            
            repos = await self.github_explorer.search_repositories(requirements)
            
            code_units = []
            for repo in repos[:3]:
                code = await self.github_explorer.fetch_code(repo)
                analysis = await self.code_analyzer.analyze(code, requirements)
                code_units.append(analysis)
            
            validated_units = []
            for unit in code_units:
                test_results = await self.test_runner.run_tests(unit)
                if test_results["pass_rate"] > 0.7:
                    validated_units.append((unit, test_results))
            
            integrated_tools = []
            for unit, results in validated_units:
                tool = await self.integration_manager.integrate(unit, results)
                integrated_tools.append(tool)
            
            experience = await self.record_learning_experience(
                need_description, requirements, integrated_tools
            )
            
            await self.learning_strategy.optimize_strategy({
                "success_rate": len(integrated_tools) / len(code_units) if code_units else 0,
                "learned_tools": integrated_tools
            })
            
            total_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"学习完成：{need_description}，成功率 {len(integrated_tools) / len(code_units) if code_units else 0:.2f}")
            
            return {
                "success": True,
                "learned_tools": integrated_tools,
                "success_rate": len(integrated_tools) / len(code_units) if code_units else 0,
                "total_time": total_time,
                "experience_id": experience.id
            }
            
        except Exception as e:
            logger.error(f"学习失败：{e}")
            return {
                "success": False,
                "error": str(e),
                "total_time": (datetime.now() - start_time).total_seconds()
            }
    
    async def analyze_requirements(self, need_description: str) -> Dict[str, Any]:
        """分析学习需求"""
        requirements = {
            "description": need_description,
            "type": await self._classify_need_type(need_description),
            "language": "python",
            "difficulty": "medium",
            "keywords": self._extract_keywords(need_description)
        }
        
        return requirements
    
    async def _classify_need_type(self, description: str) -> str:
        """分类需求类型"""
        description_lower = description.lower()
        
        if any(keyword in description_lower for keyword in ["数据", "分析", "统计", "处理"]):
            return "data_processing"
        elif any(keyword in description_lower for keyword in ["网络", "http", "api", "爬虫"]):
            return "network_tool"
        elif any(keyword in description_lower for keyword in ["文件", "读写", "格式", "转换"]):
            return "file_operation"
        elif any(keyword in description_lower for keyword in ["算法", "计算", "数学", "模型"]):
            return "algorithm"
        elif any(keyword in description_lower for keyword in ["系统", "进程", "操作系统", "管理"]):
            return "system_tool"
        else:
            return "general"
    
    def _extract_keywords(self, description: str) -> List[str]:
        """提取关键词"""
        words = re.findall(r'[\u4e00-\u9fa5]+|\w+', description)
        stop_words = {"的", "了", "和", "是", "在", "有", "我", "你", "他", "这", "那"}
        
        keywords = [word for word in words if len(word) > 1 and word not in stop_words]
        return list(set(keywords))[:10]
    
    async def record_learning_experience(self, need_description: str,
                                       requirements: Dict[str, Any],
                                       learned_tools: List[Dict[str, Any]]) -> LearningExperience:
        """记录学习经验"""
        experience_id = f"learning_{int(time.time())}"
        
        experience = LearningExperience(
            id=experience_id,
            need_description=need_description,
            requirements=requirements,
            learned_tools=learned_tools,
            success_rate=len(learned_tools) / len(requirements.get("keywords", [1])),
            timestamp=datetime.now(),
            metadata={
                "learning_stages": list(LearningStage.__members__.keys()),
                "total_tools": len(learned_tools)
            }
        )
        
        self.learning_history.append(experience)
        
        await self.knowledge_graph.add_learning_experience({
            "need_description": need_description,
            "success_rate": experience.success_rate,
            "learned_tools": learned_tools,
            "timestamp": experience.timestamp.isoformat()
        })
        
        return experience
    
    def get_learning_history(self, limit: int = 10) -> List[LearningExperience]:
        """获取学习历史"""
        return self.learning_history[-limit:]
    
    def get_current_learning(self) -> Optional[Dict[str, Any]]:
        """获取当前学习状态"""
        return self.current_learning
    
    async def suggest_learning_path(self, current_need: str) -> List[str]:
        """建议学习路径"""
        return await self.knowledge_graph.suggest_learning_path(current_need)


class GitHubExplorer:
    """GitHub 代码探索器"""
    
    def __init__(self, learning_system):
        self.learning_system = learning_system
        self.github_token = os.getenv("GITHUB_TOKEN", "")
        self.cache_dir = "./data/github_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
    
    async def search_repositories(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """搜索 GitHub 仓库"""
        search_queries = await self._generate_search_queries(requirements)
        all_repos = []
        
        for query in search_queries[:5]:
            repos = await self._execute_github_search(query)
            all_repos.extend(repos)
        
        unique_repos = self._deduplicate_repos(all_repos)
        sorted_repos = self._rank_repositories(unique_repos, requirements)
        
        return sorted_repos[:10]
    
    async def _generate_search_queries(self, requirements: Dict[str, Any]) -> List[str]:
        """生成搜索查询"""
        queries = []
        
        keywords = requirements.get("keywords", [])
        for keyword in keywords[:3]:
            queries.append(f"{keyword} python")
        
        type_query = {
            "data_processing": "data processing python",
            "network_tool": "network api python",
            "file_operation": "file handling python",
            "algorithm": "algorithm python",
            "system_tool": "system utilities python"
        }.get(requirements.get("type"), "python library")
        
        queries.append(type_query)
        
        return list(set(queries))
    
    async def _execute_github_search(self, query: str) -> List[Dict[str, Any]]:
        """执行 GitHub 搜索（模拟实现）"""
        return [
            {
                "name": f"python-{query.replace(' ', '-')}",
                "full_name": f"testuser/python-{query.replace(' ', '-')}",
                "description": f"A Python library for {query}",
                "stars": 100 + len(query),
                "forks": 20 + len(query),
                "url": f"https://github.com/testuser/python-{query.replace(' ', '-')}",
                "language": "Python",
                "updated_at": datetime.now().isoformat()
            }
        ]
    
    async def fetch_code(self, repo_info: Dict[str, Any]) -> Dict[str, Any]:
        """获取仓库代码（模拟实现）"""
        return {
            "repo_info": repo_info,
            "files": [
                {
                    "path": "main.py",
                    "name": "main.py",
                    "size": 1024,
                    "content": "# Sample code\n\ndef hello_world():\n    return \"Hello, World!\"\n"
                }
            ],
            "directories": [],
            "requirements": "requests\nnumpy",
            "readme": "# Sample Repository"
        }
    
    def _deduplicate_repos(self, repos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重仓库"""
        seen = set()
        unique_repos = []
        
        for repo in repos:
            full_name = repo.get("full_name")
            if full_name not in seen:
                seen.add(full_name)
                unique_repos.append(repo)
        
        return unique_repos
    
    def _rank_repositories(self, repos: List[Dict[str, Any]], requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """排序仓库"""
        def rank_repo(repo):
            score = repo.get("stars", 0)
            
            description = repo.get("description", "").lower()
            keywords = requirements.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in description:
                    score += 10
            
            return score
        
        return sorted(repos, key=rank_repo, reverse=True)


class CodeAnalyzer:
    """代码分析器"""
    
    def __init__(self, learning_system):
        self.learning_system = learning_system
    
    async def analyze(self, code_structure: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """分析代码结构"""
        analysis_result = {
            "summary": "",
            "functions": [],
            "classes": [],
            "dependencies": [],
            "usage_examples": [],
            "complexity": 0,
            "quality_score": 0
        }
        
        python_files = [f for f in code_structure.get("files", []) if f["path"].endswith('.py')]
        
        for file_data in python_files[:10]:
            file_analysis = await self._analyze_file(file_data, requirements)
            
            analysis_result["functions"].extend(file_analysis.get("functions", []))
            analysis_result["classes"].extend(file_analysis.get("classes", []))
            analysis_result["dependencies"].extend(file_analysis.get("dependencies", []))
        
        analysis_result["summary"] = await self._generate_summary(analysis_result, requirements)
        analysis_result["usage_examples"] = await self._generate_usage_examples(analysis_result, requirements)
        analysis_result["quality_score"] = self._calculate_quality_score(analysis_result)
        
        return analysis_result
    
    async def _analyze_file(self, file_data: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """分析单个文件"""
        import ast
        
        content = file_data["content"]
        file_analysis = {
            "file_name": file_data["name"],
            "functions": [],
            "classes": [],
            "dependencies": []
        }
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = {
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "docstring": ast.get_docstring(node),
                        "line_count": node.end_lineno - node.lineno if node.end_lineno else 0
                    }
                    
                    if self._is_relevant_function(func_info, requirements):
                        file_analysis["functions"].append(func_info)
                
                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "methods": [],
                        "docstring": ast.get_docstring(node)
                    }
                    
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            class_info["methods"].append(item.name)
                    
                    file_analysis["classes"].append(class_info)
            
            imports = re.findall(r'^import\s+(\w+)', content, re.MULTILINE)
            imports_from = re.findall(r'^from\s+(\w+)', content, re.MULTILINE)
            file_analysis["dependencies"] = list(set(imports + imports_from))
            
        except SyntaxError:
            functions = re.findall(r'def\s+(\w+)\s*\(', content)
            file_analysis["functions"] = [{"name": func, "args": [], "docstring": None} for func in functions]
        
        return file_analysis
    
    def _is_relevant_function(self, func_info: Dict[str, Any], requirements: Dict[str, Any]) -> bool:
        """判断函数是否相关"""
        keywords = requirements.get("keywords", [])
        text_to_check = f"{func_info['name']} {func_info.get('docstring', '')}".lower()
        
        for keyword in keywords:
            if keyword.lower() in text_to_check:
                return True
        
        return True
    
    async def _generate_summary(self, analysis: Dict[str, Any], requirements: Dict[str, Any]) -> str:
        """生成分析总结"""
        return f"代码库包含 {len(analysis['functions'])} 个函数和 {len(analysis['classes'])} 个类，主要依赖：{', '.join(set(analysis['dependencies']))[:100]}"
    
    async def _generate_usage_examples(self, analysis: Dict[str, Any], requirements: Dict[str, Any]) -> List[str]:
        """生成使用示例"""
        examples = []
        
        for func in analysis["functions"][:3]:
            example = f"# 使用{func['name']}函数\nresult = {func['name']}({', '.join(func['args'])})"
            examples.append(example)
        
        return examples
    
    def _calculate_quality_score(self, analysis: Dict[str, Any]) -> float:
        """计算质量分数"""
        score = 0
        
        score += min(len(analysis["functions"]) * 0.1, 3)
        score += min(len(analysis["classes"]) * 0.2, 2)
        score += max(5 - len(analysis["dependencies"]), 0)
        score += len(analysis["usage_examples"])
        
        return min(score, 10)


class TestRunner:
    """测试运行器"""
    
    def __init__(self, learning_system):
        self.learning_system = learning_system
        self.test_env = self._create_test_environment()
    
    def _create_test_environment(self) -> Dict[str, Any]:
        """创建测试环境"""
        import tempfile
        
        return {
            "temp_dir": tempfile.mkdtemp(prefix="self_learning_test_"),
            "max_execution_time": 5,
            "allowed_imports": ["os", "sys", "json", "math", "datetime", "re"]
        }
    
    async def run_tests(self, code_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """运行测试"""
        test_results = {
            "pass_rate": 0,
            "tests_run": 0,
            "tests_passed": 0,
            "errors": []
        }
        
        test_cases = await self._generate_test_cases(code_analysis)
        
        for test_case in test_cases[:5]:
            result = await self._execute_test_case(test_case, code_analysis)
            
            test_results["tests_run"] += 1
            if result["passed"]:
                test_results["tests_passed"] += 1
            else:
                test_results["errors"].append(result["error"])
        
        if test_results["tests_run"] > 0:
            test_results["pass_rate"] = test_results["tests_passed"] / test_results["tests_run"]
        
        return test_results
    
    async def _generate_test_cases(self, code_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成测试用例"""
        test_cases = []
        
        for func in code_analysis["functions"][:3]:
            test_cases.append({
                "function": func["name"],
                "test_input": "1, 2",
                "expected_output": "3",
                "type": "unit_test"
            })
        
        return test_cases
    
    async def _execute_test_case(self, test_case: Dict[str, Any], code_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """执行测试用例（模拟）"""
        import random
        
        return {
            "passed": random.random() > 0.3,
            "output": "test_result",
            "error": "" if random.random() > 0.3 else "测试失败",
            "execution_time": 0.1
        }


class IntegrationManager:
    """集成管理器"""
    
    def __init__(self, learning_system):
        self.learning_system = learning_system
        self.tools_dir = "./data/learned_tools"
        os.makedirs(self.tools_dir, exist_ok=True)
    
    async def integrate(self, code_analysis: Dict[str, Any], test_results: Dict[str, Any]) -> Dict[str, Any]:
        """集成新工具"""
        selected_function = await self._select_function_to_integrate(code_analysis, test_results)
        
        if not selected_function:
            return {"error": "没有找到合适的功能"}
        
        tool_code = await self._generate_tool_code(selected_function, code_analysis)
        
        tool_path = os.path.join(self.tools_dir, f"{selected_function['name']}.py")
        with open(tool_path, 'w', encoding='utf-8') as f:
            f.write(tool_code)
        
        registration_result = await self._register_tool_to_agent(selected_function, tool_path)
        
        return {
            "tool_name": selected_function['name'],
            "tool_path": tool_path,
            "registration": registration_result,
            "source_repo": code_analysis.get("repo_info", {}).get("full_name", "unknown")
        }
    
    async def _select_function_to_integrate(self, code_analysis: Dict[str, Any],
                                         test_results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """选择要集成的函数"""
        functions = code_analysis.get("functions", [])
        return functions[0] if functions else None
    
    async def _generate_tool_code(self, function: Dict[str, Any],
                                 code_analysis: Dict[str, Any]) -> str:
        """生成工具代码"""
        template = f'''#!/usr/bin/env python3
"""
自动生成的工具：{function.get('name', 'unknown')}
"""

from typing import Dict, Any


class {function['name'].title()}Tool:
    """自动生成的工具"""
    
    def __init__(self):
        self.name = "{function['name']}"
        self.description = "{function.get('docstring', '')}"
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        try:
            result = self._implementation(**kwargs)
            return {{
                "success": True,
                "result": result,
                "tool": self.name
            }}
        except Exception as e:
            return {{
                "success": False,
                "error": str(e),
                "tool": self.name
            }}
    
    def _implementation(self, **kwargs):
        """工具实现"""
        return f"执行{{self.name}}工具，参数：{{kwargs}}"
'''
        return template
    
    async def _register_tool_to_agent(self, function: Dict[str, Any], tool_path: str) -> Dict[str, Any]:
        """注册工具到 Agent"""
        try:
            import importlib.util
            import sys
            
            spec = importlib.util.spec_from_file_location(f"learned_tool_{function['name']}", tool_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            
            tool_class_name = f"{function['name'].title()}Tool"
            tool_instance = getattr(module, tool_class_name)()
            
            if self.learning_system.agent and hasattr(self.learning_system.agent, 'tools'):
                self.learning_system.agent.tools[function['name']] = tool_instance.execute
            
            return {
                "success": True,
                "tool_class": tool_class_name,
                "module": spec.name
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class KnowledgeGraphLearning:
    """知识图谱（学习用）"""
    
    def __init__(self, learning_system):
        self.learning_system = learning_system
        self.graph = self._init_graph()
    
    def _init_graph(self):
        """初始化知识图谱"""
        try:
            import networkx as nx
            graph = nx.Graph()
            graph.add_node("agent", type="agent", name="学习系统")
            graph.add_node("github", type="source", name="GitHub")
            return graph
        except ImportError:
            return {}
    
    async def add_learning_experience(self, experience: Dict[str, Any]):
        """添加学习经验"""
        if isinstance(self.graph, dict):
            return
        
        learning_id = f"learning_{len(list(self.graph.nodes))}"
        
        if hasattr(self.graph, 'add_node'):
            self.graph.add_node(
                learning_id,
                type="learning",
                description=experience.get("need_description", ""),
                success_rate=experience.get("success_rate", 0)
            )
            
            self.graph.add_edge(learning_id, "agent", relation="performed_by")
            
            for tool in experience.get("learned_tools", []):
                tool_id = f"tool_{tool.get('tool_name', 'unknown')}"
                self.graph.add_node(
                    tool_id,
                    type="tool",
                    name=tool.get('tool_name', ''),
                    source=tool.get('source_repo', '')
                )
                
                self.graph.add_edge(learning_id, tool_id, relation="produced")
                self.graph.add_edge(tool_id, "github", relation="sourced_from")
    
    async def query_related_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """查询相关知识"""
        if isinstance(self.graph, dict):
            return []
        
        related_nodes = []
        
        for node, data in self.graph.nodes(data=True):
            if query.lower() in str(data).lower():
                neighbors = list(self.graph.neighbors(node))
                related_nodes.append({
                    "node": node,
                    "data": data,
                    "neighbors": neighbors
                })
        
        return related_nodes
    
    async def suggest_learning_path(self, current_need: str) -> List[str]:
        """建议学习路径"""
        return [
            f"1. 搜索与'{current_need}'相关的 Python 库",
            "2. 分析代码结构和功能",
            "3. 测试核心功能的正确性",
            "4. 集成到 Agent 系统中",
            "5. 记录学习经验到知识图谱"
        ]


class LearningStrategyOptimizer:
    """学习策略优化器"""
    
    def __init__(self, learning_system):
        self.learning_system = learning_system
        self.strategies = {
            "exploration": 0.3,
            "exploitation": 0.7,
            "collaborative": 0.2,
            "reinforcement": 0.5
        }
    
    async def optimize_strategy(self, learning_result: Dict[str, Any]):
        """优化学习策略"""
        success_rate = learning_result.get("success_rate", 0)
        
        if success_rate > 0.8:
            self.strategies["exploration"] = min(0.5, self.strategies["exploration"] + 0.1)
        elif success_rate < 0.3:
            self.strategies["exploration"] = max(0.1, self.strategies["exploration"] - 0.1)
            self.strategies["exploitation"] = min(0.9, self.strategies["exploitation"] + 0.1)
        
        return self.strategies
    
    async def generate_learning_plan(self, need_description: str) -> Dict[str, Any]:
        """生成学习计划"""
        need_type = await self.learning_system._classify_need_type(need_description)
        
        return {
            "need": need_description,
            "type": need_type,
            "strategy": "balanced",
            "steps": [
                "需求分析",
                "资源搜索",
                "代码分析",
                "测试验证",
                "集成部署",
                "知识记录"
            ],
            "estimated_time": "30-60 分钟",
            "resources_needed": ["GitHub API", "Python 环境", "测试沙箱"]
        }


self_learning_system = SelfLearningSystem()
