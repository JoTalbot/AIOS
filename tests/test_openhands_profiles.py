"""Тесты профилей разговоров OpenHands-контура."""

import pytest

from aios_core.openhands import AgentRole, build_prompt, conversation_title


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
        [
            AgentRole.ARCHITECT, AgentRole.CODER, AgentRole.TESTER, AgentRole.REVIEWER,
            AgentRole.SECURITY, AgentRole.QA, AgentRole.DEVOPS, AgentRole.ANDROID,
            AgentRole.ML, AgentRole.RESEARCH, AgentRole.DOCUMENTATION,
        ],
    )
    def test_all_scoped_roles_render(self, role):
        prompt = build_prompt(role, "задача")
        assert "задача" in prompt
        assert "## Ограничения доступа" in prompt
        assert "## Правила репозитория" in prompt


class TestConversationTitle:
    def test_format(self):
        assert conversation_title(AgentRole.CODER, "t-42") == "aios-coder-t-42"
