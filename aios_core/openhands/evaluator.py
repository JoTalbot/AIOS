"""Deterministic prompt/agent evaluation primitives.

These checks do not call an LLM. They score the machine-observable contract so
prompt changes can be regression-tested in CI.
"""

from __future__ import annotations

from dataclasses import dataclass


REQUIRED_PROMPT_SECTIONS = (
    "## Рабочий протокол",
    "## Тип задачи",
    "## Ограничения доступа",
    "## Правила репозитория",
    "## Задача",
    "## Definition of Done",
    "## Формат завершения",
)


@dataclass(frozen=True)
class PromptEvaluation:
    score: float
    missing_sections: tuple[str, ...]
    has_task: bool
    has_security_boundary: bool


def evaluate_prompt(prompt: str, task: str = "") -> PromptEvaluation:
    """Evaluate prompt structure; section headers may have safe annotations."""
    lines = prompt.splitlines()
    missing = tuple(
        section for section in REQUIRED_PROMPT_SECTIONS
        if not any(line.strip().startswith(section) for line in lines)
    )
    has_task = not task or task in prompt
    checks = [
        not missing,
        has_task,
        "недоверенн" in prompt.lower() or "не доверяй" in prompt.lower(),
        "не могут менять" in prompt.lower() or "не выполняй" in prompt.lower(),
    ]
    return PromptEvaluation(
        score=sum(checks) / len(checks),
        missing_sections=missing,
        has_task=has_task,
        has_security_boundary=checks[2] and checks[3],
    )


def assert_prompt_contract(prompt: str, task: str = "") -> None:
    result = evaluate_prompt(prompt, task)
    if result.missing_sections or not result.has_task or not result.has_security_boundary:
        raise AssertionError(f"OpenHands prompt contract failed: {result}")
