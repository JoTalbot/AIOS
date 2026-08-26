from aios.digital_twin.audit import TwinAuditLog
from aios.digital_twin.health_monitor import TwinHealthMonitor


def test_audit_records():
    audit = TwinAuditLog()
    entry = audit.record("simulation.completed", {"id": 1})
    assert entry.event == "simulation.completed"
    assert len(audit.entries) == 1


def test_health_monitor():
    result = TwinHealthMonitor().evaluate({"load": 10, "error": -1})
    assert result["load"] == "healthy"
    assert result["error"] == "warning"
