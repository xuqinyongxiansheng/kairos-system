"""
测试生成器模块
自动生成单元测试和集成测试
支持: AST分析、测试模板、覆盖率分析、边界用例生成
"""

import ast
import os
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import textwrap

logger = logging.getLogger("TestGenerator")


class TestType(Enum):
    """测试类型"""
    UNIT = "unit"
    INTEGRATION = "integration"
    FUNCTIONAL = "functional"
    EDGE_CASE = "edge_case"
    PERFORMANCE = "performance"


class TestFramework(Enum):
    """测试框架"""
    PYTEST = "pytest"
    UNITTEST = "unittest"


@dataclass
class FunctionAnalysis:
    """函数分析结果"""
    name: str
    args: List[Dict[str, str]]
    returns: Optional[str]
    docstring: Optional[str]
    is_async: bool
    is_method: bool
    decorators: List[str]
    complexity: int
    lines: Tuple[int, int]


@dataclass
class ClassAnalysis:
    """类分析结果"""
    name: str
    bases: List[str]
    methods: List[FunctionAnalysis]
    docstring: Optional[str]
    is_abstract: bool


@dataclass
class TestConfig:
    """测试配置"""
    framework: TestFramework = TestFramework.PYTEST
    coverage_target: float = 0.8
    include_edge_cases: bool = True
    include_mocks: bool = True
    include_docstrings: bool = True
    test_directory: str = "./tests"


@dataclass
class GeneratedTest:
    """生成的测试"""
    test_name: str
    test_type: TestType
    test_code: str
    target_function: str
    coverage_estimate: float
    dependencies: List[str]


class TestGenerator:
    """
    测试代码生成器
    
    功能:
    - AST代码分析
    - 测试模板生成
    - 边界用例生成
    - Mock自动创建
    - 覆盖率估算
    """
    
    def __init__(self, config: TestConfig = None):
        self.config = config or TestConfig()
        self.generated_tests: List[GeneratedTest] = []
        
        os.makedirs(self.config.test_directory, exist_ok=True)
        
        logger.info(f"测试生成器初始化 (framework={self.config.framework.value})")
    
    async def analyze_code(self, code: str) -> Dict[str, Any]:
        """
        分析代码结构
        
        Args:
            code: 源代码
            
        Returns:
            分析结果
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {"status": "error", "error": f"语法错误: {e}"}
        
        functions = []
        classes = []
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(self._analyze_function(node))
            elif isinstance(node, ast.AsyncFunctionDef):
                functions.append(self._analyze_function(node, is_async=True))
            elif isinstance(node, ast.ClassDef):
                classes.append(self._analyze_class(node, code))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(self._analyze_import(node))
        
        return {
            "status": "success",
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "total_functions": len(functions),
            "total_classes": len(classes)
        }
    
    def _analyze_function(self, node: ast.FunctionDef, 
                         is_async: bool = False) -> Dict[str, Any]:
        """分析函数"""
        args = []
        
        # 参数分析
        for arg in node.args.args:
            arg_info = {
                "name": arg.arg,
                "type": self._get_annotation_type(arg.annotation)
            }
            args.append(arg_info)
        
        # 返回类型
        returns = self._get_annotation_type(node.returns)
        
        # 装饰器
        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                decorators.append(dec.attr)
        
        # 复杂度估算
        complexity = self._estimate_complexity(node)
        
        return {
            "name": node.name,
            "args": args,
            "returns": returns,
            "docstring": ast.get_docstring(node),
            "is_async": is_async,
            "is_method": any(arg.arg == "self" for arg in node.args.args),
            "decorators": decorators,
            "complexity": complexity,
            "lines": (node.lineno, node.end_lineno or node.lineno)
        }
    
    def _analyze_class(self, node: ast.ClassDef, code: str) -> Dict[str, Any]:
        """分析类"""
        methods = []
        
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self._analyze_function(
                    item, 
                    is_async=isinstance(item, ast.AsyncFunctionDef)
                ))
        
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
        
        return {
            "name": node.name,
            "bases": bases,
            "methods": methods,
            "docstring": ast.get_docstring(node),
            "is_abstract": any(
                isinstance(item, ast.Expr) and 
                isinstance(item.value, ast.Call) and
                isinstance(item.value.func, ast.Name) and
                item.value.func.id == "abstractmethod"
                for item in node.body
            )
        }
    
    def _analyze_import(self, node) -> Dict[str, Any]:
        """分析导入"""
        if isinstance(node, ast.Import):
            return {
                "type": "import",
                "module": None,
                "names": [n.name for n in node.names]
            }
        else:
            return {
                "type": "from_import",
                "module": node.module,
                "names": [n.name for n in node.names]
            }
    
    def _get_annotation_type(self, annotation) -> Optional[str]:
        """获取类型注解"""
        if annotation is None:
            return None
        if isinstance(annotation, ast.Name):
            return annotation.id
        if isinstance(annotation, ast.Constant):
            return str(annotation.value)
        if isinstance(annotation, ast.Subscript):
            return ast.unparse(annotation)
        return None
    
    def _estimate_complexity(self, node: ast.FunctionDef) -> int:
        """估算复杂度"""
        complexity = 1
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    async def generate_tests(self, code: str, 
                            source_file: str = None) -> Dict[str, Any]:
        """
        生成测试代码
        
        Args:
            code: 源代码
            source_file: 源文件路径
            
        Returns:
            生成结果
        """
        analysis = await self.analyze_code(code)
        
        if analysis["status"] != "success":
            return analysis
        
        tests = []
        
        # 为每个函数生成测试
        for func in analysis["functions"]:
            if func["name"].startswith("_") and not func["name"].startswith("__"):
                continue  # 跳过私有方法
            
            test = await self._generate_function_test(func, analysis, source_file)
            tests.append(test)
        
        # 为每个类生成测试
        for cls in analysis["classes"]:
            test = await self._generate_class_test(cls, analysis, source_file)
            tests.append(test)
        
        # 生成测试文件
        test_file_content = self._generate_test_file(tests, analysis, source_file)
        
        return {
            "status": "success",
            "tests": tests,
            "test_file": test_file_content,
            "coverage_estimate": self._estimate_coverage(analysis, tests)
        }
    
    async def _generate_function_test(self, func: Dict[str, Any],
                                      analysis: Dict[str, Any],
                                      source_file: str) -> GeneratedTest:
        """生成函数测试"""
        test_name = f"test_{func['name']}"
        
        # 生成测试代码
        if self.config.framework == TestFramework.PYTEST:
            test_code = self._generate_pytest_function(func, source_file)
        else:
            test_code = self._generate_unittest_function(func, source_file)
        
        return GeneratedTest(
            test_name=test_name,
            test_type=TestType.UNIT,
            test_code=test_code,
            target_function=func["name"],
            coverage_estimate=0.7,
            dependencies=[]
        )
    
    async def _generate_class_test(self, cls: Dict[str, Any],
                                   analysis: Dict[str, Any],
                                   source_file: str) -> GeneratedTest:
        """生成类测试"""
        test_name = f"Test{cls['name']}"
        
        # 生成测试代码
        if self.config.framework == TestFramework.PYTEST:
            test_code = self._generate_pytest_class(cls, source_file)
        else:
            test_code = self._generate_unittest_class(cls, source_file)
        
        return GeneratedTest(
            test_name=test_name,
            test_type=TestType.UNIT,
            test_code=test_code,
            target_function=cls["name"],
            coverage_estimate=0.6,
            dependencies=[]
        )
    
    def _generate_pytest_function(self, func: Dict[str, Any], 
                                  source_file: str) -> str:
        """生成pytest函数测试"""
        func_name = func["name"]
        args = func["args"]
        
        # 导入
        import_line = ""
        if source_file:
            module_name = os.path.splitext(os.path.basename(source_file))[0]
            import_line = f"from {module_name} import {func_name}"
        
        # 参数准备
        param_setup = []
        for arg in args:
            if arg["name"] == "self":
                continue
            param_setup.append(f"    {arg['name']} = None  # TODO: 设置测试值")
        
        param_setup_str = "\n".join(param_setup)
        
        # 测试代码
        test_code = f'''
{import_line}

def test_{func_name}():
    """测试 {func_name} 函数"""
    # 准备测试数据
{param_setup_str}
    
    # 执行测试
    result = {func_name}({", ".join(a["name"] for a in args if a["name"] != "self")})
    
    # 验证结果
    assert result is not None  # TODO: 添加具体断言


def test_{func_name}_edge_cases():
    """测试 {func_name} 边界情况"""
    # 测试空输入
    # 测试边界值
    # 测试异常情况
    pass
'''
        
        return textwrap.dedent(test_code).strip()
    
    def _generate_pytest_class(self, cls: Dict[str, Any],
                               source_file: str) -> str:
        """生成pytest类测试"""
        class_name = cls["name"]
        
        # 导入
        import_line = ""
        if source_file:
            module_name = os.path.splitext(os.path.basename(source_file))[0]
            import_line = f"from {module_name} import {class_name}"
        
        # 方法测试
        method_tests = []
        for method in cls["methods"]:
            if method["name"].startswith("_") and not method["name"].startswith("__"):
                continue
            
            method_test = f'''
def test_{method["name"]}(self):
    """测试 {method["name"]} 方法"""
    instance = {class_name}()
    # TODO: 设置测试参数
    result = instance.{method["name"]}()
    assert result is not None
'''
            method_tests.append(method_test)
        
        method_tests_str = "\n".join(method_tests)
        
        test_code = f'''
{import_line}

class Test{class_name}:
    """测试 {class_name} 类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.instance = {class_name}()
    
    def teardown_method(self):
        """每个测试方法后的清理"""
        pass
    
{method_tests_str}
'''
        
        return textwrap.dedent(test_code).strip()
    
    def _generate_unittest_function(self, func: Dict[str, Any],
                                    source_file: str) -> str:
        """生成unittest函数测试"""
        func_name = func["name"]
        
        import_line = ""
        if source_file:
            module_name = os.path.splitext(os.path.basename(source_file))[0]
            import_line = f"from {module_name} import {func_name}"
        
        test_code = f'''
import unittest
{import_line}


class Test{func_name.capitalize()}(unittest.TestCase):
    """测试 {func_name} 函数"""
    
    def test_{func_name}_normal(self):
        """测试正常情况"""
        # TODO: 设置测试参数
        result = {func_name}()
        self.assertIsNotNone(result)
    
    def test_{func_name}_edge_cases(self):
        """测试边界情况"""
        pass


if __name__ == "__main__":
    unittest.main()
'''
        
        return textwrap.dedent(test_code).strip()
    
    def _generate_unittest_class(self, cls: Dict[str, Any],
                                 source_file: str) -> str:
        """生成unittest类测试"""
        class_name = cls["name"]
        
        import_line = ""
        if source_file:
            module_name = os.path.splitext(os.path.basename(source_file))[0]
            import_line = f"from {module_name} import {class_name}"
        
        test_code = f'''
import unittest
{import_line}


class Test{class_name}(unittest.TestCase):
    """测试 {class_name} 类"""
    
    def setUp(self):
        """测试前设置"""
        self.instance = {class_name}()
    
    def tearDown(self):
        """测试后清理"""
        pass
    
    def test_instance(self):
        """测试实例化"""
        self.assertIsInstance(self.instance, {class_name})


if __name__ == "__main__":
    unittest.main()
'''
        
        return textwrap.dedent(test_code).strip()
    
    def _generate_test_file(self, tests: List[GeneratedTest],
                           analysis: Dict[str, Any],
                           source_file: str) -> str:
        """生成完整测试文件"""
        header = f'"""\n自动生成的测试文件\n生成时间: {datetime.now().isoformat()}\n源文件: {source_file or "unknown"}\n"""\n\n'
        
        imports = "import pytest\nimport unittest\nfrom unittest.mock import Mock, patch\n\n"
        
        test_codes = "\n\n".join(t.test_code for t in tests)
        
        return header + imports + test_codes
    
    def _estimate_coverage(self, analysis: Dict[str, Any],
                          tests: List[GeneratedTest]) -> float:
        """估算覆盖率"""
        total_items = analysis["total_functions"] + analysis["total_classes"]
        if total_items == 0:
            return 1.0
        
        covered = len(tests)
        return min(covered / total_items, 1.0)
    
    async def save_tests(self, test_content: str, 
                        test_file_name: str) -> Dict[str, Any]:
        """保存测试文件"""
        test_path = os.path.join(self.config.test_directory, test_file_name)
        
        try:
            with open(test_path, 'w', encoding='utf-8') as f:
                f.write(test_content)
            
            logger.info(f"测试文件已保存: {test_path}")
            return {"status": "success", "path": test_path}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def generate_from_file(self, source_path: str) -> Dict[str, Any]:
        """从文件生成测试"""
        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            return {"status": "error", "error": f"读取文件失败: {e}"}
        
        result = await self.generate_tests(code, source_path)
        
        if result["status"] == "success":
            # 保存测试文件
            test_file_name = f"test_{os.path.basename(source_path)}"
            save_result = await self.save_tests(result["test_file"], test_file_name)
            result["saved_to"] = save_result.get("path")
        
        return result


# 全局实例
test_generator = TestGenerator()


def get_test_generator() -> TestGenerator:
    """获取全局测试生成器"""
    return test_generator
