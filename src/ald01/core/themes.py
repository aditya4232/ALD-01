"""
ALD-01 Terminal Themes
Customizable color schemes for the terminal interface. Like Terminator.
Supports predefined and custom themes with full color control.
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from rich.theme import Theme
from rich.style import Style

from ald01 import CONFIG_DIR

logger = logging.getLogger("ald01.themes")


@dataclass
class TerminalTheme:
    """A complete terminal color theme."""
    name: str
    display_name: str
    description: str
    colors: Dict[str, str]  # Semantic color mappings
    is_dark: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "colors": self.colors,
            "is_dark": self.is_dark,
        }

    def to_rich_theme(self) -> Theme:
        """Convert to a Rich library Theme object."""
        styles = {}
        for key, value in self.colors.items():
            try:
                styles[key] = Style.parse(value)
            except Exception:
                pass
        return Theme(styles)


# ──────────────────────────────────────────────────────────────
# Built-in Themes
# ──────────────────────────────────────────────────────────────

BUILT_IN_THEMES: Dict[str, TerminalTheme] = {
    "cyberpunk": TerminalTheme(
        name="cyberpunk",
        display_name="🌆 Cyberpunk",
        description="Neon colors on dark background, sci-fi aesthetic",
        is_dark=True,
        colors={
            "primary": "bold bright_cyan",
            "secondary": "bright_magenta",
            "accent": "bold bright_yellow",
            "success": "bold bright_green",
            "warning": "bold yellow",
            "error": "bold bright_red",
            "info": "cyan",
            "dim": "bright_black",
            "muted": "grey50",
            "highlight": "bold reverse bright_cyan",
            "user_prompt": "bold bright_green",
            "ai_response": "bright_cyan",
            "code": "bright_yellow",
            "header": "bold bright_magenta",
            "border": "bright_blue",
            "status_online": "bold bright_green",
            "status_offline": "bold bright_red",
            "agent_label": "bold bright_magenta",
            "provider_label": "bold bright_cyan",
            "tool_label": "bold bright_green",
            "thinking": "italic bright_yellow",
            "banner": "bold bright_cyan",
        },
    ),
    "matrix": TerminalTheme(
        name="matrix",
        display_name="🟢 Matrix",
        description="Green-on-black hacker aesthetic",
        is_dark=True,
        colors={
            "primary": "bold green",
            "secondary": "bright_green",
            "accent": "bold bright_green",
            "success": "bold green",
            "warning": "bold yellow",
            "error": "bold red",
            "info": "green",
            "dim": "dark_green",
            "muted": "grey37",
            "highlight": "bold reverse green",
            "user_prompt": "bold bright_green",
            "ai_response": "green",
            "code": "bright_green",
            "header": "bold bright_green",
            "border": "green",
            "status_online": "bold bright_green",
            "status_offline": "bold red",
            "agent_label": "bold bright_green",
            "provider_label": "bold green",
            "tool_label": "bold bright_green",
            "thinking": "italic green",
            "banner": "bold bright_green",
        },
    ),
    "ocean": TerminalTheme(
        name="ocean",
        display_name="🌊 Ocean",
        description="Calm blue tones, professional feel",
        is_dark=True,
        colors={
            "primary": "bold bright_blue",
            "secondary": "bright_cyan",
            "accent": "bold cyan",
            "success": "bold bright_green",
            "warning": "bold yellow",
            "error": "bold bright_red",
            "info": "bright_blue",
            "dim": "grey50",
            "muted": "grey42",
            "highlight": "bold reverse bright_blue",
            "user_prompt": "bold bright_cyan",
            "ai_response": "bright_blue",
            "code": "bright_cyan",
            "header": "bold bright_blue",
            "border": "blue",
            "status_online": "bold bright_green",
            "status_offline": "bold red",
            "agent_label": "bold bright_blue",
            "provider_label": "bold cyan",
            "tool_label": "bold bright_cyan",
            "thinking": "italic bright_blue",
            "banner": "bold bright_blue",
        },
    ),
    "sunset": TerminalTheme(
        name="sunset",
        display_name="🌅 Sunset",
        description="Warm orange and red tones",
        is_dark=True,
        colors={
            "primary": "bold bright_red",
            "secondary": "bright_yellow",
            "accent": "bold yellow",
            "success": "bold bright_green",
            "warning": "bold bright_yellow",
            "error": "bold bright_red",
            "info": "gold1",
            "dim": "grey50",
            "muted": "grey42",
            "highlight": "bold reverse bright_red",
            "user_prompt": "bold bright_yellow",
            "ai_response": "bright_red",
            "code": "bright_yellow",
            "header": "bold bright_red",
            "border": "red",
            "status_online": "bold bright_green",
            "status_offline": "bold red",
            "agent_label": "bold bright_red",
            "provider_label": "bold bright_yellow",
            "tool_label": "bold yellow",
            "thinking": "italic bright_yellow",
            "banner": "bold bright_red",
        },
    ),
    "dracula": TerminalTheme(
        name="dracula",
        display_name="🧛 Dracula",
        description="Popular dark theme with purple accents",
        is_dark=True,
        colors={
            "primary": "bold bright_magenta",
            "secondary": "bright_cyan",
            "accent": "bold bright_green",
            "success": "bold bright_green",
            "warning": "bold bright_yellow",
            "error": "bold bright_red",
            "info": "bright_magenta",
            "dim": "grey50",
            "muted": "grey42",
            "highlight": "bold reverse bright_magenta",
            "user_prompt": "bold bright_green",
            "ai_response": "bright_magenta",
            "code": "bright_cyan",
            "header": "bold bright_magenta",
            "border": "magenta",
            "status_online": "bold bright_green",
            "status_offline": "bold bright_red",
            "agent_label": "bold bright_magenta",
            "provider_label": "bold bright_cyan",
            "tool_label": "bold bright_green",
            "thinking": "italic bright_magenta",
            "banner": "bold bright_magenta",
        },
    ),
    "nord": TerminalTheme(
        name="nord",
        display_name="❄️ Nord",
        description="Arctic, cool blue-grey palette",
        is_dark=True,
        colors={
            "primary": "bold bright_blue",
            "secondary": "bright_cyan",
            "accent": "bold bright_cyan",
            "success": "bold bright_green",
            "warning": "bold bright_yellow",
            "error": "bold bright_red",
            "info": "bright_blue",
            "dim": "grey62",
            "muted": "grey50",
            "highlight": "bold reverse bright_blue",
            "user_prompt": "bold bright_cyan",
            "ai_response": "bright_blue",
            "code": "bright_cyan",
            "header": "bold bright_blue",
            "border": "blue",
            "status_online": "bold bright_green",
            "status_offline": "bold bright_red",
            "agent_label": "bold bright_blue",
            "provider_label": "bold bright_cyan",
            "tool_label": "bold bright_green",
            "thinking": "italic bright_blue",
            "banner": "bold bright_cyan",
        },
    ),
    "terminal_green": TerminalTheme(
        name="terminal_green",
        display_name="💚 Terminal Classic",
        description="Classic green-on-black terminal",
        is_dark=True,
        colors={
            "primary": "green",
            "secondary": "bright_green",
            "accent": "bold green",
            "success": "bold green",
            "warning": "bold yellow",
            "error": "bold red",
            "info": "green",
            "dim": "dark_green",
            "muted": "grey37",
            "highlight": "bold reverse green",
            "user_prompt": "bold green",
            "ai_response": "green",
            "code": "bright_green",
            "header": "bold green",
            "border": "green",
            "status_online": "bold green",
            "status_offline": "bold red",
            "agent_label": "bold green",
            "provider_label": "bold green",
            "tool_label": "bold green",
            "thinking": "italic green",
            "banner": "bold green",
        },
    ),
    "light": TerminalTheme(
        name="light",
        display_name="☀️ Light",
        description="Light theme for bright environments",
        is_dark=False,
        colors={
            "primary": "bold blue",
            "secondary": "dark_blue",
            "accent": "bold dark_cyan",
            "success": "bold dark_green",
            "warning": "bold dark_orange",
            "error": "bold dark_red",
            "info": "blue",
            "dim": "grey50",
            "muted": "grey62",
            "highlight": "bold reverse blue",
            "user_prompt": "bold dark_blue",
            "ai_response": "blue",
            "code": "dark_cyan",
            "header": "bold dark_blue",
            "border": "blue",
            "status_online": "bold dark_green",
            "status_offline": "bold dark_red",
            "agent_label": "bold dark_blue",
            "provider_label": "bold dark_cyan",
            "tool_label": "bold dark_green",
            "thinking": "italic blue",
            "banner": "bold dark_blue",
        },
    ),
}


class ThemeManager:
    """
    Manages terminal color themes for ALD-01.
    Supports built-in themes, custom themes, and runtime switching.
    """

    def __init__(self):
        self._current_theme_name: str = "cyberpunk"
        self._themes: Dict[str, TerminalTheme] = dict(BUILT_IN_THEMES)
        self._persistence_path = os.path.join(CONFIG_DIR, "themes.json")
        self._load_custom_themes()
        self._load_current_theme()

    @property
    def current_theme(self) -> TerminalTheme:
        return self._themes.get(self._current_theme_name, BUILT_IN_THEMES["cyberpunk"])

    @property
    def current_theme_name(self) -> str:
        return self._current_theme_name

    def switch_theme(self, theme_name: str) -> TerminalTheme:
        """Switch to a different theme."""
        theme_name = theme_name.lower().strip()
        if theme_name not in self._themes:
            # Try partial match
            for key in self._themes:
                if theme_name in key or key in theme_name:
                    theme_name = key
                    break
            else:
                raise ValueError(
                    f"Unknown theme: '{theme_name}'. Available: {', '.join(self._themes.keys())}"
                )

        self._current_theme_name = theme_name
        self._save_current_theme()
        logger.info(f"Theme switched to: {self._themes[theme_name].display_name}")
        return self._themes[theme_name]

    def get_color(self, semantic_name: str) -> str:
        """Get a color by semantic name from the current theme."""
        return self.current_theme.colors.get(semantic_name, "white")

    def get_rich_theme(self) -> Theme:
        """Get current theme as Rich Theme object."""
        return self.current_theme.to_rich_theme()

    def create_custom_theme(
        self,
        name: str,
        display_name: str,
        description: str,
        colors: Dict[str, str],
        base_theme: str = "cyberpunk",
    ) -> TerminalTheme:
        """Create a custom theme, optionally based on an existing one."""
        # Start from base theme colors
        base = self._themes.get(base_theme, BUILT_IN_THEMES["cyberpunk"])
        merged_colors = dict(base.colors)
        merged_colors.update(colors)

        theme = TerminalTheme(
            name=name.lower(),
            display_name=display_name,
            description=description,
            colors=merged_colors,
            is_dark=True,
            metadata={"user_created": True, "base_theme": base_theme},
        )
        self._themes[name.lower()] = theme
        self._save_custom_themes()
        return theme

    def delete_custom_theme(self, name: str) -> bool:
        """Delete a custom theme."""
        name = name.lower()
        if name in BUILT_IN_THEMES:
            return False
        if name in self._themes:
            del self._themes[name]
            self._save_custom_themes()
            if self._current_theme_name == name:
                self._current_theme_name = "cyberpunk"
                self._save_current_theme()
            return True
        return False

    def list_themes(self) -> List[Dict[str, Any]]:
        """List all available themes."""
        result = []
        for name, theme in self._themes.items():
            info = theme.to_dict()
            info["active"] = (name == self._current_theme_name)
            info["built_in"] = name in BUILT_IN_THEMES
            result.append(info)
        return result

    def preview_theme(self, theme_name: str) -> Dict[str, str]:
        """Get a preview of a theme's colors."""
        theme = self._themes.get(theme_name)
        if theme:
            return theme.colors
        return {}

    # ──────────────────────────────────────────────────────────
    # Persistence
    # ──────────────────────────────────────────────────────────

    def _save_current_theme(self) -> None:
        try:
            data = self._load_persistence()
            data["current_theme"] = self._current_theme_name
            self._write_persistence(data)
        except Exception as e:
            logger.warning(f"Failed to save theme: {e}")

    def _load_current_theme(self) -> None:
        try:
            data = self._load_persistence()
            self._current_theme_name = data.get("current_theme", "cyberpunk")
            if self._current_theme_name not in self._themes:
                self._current_theme_name = "cyberpunk"
        except Exception:
            self._current_theme_name = "cyberpunk"

    def _save_custom_themes(self) -> None:
        try:
            data = self._load_persistence()
            custom = {}
            for name, theme in self._themes.items():
                if name not in BUILT_IN_THEMES:
                    custom[name] = theme.to_dict()
            data["custom_themes"] = custom
            self._write_persistence(data)
        except Exception as e:
            logger.warning(f"Failed to save custom themes: {e}")

    def _load_custom_themes(self) -> None:
        try:
            data = self._load_persistence()
            for name, theme_data in data.get("custom_themes", {}).items():
                self._themes[name] = TerminalTheme(
                    name=name,
                    display_name=theme_data.get("display_name", name),
                    description=theme_data.get("description", ""),
                    colors=theme_data.get("colors", {}),
                    is_dark=theme_data.get("is_dark", True),
                )
        except Exception:
            pass

    def _load_persistence(self) -> Dict[str, Any]:
        if os.path.exists(self._persistence_path):
            try:
                with open(self._persistence_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _write_persistence(self, data: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self._persistence_path), exist_ok=True)
        with open(self._persistence_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


# Singleton
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """Get or create the global theme manager."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager
