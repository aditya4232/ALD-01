"""
ALD-01 Configuration Management
Handles YAML-based configuration with environment variable overrides.
"""

import os
import yaml
import copy
from typing import Any, Optional, Dict, List
from pathlib import Path

from ald01 import CONFIG_DIR

DEFAULT_CONFIG_PATH = os.path.join(CONFIG_DIR, "config.yaml")

# ──────────────────────────────────────────────────────────────
# Default Configuration
# ──────────────────────────────────────────────────────────────

DEFAULT_CONFIG: Dict[str, Any] = {
    "system": {
        "name": "ALD-01",
        "version": "1.0.0",
        "data_dir": os.path.join(CONFIG_DIR, "data"),
        "log_level": "info",
        "port": 7860,
        "host": "127.0.0.1",
    },
    "reasoning": {
        "enabled": True,
        "brain_power": 5,
        "interval": 30,
        "model": "auto",
        "max_thoughts": 10,
        "background_enabled": False,
    },
    "agents": {
        "code_gen": {
            "enabled": True,
            "model": "auto",
            "temperature": 0.3,
            "max_tokens": 4096,
            "system_prompt": "You are an expert code generation agent. Write clean, efficient, well-documented code.",
        },
        "debug": {
            "enabled": True,
            "model": "auto",
            "temperature": 0.2,
            "max_tokens": 4096,
            "auto_fix": False,
            "explain_level": "detailed",
            "system_prompt": "You are an expert debugging agent. Analyze errors, find root causes, and suggest fixes.",
        },
        "review": {
            "enabled": True,
            "model": "auto",
            "temperature": 0.2,
            "max_tokens": 4096,
            "strictness": 4,
            "security_first": True,
            "system_prompt": "You are an expert code review agent. Analyze code quality, security, and best practices.",
        },
        "security": {
            "enabled": True,
            "model": "auto",
            "temperature": 0.1,
            "max_tokens": 4096,
            "audit_mode": "full",
            "auto_disable": False,
            "system_prompt": "You are a cybersecurity expert agent. Identify vulnerabilities, assess risks, and recommend mitigations.",
        },
        "general": {
            "enabled": True,
            "model": "auto",
            "temperature": 0.7,
            "max_tokens": 4096,
            "creativity": 0.7,
            "search_enabled": False,
            "system_prompt": "You are a versatile AI assistant. Help with any task across all domains.",
        },
    },
    "providers": {
        "ollama": {
            "enabled": True,
            "host": "http://localhost:11434",
            "default_model": "llama3.2",
            "timeout": 120,
            "priority": 1,
        },
        "openai": {
            "enabled": False,
            "api_key": "",
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4o-mini",
            "timeout": 60,
            "priority": 2,
        },
        "anthropic": {
            "enabled": False,
            "api_key": "",
            "base_url": "https://api.anthropic.com",
            "default_model": "claude-3-5-sonnet-20241022",
            "timeout": 60,
            "priority": 3,
        },
        "custom": [],
    },
    "telegram": {
        "enabled": False,
        "token": "",
        "chat_ids": [],
        "webhook_url": "",
    },
    "dashboard": {
        "enabled": True,
        "port": 7860,
        "host": "127.0.0.1",
        "open_browser": True,
    },
    "memory": {
        "enabled": True,
        "db_path": os.path.join(CONFIG_DIR, "memory", "ald01.db"),
        "max_context_messages": 50,
        "auto_summarize": True,
        "retention_days": 90,
    },
    "autostart": {
        "enabled": False,
        "gateway": True,
        "dashboard": True,
    },
    "tools": {
        "file_read": {"enabled": True, "sandboxed": True},
        "file_write": {"enabled": True, "sandboxed": True, "allowed_dirs": []},
        "code_execute": {"enabled": False, "sandboxed": True, "timeout": 30},
        "web_search": {"enabled": False},
        "http_request": {"enabled": True, "timeout": 30},
        "terminal": {"enabled": False, "sandboxed": True},
    },
}


# ──────────────────────────────────────────────────────────────
# Configuration Manager
# ──────────────────────────────────────────────────────────────

class ConfigManager:
    """Manages ALD-01 configuration with file persistence and env overrides."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._config: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load configuration from file, falling back to defaults."""
        self._config = copy.deepcopy(DEFAULT_CONFIG)

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    file_config = yaml.safe_load(f) or {}
                self._deep_merge(self._config, file_config)
            except Exception as e:
                print(f"[ALD-01] Warning: Could not load config from {self.config_path}: {e}")
        else:
            self.save()  # Create default config file

        # Apply environment variable overrides
        self._apply_env_overrides()

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Recursively merge override into base dict."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides (ALD01_* prefix)."""
        env_mappings = {
            "ALD01_PORT": ("system", "port", int),
            "ALD01_HOST": ("system", "host", str),
            "ALD01_LOG_LEVEL": ("system", "log_level", str),
            "ALD01_BRAIN_POWER": ("reasoning", "brain_power", int),
            "ALD01_OLLAMA_HOST": ("providers", "ollama", "host"),
            "ALD01_OPENAI_KEY": ("providers", "openai", "api_key"),
            "ALD01_OPENAI_BASE_URL": ("providers", "openai", "base_url"),
            "ALD01_ANTHROPIC_KEY": ("providers", "anthropic", "api_key"),
            "ALD01_TELEGRAM_TOKEN": ("telegram", "token", str),
        }

        for env_key, path in env_mappings.items():
            value = os.environ.get(env_key)
            if value is not None:
                self._set_nested(path[:-1] if callable(path[-1]) else path, value)

    def _set_nested(self, keys: tuple, value: Any) -> None:
        """Set a nested configuration value."""
        d = self._config
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value

    def get(self, *keys: str, default: Any = None) -> Any:
        """Get a nested configuration value. Usage: config.get('system', 'port')"""
        d = self._config
        for key in keys:
            if isinstance(d, dict):
                d = d.get(key)
                if d is None:
                    return default
            else:
                return default
        return d

    def set(self, *args: Any) -> None:
        """Set a nested configuration value. Last arg is the value."""
        if len(args) < 2:
            raise ValueError("Need at least a key and a value")

        keys = args[:-1]
        value = args[-1]

        d = self._config
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value

    def save(self) -> None:
        """Save current configuration to file."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, default_flow_style=False, sort_keys=False, indent=2)

    def reset(self) -> None:
        """Reset to default configuration."""
        self._config = copy.deepcopy(DEFAULT_CONFIG)
        self.save()

    def to_dict(self) -> Dict[str, Any]:
        """Return full config as dict."""
        return copy.deepcopy(self._config)

    def get_provider_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific provider."""
        providers = self._config.get("providers", {})
        if name == "custom":
            return providers.get("custom", [])
        return providers.get(name)

    def get_agent_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific agent."""
        return self._config.get("agents", {}).get(name)

    def get_active_providers(self) -> List[Dict[str, Any]]:
        """Get list of enabled providers sorted by priority."""
        providers = []
        for name, conf in self._config.get("providers", {}).items():
            if name == "custom":
                for custom_p in conf:
                    if custom_p.get("enabled", False):
                        providers.append({"name": custom_p.get("name", "custom"), **custom_p})
            elif isinstance(conf, dict) and conf.get("enabled", False):
                providers.append({"name": name, **conf})

        return sorted(providers, key=lambda p: p.get("priority", 99))

    def get_active_agents(self) -> List[str]:
        """Get list of enabled agent names."""
        return [
            name
            for name, conf in self._config.get("agents", {}).items()
            if conf.get("enabled", False)
        ]

    @property
    def brain_power(self) -> int:
        """Get current brain power level (1-10)."""
        return self.get("reasoning", "brain_power", default=5)

    @brain_power.setter
    def brain_power(self, level: int) -> None:
        """Set brain power level (clamped 1-10)."""
        level = max(1, min(10, level))
        self.set("reasoning", "brain_power", level)


# ──────────────────────────────────────────────────────────────
# Brain Power Presets
# ──────────────────────────────────────────────────────────────

BRAIN_POWER_PRESETS = {
    1: {
        "name": "Basic",
        "reasoning_depth": 1,
        "context_window": 4096,
        "tool_access": "none",
        "autonomous": False,
        "creativity": 0.2,
        "response_detail": "brief",
        "description": "Simple Q&A, minimal reasoning",
    },
    2: {
        "name": "Assistant",
        "reasoning_depth": 1,
        "context_window": 4096,
        "tool_access": "basic",
        "autonomous": False,
        "creativity": 0.3,
        "response_detail": "brief",
        "description": "Standard helpful responses",
    },
    3: {
        "name": "Capable",
        "reasoning_depth": 2,
        "context_window": 8192,
        "tool_access": "basic",
        "autonomous": False,
        "creativity": 0.4,
        "response_detail": "standard",
        "description": "Moderate reasoning depth",
    },
    4: {
        "name": "Proficient",
        "reasoning_depth": 3,
        "context_window": 16384,
        "tool_access": "standard",
        "autonomous": False,
        "creativity": 0.5,
        "response_detail": "standard",
        "description": "Complex problem solving",
    },
    5: {
        "name": "Advanced",
        "reasoning_depth": 4,
        "context_window": 32768,
        "tool_access": "standard",
        "autonomous": True,
        "creativity": 0.6,
        "response_detail": "detailed",
        "description": "Deep analysis and planning",
    },
    6: {
        "name": "Expert",
        "reasoning_depth": 5,
        "context_window": 32768,
        "tool_access": "standard",
        "autonomous": True,
        "creativity": 0.7,
        "response_detail": "detailed",
        "description": "Specialized reasoning",
    },
    7: {
        "name": "Master",
        "reasoning_depth": 6,
        "context_window": 65536,
        "tool_access": "full",
        "autonomous": True,
        "creativity": 0.7,
        "response_detail": "detailed",
        "description": "Multi-domain synthesis",
    },
    8: {
        "name": "Superior",
        "reasoning_depth": 7,
        "context_window": 65536,
        "tool_access": "full",
        "autonomous": True,
        "creativity": 0.8,
        "response_detail": "exhaustive",
        "description": "Advanced AGI reasoning",
    },
    9: {
        "name": "Near-AGI",
        "reasoning_depth": 8,
        "context_window": 128000,
        "tool_access": "full",
        "autonomous": True,
        "creativity": 0.85,
        "response_detail": "exhaustive",
        "description": "Human-level reasoning",
    },
    10: {
        "name": "AGI",
        "reasoning_depth": 10,
        "context_window": 128000,
        "tool_access": "full",
        "autonomous": True,
        "creativity": 0.9,
        "response_detail": "exhaustive",
        "description": "Full autonomous reasoning",
    },
}


def get_brain_power_preset(level: int) -> Dict[str, Any]:
    """Get the brain power preset configuration for a given level."""
    level = max(1, min(10, level))
    return BRAIN_POWER_PRESETS.get(level, BRAIN_POWER_PRESETS[5])


# Singleton config instance
_config_instance: Optional[ConfigManager] = None


def get_config(config_path: Optional[str] = None) -> ConfigManager:
    """Get or create the global config manager instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager(config_path)
    return _config_instance
