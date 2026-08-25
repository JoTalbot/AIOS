"""Deterministic aggregation of specialist micro-agent verdicts."""

from __future__ import annotations

from dataclasses import dataclass

from .models import ReviewDecision


@dataclass(frozen=True)
class SpecialistVerdict:
    name: str
    decision: ReviewDecision
    summary: str = ""


@dataclass(frozen=True)
class MetaReview:
    decision: ReviewDecision
    blockers: tuple[str, ...] = ()
    approved: tuple[str, ...] = ()


def aggregate_verdicts(verdicts: tuple[SpecialistVerdict, ...]) -> MetaReview:
    """Fail closed: any rejection blocks the meta-review; no verdict also blocks it."""
    if not verdicts:
        return MetaReview(ReviewDecision.CHANGES_REQUESTED, blockers=("no specialist verdicts",))
    blockers = tuple(v.name for v in verdicts if v.decision != ReviewDecision.APPROVED)
    approved = tuple(v.name for v in verdicts if v.decision == ReviewDecision.APPROVED)
    return MetaReview(
        ReviewDecision.CHANGES_REQUESTED if blockers else ReviewDecision.APPROVED,
        blockers=blockers,
        approved=approved,
    )
