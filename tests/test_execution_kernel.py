from aios_core.execution import Action, ExecutionContext, ExecutionKernel


class FakeCapabilities:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def execute(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def test_kernel_delegates_to_capability_engine():
    capabilities = FakeCapabilities(
        {"success": True, "result": {"message": "hello"}, "capability": "echo"}
    )
    kernel = ExecutionKernel(capabilities)
    action = Action(capability="echo", arguments={"message": "hello"})

    observation = kernel.execute(
        action,
        ExecutionContext(task_id="task-1", agent_id="agent-1", authority="system"),
    )

    assert observation.success is True
    assert observation.result["success"] is True
    assert observation.action_id == action.id
    assert capabilities.calls == [
        {
            "capability_name": "echo",
            "input_data": {"message": "hello"},
            "agent_id": "agent-1",
            "authority": "system",
        }
    ]


def test_kernel_preserves_capability_failure():
    capabilities = FakeCapabilities(
        {"success": False, "result": None, "capability": "echo", "error": "denied"}
    )
    kernel = ExecutionKernel(capabilities)
    action = Action(capability="echo")

    observation = kernel.execute(
        action,
        ExecutionContext(task_id="task-1", agent_id="agent-1"),
    )

    assert observation.success is False
    assert observation.error == "denied"
