"""
反馈层
负责收集和处理反馈
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class FeedbackLayer:
    """反馈层 - 收集和处理反馈"""
    
    def __init__(self):
        self.feedback_store = []
        self.feedback_stats = {
            'positive': 0,
            'negative': 0,
            'neutral': 0
        }
        self.improvement_suggestions = []
    
    async def collect_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        收集反馈
        
        Args:
            feedback_data: 反馈数据
            
        Returns:
            收集结果
        """
        try:
            logger.info(f"收集反馈：{feedback_data.get('type', 'general')}")
            
            feedback_record = {
                'id': len(self.feedback_store) + 1,
                'timestamp': datetime.now().isoformat(),
                'type': feedback_data.get('type', 'general'),
                'content': feedback_data.get('content', ''),
                'sentiment': self._analyze_sentiment(feedback_data),
                'source': feedback_data.get('source', 'unknown'),
                'processed': False
            }
            
            self.feedback_store.append(feedback_record)
            
            sentiment = feedback_record['sentiment']
            if sentiment in self.feedback_stats:
                self.feedback_stats[sentiment] += 1
            
            logger.info(f"反馈已收集，情感：{sentiment}")
            return {
                'status': 'success',
                'feedback_id': feedback_record['id'],
                'sentiment': sentiment
            }
            
        except Exception as e:
            logger.error(f"反馈收集失败：{e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _analyze_sentiment(self, feedback_data: Dict[str, Any]) -> str:
        """分析反馈情感"""
        content = str(feedback_data.get('content', '')).lower()
        
        positive_words = ['good', 'great', 'excellent', '满意', '好', 'helpful']
        negative_words = ['bad', 'poor', 'terrible', '失望', '差', 'error']
        
        pos_count = sum(1 for word in positive_words if word in content)
        neg_count = sum(1 for word in negative_words if word in content)
        
        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        else:
            return 'neutral'
    
    async def process_feedback(self, feedback_id: int) -> Dict[str, Any]:
        """处理反馈"""
        for feedback in self.feedback_store:
            if feedback['id'] == feedback_id:
                feedback['processed'] = True
                
                if feedback['sentiment'] == 'negative':
                    suggestion = self._generate_improvement(feedback)
                    self.improvement_suggestions.append(suggestion)
                
                logger.info(f"反馈已处理：{feedback_id}")
                return {
                    'status': 'success',
                    'message': '反馈已处理'
                }
        
        return {
            'status': 'not_found',
            'message': f'反馈 ID 不存在：{feedback_id}'
        }
    
    def _generate_improvement(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """生成改进建议"""
        return {
            'feedback_id': feedback['id'],
            'suggestion': f"针对反馈 #{feedback['id']} 的改进建议",
            'priority': 'medium',
            'generated_at': datetime.now().isoformat()
        }
    
    async def get_feedback_summary(self) -> Dict[str, Any]:
        """获取反馈摘要"""
        total = len(self.feedback_store)
        
        return {
            'status': 'success',
            'total_feedback': total,
            'sentiment_distribution': self.feedback_stats.copy(),
            'improvement_suggestions': len(self.improvement_suggestions),
            'positive_rate': self.feedback_stats['positive'] / max(total, 1)
        }
    
    async def get_unprocessed_feedback(self) -> List[Dict[str, Any]]:
        """获取未处理的反馈"""
        unprocessed = [
            f for f in self.feedback_store 
            if not f['processed']
        ]
        return unprocessed
