"""Tests for PluginManager"""

from aios_core.plugin_manager import PluginManager


def test_register_plugin():
    pm = PluginManager()
    assert pm.register_plugin("test", {"version": "1.0"}) is True


def test_hook_system():
    pm = PluginManager()
    results = []

    def my_hook(x):
        results.append(x * 2)

    pm.register_hook("test_hook", my_hook)
    pm.run_hook("test_hook", 5)

    assert 10 in results
