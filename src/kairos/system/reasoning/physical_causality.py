# -*- coding: utf-8 -*-
"""
物理因果验证器 (Physical Causality Validator)
Kairos 3.0 4b核心组件

特点:
- 验证物理因果关系
- 检查时间因果一致性
- 能量守恒验证
- 物理定律约束
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import time


class PhysicalLawType(Enum):
    """物理定律类型"""
    ENERGY_CONSERVATION = "energy_conservation"
    MOMENTUM_CONSERVATION = "momentum_conservation"
    CAUSALITY = "causality"
    THERMODYNAMICS = "thermodynamics"
    ENTROPY = "entropy"


class ViolationSeverity(Enum):
    """违规严重程度"""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    NONE = "none"


@dataclass
class PhysicalConstraint:
    """物理约束"""
    name: str
    law_type: PhysicalLawType
    description: str
    check_function: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Violation:
    """违规记录"""
    constraint_name: str
    severity: ViolationSeverity
    description: str
    location: str
    suggested_fix: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'constraint_name': self.constraint_name,
            'severity': self.severity.value,
            'description': self.description,
            'location': self.location,
            'suggested_fix': self.suggested_fix
        }


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    violations: List[Violation]
    warnings: List[str]
    physics_score: float
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'is_valid': self.is_valid,
            'violations': [v.to_dict() for v in self.violations],
            'warnings': self.warnings,
            'physics_score': self.physics_score,
            'details': self.details
        }


class PhysicalCausalityValidator:
    """
    物理因果验证器
    
    核心功能:
    - 时间因果验证 (原因必须先于结果)
    - 能量守恒验证
    - 动量守恒验证
    - 热力学定律验证
    - 熵增原理验证
    """
    
    def __init__(self):
        self.constraints: Dict[str, PhysicalConstraint] = {}
        self.validation_history: List[Dict[str, Any]] = []
        
        self._register_default_constraints()
    
    def _register_default_constraints(self):
        """注册默认物理约束"""
        self.register_constraint(PhysicalConstraint(
            name="temporal_causality",
            law_type=PhysicalLawType.CAUSALITY,
            description="原因必须在时间上先于结果",
            check_function="check_temporal_order",
            parameters={'tolerance_ms': 0}
        ))
        
        self.register_constraint(PhysicalConstraint(
            name="energy_conservation",
            law_type=PhysicalLawType.ENERGY_CONSERVATION,
            description="能量不能凭空产生或消失",
            check_function="check_energy_balance",
            parameters={'tolerance': 0.01}
        ))
        
        self.register_constraint(PhysicalConstraint(
            name="momentum_conservation",
            law_type=PhysicalLawType.MOMENTUM_CONSERVATION,
            description="封闭系统动量守恒",
            check_function="check_momentum_balance",
            parameters={'tolerance': 0.01}
        ))
        
        self.register_constraint(PhysicalConstraint(
            name="entropy_increase",
            law_type=PhysicalLawType.ENTROPY,
            description="孤立系统熵不减",
            check_function="check_entropy_change",
            parameters={'allow_zero': True}
        ))
        
        self.register_constraint(PhysicalConstraint(
            name="thermodynamics_second_law",
            law_type=PhysicalLawType.THERMODYNAMICS,
            description="热量不能自发从低温传到高温",
            check_function="check_heat_flow",
            parameters={}
        ))
    
    def register_constraint(self, constraint: PhysicalConstraint):
        """注册物理约束"""
        self.constraints[constraint.name] = constraint
    
    def validate(
        self,
        scenario: Dict[str, Any],
        constraints_to_check: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        验证物理因果关系
        
        Args:
            scenario: 场景描述
                {
                    'cause': {'time': t1, 'energy': e1, ...},
                    'effect': {'time': t2, 'energy': e2, ...},
                    'system': {'isolated': bool, ...}
                }
            constraints_to_check: 要检查的约束列表
            
        Returns:
            验证结果
        """
        start_time = time.time()
        
        violations = []
        warnings = []
        details = {}
        
        if constraints_to_check is None:
            constraints_to_check = list(self.constraints.keys())
        
        for constraint_name in constraints_to_check:
            if constraint_name not in self.constraints:
                warnings.append(f"未知约束: {constraint_name}")
                continue
            
            constraint = self.constraints[constraint_name]
            check_result = self._check_constraint(constraint, scenario)
            
            if not check_result['passed']:
                violations.append(Violation(
                    constraint_name=constraint_name,
                    severity=check_result['severity'],
                    description=check_result['message'],
                    location=check_result.get('location', 'unknown'),
                    suggested_fix=check_result.get('suggested_fix', '')
                ))
            
            details[constraint_name] = check_result
        
        critical_violations = [v for v in violations if v.severity == ViolationSeverity.CRITICAL]
        major_violations = [v for v in violations if v.severity == ViolationSeverity.MAJOR]
        
        is_valid = len(critical_violations) == 0
        
        physics_score = self._compute_physics_score(violations, warnings)
        
        result = ValidationResult(
            is_valid=is_valid,
            violations=violations,
            warnings=warnings,
            physics_score=physics_score,
            details=details
        )
        
        elapsed = time.time() - start_time
        self.validation_history.append({
            'scenario_id': scenario.get('id', 'unknown'),
            'is_valid': is_valid,
            'violations_count': len(violations),
            'physics_score': physics_score,
            'elapsed_ms': elapsed * 1000
        })
        
        return result
    
    def _check_constraint(
        self,
        constraint: PhysicalConstraint,
        scenario: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检查单个约束"""
        check_function = getattr(self, f"_{constraint.check_function}", None)
        
        if check_function is None:
            return {
                'passed': True,
                'message': f"检查函数 {constraint.check_function} 未实现",
                'severity': ViolationSeverity.NONE
            }
        
        return check_function(scenario, constraint.parameters)
    
    def _check_temporal_order(
        self,
        scenario: Dict[str, Any],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检查时间顺序"""
        cause = scenario.get('cause', {})
        effect = scenario.get('effect', {})
        
        cause_time = cause.get('time', 0)
        effect_time = effect.get('time', 0)
        tolerance = params.get('tolerance_ms', 0)
        
        if effect_time < cause_time - tolerance:
            return {
                'passed': False,
                'message': f"结果时间({effect_time})早于原因时间({cause_time})",
                'severity': ViolationSeverity.CRITICAL,
                'location': 'temporal_order',
                'suggested_fix': "调整时间顺序，确保原因先于结果"
            }
        
        return {
            'passed': True,
            'message': "时间顺序正确",
            'severity': ViolationSeverity.NONE
        }
    
    def _check_energy_balance(
        self,
        scenario: Dict[str, Any],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检查能量平衡"""
        cause = scenario.get('cause', {})
        effect = scenario.get('effect', {})
        system = scenario.get('system', {})
        
        cause_energy = cause.get('energy', 0)
        effect_energy = effect.get('energy', 0)
        external_energy = scenario.get('external_energy', 0)
        
        tolerance = params.get('tolerance', 0.01)
        
        if system.get('isolated', False):
            expected_energy = cause_energy
            actual_energy = effect_energy
            
            if abs(actual_energy - expected_energy) > tolerance * abs(expected_energy):
                return {
                    'passed': False,
                    'message': f"能量不守恒: 输入{cause_energy}, 输出{effect_energy}",
                    'severity': ViolationSeverity.MAJOR,
                    'location': 'energy_balance',
                    'suggested_fix': "检查能量来源/去向，确保能量守恒"
                }
        else:
            total_input = cause_energy + external_energy
            if abs(effect_energy - total_input) > tolerance * abs(total_input):
                return {
                    'passed': False,
                    'message': f"能量不守恒: 总输入{total_input}, 输出{effect_energy}",
                    'severity': ViolationSeverity.MAJOR,
                    'location': 'energy_balance',
                    'suggested_fix': "检查外部能量输入"
                }
        
        return {
            'passed': True,
            'message': "能量守恒",
            'severity': ViolationSeverity.NONE
        }
    
    def _check_momentum_balance(
        self,
        scenario: Dict[str, Any],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检查动量平衡"""
        cause = scenario.get('cause', {})
        effect = scenario.get('effect', {})
        
        cause_momentum = cause.get('momentum', [0, 0, 0])
        effect_momentum = effect.get('momentum', [0, 0, 0])
        external_force = scenario.get('external_force', [0, 0, 0])
        
        tolerance = params.get('tolerance', 0.01)
        
        for i in range(3):
            expected = cause_momentum[i] + external_force[i]
            actual = effect_momentum[i]
            
            if abs(actual - expected) > tolerance * (abs(expected) + 0.001):
                return {
                    'passed': False,
                    'message': f"动量不守恒(维度{i}): 预期{expected}, 实际{actual}",
                    'severity': ViolationSeverity.MAJOR,
                    'location': f'momentum_dim_{i}',
                    'suggested_fix': "检查外力作用，确保动量守恒"
                }
        
        return {
            'passed': True,
            'message': "动量守恒",
            'severity': ViolationSeverity.NONE
        }
    
    def _check_entropy_change(
        self,
        scenario: Dict[str, Any],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检查熵变化"""
        cause = scenario.get('cause', {})
        effect = scenario.get('effect', {})
        system = scenario.get('system', {})
        
        cause_entropy = cause.get('entropy', 0)
        effect_entropy = effect.get('entropy', 0)
        allow_zero = params.get('allow_zero', True)
        
        if system.get('isolated', False):
            entropy_change = effect_entropy - cause_entropy
            
            if entropy_change < 0:
                return {
                    'passed': False,
                    'message': f"孤立系统熵减少: {entropy_change}",
                    'severity': ViolationSeverity.CRITICAL,
                    'location': 'entropy',
                    'suggested_fix': "熵不能减少，检查计算或系统定义"
                }
            
            if entropy_change == 0 and not allow_zero:
                return {
                    'passed': False,
                    'message': "熵变为零，可能存在计算错误",
                    'severity': ViolationSeverity.MINOR,
                    'location': 'entropy',
                    'suggested_fix': "检查熵计算"
                }
        
        return {
            'passed': True,
            'message': "熵变化符合热力学第二定律",
            'severity': ViolationSeverity.NONE
        }
    
    def _check_heat_flow(
        self,
        scenario: Dict[str, Any],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检查热流方向"""
        cause = scenario.get('cause', {})
        effect = scenario.get('effect', {})
        
        cause_temp = cause.get('temperature', 300)
        effect_temp = effect.get('temperature', 300)
        heat_transferred = scenario.get('heat_transferred', 0)
        
        if heat_transferred > 0 and cause_temp < effect_temp:
            return {
                'passed': False,
                'message': f"热量从低温({cause_temp}K)流向高温({effect_temp}K)",
                'severity': ViolationSeverity.CRITICAL,
                'location': 'heat_flow',
                'suggested_fix': "热量只能自发从高温流向低温"
            }
        
        return {
            'passed': True,
            'message': "热流方向正确",
            'severity': ViolationSeverity.NONE
        }
    
    def _compute_physics_score(
        self,
        violations: List[Violation],
        warnings: List[str]
    ) -> float:
        """计算物理一致性分数"""
        score = 1.0
        
        for violation in violations:
            if violation.severity == ViolationSeverity.CRITICAL:
                score -= 0.4
            elif violation.severity == ViolationSeverity.MAJOR:
                score -= 0.2
            elif violation.severity == ViolationSeverity.MINOR:
                score -= 0.05
        
        score -= len(warnings) * 0.02
        
        return max(0.0, min(1.0, score))
    
    def validate_chain(
        self,
        chain: Dict[str, Any],
        events: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        验证因果链的物理一致性
        
        Args:
            chain: 因果链
            events: 事件列表
            
        Returns:
            验证结果
        """
        all_violations = []
        all_warnings = []
        all_details = {}
        
        edges = chain.get('edges', [])
        nodes = {n['id']: n for n in chain.get('nodes', [])}
        
        for edge in edges:
            source = nodes.get(edge['source_id'], {})
            target = nodes.get(edge['target_id'], {})
            
            scenario = {
                'id': f"{edge['source_id']}->{edge['target_id']}",
                'cause': {
                    'time': source.get('time', 0),
                    'energy': source.get('energy', 0),
                    'momentum': source.get('momentum', [0, 0, 0]),
                    'entropy': source.get('entropy', 0),
                    'temperature': source.get('temperature', 300)
                },
                'effect': {
                    'time': target.get('time', 0),
                    'energy': target.get('energy', 0),
                    'momentum': target.get('momentum', [0, 0, 0]),
                    'entropy': target.get('entropy', 0),
                    'temperature': target.get('temperature', 300)
                },
                'system': {'isolated': edge.get('isolated', False)}
            }
            
            result = self.validate(scenario)
            
            all_violations.extend(result.violations)
            all_warnings.extend(result.warnings)
            all_details[scenario['id']] = result.to_dict()
        
        physics_score = self._compute_physics_score(all_violations, all_warnings)
        
        return ValidationResult(
            is_valid=len([v for v in all_violations if v.severity == ViolationSeverity.CRITICAL]) == 0,
            violations=all_violations,
            warnings=all_warnings,
            physics_score=physics_score,
            details=all_details
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.validation_history:
            return {'total_validations': 0}
        
        valid_count = sum(1 for r in self.validation_history if r['is_valid'])
        total_violations = sum(r['violations_count'] for r in self.validation_history)
        avg_score = sum(r['physics_score'] for r in self.validation_history) / len(self.validation_history)
        
        return {
            'total_validations': len(self.validation_history),
            'valid_count': valid_count,
            'valid_rate': valid_count / len(self.validation_history),
            'total_violations': total_violations,
            'avg_physics_score': avg_score,
            'registered_constraints': len(self.constraints)
        }


def create_physical_validator() -> PhysicalCausalityValidator:
    """创建物理因果验证器实例"""
    return PhysicalCausalityValidator()
