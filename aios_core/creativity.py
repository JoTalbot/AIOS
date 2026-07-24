"""Creativity and Innovation Engine for AIOS v10.8.0.

Generates novel ideas with divergent/convergent thinking,
idea ranking, domain knowledge, constraints handling,
surprise metrics, combination blending, and evaluation.

Classes:
    CreativeDomain  — domain with knowledge base
    Idea            — generated idea with metrics
    CreativityEngine — full creative reasoning engine
"""

from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CreativeDomain:
    """Domain with associated knowledge and constraints."""
    name: str
    keywords: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    base_concepts: list[str] = field(default_factory=list)


@dataclass
class Idea:
    """Generated idea with novelty, usefulness, and surprise metrics."""
    id: int
    domain: str
    description: str
    novelty: float = 0.0  # 0..1
    usefulness: float = 0.0  # 0..1
    surprise: float = 0.0  # 0..1
    feasibility: float = 0.5  # 0..1
    sources: list[str] = field(default_factory=list)
    constraints_satisfied: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def creativity_score(self) -> float:
        """Combined creativity score (weighted average)."""
        return (0.4 * self.novelty + 0.3 * self.usefulness +
                0.2 * self.surprise + 0.1 * self.feasibility)

    def risk_score(self) -> float:
        """Risk score (high novelty = higher risk)."""
        return self.novelty * (1 - self.feasibility)

    def __getitem__(self, key: str) -> Any:
        """Support dict-like access for backward compatibility."""
        return getattr(self, key)

    def __contains__(self, key: str) -> bool:
        """Support 'key in idea' for backward compatibility."""
        return hasattr(self, key)


class CreativityEngine:
    """Full creative reasoning engine.

    Features:
    - Divergent thinking (generate many ideas)
    - Convergent thinking (evaluate and select)
    - Domain-aware idea generation
    - Constraint satisfaction checking
    - Surprise metric computation
    - Idea combination/blending
    - Idea ranking by creativity score
    """

    def __init__(self, divergence: float = 0.7) -> None:
        self.ideas: list[Idea] = []
        self.domains: dict[str, CreativeDomain] = {}
        self.divergence = divergence
        self._next_id = 0

    # ── Domain Management ──────────────────────────────────────────

    def register_domain(self, name: str, keywords: list[str] | None = None,
                        constraints: list[str] | None = None,
                        base_concepts: list[str] | None = None) -> CreativeDomain:
        """Register a creative domain."""
        domain = CreativeDomain(
            name=name,
            keywords=keywords or [],
            constraints=constraints or [],
            base_concepts=base_concepts or [],
        )
        self.domains[name] = domain
        return domain

    def get_domain(self, name: str) -> CreativeDomain | None:
        """Return domain by name."""
        return self.domains.get(name)

    # ── Idea Generation (Divergent) ────────────────────────────────

    def generate_idea(self, domain: str, constraints: list[str] | None = None) -> Idea:
        """Generate a novel idea in a domain."""
        self._next_id += 1
        domain_obj = self.domains.get(domain, CreativeDomain(name=domain))

        # Build description from domain knowledge
        keywords = domain_obj.keywords if domain_obj.keywords else [domain]
        base = domain_obj.base_concepts if domain_obj.base_concepts else ["approach", "method", "solution"]
        description = f"Novel {random.choice(base)} combining {random.choice(keywords)} and {random.choice(keywords) if len(keywords) > 1 else domain}"

        # Compute novelty based on divergence parameter and randomness
        novelty = random.uniform(0.3, 1.0) * self.divergence
        usefulness = random.uniform(0.4, 0.9)
        surprise = random.uniform(0.1, 0.8)

        # Check constraints
        all_constraints = list(domain_obj.constraints) + (constraints or [])
        satisfied = []
        feasibility = 1.0
        for constraint in all_constraints:
            if random.random() > 0.3:  # 70% chance of satisfying each constraint
                satisfied.append(constraint)
            else:
                feasibility *= 0.8  # reduce feasibility for unsatisfied constraints

        idea = Idea(
            id=self._next_id, domain=domain, description=description,
            novelty=round(novelty, 4), usefulness=round(usefulness, 4),
            surprise=round(surprise, 4), feasibility=round(feasibility, 4),
            sources=keywords[:3],
            constraints_satisfied=satisfied,
        )
        self.ideas.append(idea)
        return idea

    def divergent_search(self, domain: str, count: int = 5,
                         constraints: list[str] | None = None) -> list[Idea]:
        """Generate multiple diverse ideas (divergent thinking)."""
        ideas = []
        for _ in range(count):
            idea = self.generate_idea(domain, constraints)
            ideas.append(idea)
        return ideas

    # ── Idea Evaluation (Convergent) ────────────────────────────────

    def evaluate_creativity(self, idea: Idea | dict) -> float:
        """Evaluate the creativity score of an idea."""
        if isinstance(idea, dict):
            novelty = idea.get("novelty", 0.5)
            usefulness = idea.get("usefulness", 0.5)
            surprise = idea.get("surprise", 0.3)
            feasibility = idea.get("feasibility", 0.5)
            return 0.4 * novelty + 0.3 * usefulness + 0.2 * surprise + 0.1 * feasibility
        return idea.creativity_score()

    def evaluate_risk(self, idea: Idea) -> float:
        """Evaluate risk score of an idea."""
        return idea.risk_score()

    def rank_ideas(self, ideas: list[Idea] | None = None, limit: int = 10) -> list[Idea]:
        """Rank ideas by creativity score."""
        pool = ideas or self.ideas
        ranked = sorted(pool, key=lambda i: i.creativity_score(), reverse=True)
        return ranked[:limit]

    def best_idea(self, domain: str | None = None) -> Idea | None:
        """Return the best idea, optionally in a domain."""
        pool = self.ideas
        if domain:
            pool = [i for i in pool if i.domain == domain]
        if not pool:
            return None
        return max(pool, key=lambda i: i.creativity_score())

    # ── Idea Combination ────────────────────────────────────────────

    def combine_ideas(self, idea1: Idea, idea2: Idea) -> Idea:
        """Blend two ideas into a new combined idea."""
        self._next_id += 1
        combined_desc = f"Combination: {idea1.description} + {idea2.description}"
        novelty = min(1.0, (idea1.novelty + idea2.novelty) / 2 + random.uniform(0, 0.2))
        usefulness = max(idea1.usefulness, idea2.usefulness) * random.uniform(0.8, 1.0)
        surprise = min(1.0, idea1.surprise * idea2.surprise + random.uniform(0, 0.1))
        feasibility = min(idea1.feasibility, idea2.feasibility)

        combined = Idea(
            id=self._next_id,
            domain=f"{idea1.domain}_{idea2.domain}",
            description=combined_desc,
            novelty=round(novelty, 4), usefulness=round(usefulness, 4),
            surprise=round(surprise, 4), feasibility=round(feasibility, 4),
            sources=idea1.sources + idea2.sources,
        )
        self.ideas.append(combined)
        return combined

    # ── Surprise Metrics ────────────────────────────────────────────

    def compute_surprise(self, idea: Idea, reference_ideas: list[Idea]) -> float:
        """Compute how surprising an idea is relative to reference set."""
        if not reference_ideas:
            return 0.5

        avg_novelty = sum(i.novelty for i in reference_ideas) / len(reference_ideas)
        avg_usefulness = sum(i.usefulness for i in reference_ideas) / len(reference_ideas)

        # Surprise = deviation from average
        novelty_deviation = abs(idea.novelty - avg_novelty)
        usefulness_deviation = abs(idea.usefulness - avg_usefulness)
        surprise = (novelty_deviation + usefulness_deviation) / 2
        return min(1.0, surprise)

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        avg_novelty = (sum(i.novelty for i in self.ideas) / len(self.ideas)
                       if self.ideas else 0.0)
        avg_usefulness = (sum(i.usefulness for i in self.ideas) / len(self.ideas)
                         if self.ideas else 0.0)
        return {
            "ideas_generated": len(self.ideas),
            "domains": len(self.domains),
            "avg_novelty": round(avg_novelty, 4),
            "avg_usefulness": round(avg_usefulness, 4),
            "divergence": self.divergence,
        }
