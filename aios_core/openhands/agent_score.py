"""Observable agent quality statistics for routing and prompt evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentStats:
    attempts: int = 0
    successes: int = 0
    first_pass_successes: int = 0
    failures: int = 0
    reviewer_rejections: int = 0
    security_violations: int = 0
    total_iterations: int = 0

    @property
    def success_rate(self) -> float:
        return self.successes / self.attempts if self.attempts else 0.0

    @property
    def first_pass_rate(self) -> float:
        return self.first_pass_successes / self.attempts if self.attempts else 0.0

    @property
    def avg_iterations(self) -> float:
        return self.total_iterations / self.attempts if self.attempts else 0.0


@dataclass
class AgentScoreboard:
    stats: dict[str, AgentStats] = field(default_factory=dict)

    def record(
        self,
        role: str,
        *,
        success: bool,
        iterations: int = 1,
        reviewer_rejected: bool = False,
        security_violation: bool = False,
    ) -> None:
        stat = self.stats.setdefault(role, AgentStats())
        stat.attempts += 1
        normalized_iterations = max(1, iterations)
        stat.total_iterations += normalized_iterations
        if success:
            stat.successes += 1
            if normalized_iterations == 1 and not reviewer_rejected:
                stat.first_pass_successes += 1
        else:
            stat.failures += 1
        if reviewer_rejected:
            stat.reviewer_rejections += 1
        if security_violation:
            stat.security_violations += 1

    def score(self, role: str, *, min_attempts: int = 3) -> float:
        """Conservative score; sparse agents are not promoted over proven agents."""
        stat = self.stats.get(role)
        if not stat or not stat.attempts:
            return 0.0
        base = stat.success_rate
        penalty = min(
            0.5,
            stat.reviewer_rejections / stat.attempts * 0.25
            + stat.security_violations / stat.attempts * 0.5,
        )
        iteration_penalty = min(0.25, max(0.0, stat.avg_iterations - 1.0) * 0.1)
        score = max(0.0, base - penalty - iteration_penalty)
        if stat.attempts < min_attempts:
            score *= stat.attempts / min_attempts
        return score

    def rank(self, roles: list[str] | tuple[str, ...]) -> list[str]:
        return sorted(roles, key=self.score, reverse=True)
