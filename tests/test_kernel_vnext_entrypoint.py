import pytest

from kernel.kernel import Kernel


class Orchestrator:
    async def run(self, goal, task_id, metadata=None):
        return {"goal": goal, "task_id": task_id, "metadata": metadata or {}}


@pytest.mark.asyncio
async def test_kernel_delegates_execution_to_vnext_orchestrator():
    kernel = Kernel()
    orchestrator = Orchestrator()
    kernel.attach_orchestrator(orchestrator)

    result = await kernel.execute("build", "task-1", {"source": "test"})

    assert result == {"goal": "build", "task_id": "task-1", "metadata": {"source": "test"}}


@pytest.mark.asyncio
async def test_kernel_requires_vnext_orchestrator():
    with pytest.raises(RuntimeError, match="orchestrator is not configured"):
        await Kernel().execute("build", "task-1")
