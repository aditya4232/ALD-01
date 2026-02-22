"""
ALD-01 Plugin System
Extensible skill/plugin framework for adding capabilities to ALD-01.
Plugins are Python modules that register tools, agents, or processors.
"""

import os
import sys
import time
import json
import logging
import importlib
import importlib.util
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field

from ald01 import CONFIG_DIR, DATA_DIR

logger = logging.getLogger("ald01.plugins")


@dataclass
class Plugin:
    """Represents a loaded plugin."""
    name: str
    display_name: str
    version: str
    description: str
    author: str
    enabled: bool = True
    loaded: bool = False
    module: Any = None
    hooks: Dict[str, Callable] = field(default_factory=dict)
    tools: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    loaded_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "enabled": self.enabled,
            "loaded": self.loaded,
            "hooks": list(self.hooks.keys()),
            "tools": self.tools,
            "error": self.error,
        }


class PluginManager:
    """
    Manages ALD-01 plugins/skills.

    Plugin structure:
    ~/.ald01/plugins/
        my_plugin/
            __init__.py    # Must define: name, version, description
            plugin.py      # Must define: setup(manager), teardown(manager)

    Hook system allows plugins to:
    - Register custom tools
    - Add pre/post processing for queries
    - Add custom commands
    - Extend agent capabilities
    """

    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._plugin_dir = os.path.join(CONFIG_DIR, "plugins")
        self._persistence_path = os.path.join(CONFIG_DIR, "plugins_config.json")
        os.makedirs(self._plugin_dir, exist_ok=True)
        self._load_plugin_configs()

    def discover_plugins(self) -> List[str]:
        """Discover available plugins in the plugins directory."""
        found = []
        if not os.path.exists(self._plugin_dir):
            return found

        for item in os.listdir(self._plugin_dir):
            plugin_path = os.path.join(self._plugin_dir, item)
            if os.path.isdir(plugin_path):
                init_file = os.path.join(plugin_path, "__init__.py")
                plugin_file = os.path.join(plugin_path, "plugin.py")
                if os.path.exists(init_file) or os.path.exists(plugin_file):
                    found.append(item)

        return found

    def load_plugin(self, name: str) -> bool:
        """Load a single plugin by name."""
        plugin_path = os.path.join(self._plugin_dir, name)
        plugin_file = os.path.join(plugin_path, "plugin.py")
        init_file = os.path.join(plugin_path, "__init__.py")

        entry = plugin_file if os.path.exists(plugin_file) else init_file
        if not os.path.exists(entry):
            logger.warning(f"Plugin '{name}' not found at {plugin_path}")
            return False

        try:
            # Load module
            spec = importlib.util.spec_from_file_location(f"ald01_plugin_{name}", entry)
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot create module spec for {entry}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Extract metadata
            plugin = Plugin(
                name=name,
                display_name=getattr(module, "DISPLAY_NAME", name),
                version=getattr(module, "VERSION", "0.1.0"),
                description=getattr(module, "DESCRIPTION", ""),
                author=getattr(module, "AUTHOR", ""),
                module=module,
                loaded=True,
                loaded_at=time.time(),
            )

            # Call setup function
            setup_fn = getattr(module, "setup", None)
            if setup_fn:
                setup_fn(self)

            self._plugins[name] = plugin
            logger.info(f"Plugin loaded: {plugin.display_name} v{plugin.version}")
            return True

        except Exception as e:
            logger.error(f"Failed to load plugin '{name}': {e}")
            self._plugins[name] = Plugin(
                name=name,
                display_name=name,
                version="unknown",
                description="",
                author="",
                loaded=False,
                error=str(e),
            )
            return False

    def unload_plugin(self, name: str) -> bool:
        """Unload a plugin."""
        plugin = self._plugins.get(name)
        if not plugin or not plugin.loaded:
            return False

        try:
            teardown = getattr(plugin.module, "teardown", None)
            if teardown:
                teardown(self)

            # Remove hooks
            for hook_name in list(plugin.hooks.keys()):
                self.remove_hook(hook_name, plugin.hooks[hook_name])

            plugin.loaded = False
            plugin.module = None
            logger.info(f"Plugin unloaded: {name}")
            return True

        except Exception as e:
            logger.error(f"Error unloading plugin '{name}': {e}")
            return False

    def load_all(self) -> Dict[str, bool]:
        """Discover and load all plugins."""
        results = {}
        for name in self.discover_plugins():
            # Check if disabled in config
            cfg = self._get_plugin_config(name)
            if not cfg.get("enabled", True):
                results[name] = False
                continue
            results[name] = self.load_plugin(name)
        return results

    def register_hook(self, hook_name: str, callback: Callable, plugin_name: str = "") -> None:
        """Register a hook callback."""
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(callback)

        if plugin_name and plugin_name in self._plugins:
            self._plugins[plugin_name].hooks[hook_name] = callback

    def remove_hook(self, hook_name: str, callback: Callable) -> None:
        """Remove a hook callback."""
        if hook_name in self._hooks:
            self._hooks[hook_name] = [h for h in self._hooks[hook_name] if h != callback]

    async def run_hook(self, hook_name: str, **kwargs) -> List[Any]:
        """Run all callbacks registered for a hook."""
        results = []
        for callback in self._hooks.get(hook_name, []):
            try:
                import asyncio
                if asyncio.iscoroutinefunction(callback):
                    result = await callback(**kwargs)
                else:
                    result = callback(**kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Hook '{hook_name}' callback error: {e}")
        return results

    def register_tool(self, name: str, func: Callable, description: str = "", plugin_name: str = "") -> None:
        """Register a custom tool from a plugin."""
        if plugin_name and plugin_name in self._plugins:
            self._plugins[plugin_name].tools.append(name)
        logger.info(f"Tool registered by plugin: {name}")

    def enable_plugin(self, name: str) -> bool:
        """Enable a plugin."""
        self._set_plugin_config(name, {"enabled": True})
        if name in self._plugins:
            self._plugins[name].enabled = True
            if not self._plugins[name].loaded:
                return self.load_plugin(name)
        return True

    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin."""
        self._set_plugin_config(name, {"enabled": False})
        if name in self._plugins:
            self._plugins[name].enabled = False
            if self._plugins[name].loaded:
                self.unload_plugin(name)
        return True

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all known plugins."""
        # Include discovered but not loaded
        all_names = set(self._plugins.keys()) | set(self.discover_plugins())
        result = []
        for name in sorted(all_names):
            if name in self._plugins:
                result.append(self._plugins[name].to_dict())
            else:
                result.append({"name": name, "loaded": False, "enabled": True, "description": "Not loaded"})
        return result

    def get_plugin(self, name: str) -> Optional[Dict[str, Any]]:
        """Get plugin info."""
        p = self._plugins.get(name)
        return p.to_dict() if p else None

    def _get_plugin_config(self, name: str) -> Dict[str, Any]:
        try:
            if os.path.exists(self._persistence_path):
                with open(self._persistence_path, "r") as f:
                    data = json.load(f)
                return data.get("plugins", {}).get(name, {})
        except Exception:
            pass
        return {}

    def _set_plugin_config(self, name: str, config: Dict[str, Any]) -> None:
        try:
            data = {}
            if os.path.exists(self._persistence_path):
                with open(self._persistence_path, "r") as f:
                    data = json.load(f)
            if "plugins" not in data:
                data["plugins"] = {}
            data["plugins"][name] = {**data["plugins"].get(name, {}), **config}
            with open(self._persistence_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save plugin config: {e}")

    def _load_plugin_configs(self) -> None:
        """Load plugin configs from disk."""
        pass  # Configs loaded on demand


_plugin_manager: Optional[PluginManager] = None

def get_plugin_manager() -> PluginManager:
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
