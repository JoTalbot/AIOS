class AIOSAPIServer:
    """External API entrypoint foundation."""

    def __init__(self, coordinator=None):
        self.coordinator = coordinator

    async def submit(self, agent, task):
        if not self.coordinator:
            return {"status": "no_coordinator"}
        return await self.coordinator.dispatch(agent, task)
