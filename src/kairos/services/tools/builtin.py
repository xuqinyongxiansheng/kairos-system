"""
内置工具实现
包含核心工具：Bash、FileRead、FileEdit、FileWrite、Glob、Grep、WorkflowTool
借鉴 cc-haha-main 的工具架构，完全重写实现
"""

import os
import re
import json
import glob as glob_module
import asyncio
import logging
import subprocess
import tempfile
from typing import Dict, Any, List

from . import (
    ToolDef, ToolResult, ToolParameter, ToolRegistry,
    PermissionLevel, build_tool
)

logger = logging.getLogger("BuiltInTools")

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_OUTPUT_LENGTH = 50000
MAX_BASH_TIMEOUT = 300

DANGEROUS_PATTERNS = [
    re.compile(r'rm\s+-rf\s+/', re.IGNORECASE),
    re.compile(r'del\s+/s\s+/q\s+[A-Za-z]:', re.IGNORECASE),
    re.compile(r'format\s+[A-Za-z]:', re.IGNORECASE),
    re.compile(r'mkfs\.'),
    re.compile(r':\(\)\{\s*:\|:&\s*\}'),
    re.compile(r'shutdown\b', re.IGNORECASE),
    re.compile(r'reboot\b', re.IGNORECASE),
    re.compile(r'taskkill\s+/F', re.IGNORECASE),
    re.compile(r'chkdsk\s+/f', re.IGNORECASE),
    re.compile(r'diskpart', re.IGNORECASE),
    re.compile(r'>\s*/etc/', re.IGNORECASE),
    re.compile(r'>\s*/dev/sd', re.IGNORECASE),
    re.compile(r'chmod\s+777\s+/', re.IGNORECASE),
    re.compile(r'chown\s+\S+\s+/', re.IGNORECASE),
    re.compile(r'wget\s+.*\|\s*(ba)?sh', re.IGNORECASE),
    re.compile(r'curl\s+.*\|\s*(ba)?sh', re.IGNORECASE),
    re.compile(r'\bsu\b\s+-', re.IGNORECASE),
    re.compile(r'\bsudo\s+rm\b', re.IGNORECASE),
    re.compile(r'\bsudo\s+dd\b', re.IGNORECASE),
    re.compile(r'>\s*/etc/passwd', re.IGNORECASE),
    re.compile(r'>\s*/etc/shadow', re.IGNORECASE),
    re.compile(r'\bdd\s+if=', re.IGNORECASE),
    re.compile(r':(){ :|:& };:', re.IGNORECASE),
]

SHELL_META_PATTERN = re.compile(r'(?<!\\)\||(?<!\\)>|(?<!\\)>>|(?<!\\)\$\(|(?<!\\)`|(?<!\\)\$\{')

SAFE_COMMAND_PREFIXES = [
    'ls', 'dir', 'cat', 'type', 'head', 'tail', 'pwd', 'echo',
    'whoami', 'date', 'uname', 'hostname', 'id', 'env', 'printenv',
    'git status', 'git log', 'git diff', 'git branch', 'git remote',
    'git show', 'git stash', 'git tag',
    'python --version', 'pip list', 'pip show', 'pip freeze',
    'node --version', 'npm list',
    'docker ps', 'docker images', 'docker logs',
    'ps', 'top', 'df', 'du', 'free', 'uptime',
    'find', 'grep', 'wc', 'sort', 'uniq', 'awk',
    'which', 'where', 'command -v',
]

REQUIRES_CONFIRMATION_PREFIXES = [
    'python -c', 'python -m', 'sed', 'npm install',
    'pip install', 'cargo install', 'go install',
    'git push', 'git reset', 'git clean', 'git checkout',
    'docker run', 'docker exec', 'docker build',
    'curl', 'wget',
]


def _validate_bash_command(command: str) -> tuple:
    """验证 Bash 命令安全性，返回 (is_safe, reason)"""
    stripped = command.strip()

    for pattern in DANGEROUS_PATTERNS:
        if pattern.search(stripped):
            return False, f"危险命令模式被拦截"

    for prefix in SAFE_COMMAND_PREFIXES:
        if stripped.lower().startswith(prefix.lower()):
            if not SHELL_META_PATTERN.search(stripped[len(prefix):]):
                return True, ""

    for prefix in REQUIRES_CONFIRMATION_PREFIXES:
        if stripped.lower().startswith(prefix.lower()):
            return True, "需权限确认的命令类型"

    if SHELL_META_PATTERN.search(stripped):
        return True, "shell元字符检测，需权限确认"

    return True, "未知命令，需权限确认"


PROJECT_ROOT = os.environ.get(
    "GEMMA4_PROJECT_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

FORBIDDEN_PATH_PATTERNS = [
    re.compile(r'[\\/]\.ssh[\\/]', re.IGNORECASE),
    re.compile(r'[\\/]etc[\\/]passwd', re.IGNORECASE),
    re.compile(r'[\\/]etc[\\/]shadow', re.IGNORECASE),
    re.compile(r'[\\/]Windows[\\/]System32[\\/]', re.IGNORECASE),
    re.compile(r'[\\/]boot[\\/]', re.IGNORECASE),
    re.compile(r'[\\/]proc[\\/]', re.IGNORECASE),
    re.compile(r'[\\/]sys[\\/]', re.IGNORECASE),
    re.compile(r'[\\/]dev[\\/]', re.IGNORECASE),
    re.compile(r'[\\/]root[\\/]\.ssh', re.IGNORECASE),
]


def _validate_file_path(filepath: str, allow_write: bool = False) -> tuple:
    """验证文件路径安全性，返回 (is_safe, reason)"""
    abs_path = os.path.abspath(filepath)

    for pattern in FORBIDDEN_PATH_PATTERNS:
        if pattern.search(abs_path):
            return False, "禁止访问敏感路径"

    if allow_write:
        home = os.path.expanduser("~")
        sensitive_dirs = [
            os.path.join(home, ".ssh"),
            os.path.join(home, ".gnupg"),
            os.path.join(home, ".aws"),
        ]
        for sd in sensitive_dirs:
            if abs_path.startswith(sd):
                return False, "禁止写入安全凭证目录"

        sandbox_enabled = os.environ.get("GEMMA4_FILE_SANDBOX", "true").lower() == "true"
        if sandbox_enabled:
            if not abs_path.startswith(PROJECT_ROOT):
                return False, f"禁止写入项目目录外的文件（沙箱模式）"

    return True, ""


async def _tool_bash(params: Dict[str, Any], ctx: Dict[str, Any]) -> ToolResult:
    """执行 Bash/Shell 命令"""
    command = params.get("command", "")
    timeout = min(int(params.get("timeout", 30)), MAX_BASH_TIMEOUT)
    cwd = params.get("cwd", os.getcwd())

    if not command:
        return ToolResult(success=False, error="缺少 command 参数")

    is_safe, reason = _validate_bash_command(command)
    if not is_safe:
        return ToolResult(success=False, error=f"命令被安全策略拦截: {reason}")

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return ToolResult(success=False, error=f"命令超时（{timeout}s）", data={"timed_out": True})

        output = stdout.decode("utf-8", errors="replace")
        error_output = stderr.decode("utf-8", errors="replace")

        if len(output) > MAX_OUTPUT_LENGTH:
            output = output[:MAX_OUTPUT_LENGTH] + f"\n... (截断，共 {len(output)} 字符)"

        result_data = {
            "exit_code": proc.returncode,
            "stdout_length": len(output),
            "stderr_length": len(error_output),
        }

        combined = output
        if error_output:
            combined += f"\n[stderr]\n{error_output}"

        return ToolResult(
            success=proc.returncode == 0,
            output=combined,
            data=result_data,
        )
    except Exception as e:
        return ToolResult(success=False, error=f"命令执行失败: {e}")


async def _tool_file_read(params: Dict[str, Any], ctx: Dict[str, Any]) -> ToolResult:
    """读取文件内容"""
    filepath = params.get("path", "")
    encoding = params.get("encoding", "utf-8")
    offset = int(params.get("offset", 0))
    limit = int(params.get("limit", 2000))

    if not filepath:
        return ToolResult(success=False, error="缺少 path 参数")

    if not os.path.exists(filepath):
        return ToolResult(success=False, error=f"文件不存在: {filepath}")

    if os.path.getsize(filepath) > MAX_FILE_SIZE:
        return ToolResult(success=False, error=f"文件过大（>{MAX_FILE_SIZE // 1024 // 1024}MB）")

    try:
        with open(filepath, "r", encoding=encoding, errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)
        start = max(0, offset)
        end = min(total_lines, start + limit)
        selected = lines[start:end]

        output_lines = []
        for i, line in enumerate(selected, start=start + 1):
            output_lines.append(f"{i:>6}→{line.rstrip()}")

        output = "\n".join(output_lines)
        return ToolResult(
            success=True,
            output=output,
            data={
                "total_lines": total_lines,
                "shown_lines": end - start,
                "offset": start,
                "path": filepath,
            }
        )
    except Exception as e:
        return ToolResult(success=False, error=f"读取文件失败: {e}")


async def _tool_file_edit(params: Dict[str, Any], ctx: Dict[str, Any]) -> ToolResult:
    """编辑文件（搜索替换）"""
    filepath = params.get("path", "")
    old_str = params.get("old_str", "")
    new_str = params.get("new_str", "")
    encoding = params.get("encoding", "utf-8")

    if not all([filepath, old_str]):
        return ToolResult(success=False, error="缺少 path 或 old_str 参数")

    is_safe, reason = _validate_file_path(filepath, allow_write=True)
    if not is_safe:
        return ToolResult(success=False, error=f"路径安全策略拦截: {reason}")

    if not os.path.exists(filepath):
        return ToolResult(success=False, error=f"文件不存在: {filepath}")

    try:
        with open(filepath, "r", encoding=encoding, errors="replace") as f:
            content = f.read()

        count = content.count(old_str)
        if count == 0:
            return ToolResult(success=False, error="未找到匹配内容")
        if count > 1:
            return ToolResult(success=False, error=f"找到 {count} 处匹配，请提供更精确的上下文")

        new_content = content.replace(old_str, new_str, 1)

        tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(filepath), suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding=encoding) as f:
                f.write(new_content)
            os.replace(tmp_path, filepath)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

        return ToolResult(
            success=True,
            output=f"已替换 1 处匹配",
            data={"path": filepath, "replacements": 1}
        )
    except Exception as e:
        return ToolResult(success=False, error=f"编辑文件失败: {e}")


async def _tool_file_write(params: Dict[str, Any], ctx: Dict[str, Any]) -> ToolResult:
    """写入文件"""
    filepath = params.get("path", "")
    content = params.get("content", "")
    encoding = params.get("encoding", "utf-8")
    append = params.get("append", False)

    if not filepath:
        return ToolResult(success=False, error="缺少 path 参数")

    is_safe, reason = _validate_file_path(filepath, allow_write=True)
    if not is_safe:
        return ToolResult(success=False, error=f"路径安全策略拦截: {reason}")

    try:
        dirpath = os.path.dirname(filepath)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)

        if append:
            with open(filepath, "a", encoding=encoding) as f:
                f.write(content)
        else:
            tmp_fd, tmp_path = tempfile.mkstemp(dir=dirpath or ".", suffix=".tmp")
            try:
                with os.fdopen(tmp_fd, "w", encoding=encoding) as f:
                    f.write(content)
                os.replace(tmp_path, filepath)
            except Exception:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise

        return ToolResult(
            success=True,
            output=f"已{'追加' if append else '写入'} {len(content)} 字符到 {filepath}",
            data={"path": filepath, "bytes_written": len(content.encode(encoding)), "append": append}
        )
    except Exception as e:
        return ToolResult(success=False, error=f"写入文件失败: {e}")


async def _tool_glob(params: Dict[str, Any], ctx: Dict[str, Any]) -> ToolResult:
    """文件模式匹配搜索"""
    pattern = params.get("pattern", "")
    path = params.get("path", os.getcwd())

    if not pattern:
        return ToolResult(success=False, error="缺少 pattern 参数")

    try:
        matches = glob_module.glob(os.path.join(path, pattern), recursive=True)
        matches = sorted(matches)[:500]

        if not matches:
            return ToolResult(success=True, output="未找到匹配文件", data={"count": 0})

        output_lines = [f"找到 {len(matches)} 个文件：", ""]
        for m in matches:
            rel = os.path.relpath(m, path) if not os.path.isabs(m) else m
            output_lines.append(f"  {rel}")

        return ToolResult(
            success=True,
            output="\n".join(output_lines),
            data={"count": len(matches), "pattern": pattern}
        )
    except Exception as e:
        return ToolResult(success=False, error=f"Glob 搜索失败: {e}")


async def _tool_grep(params: Dict[str, Any], ctx: Dict[str, Any]) -> ToolResult:
    """文本内容搜索（类 ripgrep）"""
    pattern = params.get("pattern", "")
    path = params.get("path", os.getcwd())
    file_pattern = params.get("glob", "")
    case_insensitive = params.get("ignore_case", True)
    max_results = int(params.get("max_results", 100))

    if not pattern:
        return ToolResult(success=False, error="缺少 pattern 参数")

    try:
        flags = re.IGNORECASE if case_insensitive else 0
        regex = re.compile(pattern, flags)
    except re.error as e:
        return ToolResult(success=False, error=f"正则表达式无效: {e}")

    try:
        results = []
        for root, dirs, files in os.walk(path):
            for fname in files:
                if file_pattern:
                    if not glob_module.fnmatch.fnmatch(fname, file_pattern):
                        continue

                fpath = os.path.join(root, fname)
                try:
                    if os.path.getsize(fpath) > MAX_FILE_SIZE:
                        continue
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                rel = os.path.relpath(fpath, path)
                                results.append(f"{rel}:{line_num}: {line.rstrip()}")
                                if len(results) >= max_results:
                                    break
                except Exception:
                    continue
                if len(results) >= max_results:
                    break

        if not results:
            return ToolResult(success=True, output="未找到匹配", data={"count": 0})

        output = "\n".join(results)
        if len(output) > MAX_OUTPUT_LENGTH:
            output = output[:MAX_OUTPUT_LENGTH] + f"\n... (截断)"

        return ToolResult(
            success=True,
            output=output,
            data={"count": len(results), "pattern": pattern}
        )
    except Exception as e:
        return ToolResult(success=False, error=f"Grep 搜索失败: {e}")


async def _tool_workflow(params: Dict[str, Any], ctx: Dict[str, Any]) -> ToolResult:
    """
    工作流工具
    借鉴 cc-haha-main 的 WorkflowTool，实现脚本化工作流执行
    支持 YAML/JSON 格式的工作流定义
    """
    workflow_str = params.get("workflow", "")
    workflow_file = params.get("workflow_file", "")
    variables = params.get("variables", {})

    if not workflow_str and not workflow_file:
        return ToolResult(success=False, error="缺少 workflow 或 workflow_file 参数")

    if workflow_file:
        if not os.path.exists(workflow_file):
            return ToolResult(success=False, error=f"工作流文件不存在: {workflow_file}")
        try:
            with open(workflow_file, "r", encoding="utf-8") as f:
                workflow_str = f.read()
        except Exception as e:
            return ToolResult(success=False, error=f"读取工作流文件失败: {e}")

    try:
        if workflow_str.strip().startswith("{"):
            workflow = json.loads(workflow_str)
        else:
            try:
                import yaml
                workflow = yaml.safe_load(workflow_str)
            except ImportError:
                return ToolResult(
                    success=False,
                    error="YAML 工作流需要 PyYAML 库，请使用 JSON 格式或安装 PyYAML"
                )
    except json.JSONDecodeError as e:
        return ToolResult(success=False, error=f"工作流定义解析失败: {e}")

    if not isinstance(workflow, dict):
        return ToolResult(success=False, error="工作流定义必须是对象/字典")

    name = workflow.get("name", "未命名工作流")
    steps = workflow.get("steps", [])
    if not steps:
        return ToolResult(success=False, error="工作流无步骤定义")

    results = []
    for i, step in enumerate(steps):
        step_name = step.get("name", f"步骤 {i + 1}")
        step_type = step.get("type", "shell")
        step_command = step.get("command", "")
        step_params = step.get("params", {})

        for key, value in variables.items():
            if isinstance(step_command, str):
                step_command = step_command.replace(f"{{{{{key}}}}}", str(value))

        step_result = {"step": step_name, "type": step_type}

        if step_type == "shell":
            try:
                proc = await asyncio.create_subprocess_shell(
                    step_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=step_params.get("timeout", 60)
                )
                step_result["exit_code"] = proc.returncode
                step_result["output"] = stdout.decode("utf-8", errors="replace")[:2000]
                step_result["success"] = proc.returncode == 0
            except asyncio.TimeoutError:
                step_result["success"] = False
                step_result["error"] = "超时"
            except Exception as e:
                step_result["success"] = False
                step_result["error"] = str(e)

        elif step_type == "tool":
            try:
                from kairos.services.tools import get_tool_registry
                tr = get_tool_registry()
                tool_result = await tr.execute(step_command, step_params, ctx)
                step_result["success"] = tool_result.success
                step_result["output"] = tool_result.output[:2000]
                step_result["error"] = tool_result.error
            except Exception as e:
                step_result["success"] = False
                step_result["error"] = str(e)

        elif step_type == "echo":
            step_result["output"] = step_command
            step_result["success"] = True

        else:
            step_result["success"] = False
            step_result["error"] = f"未知步骤类型: {step_type}"

        results.append(step_result)

        on_failure = step.get("on_failure", "stop")
        if not step_result["success"] and on_failure == "stop":
            break

    success_count = sum(1 for r in results if r.get("success"))
    total_count = len(results)
    all_success = success_count == total_count

    output_lines = [
        f"工作流: {name}",
        f"结果: {success_count}/{total_count} 步骤成功",
        "",
    ]
    for r in results:
        status = "✓" if r.get("success") else "✗"
        output_lines.append(f"  [{status}] {r['step']}")
        if r.get("output"):
            output_lines.append(f"       {r['output'][:200]}")
        if r.get("error"):
            output_lines.append(f"       错误: {r['error'][:200]}")

    return ToolResult(
        success=all_success,
        output="\n".join(output_lines),
        data={
            "workflow_name": name,
            "total_steps": total_count,
            "success_steps": success_count,
            "results": results,
        }
    )


async def _tool_web_fetch(params: Dict[str, Any], ctx: Dict[str, Any]) -> ToolResult:
    """获取网页内容"""
    url = params.get("url", "")
    max_length = int(params.get("max_length", 10000))

    if not url:
        return ToolResult(success=False, error="缺少 url 参数")

    if not url.startswith(("http://", "https://")):
        return ToolResult(success=False, error="URL 必须以 http:// 或 https:// 开头")

    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Gemma4/1.0"})
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: urllib.request.urlopen(req, timeout=15)
        )
        content = response.read().decode("utf-8", errors="replace")

        if len(content) > max_length:
            content = content[:max_length] + f"\n... (截断，共 {len(content)} 字符)"

        return ToolResult(
            success=True,
            output=content,
            data={"url": url, "status": response.status, "length": len(content)}
        )
    except Exception as e:
        return ToolResult(success=False, error=f"获取网页失败: {e}")


async def _tool_list_dir(params: Dict[str, Any], ctx: Dict[str, Any]) -> ToolResult:
    """列出目录内容"""
    path = params.get("path", os.getcwd())
    show_hidden = params.get("show_hidden", False)

    if not os.path.exists(path):
        return ToolResult(success=False, error=f"路径不存在: {path}")

    if not os.path.isdir(path):
        return ToolResult(success=False, error=f"不是目录: {path}")

    try:
        entries = os.listdir(path)
        if not show_hidden:
            entries = [e for e in entries if not e.startswith(".")]

        dirs = []
        files = []
        for e in sorted(entries):
            full = os.path.join(path, e)
            if os.path.isdir(full):
                dirs.append(f"  📁 {e}/")
            else:
                size = os.path.getsize(full)
                size_str = f"{size}" if size < 1024 else f"{size / 1024:.1f}KB"
                files.append(f"  📄 {e} ({size_str})")

        output_lines = [f"目录: {path}", f"共 {len(dirs)} 个目录, {len(files)} 个文件", ""]
        output_lines.extend(dirs)
        output_lines.extend(files)

        return ToolResult(
            success=True,
            output="\n".join(output_lines),
            data={"dirs": len(dirs), "files": len(files), "path": path}
        )
    except Exception as e:
        return ToolResult(success=False, error=f"列出目录失败: {e}")


def register_builtin_tools(registry: ToolRegistry) -> None:
    """注册所有内置工具"""

    registry.register(build_tool(
        name="bash",
        description="执行 Shell/Bash 命令",
        handler=_tool_bash,
        parameters=[
            ToolParameter("command", "string", "要执行的命令", required=True),
            ToolParameter("timeout", "integer", "超时秒数", required=False, default=30),
            ToolParameter("cwd", "string", "工作目录", required=False),
        ],
        permission=PermissionLevel.EXECUTE,
        is_concurrency_safe=False,
        is_read_only=False,
        category="系统",
        timeout_seconds=MAX_BASH_TIMEOUT,
    ))

    registry.register(build_tool(
        name="file_read",
        description="读取文件内容",
        handler=_tool_file_read,
        parameters=[
            ToolParameter("path", "string", "文件路径", required=True),
            ToolParameter("encoding", "string", "编码", required=False, default="utf-8"),
            ToolParameter("offset", "integer", "起始行号", required=False, default=0),
            ToolParameter("limit", "integer", "最大行数", required=False, default=2000),
        ],
        permission=PermissionLevel.READ,
        is_concurrency_safe=True,
        is_read_only=True,
        category="文件",
    ))

    registry.register(build_tool(
        name="file_edit",
        description="编辑文件（搜索替换）",
        handler=_tool_file_edit,
        parameters=[
            ToolParameter("path", "string", "文件路径", required=True),
            ToolParameter("old_str", "string", "要替换的文本", required=True),
            ToolParameter("new_str", "string", "替换后的文本", required=True),
            ToolParameter("encoding", "string", "编码", required=False, default="utf-8"),
        ],
        permission=PermissionLevel.WRITE,
        is_concurrency_safe=False,
        is_read_only=False,
        category="文件",
    ))

    registry.register(build_tool(
        name="file_write",
        description="写入文件",
        handler=_tool_file_write,
        parameters=[
            ToolParameter("path", "string", "文件路径", required=True),
            ToolParameter("content", "string", "文件内容", required=True),
            ToolParameter("encoding", "string", "编码", required=False, default="utf-8"),
            ToolParameter("append", "boolean", "追加模式", required=False, default=False),
        ],
        permission=PermissionLevel.WRITE,
        is_concurrency_safe=False,
        is_read_only=False,
        category="文件",
    ))

    registry.register(build_tool(
        name="glob",
        description="文件模式匹配搜索",
        handler=_tool_glob,
        parameters=[
            ToolParameter("pattern", "string", "匹配模式（如 **/*.py）", required=True),
            ToolParameter("path", "string", "搜索根目录", required=False),
        ],
        permission=PermissionLevel.READ,
        is_concurrency_safe=True,
        is_read_only=True,
        category="文件",
    ))

    registry.register(build_tool(
        name="grep",
        description="文本内容搜索（支持正则）",
        handler=_tool_grep,
        parameters=[
            ToolParameter("pattern", "string", "搜索模式（正则表达式）", required=True),
            ToolParameter("path", "string", "搜索目录", required=False),
            ToolParameter("glob", "string", "文件名过滤（如 *.py）", required=False),
            ToolParameter("ignore_case", "boolean", "忽略大小写", required=False, default=True),
            ToolParameter("max_results", "integer", "最大结果数", required=False, default=100),
        ],
        permission=PermissionLevel.READ,
        is_concurrency_safe=True,
        is_read_only=True,
        category="文件",
    ))

    registry.register(build_tool(
        name="workflow",
        description="执行工作流脚本（支持 JSON/YAML 格式）",
        handler=_tool_workflow,
        parameters=[
            ToolParameter("workflow", "string", "工作流定义（JSON/YAML 字符串）", required=False),
            ToolParameter("workflow_file", "string", "工作流文件路径", required=False),
            ToolParameter("variables", "object", "变量映射", required=False, default={}),
        ],
        permission=PermissionLevel.EXECUTE,
        is_concurrency_safe=False,
        is_read_only=False,
        category="工作流",
        timeout_seconds=600,
    ))

    registry.register(build_tool(
        name="web_fetch",
        description="获取网页内容",
        handler=_tool_web_fetch,
        parameters=[
            ToolParameter("url", "string", "URL 地址", required=True),
            ToolParameter("max_length", "integer", "最大内容长度", required=False, default=10000),
        ],
        permission=PermissionLevel.READ,
        is_concurrency_safe=True,
        is_read_only=True,
        category="网络",
    ))

    registry.register(build_tool(
        name="list_dir",
        description="列出目录内容",
        handler=_tool_list_dir,
        parameters=[
            ToolParameter("path", "string", "目录路径", required=False),
            ToolParameter("show_hidden", "boolean", "显示隐藏文件", required=False, default=False),
        ],
        permission=PermissionLevel.READ,
        is_concurrency_safe=True,
        is_read_only=True,
        category="文件",
    ))

    logger.info(f"已注册 {len(registry._tools)} 个内置工具")
