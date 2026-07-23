"""Audit logger ops."""
from aios_core.audit_logger import AuditLogger
def test_audit(): al = AuditLogger(); assert al is not None
