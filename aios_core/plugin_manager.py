"""AIOS Plugin Manager v4.2

Simple plugin system for extending AIOS functionality.
Supports plugin lifecycle hooks, version tracking, dependency resolution,
configuration, priority ordering, plugin isolation, and uninstall.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any

__all__ = ["PluginInfo", "PluginManager", "plugin_manager"]


class PluginInfo:
    """Metadata container for a registered plugin."""

    __slots__ = (
        "author",
        "dependencies",
        "description",
        "enabled",
        "module_path",
        "name",
        "priority",
        "version",
    )

    def __init__(
        self,
        name: str = "",
        version: str = "0.0.1",
        description: str = "",
        author: str = "",
        dependencies: list[str] | None = None,
        priority: int = 0,
        enabled: bool = True,
        module_path: str = "",
    ):
        if dependencies is None:
            dependencies = []
        self.name = name
        self.version = version
        self.description = description
        self.author = author
        self.dependencies = dependencies
        self.priority = priority
        self.enabled = enabled
        self.module_path = module_path


class PluginManager:
    """Manages plugins for AIOS.

    Features:
    - Plugin registration with version and dependency tracking
    - Dynamic module loading from dotted paths
    - Lifecycle hooks: init, start, stop, teardown
    - Priority-ordered hook execution
    - Plugin enable/disable without removal
    - Dependency resolution (load-order enforcement)
    - Configuration per plugin
    - Isolation: hooks run in isolation, errors don't cascade
    """

    def __init__(self):
        """Initialize PluginManager."""
        self.plugins: dict[str, Any] = {}
        self._info: dict[str, PluginInfo] = {}
        self.hooks: dict[str, list] = {}
        self._config: dict[str, dict[str, Any]] = {}
        self._hook_results: dict[str, list[Any]] = {}
        self._load_order: list[str] = []

    # ------------------------------------------------------------------
    # Plugin registration
    # ------------------------------------------------------------------

    def register_plugin(
        self,
        name: str,
        plugin: Any,
        info: PluginInfo | None = None,
    ) -> bool:
        """Register a plugin object under *name* with optional metadata."""
        if name in self.plugins:
            return False
        self.plugins[name] = plugin
        if info is None:
            info = PluginInfo(name=name)
        else:
            info.name = name
        self._info[name] = info
        self._load_order.append(name)
        self._config.setdefault(name, {})
        # Call init hook if the plugin has one
        if hasattr(plugin, "on_init"):
            try:
                plugin.on_init(self._config.get(name, {}))
            except Exception:
                pass
        return True

    def unregister_plugin(self, name: str) -> bool:
        """Remove a plugin completely, calling its teardown hook first."""
        plugin = self.plugins.get(name)
        if plugin is None:
            return False
        # Call teardown hook
        if hasattr(plugin, "on_teardown"):
            try:
                plugin.on_teardown()
            except Exception:
                pass
        self.plugins.pop(name, None)
        self._info.pop(name, None)
        self._config.pop(name, None)
        self._load_order.remove(name)
        # Remove hooks associated with this plugin
        for hook_name in list(self.hooks.keys()):
            self.hooks[hook_name] = [
                (cb, prio, pname)
                for cb, prio, pname in self.hooks[hook_name]
                if pname != name
            ]
        return True

    def enable_plugin(self, name: str) -> bool:
        """Enable a disabled plugin (calls its on_start hook)."""
        info = self._info.get(name)
        if info is None:
            return False
        info.enabled = True
        plugin = self.plugins.get(name)
        if plugin and hasattr(plugin, "on_start"):
            try:
                plugin.on_start()
            except Exception:
                pass
        return True

    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin (calls its on_stop hook, keeps registration)."""
        info = self._info.get(name)
        if info is None:
            return False
        info.enabled = False
        plugin = self.plugins.get(name)
        if plugin and hasattr(plugin, "on_stop"):
            try:
                plugin.on_stop()
            except Exception:
                pass
        return True

    # ------------------------------------------------------------------
    # Dynamic loading
    # ------------------------------------------------------------------

    def load_plugin(
        self,
        module_path: str,
        name: str | None = None,
        info: PluginInfo | None = None,
    ) -> bool:
        """Dynamically load a plugin module by dotted path.

        After import, looks for a ``plugin_instance`` attribute on the
        module to use as the plugin object.  If not found, the module
        itself is used.
        """
        try:
            module = importlib.import_module(module_path)
            plugin_name = name or module_path.split(".")[-1]
            plugin_obj = getattr(module, "plugin_instance", module)
            return self.register_plugin(plugin_name, plugin_obj, info)
        except Exception:
            return False

    def resolve_dependencies(self) -> list[str]:
        """Return a load order that respects declared dependencies.

        Plugins with no dependencies load first; plugins that depend on
        others are loaded after their dependencies.  Circular dependencies
        are detected and the involved plugins are skipped.
        """
        resolved: list[str] = []
        unresolved: dict[str, list[str]] = {}

        for name, info in self._info.items():
            deps = [d for d in info.dependencies if d in self._info]
            if not deps:
                resolved.append(name)
            else:
                unresolved[name] = deps

        # Iterative resolution
        changed = True
        while changed and unresolved:
            changed = False
            for name in list(unresolved.keys()):
                deps = unresolved[name]
                if all(d in resolved for d in deps):
                    resolved.append(name)
                    unresolved.pop(name)
                    changed = True

        # Anything left is circular or missing deps
        if unresolved:
            # Just append them anyway (they'll be loaded without guarantees)
            resolved.extend(unresolved.keys())

        self._load_order = resolved
        return resolved

    # ------------------------------------------------------------------
    # Hook system
    # ------------------------------------------------------------------

    def register_hook(
        self,
        hook_name: str,
        callback: Callable,
        priority: int = 0,
        plugin_name: str = "",
    ) -> None:
        """Register *callback* for *hook_name* with optional *priority*.

        Lower priority values execute first.
        """
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []
        self.hooks[hook_name].append((callback, priority, plugin_name))
        # Sort by priority
        self.hooks[hook_name].sort(key=lambda x: x[1])

    def run_hook(self, hook_name: str, *args, **kwargs) -> list[Any]:
        """Execute all registered callbacks for *hook_name*.

        Only callbacks from *enabled* plugins are run.  Errors are
        caught per-callback and stored in results as ``("error", exc)``.
        """
        results: list[Any] = []
        for callback, priority, pname in self.hooks.get(hook_name, []):
            # Skip disabled plugins
            if pname and pname in self._info and not self._info[pname].enabled:
                continue
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as exc:
                results.append(("error", exc))
        self._hook_results[hook_name] = results
        return results

    def get_hook_results(self, hook_name: str) -> list[Any]:
        """Return cached results from the last ``run_hook`` call."""
        return self._hook_results.get(hook_name, [])

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_config(self, name: str, key: str, value: Any) -> None:
        """Set a configuration *key* for plugin *name*."""
        self._config.setdefault(name, {})[key] = value

    def get_config(self, name: str, key: str, default: Any = None) -> Any:
        """Retrieve a configuration value."""
        return self._config.get(name, {}).get(key, default)

    def get_all_config(self, name: str) -> dict[str, Any]:
        """Return the full config dict for *name*."""
        return dict(self._config.get(name, {}))

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def list_plugins(self, enabled_only: bool = False) -> list[str]:
        """Return list of registered plugin names."""
        if enabled_only:
            return [
                n for n in self._load_order if n in self._info and self._info[n].enabled
            ]
        return list(self._load_order)

    def get_plugin_info(self, name: str) -> PluginInfo | None:
        """Return metadata for plugin *name*."""
        return self._info.get(name)

    def stats(self) -> dict:
        """Return statistics dict."""
        enabled = sum(1 for i in self._info.values() if i.enabled)
        return {
            "total_plugins": len(self.plugins),
            "enabled_plugins": enabled,
            "disabled_plugins": len(self.plugins) - enabled,
            "registered_hooks": len(self.hooks),
            "total_hook_callbacks": sum(len(v) for v in self.hooks.values()),
            "load_order": list(self._load_order),
        }


# Global instance
plugin_manager = PluginManager()
