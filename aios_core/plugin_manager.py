"""AIOS Plugin Manager v4.2-alpha

Simple plugin system for extending AIOS functionality.
"""

import importlib
from typing import Any, Callable, Dict


class PluginManager:
    """Manages plugins for AIOS."""

    def __init__(self):
        self.plugins: Dict[str, Any] = {}
        self.hooks: Dict[str, list] = {}

    def register_plugin(self, name: str, plugin: Any):
        self.plugins[name] = plugin
        return True

    def load_plugin(self, module_path: str, name: str = None):
        """Dynamically load a plugin module."""
        try:
            module = importlib.import_module(module_path)
            plugin_name = name or module_path.split(".")[-1]
            self.plugins[plugin_name] = module
            return True
        except Exception as e:
            print(f"Failed to load plugin {module_path}: {e}")
            return False

    def register_hook(self, hook_name: str, callback: Callable):
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []
        self.hooks[hook_name].append(callback)

    def run_hook(self, hook_name: str, *args, **kwargs):
        results = []
        for callback in self.hooks.get(hook_name, []):
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                print(f"Hook {hook_name} failed: {e}")
        return results

    def list_plugins(self) -> list:
        return list(self.plugins.keys())

    def stats(self) -> dict:
        return {"total_plugins": len(self.plugins), "registered_hooks": len(self.hooks)}


# Global instance
plugin_manager = PluginManager()
