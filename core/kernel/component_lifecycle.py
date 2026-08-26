from .dependency_graph import DependencyGraph


class ComponentLifecycleManager:
    def __init__(self, registry, events=None, dependency_graph=None):
        self.registry = registry
        self.events = events
        self.dependencies = dependency_graph or DependencyGraph()

    def _emit(self, name, payload):
        if self.events:
            self.events.publish(name, payload)

    def discover_dependencies(self):
        """Build dependency graph automatically from registered components."""
        self.dependencies = DependencyGraph()

        for name in self.registry.list_components():
            self.dependencies.add(
                name,
                self.registry.get_dependencies(name),
            )

        return self.dependencies

    def validate_dependencies(self):
        """Validate that all declared dependencies exist before startup."""
        errors = []

        for name in self.registry.list_components():
            for dependency in self.registry.get_dependencies(name):
                if self.registry.get(dependency) is None:
                    errors.append(
                        {
                            "component": name,
                            "missing": dependency,
                        }
                    )

        result = {
            "valid": len(errors) == 0,
            "errors": errors,
        }

        self._emit("component.dependencies.validated", result)
        return result

    def set_dependencies(self, component, requires=None):
        self.dependencies.add(component, requires)

    def initialize_all(self):
        self.discover_dependencies()
        self.validate_dependencies()

        for name in self.dependencies.startup_order():
            component = self.registry.get(name)
            if component is None:
                continue
            initialize = getattr(component, "initialize", None)
            if initialize:
                initialize()
            self._emit("component.initialized", {"name": name})

    def start_all(self):
        self.discover_dependencies()
        self.validate_dependencies()

        for name in self.dependencies.startup_order():
            component = self.registry.get(name)
            if component is None:
                continue
            start = getattr(component, "start", None)
            if start:
                start()
            self._emit("component.started", {"name": name})

    def stop_all(self):
        self.discover_dependencies()

        for name in self.dependencies.shutdown_order():
            component = self.registry.get(name)
            if component is None:
                continue
            stop = getattr(component, "stop", None)
            if stop:
                stop()
            self._emit("component.stopped", {"name": name})
