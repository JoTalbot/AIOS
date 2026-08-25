from aios_core.execution.kernel import ExecutionKernel
from aios_core.execution.models import Observation
from aios_core.execution.orchestrator_adapter import execute_tool_step


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
        return {"success": True, "result": {"echo": input_data["value"]}}


def test_tool_adapter_reaches_kernel_and_capability_engine():
    capabilities = FakeCapabilities()
    kernel = ExecutionKernel(capabilities)

    observation = execute_tool_step(
        kernel,
        task_id="task-42",
        agent_id="agent-7",
        authority="system",
        params={"capability": "echo", "arguments": {"value": "hello"}},
    )

    assert isinstance(observation, Observation)
    assert observation.success is True
    assert observation.result == {"echo": "hello"}
    assert len(capabilities.calls) == 1
    assert capabilities.calls[0] == {
        "capability_name": "echo",
        "input_data": {"value": "hello"},
        "agent_id": "agent-7",
        "authority": "system",
    }
