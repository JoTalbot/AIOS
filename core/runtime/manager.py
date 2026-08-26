"""AIOS runtime manager foundation."""

from .context import ExecutionContext


class RuntimeManager:
    """Coordinates task execution lifecycle."""

    def __init__(self):
        self.running = False

    async def start(self):
        self.running = True

    async def stop(self):
        self.running = False

    async def execute(self, context: ExecutionContext):
        if not self.running:
            raise RuntimeError("Runtime is not started")
        return context
