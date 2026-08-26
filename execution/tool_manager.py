class ToolExecutionManager:
    """Coordinates tool execution lifecycle."""

    def __init__(self, registry=None):
        self.registry = registry

    def execute(self, name, *args, **kwargs):
        if self.registry is None:
            raise RuntimeError("tool registry is not configured")
        tool = self.registry.get(name)
        return tool(*args, **kwargs)
