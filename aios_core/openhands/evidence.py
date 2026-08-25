"""Evidence and Definition-of-Done primitives for OpenHands agents.

The orchestration layer must distinguish an agent claim from a verified result.
This module is intentionally dependency-free so it can also be used by tests and
future evaluation runners.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class EvidenceKind(StrEnum):
    TEST = "test"
    COMPILE = "compile"
    DIFF = "diff"
    LINT = "lint"
    SECURITY = "security"
    COMMAND = "command"
    REVIEW = "review"


@dataclass(frozen=True)
class Evidence:
    kind: EvidenceKind
    command: str
    result: str
    passed: bool
    details: str = ""


@dataclass(frozen=True)
class DoDItem:
    key: str
    description: str
    required: bool = True


@dataclass
class CompletionReport:
    """Machine-readable completion report emitted/validated by the orchestrator."""

    claims: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    dod: dict[str, bool] = field(default_factory=dict)
    risks: list[str] = field(default_factory=list)

    def required_dod_passed(self, items: tuple[DoDItem, ...]) -> bool:
        return all(not item.required or self.dod.get(item.key, False) for item in items)

    def evidence_passed(self) -> bool:
        return bool(self.evidence) and all(item.passed for item in self.evidence)


ROLE_DOD: dict[str, tuple[DoDItem, ...]] = {
    "architect": (
        DoDItem("repo_inspected", "Связанные код, тесты и правила репозитория изучены"),
        DoDItem("design_written", "Минимальный дизайн и затрагиваемые файлы зафиксированы"),
        DoDItem("acceptance_defined", "Критерии приёмки определены"),
    ),
    "coder": (
        DoDItem("scope_ok", "Изменения находятся в пределах задачи и разрешённых путей"),
        DoDItem("implementation_done", "Требуемая функциональность реализована"),
        DoDItem("tests_done", "Релевантные тесты добавлены или обновлены"),
        DoDItem("compile_passed", "Изменённый Python-код прошёл py_compile"),
        DoDItem("tests_passed", "Целевые тесты прошли"),
        DoDItem("diff_reviewed", "Фактический diff проверен перед завершением"),
        DoDItem("git_synced", "Commit и push выполнены"),
    ),
    "tester": (
        DoDItem("diff_inspected", "Фактический diff изучен"),
        DoDItem("happy_path", "Основной сценарий проверен"),
        DoDItem("edge_cases", "Ключевые edge cases проверены"),
        DoDItem("regression", "Regression-сценарии проверены"),
        DoDItem("results_recorded", "Команды и фактические результаты записаны"),
    ),
    "reviewer": (
        DoDItem("requirements", "Требования проверены"),
        DoDItem("architecture", "Архитектура и совместимость проверены"),
        DoDItem("tests", "Тесты и regression проверены"),
        DoDItem("security", "Основные security-риски проверены"),
        DoDItem("evidence", "Вердикт основан на фактических доказательствах"),
    ),
    "security": (
        DoDItem("secrets", "Проверены секреты и утечки"),
        DoDItem("attack_surface", "Проверена поверхность атаки"),
        DoDItem("evidence", "Подтверждённые проблемы отделены от гипотез"),
        DoDItem("report", "Security-отчёт содержит severity и evidence"),
    ),
    "qa": (
        DoDItem("happy_path", "Основной пользовательский сценарий проверен"),
        DoDItem("invalid_input", "Ошибочные входы проверены"),
        DoDItem("regression", "Regression проверен"),
        DoDItem("results_recorded", "Фактические результаты записаны"),
    ),
}


def dod_for_role(role: str) -> tuple[DoDItem, ...]:
    """Return role-specific DoD, with a conservative generic fallback."""
    return ROLE_DOD.get(role, (
        DoDItem("scope_ok", "Изменения находятся в пределах роли и задачи"),
        DoDItem("checks_done", "Релевантные проверки выполнены"),
        DoDItem("result_recorded", "Результат и оставшиеся риски записаны"),
    ))
