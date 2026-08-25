"""Conservative adaptive routing for OpenHands agents."""

from __future__ import annotations

from dataclasses import dataclass

from .agent_score import AgentScoreboard
from .models import AgentRole


@dataclass(frozen=True)
class RouteDecision:
    role: AgentRole
    score: float
    reason: str


class AdaptiveRouter:
    """Selects among equivalent specialists without allowing sparse data to dominate."""

    def __init__(self, scoreboard: AgentScoreboard) -> None:
        self.scoreboard = scoreboard

    def choose(self, candidates: tuple[AgentRole, ...], *, task_type: str = "feature") -> RouteDecision:
        if not candidates:
            raise ValueError("candidates must not be empty")
        ranked = self.scoreboard.rank([role.value for role in candidates])
        selected_name = ranked[0] if ranked else candidates[0].value
        selected = next(role for role in candidates if role.value == selected_name)
        score = self.scoreboard.score(selected.value)
        reason = "scoreboard ranking" if self.scoreboard.stats else "no history; deterministic first candidate"
        return RouteDecision(selected, score, reason)


def default_route_candidates(task_type: str) -> tuple[AgentRole, ...]:
    if task_type in {"security", "audit"}:
        return (AgentRole.SECURITY, AgentRole.REVIEWER)
    if task_type in {"test", "bugfix"}:
        return (AgentRole.TESTER, AgentRole.CODER)
    return (AgentRole.CODER, AgentRole.REVIEWER)
