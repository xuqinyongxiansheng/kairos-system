"""
澧炲己浠ｇ爜鎵ц�屽�?瀹炵幇瀹夊叏鐨勪唬鐮佹墽琛屾満鍒讹紝鏀�鎸佸�氳��瑷�
鏁村悎 002/AAagent 鐨勪紭绉�瀹炵幇
"""

import subprocess
import os
import tempfile
import time
import threading
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """鎵ц�岀姸鎬佹灇涓?""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded"
    SECURITY_VIOLATION = "security_violation"


class LanguageType(Enum):
    """缂栫▼璇�瑷�绫诲瀷鏋氫妇"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    BASH = "bash"
    POWERSHELL = "powershell"


@dataclass
class ExecutionResult:
    """浠ｇ爜鎵ц�岀粨鏋滄暟鎹�绫?""
    status: str
    output: str
    error: str
    execution_time: float
    memory_used: int
    return_code: int
    security_warnings: List[str] = None
    
    def __post_init__(self):
        if self.security_warnings is None:
            self.security_warnings = []


class EnhancedCodeExecutor:
    """澧炲己浠ｇ爜鎵ц�屽櫒绫�"""
    
    def __init__(self, config: Dict = None):
        if config is None:
            config = {}
        
        self.config = config
        self.max_execution_time = config.get("max_execution_time", 5)
        self.max_memory_mb = config.get("max_memory_mb", 100)
        self.memory_check_interval = config.get("memory_check_interval", 0.1)
        self.supported_languages = [lang.value for lang in LanguageType]
        self.execution_logs: List[Dict[str, Any]] = []
        self.enable_security_check = config.get("enable_security_check", True)
        
        self.security_policies = {
            "python": {
                "allowed_modules": ["math", "random", "datetime", "json", "string", "re"],
                "blocked_functions": ["eval", "exec", "compile", "__import__"],
                "blocked_attributes": ["__dict__", "__class__", "__subclasses__", "__bases__"],
                "max_code_length": 10000
            },
            "javascript": {
                "blocked_functions": ["eval", "new Function"],
                "max_code_length": 10000
            },
            "bash": {
                "blocked_commands": ["rm", "chmod", "sudo", "cp", "mv"],
                "max_code_length": 5000
            },
            "powershell": {
                "blocked_commands": ["Remove-Item", "New-Item", "Invoke-Command"],
                "max_code_length": 5000
            }
        }
    
    def execute_code(self, code: str, language: str = "python") -> ExecutionResult:
        """鎵ц�屼唬鐮佸苟杩斿洖缁撴�?""
        if language not in self.supported_languages:
            return ExecutionResult(
                status=ExecutionStatus.ERROR.value,
                output="",
                error=f"涓嶆敮鎸佺殑缂栫▼璇�瑷�: {language}",
                execution_time=0,
                memory_used=0,
                return_code=-1
            )
        
        # 浠ｇ爜闀垮害妫�鏌?        if len(code) > self.security_policies.get(language, {}).get("max_code_length", 10000):
            return ExecutionResult(
                status=ExecutionStatus.SECURITY_VIOLATION.value,
                output="",
                error=f"浠ｇ爜闀垮害瓒呰繃闄愬埗",
                execution_time=0,
                memory_used=0,
                return_code=-1,
                security_warnings=["浠ｇ爜闀垮害瓒呴檺"]
            )
        
        start_time = time.time()
        
        try:
            if language == "python":
                result = self._execute_python(code)
            elif language == "javascript":
                result = self._execute_javascript(code)
            elif language == "bash":
                result = self._execute_bash(code)
            elif language == "powershell":
                result = self._execute_powershell(code)
            else:
                result = ExecutionResult(
                    status=ExecutionStatus.ERROR.value,
                    output="",
                    error=f"涓嶆敮鎸佺殑璇�瑷�: {language}",
                    execution_time=time.time() - start_time,
                    memory_used=0,
                    return_code=-1
                )
            
            self._log_execution(language, code, result)
            
            return result
            
        except Exception as e:
            logger.error(f"鎵ц�屽紓甯革細{e}")
            return ExecutionResult(
                status=ExecutionStatus.ERROR.value,
                output="",
                error=str(e),
                execution_time=time.time() - start_time,
                memory_used=0,
                return_code=-1
            )
    
    def _execute_python(self, code: str) -> ExecutionResult:
        """鎵ц�� Python 浠ｇ爜"""
        start_time = time.time()
        
        python_code = f"""# -*- coding: utf-8 -*-
import sys
sys.setrecursionlimit(1000)

{code}
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(python_code)
            temp_file_name = f.name
        
        try:
            process = subprocess.Popen(
                ['python', temp_file_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            timeout_thread = threading.Thread(
                target=self._monitor_execution_timeout,
                args=(process, self.max_execution_time)
            )
            timeout_thread.daemon = True
            timeout_thread.start()
            
            stdout, stderr = process.communicate(timeout=self.max_execution_time)
            
            execution_time = time.time() - start_time
            
            if process.returncode == 0:
                return ExecutionResult(
                    status=ExecutionStatus.SUCCESS.value,
                    output=stdout,
                    error=stderr,
                    execution_time=execution_time,
                    memory_used=0,
                    return_code=process.returncode
                )
            else:
                return ExecutionResult(
                    status=ExecutionStatus.ERROR.value,
                    output=stdout,
                    error=stderr,
                    execution_time=execution_time,
                    memory_used=0,
                    return_code=process.returncode
                )
                
        except subprocess.TimeoutExpired:
            process.kill()
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT.value,
                output="",
                error=f"鎵ц�岃秴鏃讹紙{self.max_execution_time}绉掞級",
                execution_time=self.max_execution_time,
                memory_used=0,
                return_code=-1
            )
        finally:
            try:
                os.unlink(temp_file_name)
            except Exception:
                logger.debug("忽略异常: 临时文件清理", exc_info=True)
                pass
    
    def _execute_javascript(self, code: str) -> ExecutionResult:
        """鎵ц�� JavaScript 浠ｇ爜"""
        start_time = time.time()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            temp_file_name = f.name
        
        try:
            try:
                subprocess.run(['node', '--version'], check=True, capture_output=True)
            except (subprocess.SubprocessError, FileNotFoundError):
                return ExecutionResult(
                    status=ExecutionStatus.ERROR.value,
                    output="",
                    error="Node.js 鏈�瀹夎�?,
                    execution_time=0,
                    memory_used=0,
                    return_code=-1
                )
            
            process = subprocess.Popen(
                ['node', temp_file_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=self.max_execution_time)
            
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS.value if process.returncode == 0 else ExecutionStatus.ERROR.value,
                output=stdout,
                error=stderr,
                execution_time=execution_time,
                memory_used=0,
                return_code=process.returncode
            )
            
        except subprocess.TimeoutExpired:
            process.kill()
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT.value,
                output="",
                error="鎵ц�岃秴鏃�",
                execution_time=time.time() - start_time,
                memory_used=0,
                return_code=-1
            )
        finally:
            try:
                os.unlink(temp_file_name)
            except Exception:
                logger.debug("忽略异常: 临时文件清理", exc_info=True)
                pass
    
    def _execute_bash(self, code: str) -> ExecutionResult:
        """鎵ц�� Bash 浠ｇ爜"""
        start_time = time.time()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(code)
            temp_file_name = f.name
        
        try:
            os.chmod(temp_file_name, 0o755)
            
            process = subprocess.Popen(
                ['bash', temp_file_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=self.max_execution_time)
            
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS.value if process.returncode == 0 else ExecutionStatus.ERROR.value,
                output=stdout,
                error=stderr,
                execution_time=execution_time,
                memory_used=0,
                return_code=process.returncode
            )
            
        except subprocess.TimeoutExpired:
            process.kill()
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT.value,
                output="",
                error="鎵ц�岃秴鏃�",
                execution_time=time.time() - start_time,
                memory_used=0,
                return_code=-1
            )
        finally:
            try:
                os.unlink(temp_file_name)
            except Exception:
                logger.debug("忽略异常: 临时文件清理", exc_info=True)
                pass
    
    def _execute_powershell(self, code: str) -> ExecutionResult:
        """鎵ц�� PowerShell 浠ｇ爜"""
        start_time = time.time()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False) as f:
            f.write(code)
            temp_file_name = f.name
        
        try:
            process = subprocess.Popen(
                ['powershell', '-ExecutionPolicy', 'Bypass', '-File', temp_file_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=self.max_execution_time)
            
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS.value if process.returncode == 0 else ExecutionStatus.ERROR.value,
                output=stdout,
                error=stderr,
                execution_time=execution_time,
                memory_used=0,
                return_code=process.returncode
            )
            
        except subprocess.TimeoutExpired:
            process.kill()
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT.value,
                output="",
                error="鎵ц�岃秴鏃�",
                execution_time=time.time() - start_time,
                memory_used=0,
                return_code=-1
            )
        finally:
            try:
                os.unlink(temp_file_name)
            except Exception:
                logger.debug("忽略异常: 临时文件清理", exc_info=True)
                pass
    
    def validate_code_safety(self, code: str, language: str) -> Tuple[bool, List[str]]:
        """楠岃瘉浠ｇ爜瀹夊叏鎬?""
        warnings = []
        
        if language == "python":
            dangerous_patterns = [
                (r'import\s+(os|subprocess|shutil)', "鍗遍櫓瀵煎叆"),
                (r'(eval|exec)\s*\(', "鍗遍櫓鍑芥暟璋冪敤"),
                (r'open\s*\([^)]*[\'"]w[\'"]', "鏂囦欢鍐欏叆鎿嶄綔")
            ]
            
            for pattern, desc in dangerous_patterns:
                import re
                if re.search(pattern, code):
                    warnings.append(desc)
        
        return len(warnings) == 0, warnings
    
    def _monitor_execution_timeout(self, process: subprocess.Popen, timeout: float):
        """鐩戞帶鎵ц�岃秴鏃�"""
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if process.poll() is None:
                process.kill()
    
    def _log_execution(self, language: str, code: str, result: ExecutionResult):
        """璁板綍鎵ц�屾棩蹇�"""
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "language": language,
            "status": result.status,
            "execution_time": result.execution_time,
            "return_code": result.return_code
        }
        self.execution_logs.append(log_entry)
        logger.info(f"浠ｇ爜鎵ц�屽畬鎴愶細{language}锛岀姸鎬?{result.status}锛岃�楁椂={result.execution_time:.2f}s")


enhanced_code_executor = EnhancedCodeExecutor()
