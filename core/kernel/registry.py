"""Service registry for automatic AIOS core wiring."""


class KernelRegistry:
    def __init__(self):
        self.components = {}
        self.metadata = {}

    def register(self, name, component):
        self.components[name] = component
        self.metadata[name] = {
            "requires": getattr(component, "requires", []),
            "component_name": getattr(component, "name", name),
        }
        return component

    def get(self, name):
        return self.components.get(name)

    def list_components(self):
        return list(self.components.keys())

    def get_dependencies(self, name):
        return self.metadata.get(name, {}).get("requires", [])

    def register_core(self, kernel=None, agent_manager=None, bootstrap=None):
        if kernel is not None:
            self.register("kernel", kernel)
        if agent_manager is not None:
            self.register("agent_manager", agent_manager)
        if bootstrap is not None:
            self.register("bootstrap", bootstrap)
        return self

    def restore(self, recovery):
        recovery.restore(self)
        return self
