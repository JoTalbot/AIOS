"""Тесты permissions OpenHands-контура: RBAC-регистрация, path enforcement, protected-gate.

Без моков: используется реальный ``aios_core.rbac.RBACEngine`` и реальный
``aios_core.self_protection.is_protected``.
"""

import pytest

from aios_core.openhands import (
    MVP_ROLES,
    PROFILES,
    AgentRole,
    check_paths,
    path_allowed,
    rbac_role_name,
    register_roles,
)
from aios_core.rbac import RBACEngine


class TestProfiles:
    def test_mvp_roles_have_profiles(self):
        for role in MVP_ROLES:
            assert role in PROFILES

    def test_least_privilege_no_secrets_by_default(self):
        for profile in PROFILES.values():
            assert profile.permissions.secret_allowlist == ()

    def test_reviewer_cannot_write_code(self):
        assert not path_allowed("aios_core/foo.py", PROFILES[AgentRole.REVIEWER].permissions)

    def test_tester_only_tests_and_reports(self):
        perms = PROFILES[AgentRole.TESTER].permissions
        assert path_allowed("tests/test_x.py", perms)
        assert path_allowed("reports/run1.md", perms)
        assert not path_allowed("aios_core/foo.py", perms)

    def test_orchestrator_cannot_write_python(self):
        perms = PROFILES[AgentRole.ORCHESTRATOR].permissions
        assert path_allowed("data/openhands/tasks.json", perms)
        assert not path_allowed("aios_core/openhands/models.py", perms)

    def test_coder_denied_secrets(self):
        perms = PROFILES[AgentRole.CODER].permissions
        assert not path_allowed(".env", perms)
        assert not path_allowed(".env.production", perms)
        assert not path_allowed("data/.llm_keys.json", perms)
        assert path_allowed("aios_core/openhands/models.py", perms)


class TestRbacRegistration:
    def test_register_roles(self):
        engine = RBACEngine()
        names = register_roles(engine)
        assert names == [rbac_role_name(r) for r in MVP_ROLES]
        assert engine.has_permission(rbac_role_name(AgentRole.CODER), "workspace:write")
        assert engine.has_permission(rbac_role_name(AgentRole.REVIEWER), "reports:write")
        assert not engine.has_permission(rbac_role_name(AgentRole.REVIEWER), "workspace:write")

    def test_register_roles_idempotent(self):
        engine = RBACEngine()
        register_roles(engine)
        register_roles(engine)  # повтор — без дублей и ошибок
        assert len([r for r in engine.hierarchy.roles if r.startswith("oh-")]) == len(MVP_ROLES)


class TestCheckPaths:
    def test_protected_files_denied_for_coder(self):
        allowed, denied = check_paths(
            AgentRole.CODER,
            ["aios_core/openhands/models.py", "aios_core/autocoder_v3.py", "run_telegram_bot.py"],
        )
        assert allowed == ["aios_core/openhands/models.py"]
        assert set(denied) == {"aios_core/autocoder_v3.py", "run_telegram_bot.py"}

    def test_protected_denied_even_in_allowed_glob(self):
        # self_protection защищает __init__.py везде — роль Coder с allowed "**"
        # всё равно не может его править.
        allowed, denied = check_paths(AgentRole.CODER, ["aios_core/openhands/__init__.py"])
        assert allowed == []
        assert denied == ["aios_core/openhands/__init__.py"]

    def test_reviewer_diff_is_all_denied_code(self):
        _, denied = check_paths(AgentRole.REVIEWER, ["scripts/x.py", "README.md"])
        assert "scripts/x.py" in denied

    @pytest.mark.parametrize("role", list(MVP_ROLES))
    def test_env_never_allowed(self, role):
        _, denied = check_paths(role, [".env"])
        assert denied == [".env"]
