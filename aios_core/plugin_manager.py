"""AIOS Plugin Runtime Layer v2.1.1"""

class PluginManager:
    def __init__(self):
        self.plugins = {}

    def register(self, name, plugin):
        self.plugins[name] = plugin
