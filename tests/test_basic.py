#!/usr/bin/env python3
"""
基本功能测试
测试系统的核心功能是否正常工作
"""

import unittest
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestBasicFunctionality(unittest.TestCase):
    """
    基本功能测试类
    """
    
    def test_environment(self):
        """
        测试环境
        """
        # 测试Python版本
        self.assertTrue(sys.version_info >= (3, 12), "Python版本需要3.12或更高")
        
        # 测试核心依赖
        try:
            import transformers
            import fastapi
            import uvicorn
        except ImportError as e:
            self.fail(f"核心依赖导入失败: {str(e)}")
    
    def test_directories(self):
        """
        测试目录结构
        """
        # 测试模型目录
        model_dir = "models/gemma4_e4b/"
        if not os.path.exists(model_dir):
            os.makedirs(model_dir, exist_ok=True)
        self.assertTrue(os.path.exists(model_dir), f"模型目录不存在: {model_dir}")
        
        # 测试模块目录
        module_dirs = [
            "modules/audio/",
            "modules/vision/",
            "modules/communication/",
            "modules/planning/",
            "modules/analysis/",
            "modules/learning/"
        ]
        for dir_path in module_dirs:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            self.assertTrue(os.path.exists(dir_path), f"模块目录不存在: {dir_path}")
        
        # 测试日志和测试目录
        if not os.path.exists("logs/"):
            os.makedirs("logs/", exist_ok=True)
        if not os.path.exists("tests/"):
            os.makedirs("tests/", exist_ok=True)
        self.assertTrue(os.path.exists("logs/"), "日志目录不存在")
        self.assertTrue(os.path.exists("tests/"), "测试目录不存在")
    
    def test_api_import(self):
        """
        测试API模块导入
        """
        try:
            from api import app
            self.assertIsNotNone(app, "API应用导入失败")
        except Exception as e:
            self.fail(f"API模块导入失败: {str(e)}")

if __name__ == "__main__":
    unittest.main()