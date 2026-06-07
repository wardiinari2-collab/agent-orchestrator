"""Plugin system — load, register, and execute plugin methods."""
from __future__ import annotations
import importlib
import inspect
import logging
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


class Plugin:
    """Base class for plugins. Subclass and implement methods."""

    name: str = "base"
    description: str = ""

    def setup(self, config: dict) -> None:
        """Called once when plugin is loaded. Override for init logic."""
        pass

    def teardown(self) -> None:
        """Called on shutdown. Override for cleanup."""
        pass


class PluginManager:
    """Discovers, loads, and manages plugins."""

    def __init__(self):
        self._plugins: dict[str, Plugin] = {}
        self._methods: dict[str, Callable] = {}  # "plugin.method" -> callable

    def register(self, plugin: Plugin) -> None:
        """Register a plugin instance."""
        name = plugin.name
        if name in self._plugins:
            logger.warning(f"Plugin '{name}' already registered, overwriting")
        self._plugins[name] = plugin
        for attr_name in dir(plugin):
            if attr_name.startswith("_"):
                continue
            attr = getattr(plugin, attr_name)
            if callable(attr) and not isinstance(attr, type):
                key = f"{name}.{attr_name}"
                self._methods[key] = attr
        logger.info(f"Registered plugin '{name}' with {sum(1 for k in self._methods if k.startswith(name + '.'))} methods")

    def load_directory(self, path: Path, config: dict | None = None) -> int:
        """Load all plugin .py files from a directory."""
        loaded = 0
        if not path.exists():
            logger.warning(f"Plugin directory not found: {path}")
            return 0
        for py_file in sorted(path.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, Plugin) and attr is not Plugin:
                        instance = attr()
                        plugin_config = (config or {}).get(instance.name, {})
                        instance.setup(plugin_config)
                        self.register(instance)
                        loaded += 1
            except Exception as e:
                logger.error(f"Failed to load plugin {py_file.name}: {e}")
        return loaded

    def get_method(self, key: str) -> Callable | None:
        """Get method by 'plugin.method' key."""
        return self._methods.get(key)

    def call(self, key: str, **kwargs) -> Any:
        """Call a plugin method by key."""
        method = self._methods.get(key)
        if not method:
            raise KeyError(f"Plugin method '{key}' not found")
        return method(**kwargs)

    def list_plugins(self) -> list[dict]:
        """List all registered plugins and their methods."""
        result = []
        for name, plugin in self._plugins.items():
            methods = [k.split(".", 1)[1] for k in self._methods if k.startswith(name + ".")]
            result.append({
                "name": name,
                "description": plugin.description,
                "methods": methods,
            })
        return result

    def shutdown(self) -> None:
        """Call teardown on all plugins."""
        for plugin in self._plugins.values():
            try:
                plugin.teardown()
            except Exception as e:
                logger.error(f"Error in {plugin.name}.teardown(): {e}")
