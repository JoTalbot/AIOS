"""Single-point API application wiring for the vNext runtime."""

from .router import Router
from .runtime_service import RuntimeAPIService
from .server import APIServer


class APIApplication:
    def __init__(self, runtime, execute_path="/execute"):
        self.runtime = runtime
        self.service = RuntimeAPIService(runtime)
        self.router = Router()
        self.router.register_runtime(self.service, execute_path)
        self.server = APIServer(pipeline=self.router)
        self.execute_path = execute_path

    async def handle(self, request, path=None):
        return await self.server.handle((path or self.execute_path, request))

    async def dispatch(self, path, request):
        return await self.router.dispatch(path, request)
