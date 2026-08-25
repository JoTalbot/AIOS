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


class FakeTask:
    id = "task-e2e"
    agent_id = "agent-e2e"
    authority = "delegated"


class FakeStep:
    params = {"capability": "test.echo", "arguments": {"value": "ok"}}


def test_orchestrator_tool_step_reaches_execution_kernel():
    observation = execute_orchestrator_tool_step(
        ExecutionKernel(FakeCapabilities()),
        FakeTask(),
        FakeStep(),
    )

    assert observation.success is True
    assert observation.result["capability"] == "test.echo"
    assert observation.result["arguments"] == {"value": "ok"}
    assert observation.result["agent_id"] == "agent-e2e"
    assert observation.result["authority"] == "delegated"
