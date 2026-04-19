"""
功能层模块
包含 6 层架构的所有层（中英文双版本）
"""

from .perception import PerceptionLayer
from .integration import IntegrationLayer
from .decision import DecisionLayer
from .execution import ExecutionLayer
from .feedback import FeedbackLayer
from .evaluation import EvaluationLayer

from .perception_zhiwei import PerceptionLayer_ZhiWei
from .integration_huizhi import IntegrationLayer_HuiZhi
from .decision_mingce import DecisionLayer_MingCe
from .execution_xingcheng import ExecutionLayer_XingCheng
from .evaluation_hengzhi import EvaluationLayer_HengZhi
from .feedback_huiheng import FeedbackLayer_HuiHeng

__all__ = [
    'PerceptionLayer',
    'IntegrationLayer',
    'DecisionLayer',
    'ExecutionLayer',
    'FeedbackLayer',
    'EvaluationLayer',
    'PerceptionLayer_ZhiWei',
    'IntegrationLayer_HuiZhi',
    'DecisionLayer_MingCe',
    'ExecutionLayer_XingCheng',
    'EvaluationLayer_HengZhi',
    'FeedbackLayer_HuiHeng'
]
