#!/usr/bin/env python3
"""
基本功能测试
测试系统的核心功能是否正常工作
"""

import unittest
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBasicFunctionality(unittest.TestCase):
    """基本功能测试类"""

    def test_environment(self):
        """测试环境"""
        self.assertTrue(sys.version_info >= (3, 11), "Python版本需要3.11或更高")

        try:
            import fastapi
            import uvicorn
            import pydantic
        except ImportError as e:
            self.fail(f"核心依赖导入失败: {str(e)}")

    def test_directories(self):
        """测试目录结构"""
        base = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "kairos")
        self.assertTrue(os.path.exists(base), f"源代码目录不存在: {base}")

        required_dirs = [
            os.path.join(base, "system"),
            os.path.join(base, "agents"),
            os.path.join(base, "routers"),
            os.path.join(base, "services"),
            os.path.join(base, "skills"),
            os.path.join(base, "layers"),
            os.path.join(base, "models"),
            os.path.join(base, "tools"),
        ]
        for dir_path in required_dirs:
            self.assertTrue(os.path.isdir(dir_path), f"模块目录不存在: {dir_path}")

    def test_package_import(self):
        """测试包导入"""
        try:
            from kairos.system.response import ApiResponse
            from kairos.system.event_system import EventSystem
            self.assertIsNotNone(ApiResponse)
            self.assertIsNotNone(EventSystem)
        except Exception as e:
            self.fail(f"模块导入失败: {str(e)}")


if __name__ == "__main__":
    unittest.main()
