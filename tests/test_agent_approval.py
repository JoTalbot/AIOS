from aios_core.runtime.approval import ApprovalQueue, ApprovalStatus
from aios_core.runtime.contracts import AgentTask


def test_approval_request_and_approval_transition():
    queue = ApprovalQueue()
    request = queue.request(AgentTask(id="t1", goal="deploy"), "production.deploy", "production change")

    assert request.status is ApprovalStatus.PENDING
    assert queue.pending() == (request,)

    decided = queue.decide(request.request_id, approved=True, decided_by="operator")
    assert decided.status is ApprovalStatus.APPROVED
    assert decided.decided_by == "operator"
    assert queue.pending() == ()


def test_rejected_request_cannot_be_decided_twice():
    queue = ApprovalQueue()
    request = queue.request(AgentTask(id="t2", goal="deploy"), "production.deploy", "risk")
    queue.decide(request.request_id, approved=False, decided_by="operator")

    try:
        queue.decide(request.request_id, approved=True, decided_by="operator")
    except ValueError as exc:
        assert "no longer pending" in str(exc)
    else:
        raise AssertionError("terminal approval request must not be decided twice")
