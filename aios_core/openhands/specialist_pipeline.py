"""Specialist review fan-out and fail-closed aggregation for OpenHands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .meta_review import MetaReview, SpecialistVerdict, aggregate_verdicts
from .micro_agents import MicroAgentSpec, select_micro_agents
from .models import AgentRole, ReviewDecision


@dataclass(frozen=True)
class SpecialistResult:
    spec: MicroAgentSpec
    verdict: ReviewDecision
    evidence: str = ""
    error: str | None = None
    spawned: bool = False


class SpecialistReviewPipeline:
    """Run selected specialists, auto-spawn missing runtimes, then aggregate."""

    def __init__(self, executor: Callable[[MicroAgentSpec, str], SpecialistResult], spawner: Callable[[MicroAgentSpec, str], SpecialistResult] | None = None):
        self._executor = executor
        self._spawner = spawner

    def run(self, task_type: str, context: str = "") -> tuple[tuple[SpecialistResult, ...], MetaReview]:
        specs = select_micro_agents(task_type)
        results: list[SpecialistResult] = []
        for spec in specs:
            result = self._executor(spec, context)
            if result.error and self._spawner is not None:
                result = self._spawner(spec, context)
                if result.error is None:
                    result = SpecialistResult(result.spec, result.verdict, result.evidence, None, True)
            results.append(result)
        verdicts = tuple(SpecialistVerdict(name=r.spec.name, decision=r.verdict, summary=r.evidence) for r in results)
        return tuple(results), aggregate_verdicts(verdicts)


def conservative_executor(spec: MicroAgentSpec, context: str) -> SpecialistResult:
    """Safe default when no specialist runtime is attached: fail closed."""
    return SpecialistResult(spec=spec, verdict=ReviewDecision.CHANGES_REQUESTED, error="specialist runtime is not attached")
