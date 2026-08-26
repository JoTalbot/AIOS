"""Runtime restart orchestration for AIOS kernel stack."""


class RestartManager:
    """Coordinates restart operations without rebuilding the container."""

    def __init__(self, context):
        self.context = context

    def restart(self):
        self.context.stop()
        self.context.start()
        return self.context
