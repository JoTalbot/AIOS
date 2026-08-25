from aios_core.runtime.contracts import AgentResult, AgentStatus, AgentTask
from aios_core.runtime.executor import AgentExecutor
from aios_core.runtime.policy import PolicyDecision, PolicyEngine


def test_executor_blocks_denied_permission_without_running_handler():
    calls = []

    def handler(task):
        calls.append(task.task_id)
        return AgentResult(task_id=task.task_id, status=AgentStatus.COMPLETED)

    task = AgentTask(id="p1", goal="read", permissions=())
    executor = AgentExecutor(handler, policy=PolicyEngine())
    record = executor.execute(task, required_permission="filesystem.read")

    assert record.status is AgentStatus.BLOCKED
    assert record.result.verdict == "BLOCKED"
    assert calls == []


def test_executor_allows_explicit_permission():
    task = AgentTask(id="p2", goal="read", permissions=("filesystem.read",))
    executor = AgentExecutor(
        lambda t: AgentResult(task_id=t.task_id, status=AgentStatus.COMPLETED, verdict="APPROVED"),
        policy=PolicyEngine(),
    )
    record = executor.execute(task, required_permission="filesystem.read")

    assert record.status is AgentStatus.COMPLETED
    assert record.result.verdict == "APPROVED"


def test_executor_blocks_sandbox_and_approval_decisions_at_boundary():
    for permission, kwargs in (
        ("shell.execute", {"sandbox_permissions": ("shell.execute",)}),
        ("production.deploy", {"approval_permissions": ("production.deploy",)}),
    ):
        task = AgentTask(id=permission, goal="sensitive", permissions=(permission,))
        executor = AgentExecutor(lambda _: None, policy=PolicyEngine(**kwargs))
        record = executor.execute(task, required_permission=permission)
        assert record.status is AgentStatus.BLOCKED
        assert record.result.verdict == "BLOCKED"
