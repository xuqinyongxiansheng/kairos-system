"""
评估层
负责评估系统性能和效果
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class EvaluationLayer:
    """评估层 - 评估系统性能和效果"""
    
    def __init__(self):
        self.metrics = {}
        self.evaluation_history = []
        self.performance_benchmarks = {}
    
    async def evaluate_performance(self, component: str, 
                                   metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估性能
        
        Args:
            component: 组件名称
            metrics_data: 指标数据
            
        Returns:
            评估结果
        """
        try:
            logger.info(f"开始评估性能：{component}")
            
            evaluation = {
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                'component': component,
                'metrics': {},
                'overall_score': 0.0,
                'recommendations': []
            }
            
            for metric_name, metric_value in metrics_data.items():
                score = self._calculate_metric_score(metric_name, metric_value)
                evaluation['metrics'][metric_name] = {
                    'value': metric_value,
                    'score': score
                }
            
            evaluation['overall_score'] = self._calculate_overall_score(
                evaluation['metrics']
            )
            evaluation['recommendations'] = self._generate_recommendations(
                component, evaluation['metrics']
            )
            
            self.evaluation_history.append(evaluation)
            
            if component not in self.metrics:
                self.metrics[component] = []
            self.metrics[component].append(evaluation)
            
            logger.info(f"性能评估完成，总体得分：{evaluation['overall_score']:.2f}")
            return evaluation
            
        except Exception as e:
            logger.error(f"性能评估失败：{e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _calculate_metric_score(self, metric_name: str, 
                                 metric_value: Any) -> float:
        """计算指标得分"""
        if isinstance(metric_value, (int, float)):
            if 'time' in metric_name.lower() or 'latency' in metric_name.lower():
                return max(0, 1.0 - (metric_value / 1000))
            elif 'rate' in metric_name.lower() or 'accuracy' in metric_name.lower():
                return min(1.0, metric_value / 100)
            else:
                return min(1.0, metric_value / 10)
        else:
            return 0.5
    
    def _calculate_overall_score(self, metrics: Dict[str, Any]) -> float:
        """计算总体得分"""
        if not metrics:
            return 0.0
        
        total_score = sum(
            m.get('score', 0) for m in metrics.values()
        )
        return total_score / len(metrics)
    
    def _generate_recommendations(self, component: str, 
                                   metrics: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        for metric_name, metric_data in metrics.items():
            score = metric_data.get('score', 0)
            
            if score < 0.5:
                recommendations.append(
                    f"{component} 的 {metric_name} 需要改进 (当前得分：{score:.2f})"
                )
            elif score < 0.7:
                recommendations.append(
                    f"{component} 的 {metric_name} 可以优化 (当前得分：{score:.2f})"
                )
        
        return recommendations
    
    async def set_benchmark(self, component: str, 
                           benchmark_data: Dict[str, Any]):
        """设置性能基准"""
        self.performance_benchmarks[component] = {
            'benchmark': benchmark_data,
            'set_at': datetime.now().isoformat()
        }
        logger.info(f"性能基准已设置：{component}")
    
    async def compare_with_benchmark(self, component: str, 
                                     current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """与基准比较"""
        if component not in self.performance_benchmarks:
            return {
                'status': 'not_found',
                'message': f'基准不存在：{component}'
            }
        
        benchmark = self.performance_benchmarks[component]['benchmark']
        
        comparison = {
            'status': 'success',
            'component': component,
            'comparisons': {}
        }
        
        for metric_name, current_value in current_metrics.items():
            if metric_name in benchmark:
                benchmark_value = benchmark[metric_name]
                comparison['comparisons'][metric_name] = {
                    'current': current_value,
                    'benchmark': benchmark_value,
                    'difference': current_value - benchmark_value
                }
        
        return comparison
    
    async def get_evaluation_summary(self) -> Dict[str, Any]:
        """获取评估摘要"""
        total_evaluations = len(self.evaluation_history)
        
        avg_scores = {}
        for component, evaluations in self.metrics.items():
            if evaluations:
                scores = [e['overall_score'] for e in evaluations]
                avg_scores[component] = sum(scores) / len(scores)
        
        return {
            'status': 'success',
            'total_evaluations': total_evaluations,
            'components_evaluated': len(self.metrics),
            'average_scores': avg_scores,
            'benchmarks_set': len(self.performance_benchmarks)
        }
