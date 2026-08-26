"""Agent invocation service foundation."""

from core.services.response import ServiceResponse


class AgentService:
    def __init__(self, runtime):
        self.runtime = runtime

    async def invoke(self, task):
        result = await self.runtime.execute(task)
        return ServiceResponse(success=True, result=result)
