"""Conservative prompt optimization from observed agent metrics.

The optimizer proposes changes; it never mutates production prompts automatically.
This keeps prompt evolution reviewable and prevents a bad run from teaching the
system a bad instruction forever.
"""

from __future__ import annotations

from dataclasses import dataclass
from .agent_score import AgentScoreboard


@dataclass(frozen=True)
class PromptOptimizationSuggestion:
    role: str
    reason: str
    proposed_change: str
    evidence: str


def suggest_improvements(scoreboard: AgentScoreboard) -> tuple[PromptOptimizationSuggestion, ...]:
    suggestions: list[PromptOptimizationSuggestion] = []
    for role, stats in scoreboard.stats.items():
        if stats.attempts >= 5 and stats.reviewer_rejections / stats.attempts > 0.25:
            suggestions.append(PromptOptimizationSuggestion(role, "Высокая доля отклонений Reviewer", "Усилить role-specific preflight и acceptance criteria", f"rejections={stats.reviewer_rejections}/{stats.attempts}"))
        if stats.attempts >= 5 and stats.avg_iterations > 2.0:
            suggestions.append(PromptOptimizationSuggestion(role, "Слишком много итераций", "Добавить более ранний self-check и обязательные evidence", f"avg_iterations={stats.avg_iterations:.2f}"))
        if stats.security_violations:
            suggestions.append(PromptOptimizationSuggestion(role, "Обнаружены security violations", "Усилить security boundary и task/context firewall", f"security_violations={stats.security_violations}"))
    return tuple(suggestions)
