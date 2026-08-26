import asyncio

import pytest

from api.runtime_service import RuntimeAPIService


class Runtime:
    async def execute(self, goal, task_id, metadata):
        return {"goal": goal, "metadata": metadata}


def test_runtime_api_service_normalizes_and_dispatches():
    result = asyncio.run(RuntimeAPIService(Runtime()).execute({"goal": "hello", "task_id": "t1", "metadata": {"source": "api"}}))
    assert result == {"task_id": "t1", "result": {"goal": "hello", "metadata": {"source": "api"}}}


@pytest.mark.parametrize("request, error", [
    ({"task_id": "t1"}, ValueError),
    ({"goal": "hello"}, ValueError),
    ({"goal": "hello", "task_id": "t1", "metadata": []}, TypeError),
])
def test_runtime_api_service_validates_request(request, error):
    with pytest.raises(error):
        asyncio.run(RuntimeAPIService(Runtime()).execute(request))
