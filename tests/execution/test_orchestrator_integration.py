from aios_core.execution.kernel import ExecutionKernel
from aios_core.execution.models import Observation
from aios_core.execution.orchestrator_integration import execute_orchestrator_tool_step


class FakeCapabilities:
    def __init__(self):
        self.calls = []

    def execute(self, *, capability_name, input_data, agent_id, authority):
        self.calls.append(
            {
                "capability_name": capability_name,
                "input_data": input_data,
                "agent_id": agent_id,
                "authority": authority,
            }
        )
        return {"success": True, "result": {"answer": 42}}


class Task:
    id = "task-123"
    agent_id = "agent-7"
    authority = "operator"


class Step:
    params = {"capability": "calculator", "arguments": {"a": 40, "b": 2}}


def test_orchestrator_tool_step_routes_through_kernel():
    capabilities = FakeCapabilities()
    kernel = ExecutionKernel(capabilities)

    observation = execute_orchestrator_tool_step(kernel, Task(), Step())

    assert isinstance(observation, Observation)
    assert observation.success is True
    assert observation.result == {"success": True, "result": {"answer": 42}}
    assert capabilities.calls == [
        {
            "capability_name": "calculator",
            "input_data": {"a": 40, "b": 2},
            "agent_id": "agent-7",
            "authority": "operator",
        }
    ]


def test_orchestrator_tool_step_rejects_missing_capability():
    class InvalidStep:
        params = {"arguments": {"a": 1}}

    capabilities = FakeCapabilities()
    kernel = ExecutionKernel(capabilities)

    try:
        execute_orchestrator_tool_step(kernel, Task(), InvalidStep())
    except ValueError as exc:
        assert str(exc) == "Tool step requires a 'capability' parameter"
    else:
        raise AssertionError("missing capability must raise ValueError")
