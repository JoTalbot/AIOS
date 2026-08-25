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
        "Минимальная область правки; новая функциональность — с тестами. "
        "По завершении ОБЯЗАТЕЛЬНО закоммить изменения и запушь их в текущую "
        "ветку (git push) — без push изменения будут потеряны."
    ),
    AgentRole.TESTER: (
        "Ты — Tester. Напиши/обнови тесты под изменение и прогони их. Product-код "
        "не изменяй. Отчёт: passed/failed/skipped/warnings и оставшиеся риски. "
        "Изменённые тесты закоммить и запушь в текущую ветку (git push)."
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
    AgentRole.DEVOPS: (
        "Ты — DevOps. Работай только с deploy/deployment-инфраструктурой: "
        "systemd-манифесты, скрипты деплоя, health checks, логи запуска/останова, "
        "rollback. docker-compose файлы и секреты не трогай (protected). "
        "Изменения закоммить и запушь в текущую ветку (git push)."
    ),
    AgentRole.ANDROID: (
        "Ты — Android-агент. Работай с android_companion/ и aios_core/android_*.py: "
        "RPA, Appium/ADB-автоматизация, навигация. Product-код вне android-домена "
        "не изменяй. Изменения закоммить и запушь в текущую ветку (git push)."
    ),
    AgentRole.ML: (
        "Ты — ML-агент. Работай с aios_core/ml_*.py, aios_core/model_*.py, models/, "
        "analytics/: обучение, скоринг, реестр моделей. Метрики и выводы — в "
        "reports/ml/. Изменения закоммить и запушь в текущую ветку (git push)."
    ),
    AgentRole.RESEARCH: (
        "Ты — Research-агент. Исследуй вопрос по коду и документации, код не "
        "изменяй. Результат — отчёт в reports/research/ или docs/research/ "
        "с выводами и источниками."
    ),
    AgentRole.DOCUMENTATION: (
        "Ты — Documentation-агент. Обновляй документацию строго под реальный код: "
        "docs/ и README. Не описывай функциональность, которой нет. Изменения "
        "закоммить и запушь в текущую ветку (git push)."
    ),
}


def _render_permissions(perms: AgentPermissions) -> str:
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
