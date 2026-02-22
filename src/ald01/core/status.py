"""
ALD-01 User Status System
Manages user availability status (open, silent, do-not-disturb).
Status affects how ALD-01 interacts across all interfaces (dashboard, terminal, Telegram).
"""

import os
import time
import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from ald01 import CONFIG_DIR

logger = logging.getLogger("ald01.status")


class UserStatus(str, Enum):
    """User availability status."""
    OPEN = "open"             # ALD-01 can proactively message, notify, suggest
    SILENT = "silent"         # ALD-01 responds only when asked, minimal notifications
    DND = "dnd"               # Do Not Disturb — no Telegram messages, no dashboard popups
    AWAY = "away"             # User is away — queue messages for later
    FOCUS = "focus"           # Deep focus — only critical notifications
    OFFLINE = "offline"       # System paused — no processing


STATUS_PROFILES: Dict[str, Dict[str, Any]] = {
    UserStatus.OPEN.value: {
        "display_name": "Open",
        "icon": "🟢",
        "color": "green",
        "description": "Available — ALD-01 can proactively help",
        "allow_proactive": True,
        "allow_notifications": True,
        "allow_telegram": True,
        "allow_voice": True,
        "allow_dashboard_popups": True,
        "response_style": "full",
        "greeting": "I'm here and ready to help!",
    },
    UserStatus.SILENT.value: {
        "display_name": "Silent Work",
        "icon": "🔇",
        "color": "yellow",
        "description": "Working quietly — respond only when asked",
        "allow_proactive": False,
        "allow_notifications": False,
        "allow_telegram": True,
        "allow_voice": False,
        "allow_dashboard_popups": False,
        "response_style": "concise",
        "greeting": "Working silently. I'll respond when you need me.",
    },
    UserStatus.DND.value: {
        "display_name": "Do Not Disturb",
        "icon": "🔴",
        "color": "red",
        "description": "No messages, no notifications, no interruptions",
        "allow_proactive": False,
        "allow_notifications": False,
        "allow_telegram": False,
        "allow_voice": False,
        "allow_dashboard_popups": False,
        "response_style": "minimal",
        "greeting": "DND active. Messages are queued.",
    },
    UserStatus.AWAY.value: {
        "display_name": "Away",
        "icon": "🟡",
        "color": "bright_yellow",
        "description": "User is away — messages queued for return",
        "allow_proactive": False,
        "allow_notifications": False,
        "allow_telegram": False,
        "allow_voice": False,
        "allow_dashboard_popups": False,
        "response_style": "queue",
        "greeting": "You're away. I'll save messages for when you're back.",
    },
    UserStatus.FOCUS.value: {
        "display_name": "Deep Focus",
        "icon": "🎯",
        "color": "magenta",
        "description": "Deep work — only critical alerts",
        "allow_proactive": False,
        "allow_notifications": False,
        "allow_telegram": False,
        "allow_voice": False,
        "allow_dashboard_popups": False,
        "response_style": "brief",
        "greeting": "Focus mode. Only critical issues will get through.",
    },
    UserStatus.OFFLINE.value: {
        "display_name": "Offline",
        "icon": "⚫",
        "color": "dim",
        "description": "System paused — no processing",
        "allow_proactive": False,
        "allow_notifications": False,
        "allow_telegram": False,
        "allow_voice": False,
        "allow_dashboard_popups": False,
        "response_style": "none",
        "greeting": "System paused.",
    },
}


@dataclass
class QueuedMessage:
    """A message queued during DND/Away status."""
    content: str
    source: str  # 'telegram', 'dashboard', 'system', 'agent'
    priority: str  # 'critical', 'high', 'normal', 'low'
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "source": self.source,
            "priority": self.priority,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "age_seconds": round(time.time() - self.timestamp),
        }


class StatusManager:
    """
    Manages user status across all ALD-01 interfaces.
    Controls notifications, proactive behavior, and message queueing.
    """

    def __init__(self):
        self._status: UserStatus = UserStatus.OPEN
        self._status_history: List[Dict[str, Any]] = []
        self._queued_messages: List[QueuedMessage] = []
        self._scheduled_status: Optional[Dict[str, Any]] = None
        self._auto_away_minutes: int = 30
        self._last_activity: float = time.time()
        self._persistence_path = os.path.join(CONFIG_DIR, "status.json")
        self._load_status()

    @property
    def current_status(self) -> UserStatus:
        return self._status

    @property
    def status_profile(self) -> Dict[str, Any]:
        return STATUS_PROFILES.get(self._status.value, STATUS_PROFILES[UserStatus.OPEN.value])

    def set_status(self, status: str) -> Dict[str, Any]:
        """Set user status. Returns the status profile."""
        status = status.lower().strip()

        # Map common aliases
        aliases = {
            "open": UserStatus.OPEN,
            "available": UserStatus.OPEN,
            "online": UserStatus.OPEN,
            "silent": UserStatus.SILENT,
            "quiet": UserStatus.SILENT,
            "dnd": UserStatus.DND,
            "donotdisturb": UserStatus.DND,
            "do_not_disturb": UserStatus.DND,
            "busy": UserStatus.DND,
            "away": UserStatus.AWAY,
            "afk": UserStatus.AWAY,
            "focus": UserStatus.FOCUS,
            "deepwork": UserStatus.FOCUS,
            "deep_focus": UserStatus.FOCUS,
            "offline": UserStatus.OFFLINE,
            "pause": UserStatus.OFFLINE,
        }

        new_status = aliases.get(status.replace(" ", "").replace("-", ""))
        if new_status is None:
            try:
                new_status = UserStatus(status)
            except ValueError:
                raise ValueError(
                    f"Unknown status: '{status}'. "
                    f"Available: {', '.join(s.value for s in UserStatus)}"
                )

        old_status = self._status
        self._status = new_status
        self._last_activity = time.time()

        # Log change
        self._status_history.append({
            "from": old_status.value,
            "to": new_status.value,
            "timestamp": time.time(),
        })
        if len(self._status_history) > 100:
            self._status_history = self._status_history[-100:]

        self._save_status()
        logger.info(f"Status changed: {old_status.value} → {new_status.value}")

        profile = self.status_profile
        profile["previous"] = old_status.value

        # If returning from DND/Away, deliver queued messages
        if old_status in (UserStatus.DND, UserStatus.AWAY) and new_status == UserStatus.OPEN:
            profile["queued_messages"] = len(self._queued_messages)

        return profile

    def can_notify(self, priority: str = "normal") -> bool:
        """Check if ALD-01 is allowed to send a notification at the current status."""
        profile = self.status_profile

        if not profile.get("allow_notifications", False):
            # Only allow critical through during Focus mode
            if self._status == UserStatus.FOCUS and priority == "critical":
                return True
            return False
        return True

    def can_send_telegram(self) -> bool:
        """Check if Telegram messages are allowed."""
        return self.status_profile.get("allow_telegram", False)

    def can_use_voice(self) -> bool:
        """Check if voice output is allowed."""
        return self.status_profile.get("allow_voice", False)

    def can_be_proactive(self) -> bool:
        """Check if proactive suggestions are allowed."""
        return self.status_profile.get("allow_proactive", False)

    def get_response_style(self) -> str:
        """Get how responses should be formatted based on status."""
        return self.status_profile.get("response_style", "full")

    def queue_message(self, content: str, source: str = "system", priority: str = "normal") -> None:
        """Queue a message for delivery when status changes."""
        msg = QueuedMessage(content=content, source=source, priority=priority)
        self._queued_messages.append(msg)

        # Keep queue bounded
        if len(self._queued_messages) > 200:
            self._queued_messages = self._queued_messages[-200:]

        logger.debug(f"Message queued ({source}): {content[:50]}")

    def get_queued_messages(self, clear: bool = True) -> List[Dict[str, Any]]:
        """Get and optionally clear queued messages."""
        messages = [m.to_dict() for m in self._queued_messages]
        if clear:
            self._queued_messages.clear()
        return messages

    def record_activity(self) -> None:
        """Record user activity (for auto-away detection)."""
        self._last_activity = time.time()
        # If was auto-away, come back
        if self._status == UserStatus.AWAY:
            self.set_status("open")

    def check_auto_away(self) -> bool:
        """Check if user should be auto-set to Away."""
        if self._status != UserStatus.OPEN:
            return False
        if self._auto_away_minutes <= 0:
            return False
        elapsed = time.time() - self._last_activity
        if elapsed > self._auto_away_minutes * 60:
            self.set_status("away")
            return True
        return False

    def schedule_status(self, status: str, at_time: float) -> None:
        """Schedule a status change at a future time."""
        self._scheduled_status = {
            "status": status,
            "at_time": at_time,
            "created_at": time.time(),
        }

    def check_scheduled(self) -> Optional[str]:
        """Check if a scheduled status change is due."""
        if self._scheduled_status and time.time() >= self._scheduled_status["at_time"]:
            status = self._scheduled_status["status"]
            self._scheduled_status = None
            self.set_status(status)
            return status
        return None

    def list_statuses(self) -> List[Dict[str, Any]]:
        """List all available statuses."""
        result = []
        for status_key, profile in STATUS_PROFILES.items():
            info = dict(profile)
            info["key"] = status_key
            info["active"] = (status_key == self._status.value)
            result.append(info)
        return result

    def get_status_info(self) -> Dict[str, Any]:
        """Get comprehensive status information."""
        profile = dict(self.status_profile)
        profile["status"] = self._status.value
        profile["queued_messages_count"] = len(self._queued_messages)
        profile["last_activity"] = self._last_activity
        profile["idle_seconds"] = round(time.time() - self._last_activity)
        profile["scheduled"] = self._scheduled_status
        return profile

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get status change history."""
        return self._status_history[-limit:]

    # ──────────────────────────────────────────────────────────
    # Persistence
    # ──────────────────────────────────────────────────────────

    def _save_status(self) -> None:
        """Save current status to disk."""
        try:
            data = {
                "status": self._status.value,
                "last_activity": self._last_activity,
                "auto_away_minutes": self._auto_away_minutes,
                "queued_count": len(self._queued_messages),
            }
            os.makedirs(os.path.dirname(self._persistence_path), exist_ok=True)
            with open(self._persistence_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save status: {e}")

    def _load_status(self) -> None:
        """Load status from disk."""
        try:
            if os.path.exists(self._persistence_path):
                with open(self._persistence_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                try:
                    self._status = UserStatus(data.get("status", "open"))
                except ValueError:
                    self._status = UserStatus.OPEN
                self._auto_away_minutes = data.get("auto_away_minutes", 30)
        except Exception:
            self._status = UserStatus.OPEN


# Singleton
_status_manager: Optional[StatusManager] = None


def get_status_manager() -> StatusManager:
    """Get or create the global status manager."""
    global _status_manager
    if _status_manager is None:
        _status_manager = StatusManager()
    return _status_manager
