"""
ALD-01 MCP (Model Context Protocol) Manager
Discovers, installs, and manages MCP servers for extended capabilities.
"""

import os
import json
import time
import shutil
import asyncio
import subprocess
import logging
from typing import Any, Dict, List, Optional

from ald01 import CONFIG_DIR, DATA_DIR

logger = logging.getLogger("ald01.mcp")


# Known MCP servers that ALD can auto-install
MCP_REGISTRY = {
    "filesystem": {
        "name": "Filesystem",
        "icon": "folder-open",
        "description": "Read, write, and navigate files and directories",
        "package": "@anthropic-ai/mcp-server-filesystem",
        "command": "npx",
        "args": ["-y", "@anthropic-ai/mcp-server-filesystem"],
        "category": "core",
    },
    "github": {
        "name": "GitHub",
        "icon": "github",
        "description": "Interact with GitHub repos, issues, PRs, and code",
        "package": "@anthropic-ai/mcp-server-github",
        "command": "npx",
        "args": ["-y", "@anthropic-ai/mcp-server-github"],
        "env_vars": ["GITHUB_TOKEN"],
        "category": "dev",
    },
    "postgres": {
        "name": "PostgreSQL",
        "icon": "database",
        "description": "Query PostgreSQL databases",
        "package": "@anthropic-ai/mcp-server-postgres",
        "command": "npx",
        "args": ["-y", "@anthropic-ai/mcp-server-postgres"],
        "env_vars": ["DATABASE_URL"],
        "category": "data",
    },
    "memory": {
        "name": "Memory",
        "icon": "brain",
        "description": "Knowledge graph-based persistent memory",
        "package": "@anthropic-ai/mcp-server-memory",
        "command": "npx",
        "args": ["-y", "@anthropic-ai/mcp-server-memory"],
        "category": "core",
    },
    "puppeteer": {
        "name": "Puppeteer",
        "icon": "globe",
        "description": "Browser automation and web scraping",
        "package": "@anthropic-ai/mcp-server-puppeteer",
        "command": "npx",
        "args": ["-y", "@anthropic-ai/mcp-server-puppeteer"],
        "category": "web",
    },
    "sequential-thinking": {
        "name": "Sequential Thinking",
        "icon": "list-ordered",
        "description": "Step-by-step reasoning and problem decomposition",
        "package": "@anthropic-ai/mcp-server-sequential-thinking",
        "command": "npx",
        "args": ["-y", "@anthropic-ai/mcp-server-sequential-thinking"],
        "category": "core",
    },
    "brave-search": {
        "name": "Brave Search",
        "icon": "search",
        "description": "Web search via Brave Search API",
        "package": "@anthropic-ai/mcp-server-brave-search",
        "command": "npx",
        "args": ["-y", "@anthropic-ai/mcp-server-brave-search"],
        "env_vars": ["BRAVE_SEARCH_API_KEY"],
        "category": "web",
    },
    "tavily-search": {
        "name": "Tavily Search",
        "icon": "scan-search",
        "description": "AI-powered web research and content extraction",
        "package": "@tavily/mcp-server",
        "command": "npx",
        "args": ["-y", "@tavily/mcp-server"],
        "env_vars": ["TAVILY_API_KEY"],
        "category": "web",
    },
    "slack": {
        "name": "Slack",
        "icon": "message-circle",
        "description": "Send and read Slack messages",
        "package": "@anthropic-ai/mcp-server-slack",
        "command": "npx",
        "args": ["-y", "@anthropic-ai/mcp-server-slack"],
        "env_vars": ["SLACK_BOT_TOKEN"],
        "category": "communication",
    },
    "sqlite": {
        "name": "SQLite",
        "icon": "hard-drive",
        "description": "Query SQLite databases",
        "package": "@anthropic-ai/mcp-server-sqlite",
        "command": "npx",
        "args": ["-y", "@anthropic-ai/mcp-server-sqlite"],
        "category": "data",
    },
    "fetch": {
        "name": "Fetch",
        "icon": "download",
        "description": "HTTP requests and URL content extraction",
        "package": "@anthropic-ai/mcp-server-fetch",
        "command": "npx",
        "args": ["-y", "@anthropic-ai/mcp-server-fetch"],
        "category": "web",
    },
    "docker": {
        "name": "Docker",
        "icon": "container",
        "description": "Manage Docker containers and images",
        "package": "@anthropic-ai/mcp-server-docker",
        "command": "npx",
        "args": ["-y", "@anthropic-ai/mcp-server-docker"],
        "category": "dev",
    },
}


class MCPManager:
    """
    MCP Server Manager for ALD-01.
    Installs, configures, and manages MCP servers.
    """

    def __init__(self):
        self._installed: Dict[str, Dict[str, Any]] = {}
        self._running: Dict[str, Any] = {}
        self._persistence_path = os.path.join(CONFIG_DIR, "mcp_config.json")
        self._load()

    def list_available(self) -> List[Dict[str, Any]]:
        """List all available MCP servers."""
        return [
            {
                "id": sid,
                **{k: v for k, v in sdata.items() if k != "args"},
                "installed": sid in self._installed,
                "running": sid in self._running,
            }
            for sid, sdata in MCP_REGISTRY.items()
        ]

    def list_installed(self) -> List[Dict[str, Any]]:
        return [
            {"id": sid, **sdata, "running": sid in self._running}
            for sid, sdata in self._installed.items()
        ]

    async def install_server(self, server_id: str) -> Dict[str, Any]:
        """Install an MCP server via npm."""
        if server_id not in MCP_REGISTRY:
            return {"success": False, "error": f"Unknown MCP server: {server_id}"}

        info = MCP_REGISTRY[server_id]

        if not shutil.which("npx"):
            return {"success": False, "error": "npx not found. Install Node.js first."}

        try:
            proc = await asyncio.create_subprocess_exec(
                "npm", "install", "-g", info["package"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

            if proc.returncode != 0:
                err_msg = stderr.decode("utf-8", errors="replace")[:500]
                return {"success": False, "error": err_msg}

            self._installed[server_id] = {
                "name": info["name"],
                "icon": info["icon"],
                "description": info["description"],
                "package": info["package"],
                "installed_at": time.time(),
                "enabled": True,
            }
            self._save()
            return {"success": True, "server": server_id, "package": info["package"]}

        except asyncio.TimeoutError:
            return {"success": False, "error": "Installation timed out after 120s"}
        except Exception as e:
            logger.error(f"MCP install error for {server_id}: {e}")
            return {"success": False, "error": str(e)}

    def uninstall_server(self, server_id: str) -> bool:
        if server_id in self._installed:
            del self._installed[server_id]
            self._save()
            return True
        return False

    def enable_server(self, server_id: str) -> bool:
        if server_id in self._installed:
            self._installed[server_id]["enabled"] = True
            self._save()
            return True
        return False

    def disable_server(self, server_id: str) -> bool:
        if server_id in self._installed:
            self._installed[server_id]["enabled"] = False
            self._save()
            return True
        return False

    def get_config_for_client(self) -> Dict[str, Any]:
        """Generate MCP client config (e.g. for Claude Desktop, Windsurf)."""
        servers = {}
        for sid, sdata in self._installed.items():
            if not sdata.get("enabled"):
                continue
            reg = MCP_REGISTRY.get(sid, {})
            config = {
                "command": reg.get("command", "npx"),
                "args": reg.get("args", []),
            }
            env_vars = reg.get("env_vars", [])
            if env_vars:
                config["env"] = {v: os.environ.get(v, "") for v in env_vars}
            servers[sid] = config
        return {"mcpServers": servers}

    def export_config(self, path: str = "") -> str:
        """Export MCP config to a JSON file."""
        config = self.get_config_for_client()
        if not path:
            path = os.path.join(CONFIG_DIR, "mcp_servers.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return path

    def get_stats(self) -> Dict[str, Any]:
        return {
            "available": len(MCP_REGISTRY),
            "installed": len(self._installed),
            "enabled": sum(1 for s in self._installed.values() if s.get("enabled")),
            "running": len(self._running),
            "categories": sorted(set(s.get("category", "") for s in MCP_REGISTRY.values())),
        }

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._persistence_path), exist_ok=True)
            with open(self._persistence_path, "w", encoding="utf-8") as f:
                json.dump(self._installed, f, indent=2)
        except Exception as e:
            logger.warning(f"MCP config save failed: {e}")

    def _load(self) -> None:
        try:
            if os.path.exists(self._persistence_path):
                with open(self._persistence_path, encoding="utf-8") as f:
                    self._installed = json.load(f)
        except Exception:
            self._installed = {}


_mcp_mgr: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    global _mcp_mgr
    if _mcp_mgr is None:
        _mcp_mgr = MCPManager()
    return _mcp_mgr
