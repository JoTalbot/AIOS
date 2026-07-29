
from .base import BasePlugin


class PluginRegistry:
    def __init__(self):
        self._plugins: dict[str, type[BasePlugin]] = {}
    
    def register(self, plugin_class: type[BasePlugin]):
        instance = plugin_class()
        self._plugins[instance.name] = plugin_class
    
    def get_plugin(self, name: str) -> type[BasePlugin]:
        return self._plugins.get(name)
    
    def list_plugins(self) -> list:
        return [cls().name for cls in self._plugins.values()]

plugin_registry = PluginRegistry()
