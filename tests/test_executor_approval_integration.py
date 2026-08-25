from aios_core.runtime.approval import ApprovalQueue, ApprovalStatus
from aios_core.runtime.contracts import AgentResult, AgentStatus, AgentTask
from aios_core.runtime.executor import AgentExecutor
from aios_core.runtime.policy import PolicyEngine


def test_executor_creates_pending_approval_without_running_handler():
    calls = []
    approvals = ApprovalQueue()

    def handler(task):
        calls.append(task.task_id)
        return AgentResult(task.task_id, AgentStatus.COMPLETED)

    task = AgentTask(id="a1", goal="deploy", permissions=("production.deploy",))
    executor = AgentExecutor(handler, policy=PolicyEngine(approval_permissions=("production.deploy",)), approvals=approvals)
    record = executor.execute(task, required_permission="production.deploy")

    assert record.status is AgentStatus.BLOCKED
    assert record.result.verdict == "PENDING_APPROVAL"
    assert record.approval_request_id is not None
    assert approvals.get(record.approval_request_id).status is ApprovalStatus.PENDING
    assert calls == []


def test_executor_runs_after_matching_approval():
    approvals = ApprovalQueue()
    task = AgentTask(id="a2", goal="deploy", permissions=("production.deploy",))
    executor = AgentExecutor(
        lambda t: AgentResult(t.task_id, AgentStatus.COMPLETED, verdict="APPROVED"),
        policy=PolicyEngine(approval_permissions=("production.deploy",)),
        approvals=approvals,
    )

    pending = executor.execute(task, required_permission="production.deploy")
    approvals.decide(pending.approval_request_id, approved=True, decided_by="operator")
    completed = executor.execute(task, required_permission="production.deploy", approval_request_id=pending.approval_request_id)

    assert completed.status is AgentStatus.COMPLETED
    assert completed.result.verdict == "APPROVED"
