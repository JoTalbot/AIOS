class ComponentLifecycleManager:
    def __init__(self, registry, events=None):
        self.registry = registry
        self.events = events

    def _emit(self, name, payload):
        if self.events:
            self.events.publish(name, payload)

    def initialize_all(self):
        for name in self.registry.list_components():
            component = self.registry.get(name)
            initialize = getattr(component, "initialize", None)
            if initialize:
                initialize()
            self._emit("component.initialized", {"name": name})

    def start_all(self):
        for name in self.registry.list_components():
            component = self.registry.get(name)
            start = getattr(component, "start", None)
            if start:
                start()
            self._emit("component.started", {"name": name})

    def stop_all(self):
        for name in self.registry.list_components():
            component = self.registry.get(name)
            stop = getattr(component, "stop", None)
            if stop:
                stop()
            self._emit("component.stopped", {"name": name})
