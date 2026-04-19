#!/usr/bin/env python3
"""
安全管理器
处理权限控制和安全检查
"""

import os
import subprocess
import signal
import time
from typing import Dict, Any, Optional

# 只在非 Windows 系统上导入 resource 模块
if os.name != 'nt':
    import resource
else:
    # 在 Windows 系统上模拟 resource 模块
    class resource:
        RLIMIT_AS = 0
        RLIMIT_CPU = 1
        RLIMIT_FSIZE = 2
        
        @staticmethod
        def setrlimit(limit_type, limits):
            pass


class SecurityManager:
    """安全管理器"""
    
    def __init__(self):
        self.permission_whitelist = {
            "read": [".py", ".txt", ".md", ".json", ".yaml", ".yml"],
            "write": [".py", ".txt", ".md", ".json", ".yaml", ".yml"],
            "execute": [".py", ".sh", ".bat"]
        }
        
        self.path_blacklist = [
            "/etc", "/sys", "/proc", "/dev",
            "c:\\Windows", "c:\\Program Files",
            os.path.expanduser("~"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        ]
    
    def check_permission(self, action: str, resource: str) -> bool:
        """检查权限"""
        # 检查路径
        if self._is_path_restricted(resource):
            return False
        
        # 检查文件类型
        if action in self.permission_whitelist:
            ext = os.path.splitext(resource)[1]
            return ext in self.permission_whitelist[action]
        
        return False
    
    def _is_path_restricted(self, path: str) -> bool:
        """检查路径是否受限"""
        absolute_path = os.path.abspath(path)
        
        for restricted_path in self.path_blacklist:
            if absolute_path.startswith(restricted_path):
                return True
        
        return False
    
    def validate_input(self, input_data: str, max_length: int = 10000) -> bool:
        """验证输入"""
        # 检查长度
        if len(input_data) > max_length:
            return False
        
        # 检查危险字符
        dangerous_patterns = [
            "eval(", "exec(", "__import__(",
            "os.system(", "subprocess.", "open(",
            "file(", "compile(", "compile",
            "__getattr__", "__setattr__", "__delattr__",
            "__dict__", "__class__", "__bases__"
        ]
        
        for pattern in dangerous_patterns:
            if pattern in input_data:
                return False
        
        return True
    
    def execute_in_sandbox(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """在沙箱中执行命令"""
        result = {
            "success": False,
            "output": "",
            "error": "",
            "returncode": -1
        }
        
        try:
            # 限制资源使用
            def set_limits():
                # 限制内存使用 (100MB)
                resource.setrlimit(resource.RLIMIT_AS, (100 * 1024 * 1024, 100 * 1024 * 1024))
                # 限制CPU时间 (10秒)
                resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
                # 限制文件大小 (1MB)
                resource.setrlimit(resource.RLIMIT_FSIZE, (1 * 1024 * 1024, 1 * 1024 * 1024))
            
            # 执行命令
            process = subprocess.Popen(
                command, 
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=set_limits if os.name != 'nt' else None
            )
            
            # 等待完成或超时
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                result["output"] = stdout.decode('utf-8', errors='replace')
                result["error"] = stderr.decode('utf-8', errors='replace')
                result["returncode"] = process.returncode
                result["success"] = process.returncode == 0
            except subprocess.TimeoutExpired:
                process.kill()
                result["error"] = "Command timed out"
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def sanitize_path(self, path: str) -> str:
        """清理路径"""
        # 移除路径遍历
        path = path.replace("../", "").replace("..\\", "")
        # 移除绝对路径
        if os.path.isabs(path):
            path = os.path.basename(path)
        return path
    
    def generate_secure_token(self, length: int = 32) -> str:
        """生成安全令牌"""
        import secrets
        return secrets.token_hex(length)


# 全局安全管理器实例
_security_manager = None

def get_security_manager() -> SecurityManager:
    """获取安全管理器实例"""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager


if __name__ == "__main__":
    # 测试
    security = get_security_manager()
    
    # 测试权限检查
    print("权限检查:")
    print(f"读取 .py 文件: {security.check_permission('read', 'test.py')}")
    print(f"写入 .exe 文件: {security.check_permission('write', 'test.exe')}")
    print(f"执行 .py 文件: {security.check_permission('execute', 'test.py')}")
    
    # 测试输入验证
    print("\n输入验证:")
    print(f"正常输入: {security.validate_input('Hello world')}")
    print(f"危险输入: {security.validate_input('eval(1+1)')}")
    
    # 测试沙箱执行
    print("\n沙箱执行:")
    result = security.execute_in_sandbox("echo 'Hello from sandbox'")
    print(f"执行结果: {result}")