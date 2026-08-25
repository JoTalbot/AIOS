"""Тесты профилей разговоров OpenHands-контура."""

import pytest

from aios_core.openhands import AgentRole, build_prompt, conversation_title
from aios_core.openhands.models import AgentPermissions
from aios_core.openhands.profiles import _render_permissions


class TestRenderPermissions:
    def test_render_permissions_has_docstring(self):
        assert _render_permissions.__doc__ is not None
        assert _render_permissions.__doc__.strip()

    def test_render_permissions_full_block(self):
        perms = AgentPermissions(
            read="project",
            write="none",
            allowed_paths=("tests/**", "reports/**"),
            deny_paths=(".env",),
        )
        rendered = _render_permissions(perms)
        assert "Доступ на чтение: project; запись: none." in rendered
        assert "`tests/**`" in rendered and "`reports/**`" in rendered
        assert "Запрещённые пути: `.env`" in rendered
        assert "Секреты не выдаются" in rendered

    def test_render_permissions_without_deny_paths_and_with_allowlist(self):
        perms = AgentPermissions(read="all", write="workspace", secret_allowlist=("GITHUB_TOKEN",))
        rendered = _render_permissions(perms)
        assert "Запрещённые пути:" not in rendered
        assert "Секреты не выдаются" not in rendered
        assert "Разрешённые пути записи: нет" in rendered


class TestBuildPrompt:
    def test_coder_prompt_contains_task_and_rules(self):
        prompt = build_prompt(AgentRole.CODER, "Добавь функцию X в модуль Y")
        assert "Coder" in prompt
        assert "Добавь функцию X в модуль Y" in prompt
        assert "protected-файлы" in prompt
        assert ".env" in prompt  # deny_paths из профиля

    def test_reviewer_prompt_independent(self):
        prompt = build_prompt(AgentRole.REVIEWER, "Проверь diff задачи t-1")
        assert "независимый Reviewer" in prompt
        assert "APPROVED" in prompt and "CHANGES_REQUESTED" in prompt

    def test_context_block(self):
        prompt = build_prompt(AgentRole.TESTER, "Прогони тесты", context="diff: a.py +10")
        assert "## Контекст" in prompt
        assert "diff: a.py +10" in prompt

    def test_permissions_rendered(self):
        prompt = build_prompt(AgentRole.TESTER, "t")
        assert "tests/**" in prompt
        assert "reports/**" in prompt
        assert "Секреты не выдаются" in prompt

    def test_orchestrator_has_no_prompt(self):
        # Оркестратор — AIOS-сторона, разговор для него не создаётся.
        with pytest.raises(KeyError):
            build_prompt(AgentRole.ORCHESTRATOR, "t")

    @pytest.mark.parametrize(
        "role",
        [AgentRole.ARCHITECT, AgentRole.CODER, AgentRole.TESTER, AgentRole.REVIEWER, AgentRole.SECURITY, AgentRole.QA],
    )
    def test_all_scoped_roles_render(self, role):
        prompt = build_prompt(role, "задача")
        assert "задача" in prompt
        assert "## Ограничения доступа" in prompt
        assert "## Правила репозитория" in prompt


class TestConversationTitle:
    def test_format(self):
        assert conversation_title(AgentRole.CODER, "t-42") == "aios-coder-t-42"
