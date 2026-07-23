"""End-to-end smoke tests for critical paths."""

from aios_core import __version__


def test_version_defined():
    assert __version__ == "9.3.0"


def test_core_imports_work():
    from aios_core import Database, Orchestrator
    assert Database is not None
    assert Orchestrator is not None
