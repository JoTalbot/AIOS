import asyncio

from api.server import APIServer
from api.runtime_service import RuntimeAPIService


class Runtime:
    async def execute(self, goal, task_id, metadata):
        return {"goal": goal, "task_id": task_id, "metadata": metadata}


def test_api_server_reaches_runtime_service():
    server = APIServer(service=RuntimeAPIService(Runtime()))
    result = asyncio.run(server.handle({"goal": "hello", "task_id": "t1"}))
    assert result == {
        "task_id": "t1",
        "result": {"goal": "hello", "task_id": "t1", "metadata": {}},
    }
