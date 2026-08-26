"""Memory checkpoint foundation."""


class CheckpointManager:
    def save(self, context):
        return context

    def restore(self, key):
        return None
