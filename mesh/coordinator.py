class MeshCoordinator:

    def __init__(self, router):
        self.router = router

    async def dispatch(self, packet):
        return await self.router.send(packet)
