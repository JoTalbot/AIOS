from types import SimpleNamespace

from aios_core.execution.kernel import ExecutionKernel
from aios_core.execution.orchestrator_bridge import OrchestratorExecutionBridge


class FakeCapabilities:
    def __init__(self):
        self.calls = []

    def execute(self, capability_name, input_data, agent_id, authority):
        self.calls.append((capability_name, input_data, agent_id, authority))
        return {"success": True, "result": {"ok": True}}


def test_orchestrator_execution_bridge_routes_tool_step_to_kernel():
    capabilities = FakeCapabilities()
    bridge = OrchestratorExecutionBridge(ExecutionKernel(capabilities))
    task = SimpleNamespace(id="task-1", agent_id="agent-1", authority="operator")
    step = SimpleNamespace(
        params={
            "capability": "search",
            "arguments": {"query": "AIOS"},
        }
    )

    observation = bridge.execute(task, step)

    assert observation.success is True
    assert capabilities.calls == [
        ("search", {"query": "AIOS"}, "agent-1", "operator")
    ]
