class ContextManager:
    """AIOS reasoning context foundation."""

    def build(self, data):
        return {
            "data": data,
            "context": True
        }
