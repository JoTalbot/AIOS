class ContextManager:
    """Reasoning context management foundation."""

    def build(self, inputs):
        return {
            "context": inputs
        }

    def update(self, context, data):
        context.update(data)
        return context
