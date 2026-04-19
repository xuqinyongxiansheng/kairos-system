# -*- coding: utf-8 -*-
"""
多尺度注意力模块 - Kairos 3.0 4b核心特性
包含SWA/DSWA/GLA三种注意力机制
"""

from .swa import SlidingWindowAttention
from .dswa import DualSlidingWindowAttention
from .gla import GatedLinearAttention
from .multi_scale_attention import MultiScaleAttention, create_multi_scale_attention

__all__ = [
    'SlidingWindowAttention',
    'DualSlidingWindowAttention', 
    'GatedLinearAttention',
    'MultiScaleAttention',
    'create_multi_scale_attention'
]
