"""
规则提示词系统
基于 ClaudeCode 的规则提示词模块，用于判断各 Agent 角色工作进行情况
整合 002/AAagent 的优秀实现
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class RulePromptSystem:
    """规则提示词系统"""
    
    def __init__(self):
        """初始化规则提示词系统"""
        self.rules = {}
        self.agent_performance_rules = {}
        self.rule_categories = []
        self._load_rules()
        
        logger.info("规则提示词系统初始化完成")
    
    def _load_rules(self):
        """加载规则提示词"""
        self.rules = {
            "agent_performance": {
                "code_quality": [
                    "代码应该具有良好的结构和可读性",
                    "代码应该包含适当的注释和文档",
                    "代码应该遵循一致的编码规范",
                    "代码应该经过充分的测试",
                    "代码应该避免冗余和重复"
                ],
                "efficiency": [
                    "任务应该按时完成",
                    "资源使用应该高效",
                    "算法复杂度应该合理",
                    "响应时间应该在可接受范围内",
                    "避免不必要的计算和操作"
                ],
                "communication": [
                    "沟通应该清晰明确",
                    "反馈应该及时准确",
                    "进度报告应该详细",
                    "问题应该及时上报",
                    "协作应该顺畅"
                ],
                "problem_solving": [
                    "问题分析应该深入",
                    "解决方案应该有效",
                    "应该考虑多种解决方案",
                    "应该学习经验教训",
                    "应该预防类似问题"
                ]
            },
            "agent_specific": {
                "代码开发": [
                    "代码应该符合项目编码规范",
                    "代码应该具有良好的错误处理",
                    "代码应该具有可扩展性",
                    "代码应该考虑性能优化",
                    "代码应该有适当的测试覆盖率"
                ],
                "需求分析师": [
                    "需求分析应该全面深入",
                    "需求应该清晰明确",
                    "需求应该可衡量可测试",
                    "需求应该符合业务目标",
                    "需求应该考虑可行性"
                ],
                "项目经理": [
                    "项目计划应该合理",
                    "进度监控应该及时",
                    "风险识别应该全面",
                    "资源分配应该合理",
                    "沟通协调应该有效"
                ],
                "测试工程师": [
                    "测试用例应该全面",
                    "测试应该覆盖各种场景",
                    "测试应该自动化",
                    "缺陷跟踪应该完善",
                    "测试报告应该详细"
                ]
            },
            "general_guidelines": [
                "遵循最小惊讶原则",
                "保持代码简洁明了",
                "避免过度设计",
                "注重用户体验",
                "确保安全性",
                "关注性能优化",
                "保持文档更新",
                "遵循最佳实践"
            ]
        }
        
        self.agent_performance_rules = {
            "代码开发": {
                "evaluation_criteria": [
                    "代码质量",
                    "功能完整性",
                    "性能表现",
                    "错误处理",
                    "代码可读性",
                    "测试覆盖率"
                ],
                "warning_thresholds": {
                    "bug_count": 3,
                    "code_complexity": 10,
                    "test_coverage": 70
                }
            },
            "需求分析师": {
                "evaluation_criteria": [
                    "需求完整性",
                    "需求清晰度",
                    "需求可行性",
                    "业务理解",
                    "沟通效果"
                ],
                "warning_thresholds": {
                    "ambiguous_requirements": 2,
                    "missing_requirements": 1,
                    "stakeholder_feedback": "negative"
                }
            },
            "项目经理": {
                "evaluation_criteria": [
                    "进度控制",
                    "风险管理",
                    "资源分配",
                    "团队协作",
                    "沟通协调"
                ],
                "warning_thresholds": {
                    "delay_days": 2,
                    "unidentified_risks": 3,
                    "resource_conflicts": 2
                }
            },
            "测试工程师": {
                "evaluation_criteria": [
                    "测试覆盖率",
                    "缺陷发现率",
                    "测试效率",
                    "自动化程度",
                    "测试报告质量"
                ],
                "warning_thresholds": {
                    "coverage_percentage": 80,
                    "missed_bugs": 5,
                    "manual_testing_ratio": 0.5
                }
            }
        }
        
        self.rule_categories = list(self.rules.keys())
    
    def get_rules_by_category(self, category: str) -> List[str]:
        """根据类别获取规则"""
        if category in self.rules:
            return self.rules[category]
        return []
    
    def get_agent_rules(self, agent_type: str) -> Dict[str, Any]:
        """获取特定 Agent 类型的规则"""
        agent_rules = {}
        
        agent_rules["performance_rules"] = self.rules.get("agent_performance", {})
        
        if agent_type in self.rules.get("agent_specific", {}):
            agent_rules["specific_rules"] = self.rules["agent_specific"][agent_type]
        
        agent_rules["general_guidelines"] = self.rules.get("general_guidelines", [])
        
        return agent_rules
    
    def evaluate_agent_performance(self, agent_name: str, agent_type: str,
                                  performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估 Agent 性能"""
        if agent_type not in self.agent_performance_rules:
            return {
                "success": False,
                "error": f"未知的 Agent 类型：{agent_type}"
            }
        
        rules = self.agent_performance_rules[agent_type]
        evaluation = {
            "agent_name": agent_name,
            "agent_type": agent_type,
            "timestamp": datetime.now().isoformat(),
            "evaluation_criteria": rules["evaluation_criteria"],
            "scores": {},
            "warnings": [],
            "overall_score": 0,
            "status": "normal"
        }
        
        total_score = 0
        criteria_count = len(rules["evaluation_criteria"])
        
        for criterion in rules["evaluation_criteria"]:
            score = performance_data.get(criterion, 0)
            evaluation["scores"][criterion] = score
            total_score += score
        
        evaluation["overall_score"] = total_score / criteria_count if criteria_count > 0 else 0
        
        thresholds = rules["warning_thresholds"]
        for key, threshold in thresholds.items():
            if key in performance_data:
                value = performance_data[key]
                
                if isinstance(threshold, (int, float)):
                    if key in ["bug_count", "code_complexity", "delay_days",
                              "unidentified_risks", "resource_conflicts", "missed_bugs"]:
                        if value > threshold:
                            evaluation["warnings"].append(f"{key} 超过阈值：{value} > {threshold}")
                    else:
                        if value < threshold:
                            evaluation["warnings"].append(f"{key} 低于阈值：{value} < {threshold}")
                elif isinstance(threshold, str):
                    if str(value).lower() == threshold:
                        evaluation["warnings"].append(f"{key} 达到警告状态：{value}")
        
        if evaluation["overall_score"] >= 80:
            evaluation["status"] = "excellent"
        elif evaluation["overall_score"] >= 60:
            evaluation["status"] = "good"
        elif evaluation["overall_score"] >= 40:
            evaluation["status"] = "average"
        else:
            evaluation["status"] = "poor"
        
        if evaluation["warnings"]:
            evaluation["status"] = "warning"
        
        return evaluation
    
    def generate_improvement_suggestions(self, evaluation: Dict[str, Any]) -> List[str]:
        """根据评估结果生成改进建议"""
        suggestions = []
        
        agent_type = evaluation["agent_type"]
        scores = evaluation["scores"]
        warnings = evaluation["warnings"]
        
        if agent_type == "代码开发":
            if scores.get("代码质量", 0) < 70:
                suggestions.append("提高代码质量，加强代码审查")
            if scores.get("测试覆盖率", 0) < 70:
                suggestions.append("增加测试用例，提高测试覆盖率")
            if scores.get("性能表现", 0) < 70:
                suggestions.append("优化代码性能，减少资源消耗")
        
        elif agent_type == "需求分析师":
            if scores.get("需求完整性", 0) < 70:
                suggestions.append("完善需求分析，确保需求完整性")
            if scores.get("需求清晰度", 0) < 70:
                suggestions.append("提高需求文档的清晰度和准确性")
        
        elif agent_type == "项目经理":
            if scores.get("进度控制", 0) < 70:
                suggestions.append("加强进度监控，及时调整计划")
            if scores.get("风险管理", 0) < 70:
                suggestions.append("完善风险识别和管理机制")
        
        elif agent_type == "测试工程师":
            if scores.get("测试覆盖率", 0) < 70:
                suggestions.append("提高测试覆盖率，确保测试全面")
            if scores.get("自动化程度", 0) < 70:
                suggestions.append("增加自动化测试，提高测试效率")
        
        for warning in warnings:
            if "bug_count" in warning:
                suggestions.append("加强代码质量控制，减少bug数量")
            elif "code_complexity" in warning:
                suggestions.append("简化代码结构，降低复杂度")
            elif "delay_days" in warning:
                suggestions.append("优化任务排期，避免进度延迟")
            elif "unidentified_risks" in warning:
                suggestions.append("加强风险识别，提前防范风险")
        
        if evaluation["overall_score"] < 60:
            suggestions.append("加强团队协作，提高工作效率")
            suggestions.append("学习最佳实践，提升专业能力")
        
        return suggestions
    
    def get_all_rules(self) -> Dict[str, Any]:
        """获取所有规则"""
        return {
            "rules": self.rules,
            "agent_performance_rules": self.agent_performance_rules,
            "categories": self.rule_categories,
            "total_rules": sum(len(rules) for rules in self.rules.values())
        }


rule_prompt_system = RulePromptSystem()


def get_rule_prompt_system() -> RulePromptSystem:
    """获取规则提示词系统实例"""
    return rule_prompt_system
