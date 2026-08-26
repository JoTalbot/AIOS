class PluginLifecycle:
    def __init__(self):
        self.plugins = {}

    def register(self, name, plugin):
        self.plugins[name] = plugin

    def start_all(self):
        for plugin in self.plugins.values():
            start = getattr(plugin, 'start', None)
            if start:
                start()

    def stop_all(self):
        for plugin in self.plugins.values():
            stop = getattr(plugin, 'stop', None)
            if stop:
                stop()
