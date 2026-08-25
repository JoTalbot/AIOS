from aios_core.openhands.audit import OHAuditLogger
from aios_core.openhands.models import AgentRole
from aios_core.audit_logger import AuditLogger


def test_checkpoint_is_persisted_as_audit_event(tmp_path):
    logger = AuditLogger(db_path=str(tmp_path / "audit.db"))
    audit = OHAuditLogger(logger=logger)
    audit.log("start", "task-1", AgentRole.CODER, note="hello")
    checkpoint = audit.checkpoint("task-1", AgentRole.CODER)
    persisted = [e for e in logger.query(limit=100) if e.get("type") == "openhands.audit_checkpoint"]
    assert persisted
    assert persisted[-1]["sequence"] == checkpoint.sequence
    assert persisted[-1]["root_hash"] == checkpoint.root_hash
