"""
错误调试模块
实现代码错误分析、定位、修复建议生成功能
整合 002/AAagent 的优秀实现
"""

import re
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """错误类型枚举"""
    SYNTAX_ERROR = "syntax_error"
    RUNTIME_ERROR = "runtime_error"
    IMPORT_ERROR = "import_error"
    NAME_ERROR = "name_error"
    TYPE_ERROR = "type_error"
    VALUE_ERROR = "value_error"
    INDEX_ERROR = "index_error"
    KEY_ERROR = "key_error"
    ATTRIBUTE_ERROR = "attribute_error"
    IO_ERROR = "io_error"
    PERMISSION_ERROR = "permission_error"
    TIMEOUT_ERROR = "timeout_error"
    MEMORY_ERROR = "memory_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorSeverity(Enum):
    """错误严重程度枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ErrorAnalysis:
    """错误分析结果数据类"""
    error_type: str
    error_message: str
    error_location: str
    severity: str
    root_cause: str
    suggested_fixes: List[str]
    related_code: str


class ErrorDebugger:
    """错误调试器类"""
    
    def __init__(self):
        self.error_patterns = self._load_error_patterns()
        self.fix_templates = self._load_fix_templates()
        logger.info("错误调试器初始化完成")
    
    def _load_error_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """加载错误模式识别规则"""
        return {
            "python": [
                {
                    "pattern": r"SyntaxError: (.+)",
                    "error_type": ErrorType.SYNTAX_ERROR.value,
                    "severity": ErrorSeverity.HIGH.value,
                    "description": "语法错误"
                },
                {
                    "pattern": r"NameError: name '([^']+)' is not defined",
                    "error_type": ErrorType.NAME_ERROR.value,
                    "severity": ErrorSeverity.MEDIUM.value,
                    "description": "名称未定义错误"
                },
                {
                    "pattern": r"TypeError: (.+)",
                    "error_type": ErrorType.TYPE_ERROR.value,
                    "severity": ErrorSeverity.MEDIUM.value,
                    "description": "类型错误"
                },
                {
                    "pattern": r"ValueError: (.+)",
                    "error_type": ErrorType.VALUE_ERROR.value,
                    "severity": ErrorSeverity.MEDIUM.value,
                    "description": "值错误"
                },
                {
                    "pattern": r"IndexError: list index out of range",
                    "error_type": ErrorType.INDEX_ERROR.value,
                    "severity": ErrorSeverity.MEDIUM.value,
                    "description": "索引越界错误"
                },
                {
                    "pattern": r"KeyError: '([^']+)'",
                    "error_type": ErrorType.KEY_ERROR.value,
                    "severity": ErrorSeverity.MEDIUM.value,
                    "description": "字典键不存在错误"
                },
                {
                    "pattern": r"AttributeError: '([^']+)' object has no attribute '([^']+)'",
                    "error_type": ErrorType.ATTRIBUTE_ERROR.value,
                    "severity": ErrorSeverity.MEDIUM.value,
                    "description": "属性错误"
                },
                {
                    "pattern": r"(ImportError|ModuleNotFoundError): (.+)",
                    "error_type": ErrorType.IMPORT_ERROR.value,
                    "severity": ErrorSeverity.HIGH.value,
                    "description": "导入/模块未找到错误"
                },
                {
                    "pattern": r"(IOError|FileNotFoundError): (.+)",
                    "error_type": ErrorType.IO_ERROR.value,
                    "severity": ErrorSeverity.HIGH.value,
                    "description": "IO/文件未找到错误"
                },
                {
                    "pattern": r"PermissionError: (.+)",
                    "error_type": ErrorType.PERMISSION_ERROR.value,
                    "severity": ErrorSeverity.HIGH.value,
                    "description": "权限错误"
                }
            ],
            "javascript": [
                {
                    "pattern": r"SyntaxError: (.+)",
                    "error_type": ErrorType.SYNTAX_ERROR.value,
                    "severity": ErrorSeverity.HIGH.value,
                    "description": "语法错误"
                },
                {
                    "pattern": r"ReferenceError: (.+) is not defined",
                    "error_type": ErrorType.NAME_ERROR.value,
                    "severity": ErrorSeverity.MEDIUM.value,
                    "description": "引用错误"
                },
                {
                    "pattern": r"TypeError: (.+)",
                    "error_type": ErrorType.TYPE_ERROR.value,
                    "severity": ErrorSeverity.MEDIUM.value,
                    "description": "类型错误"
                },
                {
                    "pattern": r"RangeError: (.+)",
                    "error_type": ErrorType.VALUE_ERROR.value,
                    "severity": ErrorSeverity.MEDIUM.value,
                    "description": "范围错误"
                }
            ]
        }
    
    def _load_fix_templates(self) -> Dict[str, List[str]]:
        """加载修复方案模板"""
        return {
            ErrorType.SYNTAX_ERROR.value: [
                "检查代码的语法结构，确保所有括号、引号、逗号等符号都正确配对",
                "查看错误提示中的行号和位置，重点检查该行附近的代码",
                "检查是否缺少冒号、引号或括号",
                "使用代码编辑器的语法高亮功能辅助检查"
            ],
            ErrorType.NAME_ERROR.value: [
                "确保变量或函数名拼写正确",
                "检查变量是否在使用前已经定义",
                "如果是导入的模块，确保已经正确导入",
                "检查作用域问题，确保变量在当前作用域内可见"
            ],
            ErrorType.TYPE_ERROR.value: [
                "检查操作数的类型是否匹配",
                "使用type()函数检查变量类型",
                "确保函数调用时传入了正确类型的参数",
                "考虑使用类型转换函数（如int()、str()等）"
            ],
            ErrorType.VALUE_ERROR.value: [
                "检查输入值是否符合函数或方法的要求",
                "查看错误信息中提到的具体值和期望范围",
                "添加输入验证逻辑",
                "使用try-except块捕获并处理异常"
            ],
            ErrorType.INDEX_ERROR.value: [
                "检查列表或字符串的长度是否足够",
                "确保索引值在有效范围内（0到长度-1）",
                "使用len()函数获取长度信息",
                "考虑使用条件判断避免越界访问"
            ],
            ErrorType.KEY_ERROR.value: [
                "检查字典中是否存在指定的键",
                "使用in关键字检查键是否存在",
                "考虑使用dict.get()方法提供默认值",
                "检查键的拼写是否正确"
            ],
            ErrorType.ATTRIBUTE_ERROR.value: [
                "检查对象是否确实具有该属性",
                "查看类的定义，确认属性是否存在",
                "检查属性名的拼写",
                "考虑对象是否为None或其他不包含该属性的类型"
            ],
            ErrorType.IMPORT_ERROR.value: [
                "确保模块已经安装：pip install 模块名",
                "检查导入路径是否正确",
                "确认模块名称拼写正确",
                "检查Python环境和路径设置"
            ],
            ErrorType.IO_ERROR.value: [
                "检查文件路径是否正确",
                "确认文件是否存在",
                "检查文件权限",
                "确保磁盘空间充足"
            ],
            ErrorType.PERMISSION_ERROR.value: [
                "检查文件或目录的权限设置",
                "以管理员或适当权限运行程序",
                "确认当前用户是否有权限访问该资源",
                "考虑修改文件权限"
            ]
        }
    
    def analyze_error(self, error_message: str, code: str, language: str = "python") -> ErrorAnalysis:
        """分析错误信息并提供修复建议"""
        if language not in self.error_patterns:
            return ErrorAnalysis(
                error_type=ErrorType.UNKNOWN_ERROR.value,
                error_message=error_message,
                error_location="未知",
                severity=ErrorSeverity.MEDIUM.value,
                root_cause="无法识别的错误类型",
                suggested_fixes=["请提供更多上下文信息以便进一步分析"],
                related_code=""
            )
        
        # 识别错误类型
        error_type = ErrorType.UNKNOWN_ERROR.value
        severity = ErrorSeverity.MEDIUM.value
        root_cause = "未知错误"
        
        for pattern_info in self.error_patterns[language]:
            match = re.search(pattern_info["pattern"], error_message)
            if match:
                error_type = pattern_info["error_type"]
                severity = pattern_info["severity"]
                root_cause = pattern_info["description"]
                break
        
        # 提取错误位置
        error_location = self._extract_error_location(error_message)
        
        # 获取相关代码
        related_code = self._extract_related_code(code, error_location)
        
        # 生成修复建议
        suggested_fixes = self._generate_suggested_fixes(error_type, error_message, code)
        
        logger.info(f"分析错误完成：{error_type} - {root_cause}")
        
        return ErrorAnalysis(
            error_type=error_type,
            error_message=error_message,
            error_location=error_location,
            severity=severity,
            root_cause=root_cause,
            suggested_fixes=suggested_fixes,
            related_code=related_code
        )
    
    def _extract_error_location(self, error_message: str) -> str:
        """提取错误位置信息"""
        line_match = re.search(r"line (\d+)", error_message)
        if line_match:
            return f"第 {line_match.group(1)} 行"
        
        file_match = re.search(r'File "([^"]+)"', error_message)
        if file_match:
            file_path = file_match.group(1)
            file_name = os.path.basename(file_path)
            return f"文件: {file_name}"
        
        return "未知位置"
    
    def _extract_related_code(self, code: str, error_location: str) -> str:
        """提取相关代码片段"""
        line_match = re.search(r"第 (\d+) 行", error_location)
        if line_match:
            line_number = int(line_match.group(1))
            lines = code.split('\n')
            
            start_line = max(0, line_number - 3)
            end_line = min(len(lines), line_number + 2)
            
            context = []
            for i in range(start_line, end_line):
                line_num = i + 1
                marker = " >> " if line_num == line_number else "    "
                context.append(f"{marker}{line_num:3d}: {lines[i]}")
            
            return "\n".join(context)
        
        return "无法提取相关代码"
    
    def _generate_suggested_fixes(self, error_type: str, error_message: str, code: str) -> List[str]:
        """生成修复建议"""
        fixes = []
        
        # 从模板中获取通用建议
        if error_type in self.fix_templates:
            fixes.extend(self.fix_templates[error_type])
        
        # 根据具体错误信息提供更具体的建议
        if error_type == ErrorType.NAME_ERROR.value:
            name_match = re.search(r"name '([^']+)' is not defined", error_message)
            if name_match:
                var_name = name_match.group(1)
                fixes.append(f"检查变量 '{var_name}' 是否在使用前已定义")
                
                if var_name.lower() in code.lower():
                    fixes.append(f"可能是拼写错误，请检查 '{var_name}' 的拼写")
        
        elif error_type == ErrorType.IMPORT_ERROR.value:
            module_match = re.search(r"No module named '([^']+)'|cannot import name '([^']+)'", error_message)
            if module_match:
                module_name = module_match.group(1) or module_match.group(2)
                fixes.append(f"请安装缺失的模块: pip install {module_name}")
        
        elif error_type == ErrorType.INDEX_ERROR.value:
            if "[" in code and "]" in code:
                fixes.append("确保列表索引在有效范围内")
                fixes.append("使用len()函数检查列表长度")
        
        elif error_type == ErrorType.KEY_ERROR.value:
            key_match = re.search(r"KeyError: '([^']+)'", error_message)
            if key_match:
                key_name = key_match.group(1)
                fixes.append(f"检查字典中是否存在键 '{key_name}'")
                fixes.append(f"使用 dict.get('{key_name}', 默认值) 避免 KeyError")
        
        elif error_type == ErrorType.TYPE_ERROR.value:
            if "int" in error_message and "str" in error_message:
                fixes.append("可能是字符串和数字混合操作，请进行类型转换")
            elif "NoneType" in error_message:
                fixes.append("检查变量是否为None，可能需要添加None检查")
        
        return fixes[:5]  # 最多返回5条建议
    
    def suggest_code_fix(self, code: str, error_analysis: ErrorAnalysis) -> str:
        """根据错误分析提供代码修复建议"""
        if error_analysis.error_type == ErrorType.SYNTAX_ERROR.value:
            return self._fix_syntax_error(code)
        elif error_analysis.error_type == ErrorType.NAME_ERROR.value:
            return self._fix_name_error(code, error_analysis.error_message)
        elif error_analysis.error_type == ErrorType.TYPE_ERROR.value:
            return self._fix_type_error(error_analysis.error_message)
        elif error_analysis.error_type == ErrorType.INDEX_ERROR.value:
            return self._fix_index_error(code)
        elif error_analysis.error_type == ErrorType.KEY_ERROR.value:
            return self._fix_key_error(error_analysis.error_message)
        else:
            return "无法自动修复此类型的错误，请根据建议手动修改"
    
    def _fix_syntax_error(self, code: str) -> str:
        """修复语法错误"""
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            # 检查是否缺少冒号
            if re.search(r'^\s*(if|elif|else|for|while|def|class)\s+.+$', line) and not line.strip().endswith(':'):
                lines[i] = line + ':'
                return '\n'.join(lines)
        
        return "无法自动修复语法错误，请根据错误信息手动检查"
    
    def _fix_name_error(self, code: str, error_message: str) -> str:
        """修复名称未定义错误"""
        name_match = re.search(r"name '([^']+)' is not defined", error_message)
        if not name_match:
            return "无法识别未定义的名称"
        
        var_name = name_match.group(1)
        similar_vars = []
        lines = code.split('\n')
        
        for line in lines:
            words = re.findall(r'\b[a-zA-Z_]\w*\b', line)
            for word in words:
                if word != var_name and self._levenshtein_distance(word, var_name) <= 2:
                    similar_vars.append(word)
        
        if similar_vars:
            return f"可能的拼写错误：{'、'.join(similar_vars)}"
        
        return f"请在使用变量 '{var_name}' 前先定义它"
    
    def _fix_type_error(self, error_message: str) -> str:
        """修复类型错误"""
        if "int" in error_message and "str" in error_message:
            return "可能是字符串和数字混合操作，建议使用int()或str()进行类型转换"
        elif "NoneType" in error_message:
            return "检查变量是否为None，建议添加None检查"
        else:
            return "请检查操作数的类型是否匹配"
    
    def _fix_index_error(self, code: str) -> str:
        """修复索引越界错误"""
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            if "[" in line and "]" in line:
                return f"在第{i+1}行，建议添加列表长度检查：\nif len(列表名) > 索引值:  # 访问列表"
        
        return "无法定位具体的列表访问操作"
    
    def _fix_key_error(self, error_message: str) -> str:
        """修复键错误"""
        key_match = re.search(r"KeyError: '([^']+)'", error_message)
        if not key_match:
            return "无法识别缺失的键"
        
        key_name = key_match.group(1)
        return f"建议使用字典的get方法：字典名.get('{key_name}', 默认值)"
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """计算两个字符串的编辑距离"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def generate_debug_report(self, error_analysis: ErrorAnalysis) -> str:
        """生成调试报告"""
        report_lines = [
            "=" * 60,
            "错误调试报告",
            "=" * 60,
            f"错误类型: {error_analysis.error_type}",
            f"严重程度: {error_analysis.severity}",
            f"错误位置: {error_analysis.error_location}",
            f"错误信息: {error_analysis.error_message}",
            f"根本原因: {error_analysis.root_cause}",
            "",
            "相关代码:",
            "-" * 40,
            error_analysis.related_code or "无相关代码",
            "-" * 40,
            "",
            "修复建议:"
        ]
        
        for i, fix in enumerate(error_analysis.suggested_fixes, 1):
            report_lines.append(f"  {i}. {fix}")
        
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)


error_debugger = ErrorDebugger()
