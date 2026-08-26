"""AIOS runtime bootstrap layer."""

class RuntimeBootstrap:
    def __init__(self, container=None):
        self.container = container
        self.started = False

    async def start(self):
        self.started = True

    async def stop(self):
        self.started = False
