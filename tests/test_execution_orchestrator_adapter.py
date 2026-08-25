from aios_core.execution.models import Observation
from aios_core.execution.orchestrator_adapter import execute_tool_step


class FakeKernel:
    def execute(self, action, context):
        assert action.capability == "echo"
        assert action.arguments == {"value": "hello"}
        assert context.task_id == "task-1"
        assert context.agent_id == "agent-1"
        assert context.authority == "system"
        return Observation(action_id=action.id, success=True, result={"value": "hello"})


def test_execute_tool_step_builds_action_and_context():
    observation = execute_tool_step(
        FakeKernel(),
        task_id="task-1",
        agent_id="agent-1",
        authority="system",
        params={"capability": "echo", "arguments": {"value": "hello"}},
    )

    assert observation.success is True
    assert observation.result == {"value": "hello"}


def test_execute_tool_step_requires_capability():
    try:
        execute_tool_step(
            FakeKernel(),
            task_id="task-1",
            agent_id="agent-1",
            authority="system",
            params={"arguments": {}},
        )
    except ValueError as exc:
        assert "capability" in str(exc)
    else:
        raise AssertionError("expected ValueError")
