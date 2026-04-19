#!/usr/bin/env python3
"""
价值评估层 - 衡值
负责评估信息的价值和重要性，管理多维度记忆系统
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class EvaluationLayer_HengZhi:
    """
    价值评估层 - 衡值
    角色：价值评估师和记忆管理员
    工作流程：接收整合信息 → 记忆检索 → 价值评估 → 重要性排序 → 输出价值评估结果
    """
    
    def __init__(self):
        self.name = "衡值"
        self.role = "价值评估层"
        self.models = {
            "evaluation": "qwen2.5:3b-instruct-q4_K_M",
            "memory": "Memory 系统",
            "retrieval": "Sonnet 记忆检索员"
        }
        self.memory_priorities = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.5,
            "low": 0.2
        }
        self.evaluation_history = []
    
    async def evaluate_value(self, integrated_info: Dict[str, Any]) -> Dict[str, Any]:
        """评估整合信息的价值"""
        try:
            memory_results = self._retrieve_relevant_memories(integrated_info)
            value_scores = self._assess_information_value(integrated_info, memory_results)
            prioritized_info = self._prioritize_information(integrated_info, value_scores)
            evaluation_report = self._generate_evaluation_report(
                integrated_info,
                memory_results,
                value_scores,
                prioritized_info
            )
            
            self.evaluation_history.append(evaluation_report)
            logger.info(f"衡值评估完成：总体价值分数 {value_scores.get('overall', 0):.2f}")
            
            return evaluation_report
            
        except Exception as e:
            logger.error(f"衡值评估失败：{e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _retrieve_relevant_memories(self, integrated_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检索相关记忆"""
        keywords = self._extract_keywords(integrated_info)
        memories = []
        
        for keyword in keywords:
            memory = self._search_memory(keyword)
            if memory:
                memories.extend(memory)
        
        return memories
    
    def _assess_information_value(
        self,
        integrated_info: Dict[str, Any],
        memory_results: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """评估信息价值"""
        value_scores = {}
        
        if 'original_data' in integrated_info:
            value_scores['original_data'] = self._evaluate_data_value(
                integrated_info['original_data']
            )
        
        if 'knowledge_enhanced' in integrated_info:
            value_scores['knowledge_enhanced'] = self._evaluate_knowledge_value(
                integrated_info['knowledge_enhanced']
            )
        
        if 'research_results' in integrated_info:
            value_scores['research_results'] = self._evaluate_research_value(
                integrated_info['research_results']
            )
        
        memory_relevance = self._assess_memory_relevance(memory_results)
        value_scores['memory_relevance'] = memory_relevance
        
        value_scores['overall'] = self._calculate_overall_score(value_scores)
        
        return value_scores
    
    def _prioritize_information(
        self,
        integrated_info: Dict[str, Any],
        value_scores: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """信息重要性排序"""
        info_items = self._extract_info_items(integrated_info)
        prioritized_items = []
        
        for item in info_items:
            priority_score = self._calculate_priority_score(item, value_scores)
            prioritized_items.append({
                "item": item,
                "priority_score": priority_score,
                "priority_level": self._determine_priority_level(priority_score)
            })
        
        prioritized_items.sort(key=lambda x: x['priority_score'], reverse=True)
        return prioritized_items
    
    def _generate_evaluation_report(
        self,
        integrated_info: Dict[str, Any],
        memory_results: List[Dict[str, Any]],
        value_scores: Dict[str, float],
        prioritized_info: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成评估报告"""
        return {
            "status": "success",
            "type": "value_evaluation",
            "original_info": integrated_info,
            "memory_results": memory_results,
            "value_scores": value_scores,
            "prioritized_info": prioritized_info,
            "recommendations": self._generate_recommendations(prioritized_info),
            "processed_by": self.name,
            "timestamp": datetime.now().isoformat()
        }
    
    def _extract_keywords(self, integrated_info: Dict[str, Any]) -> List[str]:
        """提取关键词"""
        keywords = []
        
        if 'summary' in integrated_info:
            summary = integrated_info['summary']
            keywords.extend(self._extract_from_text(summary))
        
        if 'research_results' in integrated_info:
            for result in integrated_info['research_results']:
                if 'topic' in result:
                    keywords.append(result['topic'])
        
        return list(set(keywords))
    
    def _extract_from_text(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        keywords = []
        important_words = ['人工智能', '机器学习', '深度学习', '神经网络', '算法', '模型']
        
        for word in important_words:
            if word in text:
                keywords.append(word)
        
        return keywords
    
    def _search_memory(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索记忆"""
        return [
            {
                "id": f"mem_{hash(keyword)}",
                "content": f"关于{keyword}的记忆内容",
                "timestamp": datetime.now().isoformat(),
                "priority": "medium",
                "relevance": 0.85
            }
        ]
    
    def _evaluate_data_value(self, data: Any) -> float:
        """评估数据价值"""
        value_score = 0.5
        
        if isinstance(data, dict) and 'type' in data:
            data_type = data['type']
            
            if data_type == 'text':
                if 'content' in data:
                    length = len(data['content'])
                    if length > 1000:
                        value_score = 0.8
                    elif length > 100:
                        value_score = 0.6
                    else:
                        value_score = 0.3
            elif data_type == 'image':
                if 'detections' in data and len(data['detections']) > 0:
                    value_score = 0.7
                else:
                    value_score = 0.4
        
        return value_score
    
    def _evaluate_knowledge_value(self, knowledge_items: List[Dict[str, Any]]) -> float:
        """评估知识价值"""
        if not knowledge_items:
            return 0.0
        
        total_value = 0.0
        for item in knowledge_items:
            source = item.get('source', '')
            if source == 'openwebui':
                total_value += 0.8
            elif source == 'cognee':
                total_value += 0.9
            elif source == 'web_search':
                total_value += 0.7
        
        return total_value / len(knowledge_items)
    
    def _evaluate_research_value(self, research_results: List[Dict[str, Any]]) -> float:
        """评估研究价值"""
        if not research_results:
            return 0.0
        
        total_value = 0.0
        for result in research_results:
            confidence = result.get('result', {}).get('confidence', 0.5)
            total_value += confidence
        
        return total_value / len(research_results)
    
    def _assess_memory_relevance(self, memory_results: List[Dict[str, Any]]) -> float:
        """评估记忆相关性"""
        if not memory_results:
            return 0.0
        
        total_relevance = sum(memory.get('relevance', 0.5) for memory in memory_results)
        return total_relevance / len(memory_results)
    
    def _calculate_overall_score(self, value_scores: Dict[str, float]) -> float:
        """计算综合价值分数"""
        weights = {
            'original_data': 0.3,
            'knowledge_enhanced': 0.3,
            'research_results': 0.3,
            'memory_relevance': 0.1
        }
        
        total_score = 0.0
        for key, weight in weights.items():
            if key in value_scores:
                total_score += value_scores[key] * weight
        
        return total_score
    
    def _extract_info_items(self, integrated_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取信息项"""
        items = []
        
        if 'original_data' in integrated_info:
            items.append({
                'type': 'original_data',
                'content': integrated_info['original_data']
            })
        
        if 'knowledge_enhanced' in integrated_info:
            for item in integrated_info['knowledge_enhanced']:
                items.append({
                    'type': 'knowledge',
                    'content': item
                })
        
        if 'research_results' in integrated_info:
            for item in integrated_info['research_results']:
                items.append({
                    'type': 'research',
                    'content': item
                })
        
        return items
    
    def _calculate_priority_score(self, item: Dict[str, Any], value_scores: Dict[str, float]) -> float:
        """计算优先级分数"""
        base_score = value_scores.get('overall', 0.5)
        
        if item['type'] == 'original_data':
            return base_score * 0.8
        elif item['type'] == 'knowledge':
            return base_score * 0.9
        elif item['type'] == 'research':
            return base_score * 1.0
        
        return base_score
    
    def _determine_priority_level(self, score: float) -> str:
        """确定优先级级别"""
        if score >= 0.8:
            return 'critical'
        elif score >= 0.6:
            return 'high'
        elif score >= 0.4:
            return 'medium'
        else:
            return 'low'
    
    def _generate_recommendations(self, prioritized_info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成推荐"""
        recommendations = []
        
        for item in prioritized_info[:3]:
            priority_level = item['priority_level']
            
            if priority_level == 'critical':
                recommendations.append({
                    "action": "紧急处理",
                    "reason": "信息价值极高，需要立即处理",
                    "priority": priority_level
                })
            elif priority_level == 'high':
                recommendations.append({
                    "action": "优先处理",
                    "reason": "信息价值较高，建议优先处理",
                    "priority": priority_level
                })
        
        return recommendations
    
    async def get_agent_info(self) -> Dict[str, Any]:
        """获取 Agent 信息"""
        return {
            "name": self.name,
            "role": self.role,
            "models": self.models,
            "description": "负责评估信息的价值和重要性，管理多维度记忆系统"
        }
