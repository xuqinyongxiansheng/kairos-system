"""
感知层
负责感知和接收外部信息
使用 Ollama LLM 进行语义分析，替代关键词匹配
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PerceptionLayer:
    """感知层 - 接收和处理外部输入，使用 LLM 语义分析"""

    def __init__(self):
        self.input_buffer = []
        self.perception_history = []
        self.sensors = {}
        self._llm_enabled = True

    async def receive_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        接收输入，使用 LLM 进行语义感知
        """
        try:
            logger.info(f"接收输入：{input_data.get('type', 'unknown')}")

            timestamp = datetime.now().isoformat()
            content = input_data.get('content', '')

            perception = await self._llm_perceive(content)

            perception_result = {
                'status': 'success',
                'timestamp': timestamp,
                'input_type': input_data.get('type', 'unknown'),
                'content': content,
                'source': input_data.get('source', 'unknown'),
                'priority': perception.get('priority', 'normal'),
                'category': perception.get('category', 'unknown'),
                'sentiment': perception.get('sentiment', 'neutral'),
                'urgency': perception.get('urgency', 0.3),
                'key_entities': perception.get('key_entities', []),
            }

            self.input_buffer.append(perception_result)
            self.perception_history.append(perception_result)

            logger.info(f"感知完成 - 优先级:{perception_result['priority']} 类别:{perception_result['category']} 情感:{perception_result['sentiment']}")
            return perception_result

        except Exception as e:
            logger.error(f"感知层处理失败：{e}")
            return {'status': 'error', 'error': str(e)}

    async def _llm_perceive(self, content: str) -> Dict[str, Any]:
        """使用 LLM 进行语义感知分析"""
        if not self._llm_enabled or not content:
            return self._keyword_fallback(content)

        try:
            from kairos.system.llm_reasoning import llm_perceive
            return await llm_perceive(content)
        except ImportError:
            self._llm_enabled = False
            return self._keyword_fallback(content)
        except Exception as e:
            logger.warning(f"LLM 感知失败，回退到关键词模式: {e}")
            return self._keyword_fallback(content)

    def _keyword_fallback(self, content: str) -> Dict[str, Any]:
        """关键词回退（Ollama 不可用时）"""
        content_lower = str(content).lower()
        urgent = any(kw in content_lower for kw in ['紧急', 'urgent', '立即', '错误', '崩溃', 'asap'])
        return {
            'priority': 'high' if urgent else 'normal',
            'category': '问题' if '？' in content or '?' in content else '陈述',
            'sentiment': 'negative' if any(kw in content_lower for kw in ['不好', '差', '错', '失败']) else 'neutral',
            'urgency': 0.8 if urgent else 0.3,
            'key_entities': [w for w in content.split() if len(w) > 2][:5],
        }

    async def register_sensor(self, name: str, sensor_config: Dict[str, Any]):
        """注册传感器"""
        self.sensors[name] = {
            'config': sensor_config,
            'active': True,
            'last_update': datetime.now().isoformat()
        }
        logger.info(f"传感器注册成功：{name}")

    async def get_buffer_status(self) -> Dict[str, Any]:
        """获取缓冲区状态"""
        return {
            'status': 'success',
            'buffer_size': len(self.input_buffer),
            'total_perceptions': len(self.perception_history),
            'active_sensors': len([s for s in self.sensors.values() if s['active']]),
            'llm_enabled': self._llm_enabled,
        }

    async def clear_buffer(self):
        """清空缓冲区"""
        self.input_buffer = []
        logger.info("缓冲区已清空")
        return {'status': 'success', 'message': '缓冲区已清空'}
