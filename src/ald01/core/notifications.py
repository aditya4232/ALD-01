"""
ALD-01 Desktop Notifications
Cross-platform desktop notifications that work even when dashboard is closed.
Also integrates with Telegram for remote notifications.
"""

import os
import sys
import time
import asyncio
import logging
import subprocess
from typing import Any, Dict, List, Optional

from ald01.core.status import get_status_manager

logger = logging.getLogger("ald01.notifications")


class NotificationManager:
    """
    Cross-platform notification system.
    Works via:
    - Windows: PowerShell toast notifications
    - macOS: osascript notifications
    - Linux: notify-send
    - Telegram: via bot API
    Respects user status (DND = no notifications).
    """

    def __init__(self):
        self._history: List[Dict[str, Any]] = []
        self._enabled = True
        self._telegram_enabled = True

    async def notify(
        self,
        title: str,
        message: str,
        priority: str = "normal",  # 'critical', 'high', 'normal', 'low'
        source: str = "system",
        send_telegram: bool = True,
    ) -> bool:
        """Send a notification across all enabled channels."""
        status_mgr = get_status_manager()

        # Record in history
        self._history.append({
            "title": title,
            "message": message,
            "priority": priority,
            "source": source,
            "timestamp": time.time(),
            "delivered": False,
        })
        if len(self._history) > 200:
            self._history = self._history[-200:]

        # Check status
        if not status_mgr.can_notify(priority):
            status_mgr.queue_message(f"{title}: {message}", source, priority)
            return False

        delivered = False

        # Desktop notification
        if self._enabled:
            try:
                self._send_desktop(title, message)
                delivered = True
            except Exception as e:
                logger.debug(f"Desktop notification failed: {e}")

        # Telegram notification
        if send_telegram and self._telegram_enabled and status_mgr.can_send_telegram():
            try:
                from ald01.telegram.bot import get_telegram_bot
                bot = get_telegram_bot()
                if bot.is_configured():
                    text = f"<b>🤖 ALD-01 — {title}</b>\n\n{message}"
                    # Send to first allowed user
                    for uid in bot.allowed_users:
                        await bot.send_message(uid, text)
                        delivered = True
                        break
            except Exception as e:
                logger.debug(f"Telegram notification failed: {e}")

        self._history[-1]["delivered"] = delivered
        return delivered

    def _send_desktop(self, title: str, message: str) -> None:
        """Send OS-native desktop notification."""
        platform = sys.platform

        if platform == "win32":
            # Windows PowerShell toast
            ps_script = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $textNodes = $template.GetElementsByTagName("text")
            $textNodes.Item(0).AppendChild($template.CreateTextNode("{title}")) > $null
            $textNodes.Item(1).AppendChild($template.CreateTextNode("{message}")) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("ALD-01").Show($toast)
            """
            try:
                subprocess.run(
                    ["powershell", "-Command", ps_script],
                    capture_output=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
                )
            except Exception:
                # Fallback: simple msg box
                try:
                    subprocess.Popen(
                        ["msg", "*", f"ALD-01: {title}\n{message}"],
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
                    )
                except Exception:
                    pass

        elif platform == "darwin":
            # macOS
            script = f'display notification "{message}" with title "ALD-01" subtitle "{title}"'
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)

        elif platform.startswith("linux"):
            # Linux
            try:
                subprocess.run(
                    ["notify-send", f"ALD-01 — {title}", message, "--app-name=ALD-01"],
                    capture_output=True, timeout=5,
                )
            except FileNotFoundError:
                pass

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._history[-limit:]

    def clear_history(self) -> None:
        self._history.clear()

    def set_enabled(self, desktop: bool = True, telegram: bool = True) -> None:
        self._enabled = desktop
        self._telegram_enabled = telegram


_notification_mgr: Optional[NotificationManager] = None

def get_notification_manager() -> NotificationManager:
    global _notification_mgr
    if _notification_mgr is None:
        _notification_mgr = NotificationManager()
    return _notification_mgr
