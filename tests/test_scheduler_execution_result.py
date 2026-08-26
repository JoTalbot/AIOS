import asyncio

from execution import ExecutionResult
from kernel.scheduler import AgentTask, Scheduler, TaskState


def test_scheduler_preserves_canonical_execution_result():
    async def scenario():
        async def executor(payload):
            return ExecutionResult.success(payload["task_id"], {"answer": 42})

        scheduler = Scheduler(executor=executor)
        task = AgentTask("result-1", "agent", {"task_id": "result-1"})
        await scheduler.submit(task)
        await scheduler.run_until_idle()
        await scheduler.stop()

        assert task.state is TaskState.DONE
        assert task.result.to_dict() == {
            "task_id": "result-1",
            "status": "completed",
            "value": {"answer": 42},
            "error": None,
            "metadata": {},
        }

    asyncio.run(scenario())
