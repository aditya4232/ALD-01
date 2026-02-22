"""
ALD-01 Configuration Editor
Allows editing all ALD-01 configuration via API with validation,
without breaking the system.
"""

import os
import json
import time
import logging
from typing import Any, Dict, List, Optional

import yaml

from ald01 import CONFIG_DIR

logger = logging.getLogger("ald01.config_editor")


# All editable config keys with types and defaults
CONFIG_SCHEMA = {
    "brain_power": {
        "type": "int",
        "min": 1,
        "max": 10,
        "default": 5,
        "description": "AI reasoning power level (1=basic, 10=AGI)",
        "category": "core",
    },
    "default_provider": {
        "type": "str",
        "default": "groq",
        "options": ["groq", "cerebras", "ollama", "github_copilot", "openai", "auto"],
        "description": "Default AI provider",
        "category": "providers",
    },
    "default_model": {
        "type": "str",
        "default": "auto",
        "description": "Default AI model (or 'auto' for provider default)",
        "category": "providers",
    },
    "dashboard_host": {
        "type": "str",
        "default": "127.0.0.1",
        "description": "Dashboard server host",
        "category": "dashboard",
    },
    "dashboard_port": {
        "type": "int",
        "min": 1024,
        "max": 65535,
        "default": 7860,
        "description": "Dashboard server port",
        "category": "dashboard",
    },
    "enable_voice": {
        "type": "bool",
        "default": False,
        "description": "Enable voice responses (requires TTS package)",
        "category": "voice",
    },
    "voice_engine": {
        "type": "str",
        "default": "pyttsx3",
        "options": ["pyttsx3", "edge-tts", "coqui"],
        "description": "Text-to-speech engine",
        "category": "voice",
    },
    "voice_rate": {
        "type": "int",
        "min": 100,
        "max": 300,
        "default": 180,
        "description": "Voice speaking rate (words per minute)",
        "category": "voice",
    },
    "language": {
        "type": "str",
        "default": "en",
        "options": ["en", "hi", "hinglish"],
        "description": "Interface language",
        "category": "localization",
    },
    "autostart": {
        "type": "bool",
        "default": False,
        "description": "Start ALD-01 when computer boots",
        "category": "system",
    },
    "enable_notifications": {
        "type": "bool",
        "default": True,
        "description": "Enable desktop notifications",
        "category": "notifications",
    },
    "enable_telegram": {
        "type": "bool",
        "default": False,
        "description": "Enable Telegram bot notifications",
        "category": "notifications",
    },
    "telegram_bot_token": {
        "type": "str",
        "default": "",
        "description": "Telegram bot token (from @BotFather)",
        "category": "telegram",
        "sensitive": True,
    },
    "telegram_chat_id": {
        "type": "str",
        "default": "",
        "description": "Telegram chat ID for notifications",
        "category": "telegram",
    },
    "max_context_messages": {
        "type": "int",
        "min": 5,
        "max": 100,
        "default": 30,
        "description": "Max messages to include in context window",
        "category": "chat",
    },
    "streaming_enabled": {
        "type": "bool",
        "default": True,
        "description": "Enable streaming responses",
        "category": "chat",
    },
    "sandbox_timeout": {
        "type": "int",
        "min": 5,
        "max": 300,
        "default": 30,
        "description": "Code execution timeout (seconds)",
        "category": "sandbox",
    },
    "auto_backup_interval_hours": {
        "type": "int",
        "min": 1,
        "max": 168,
        "default": 6,
        "description": "Auto-backup interval in hours",
        "category": "system",
    },
    "max_backup_count": {
        "type": "int",
        "min": 3,
        "max": 50,
        "default": 20,
        "description": "Maximum number of backups to keep",
        "category": "system",
    },
    "theme": {
        "type": "str",
        "default": "cyberpunk",
        "options": ["cyberpunk", "matrix", "ocean", "sunset", "dracula", "nord", "classic", "light"],
        "description": "Terminal/UI theme",
        "category": "appearance",
    },
    "enable_learning": {
        "type": "bool",
        "default": True,
        "description": "Enable adaptive learning from interactions",
        "category": "ai",
    },
    "enable_brain_tracking": {
        "type": "bool",
        "default": True,
        "description": "Track skill and knowledge growth",
        "category": "ai",
    },
    "multi_model_strategy": {
        "type": "str",
        "default": "primary",
        "options": ["primary", "fastest", "consensus", "blend", "specialist"],
        "description": "Strategy for multi-model orchestration",
        "category": "ai",
    },
}


class ConfigEditor:
    """
    Safe configuration editor with validation.
    Changes are validated before saving, with automatic snapshots.
    """

    def __init__(self):
        self._config_path = os.path.join(CONFIG_DIR, "config.yaml")
        self._config: Dict[str, Any] = {}
        self._load()

    def get_all(self) -> Dict[str, Any]:
        """Get all config values with schema info."""
        result = {}
        for key, schema in CONFIG_SCHEMA.items():
            value = self._config.get(key, schema["default"])
            entry = {
                "value": value if not schema.get("sensitive") else ("***" if value else ""),
                "default": schema["default"],
                "type": schema["type"],
                "description": schema["description"],
                "category": schema["category"],
            }
            if "options" in schema:
                entry["options"] = schema["options"]
            if "min" in schema:
                entry["min"] = schema["min"]
            if "max" in schema:
                entry["max"] = schema["max"]
            result[key] = entry
        return result

    def get(self, key: str) -> Any:
        schema = CONFIG_SCHEMA.get(key)
        if not schema:
            return None
        return self._config.get(key, schema["default"])

    def set(self, key: str, value: Any) -> Dict[str, Any]:
        """Set a config value with validation."""
        schema = CONFIG_SCHEMA.get(key)
        if not schema:
            return {"success": False, "error": f"Unknown config key: {key}"}

        # Validate type
        expected_type = schema["type"]
        try:
            if expected_type == "int":
                value = int(value)
                if "min" in schema and value < schema["min"]:
                    return {"success": False, "error": f"Value must be >= {schema['min']}"}
                if "max" in schema and value > schema["max"]:
                    return {"success": False, "error": f"Value must be <= {schema['max']}"}
            elif expected_type == "bool":
                if isinstance(value, str):
                    value = value.lower() in ("true", "1", "yes")
                value = bool(value)
            elif expected_type == "str":
                value = str(value)
                if "options" in schema and value not in schema["options"]:
                    return {"success": False, "error": f"Must be one of: {schema['options']}"}
        except (ValueError, TypeError) as e:
            return {"success": False, "error": f"Invalid value: {e}"}

        # Create snapshot before change
        try:
            from ald01.core.revert import get_revert_manager
            get_revert_manager().create_snapshot(f"config_{key}")
        except Exception:
            pass

        self._config[key] = value
        self._save()
        return {"success": True, "key": key, "value": value}

    def set_multiple(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Set multiple config values."""
        results = {}
        for key, value in updates.items():
            results[key] = self.set(key, value)
        return results

    def reset_key(self, key: str) -> Dict[str, Any]:
        """Reset a key to default."""
        schema = CONFIG_SCHEMA.get(key)
        if not schema:
            return {"success": False, "error": f"Unknown key: {key}"}
        return self.set(key, schema["default"])

    def reset_all(self) -> Dict[str, Any]:
        """Reset all config to defaults."""
        try:
            from ald01.core.revert import get_revert_manager
            get_revert_manager().create_snapshot("config_reset_all")
        except Exception:
            pass

        self._config = {}
        self._save()
        return {"success": True, "message": "All settings reset to defaults"}

    def get_categories(self) -> Dict[str, List[str]]:
        """Get config keys grouped by category."""
        categories: Dict[str, List[str]] = {}
        for key, schema in CONFIG_SCHEMA.items():
            cat = schema["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(key)
        return categories

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            with open(self._config_path, "w") as f:
                yaml.dump(self._config, f, default_flow_style=False)
        except Exception as e:
            logger.warning(f"Config save failed: {e}")

    def _load(self) -> None:
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path) as f:
                    self._config = yaml.safe_load(f) or {}
        except Exception:
            self._config = {}


_config_editor: Optional[ConfigEditor] = None

def get_config_editor() -> ConfigEditor:
    global _config_editor
    if _config_editor is None:
        _config_editor = ConfigEditor()
    return _config_editor
