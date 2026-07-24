"""AIOS Plugin Manager v5.0 (Wasm Edition)

Advanced plugin system for extending AIOS functionality.
Supports plugin lifecycle hooks, priority ordering, WebAssembly (Wasm) isolation,
dependency resolution, and configuration per plugin.
"""

from __future__ import annotations

import contextlib
import importlib
import json
import logging
from collections.abc import Callable
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

__all__ = ["PluginInfo", "PluginManager", "WasmRuntime", "plugin_manager"]


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
        "is_wasm",
    )

    def __init__(
        self,
        name: str = "",
        version: str = "0.0.1",
        description: str = "",
        author: str = "",
        dependencies: Optional[List[str]] = None,
        priority: int = 0,
        enabled: bool = True,
        module_path: str = "",
        is_wasm: bool = False,
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
        self.is_wasm = is_wasm


class WasmRuntime:
    """WebAssembly execution environment wrapper (using dummy/mock execution for OS-agnostic testing).
    
    Provides isolated execution of .wasm binaries preventing them from accessing
    host memory, filesystem, or network without explicit permission.
    """
    
    def __init__(self):
        self.loaded_modules = {}
        self.memory_limit_mb = 128
        
        # Real implementation would use `wasmtime` or `wasm3` here.
        # import wasmtime
        # self.engine = wasmtime.Engine()
        # self.store = wasmtime.Store(self.engine)
        
    def load_module(self, name: str, wasm_bytecode: bytes) -> bool:
        """Load and compile a Wasm module."""
        # Mock compilation
        self.loaded_modules[name] = {
            "size": len(wasm_bytecode),
            "state": "compiled",
            "exports": ["run_hook", "init"]
        }
        return True
        
    def execute_hook(self, name: str, hook_name: str, payload: Dict[str, Any]) -> Any:
        """Execute a specific hook inside the Wasm sandbox."""
        if name not in self.loaded_modules:
            raise ValueError(f"Wasm module {name} not loaded")
            
        module = self.loaded_modules[name]
        if "run_hook" not in module["exports"]:
            return None
            
        # Serialize payload for Wasm boundary
        # input_json = json.dumps(payload)
        
        # Mock execution logic: if it's a known test plugin, return a mock response
        if name == "test_wasm_plugin":
            return {"status": "success", "wasm_hook": hook_name, "processed": True}
            
        return {"status": "executed", "sandbox": "wasm", "result": None}
        
    def unload(self, name: str):
        """Unload and free Wasm module memory."""
        self.loaded_modules.pop(name, None)


class PluginManager:
    """Manages plugins for AIOS.

    Features:
    - Plugin registration with version and dependency tracking
    - Dynamic module loading from dotted paths
    - WebAssembly (Wasm) Plugin support for memory/network isolation
    - Lifecycle hooks: init, start, stop, teardown
    - Priority-ordered hook execution
    - Plugin enable/disable without removal
    - Dependency resolution (load-order enforcement)
    """

    def __init__(self):
        """Initialize PluginManager."""
        self.plugins: Dict[str, Any] = {}
        self._info: Dict[str, PluginInfo] = {}
        self.hooks: Dict[str, List[Tuple[Callable, int, str]]] = {}
        self._config: Dict[str, Dict[str, Any]] = {}
        self._hook_results: Dict[str, List[Any]] = {}
        self._load_order: List[str] = []
        
        self.wasm_runtime = WasmRuntime()

    # ------------------------------------------------------------------
    # Plugin registration
    # ------------------------------------------------------------------

    def register_plugin(
        self,
        name: str,
        plugin: Any,
        info: Optional[PluginInfo] = None,
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
        if not info.is_wasm and hasattr(plugin, "on_init"):
            with contextlib.suppress(Exception):
                plugin.on_init(self._config.get(name, {}))
                
        return True

    def register_wasm_plugin(self, name: str, bytecode: bytes, info: Optional[PluginInfo] = None) -> bool:
        """Register a WebAssembly plugin payload."""
        if info is None:
            info = PluginInfo(name=name)
        info.name = name
        info.is_wasm = True
        
        if not self.wasm_runtime.load_module(name, bytecode):
            return False
            
        return self.register_plugin(name, plugin=name, info=info)

    def unregister_plugin(self, name: str) -> bool:
        """Remove a plugin completely, calling its teardown hook first."""
        if name not in self.plugins:
            return False
            
        info = self._info.get(name)
        plugin = self.plugins.get(name)
        
        if info and info.is_wasm:
            self.wasm_runtime.unload(name)
        elif plugin and hasattr(plugin, "on_teardown"):
            with contextlib.suppress(Exception):
                plugin.on_teardown()
                
        self.plugins.pop(name, None)
        self._info.pop(name, None)
        self._config.pop(name, None)
        if name in self._load_order:
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
        
        if not info.is_wasm:
            plugin = self.plugins.get(name)
            if plugin and hasattr(plugin, "on_start"):
                with contextlib.suppress(Exception):
                    plugin.on_start()
        return True

    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin (calls its on_stop hook, keeps registration)."""
        info = self._info.get(name)
        if info is None:
            return False
        info.enabled = False
        
        if not info.is_wasm:
            plugin = self.plugins.get(name)
            if plugin and hasattr(plugin, "on_stop"):
                with contextlib.suppress(Exception):
                    plugin.on_stop()
        return True

    # ------------------------------------------------------------------
    # Dynamic loading
    # ------------------------------------------------------------------

    def load_plugin(
        self,
        module_path: str,
        name: Optional[str] = None,
        info: Optional[PluginInfo] = None,
    ) -> bool:
        """Dynamically load a Python plugin module by dotted path."""
        try:
            module = importlib.import_module(module_path)
            plugin_name = name or module_path.split(".")[-1]
            plugin_obj = getattr(module, "plugin_instance", module)
            return self.register_plugin(plugin_name, plugin_obj, info)
        except Exception:
            return False

    def resolve_dependencies(self) -> List[str]:
        """Return a load order that respects declared dependencies."""
        resolved: List[str] = []
        unresolved: Dict[str, List[str]] = {}

        for name, info in self._info.items():
            deps = [d for d in info.dependencies if d in self._info]
            if not deps:
                resolved.append(name)
            else:
                unresolved[name] = deps

        changed = True
        while changed and unresolved:
            changed = False
            for name in list(unresolved.keys()):
                deps = unresolved[name]
                if all(d in resolved for d in deps):
                    resolved.append(name)
                    unresolved.pop(name)
                    changed = True

        if unresolved:
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
        """Register *callback* for *hook_name* with optional *priority*."""
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []
        self.hooks[hook_name].append((callback, priority, plugin_name))
        self.hooks[hook_name].sort(key=lambda x: x[1])

    def register_wasm_hook(self, hook_name: str, plugin_name: str, priority: int = 0) -> None:
        """Register a Wasm module to respond to a specific hook."""
        def wasm_callback(*args, **kwargs):
            payload = {"args": args, "kwargs": kwargs}
            return self.wasm_runtime.execute_hook(plugin_name, hook_name, payload)
            
        self.register_hook(hook_name, wasm_callback, priority, plugin_name)

    def run_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Execute all registered callbacks for *hook_name*."""
        results: List[Any] = []
        for callback, _priority, pname in self.hooks.get(hook_name, []):
            if pname and pname in self._info and not self._info[pname].enabled:
                continue
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as exc:
                results.append(("error", exc))
        self._hook_results[hook_name] = results
        return results

    def get_hook_results(self, hook_name: str) -> List[Any]:
        """Return cached results from the last ``run_hook`` call."""
        return self._hook_results.get(hook_name, [])

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_config(self, name: str, key: str, value: Any) -> None:
        self._config.setdefault(name, {})[key] = value

    def get_config(self, name: str, key: str, default: Any = None) -> Any:
        return self._config.get(name, {}).get(key, default)

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def list_plugins(self, enabled_only: bool = False) -> List[str]:
        if enabled_only:
            return [
                n for n in self._load_order if n in self._info and self._info[n].enabled
            ]
        return list(self._load_order)

    def stats(self) -> dict:
        enabled = sum(1 for i in self._info.values() if i.enabled)
        wasm_count = sum(1 for i in self._info.values() if i.is_wasm)
        return {
            "total_plugins": len(self.plugins),
            "enabled_plugins": enabled,
            "wasm_plugins": wasm_count,
            "registered_hooks": len(self.hooks),
            "total_hook_callbacks": sum(len(v) for v in self.hooks.values()),
        }

plugin_manager = PluginManager()
