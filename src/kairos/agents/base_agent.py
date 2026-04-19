#!/usr/bin/env python3
"""
通用 Agent 基类 - 为所有 Agent 提供基础功能
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("BaseAgent")


class BaseAgent:
    """通用 Agent 基类 - 提供基础功能"""
    
    def __init__(self, agent_name: str, agent_role: str):
        """
        初始化 Agent
        
        Args:
            agent_name: Agent 名称
            agent_role: Agent 角色
        """
        self.agent_name = agent_name
        self.agent_role = agent_role
        self.permissions = {
            "read": [],
            "write": [],
            "execute": []
        }
        self.capabilities = []
        self.workflow = {}
        self.model_config = {}
        
        logger.info(f"{self.agent_name}初始化完成，角色：{self.agent_role}")
    
    def get_agent_info(self) -> Dict[str, Any]:
        """
        获取 Agent 信息
        
        Returns:
            Agent 信息
        """
        return {
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "permissions": self.permissions,
            "capabilities": self.capabilities,
            "workflow": self.workflow,
            "model_config": self.model_config
        }
    
    async def execute(self, task: str, **kwargs) -> Dict[str, Any]:
        """
        执行任务
        
        Args:
            task: 任务描述
            **kwargs: 任务参数
            
        Returns:
            执行结果
        """
        try:
            logger.info(f"{self.agent_name}执行任务：{task[:50]}...")
            
            # 默认实现：返回成功
            return {
                "success": True,
                "message": f"{self.agent_name}完成任务：{task}",
                "agent": self.agent_name
            }
            
        except Exception as e:
            logger.error(f"{self.agent_name}执行任务失败：{e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.agent_name
            }


class TaskLearningMixin:
    """任务学习混入类 - 为 Agent 提供任务学习能力"""

    def __init__(self):
        self._task_patterns: Dict[str, Dict[str, Any]] = {}
        self._task_history: List[Dict[str, Any]] = []

    async def learn_task_pattern(self, pattern: str) -> Dict[str, Any]:
        """
        学习任务模式
        基于任务历史提取模式（频率/成功率/耗时统计）
        """
        try:
            logger.info(f"学习任务模式：{pattern}")

            if pattern not in self._task_patterns:
                self._task_patterns[pattern] = {
                    "count": 0,
                    "success_count": 0,
                    "total_duration": 0.0,
                    "first_seen": datetime.now().isoformat(),
                    "last_seen": datetime.now().isoformat(),
                }

            stats = self._task_patterns[pattern]
            stats["count"] += 1
            stats["last_seen"] = datetime.now().isoformat()

            matching_history = [h for h in self._task_history if h.get("pattern") == pattern]
            if matching_history:
                stats["success_count"] = sum(1 for h in matching_history if h.get("success", False))
                stats["total_duration"] = sum(h.get("duration", 0) for h in matching_history)

            success_rate = stats["success_count"] / stats["count"] if stats["count"] > 0 else 0
            avg_duration = stats["total_duration"] / stats["count"] if stats["count"] > 0 else 0

            return {
                "success": True,
                "message": f"任务模式学习成功：{pattern}",
                "pattern": pattern,
                "stats": {
                    "occurrences": stats["count"],
                    "success_rate": round(success_rate, 4),
                    "avg_duration": round(avg_duration, 2),
                }
            }

        except Exception as e:
            logger.error(f"学习任务模式失败：{e}")
            return {"success": False, "error": str(e)}

    async def search_task_examples(self, query: str) -> Dict[str, Any]:
        """
        搜索任务示例
        基于模式匹配搜索历史任务案例
        """
        try:
            logger.info(f"搜索任务示例：{query}")

            results = []
            query_lower = query.lower()

            for history in self._task_history:
                pattern = history.get("pattern", "").lower()
                if query_lower in pattern or pattern in query_lower:
                    results.append(history)

            for pattern_key, stats in self._task_patterns.items():
                if query_lower in pattern_key.lower():
                    results.append({
                        "pattern": pattern_key,
                        "type": "pattern_stats",
                        "occurrences": stats["count"],
                        "success_rate": stats["success_count"] / stats["count"] if stats["count"] > 0 else 0,
                    })

            return {
                "success": True,
                "message": f"找到 {len(results)} 个任务示例：{query}",
                "query": query,
                "results": results[:10],
                "total": len(results)
            }

        except Exception as e:
            logger.error(f"搜索任务示例失败：{e}")
            return {"success": False, "error": str(e)}

    def record_task_execution(self, pattern: str, success: bool, duration: float):
        """记录任务执行结果"""
        self._task_history.append({
            "pattern": pattern,
            "success": success,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
        })
        if len(self._task_history) > 1000:
            self._task_history = self._task_history[-500:]
