"""
监控 Agent
负责监控系统状态
"""

import logging
from typing import Dict, Any, List
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class MonitoringAgent(BaseAgent):
    """监控 Agent - 监控系统状态和性能"""
    
    def __init__(self):
        super().__init__("MonitoringAgent", "监控系统状态")
        self.metrics = {}
        self.alerts = []
        self.monitoring_history = []
    
    async def initialize(self):
        """初始化监控 Agent"""
        logger.info("初始化监控 Agent")
        return {'status': 'success', 'message': '监控 Agent 初始化完成'}
    
    async def monitor(self, component: str, 
                     metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        监控组件
        
        Args:
            component: 组件名称
            metrics_data: 指标数据
            
        Returns:
            监控结果
        """
        try:
            logger.info(f"监控组件：{component}")
            
            timestamp = self._get_timestamp()
            
            monitoring_result = {
                'status': 'success',
                'timestamp': timestamp,
                'component': component,
                'metrics': metrics_data,
                'health': self._calculate_health(metrics_data),
                'alerts': []
            }
            
            self.metrics[component] = {
                'latest': metrics_data,
                'updated_at': timestamp
            }
            
            self.monitoring_history.append(monitoring_result)
            
            alerts = self._check_thresholds(component, metrics_data)
            if alerts:
                monitoring_result['alerts'] = alerts
                self.alerts.extend(alerts)
            
            return monitoring_result
            
        except Exception as e:
            logger.error(f"监控失败：{e}")
            return {'status': 'error', 'error': str(e)}
    
    def _calculate_health(self, metrics_data: Dict[str, Any]) -> str:
        """计算健康状态"""
        if not metrics_data:
            return 'unknown'
        
        error_rate = metrics_data.get('error_rate', 0)
        
        if error_rate < 0.01:
            return 'healthy'
        elif error_rate < 0.05:
            return 'warning'
        else:
            return 'critical'
    
    def _check_thresholds(self, component: str, 
                         metrics_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查阈值"""
        alerts = []
        
        cpu_usage = metrics_data.get('cpu_usage', 0)
        if cpu_usage > 90:
            alerts.append({
                'level': 'critical',
                'message': f'{component} CPU 使用率过高：{cpu_usage}%',
                'timestamp': self._get_timestamp()
            })
        
        memory_usage = metrics_data.get('memory_usage', 0)
        if memory_usage > 90:
            alerts.append({
                'level': 'warning',
                'message': f'{component} 内存使用率过高：{memory_usage}%',
                'timestamp': self._get_timestamp()
            })
        
        return alerts
    
    async def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        health_summary = {}
        
        for component, data in self.metrics.items():
            health = self._calculate_health(data['latest'])
            health_summary[component] = health
        
        return {
            'status': 'success',
            'health': health_summary,
            'active_alerts': len(self.alerts)
        }
    
    async def get_monitoring_summary(self) -> Dict[str, Any]:
        """获取监控摘要"""
        return {
            'status': 'success',
            'components_monitored': len(self.metrics),
            'total_monitoring': len(self.monitoring_history),
            'active_alerts': len(self.alerts)
        }
