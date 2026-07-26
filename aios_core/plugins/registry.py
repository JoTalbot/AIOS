from typing import Dict, Type
from .base import BasePlugin

class PluginRegistry:
    def __init__(self):
        self._plugins: Dict[str, Type[BasePlugin]] = {}
    
    def register(self, plugin_class: Type[BasePlugin]):
        instance = plugin_class()
        self._plugins[instance.name] = plugin_class
    
    def get_plugin(self, name: str) -> Type[BasePlugin]:
        return self._plugins.get(name)
    
    def list_plugins(self) -> list:
        return [cls().name for cls in self._plugins.values()]

plugin_registry = PluginRegistry()
