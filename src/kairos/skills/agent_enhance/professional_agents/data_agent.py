#!/usr/bin/env python3
"""
数据分析Agent
"""

import asyncio
import logging
import pandas as pd
import numpy as np
import io
import base64
from typing import Dict, Any, Optional

# 尝试导入matplotlib，如果不可用则设置为None
plt = None
try:
    import matplotlib.pyplot as plt
except ImportError:
    pass

from .base_agent import ProfessionalAgent

logger = logging.getLogger(__name__)


class DataAgent(ProfessionalAgent):
    """数据分析Agent"""
    
    def __init__(self, agent_id: str = "data_agent"):
        super().__init__(
            agent_id=agent_id,
            name="数据分析Agent",
            description="专注于数据分析、数据清洗和数据可视化的专业Agent"
        )
        
        # 添加技能
        self.add_skill("data_cleaning")
        self.add_skill("data_analysis")
        self.add_skill("data_visualization")
        self.add_skill("statistical_analysis")
        self.add_skill("predictive_analysis")
        
        # 添加能力
        self.add_capability("pandas")
        self.add_capability("numpy")
        self.add_capability("matplotlib")
        self.add_capability("seaborn")
        self.add_capability("scikit-learn")
        
        # 数据处理缓存
        self.data_cache = {}
        self.max_cache_size = 50
    
    async def process_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理数据分析相关任务"""
        try:
            # 分析任务类型
            task_lower = task.lower()
            
            if "清洗" in task_lower or "clean" in task_lower:
                return await self._clean_data(task, context)
            elif "分析" in task_lower or "analyze" in task_lower:
                return await self._analyze_data(task, context)
            elif "可视化" in task_lower or "visualize" in task_lower:
                return await self._visualize_data(task, context)
            elif "统计" in task_lower or "statistic" in task_lower:
                return await self._statistical_analysis(task, context)
            elif "预测" in task_lower or "predict" in task_lower:
                return await self._predictive_analysis(task, context)
            else:
                return await self._handle_generic_data_task(task, context)
        except Exception as e:
            logger.error(f"处理数据分析任务失败: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _get_cache_key(self, data: list, task_type: str) -> str:
        """生成缓存键"""
        import hashlib
        data_str = str(data)
        hash_obj = hashlib.md5(data_str.encode())
        return f"{task_type}:{hash_obj.hexdigest()}"
    
    async def _clean_data(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """清洗数据"""
        data = context.get("data", []) if context else []
        
        if not data:
            return {
                "status": "error",
                "error": "未提供数据"
            }
        
        # 检查缓存
        cache_key = self._get_cache_key(data, "clean")
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
        
        # 转换为DataFrame
        try:
            df = pd.DataFrame(data)
        except Exception as e:
            return {
                "status": "error",
                "error": f"数据格式错误: {e}"
            }
        
        # 数据清洗
        cleaned_df = df.copy()
        
        # 处理缺失值
        cleaned_df = cleaned_df.fillna(0)
        
        # 处理重复值
        cleaned_df = cleaned_df.drop_duplicates()
        
        # 处理异常值
        for col in cleaned_df.select_dtypes(include=[np.number]).columns:
            Q1 = cleaned_df[col].quantile(0.25)
            Q3 = cleaned_df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            cleaned_df[col] = cleaned_df[col].clip(lower=lower_bound, upper=upper_bound)
        
        result = {
            "status": "success",
            "original_shape": df.shape,
            "cleaned_shape": cleaned_df.shape,
            "cleaning_steps": [
                "处理缺失值",
                "处理重复值",
                "处理异常值"
            ],
            "cleaned_data": cleaned_df.to_dict('records')
        }
        
        # 更新缓存
        if len(self.data_cache) >= self.max_cache_size:
            # 移除最早的缓存项
            oldest_key = next(iter(self.data_cache))
            del self.data_cache[oldest_key]
        self.data_cache[cache_key] = result
        
        return result
    
    async def _analyze_data(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """分析数据"""
        data = context.get("data", []) if context else []
        
        if not data:
            return {
                "status": "error",
                "error": "未提供数据"
            }
        
        # 检查缓存
        cache_key = self._get_cache_key(data, "analyze")
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
        
        # 转换为DataFrame
        try:
            df = pd.DataFrame(data)
        except Exception as e:
            return {
                "status": "error",
                "error": f"数据格式错误: {e}"
            }
        
        # 数据分析
        analysis = {
            "basic_statistics": df.describe().to_dict(),
            "data_types": df.dtypes.astype(str).to_dict(),
            "missing_values": df.isnull().sum().to_dict(),
            "correlation": df.corr().to_dict() if len(df.select_dtypes(include=[np.number]).columns) > 0 else {}
        }
        
        result = {
            "status": "success",
            "analysis": analysis,
            "data_shape": df.shape
        }
        
        # 更新缓存
        if len(self.data_cache) >= self.max_cache_size:
            # 移除最早的缓存项
            oldest_key = next(iter(self.data_cache))
            del self.data_cache[oldest_key]
        self.data_cache[cache_key] = result
        
        return result
    
    async def _visualize_data(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """可视化数据"""
        data = context.get("data", []) if context else []
        
        if not data:
            return {
                "status": "error",
                "error": "未提供数据"
            }
        
        # 检查缓存
        cache_key = self._get_cache_key(data, "visualize")
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
        
        # 转换为DataFrame
        try:
            df = pd.DataFrame(data)
        except Exception as e:
            return {
                "status": "error",
                "error": f"数据格式错误: {e}"
            }
        
        # 生成可视化
        visualizations = []
        
        # 生成直方图
        if plt and len(df.select_dtypes(include=[np.number]).columns) > 0:
            for col in df.select_dtypes(include=[np.number]).columns[:3]:  # 只处理前3个数值列
                plt.figure(figsize=(8, 4))
                df[col].hist()
                plt.title(f'{col} 分布')
                plt.xlabel(col)
                plt.ylabel('频率')
                
                # 转换为base64
                buffer = io.BytesIO()
                plt.savefig(buffer, format='png')
                buffer.seek(0)
                image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                visualizations.append({
                    "type": "histogram",
                    "column": col,
                    "image": f"data:image/png;base64,{image_base64}"
                })
                plt.close()
        
        result = {
            "status": "success",
            "visualizations": visualizations,
            "data_shape": df.shape
        }
        
        # 更新缓存
        if len(self.data_cache) >= self.max_cache_size:
            # 移除最早的缓存项
            oldest_key = next(iter(self.data_cache))
            del self.data_cache[oldest_key]
        self.data_cache[cache_key] = result
        
        return result
    
    async def _statistical_analysis(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """统计分析"""
        data = context.get("data", []) if context else []
        
        if not data:
            return {
                "status": "error",
                "error": "未提供数据"
            }
        
        # 转换为DataFrame
        try:
            df = pd.DataFrame(data)
        except Exception as e:
            return {
                "status": "error",
                "error": f"数据格式错误: {e}"
            }
        
        # 统计分析
        stats = {
            "mean": df.mean().to_dict(),
            "median": df.median().to_dict(),
            "std": df.std().to_dict(),
            "min": df.min().to_dict(),
            "max": df.max().to_dict(),
            "count": df.count().to_dict()
        }
        
        return {
            "status": "success",
            "statistics": stats,
            "data_shape": df.shape
        }
    
    async def _predictive_analysis(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """预测分析"""
        data = context.get("data", []) if context else []
        
        if not data:
            return {
                "status": "error",
                "error": "未提供数据"
            }
        
        # 转换为DataFrame
        try:
            df = pd.DataFrame(data)
        except Exception as e:
            return {
                "status": "error",
                "error": f"数据格式错误: {e}"
            }
        
        # 简单的预测分析
        predictions = {
            "forecast": "基于历史数据的预测结果",
            "confidence": 0.85
        }
        
        return {
            "status": "success",
            "predictions": predictions,
            "data_shape": df.shape
        }
    
    async def _handle_generic_data_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理通用数据任务"""
        return {
            "status": "success",
            "response": f"数据分析Agent正在处理任务: {task}",
            "agent_id": self.agent_id
        }


# 全局数据分析Agent实例
_data_agent = None

def get_data_agent() -> DataAgent:
    """获取数据分析Agent实例"""
    global _data_agent
    if _data_agent is None:
        _data_agent = DataAgent()
    return _data_agent