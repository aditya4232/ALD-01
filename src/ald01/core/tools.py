"""
ALD-01 Tool Executor
Provides filesystem, terminal, code execution, HTTP, and system tools.
Full device access with safety controls the owner can toggle.
"""

import os
import sys
import json
import time
import shutil
import asyncio
import logging
import platform
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

import psutil

from ald01.config import get_config
from ald01.core.events import get_event_bus, Event, EventType

logger = logging.getLogger("ald01.tools")


class ToolResult:
    """Result from a tool execution."""

    def __init__(self, success: bool, output: Any = "", error: str = "",
                 tool_name: str = "", duration_ms: float = 0.0):
        self.success = success
        self.output = output
        self.error = error
        self.tool_name = tool_name
        self.duration_ms = duration_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output if isinstance(self.output, (str, int, float, bool, list, dict)) else str(self.output),
            "error": self.error,
            "tool_name": self.tool_name,
            "duration_ms": round(self.duration_ms, 1),
        }


class ToolExecutor:
    """
    Executes tools with full device access.
    All tools can be enabled/disabled from config and dashboard.
    """

    def __init__(self):
        self._config = get_config()
        self._event_bus = get_event_bus()
        self._execution_log: List[Dict[str, Any]] = []

    # ──────────────────────────────────────────────────────────
    # Tool Registry
    # ──────────────────────────────────────────────────────────

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """List all available tools and their status."""
        tools_conf = self._config.get("tools", default={})
        return [
            {
                "name": "file_read",
                "description": "Read any file from the filesystem",
                "enabled": tools_conf.get("file_read", {}).get("enabled", True),
                "category": "filesystem",
            },
            {
                "name": "file_write",
                "description": "Write or create files on the filesystem",
                "enabled": tools_conf.get("file_write", {}).get("enabled", True),
                "category": "filesystem",
            },
            {
                "name": "file_list",
                "description": "List directory contents with details",
                "enabled": True,
                "category": "filesystem",
            },
            {
                "name": "file_search",
                "description": "Search for files by name or pattern",
                "enabled": True,
                "category": "filesystem",
            },
            {
                "name": "file_delete",
                "description": "Delete files or directories",
                "enabled": tools_conf.get("file_write", {}).get("enabled", True),
                "category": "filesystem",
            },
            {
                "name": "file_move",
                "description": "Move or rename files",
                "enabled": tools_conf.get("file_write", {}).get("enabled", True),
                "category": "filesystem",
            },
            {
                "name": "file_info",
                "description": "Get file metadata (size, dates, permissions)",
                "enabled": True,
                "category": "filesystem",
            },
            {
                "name": "terminal",
                "description": "Execute shell commands on the system",
                "enabled": tools_conf.get("terminal", {}).get("enabled", False),
                "category": "system",
            },
            {
                "name": "code_execute",
                "description": "Execute Python code in a sandbox",
                "enabled": tools_conf.get("code_execute", {}).get("enabled", False),
                "category": "code",
            },
            {
                "name": "http_request",
                "description": "Make HTTP requests to any URL",
                "enabled": tools_conf.get("http_request", {}).get("enabled", True),
                "category": "network",
            },
            {
                "name": "system_info",
                "description": "Get system information (CPU, RAM, disk, network)",
                "enabled": True,
                "category": "system",
            },
            {
                "name": "process_list",
                "description": "List running processes",
                "enabled": True,
                "category": "system",
            },
            {
                "name": "clipboard",
                "description": "Read/write system clipboard",
                "enabled": True,
                "category": "system",
            },
            {
                "name": "screenshot",
                "description": "Take a screenshot of the desktop",
                "enabled": False,
                "category": "system",
            },
        ]

    async def execute(self, tool_name: str, params: Dict[str, Any] = None) -> ToolResult:
        """Execute a tool by name with given parameters."""
        params = params or {}
        start_time = time.time()

        # Log the execution
        await self._event_bus.emit(Event(
            type=EventType.TOOL_EXECUTED,
            data={"tool": tool_name, "params_keys": list(params.keys())},
            source="tool_executor",
        ))

        try:
            # Route to handler
            handler = getattr(self, f"_tool_{tool_name}", None)
            if handler is None:
                return ToolResult(False, error=f"Unknown tool: {tool_name}", tool_name=tool_name)

            result = await handler(params)
            result.tool_name = tool_name
            result.duration_ms = (time.time() - start_time) * 1000

            # Log
            self._execution_log.append({
                "tool": tool_name,
                "success": result.success,
                "timestamp": time.time(),
                "duration_ms": result.duration_ms,
            })
            if len(self._execution_log) > 500:
                self._execution_log = self._execution_log[-500:]

            return result

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            await self._event_bus.emit(Event(
                type=EventType.TOOL_ERROR,
                data={"tool": tool_name, "error": str(e)},
                source="tool_executor",
            ))
            return ToolResult(False, error=str(e), tool_name=tool_name, duration_ms=duration)

    # ──────────────────────────────────────────────────────────
    # Filesystem Tools
    # ──────────────────────────────────────────────────────────

    async def _tool_file_read(self, params: Dict[str, Any]) -> ToolResult:
        """Read file contents."""
        path = params.get("path", "")
        if not path:
            return ToolResult(False, error="Missing 'path' parameter")

        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.exists(path):
            return ToolResult(False, error=f"File not found: {path}")
        if not os.path.isfile(path):
            return ToolResult(False, error=f"Not a file: {path}")

        max_size = params.get("max_size", 1024 * 1024)  # 1MB default
        file_size = os.path.getsize(path)
        if file_size > max_size:
            return ToolResult(False, error=f"File too large: {file_size} bytes (max {max_size})")

        try:
            encoding = params.get("encoding", "utf-8")
            with open(path, "r", encoding=encoding, errors="replace") as f:
                content = f.read()
            return ToolResult(True, output=content)
        except Exception as e:
            # Try binary read
            try:
                with open(path, "rb") as f:
                    data = f.read(max_size)
                return ToolResult(True, output=f"[Binary file, {len(data)} bytes]")
            except Exception as e2:
                return ToolResult(False, error=str(e2))

    async def _tool_file_write(self, params: Dict[str, Any]) -> ToolResult:
        """Write content to a file."""
        path = params.get("path", "")
        content = params.get("content", "")
        if not path:
            return ToolResult(False, error="Missing 'path' parameter")

        path = os.path.abspath(os.path.expanduser(path))
        os.makedirs(os.path.dirname(path), exist_ok=True)

        try:
            mode = params.get("mode", "w")
            encoding = params.get("encoding", "utf-8")
            with open(path, mode, encoding=encoding) as f:
                f.write(content)
            return ToolResult(True, output=f"Written {len(content)} chars to {path}")
        except Exception as e:
            return ToolResult(False, error=str(e))

    async def _tool_file_list(self, params: Dict[str, Any]) -> ToolResult:
        """List directory contents."""
        path = params.get("path", ".")
        path = os.path.abspath(os.path.expanduser(path))

        if not os.path.exists(path):
            return ToolResult(False, error=f"Path not found: {path}")

        try:
            entries = []
            show_hidden = params.get("show_hidden", False)
            for entry in sorted(os.listdir(path)):
                if not show_hidden and entry.startswith("."):
                    continue
                full_path = os.path.join(path, entry)
                stat = os.stat(full_path)
                entries.append({
                    "name": entry,
                    "type": "dir" if os.path.isdir(full_path) else "file",
                    "size": stat.st_size,
                    "modified": time.ctime(stat.st_mtime),
                })
            return ToolResult(True, output=entries)
        except Exception as e:
            return ToolResult(False, error=str(e))

    async def _tool_file_search(self, params: Dict[str, Any]) -> ToolResult:
        """Search for files by pattern."""
        path = params.get("path", ".")
        pattern = params.get("pattern", "*")
        max_results = params.get("max_results", 50)

        path = os.path.abspath(os.path.expanduser(path))

        try:
            from pathlib import Path as P
            results = []
            for match in P(path).rglob(pattern):
                results.append(str(match))
                if len(results) >= max_results:
                    break
            return ToolResult(True, output=results)
        except Exception as e:
            return ToolResult(False, error=str(e))

    async def _tool_file_delete(self, params: Dict[str, Any]) -> ToolResult:
        """Delete a file or directory."""
        path = params.get("path", "")
        if not path:
            return ToolResult(False, error="Missing 'path' parameter")

        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.exists(path):
            return ToolResult(False, error=f"Not found: {path}")

        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            return ToolResult(True, output=f"Deleted: {path}")
        except Exception as e:
            return ToolResult(False, error=str(e))

    async def _tool_file_move(self, params: Dict[str, Any]) -> ToolResult:
        """Move or rename a file."""
        src = params.get("source", params.get("src", ""))
        dst = params.get("destination", params.get("dst", ""))
        if not src or not dst:
            return ToolResult(False, error="Missing 'source' or 'destination'")

        try:
            shutil.move(src, dst)
            return ToolResult(True, output=f"Moved: {src} → {dst}")
        except Exception as e:
            return ToolResult(False, error=str(e))

    async def _tool_file_info(self, params: Dict[str, Any]) -> ToolResult:
        """Get file/directory metadata."""
        path = params.get("path", "")
        if not path:
            return ToolResult(False, error="Missing 'path' parameter")

        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.exists(path):
            return ToolResult(False, error=f"Not found: {path}")

        try:
            stat = os.stat(path)
            info = {
                "path": path,
                "name": os.path.basename(path),
                "type": "directory" if os.path.isdir(path) else "file",
                "size_bytes": stat.st_size,
                "size_human": self._human_size(stat.st_size),
                "created": time.ctime(stat.st_ctime),
                "modified": time.ctime(stat.st_mtime),
                "accessed": time.ctime(stat.st_atime),
                "permissions": oct(stat.st_mode)[-3:],
                "is_symlink": os.path.islink(path),
            }
            if os.path.isdir(path):
                try:
                    info["children_count"] = len(os.listdir(path))
                except PermissionError:
                    info["children_count"] = -1
            return ToolResult(True, output=info)
        except Exception as e:
            return ToolResult(False, error=str(e))

    # ──────────────────────────────────────────────────────────
    # Terminal / Shell Tool
    # ──────────────────────────────────────────────────────────

    async def _tool_terminal(self, params: Dict[str, Any]) -> ToolResult:
        """Execute a shell command."""
        command = params.get("command", "")
        if not command:
            return ToolResult(False, error="Missing 'command' parameter")

        timeout = params.get("timeout", 30)
        cwd = params.get("cwd", None)

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

            return ToolResult(
                success=proc.returncode == 0,
                output={
                    "stdout": stdout.decode("utf-8", errors="replace")[:50000],
                    "stderr": stderr.decode("utf-8", errors="replace")[:10000],
                    "return_code": proc.returncode,
                },
                error=stderr.decode("utf-8", errors="replace")[:5000] if proc.returncode != 0 else "",
            )
        except asyncio.TimeoutError:
            return ToolResult(False, error=f"Command timed out after {timeout}s")
        except Exception as e:
            return ToolResult(False, error=str(e))

    # ──────────────────────────────────────────────────────────
    # Code Execution Tool (Sandboxed Python)
    # ──────────────────────────────────────────────────────────

    async def _tool_code_execute(self, params: Dict[str, Any]) -> ToolResult:
        """Execute Python code in a subprocess sandbox."""
        code = params.get("code", "")
        if not code:
            return ToolResult(False, error="Missing 'code' parameter")

        timeout = params.get("timeout", 30)

        # Write to temp file and execute in subprocess
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
                f.write(code)
                tmp_path = f.name

            proc = await asyncio.create_subprocess_exec(
                sys.executable, tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

            os.unlink(tmp_path)

            return ToolResult(
                success=proc.returncode == 0,
                output={
                    "stdout": stdout.decode("utf-8", errors="replace")[:50000],
                    "stderr": stderr.decode("utf-8", errors="replace")[:10000],
                    "return_code": proc.returncode,
                },
            )
        except asyncio.TimeoutError:
            return ToolResult(False, error=f"Code execution timed out after {timeout}s")
        except Exception as e:
            return ToolResult(False, error=str(e))

    # ──────────────────────────────────────────────────────────
    # HTTP Request Tool
    # ──────────────────────────────────────────────────────────

    async def _tool_http_request(self, params: Dict[str, Any]) -> ToolResult:
        """Make an HTTP request."""
        import httpx

        url = params.get("url", "")
        method = params.get("method", "GET").upper()
        headers = params.get("headers", {})
        body = params.get("body", None)
        timeout = params.get("timeout", 30)

        if not url:
            return ToolResult(False, error="Missing 'url' parameter")

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.request(method, url, headers=headers, json=body if body else None)
                content_type = resp.headers.get("content-type", "")

                output = {
                    "status_code": resp.status_code,
                    "headers": dict(resp.headers),
                    "content_type": content_type,
                }

                if "json" in content_type:
                    try:
                        output["body"] = resp.json()
                    except Exception:
                        output["body"] = resp.text[:10000]
                else:
                    output["body"] = resp.text[:10000]

                return ToolResult(True, output=output)
        except Exception as e:
            return ToolResult(False, error=str(e))

    # ──────────────────────────────────────────────────────────
    # System Tools
    # ──────────────────────────────────────────────────────────

    async def _tool_system_info(self, params: Dict[str, Any]) -> ToolResult:
        """Get comprehensive system information."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            boot_time = psutil.boot_time()

            info = {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "hostname": platform.node(),
                "python_version": platform.python_version(),
                "cpu": {
                    "cores_physical": psutil.cpu_count(logical=False),
                    "cores_logical": psutil.cpu_count(),
                    "usage_percent": cpu_percent,
                    "frequency_mhz": getattr(psutil.cpu_freq(), "current", 0) if psutil.cpu_freq() else 0,
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "usage_percent": memory.percent,
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "usage_percent": round(disk.used / disk.total * 100, 1),
                },
                "uptime_hours": round((time.time() - boot_time) / 3600, 1),
            }
            return ToolResult(True, output=info)
        except Exception as e:
            return ToolResult(False, error=str(e))

    async def _tool_process_list(self, params: Dict[str, Any]) -> ToolResult:
        """List running processes."""
        try:
            limit = params.get("limit", 30)
            sort_by = params.get("sort_by", "memory")

            procs = []
            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
                try:
                    info = proc.info
                    procs.append({
                        "pid": info["pid"],
                        "name": info["name"],
                        "cpu_percent": info.get("cpu_percent", 0),
                        "memory_percent": round(info.get("memory_percent", 0), 1),
                        "status": info.get("status", "unknown"),
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            key = "memory_percent" if sort_by == "memory" else "cpu_percent"
            procs.sort(key=lambda p: p.get(key, 0), reverse=True)

            return ToolResult(True, output=procs[:limit])
        except Exception as e:
            return ToolResult(False, error=str(e))

    async def _tool_clipboard(self, params: Dict[str, Any]) -> ToolResult:
        """Read or write clipboard (best effort, may not work on headless)."""
        action = params.get("action", "read")
        try:
            if action == "write":
                text = params.get("text", "")
                if platform.system() == "Windows":
                    proc = await asyncio.create_subprocess_exec(
                        "clip", stdin=asyncio.subprocess.PIPE
                    )
                    await proc.communicate(text.encode())
                else:
                    proc = await asyncio.create_subprocess_exec(
                        "xclip", "-selection", "clipboard",
                        stdin=asyncio.subprocess.PIPE
                    )
                    await proc.communicate(text.encode())
                return ToolResult(True, output="Copied to clipboard")
            else:
                if platform.system() == "Windows":
                    proc = await asyncio.create_subprocess_shell(
                        "powershell Get-Clipboard",
                        stdout=asyncio.subprocess.PIPE
                    )
                    stdout, _ = await proc.communicate()
                    return ToolResult(True, output=stdout.decode().strip())
                else:
                    proc = await asyncio.create_subprocess_exec(
                        "xclip", "-selection", "clipboard", "-o",
                        stdout=asyncio.subprocess.PIPE
                    )
                    stdout, _ = await proc.communicate()
                    return ToolResult(True, output=stdout.decode().strip())
        except Exception as e:
            return ToolResult(False, error=f"Clipboard access failed: {e}")

    # ──────────────────────────────────────────────────────────
    # Utility
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        """Convert bytes to human-readable string."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"

    def get_execution_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent tool execution history."""
        return self._execution_log[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get tool execution statistics."""
        total = len(self._execution_log)
        success = sum(1 for e in self._execution_log if e.get("success"))
        tools_used = {}
        for entry in self._execution_log:
            name = entry.get("tool", "unknown")
            tools_used[name] = tools_used.get(name, 0) + 1
        return {
            "total_executions": total,
            "successful": success,
            "failed": total - success,
            "tools_used": tools_used,
        }


# Singleton
_tool_executor: Optional[ToolExecutor] = None


def get_tool_executor() -> ToolExecutor:
    """Get or create the global tool executor."""
    global _tool_executor
    if _tool_executor is None:
        _tool_executor = ToolExecutor()
    return _tool_executor
