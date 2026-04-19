"""
分析 Agent
负责分析数据和内容
"""

import logging
from typing import Dict, Any, List
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class AnalysisAgent(BaseAgent):
    """分析 Agent - 分析数据和内容"""
    
    def __init__(self):
        super().__init__("AnalysisAgent", "分析数据和内容")
        self.analysis_models = {}
        self.analysis_history = []
    
    async def initialize(self):
        """初始化分析 Agent"""
        logger.info("初始化分析 Agent")
        return {'status': 'success', 'message': '分析 Agent 初始化完成'}
    
    async def analyze(self, content: str, 
                     analysis_type: str = 'general') -> Dict[str, Any]:
        """
        分析内容
        
        Args:
            content: 待分析内容
            analysis_type: 分析类型
            
        Returns:
            分析结果
        """
        try:
            logger.info(f"开始分析：{analysis_type}")
            
            result = {
                'status': 'success',
                'timestamp': self._get_timestamp(),
                'analysis_type': analysis_type,
                'topics': self._extract_topics(content),
                'sentiment': self._analyze_sentiment(content),
                'complexity': self._measure_complexity(content),
                'key_points': self._extract_key_points(content)
            }
            
            self.analysis_history.append(result)
            
            return result
            
        except Exception as e:
            logger.error(f"分析失败：{e}")
            return {'status': 'error', 'error': str(e)}
    
    def _extract_topics(self, content: str) -> List[str]:
        """提取主题"""
        topics = []
        words = content.split()
        for word in words:
            if len(word) > 5 and word[0].isupper():
                topics.append(word)
        return topics[:5]
    
    def _analyze_sentiment(self, content: str) -> str:
        """分析情感"""
        positive = ['good', 'great', '成功', '好']
        negative = ['bad', 'error', '失败', '差']
        
        content_lower = content.lower()
        pos_count = sum(1 for w in positive if w in content_lower)
        neg_count = sum(1 for w in negative if w in content_lower)
        
        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _measure_complexity(self, content: str) -> str:
        """测量复杂度"""
        sentences = content.split('.')
        avg_length = len(content) / max(len(sentences), 1)
        
        if avg_length > 50:
            return 'high'
        elif avg_length > 20:
            return 'medium'
        else:
            return 'low'
    
    def _extract_key_points(self, content: str) -> List[str]:
        """提取关键点"""
        lines = content.split('\n')
        key_points = [line.strip()[:100] for line in lines if line.strip() and len(line) > 10]
        return key_points[:5]
    
    async def get_analysis_summary(self) -> Dict[str, Any]:
        """获取分析摘要"""
        return {
            'status': 'success',
            'total_analyses': len(self.analysis_history),
            'models': list(self.analysis_models.keys())
        }
