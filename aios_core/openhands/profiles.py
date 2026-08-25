"""Профили разговоров для ролей OpenHands-контура.

Профиль = system-инструкция + ограничения, собираемые в initial_message
Cloud-разговора. Права берутся из ``permissions.PROFILES`` (единый источник);
рендер включает их в промпт, а enforcement выполняется пост-проверкой
``check_paths`` по фактическому diff (план, §6).
"""

from .models import AgentPermissions, AgentRole
from .permissions import PROFILES

_REPO_RULES = (
    "Соблюдай AGENTS.md репозитория: минимальные правки, diff-режим для существующих "
    "файлов, protected-файлы не изменять, секреты не выводить и не коммитить, "
    "ветки agent/oh-*, в main напрямую не коммитить. После изменений — py_compile "
    "и целевые тесты."
)

_ROLE_INSTRUCTIONS: dict[AgentRole, str] = {
    AgentRole.ARCHITECT: (
        "Ты — Architect. Проанализируй задачу и существующий код, найди связанные "
        "компоненты и зависимости, предложи минимальное решение. Код не изменяй; "
        "результат — design-документ в docs/design/."
    ),
    AgentRole.CODER: (
        "Ты — Coder. Выполни изменение строго по задаче и design-документу. "
        "Минимальная область правки; новая функциональность — с тестами."
    ),
    AgentRole.TESTER: (
        "Ты — Tester. Напиши/обнови тесты под изменение и прогони их. Product-код "
        "не изменяй. Отчёт: passed/failed/skipped/warnings и оставшиеся риски."
    ),
    AgentRole.REVIEWER: (
        "Ты — независимый Reviewer (не Coder). Проверь diff: соответствие задаче, "
        "архитектуру, качество, regression, тесты, security, документацию, "
        "избыточную сложность. Код не изменяй. Вердикт: APPROVED или CHANGES_REQUESTED "
        "с конкретным списком замечаний."
    ),
    AgentRole.SECURITY: (
        "Ты — Security reviewer. Проверь secrets, auth, subprocess/shell, filesystem, "
        "network, injection, небезопасную конфигурацию. Серьёзные проблемы не "
        "исправляй молча — сначала отчёт в reports/security/."
    ),
    AgentRole.QA: (
        "Ты — QA. Функционально проверь изменение: happy path, edge cases, "
        "regression. Отчёт в reports/qa/."
    ),
}


def _render_permissions(perms: AgentPermissions) -> str:
    """Рендер блока ограничений доступа для промпта."""
    lines = [
        f"Доступ на чтение: {perms.read}; запись: {perms.write}.",
        "Разрешённые пути записи: " + (", ".join(f"`{p}`" for p in perms.allowed_paths) or "нет"),
    ]
    if perms.deny_paths:
        lines.append("Запрещённые пути: " + ", ".join(f"`{p}`" for p in perms.deny_paths))
    if not perms.secret_allowlist:
        lines.append("Секреты не выдаются; никогда не выводи токены/ключи/пароли.")
    return "\n".join(lines)


def build_prompt(role: AgentRole, task_description: str, *, context: str = "") -> str:
    """Собрать initial_message для разговора роли.

    Args:
        role: роль контура (должна иметь профиль в ``permissions.PROFILES``).
        task_description: самодостаточное описание задачи (без контекста чужой сессии).
        context: дополнительный контекст (design-документ, diff, отчёт тестов).

    Raises:
        KeyError: роль без профиля (пост-MVP роль без инструкции).
    """
    if role not in PROFILES or role not in _ROLE_INSTRUCTIONS:
        raise KeyError(f"нет профиля разговора для роли {role.value!r}")
    parts = [
        _ROLE_INSTRUCTIONS[role],
        "",
        "## Ограничения доступа",
        _render_permissions(PROFILES[role].permissions),
        "",
        "## Правила репозитория",
        _REPO_RULES,
    ]
    if context:
        parts += ["", "## Контекст", context]
    parts += ["", "## Задача", task_description]
    return "\n".join(parts)


def conversation_title(role: AgentRole, task_id: str) -> str:
    """Заголовок разговора в Cloud UI."""
    return f"aios-{role.value}-{task_id}"
