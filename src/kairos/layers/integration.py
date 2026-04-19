"""
整合层
负责整合和关联来自不同源的信息
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class IntegrationLayer:
    """整合层 - 整合和关联信息"""
    
    def __init__(self):
        self.knowledge_base = {}
        self.associations = {}
        self.integration_history = []
    
    async def integrate(self, data_sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        整合多个数据源
        
        Args:
            data_sources: 数据源列表
            
        Returns:
            整合结果
        """
        try:
            logger.info(f"开始整合 {len(data_sources)} 个数据源")
            
            integrated_data = {
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                'source_count': len(data_sources),
                'merged_data': {},
                'conflicts': [],
                'associations': []
            }
            
            for i, source in enumerate(data_sources):
                source_id = source.get('id', f'source_{i}')
                source_content = source.get('content', {})
                
                if isinstance(source_content, dict):
                    for key, value in source_content.items():
                        if key in integrated_data['merged_data']:
                            existing = integrated_data['merged_data'][key]
                            if existing != value:
                                integrated_data['conflicts'].append({
                                    'key': key,
                                    'values': [existing, value]
                                })
                        else:
                            integrated_data['merged_data'][key] = value
            
            integrated_data['associations'] = self._find_associations(
                integrated_data['merged_data']
            )
            
            self.integration_history.append({
                'timestamp': integrated_data['timestamp'],
                'source_count': len(data_sources),
                'result_status': integrated_data['status']
            })
            
            logger.info(f"整合完成，发现 {len(integrated_data['conflicts'])} 个冲突")
            return integrated_data
            
        except Exception as e:
            logger.error(f"整合层处理失败：{e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _find_associations(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """发现数据关联"""
        associations = []
        
        keys = list(data.keys())
        for i, key1 in enumerate(keys):
            for key2 in keys[i+1:]:
                if self._are_related(str(key1), str(key2)):
                    associations.append({
                        'key1': key1,
                        'key2': key2,
                        'relation_type': 'semantic'
                    })
        
        return associations
    
    def _are_related(self, text1: str, text2: str) -> bool:
        """判断两个文本是否相关"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        common_words = words1.intersection(words2)
        return len(common_words) > 0
    
    async def update_knowledge_base(self, key: str, value: Any):
        """更新知识库"""
        self.knowledge_base[key] = {
            'value': value,
            'updated_at': datetime.now().isoformat()
        }
        logger.info(f"知识库更新：{key}")
    
    async def get_integration_summary(self) -> Dict[str, Any]:
        """获取整合摘要"""
        return {
            'status': 'success',
            'knowledge_base_size': len(self.knowledge_base),
            'total_integrations': len(self.integration_history),
            'associations_count': len(self.associations)
        }
