import asyncio

from api.router import Router
from api.runtime_service import RuntimeAPIService


class Runtime:
    async def execute(self, goal, task_id, metadata):
        return {"goal": goal, "task_id": task_id, "metadata": metadata}


def test_router_runtime_execution_route():
    router = Router()
    service = RuntimeAPIService(Runtime())
    router.register_runtime(service)
    result = asyncio.run(router.dispatch("/execute", {"goal": "hello", "task_id": "t1"}))
    assert result["task_id"] == "t1"
    assert result["result"]["goal"] == "hello"
