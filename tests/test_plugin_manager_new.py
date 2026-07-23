"""plugin_manager test."""
def test(): from aios_core.plugin_manager import PluginManager; s = PluginManager().stats(); assert isinstance(s, dict)
