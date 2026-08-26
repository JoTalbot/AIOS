from agents.execution_manager import AgentExecutionManager, ExecutionState


class FakeLifecycle:
    def __init__(self):
        self.calls = []

    def handle_failure(self, execution_id, context, error):
        self.calls.append((execution_id, context, error))
        return {"action": "retry"}


def test_execution_failure_enters_recovery_pipeline():
    lifecycle = FakeLifecycle()
    manager = AgentExecutionManager(recovery_lifecycle=lifecycle)

    manager.begin("exec-1", {"task": "demo"})
    execution = manager.fail("exec-1", RuntimeError("boom"))

    assert execution["state"] in (ExecutionState.FAILED, ExecutionState.RECOVERING)
    assert execution["error"] is not None
