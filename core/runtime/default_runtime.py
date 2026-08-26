"""Default AIOS runtime composition."""

class DefaultRuntime:
    def __init__(self, container=None):
        self.container = container
        self.running = False

    async def start(self):
        self.running = True

    async def stop(self):
        self.running = False
