from aios_core.openhands.file_evidence import verify_handoff_files
from aios_core.openhands.handoff import AgentHandoff
from aios_core.openhands.models import AgentRole


def test_stage_delta_matches_handoff_and_role_permissions():
    handoff = AgentHandoff(status="DONE", summary="coded", files_changed=("src/a.py",), evidence=("pytest passed",), next_action="test")
    result = verify_handoff_files(AgentRole.CODER, handoff, ["src/a.py"])
    assert result.passed


def test_stage_delta_rejects_unreported_file():
    handoff = AgentHandoff(status="DONE", summary="coded", files_changed=("src/a.py",), evidence=("pytest passed",), next_action="test")
    result = verify_handoff_files(AgentRole.CODER, handoff, ["src/a.py", "src/b.py"])
    assert not result.passed
    assert result.missing_from_handoff == ("src/b.py",)


def test_stage_delta_rejects_restricted_role_path():
    handoff = AgentHandoff(status="DONE", summary="tested", files_changed=("src/a.py",), evidence=("pytest passed",), next_action="review", verdict="APPROVED")
    result = verify_handoff_files(AgentRole.TESTER, handoff, ["src/a.py"])
    assert not result.passed
    assert "src/a.py" in result.permission_errors
