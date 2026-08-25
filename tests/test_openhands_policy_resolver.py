from aios_core.openhands.policy_resolver import resolve_ci_policy


def test_security_task_forces_security_workflows():
    result = resolve_ci_policy("security audit authentication", [])
    assert result.security_forced
    assert "Supply Chain Gate" in result.required_workflows
    assert "Secret scanning" in result.required_workflows


def test_sensitive_auth_path_forces_security_policy():
    result = resolve_ci_policy("add API feature", ["aios_core/auth/service.py"])
    assert result.security_forced
    assert "Supply Chain Gate" in result.required_workflows
    assert "Secret scanning" in result.required_workflows
    assert "sensitive_path:aios_core/auth/service.py" in result.reasons


def test_workflow_change_forces_security_policy():
    result = resolve_ci_policy("refactor CI", [".github/workflows/full-ci-cd.yml"])
    assert result.security_forced


def test_normal_source_change_keeps_base_policy():
    result = resolve_ci_policy("add UI feature", ["aios_core/ui/dashboard.py"])
    assert not result.security_forced
    assert result.required_workflows == ("AIOS Core Gate", "OpenHands Audit Integrity")
