"""Plugin manager full new."""
from aios_core.plugin_manager import PluginManager
def test(): s=PluginManager().stats(); assert isinstance(s,dict)
