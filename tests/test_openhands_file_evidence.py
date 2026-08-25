from aios_core.openhands.file_evidence import verify_handoff_files
from aios_core.openhands.handoff import AgentHandoff
from aios_core.openhands.models import AgentRole


def test_file_evidence_requires_exact_handoff_match():
    handoff = AgentHandoff(status="DONE", summary="x", files_changed=("a.py", "b.py"))
    result = verify_handoff_files(AgentRole.CODER, handoff, ["a.py", "b.py"])
    assert result.passed


def test_file_evidence_blocks_unreported_actual_change():
    handoff = AgentHandoff(status="DONE", summary="x", files_changed=("a.py",))
    result = verify_handoff_files(AgentRole.CODER, handoff, ["a.py", "secret.txt"])
    assert not result.passed
    assert result.missing_from_handoff == ("secret.txt",)


def test_file_evidence_checks_permissions():
    handoff = AgentHandoff(status="DONE", summary="x", files_changed=("src/a.py",))
    result = verify_handoff_files(AgentRole.CODER, handoff, ["src/a.py"])
    assert not result.passed
    assert result.permission_errors
