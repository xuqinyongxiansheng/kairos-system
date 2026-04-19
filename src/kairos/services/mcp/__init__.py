"""
MCP（Model Context Protocol）协议客户端
借鉴 cc-haha-main 的 MCP 架构：
- stdio/SSE/HTTP 传输支持
- memoize 连接缓存
- tools/list 工具发现
- mcp__{server}__{tool} 命名空间
- 自动重连

完全重写实现，适配本地大模型服务场景
"""

import os
import json
import time
import logging
import asyncio
import subprocess
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger("MCPService")


class TransportType(str, Enum):
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"


@dataclass
class McpServerConfig:
    name: str
    transport: TransportType = TransportType.STDIO
    command: str = ""
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    url: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    auto_reconnect: bool = True
    max_reconnect_attempts: int = 3
    reconnect_delay_seconds: float = 2.0


@dataclass
class McpTool:
    name: str
    full_name: str
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    server_name: str = ""


@dataclass
class McpServerState:
    config: McpServerConfig
    connected: bool = False
    process: Optional[Any] = None
    tools: List[McpTool] = field(default_factory=list)
    last_connected: float = 0.0
    reconnect_attempts: int = 0
    error: str = ""


class StdioTransport:
    """stdio 传输层：通过子进程与 MCP 服务器通信"""

    def __init__(self, config: McpServerConfig):
        self.config = config
        self._process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._pending: Dict[int, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None

    async def connect(self) -> bool:
        try:
            env = {**os.environ, **self.config.env}
            self._process = await asyncio.create_subprocess_exec(
                self.config.command,
                *self.config.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            self._reader_task = asyncio.create_task(self._read_loop())
            logger.info(f"MCP stdio 连接成功: {self.config.name}")
            return True
        except Exception as e:
            logger.error(f"MCP stdio 连接失败 [{self.config.name}]: {e}")
            self._process = None
            return False

    async def disconnect(self):
        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None

    async def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        if not self._process or self._process.returncode is not None:
            return {"error": {"code": -1, "message": "未连接"}}

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }

        future = asyncio.get_event_loop().create_future()
        self._pending[self._request_id] = future

        try:
            msg = json.dumps(request) + "\n"
            self._process.stdin.write(msg.encode("utf-8"))
            await self._process.stdin.drain()

            return await asyncio.wait_for(future, timeout=30)
        except asyncio.TimeoutError:
            self._pending.pop(self._request_id, None)
            return {"error": {"code": -2, "message": "请求超时"}}
        except Exception as e:
            self._pending.pop(self._request_id, None)
            return {"error": {"code": -3, "message": str(e)}}

    async def _read_loop(self):
        try:
            while self._process and self._process.returncode is None:
                line = await self._process.stdout.readline()
                if not line:
                    break
                try:
                    msg = json.loads(line.decode("utf-8").strip())
                    msg_id = msg.get("id")
                    if msg_id and msg_id in self._pending:
                        future = self._pending.pop(msg_id)
                        if not future.done():
                            future.set_result(msg)
                except json.JSONDecodeError:
                    pass
                except Exception:
                    pass
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"MCP 读取循环异常 [{self.config.name}]: {e}")


class HttpTransport:
    """HTTP 传输层：通过 HTTP 与 MCP 服务器通信"""

    def __init__(self, config: McpServerConfig):
        self.config = config
        self._base_url = config.url

    async def connect(self) -> bool:
        try:
            import urllib.request
            url = f"{self._base_url}/health"
            req = urllib.request.Request(url, method="GET")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=5)
            )
            logger.info(f"MCP HTTP 连接成功: {self.config.name}")
            return True
        except Exception:
            logger.info(f"MCP HTTP 服务器 {self.config.name} 连接测试跳过（可能无 /health 端点）")
            return True

    async def disconnect(self):
        pass

    async def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            import urllib.request
            url = f"{self._base_url}/mcp"
            payload = json.dumps({
                "jsonrpc": "2.0",
                "id": int(time.time() * 1000),
                "method": method,
                "params": params or {},
            }).encode("utf-8")

            req = urllib.request.Request(url, data=payload, method="POST")
            req.add_header("Content-Type", "application/json")
            for k, v in self.config.headers.items():
                req.add_header(k, v)

            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=30)
            )
            result = json.loads(resp.read().decode("utf-8"))
            return result
        except Exception as e:
            return {"error": {"code": -1, "message": str(e)}}


class McpManager:
    """MCP 服务器管理器"""

    def __init__(self):
        self._servers: Dict[str, McpServerState] = {}
        self._transports: Dict[str, Any] = {}
        self._tool_cache: Dict[str, McpTool] = {}
        self._tool_cache_time: float = 0
        self._tool_cache_ttl: int = 300

    def add_server(self, config: McpServerConfig) -> bool:
        if config.name in self._servers:
            logger.warning(f"MCP 服务器 '{config.name}' 已存在")
            return False

        self._servers[config.name] = McpServerState(config=config)
        logger.info(f"已添加 MCP 服务器配置: {config.name} ({config.transport.value})")
        return True

    def remove_server(self, name: str) -> bool:
        state = self._servers.pop(name, None)
        if state:
            transport = self._transports.pop(name, None)
            if transport:
                asyncio.create_task(transport.disconnect())
            for tool_name in list(self._tool_cache.keys()):
                if tool_name.startswith(f"mcp__{name}__"):
                    del self._tool_cache[tool_name]
            return True
        return False

    async def connect_server(self, name: str) -> bool:
        state = self._servers.get(name)
        if not state:
            logger.error(f"MCP 服务器 '{name}' 未配置")
            return False

        if not state.config.enabled:
            logger.warning(f"MCP 服务器 '{name}' 已禁用")
            return False

        config = state.config
        if config.transport == TransportType.STDIO:
            transport = StdioTransport(config)
        elif config.transport in (TransportType.SSE, TransportType.HTTP):
            transport = HttpTransport(config)
        else:
            logger.error(f"不支持的传输类型: {config.transport}")
            return False

        connected = await transport.connect()
        if connected:
            self._transports[name] = transport
            state.connected = True
            state.last_connected = time.time()
            state.reconnect_attempts = 0
            state.error = ""

            await self._discover_tools(name)
            return True
        else:
            state.connected = False
            state.error = "连接失败"
            return False

    async def disconnect_server(self, name: str):
        state = self._servers.get(name)
        transport = self._transports.pop(name, None)
        if transport:
            await transport.disconnect()
        if state:
            state.connected = False
            state.tools = []

    async def connect_all(self) -> Dict[str, bool]:
        results = {}
        for name, state in self._servers.items():
            if state.config.enabled:
                results[name] = await self.connect_server(name)
        return results

    async def disconnect_all(self):
        for name in list(self._transports.keys()):
            await self.disconnect_server(name)

    async def _discover_tools(self, server_name: str):
        transport = self._transports.get(server_name)
        if not transport:
            return

        try:
            result = await transport.send_request("tools/list", {})
            if "error" in result:
                logger.warning(f"MCP 工具发现失败 [{server_name}]: {result.get('error')}")
                return

            tools_data = result.get("result", {}).get("tools", [])
            state = self._servers.get(server_name)
            if not state:
                return

            state.tools = []
            for tool_data in tools_data:
                tool_name = tool_data.get("name", "")
                full_name = f"mcp__{server_name}__{tool_name}"
                tool = McpTool(
                    name=tool_name,
                    full_name=full_name,
                    description=tool_data.get("description", ""),
                    parameters=tool_data.get("inputSchema", {}),
                    server_name=server_name,
                )
                state.tools.append(tool)
                self._tool_cache[full_name] = tool

            self._tool_cache_time = time.time()
            logger.info(f"MCP [{server_name}] 发现 {len(state.tools)} 个工具")
        except Exception as e:
            logger.error(f"MCP 工具发现异常 [{server_name}]: {e}")

    async def call_tool(self, full_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        if full_name not in self._tool_cache:
            return {"error": {"code": -1, "message": f"未知工具: {full_name}"}}

        tool = self._tool_cache[full_name]
        transport = self._transports.get(tool.server_name)
        if not transport:
            return {"error": {"code": -2, "message": f"服务器未连接: {tool.server_name}"}}

        try:
            result = await transport.send_request("tools/call", {
                "name": tool.name,
                "arguments": arguments or {},
            })

            if "error" in result:
                return result

            return result.get("result", {})
        except Exception as e:
            return {"error": {"code": -3, "message": str(e)}}

    def list_servers(self) -> List[Dict[str, Any]]:
        result = []
        for name, state in self._servers.items():
            result.append({
                "name": name,
                "transport": state.config.transport.value,
                "connected": state.connected,
                "enabled": state.config.enabled,
                "tools_count": len(state.tools),
                "last_connected": state.last_connected,
                "error": state.error,
            })
        return result

    def list_tools(self, server_name: str = None) -> List[Dict[str, Any]]:
        if server_name:
            state = self._servers.get(server_name)
            if not state:
                return []
            return [
                {"name": t.full_name, "description": t.description, "server": t.server_name}
                for t in state.tools
            ]

        all_tools = []
        for name, state in self._servers.items():
            for t in state.tools:
                all_tools.append({
                    "name": t.full_name,
                    "description": t.description,
                    "server": t.server_name,
                })
        return all_tools

    def get_tool(self, full_name: str) -> Optional[McpTool]:
        return self._tool_cache.get(full_name)

    async def auto_reconnect(self):
        for name, state in self._servers.items():
            if not state.config.auto_reconnect or state.connected or not state.config.enabled:
                continue
            if state.reconnect_attempts >= state.config.max_reconnect_attempts:
                continue
            state.reconnect_attempts += 1
            logger.info(f"MCP 自动重连 [{name}] 第 {state.reconnect_attempts} 次")
            await asyncio.sleep(state.config.reconnect_delay_seconds)
            success = await self.connect_server(name)
            if success:
                logger.info(f"MCP 自动重连成功 [{name}]")

    def load_config(self, config_path: str) -> int:
        """从配置文件加载 MCP 服务器配置"""
        if not os.path.exists(config_path):
            return 0

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"加载 MCP 配置失败: {e}")
            return 0

        servers = data.get("mcpServers", data.get("servers", {}))
        count = 0
        for name, server_config in servers.items():
            transport_str = server_config.get("transport", "stdio")
            try:
                transport = TransportType(transport_str)
            except ValueError:
                transport = TransportType.STDIO

            config = McpServerConfig(
                name=name,
                transport=transport,
                command=server_config.get("command", ""),
                args=server_config.get("args", []),
                env=server_config.get("env", {}),
                url=server_config.get("url", ""),
                headers=server_config.get("headers", {}),
                enabled=server_config.get("enabled", True),
                auto_reconnect=server_config.get("autoReconnect", True),
                max_reconnect_attempts=server_config.get("maxReconnectAttempts", 3),
            )

            if self.add_server(config):
                count += 1

        logger.info(f"从配置文件加载 {count} 个 MCP 服务器")
        return count


_mcp_manager: Optional[McpManager] = None


def get_mcp_manager() -> McpManager:
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = McpManager()
        config_path = os.environ.get(
            "GEMMA4_MCP_CONFIG",
            os.path.join(os.path.dirname(__file__), "..", "..", "mcp_config.json")
        )
        if os.path.exists(config_path):
            _mcp_manager.load_config(config_path)
    return _mcp_manager
