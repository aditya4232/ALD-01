"""
ALD-01 Session Manager
Handles dashboard authentication, session tokens, and user preferences.
Supports local-only password-less sessions with optional PIN protection.
"""

import os
import json
import time
import hmac
import hashlib
import secrets
import logging
from typing import Any, Dict, List, Optional

from ald01 import CONFIG_DIR

logger = logging.getLogger("ald01.session")


class Session:
    """Represents an active dashboard session."""

    __slots__ = (
        "session_id", "created_at", "last_active",
        "ip_address", "user_agent", "preferences",
        "is_authenticated", "auth_level",
    )

    def __init__(self, session_id: str, ip: str = "127.0.0.1", user_agent: str = ""):
        self.session_id = session_id
        self.created_at = time.time()
        self.last_active = time.time()
        self.ip_address = ip
        self.user_agent = user_agent
        self.preferences: Dict[str, Any] = {}
        self.is_authenticated = True
        self.auth_level = "local"

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    @property
    def idle_seconds(self) -> float:
        return time.time() - self.last_active

    def touch(self) -> None:
        self.last_active = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id[:8] + "...",
            "created_at": self.created_at,
            "last_active": self.last_active,
            "age_seconds": round(self.age_seconds),
            "idle_seconds": round(self.idle_seconds),
            "ip_address": self.ip_address,
            "auth_level": self.auth_level,
            "is_authenticated": self.is_authenticated,
        }


class UserPreferences:
    """Persistent user preferences for the dashboard."""

    DEFAULTS = {
        "theme": "cyberpunk",
        "language": "en",
        "font_size": 14,
        "sidebar_collapsed": False,
        "auto_scroll": True,
        "sound_enabled": False,
        "notification_enabled": True,
        "code_wrap": True,
        "show_timestamps": True,
        "compact_mode": False,
        "default_model": "",
        "max_history": 100,
        "auto_save": True,
        "keyboard_shortcuts": True,
        "animations_enabled": True,
        "high_contrast": False,
        "monospace_font": "JetBrains Mono",
        "ui_font": "Inter",
    }

    def __init__(self):
        self._prefs: Dict[str, Any] = dict(self.DEFAULTS)
        self._path = os.path.join(CONFIG_DIR, "preferences.json")
        self._load()

    def get(self, key: str, default: Any = None) -> Any:
        return self._prefs.get(key, default or self.DEFAULTS.get(key))

    def set(self, key: str, value: Any) -> None:
        if key in self.DEFAULTS:
            expected_type = type(self.DEFAULTS[key])
            if expected_type and not isinstance(value, expected_type):
                try:
                    value = expected_type(value)
                except (ValueError, TypeError):
                    return
        self._prefs[key] = value
        self._save()

    def set_multiple(self, updates: Dict[str, Any]) -> None:
        for key, value in updates.items():
            self.set(key, value)

    def get_all(self) -> Dict[str, Any]:
        return dict(self._prefs)

    def reset(self) -> None:
        self._prefs = dict(self.DEFAULTS)
        self._save()

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._prefs, f, indent=2)
        except Exception as e:
            logger.warning(f"Preferences save failed: {e}")

    def _load(self) -> None:
        try:
            if os.path.exists(self._path):
                with open(self._path, encoding="utf-8") as f:
                    loaded = json.load(f)
                # Merge with defaults (fill missing keys)
                for key, default in self.DEFAULTS.items():
                    if key not in loaded:
                        loaded[key] = default
                self._prefs = loaded
        except Exception:
            pass


class SessionManager:
    """
    Manages dashboard sessions and authentication.

    Features:
    - Token-based sessions
    - Optional PIN protection
    - Session timeout and idle expiry
    - Multi-session tracking
    - User preference management
    - Login attempt tracking
    """

    SESSION_TIMEOUT_HOURS = 24
    IDLE_TIMEOUT_MINUTES = 120
    MAX_SESSIONS = 10
    MAX_LOGIN_ATTEMPTS = 5

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._pin_hash: Optional[str] = None
        self._login_attempts: Dict[str, List[float]] = {}
        self._preferences = UserPreferences()
        self._config_path = os.path.join(CONFIG_DIR, "session_config.json")
        self._load_config()

    def create_session(
        self, ip: str = "127.0.0.1", user_agent: str = "", pin: str = "",
    ) -> Dict[str, Any]:
        """Create a new dashboard session."""
        # Check if PIN is required
        if self._pin_hash:
            if not pin:
                return {
                    "success": False,
                    "error": "PIN required",
                    "requires_pin": True,
                }
            if not self._verify_pin(pin):
                self._record_login_attempt(ip, success=False)
                attempts = len(self._get_recent_attempts(ip))
                remaining = max(0, self.MAX_LOGIN_ATTEMPTS - attempts)
                return {
                    "success": False,
                    "error": f"Invalid PIN. {remaining} attempts remaining.",
                    "remaining_attempts": remaining,
                }

            # Check if IP is locked out
            if self._is_locked_out(ip):
                return {
                    "success": False,
                    "error": "Too many failed attempts. Try again in 15 minutes.",
                }

        # Clean expired sessions
        self._cleanup_expired()

        # Check session limit
        if len(self._sessions) >= self.MAX_SESSIONS:
            oldest = min(self._sessions.values(), key=lambda s: s.last_active)
            del self._sessions[oldest.session_id]

        # Create session
        session_id = secrets.token_urlsafe(32)
        session = Session(session_id, ip, user_agent)
        if self._pin_hash:
            session.auth_level = "pin"
        self._sessions[session_id] = session

        self._record_login_attempt(ip, success=True)
        logger.info(f"Session created: {session_id[:8]}... from {ip}")

        return {
            "success": True,
            "session_id": session_id,
            "auth_level": session.auth_level,
            "preferences": self._preferences.get_all(),
        }

    def validate_session(self, session_id: str) -> Optional[Session]:
        """Validate and refresh a session."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Check timeout
        if session.age_seconds > self.SESSION_TIMEOUT_HOURS * 3600:
            del self._sessions[session_id]
            return None

        # Check idle timeout
        if session.idle_seconds > self.IDLE_TIMEOUT_MINUTES * 60:
            del self._sessions[session_id]
            return None

        session.touch()
        return session

    def end_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def end_all_sessions(self) -> int:
        count = len(self._sessions)
        self._sessions.clear()
        return count

    def set_pin(self, pin: str) -> bool:
        """Set or update the dashboard PIN."""
        if len(pin) < 4:
            return False
        self._pin_hash = hashlib.sha256(pin.encode()).hexdigest()
        self._save_config()
        logger.info("Dashboard PIN updated")
        return True

    def remove_pin(self) -> None:
        self._pin_hash = None
        self._save_config()
        logger.info("Dashboard PIN removed")

    def has_pin(self) -> bool:
        return self._pin_hash is not None

    def list_sessions(self) -> List[Dict[str, Any]]:
        self._cleanup_expired()
        return [s.to_dict() for s in self._sessions.values()]

    def get_preferences(self) -> Dict[str, Any]:
        return self._preferences.get_all()

    def update_preferences(self, updates: Dict[str, Any]) -> None:
        self._preferences.set_multiple(updates)

    def reset_preferences(self) -> None:
        self._preferences.reset()

    def get_stats(self) -> Dict[str, Any]:
        self._cleanup_expired()
        return {
            "active_sessions": len(self._sessions),
            "pin_enabled": self.has_pin(),
            "session_timeout_hours": self.SESSION_TIMEOUT_HOURS,
            "idle_timeout_minutes": self.IDLE_TIMEOUT_MINUTES,
        }

    # ── Internal helpers ──

    def _verify_pin(self, pin: str) -> bool:
        if not self._pin_hash:
            return True
        computed = hashlib.sha256(pin.encode()).hexdigest()
        return hmac.compare_digest(computed, self._pin_hash)

    def _record_login_attempt(self, ip: str, success: bool) -> None:
        if ip not in self._login_attempts:
            self._login_attempts[ip] = []
        if not success:
            self._login_attempts[ip].append(time.time())
            # Keep only recent attempts
            self._login_attempts[ip] = self._login_attempts[ip][-20:]

    def _get_recent_attempts(self, ip: str) -> List[float]:
        cutoff = time.time() - 900  # 15 minutes
        attempts = self._login_attempts.get(ip, [])
        return [t for t in attempts if t > cutoff]

    def _is_locked_out(self, ip: str) -> bool:
        return len(self._get_recent_attempts(ip)) >= self.MAX_LOGIN_ATTEMPTS

    def _cleanup_expired(self) -> None:
        expired = [
            sid for sid, s in self._sessions.items()
            if s.age_seconds > self.SESSION_TIMEOUT_HOURS * 3600
            or s.idle_seconds > self.IDLE_TIMEOUT_MINUTES * 60
        ]
        for sid in expired:
            del self._sessions[sid]

    def _save_config(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            data = {"pin_hash": self._pin_hash}
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Session config save failed: {e}")

    def _load_config(self) -> None:
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, encoding="utf-8") as f:
                    data = json.load(f)
                self._pin_hash = data.get("pin_hash")
        except Exception:
            pass


_session_mgr: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    global _session_mgr
    if _session_mgr is None:
        _session_mgr = SessionManager()
    return _session_mgr
