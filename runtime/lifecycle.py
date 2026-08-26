class LifecycleManager:
    def __init__(self):
        self.started = False

    async def start(self):
        self.started = True

    async def stop(self):
        self.started = False
