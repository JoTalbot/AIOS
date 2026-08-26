"""AIOS Runtime Supervisor v2 foundation."""

class RuntimeSupervisor:
    def __init__(self, runtime=None):
        self.runtime = runtime
        self.running = False

    async def start(self):
        self.running = True

    async def stop(self):
        self.running = False
