"""
内置命令注册
定义所有内置斜杠命令，按功能分类注册
"""

import os
import sys
import time
import psutil
import asyncio
import logging
from typing import Dict, Any

from . import CommandDef, CommandType, CommandResult, CommandRegistry

logger = logging.getLogger("BuiltInCommands")


def _get_system_info() -> Dict[str, Any]:
    try:
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)
        if sys.platform == "win32":
            disk = psutil.disk_usage("C:\\")
        else:
            disk = psutil.disk_usage("/")
        return {
            "cpu_percent": cpu,
            "memory_percent": mem.percent,
            "memory_available_mb": round(mem.available / (1024 * 1024)),
            "memory_total_mb": round(mem.total / (1024 * 1024)),
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024 ** 3), 2),
        }
    except Exception:
        return {"error": "无法获取系统信息"}


async def _cmd_help(args: str, ctx: Dict[str, Any]) -> CommandResult:
    registry = ctx.get("registry")
    if not registry:
        return CommandResult(success=False, error="注册中心不可用")

    query = args.strip()
    if query:
        cmds = registry.search(query)
        if not cmds:
            return CommandResult(success=True, output=f"未找到与 '{query}' 匹配的命令")
        lines = [f"搜索结果（{len(cmds)} 个命令）：", ""]
        for cmd in cmds:
            alias_str = f" ({', '.join('/' + a for a in cmd.aliases)})" if cmd.aliases else ""
            lines.append(f"  /{cmd.name}{alias_str} - {cmd.description}")
            if cmd.usage:
                lines.append(f"    用法: {cmd.usage}")
        return CommandResult(success=True, output="\n".join(lines))

    by_category = registry.list_by_category()
    lines = ["可用命令列表：", ""]
    for category, cmds in sorted(by_category.items()):
        lines.append(f"【{category}】")
        for cmd in cmds:
            alias_str = f" ({', '.join('/' + a for a in cmd.aliases)})" if cmd.aliases else ""
            lines.append(f"  /{cmd.name}{alias_str} - {cmd.description}")
        lines.append("")
    lines.append("输入 /help <关键词> 搜索命令")
    return CommandResult(success=True, output="\n".join(lines))


async def _cmd_clear(args: str, ctx: Dict[str, Any]) -> CommandResult:
    history = ctx.get("chat_history")
    if history is not None:
        if isinstance(history, list):
            history.clear()
        return CommandResult(success=True, output="对话历史已清除")
    return CommandResult(success=True, output="清除命令已执行")


async def _cmd_model(args: str, ctx: Dict[str, Any]) -> CommandResult:
    if not args.strip():
        current = ctx.get("current_model", "gemma4:e4b")
        return CommandResult(
            success=True,
            output=f"当前模型: {current}",
            data={"current_model": current}
        )

    new_model = args.strip()
    ctx["current_model"] = new_model
    return CommandResult(
        success=True,
        output=f"模型已切换为: {new_model}",
        data={"current_model": new_model}
    )


async def _cmd_models(args: str, ctx: Dict[str, Any]) -> CommandResult:
    try:
        import ollama
        models_data = ollama.list()
        model_list = []
        if models_data and 'models' in models_data:
            for m in models_data['models']:
                if isinstance(m, dict):
                    name = m.get('name', 'unknown')
                    size = m.get('size', 0)
                    size_str = f"{size / (1024**9):.1f}GB" if size > 1024**9 else f"{size / (1024**6):.1f}MB"
                    model_list.append(f"  {name} ({size_str})")
        if not model_list:
            return CommandResult(success=True, output="未发现可用模型，请确认 Ollama 正在运行")
        current = ctx.get("current_model", "gemma4:e4b")
        lines = [f"可用模型（当前: {current}）：", ""]
        lines.extend(model_list)
        return CommandResult(success=True, output="\n".join(lines))
    except Exception as e:
        return CommandResult(success=False, error=f"获取模型列表失败: {e}")


async def _cmd_status(args: str, ctx: Dict[str, Any]) -> CommandResult:
    sys_info = _get_system_info()
    current_model = ctx.get("current_model", "gemma4:e4b")

    try:
        from kairos.system.degradation import get_degradation_manager
        dm = get_degradation_manager()
        level = dm.current_level.name
    except Exception:
        level = "UNKNOWN"

    try:
        from kairos.version import VERSION, SYSTEM_NAME
        version = VERSION
        name = SYSTEM_NAME
    except Exception:
        version = "unknown"
        name = "Gemma4"

    lines = [
        f"系统名称: {name}",
        f"版本: {version}",
        f"当前模型: {current_model}",
        f"服务级别: {level}",
        f"Python: {sys.version.split()[0]}",
        f"CPU: {sys_info.get('cpu_percent', 'N/A')}%",
        f"内存: {sys_info.get('memory_percent', 'N/A')}% ({sys_info.get('memory_available_mb', 'N/A')} MB 可用)",
        f"磁盘: {sys_info.get('disk_percent', 'N/A')}% ({sys_info.get('disk_free_gb', 'N/A')} GB 可用)",
    ]
    return CommandResult(success=True, output="\n".join(lines))


async def _cmd_doctor(args: str, ctx: Dict[str, Any]) -> CommandResult:
    checks = []

    try:
        import ollama
        ollama.list()
        checks.append(("Ollama 服务", True, "正常运行"))
    except Exception as e:
        checks.append(("Ollama 服务", False, str(e)[:80]))

    try:
        from kairos.system.degradation import get_degradation_manager
        dm = get_degradation_manager()
        level = dm.current_level.name
        checks.append(("降级管理器", True, f"级别: {level}"))
    except Exception as e:
        checks.append(("降级管理器", False, str(e)[:80]))

    try:
        from kairos.system.llm_reasoning import get_ollama_client
        client = get_ollama_client()
        available = await client.is_available()
        checks.append(("LLM 推理服务", available, "可用" if available else "不可用"))
    except Exception as e:
        checks.append(("LLM 推理服务", False, str(e)[:80]))

    try:
        from kairos.services.compact import get_compact_service
        cs = get_compact_service()
        checks.append(("上下文压缩", True, f"已压缩 {cs._total_compactions} 次"))
    except Exception:
        checks.append(("上下文压缩", False, "未加载"))

    try:
        from kairos.services.mcp import get_mcp_manager
        mm = get_mcp_manager()
        servers = mm.list_servers()
        checks.append(("MCP 服务", True, f"{len(servers)} 个服务器"))
    except Exception:
        checks.append(("MCP 服务", False, "未加载"))

    sys_info = _get_system_info()
    mem_ok = sys_info.get("memory_percent", 100) < 90
    checks.append(("内存状态", mem_ok, f"{sys_info.get('memory_percent', 'N/A')}%"))

    lines = ["系统诊断报告：", ""]
    all_ok = True
    for name, ok, detail in checks:
        status = "✓" if ok else "✗"
        lines.append(f"  [{status}] {name}: {detail}")
        if not ok:
            all_ok = False

    lines.append("")
    lines.append("诊断结果: " + ("所有检查通过" if all_ok else "存在问题，请查看上方详情"))
    return CommandResult(success=True, output="\n".join(lines))


async def _cmd_config(args: str, ctx: Dict[str, Any]) -> CommandResult:
    if not args.strip():
        config_items = {
            "GEMMA4_MODEL": os.environ.get("GEMMA4_MODEL", "gemma4:e4b"),
            "OLLAMA_HOST": os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
            "GEMMA4_ENV": os.environ.get("GEMMA4_ENV", "development"),
            "GEMMA4_LLM_TIMEOUT": os.environ.get("GEMMA4_LLM_TIMEOUT", "30"),
            "GEMMA4_AUTH_ENABLED": os.environ.get("GEMMA4_AUTH_ENABLED", "false"),
            "GEMMA4_METRICS_ENABLED": os.environ.get("GEMMA4_METRICS_ENABLED", "true"),
        }
        lines = ["当前配置：", ""]
        for key, value in config_items.items():
            lines.append(f"  {key} = {value}")
        lines.append("")
        lines.append("使用 /config set KEY=VALUE 修改配置")
        return CommandResult(success=True, output="\n".join(lines))

    if args.strip().startswith("set "):
        kv_str = args.strip()[4:].strip()
        if "=" not in kv_str:
            return CommandResult(success=False, error="格式: /config set KEY=VALUE")
        key, _, value = kv_str.partition("=")
        key = key.strip()
        value = value.strip()

        ALLOWED_CONFIG_KEYS = {
            "GEMMA4_MODEL", "GEMMA4_ENV", "GEMMA4_LOG_LEVEL",
            "GEMMA4_CONTEXT_WINDOW", "GEMMA4_MAX_OUTPUT_TOKENS",
            "GEMMA4_DATA_DIR", "GEMMA4_HOST", "GEMMA4_PORT",
        }
        if key not in ALLOWED_CONFIG_KEYS:
            return CommandResult(
                success=False,
                error=f"不允许修改 {key}，允许的配置项: {', '.join(sorted(ALLOWED_CONFIG_KEYS))}"
            )

        os.environ[key] = value
        return CommandResult(success=True, output=f"已设置 {key}={value}")

    return CommandResult(success=False, error="未知配置操作，使用 /config 或 /config set KEY=VALUE")


async def _cmd_cost(args: str, ctx: Dict[str, Any]) -> CommandResult:
    registry = ctx.get("registry")
    if registry:
        stats = registry.get_stats()
    else:
        stats = {}

    chat_count = ctx.get("chat_count", 0)
    total_tokens = ctx.get("total_tokens", 0)

    lines = [
        "使用统计：",
        "",
        f"  对话次数: {chat_count}",
        f"  估算 Token 数: {total_tokens}",
        f"  命令执行次数: {stats.get('total_executions', 0)}",
        f"  命令成功率: {stats.get('success_rate', 0):.1%}",
        f"  平均命令耗时: {stats.get('avg_duration_ms', 0):.1f}ms",
        "",
        "注: 本地模型无实际费用，此为使用量统计",
    ]
    return CommandResult(success=True, output="\n".join(lines))


async def _cmd_memory(args: str, ctx: Dict[str, Any]) -> CommandResult:
    sub = args.strip().lower()

    if sub == "clear":
        try:
            from modules.memory.manager import MemoryManager
            mm = MemoryManager()
            mm.clear_all()
            return CommandResult(success=True, output="记忆已清除")
        except Exception as e:
            return CommandResult(success=False, error=f"清除记忆失败: {e}")

    if sub == "stats":
        try:
            from modules.memory.manager import MemoryManager
            mm = MemoryManager()
            stats = mm.get_stats()
            lines = ["记忆统计：", ""]
            for k, v in stats.items():
                lines.append(f"  {k}: {v}")
            return CommandResult(success=True, output="\n".join(lines))
        except Exception as e:
            return CommandResult(success=False, error=f"获取记忆统计失败: {e}")

    return CommandResult(
        success=True,
        output="记忆管理命令：\n  /memory stats - 查看记忆统计\n  /memory clear - 清除所有记忆"
    )


async def _cmd_compact(args: str, ctx: Dict[str, Any]) -> CommandResult:
    try:
        from kairos.services.compact import get_compact_service
        cs = get_compact_service()
        history = ctx.get("chat_history", [])
        if not history:
            return CommandResult(success=True, output="无对话历史需要压缩")

        result = await cs.compact(history)
        return CommandResult(
            success=True,
            output=f"对话历史已压缩: {result.get('original_count', 0)} 条 → {result.get('compacted_count', 0)} 条",
            data=result
        )
    except ImportError:
        return CommandResult(success=False, error="压缩服务未加载")
    except Exception as e:
        return CommandResult(success=False, error=f"压缩失败: {e}")


async def _cmd_review(args: str, ctx: Dict[str, Any]) -> CommandResult:
    history = ctx.get("chat_history", [])
    if not history:
        return CommandResult(success=True, output="无对话历史可供回顾")

    lines = [f"对话回顾（最近 {min(len(history), 10)} 条）：", ""]
    for msg in history[-10:]:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")[:80]
        lines.append(f"  [{role}] {content}{'...' if len(msg.get('content', '')) > 80 else ''}")

    return CommandResult(success=True, output="\n".join(lines))


async def _cmd_tasks(args: str, ctx: Dict[str, Any]) -> CommandResult:
    sub = args.strip().lower()

    if sub == "list":
        try:
            from modules.scheduler.task import TaskScheduler
            ts = TaskScheduler()
            tasks = ts.list_tasks()
            if not tasks:
                return CommandResult(success=True, output="当前无任务")
            lines = [f"任务列表（{len(tasks)} 个）：", ""]
            for t in tasks:
                lines.append(f"  [{t.get('status', '?')}] {t.get('name', '?')} - {t.get('description', '')[:60]}")
            return CommandResult(success=True, output="\n".join(lines))
        except Exception as e:
            return CommandResult(success=False, error=f"获取任务列表失败: {e}")

    return CommandResult(
        success=True,
        output="任务管理命令：\n  /tasks list - 查看任务列表"
    )


async def _cmd_diff(args: str, ctx: Dict[str, Any]) -> CommandResult:
    if not args.strip():
        return CommandResult(success=False, error="请指定文件路径: /diff <filepath>")

    filepath = args.strip()
    if not os.path.exists(filepath):
        return CommandResult(success=False, error=f"文件不存在: {filepath}")

    try:
        from kairos.system.git_integration import GitIntegration
        gi = GitIntegration()
        diff = gi.get_file_diff(filepath)
        if not diff:
            return CommandResult(success=True, output=f"文件 {filepath} 无变更")
        return CommandResult(success=True, output=diff[:5000])
    except Exception as e:
        return CommandResult(success=False, error=f"获取差异失败: {e}")


async def _cmd_commit(args: str, ctx: Dict[str, Any]) -> CommandResult:
    message = args.strip()
    if not message:
        return CommandResult(success=False, error="请提供提交信息: /commit <message>")

    try:
        from kairos.system.git_integration import GitIntegration
        gi = GitIntegration()
        result = gi.commit_all(message)
        return CommandResult(success=True, output=f"提交成功: {result}")
    except Exception as e:
        return CommandResult(success=False, error=f"提交失败: {e}")


async def _cmd_tools(args: str, ctx: Dict[str, Any]) -> CommandResult:
    sub = args.strip().lower()

    if sub == "list":
        try:
            from kairos.services.tools import get_tool_registry
            tr = get_tool_registry()
            tools = tr.list_tools()
            if not tools:
                return CommandResult(success=True, output="无可用工具")
            lines = [f"可用工具（{len(tools)} 个）：", ""]
            for t in tools:
                lines.append(f"  {t['name']} - {t.get('description', '')[:60]}")
            return CommandResult(success=True, output="\n".join(lines))
        except ImportError:
            return CommandResult(success=False, error="工具系统未加载")
        except Exception as e:
            return CommandResult(success=False, error=f"获取工具列表失败: {e}")

    return CommandResult(
        success=True,
        output="工具管理命令：\n  /tools list - 查看可用工具"
    )


async def _cmd_mcp(args: str, ctx: Dict[str, Any]) -> CommandResult:
    sub = args.strip().lower()

    if sub == "list" or not sub:
        try:
            from kairos.services.mcp import get_mcp_manager
            mm = get_mcp_manager()
            servers = mm.list_servers()
            if not servers:
                return CommandResult(success=True, output="无已连接的 MCP 服务器")
            lines = [f"MCP 服务器（{len(servers)} 个）：", ""]
            for s in servers:
                status = "已连接" if s.get("connected") else "未连接"
                tools_count = s.get("tools_count", 0)
                lines.append(f"  {s['name']} [{status}] ({tools_count} 工具)")
            return CommandResult(success=True, output="\n".join(lines))
        except ImportError:
            return CommandResult(success=False, error="MCP 服务未加载")
        except Exception as e:
            return CommandResult(success=False, error=f"获取 MCP 状态失败: {e}")

    return CommandResult(
        success=True,
        output="MCP 管理命令：\n  /mcp list - 查看 MCP 服务器"
    )


async def _cmd_quit(args: str, ctx: Dict[str, Any]) -> CommandResult:
    return CommandResult(success=True, output="再见！", data={"quit": True})


async def _cmd_history(args: str, ctx: Dict[str, Any]) -> CommandResult:
    registry = ctx.get("registry")
    if not registry:
        return CommandResult(success=False, error="注册中心不可用")

    history = registry._execution_history[-20:]
    if not history:
        return CommandResult(success=True, output="无命令执行历史")

    lines = [f"最近命令执行历史（{len(history)} 条）：", ""]
    for e in history:
        status = "✓" if e["success"] else "✗"
        lines.append(f"  [{status}] /{e['command']} ({e['duration_ms']:.1f}ms)")
    return CommandResult(success=True, output="\n".join(lines))


def register_builtin_commands(registry: CommandRegistry) -> None:
    """注册所有内置命令"""

    registry.register(CommandDef(
        name="help",
        type=CommandType.LOCAL,
        description="显示帮助信息或搜索命令",
        aliases=["h", "?"],
        usage="/help [关键词]",
        local_handler=_cmd_help,
        category="帮助",
    ))

    registry.register(CommandDef(
        name="clear",
        type=CommandType.LOCAL,
        description="清除对话历史",
        aliases=["cls", "清屏"],
        local_handler=_cmd_clear,
        category="对话",
    ))

    registry.register(CommandDef(
        name="model",
        type=CommandType.LOCAL,
        description="查看或切换当前模型",
        aliases=["m"],
        usage="/model [模型名]",
        local_handler=_cmd_model,
        category="模型",
    ))

    registry.register(CommandDef(
        name="models",
        type=CommandType.LOCAL,
        description="列出可用模型",
        aliases=["ml"],
        local_handler=_cmd_models,
        category="模型",
    ))

    registry.register(CommandDef(
        name="status",
        type=CommandType.LOCAL,
        description="查看系统状态",
        aliases=["st", "info"],
        local_handler=_cmd_status,
        category="系统",
    ))

    registry.register(CommandDef(
        name="doctor",
        type=CommandType.LOCAL,
        description="运行系统诊断",
        aliases=["diag", "检查"],
        local_handler=_cmd_doctor,
        category="系统",
    ))

    registry.register(CommandDef(
        name="config",
        type=CommandType.LOCAL,
        description="查看或修改配置",
        aliases=["cfg"],
        usage="/config [set KEY=VALUE]",
        local_handler=_cmd_config,
        category="系统",
    ))

    registry.register(CommandDef(
        name="cost",
        type=CommandType.LOCAL,
        description="查看使用统计",
        aliases=["usage", "统计"],
        local_handler=_cmd_cost,
        category="系统",
    ))

    registry.register(CommandDef(
        name="memory",
        type=CommandType.LOCAL,
        description="记忆管理",
        aliases=["mem"],
        usage="/memory [stats|clear]",
        local_handler=_cmd_memory,
        category="系统",
    ))

    registry.register(CommandDef(
        name="compact",
        type=CommandType.LOCAL,
        description="压缩对话历史",
        aliases=["压缩"],
        local_handler=_cmd_compact,
        category="对话",
    ))

    registry.register(CommandDef(
        name="review",
        type=CommandType.LOCAL,
        description="回顾对话历史",
        aliases=["回顾"],
        local_handler=_cmd_review,
        category="对话",
    ))

    registry.register(CommandDef(
        name="tasks",
        type=CommandType.LOCAL,
        description="任务管理",
        aliases=["task"],
        usage="/tasks [list]",
        local_handler=_cmd_tasks,
        category="任务",
    ))

    registry.register(CommandDef(
        name="diff",
        type=CommandType.LOCAL,
        description="查看文件变更",
        usage="/diff <文件路径>",
        local_handler=_cmd_diff,
        category="开发",
    ))

    registry.register(CommandDef(
        name="commit",
        type=CommandType.LOCAL,
        description="提交代码变更",
        usage="/commit <提交信息>",
        local_handler=_cmd_commit,
        category="开发",
    ))

    registry.register(CommandDef(
        name="tools",
        type=CommandType.LOCAL,
        description="工具管理",
        aliases=["tool"],
        usage="/tools [list]",
        local_handler=_cmd_tools,
        category="工具",
    ))

    registry.register(CommandDef(
        name="mcp",
        type=CommandType.LOCAL,
        description="MCP 服务器管理",
        usage="/mcp [list]",
        local_handler=_cmd_mcp,
        category="工具",
    ))

    registry.register(CommandDef(
        name="quit",
        type=CommandType.LOCAL,
        description="退出程序",
        aliases=["exit", "q", "退出"],
        local_handler=_cmd_quit,
        category="系统",
    ))

    registry.register(CommandDef(
        name="history",
        type=CommandType.LOCAL,
        description="查看命令执行历史",
        aliases=["hist"],
        local_handler=_cmd_history,
        category="帮助",
    ))

    registry.register(CommandDef(
        name="explain",
        type=CommandType.PROMPT,
        description="解释代码或概念",
        aliases=["解释"],
        usage="/explain [代码或概念]",
        prompt_template="请详细解释以下内容，使用中文回答：\n\n{args}",
        requires_llm=True,
        category="对话",
    ))

    registry.register(CommandDef(
        name="translate",
        type=CommandType.PROMPT,
        description="翻译文本",
        aliases=["翻译", "tr"],
        usage="/translate <文本>",
        prompt_template="请将以下文本翻译为中文（如果是中文则翻译为英文）：\n\n{args}",
        requires_llm=True,
        category="对话",
    ))

    registry.register(CommandDef(
        name="summarize",
        type=CommandType.PROMPT,
        description="总结文本",
        aliases=["总结", "摘要"],
        usage="/summarize <文本>",
        prompt_template="请用中文简洁总结以下内容：\n\n{args}",
        requires_llm=True,
        category="对话",
    ))

    registry.register(CommandDef(
        name="code",
        type=CommandType.PROMPT,
        description="生成代码",
        aliases=["代码"],
        usage="/code <需求描述>",
        prompt_template="请根据以下需求生成代码，使用中文注释：\n\n{args}",
        requires_llm=True,
        category="开发",
    ))

    registry.register(CommandDef(
        name="fix",
        type=CommandType.PROMPT,
        description="修复代码问题",
        aliases=["修复"],
        usage="/fix <代码或错误信息>",
        prompt_template="请分析并修复以下代码问题：\n\n{args}",
        requires_llm=True,
        category="开发",
    ))

    registry.register(CommandDef(
        name="refactor",
        type=CommandType.PROMPT,
        description="重构代码",
        aliases=["重构"],
        usage="/refactor <代码>",
        prompt_template="请重构以下代码，提升可读性和性能，使用中文注释：\n\n{args}",
        requires_llm=True,
        category="开发",
    ))

    registry.register(CommandDef(
        name="test",
        type=CommandType.PROMPT,
        description="生成测试代码",
        aliases=["测试"],
        usage="/test <代码>",
        prompt_template="请为以下代码生成完整的单元测试：\n\n{args}",
        requires_llm=True,
        category="开发",
    ))

    registry.register(CommandDef(
        name="doc",
        type=CommandType.PROMPT,
        description="生成文档",
        aliases=["文档"],
        usage="/doc <代码>",
        prompt_template="请为以下代码生成完整的中文文档：\n\n{args}",
        requires_llm=True,
        category="开发",
    ))

    logger.info(f"已注册 {len(registry._commands)} 个内置命令")
