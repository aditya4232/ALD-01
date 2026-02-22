"""
ALD-01 Doctor Diagnostics
Comprehensive health checks for the entire system.
"""

import os
import sys
import time
import shutil
import asyncio
import platform
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

import psutil

from ald01 import CONFIG_DIR
from ald01.config import get_config
from ald01.providers.manager import get_provider_manager
from ald01.providers.openai_compat import FREE_PROVIDERS

logger = logging.getLogger("ald01.doctor")


@dataclass
class CheckResult:
    """Result of a single diagnostic check."""
    name: str
    category: str
    status: str  # 'pass', 'warn', 'fail'
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    fix_available: bool = False
    fix_command: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "fix_available": self.fix_available,
            "fix_command": self.fix_command,
        }

    @property
    def icon(self) -> str:
        return {"pass": "✓", "warn": "⚠", "fail": "✗"}.get(self.status, "?")


class DoctorDiagnostics:
    """Run comprehensive health checks on the ALD-01 system."""

    def __init__(self):
        self._config = get_config()
        self._results: List[CheckResult] = []

    async def run_all(self) -> List[CheckResult]:
        """Run all diagnostic checks."""
        self._results = []

        checks = [
            self._check_python_version,
            self._check_dependencies,
            self._check_config_file,
            self._check_data_directory,
            self._check_memory_database,
            self._check_ports,
            self._check_system_resources,
            self._check_network,
            self._check_ollama,
            self._check_providers,
            self._check_free_api_keys,
            self._check_voice,
        ]

        for check in checks:
            try:
                result = await check()
                if isinstance(result, list):
                    self._results.extend(result)
                else:
                    self._results.append(result)
            except Exception as e:
                self._results.append(CheckResult(
                    name=check.__name__,
                    category="system",
                    status="fail",
                    message=f"Check failed with error: {e}",
                ))

        return self._results

    async def _check_python_version(self) -> CheckResult:
        """Check Python version."""
        version = sys.version_info
        if version >= (3, 10):
            return CheckResult("Python Version", "dependencies", "pass",
                             f"Python {version.major}.{version.minor}.{version.micro}")
        elif version >= (3, 8):
            return CheckResult("Python Version", "dependencies", "warn",
                             f"Python {version.major}.{version.minor} — upgrade to 3.10+ recommended")
        else:
            return CheckResult("Python Version", "dependencies", "fail",
                             f"Python {version.major}.{version.minor} — requires 3.10+",
                             fix_available=True, fix_command="Download from python.org")

    async def _check_dependencies(self) -> List[CheckResult]:
        """Check required Python packages."""
        results = []
        required = {
            "click": "CLI framework",
            "rich": "Terminal UI",
            "httpx": "HTTP client",
            "fastapi": "Web dashboard",
            "uvicorn": "ASGI server",
            "yaml": "Config parser",
            "psutil": "System info",
        }

        for pkg, desc in required.items():
            try:
                __import__(pkg)
                results.append(CheckResult(f"Package: {pkg}", "dependencies", "pass", f"{desc} — installed"))
            except ImportError:
                results.append(CheckResult(f"Package: {pkg}", "dependencies", "fail",
                                         f"{desc} — NOT installed",
                                         fix_available=True, fix_command=f"pip install {pkg}"))

        # Optional packages
        optional = {
            "edge_tts": "Voice (Neural TTS)",
            "pyttsx3": "Voice (Offline TTS)",
        }
        for pkg, desc in optional.items():
            try:
                __import__(pkg)
                results.append(CheckResult(f"Optional: {pkg}", "dependencies", "pass", f"{desc} — installed"))
            except ImportError:
                results.append(CheckResult(f"Optional: {pkg}", "dependencies", "warn",
                                         f"{desc} — not installed (voice will be limited)",
                                         fix_available=True, fix_command=f"pip install {pkg}"))

        return results

    async def _check_config_file(self) -> CheckResult:
        """Check config file exists and is valid."""
        config_path = os.path.join(CONFIG_DIR, "config.yaml")
        if os.path.exists(config_path):
            try:
                import yaml
                with open(config_path) as f:
                    yaml.safe_load(f)
                size = os.path.getsize(config_path)
                return CheckResult("Config File", "config", "pass",
                                 f"Valid config at {config_path} ({size} bytes)")
            except Exception as e:
                return CheckResult("Config File", "config", "fail",
                                 f"Config file is corrupted: {e}",
                                 fix_available=True, fix_command="ald-01 config reset")
        else:
            return CheckResult("Config File", "config", "warn",
                             "No config file — will use defaults",
                             fix_available=True, fix_command="ald-01 config reset")

    async def _check_data_directory(self) -> CheckResult:
        """Check data directory exists and is writable."""
        if os.path.exists(CONFIG_DIR):
            test_file = os.path.join(CONFIG_DIR, ".write_test")
            try:
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                return CheckResult("Data Directory", "filesystem", "pass",
                                 f"Writable at {CONFIG_DIR}")
            except PermissionError:
                return CheckResult("Data Directory", "filesystem", "fail",
                                 f"Not writable: {CONFIG_DIR}",
                                 fix_available=True, fix_command=f"chmod 755 {CONFIG_DIR}")
        else:
            return CheckResult("Data Directory", "filesystem", "fail",
                             f"Missing: {CONFIG_DIR}",
                             fix_available=True, fix_command=f"mkdir -p {CONFIG_DIR}")

    async def _check_memory_database(self) -> CheckResult:
        """Check memory database."""
        from ald01.core.memory import get_memory
        try:
            mem = get_memory()
            stats = mem.get_stats()
            return CheckResult("Memory Database", "memory", "pass",
                             f"SQLite OK — {stats['messages']} messages, {stats['db_size_mb']} MB",
                             details=stats)
        except Exception as e:
            return CheckResult("Memory Database", "memory", "fail",
                             f"Database error: {e}")

    async def _check_ports(self) -> CheckResult:
        """Check if required ports are available."""
        port = self._config.get("dashboard", "port", default=7860)
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(1)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            if result == 0:
                return CheckResult("Dashboard Port", "network", "warn",
                                 f"Port {port} is already in use",
                                 fix_available=True, fix_command=f"ald-01 config set dashboard.port {port + 1}")
            else:
                return CheckResult("Dashboard Port", "network", "pass",
                                 f"Port {port} is available")
        except Exception:
            sock.close()
            return CheckResult("Dashboard Port", "network", "pass",
                             f"Port {port} is available")

    async def _check_system_resources(self) -> CheckResult:
        """Check system resources (CPU, RAM, disk)."""
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(os.path.expanduser("~"))

        issues = []
        if mem.available < 1 * 1024**3:  # Less than 1GB
            issues.append(f"Low RAM: {mem.available / 1024**3:.1f} GB free")
        if disk.free < 1 * 1024**3:  # Less than 1GB
            issues.append(f"Low disk: {disk.free / 1024**3:.1f} GB free")

        if issues:
            return CheckResult("System Resources", "system", "warn",
                             "; ".join(issues),
                             details={
                                 "ram_total_gb": round(mem.total / 1024**3, 1),
                                 "ram_free_gb": round(mem.available / 1024**3, 1),
                                 "disk_free_gb": round(disk.free / 1024**3, 1),
                             })
        else:
            return CheckResult("System Resources", "system", "pass",
                             f"RAM: {mem.available / 1024**3:.1f} GB free, "
                             f"Disk: {disk.free / 1024**3:.1f} GB free")

    async def _check_network(self) -> CheckResult:
        """Check internet connectivity."""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get("https://httpbin.org/get")
                if resp.status_code == 200:
                    return CheckResult("Internet", "network", "pass", "Connected")
        except Exception:
            pass
        return CheckResult("Internet", "network", "warn",
                         "No internet — only local providers (Ollama) will work")

    async def _check_ollama(self) -> CheckResult:
        """Check Ollama availability."""
        import httpx
        host = self._config.get("providers", "ollama", "host", default="http://localhost:11434")
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{host}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    return CheckResult("Ollama", "providers", "pass",
                                     f"Running at {host} — {len(models)} models",
                                     details={"models": models})
        except Exception:
            pass
        return CheckResult("Ollama", "providers", "warn",
                         f"Not running at {host}. Install: ollama.ai",
                         fix_available=True, fix_command="curl -fsSL https://ollama.ai/install.sh | sh")

    async def _check_providers(self) -> List[CheckResult]:
        """Check all configured providers."""
        results = []
        mgr = get_provider_manager()
        await mgr.initialize()
        statuses = await mgr.test_all()

        for name, status in statuses.items():
            if status.online:
                results.append(CheckResult(
                    f"Provider: {name}", "providers", "pass",
                    f"Online ({status.latency_ms:.0f}ms) — {len(status.models)} models",
                ))
            else:
                results.append(CheckResult(
                    f"Provider: {name}", "providers", "fail",
                    f"Offline: {status.error}",
                ))

        if not statuses:
            results.append(CheckResult(
                "Providers", "providers", "warn",
                "No providers configured. Run: ald-01 provider add <name>",
            ))

        return results

    async def _check_free_api_keys(self) -> List[CheckResult]:
        """Check which free API keys are configured."""
        results = []
        for key, preset in FREE_PROVIDERS.items():
            if not preset.get("free_tier"):
                continue
            env_key = preset.get("env_key", "")
            has_key = bool(os.environ.get(env_key, ""))
            if has_key:
                results.append(CheckResult(
                    f"API Key: {preset['name']}", "api_keys", "pass",
                    f"{env_key} is set",
                ))
            else:
                results.append(CheckResult(
                    f"API Key: {preset['name']}", "api_keys", "warn",
                    f"Not set: export {env_key}=<your-key>",
                    details={"description": preset["description"]},
                ))
        return results

    async def _check_voice(self) -> CheckResult:
        """Check voice/TTS availability."""
        engines = []
        try:
            import edge_tts  # noqa: F401
            engines.append("edge-tts")
        except ImportError:
            pass
        try:
            import pyttsx3  # noqa: F401
            engines.append("pyttsx3")
        except ImportError:
            pass

        if platform.system() == "Windows":
            engines.append("system-tts")
        elif platform.system() == "Darwin":
            engines.append("say")
        elif shutil.which("espeak"):
            engines.append("espeak")

        if engines:
            return CheckResult("Voice/TTS", "voice", "pass",
                             f"Available engines: {', '.join(engines)}")
        else:
            return CheckResult("Voice/TTS", "voice", "warn",
                             "No TTS engine found. Install: pip install edge-tts",
                             fix_available=True, fix_command="pip install edge-tts")

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all results."""
        passed = sum(1 for r in self._results if r.status == "pass")
        warned = sum(1 for r in self._results if r.status == "warn")
        failed = sum(1 for r in self._results if r.status == "fail")
        fixable = sum(1 for r in self._results if r.fix_available)

        return {
            "total": len(self._results),
            "passed": passed,
            "warnings": warned,
            "failed": failed,
            "fixable": fixable,
            "healthy": failed == 0,
            "results": [r.to_dict() for r in self._results],
        }
