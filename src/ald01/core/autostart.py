"""
ALD-01 Autostart Manager
Manages system startup integration so ALD-01 starts when the laptop boots.
Supports Windows (Startup folder / Task Scheduler), macOS (LaunchAgent), Linux (systemd).
"""

import os
import sys
import logging
import platform
import subprocess
from typing import Dict, Optional

logger = logging.getLogger("ald01.autostart")


class AutostartManager:
    """
    Manages autostart for ALD-01.
    When enabled, ALD-01 starts its background systems when the computer boots:
    - Loads yesterday's state
    - Initializes providers
    - Starts Telegram bot
    - Enables notifications
    """

    def __init__(self):
        self._app_name = "ALD-01"
        self._system = platform.system().lower()

    def is_enabled(self) -> bool:
        """Check if autostart is currently enabled."""
        if self._system == "windows":
            return self._check_windows()
        elif self._system == "darwin":
            return self._check_macos()
        elif self._system == "linux":
            return self._check_linux()
        return False

    def enable(self) -> Dict[str, any]:
        """Enable autostart."""
        if self._system == "windows":
            return self._enable_windows()
        elif self._system == "darwin":
            return self._enable_macos()
        elif self._system == "linux":
            return self._enable_linux()
        return {"success": False, "error": f"Unsupported OS: {self._system}"}

    def disable(self) -> Dict[str, any]:
        """Disable autostart."""
        if self._system == "windows":
            return self._disable_windows()
        elif self._system == "darwin":
            return self._disable_macos()
        elif self._system == "linux":
            return self._disable_linux()
        return {"success": False, "error": f"Unsupported OS: {self._system}"}

    def get_status(self) -> Dict[str, any]:
        return {
            "enabled": self.is_enabled(),
            "os": self._system,
            "method": self._get_method(),
        }

    def _get_method(self) -> str:
        if self._system == "windows":
            return "Windows Startup Folder"
        elif self._system == "darwin":
            return "macOS LaunchAgent"
        elif self._system == "linux":
            return "systemd user service"
        return "unknown"

    # ──── Windows ────

    def _get_windows_shortcut_path(self) -> str:
        startup_dir = os.path.join(
            os.environ.get("APPDATA", ""),
            "Microsoft", "Windows", "Start Menu", "Programs", "Startup",
        )
        return os.path.join(startup_dir, f"{self._app_name}.bat")

    def _check_windows(self) -> bool:
        return os.path.exists(self._get_windows_shortcut_path())

    def _enable_windows(self) -> Dict[str, any]:
        try:
            bat_path = self._get_windows_shortcut_path()
            python_exe = sys.executable
            script = f'@echo off\nstart /min "" "{python_exe}" -m ald01 serve --background\n'

            os.makedirs(os.path.dirname(bat_path), exist_ok=True)
            with open(bat_path, "w") as f:
                f.write(script)

            return {"success": True, "path": bat_path, "method": "Startup folder BAT"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _disable_windows(self) -> Dict[str, any]:
        try:
            path = self._get_windows_shortcut_path()
            if os.path.exists(path):
                os.remove(path)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ──── macOS ────

    def _get_macos_plist_path(self) -> str:
        return os.path.expanduser(f"~/Library/LaunchAgents/com.ald01.agent.plist")

    def _check_macos(self) -> bool:
        return os.path.exists(self._get_macos_plist_path())

    def _enable_macos(self) -> Dict[str, any]:
        try:
            plist_path = self._get_macos_plist_path()
            python_exe = sys.executable
            plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ald01.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_exe}</string>
        <string>-m</string>
        <string>ald01</string>
        <string>serve</string>
        <string>--background</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>"""
            os.makedirs(os.path.dirname(plist_path), exist_ok=True)
            with open(plist_path, "w") as f:
                f.write(plist)
            subprocess.run(["launchctl", "load", plist_path], capture_output=True)
            return {"success": True, "path": plist_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _disable_macos(self) -> Dict[str, any]:
        try:
            path = self._get_macos_plist_path()
            if os.path.exists(path):
                subprocess.run(["launchctl", "unload", path], capture_output=True)
                os.remove(path)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ──── Linux ────

    def _get_linux_service_path(self) -> str:
        return os.path.expanduser("~/.config/systemd/user/ald01.service")

    def _check_linux(self) -> bool:
        return os.path.exists(self._get_linux_service_path())

    def _enable_linux(self) -> Dict[str, any]:
        try:
            service_path = self._get_linux_service_path()
            python_exe = sys.executable
            service = f"""[Unit]
Description=ALD-01 AI Agent
After=network.target

[Service]
Type=simple
ExecStart={python_exe} -m ald01 serve --background
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
"""
            os.makedirs(os.path.dirname(service_path), exist_ok=True)
            with open(service_path, "w") as f:
                f.write(service)
            subprocess.run(["systemctl", "--user", "enable", "ald01"], capture_output=True)
            return {"success": True, "path": service_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _disable_linux(self) -> Dict[str, any]:
        try:
            subprocess.run(["systemctl", "--user", "disable", "ald01"], capture_output=True)
            path = self._get_linux_service_path()
            if os.path.exists(path):
                os.remove(path)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}


_autostart: Optional[AutostartManager] = None

def get_autostart_manager() -> AutostartManager:
    global _autostart
    if _autostart is None:
        _autostart = AutostartManager()
    return _autostart
