import asyncio

from api.application import APIApplication


class Runtime:
    async def execute(self, goal, task_id, metadata):
        return {"goal": goal, "task_id": task_id, "metadata": metadata}


def test_application_wires_server_router_and_runtime():
    app = APIApplication(Runtime())
    result = asyncio.run(app.handle({"goal": "hello", "task_id": "t1"}))
    assert result["task_id"] == "t1"
    assert result["result"]["goal"] == "hello"


def test_application_dispatches_explicit_path():
    app = APIApplication(Runtime())
    result = asyncio.run(app.dispatch("/execute", {"goal": "hello", "task_id": "t2"}))
    assert result["task_id"] == "t2"
