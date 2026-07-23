"""Tests for memory manager and audit logger."""

from aios_core.memory_manager import MemoryManager
from aios_core.audit_logger import AuditLogger


def test_memory_manager_init():
    mm = MemoryManager()
    assert mm is not None


def test_memory_manager_stats():
    mm = MemoryManager()
    s = mm.stats()
    assert isinstance(s, dict)


def test_audit_logger_init():
    al = AuditLogger()
    assert al is not None
