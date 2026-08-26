"""Execution context propagation foundation."""

class ContextPropagation:
    def propagate(self, context, target):
        if hasattr(target, "context"):
            target.context = context
        return target
