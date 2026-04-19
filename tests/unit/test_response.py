"""
统一响应格式单元测试
"""

import pytest
from kairos.system.response import ApiResponse, create_response


class TestApiResponse:
    """测试 ApiResponse 类"""
    
    def test_success_response(self):
        """测试成功响应"""
        data = {"key": "value"}
        response = ApiResponse.success(data=data, message="操作成功")
        
        assert response.success is True
        assert response.message == "操作成功"
        assert response.data == data
        assert response.error is None
        assert response.timestamp is not None
    
    def test_error_response(self):
        """测试错误响应"""
        response = ApiResponse.error(message="操作失败", error={"code": 500})
        
        assert response.success is False
        assert response.message == "操作失败"
        assert response.data is None
        assert response.error == {"code": 500}
    
    def test_not_found_response(self):
        """测试资源不存在响应"""
        response = ApiResponse.not_found(message="用户不存在")
        
        assert response.success is False
        assert response.message == "用户不存在"
        assert response.error["type"] == "not_found"
    
    def test_unauthorized_response(self):
        """测试未授权响应"""
        response = ApiResponse.unauthorized()
        
        assert response.success is False
        assert response.message == "未授权访问"
        assert response.error["type"] == "unauthorized"
    
    def test_server_error_response(self):
        """测试服务器错误响应"""
        response = ApiResponse.server_error(message="数据库连接失败")
        
        assert response.success is False
        assert response.message == "数据库连接失败"
        assert response.error["type"] == "server_error"


class TestCreateResponse:
    """测试 create_response 函数"""
    
    def test_create_success_response(self):
        """测试创建成功响应"""
        data = {"result": "ok"}
        response = create_response(
            success=True,
            data=data,
            message="成功"
        )
        
        assert response["success"] is True
        assert response["data"] == data
        assert response["message"] == "成功"
        assert response["timestamp"] is not None
    
    def test_create_error_response(self):
        """测试创建错误响应"""
        error = {"code": 400, "field": "name"}
        response = create_response(
            success=False,
            message="验证失败",
            error=error
        )
        
        assert response["success"] is False
        assert response["error"] == error
        assert response["data"] is None
