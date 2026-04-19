"""
LSP（Language Server Protocol）客户端
借鉴 cc-haha-main 的 LSP 架构：
- 工厂函数 + 闭包模式（非类继承）
- 4 层生命周期：LSPClient → LSPServerInstance → LSPServerManager → Global Manager
- JSON-RPC over stdio
- 崩溃恢复（最多 3 次重启）
- ContentModified 错误自动重试

完全重写实现，适配本地大模型服务场景
"""

import os
import json
import time
import logging
import asyncio
from enum import IntEnum, Enum
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field

logger = logging.getLogger("LSPService")

MAX_RESTARTS = 3
REQUEST_TIMEOUT = 30
CONTENT_MODIFIED_RETRY_COUNT = 3


class ServerStatus(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    CRASHED = "crashed"
    RESTARTING = "restarting"


@dataclass
class LSPServerConfig:
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    file_extensions: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class Diagnostic:
    file_path: str
    line: int
    column: int
    severity: int
    message: str
    source: str = ""
    code: str = ""


@dataclass
class Location:
    file_path: str
    line: int
    column: int
    end_line: int = 0
    end_column: int = 0


@dataclass
class HoverResult:
    contents: str
    range_start: Optional[Location] = None


@dataclass
class SymbolInfo:
    name: str
    kind: int
    file_path: str
    line: int
    column: int
    container_name: str = ""


class LSPServerInstance:
    """LSP 服务器实例：管理单个语言服务器进程"""

    def __init__(self, config: LSPServerConfig):
        self.config = config
        self._process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._pending: Dict[int, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None
        self._status = ServerStatus.STOPPED
        self._restart_count = 0
        self._initialized = False
        self._root_uri = ""
        self._diagnostics: Dict[str, List[Diagnostic]] = {}
        self._last_error = ""

    @property
    def status(self) -> str:
        return self._status

    @property
    def is_running(self) -> bool:
        return self._status == ServerStatus.RUNNING and self._initialized

    async def start(self, root_path: str = "") -> bool:
        if self._status in (ServerStatus.RUNNING, ServerStatus.STARTING):
            return True

        self._status = ServerStatus.STARTING
        self._root_uri = self._path_to_uri(root_path) if root_path else ""

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

            init_result = await self._send_request("initialize", {
                "processId": os.getpid(),
                "rootUri": self._root_uri,
                "capabilities": {
                    "textDocument": {
                        "completion": {"completionItem": {"snippetSupport": False}},
                        "hover": {"contentFormat": ["plaintext", "markdown"]},
                        "definition": {"linkSupport": True},
                        "references": {},
                        "publishDiagnostics": {"relatedInformation": True},
                        "documentSymbol": {"hierarchicalDocumentSymbolSupport": True},
                    },
                },
            })

            if "error" in init_result:
                self._status = ServerStatus.CRASHED
                self._last_error = str(init_result["error"])
                return False

            await self._send_notification("initialized", {})
            self._initialized = True
            self._status = ServerStatus.RUNNING
            self._restart_count = 0
            logger.info(f"LSP 服务器启动成功: {self.config.name}")
            return True

        except Exception as e:
            self._status = ServerStatus.CRASHED
            self._last_error = str(e)
            logger.error(f"LSP 服务器启动失败 [{self.config.name}]: {e}")
            return False

    async def stop(self):
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None

        if self._process:
            try:
                await self._send_notification("shutdown", {})
                await self._send_notification("exit", {})
            except Exception:
                pass

            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass

            self._process = None

        self._status = ServerStatus.STOPPED
        self._initialized = False

    async def restart(self, root_path: str = "") -> bool:
        if self._restart_count >= MAX_RESTARTS:
            logger.error(f"LSP 服务器 [{self.config.name}] 已达最大重启次数 ({MAX_RESTARTS})")
            self._status = ServerStatus.CRASHED
            return False

        self._restart_count += 1
        self._status = ServerStatus.RESTARTING
        logger.info(f"LSP 服务器重启 [{self.config.name}] 第 {self._restart_count} 次")

        await self.stop()
        await asyncio.sleep(1)
        return await self.start(root_path)

    async def did_open(self, file_path: str, language_id: str, content: str):
        if not self.is_running:
            return
        uri = self._path_to_uri(file_path)
        await self._send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": uri,
                "languageId": language_id,
                "version": 1,
                "text": content,
            }
        })

    async def did_change(self, file_path: str, content: str, version: int = 1):
        if not self.is_running:
            return
        uri = self._path_to_uri(file_path)
        await self._send_notification("textDocument/didChange", {
            "textDocument": {"uri": uri, "version": version},
            "contentChanges": [{"text": content}]
        })

    async def did_close(self, file_path: str):
        if not self.is_running:
            return
        uri = self._path_to_uri(file_path)
        await self._send_notification("textDocument/didClose", {
            "textDocument": {"uri": uri}
        })

    async def get_diagnostics(self, file_path: str) -> List[Diagnostic]:
        return self._diagnostics.get(file_path, [])

    async def get_definition(self, file_path: str, line: int, column: int) -> List[Location]:
        if not self.is_running:
            return []
        result = await self._send_request_with_retry("textDocument/definition", {
            "textDocument": {"uri": self._path_to_uri(file_path)},
            "position": {"line": line, "character": column},
        })
        return self._parse_locations(result)

    async def get_references(self, file_path: str, line: int, column: int) -> List[Location]:
        if not self.is_running:
            return []
        result = await self._send_request("textDocument/references", {
            "textDocument": {"uri": self._path_to_uri(file_path)},
            "position": {"line": line, "character": column},
            "context": {"includeDeclaration": True},
        })
        return self._parse_locations(result)

    async def get_hover(self, file_path: str, line: int, column: int) -> Optional[HoverResult]:
        if not self.is_running:
            return None
        result = await self._send_request("textDocument/hover", {
            "textDocument": {"uri": self._path_to_uri(file_path)},
            "position": {"line": line, "character": column},
        })
        hover_data = result.get("result")
        if not hover_data:
            return None
        contents = hover_data.get("contents", "")
        if isinstance(contents, dict):
            contents = contents.get("value", str(contents))
        elif isinstance(contents, list):
            contents = "\n".join(
                c.get("value", str(c)) if isinstance(c, dict) else str(c)
                for c in contents
            )
        return HoverResult(contents=str(contents))

    async def get_document_symbols(self, file_path: str) -> List[SymbolInfo]:
        if not self.is_running:
            return []
        result = await self._send_request("textDocument/documentSymbol", {
            "textDocument": {"uri": self._path_to_uri(file_path)},
        })
        symbols_data = result.get("result", [])
        return self._parse_symbols(symbols_data, file_path)

    async def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._process or self._process.returncode is not None:
            return {"error": {"code": -1, "message": "服务器未运行"}}

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }

        future = asyncio.get_event_loop().create_future()
        self._pending[self._request_id] = future

        try:
            content = json.dumps(request)
            header = f"Content-Length: {len(content.encode('utf-8'))}\r\n\r\n"
            self._process.stdin.write((header + content).encode("utf-8"))
            await self._process.stdin.drain()

            return await asyncio.wait_for(future, timeout=REQUEST_TIMEOUT)
        except asyncio.TimeoutError:
            self._pending.pop(self._request_id, None)
            return {"error": {"code": -2, "message": "请求超时"}}
        except Exception as e:
            self._pending.pop(self._request_id, None)
            return {"error": {"code": -3, "message": str(e)}}

    async def _send_request_with_retry(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        for attempt in range(CONTENT_MODIFIED_RETRY_COUNT):
            result = await self._send_request(method, params)
            error = result.get("error", {})
            if isinstance(error, dict) and error.get("code") == -32801:
                logger.debug(f"ContentModified 错误，重试 {attempt + 1}/{CONTENT_MODIFIED_RETRY_COUNT}")
                await asyncio.sleep(0.1 * (attempt + 1))
                continue
            return result
        return result

    async def _send_notification(self, method: str, params: Dict[str, Any]):
        if not self._process or self._process.returncode is not None:
            return

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }

        try:
            content = json.dumps(notification)
            header = f"Content-Length: {len(content.encode('utf-8'))}\r\n\r\n"
            self._process.stdin.write((header + content).encode("utf-8"))
            await self._process.stdin.drain()
        except Exception as e:
            logger.error(f"LSP 通知发送失败 [{self.config.name}]: {e}")

    async def _read_loop(self):
        buffer = b""
        try:
            while self._process and self._process.returncode is None:
                data = await self._process.stdout.read(4096)
                if not data:
                    break
                buffer += data

                while b"\r\n\r\n" in buffer:
                    header_end = buffer.index(b"\r\n\r\n")
                    header = buffer[:header_end].decode("utf-8")
                    body_start = header_end + 4

                    content_length = 0
                    for line in header.split("\r\n"):
                        if line.lower().startswith("content-length:"):
                            content_length = int(line.split(":")[1].strip())
                            break

                    if content_length == 0:
                        buffer = buffer[body_start:]
                        continue

                    if len(buffer) < body_start + content_length:
                        break

                    body = buffer[body_start:body_start + content_length]
                    buffer = buffer[body_start + content_length:]

                    try:
                        msg = json.loads(body.decode("utf-8"))
                        self._handle_message(msg)
                    except json.JSONDecodeError:
                        pass

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"LSP 读取循环异常 [{self.config.name}]: {e}")
            if self._status == ServerStatus.RUNNING:
                self._status = ServerStatus.CRASHED

    def _handle_message(self, msg: Dict[str, Any]):
        if "id" in msg:
            msg_id = msg["id"]
            future = self._pending.pop(msg_id, None)
            if future and not future.done():
                future.set_result(msg)
        elif "method" in msg:
            method = msg.get("method", "")
            params = msg.get("params", {})

            if method == "textDocument/publishDiagnostics":
                uri = params.get("uri", "")
                file_path = self._uri_to_path(uri)
                diagnostics = []
                for d in params.get("diagnostics", []):
                    start = d.get("range", {}).get("start", {})
                    diagnostics.append(Diagnostic(
                        file_path=file_path,
                        line=start.get("line", 0),
                        column=start.get("character", 0),
                        severity=d.get("severity", 1),
                        message=d.get("message", ""),
                        source=d.get("source", ""),
                        code=str(d.get("code", "")),
                    ))
                self._diagnostics[file_path] = diagnostics

    def _parse_locations(self, result: Dict[str, Any]) -> List[Location]:
        locations = []
        loc_data = result.get("result")
        if not loc_data:
            return locations
        if isinstance(loc_data, dict):
            loc_data = [loc_data]
        for loc in loc_data:
            if isinstance(loc, dict):
                uri = loc.get("uri", "")
                range_data = loc.get("range", {})
                start = range_data.get("start", {})
                end = range_data.get("end", {})
                locations.append(Location(
                    file_path=self._uri_to_path(uri),
                    line=start.get("line", 0),
                    column=start.get("character", 0),
                    end_line=end.get("line", 0),
                    end_column=end.get("character", 0),
                ))
        return locations

    def _parse_symbols(self, symbols_data: Any, file_path: str) -> List[SymbolInfo]:
        symbols = []
        if not isinstance(symbols_data, list):
            return symbols
        for s in symbols_data:
            if isinstance(s, dict):
                loc = s.get("location", {})
                range_data = loc.get("range", {}).get("start", {})
                symbols.append(SymbolInfo(
                    name=s.get("name", ""),
                    kind=s.get("kind", 0),
                    file_path=file_path,
                    line=range_data.get("line", 0),
                    column=range_data.get("character", 0),
                    container_name=s.get("containerName", ""),
                ))
                children = s.get("children", [])
                if children:
                    symbols.extend(self._parse_symbols(children, file_path))
        return symbols

    @staticmethod
    def _path_to_uri(path: str) -> str:
        if not path:
            return ""
        abs_path = os.path.abspath(path)
        return f"file:///{abs_path.replace(os.sep, '/').lstrip('/')}"

    @staticmethod
    def _uri_to_path(uri: str) -> str:
        if uri.startswith("file:///"):
            return uri[8:].replace("/", os.sep)
        if uri.startswith("file://"):
            return uri[7:].replace("/", os.sep)
        return uri


class LSPManager:
    """LSP 全局管理器"""

    def __init__(self):
        self._servers: Dict[str, LSPServerInstance] = {}
        self._configs: Dict[str, LSPServerConfig] = {}
        self._extension_map: Dict[str, str] = {}
        self._language_map: Dict[str, str] = {}

    def register_server(self, config: LSPServerConfig):
        self._configs[config.name] = config
        for ext in config.file_extensions:
            self._extension_map[ext] = config.name
        for lang in config.languages:
            self._language_map[lang] = config.name
        logger.info(f"已注册 LSP 服务器配置: {config.name}")

    def _get_server_for_file(self, file_path: str) -> Optional[LSPServerInstance]:
        ext = os.path.splitext(file_path)[1].lower()
        server_name = self._extension_map.get(ext)
        if server_name and server_name in self._servers:
            instance = self._servers[server_name]
            if instance.is_running:
                return instance
        return None

    async def start_server(self, name: str, root_path: str = "") -> bool:
        config = self._configs.get(name)
        if not config:
            logger.error(f"LSP 服务器 '{name}' 未配置")
            return False

        if name in self._servers:
            instance = self._servers[name]
            if instance.is_running:
                return True
            await instance.stop()

        instance = LSPServerInstance(config)
        self._servers[name] = instance
        return await instance.start(root_path)

    async def stop_server(self, name: str):
        instance = self._servers.get(name)
        if instance:
            await instance.stop()

    async def start_for_file(self, file_path: str, root_path: str = "") -> Optional[LSPServerInstance]:
        ext = os.path.splitext(file_path)[1].lower()
        server_name = self._extension_map.get(ext)
        if not server_name:
            return None

        config = self._configs.get(server_name)
        if not config or not config.enabled:
            return None

        instance = self._servers.get(server_name)
        if instance and instance.is_running:
            return instance

        if server_name not in self._servers:
            instance = LSPServerInstance(config)
            self._servers[server_name] = instance

        success = await self._servers[server_name].start(root_path)
        if success:
            return self._servers[server_name]
        return None

    async def get_diagnostics(self, file_path: str) -> List[Diagnostic]:
        instance = self._get_server_for_file(file_path)
        if instance:
            return await instance.get_diagnostics(file_path)
        return []

    async def get_definition(self, file_path: str, line: int, column: int) -> List[Location]:
        instance = self._get_server_for_file(file_path)
        if instance:
            return await instance.get_definition(file_path, line, column)
        return []

    async def get_references(self, file_path: str, line: int, column: int) -> List[Location]:
        instance = self._get_server_for_file(file_path)
        if instance:
            return await instance.get_references(file_path, line, column)
        return []

    async def get_hover(self, file_path: str, line: int, column: int) -> Optional[HoverResult]:
        instance = self._get_server_for_file(file_path)
        if instance:
            return await instance.get_hover(file_path, line, column)
        return None

    async def get_document_symbols(self, file_path: str) -> List[SymbolInfo]:
        instance = self._get_server_for_file(file_path)
        if instance:
            return await instance.get_document_symbols(file_path)
        return []

    def list_servers(self) -> List[Dict[str, Any]]:
        result = []
        for name, config in self._configs.items():
            instance = self._servers.get(name)
            result.append({
                "name": name,
                "command": config.command,
                "extensions": config.file_extensions,
                "languages": config.languages,
                "status": instance.status if instance else ServerStatus.STOPPED,
                "enabled": config.enabled,
            })
        return result

    async def stop_all(self):
        for name in list(self._servers.keys()):
            await self.stop_server(name)

    def load_config(self, config_path: str) -> int:
        if not os.path.exists(config_path):
            return 0

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"加载 LSP 配置失败: {e}")
            return 0

        servers = data.get("lspServers", data.get("servers", {}))
        count = 0
        for name, server_config in servers.items():
            config = LSPServerConfig(
                name=name,
                command=server_config.get("command", ""),
                args=server_config.get("args", []),
                env=server_config.get("env", {}),
                file_extensions=server_config.get("extensions", []),
                languages=server_config.get("languages", []),
                enabled=server_config.get("enabled", True),
            )
            self.register_server(config)
            count += 1

        logger.info(f"从配置文件加载 {count} 个 LSP 服务器配置")
        return count


_lsp_manager: Optional[LSPManager] = None


def get_lsp_manager() -> LSPManager:
    global _lsp_manager
    if _lsp_manager is None:
        _lsp_manager = LSPManager()
        config_path = os.environ.get(
            "GEMMA4_LSP_CONFIG",
            os.path.join(os.path.dirname(__file__), "..", "..", "lsp_config.json")
        )
        if os.path.exists(config_path):
            _lsp_manager.load_config(config_path)
    return _lsp_manager
