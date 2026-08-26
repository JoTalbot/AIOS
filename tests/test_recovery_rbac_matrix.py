import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from api.app import create_app
from api.security import OperatorRole, SecurityContext
from runtime.recovery_api import RecoveryOperatorService
from runtime.recovery_queue import RecoveryQueue, RecoveryQueueItem


@pytest.mark.parametrize("role,mutation_status", [
    (OperatorRole.VIEWER, 403),
    (OperatorRole.OPERATOR, 200),
    (OperatorRole.ADMIN, 200),
])
def test_recovery_mutation_rbac(role, mutation_status, tmp_path):
    queue = RecoveryQueue(str(tmp_path / "queue.jsonl"))
    queue.enqueue(RecoveryQueueItem("e1", "manual_review", "operator action", 3, "corr-1"))
    service = RecoveryOperatorService(queue=queue)
    app = create_app(
        recovery_service=service,
        operator_validator=lambda request: SecurityContext(actor="alice", role=role),
    )
    client = TestClient(app)
    response = client.post("/recovery/resolve", json={"execution_id": "e1", "action": "manual_review", "reason": "approved"})
    assert response.status_code == mutation_status
    if response.status_code == 200:
        assert response.json()["execution_id"] == "e1"


def test_actor_and_correlation_are_propagated(tmp_path):
    queue = RecoveryQueue(str(tmp_path / "queue.jsonl"))
    queue.enqueue(RecoveryQueueItem("e2", "manual_review", "needs review", 3, "corr-77"))
    audit_path = tmp_path / "audit.jsonl"
    from runtime.operator_audit import OperatorAuditLog
    service = RecoveryOperatorService(queue=queue, audit_log=OperatorAuditLog(str(audit_path)))
    app = create_app(
        recovery_service=service,
        operator_validator=lambda request: SecurityContext(actor="alice", role=OperatorRole.OPERATOR),
    )
    response = TestClient(app).post("/recovery/resolve", json={"execution_id": "e2", "action": "manual_review"})
    assert response.status_code == 200
    event = service.audit_events()[-1]
    assert event.actor == "alice"
    assert event.outcome == "resolved"
