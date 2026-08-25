from types import SimpleNamespace

from aios_core.execution.kernel import ExecutionKernel
from aios_core.execution.orchestrator_integration import execute_orchestrator_tool_step


class FakeCapabilities:
    def execute(self, capability_name, input_data, agent_id, authority):
        return {
            "success": True,
            "result": {
                "capability": capability_name,
                "arguments": input_data,
                "agent_id": agent_id,
                "authority": authority,
            },
        }


def test_orchestrator_tool_step_routes_through_kernel():
    task = SimpleNamespace(id="task-1", agent_id="agent-1", authority="system")
    step = SimpleNamespace(params={"capability": "echo", "arguments": {"value": "ok"}})

    observation = execute_orchestrator_tool_step(ExecutionKernel(FakeCapabilities()), task, step)

    assert observation.success is True
    assert observation.result["capability"] == "echo"
    assert observation.result["arguments"] == {"value": "ok"}
