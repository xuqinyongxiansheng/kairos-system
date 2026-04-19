"""
代码重构工具
提供代码质量分析、自动重构、性能优化建议
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

logger = logging.getLogger("RefactoringTool")


class IssueSeverity(Enum):
    """问题严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IssueCategory(Enum):
    """问题类别"""
    CODE_SMELL = "code_smell"
    COMPLEXITY = "complexity"
    DUPLICATION = "duplication"
    NAMING = "naming"
    PERFORMANCE = "performance"
    SECURITY = "security"
    STYLE = "style"
    MAINTAINABILITY = "maintainability"


@dataclass
class CodeIssue:
    """代码问题"""
    id: str
    category: IssueCategory
    severity: IssueSeverity
    message: str
    file: str
    line: int
    column: int
    suggestion: str
    auto_fixable: bool = False


@dataclass
class RefactoringAction:
    """重构动作"""
    action_type: str
    description: str
    original_code: str
    suggested_code: str
    line_start: int
    line_end: int
    confidence: float


@dataclass
class RefactoringConfig:
    """重构配置"""
    max_line_length: int = 100
    max_complexity: int = 10
    max_function_length: int = 50
    max_class_length: int = 300
    min_variable_name_length: int = 2
    enable_auto_fix: bool = True


class RefactoringTool:
    """
    代码重构工具
    
    功能:
    - 代码异味检测
    - 复杂度分析
    - 自动重构建议
    - 性能优化建议
    - 命名规范检查
    """
    
    def __init__(self, config: RefactoringConfig = None):
        self.config = config or RefactoringConfig()
        self.issues: List[CodeIssue] = []
        self.actions: List[RefactoringAction] = []
        
        logger.info("代码重构工具初始化")
    
    async def analyze(self, code: str, file_path: str = None) -> Dict[str, Any]:
        """
        分析代码质量
        
        Args:
            code: 源代码
            file_path: 文件路径
            
        Returns:
            分析结果
        """
        self.issues = []
        self.actions = []
        
        file_path = file_path or "unknown"
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "status": "error",
                "error": f"语法错误: {e}",
                "issues": [],
                "actions": []
            }
        
        # 运行各种检查
        self._check_line_length(code, file_path)
        self._check_complexity(tree, file_path)
        self._check_function_length(tree, file_path)
        self._check_naming(tree, file_path)
        self._check_imports(tree, file_path)
        self._check_code_smells(tree, file_path, code)
        
        # 计算质量分数
        quality_score = self._calculate_quality_score()
        
        return {
            "status": "success",
            "issues": [self._issue_to_dict(i) for i in self.issues],
            "actions": [self._action_to_dict(a) for a in self.actions],
            "quality_score": quality_score,
            "summary": {
                "total_issues": len(self.issues),
                "by_severity": self._count_by_severity(),
                "by_category": self._count_by_category(),
                "auto_fixable": sum(1 for i in self.issues if i.auto_fixable)
            }
        }
    
    def _issue_to_dict(self, issue: CodeIssue) -> Dict[str, Any]:
        """转换问题为字典"""
        return {
            "id": issue.id,
            "category": issue.category.value,
            "severity": issue.severity.value,
            "message": issue.message,
            "file": issue.file,
            "line": issue.line,
            "column": issue.column,
            "suggestion": issue.suggestion,
            "auto_fixable": issue.auto_fixable
        }
    
    def _action_to_dict(self, action: RefactoringAction) -> Dict[str, Any]:
        """转换动作为字典"""
        return {
            "action_type": action.action_type,
            "description": action.description,
            "original_code": action.original_code,
            "suggested_code": action.suggested_code,
            "line_start": action.line_start,
            "line_end": action.line_end,
            "confidence": action.confidence
        }
    
    def _check_line_length(self, code: str, file_path: str):
        """检查行长度"""
        for i, line in enumerate(code.split('\n'), 1):
            if len(line) > self.config.max_line_length:
                self.issues.append(CodeIssue(
                    id=f"LINE_{i}",
                    category=IssueCategory.STYLE,
                    severity=IssueSeverity.WARNING,
                    message=f"行长度超过 {self.config.max_line_length} 字符",
                    file=file_path,
                    line=i,
                    column=self.config.max_line_length,
                    suggestion="将长行拆分为多行",
                    auto_fixable=False
                ))
    
    def _check_complexity(self, tree: ast.AST, file_path: str):
        """检查复杂度"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = self._calculate_cyclomatic_complexity(node)
                
                if complexity > self.config.max_complexity:
                    self.issues.append(CodeIssue(
                        id=f"COMPLEX_{node.name}",
                        category=IssueCategory.COMPLEXITY,
                        severity=IssueSeverity.WARNING,
                        message=f"函数 '{node.name}' 复杂度过高 ({complexity})",
                        file=file_path,
                        line=node.lineno,
                        column=0,
                        suggestion="将复杂函数拆分为多个小函数",
                        auto_fixable=False
                    ))
    
    def _calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """计算圈复杂度"""
        complexity = 1
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
        
        return complexity
    
    def _check_function_length(self, tree: ast.AST, file_path: str):
        """检查函数长度"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if hasattr(node, 'end_lineno') and node.end_lineno:
                    length = node.end_lineno - node.lineno + 1
                    
                    if length > self.config.max_function_length:
                        self.issues.append(CodeIssue(
                            id=f"LONG_FUNC_{node.name}",
                            category=IssueCategory.MAINTAINABILITY,
                            severity=IssueSeverity.WARNING,
                            message=f"函数 '{node.name}' 过长 ({length} 行)",
                            file=file_path,
                            line=node.lineno,
                            column=0,
                            suggestion="将长函数拆分为多个小函数",
                            auto_fixable=False
                        ))
    
    def _check_naming(self, tree: ast.AST, file_path: str):
        """检查命名规范"""
        for node in ast.walk(tree):
            # 函数命名
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.islower() and not node.name.startswith('_'):
                    if '_' not in node.name and not node.name.isupper():
                        self.issues.append(CodeIssue(
                            id=f"NAMING_FUNC_{node.name}",
                            category=IssueCategory.NAMING,
                            severity=IssueSeverity.INFO,
                            message=f"函数名 '{node.name}' 应使用 snake_case",
                            file=file_path,
                            line=node.lineno,
                            column=node.col_offset,
                            suggestion=f"重命名为 '{self._to_snake_case(node.name)}'",
                            auto_fixable=False
                        ))
            
            # 类命名
            elif isinstance(node, ast.ClassDef):
                if not node.name[0].isupper():
                    self.issues.append(CodeIssue(
                        id=f"NAMING_CLASS_{node.name}",
                        category=IssueCategory.NAMING,
                        severity=IssueSeverity.INFO,
                        message=f"类名 '{node.name}' 应使用 PascalCase",
                        file=file_path,
                        line=node.lineno,
                        column=node.col_offset,
                        suggestion=f"重命名为 '{self._to_pascal_case(node.name)}'",
                        auto_fixable=False
                    ))
            
            # 变量命名
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        if len(name) < self.config.min_variable_name_length and not name.startswith('_'):
                            self.issues.append(CodeIssue(
                                id=f"NAMING_VAR_{name}",
                                category=IssueCategory.NAMING,
                                severity=IssueSeverity.INFO,
                                message=f"变量名 '{name}' 过短",
                                file=file_path,
                                line=node.lineno,
                                column=node.col_offset,
                                suggestion="使用更具描述性的名称",
                                auto_fixable=False
                            ))
    
    def _check_imports(self, tree: ast.AST, file_path: str):
        """检查导入"""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append((node.module, node.lineno))
        
        # 检查重复导入
        seen = set()
        for imp, line in imports:
            if imp in seen:
                self.issues.append(CodeIssue(
                    id=f"DUP_IMPORT_{imp}",
                    category=IssueCategory.STYLE,
                    severity=IssueSeverity.WARNING,
                    message=f"重复导入 '{imp}'",
                    file=file_path,
                    line=line,
                    column=0,
                    suggestion="移除重复导入",
                    auto_fixable=True
                ))
            seen.add(imp)
    
    def _check_code_smells(self, tree: ast.AST, file_path: str, code: str):
        """检查代码异味"""
        for node in ast.walk(tree):
            # 检查空的 if/else
            if isinstance(node, ast.If):
                if len(node.body) == 0 or (len(node.body) == 1 and 
                    isinstance(node.body[0], ast.Pass)):
                    self.issues.append(CodeIssue(
                        id=f"EMPTY_IF_{node.lineno}",
                        category=IssueCategory.CODE_SMELL,
                        severity=IssueSeverity.WARNING,
                        message="空的 if 语句",
                        file=file_path,
                        line=node.lineno,
                        column=0,
                        suggestion="移除空的 if 语句或添加逻辑",
                        auto_fixable=True
                    ))
            
            # 检查裸 except
            elif isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    self.issues.append(CodeIssue(
                        id=f"BARE_EXCEPT_{node.lineno}",
                        category=IssueCategory.CODE_SMELL,
                        severity=IssueSeverity.WARNING,
                        message="裸 except 语句",
                        file=file_path,
                        line=node.lineno,
                        column=0,
                        suggestion="指定具体的异常类型",
                        auto_fixable=False
                    ))
            
            # 检查 pass 语句
            elif isinstance(node, ast.Pass):
                # pass 本身不是问题，但在某些上下文中可能是
                pass
    
    def _to_snake_case(self, name: str) -> str:
        """转换为 snake_case"""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _to_pascal_case(self, name: str) -> str:
        """转换为 PascalCase"""
        return ''.join(word.capitalize() for word in name.split('_'))
    
    def _calculate_quality_score(self) -> float:
        """计算质量分数"""
        if not self.issues:
            return 100.0
        
        # 根据问题严重程度扣分
        deductions = {
            IssueSeverity.INFO: 1,
            IssueSeverity.WARNING: 3,
            IssueSeverity.ERROR: 5,
            IssueSeverity.CRITICAL: 10
        }
        
        total_deduction = sum(deductions.get(i.severity, 0) for i in self.issues)
        
        return max(0, 100 - total_deduction)
    
    def _count_by_severity(self) -> Dict[str, int]:
        """按严重程度统计"""
        counts = {}
        for issue in self.issues:
            sev = issue.severity.value
            counts[sev] = counts.get(sev, 0) + 1
        return counts
    
    def _count_by_category(self) -> Dict[str, int]:
        """按类别统计"""
        counts = {}
        for issue in self.issues:
            cat = issue.category.value
            counts[cat] = counts.get(cat, 0) + 1
        return counts
    
    async def suggest_refactoring(self, code: str, 
                                 file_path: str = None) -> Dict[str, Any]:
        """
        生成重构建议
        
        Args:
            code: 源代码
            file_path: 文件路径
            
        Returns:
            重构建议
        """
        analysis = await self.analyze(code, file_path)
        
        suggestions = []
        
        for issue in self.issues:
            if issue.auto_fixable:
                suggestion = {
                    "issue_id": issue.id,
                    "description": issue.suggestion,
                    "line": issue.line,
                    "auto_fixable": True
                }
                suggestions.append(suggestion)
        
        return {
            "status": "success",
            "suggestions": suggestions,
            "quality_score": analysis["quality_score"]
        }
    
    async def auto_fix(self, code: str, file_path: str = None) -> Dict[str, Any]:
        """
        自动修复问题
        
        Args:
            code: 源代码
            file_path: 文件路径
            
        Returns:
            修复后的代码
        """
        analysis = await self.analyze(code, file_path)
        
        lines = code.split('\n')
        fixes_applied = 0
        
        # 收集需要删除的行
        lines_to_remove = set()
        
        for issue in self.issues:
            if issue.auto_fixable:
                if "重复导入" in issue.message:
                    lines_to_remove.add(issue.line - 1)
                    fixes_applied += 1
                elif "空的 if 语句" in issue.message:
                    lines_to_remove.add(issue.line - 1)
                    fixes_applied += 1
        
        # 移除标记的行
        fixed_lines = [line for i, line in enumerate(lines) if i not in lines_to_remove]
        fixed_code = '\n'.join(fixed_lines)
        
        return {
            "status": "success",
            "original_code": code,
            "fixed_code": fixed_code,
            "fixes_applied": fixes_applied,
            "remaining_issues": len(self.issues) - fixes_applied
        }
    
    async def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """分析文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            return {"status": "error", "error": f"读取文件失败: {e}"}
        
        return await self.analyze(code, file_path)
    
    async def analyze_directory(self, directory: str, 
                               recursive: bool = True) -> Dict[str, Any]:
        """分析目录"""
        results = {}
        total_issues = 0
        total_score = 0
        
        pattern = os.path.join(directory, "**/*.py") if recursive else os.path.join(directory, "*.py")
        
        import glob
        for file_path in glob.glob(pattern, recursive=recursive):
            result = await self.analyze_file(file_path)
            results[file_path] = result
            
            if result["status"] == "success":
                total_issues += result["summary"]["total_issues"]
                total_score += result["quality_score"]
        
        file_count = len(results)
        avg_score = total_score / file_count if file_count > 0 else 0
        
        return {
            "status": "success",
            "files_analyzed": file_count,
            "total_issues": total_issues,
            "average_quality_score": avg_score,
            "results": results
        }


# 全局实例
refactoring_tool = RefactoringTool()


def get_refactoring_tool() -> RefactoringTool:
    """获取全局重构工具"""
    return refactoring_tool
