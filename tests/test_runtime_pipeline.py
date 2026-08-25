from aios_core.runtime.approval import ApprovalQueue
from aios_core.runtime.contracts import AgentResult, AgentStatus, AgentTask
from aios_core.runtime.executor import AgentExecutor
from aios_core.runtime.policy import PolicyEngine
from aios_core.runtime.sandbox import SandboxExecutor, SandboxPolicy


def test_policy_approval_then_sandbox_pipeline():
    approvals = ApprovalQueue()
    calls = []

    def handler(task):
        calls.append(task.task_id)
        return AgentResult(task.task_id, AgentStatus.COMPLETED, verdict="AGENT_OK")

    sandbox = SandboxExecutor(
        handler,
        SandboxPolicy(allowed_permissions=("production.deploy",)),
    )
    task = AgentTask(id="pipeline-1", goal="deploy", permissions=("production.deploy",))
    executor = AgentExecutor(
        handler,
        policy=PolicyEngine(approval_permissions=("production.deploy",)),
        approvals=approvals,
        sandbox=sandbox,
    )

    pending = executor.execute(task, required_permission="production.deploy")
    assert pending.result.verdict == "PENDING_APPROVAL"
    assert calls == []

    approvals.decide(pending.approval_request_id, approved=True, decided_by="operator")
    completed = executor.execute(
        task,
        required_permission="production.deploy",
        approval_request_id=pending.approval_request_id,
    )
    assert completed.status is AgentStatus.COMPLETED
    assert calls == [task.task_id]


def test_sandbox_policy_blocks_before_handler():
    calls = []
    sandbox = SandboxExecutor(
        lambda task: calls.append(task.task_id) or AgentResult(task.task_id, AgentStatus.COMPLETED),
        SandboxPolicy(allowed_permissions=("filesystem.read",)),
    )
    task = AgentTask(id="pipeline-2", goal="write", permissions=("filesystem.write",))
    result = sandbox.execute(task)
    assert result.status is AgentStatus.BLOCKED
    assert calls == []
