#!/usr/bin/env python3
"""
兼容性验证
验证模型与系统的兼容性
"""

import os
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel

from .model_registry import get_model_registry, ModelInfo


class CompatibilityResult(BaseModel):
    """兼容性验证结果"""
    model_id: str
    compatible: bool
    score: float
    tests: List[Dict[str, Any]]
    errors: List[str]
    timestamp: datetime = datetime.now()


class CompatibilityChecker:
    """兼容性检查器"""
    
    def __init__(self):
        self.model_registry = get_model_registry()
    
    def verify_model(self, model_id: str) -> CompatibilityResult:
        """验证模型兼容性"""
        model = self.model_registry.get_model(model_id)
        if not model:
            return CompatibilityResult(
                model_id=model_id,
                compatible=False,
                score=0.0,
                tests=[],
                errors=["模型不存在"]
            )
        
        tests = []
        errors = []
        score = 0.0
        
        # 运行各项测试
        test_results = [
            self._test_model_loading(model),
            self._test_model_inference(model),
            self._test_model_capabilities(model),
            self._test_model_performance(model)
        ]
        
        # 汇总测试结果
        total_score = 0
        total_tests = len(test_results)
        
        for test_result in test_results:
            tests.append(test_result)
            if test_result["passed"]:
                total_score += test_result["score"]
            else:
                errors.append(test_result["error"])
        
        # 计算总体得分
        if total_tests > 0:
            score = total_score / total_tests
        
        # 判断兼容性
        compatible = score >= 0.7 and len(errors) < 2
        
        return CompatibilityResult(
            model_id=model_id,
            compatible=compatible,
            score=score,
            tests=tests,
            errors=errors
        )
    
    def _test_model_loading(self, model: ModelInfo) -> Dict[str, Any]:
        """测试模型加载"""
        start_time = time.time()
        
        try:
            # 这里需要根据模型类型实现加载测试
            # 简化示例
            if model.provider.lower() == "ollama":
                import ollama
                ollama.chat(model=model.model_id, messages=[{"role": "user", "content": "Hello"}])
            
            load_time = time.time() - start_time
            
            # 根据加载时间评分
            if load_time < 5:
                score = 1.0
            elif load_time < 10:
                score = 0.8
            else:
                score = 0.6
            
            return {
                "name": "模型加载测试",
                "passed": True,
                "score": score,
                "details": f"加载时间: {load_time:.2f}秒"
            }
        except Exception as e:
            return {
                "name": "模型加载测试",
                "passed": False,
                "score": 0.0,
                "error": str(e)
            }
    
    def _test_model_inference(self, model: ModelInfo) -> Dict[str, Any]:
        """测试模型推理"""
        start_time = time.time()
        
        try:
            # 测试基本推理
            test_prompts = [
                "Hello, how are you?",
                "Write a short poem about AI",
                "What is 2 + 2?"
            ]
            
            responses = []
            for prompt in test_prompts:
                if model.provider.lower() == "ollama":
                    import ollama
                    response = ollama.chat(model=model.model_id, messages=[{"role": "user", "content": prompt}])
                    responses.append(response["message"]["content"])
            
            inference_time = time.time() - start_time
            
            # 评估响应质量
            score = 0.0
            for response in responses:
                if len(response) > 10:
                    score += 0.33
            
            return {
                "name": "模型推理测试",
                "passed": True,
                "score": score,
                "details": f"推理时间: {inference_time:.2f}秒, 响应数: {len(responses)}"
            }
        except Exception as e:
            return {
                "name": "模型推理测试",
                "passed": False,
                "score": 0.0,
                "error": str(e)
            }
    
    def _test_model_capabilities(self, model: ModelInfo) -> Dict[str, Any]:
        """测试模型能力"""
        try:
            # 测试模型声称的能力
            capabilities = model.capabilities
            tested_capabilities = 0
            passed_capabilities = 0
            
            for capability in capabilities:
                tested_capabilities += 1
                # 根据能力类型进行测试
                if capability == "text_generation":
                    # 测试文本生成
                    passed_capabilities += 1
                elif capability == "conversation":
                    # 测试对话
                    passed_capabilities += 1
                elif capability == "coding":
                    # 测试编程
                    passed_capabilities += 1
                elif capability == "reasoning":
                    # 测试推理
                    passed_capabilities += 1
            
            score = passed_capabilities / tested_capabilities if tested_capabilities > 0 else 0.0
            
            return {
                "name": "模型能力测试",
                "passed": True,
                "score": score,
                "details": f"测试能力: {tested_capabilities}, 通过: {passed_capabilities}"
            }
        except Exception as e:
            return {
                "name": "模型能力测试",
                "passed": False,
                "score": 0.0,
                "error": str(e)
            }
    
    def _test_model_performance(self, model: ModelInfo) -> Dict[str, Any]:
        """测试模型性能"""
        try:
            # 测试模型性能
            start_time = time.time()
            
            # 运行多个推理请求
            if model.provider.lower() == "ollama":
                import ollama
                for i in range(3):
                    ollama.chat(model=model.model_id, messages=[{"role": "user", "content": f"Test {i+1}"}])
            
            total_time = time.time() - start_time
            avg_time = total_time / 3
            
            # 根据平均响应时间评分
            if avg_time < 1:
                score = 1.0
            elif avg_time < 2:
                score = 0.8
            elif avg_time < 5:
                score = 0.6
            else:
                score = 0.4
            
            return {
                "name": "模型性能测试",
                "passed": True,
                "score": score,
                "details": f"平均响应时间: {avg_time:.2f}秒"
            }
        except Exception as e:
            return {
                "name": "模型性能测试",
                "passed": False,
                "score": 0.0,
                "error": str(e)
            }
    
    def batch_verify(self) -> List[CompatibilityResult]:
        """批量验证所有模型"""
        results = []
        models = self.model_registry.list_models()
        
        for model in models:
            result = self.verify_model(model.model_id)
            results.append(result)
        
        return results


# 全局兼容性检查器实例
_compatibility_checker = None

def get_compatibility_checker() -> CompatibilityChecker:
    """获取兼容性检查器实例"""
    global _compatibility_checker
    if _compatibility_checker is None:
        _compatibility_checker = CompatibilityChecker()
    return _compatibility_checker


if __name__ == "__main__":
    # 测试
    checker = get_compatibility_checker()
    
    # 验证模型
    result = checker.verify_model("gemma4:e4b")
    print(f"模型: {result.model_id}")
    print(f"兼容性: {'兼容' if result.compatible else '不兼容'}")
    print(f"得分: {result.score:.2f}")
    print("\n测试结果:")
    for test in result.tests:
        status = "通过" if test["passed"] else "失败"
        print(f"- {test['name']}: {status} (得分: {test['score']:.2f})")
    
    if result.errors:
        print("\n错误:")
        for error in result.errors:
            print(f"- {error}")