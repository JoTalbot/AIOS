"""Specialist review fan-out and fail-closed aggregation for OpenHands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from .meta_review import MetaReview, SpecialistVerdict, aggregate_verdicts
from .micro_agents import MicroAgentSpec, select_micro_agents
from .models import AgentRole, ReviewDecision


@dataclass(frozen=True)
class SpecialistResult:
    spec: MicroAgentSpec
    verdict: ReviewDecision
    evidence: str = ""
    error: str | None = None


class SpecialistReviewPipeline:
    """Run selected specialist checks and produce one deterministic meta-verdict.

    The executor is injected so the pipeline stays independent from a concrete
    OpenHands client and can be tested without network access.
    """

    def __init__(self, executor: Callable[[MicroAgentSpec, str], SpecialistResult]):
        self._executor = executor

    def run(self, task_type: str, context: str = "") -> tuple[tuple[SpecialistResult, ...], MetaReview]:
        specs = select_micro_agents(task_type)
        results = tuple(self._executor(spec, context) for spec in specs)
        verdicts = tuple(
            SpecialistVerdict(
                name=result.spec.name,
                decision=result.verdict,
                summary=result.evidence,
            )
            for result in results
        )
        return results, aggregate_verdicts(verdicts)


def conservative_executor(spec: MicroAgentSpec, context: str) -> SpecialistResult:
    """Safe default when no specialist runtime is attached: fail closed."""
    return SpecialistResult(
        spec=spec,
        verdict=ReviewDecision.CHANGES_REQUESTED,
        error="specialist runtime is not attached",
    )
