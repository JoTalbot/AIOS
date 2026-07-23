"""plugin_manager standalone test."""
from aios_core.plugin_manager import PluginManager
def test_init(): s = PluginManager().stats(); assert isinstance(s, dict)
