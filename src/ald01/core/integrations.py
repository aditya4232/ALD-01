"""
ALD-01 External Tool Integration
Integrates with other AI tools on the device:
OpenCode, Antigravity, KiloCLI, Cline CLI, Blender, etc.
"""

import os
import shutil
import subprocess
import asyncio
import logging
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ald01.integrations")


@dataclass
class ExternalTool:
    """An external AI tool on the device."""
    name: str
    display_name: str
    icon: str
    description: str
    command: str  # CLI command to invoke
    detected: bool = False
    path: str = ""
    version: str = ""
    category: str = "ai"  # 'ai', 'dev', 'creative', 'system'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "icon": self.icon,
            "description": self.description,
            "command": self.command,
            "detected": self.detected,
            "path": self.path,
            "version": self.version,
            "category": self.category,
        }




# Known external tools
KNOWN_TOOLS: Dict[str, Dict[str, str]] = {
    "opencode": {
        "display_name": "OpenCode",
        "icon": "wand-2",
        "description": "AI-powered code editor and assistant",
        "command": "opencode",
        "category": "ai",
    },
    "antigravity": {
        "display_name": "Antigravity",
        "icon": "rocket",
        "description": "Advanced AI coding assistant by Google DeepMind",
        "command": "antigravity",
        "category": "ai",
    },
    "kilocli": {
        "display_name": "KiloCLI",
        "icon": "zap",
        "description": "Fast AI CLI assistant",
        "command": "kilo",
        "category": "ai",
    },
    "cline": {
        "display_name": "Cline CLI",
        "icon": "bot",
        "description": "Autonomous AI coding agent in terminal",
        "command": "cline",
        "category": "ai",
    },
    "blender": {
        "display_name": "Blender",
        "icon": "palette",
        "description": "3D creation suite with Python scripting",
        "command": "blender",
        "category": "creative",
    },
    "ollama": {
        "display_name": "Ollama",
        "icon": "cpu",
        "description": "Local LLM runner",
        "command": "ollama",
        "category": "ai",
    },
    "docker": {
        "display_name": "Docker",
        "icon": "container",
        "description": "Container runtime",
        "command": "docker",
        "category": "dev",
    },
    "git": {
        "display_name": "Git",
        "icon": "git-branch",
        "description": "Version control system",
        "command": "git",
        "category": "dev",
    },
    "node": {
        "display_name": "Node.js",
        "icon": "hexagon",
        "description": "JavaScript runtime",
        "command": "node",
        "category": "dev",
    },
    "python": {
        "display_name": "Python",
        "icon": "code",
        "description": "Python interpreter",
        "command": "python",
        "category": "dev",
    },
    "code": {
        "display_name": "VS Code",
        "icon": "monitor",
        "description": "Visual Studio Code editor",
        "command": "code",
        "category": "dev",
    },
    "cursor": {
        "display_name": "Cursor",
        "icon": "mouse-pointer",
        "description": "AI-first code editor",
        "command": "cursor",
        "category": "ai",
    },
    "windsurf": {
        "display_name": "Windsurf",
        "icon": "wind",
        "description": "AI-powered code editor",
        "command": "windsurf",
        "category": "ai",
    },
    "ffmpeg": {
        "display_name": "FFmpeg",
        "icon": "film",
        "description": "Multimedia processing",
        "command": "ffmpeg",
        "category": "creative",
    },
    "npm": {
        "display_name": "npm",
        "icon": "package",
        "description": "Node package manager",
        "command": "npm",
        "category": "dev",
    },
    "pip": {
        "display_name": "pip",
        "icon": "package",
        "description": "Python package installer",
        "command": "pip",
        "category": "dev",
    },
}


class IntegrationManager:
    """
    Manages integration with external tools on the device.
    Auto-detects installed tools and provides API to invoke them.
    """

    def __init__(self):
        self._tools: Dict[str, ExternalTool] = {}
        self._scan_done = False

    def scan_tools(self) -> Dict[str, Any]:
        """Scan the system for known tools."""
        detected = 0
        for name, info in KNOWN_TOOLS.items():
            tool = ExternalTool(
                name=name,
                display_name=info["display_name"],
                icon=info["icon"],
                description=info["description"],
                command=info["command"],
                category=info.get("category", "dev"),
            )

            # Check if tool exists
            path = shutil.which(info["command"])
            if path:
                tool.detected = True
                tool.path = path

                # Try to get version
                try:
                    result = subprocess.run(
                        [info["command"], "--version"],
                        capture_output=True, text=True, timeout=5,
                    )
                    version_text = result.stdout.strip() or result.stderr.strip()
                    # Extract first line as version
                    tool.version = version_text.split("\n")[0][:80] if version_text else ""
                except Exception:
                    pass

                detected += 1

            self._tools[name] = tool

        self._scan_done = True
        return {
            "total_known": len(KNOWN_TOOLS),
            "detected": detected,
            "tools": [t.to_dict() for t in self._tools.values() if t.detected],
        }

    def get_detected_tools(self) -> List[Dict[str, Any]]:
        if not self._scan_done:
            self.scan_tools()
        return [t.to_dict() for t in self._tools.values() if t.detected]

    def get_all_tools(self) -> List[Dict[str, Any]]:
        if not self._scan_done:
            self.scan_tools()
        return [t.to_dict() for t in self._tools.values()]

    async def invoke_tool(self, tool_name: str, args: List[str] = None, timeout: int = 30) -> Dict[str, Any]:
        """Invoke an external tool."""
        tool = self._tools.get(tool_name)
        if not tool or not tool.detected:
            return {"success": False, "error": f"Tool not found or not installed: {tool_name}"}

        try:
            cmd = [tool.command] + (args or [])
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

            return {
                "success": proc.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace")[:5000],
                "stderr": stderr.decode("utf-8", errors="replace")[:2000],
                "return_code": proc.returncode,
                "tool": tool_name,
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": f"Timeout after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_tools_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        if not self._scan_done:
            self.scan_tools()
        categories: Dict[str, List] = {}
        for tool in self._tools.values():
            if tool.detected:
                cat = tool.category
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(tool.to_dict())
        return categories

    def register_custom_tool(
        self,
        name: str,
        display_name: str,
        command: str,
        description: str = "",
        icon: str = "🔧",
        category: str = "custom",
    ) -> bool:
        """Register a custom external tool."""
        path = shutil.which(command)
        self._tools[name] = ExternalTool(
            name=name,
            display_name=display_name,
            icon=icon,
            description=description,
            command=command,
            detected=bool(path),
            path=path or "",
            category=category,
        )
        return bool(path)


_integration_mgr: Optional[IntegrationManager] = None

def get_integration_manager() -> IntegrationManager:
    global _integration_mgr
    if _integration_mgr is None:
        _integration_mgr = IntegrationManager()
    return _integration_mgr
