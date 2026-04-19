#!/usr/bin/env python3
"""
代码开发Agent
"""

import asyncio
import logging
import subprocess
from typing import Dict, Any, Optional

from .base_agent import ProfessionalAgent

logger = logging.getLogger(__name__)


class CodeAgent(ProfessionalAgent):
    """代码开发Agent"""
    
    def __init__(self, agent_id: str = "code_agent"):
        super().__init__(
            agent_id=agent_id,
            name="代码开发Agent",
            description="专注于代码开发、审查和优化的专业Agent"
        )
        
        # 添加技能
        self.add_skill("code_generation")
        self.add_skill("code_review")
        self.add_skill("code_optimization")
        self.add_skill("bug_fixing")
        self.add_skill("code_documentation")
        
        # 添加能力
        self.add_capability("python")
        self.add_capability("javascript")
        self.add_capability("typescript")
        self.add_capability("java")
        self.add_capability("c++")
        self.add_capability("go")
        
        # 代码执行缓存
        self.code_execution_cache = {}
        self.max_cache_size = 100
    
    async def process_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理代码相关任务"""
        try:
            # 分析任务类型
            task_lower = task.lower()
            
            if "生成代码" in task_lower or "write code" in task_lower:
                return await self._generate_code(task, context)
            elif "审查代码" in task_lower or "code review" in task_lower:
                return await self._review_code(task, context)
            elif "优化代码" in task_lower or "optimize code" in task_lower:
                return await self._optimize_code(task, context)
            elif "修复bug" in task_lower or "fix bug" in task_lower:
                return await self._fix_bug(task, context)
            elif "文档" in task_lower or "documentation" in task_lower:
                return await self._generate_documentation(task, context)
            else:
                return await self._handle_generic_code_task(task, context)
        except Exception as e:
            logger.error(f"处理代码任务失败: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _generate_code(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成代码"""
        # 这里应该调用LLM生成代码
        # 简化示例
        code = f"""# 生成的代码
# 任务: {task}

def example_function():
    "示例函数"
    print("Hello, World!")
"""
        
        return {
            "status": "success",
            "code": code,
            "language": "python",
            "explanation": "根据任务生成的代码"
        }
    
    async def _review_code(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """审查代码"""
        code = context.get("code", "") if context else ""
        
        # 分析代码
        review_comments = []
        
        if not code:
            review_comments.append("未提供代码")
        else:
            # 简单的代码审查
            if "print(" in code:
                review_comments.append("建议使用日志系统而非print语句")
            if "def " in code and """""" not in code:
                review_comments.append("建议为函数添加文档字符串")
        
        return {
            "status": "success",
            "review_comments": review_comments,
            "code_quality": "中等" if review_comments else "良好"
        }
    
    async def _optimize_code(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """优化代码"""
        code = context.get("code", "") if context else ""
        
        if not code:
            return {
                "status": "error",
                "error": "未提供代码"
            }
        
        # 简单的代码优化
        optimized_code = code
        
        # 示例优化
        if "for i in range(len(" in optimized_code:
            optimized_code = optimized_code.replace("for i in range(len(", "for i, ")
        
        return {
            "status": "success",
            "original_code": code,
            "optimized_code": optimized_code,
            "optimization_techniques": ["循环优化"]
        }
    
    async def _fix_bug(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """修复bug"""
        code = context.get("code", "") if context else ""
        error_message = context.get("error", "") if context else ""
        
        if not code:
            return {
                "status": "error",
                "error": "未提供代码"
            }
        
        # 简单的bug修复
        fixed_code = code
        
        # 示例修复
        if "ZeroDivisionError" in error_message and "/ 0" in code:
            fixed_code = fixed_code.replace("/ 0", "/ 1")
        
        return {
            "status": "success",
            "original_code": code,
            "fixed_code": fixed_code,
            "bug_description": error_message,
            "fix_description": "修复了除零错误"
        }
    
    async def _generate_documentation(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成文档"""
        code = context.get("code", "") if context else ""
        
        if not code:
            return {
                "status": "error",
                "error": "未提供代码"
            }
        
        # 生成文档
        documentation = f"""# 代码文档

## 功能描述
根据代码自动生成的文档

## 代码分析
```python
{code}
```

## 函数说明
- 函数1: 功能描述
- 函数2: 功能描述
"""
        
        return {
            "status": "success",
            "documentation": documentation,
            "format": "markdown"
        }
    
    async def _handle_generic_code_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理通用代码任务"""
        return {
            "status": "success",
            "response": f"代码开发Agent正在处理任务: {task}",
            "agent_id": self.agent_id
        }
    
    async def execute_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """执行代码"""
        try:
            # 检查缓存
            cache_key = f"{language}:{hash(code)}"
            if cache_key in self.code_execution_cache:
                return self.code_execution_cache[cache_key]
            
            if language == "python":
                # 执行Python代码
                result = subprocess.run(
                    ["python", "-c", code],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                execution_result = {
                    "status": "success" if result.returncode == 0 else "error",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
                
                # 更新缓存
                if len(self.code_execution_cache) >= self.max_cache_size:
                    # 移除最早的缓存项
                    oldest_key = next(iter(self.code_execution_cache))
                    del self.code_execution_cache[oldest_key]
                self.code_execution_cache[cache_key] = execution_result
                
                return execution_result
            else:
                return {
                    "status": "error",
                    "error": f"不支持的语言: {language}"
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


# 全局代码Agent实例
_code_agent = None

def get_code_agent() -> CodeAgent:
    """获取代码Agent实例"""
    global _code_agent
    if _code_agent is None:
        _code_agent = CodeAgent()
    return _code_agent