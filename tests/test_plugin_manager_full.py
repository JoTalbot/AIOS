"""Full tests for plugin manager."""

from aios_core.plugin_manager import PluginManager


def test_plugin_manager_init():
    pm = PluginManager()
    assert pm is not None


def test_plugin_manager_stats():
    pm = PluginManager()
    s = pm.stats()
    assert isinstance(s, dict)
