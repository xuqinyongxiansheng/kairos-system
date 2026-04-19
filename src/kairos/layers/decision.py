"""
决策层
负责做出决策和规划
使用 Ollama LLM 进行推理决策，替代关键词匹配
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DecisionLayer:
    """决策层 - 使用 LLM 推理制定决策"""

    def __init__(self):
        self.decision_history = []
        self.active_plans = []
        self._llm_enabled = True

    async def make_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于上下文做出决策，优先使用 LLM 推理
        """
        try:
            logger.info(f"开始决策，上下文：{context.get('type', 'unknown')}")

            llm_result = await self._llm_decide(context)

            decision = {
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                'decision_type': llm_result.get('action', '对话响应'),
                'action': llm_result.get('action', '对话响应'),
                'priority': context.get('priority', 'normal'),
                'confidence': llm_result.get('confidence', 0.5),
                'reasoning': llm_result.get('reasoning', ''),
                'requires_tools': llm_result.get('requires_tools', False),
                'tool_suggestion': llm_result.get('tool_suggestion', ''),
                'llm_powered': llm_result.get('confidence', 0) > 0.3,
            }

            self.decision_history.append(decision)

            logger.info(f"决策完成：{decision['action']} (置信度:{decision['confidence']})")
            return decision

        except Exception as e:
            logger.error(f"决策层处理失败：{e}")
            return {'status': 'error', 'error': str(e)}

    async def _llm_decide(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """使用 LLM 进行推理决策"""
        if not self._llm_enabled:
            return self._keyword_fallback(context)

        try:
            from kairos.system.llm_reasoning import llm_decide
            return await llm_decide(context)
        except ImportError:
            self._llm_enabled = False
            return self._keyword_fallback(context)
        except Exception as e:
            logger.warning(f"LLM 决策失败，回退到关键词模式: {e}")
            return self._keyword_fallback(context)

    def _keyword_fallback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """关键词回退"""
        content = str(context.get('content', '')).lower()
        if any(kw in content for kw in ['搜索', '查找', 'search', 'find']):
            return {'action': '搜索', 'reasoning': '关键词匹配', 'confidence': 0.3, 'requires_tools': True, 'tool_suggestion': 'search'}
        if any(kw in content for kw in ['创建', '新建', 'create', 'write']):
            return {'action': '创建', 'reasoning': '关键词匹配', 'confidence': 0.3, 'requires_tools': True, 'tool_suggestion': 'file_write'}
        return {'action': '对话响应', 'reasoning': '关键词匹配回退', 'confidence': 0.3, 'requires_tools': False, 'tool_suggestion': ''}

    async def create_plan(self, goal: str, steps: List[str] = None) -> Dict[str, Any]:
        """创建执行计划"""
        plan = {
            'goal': goal,
            'steps': steps or [goal],
            'created_at': datetime.now().isoformat(),
            'status': 'pending'
        }
        self.active_plans.append(plan)
        return plan

    async def get_decision_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取决策历史"""
        return self.decision_history[-limit:]
