"""Bayesian Inference for AIOS v10.8.0.

Bayesian belief updating with prior/posterior tracking,
hypothesis comparison, sequential updating, confidence
intervals, marginal likelihood estimation, and evidence
accumulation.

Classes:
    Hypothesis    — named hypothesis with prior/posterior
    BayesianInference — full Bayesian reasoning engine
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Hypothesis:
    """Named hypothesis with prior, posterior, and evidence history."""

    name: str
    prior: float = 0.5
    posterior: float = 0.5
    evidence_count: int = 0
    likelihood_true: float = 0.8
    likelihood_false: float = 0.2
    created_at: float = field(default_factory=time.time)
    last_updated: float | None = None

    def confidence(self) -> float:
        """Return confidence interval width."""
        return abs(self.posterior - self.prior)

    def odds_ratio(self) -> float:
        """Return posterior odds ratio."""
        if self.posterior <= 0.0 or self.posterior >= 1.0:
            return float("inf") if self.posterior >= 1.0 else 0.0
        return self.posterior / (1.0 - self.posterior)


class BayesianInference:
    """Full Bayesian reasoning engine.

    Features:
    - Belief updating with Bayes' theorem
    - Hypothesis comparison and ranking
    - Sequential evidence accumulation
    - Marginal likelihood estimation
    - Confidence interval estimation
    - Prior reset and decay
    """

    def __init__(self, default_prior: float = 0.5) -> None:
        self.hypotheses: dict[str, Hypothesis] = {}
        self.default_prior = default_prior
        self.evidence_log: list[dict[str, Any]] = []

    # ── Hypothesis Management ──────────────────────────────────────

    def add_hypothesis(
        self,
        name: str,
        prior: float = 0.5,
        likelihood_true: float = 0.8,
        likelihood_false: float = 0.2,
    ) -> Hypothesis:
        """Register a new hypothesis."""
        h = Hypothesis(
            name=name,
            prior=prior,
            posterior=prior,
            likelihood_true=likelihood_true,
            likelihood_false=likelihood_false,
        )
        self.hypotheses[name] = h
        return h

    def remove_hypothesis(self, name: str) -> None:
        """Remove a hypothesis."""
        self.hypotheses.pop(name, None)

    def get_hypothesis(self, name: str) -> Hypothesis | None:
        """Return hypothesis by name."""
        return self.hypotheses.get(name)

    # ── Belief Updating ────────────────────────────────────────────

    def update_belief(
        self, hypothesis: str, evidence: bool, likelihood: float = 0.8
    ) -> float:
        """Update belief using Bayes' theorem.

        P(H|E) = P(E|H) * P(H) / P(E)
        """
        if hypothesis not in self.hypotheses:
            self.add_hypothesis(hypothesis, self.default_prior)

        h = self.hypotheses[hypothesis]
        prior = h.posterior  # use current posterior as prior for sequential updates

        if evidence:
            lh = likelihood if likelihood > 0 else h.likelihood_true
            posterior = (lh * prior) / (lh * prior + (1 - lh) * (1 - prior))
        else:
            lh_neg = 1 - likelihood if likelihood < 1 else h.likelihood_false
            posterior = (lh_neg * prior) / (lh_neg * prior + (1 - lh_neg) * (1 - prior))

        posterior = max(0.001, min(0.999, posterior))  # avoid extremes
        h.posterior = round(posterior, 6)
        h.evidence_count += 1
        h.last_updated = time.time()

        self.evidence_log.append(
            {
                "hypothesis": hypothesis,
                "evidence": evidence,
                "prior": prior,
                "posterior": h.posterior,
                "likelihood": likelihood,
            }
        )

        return h.posterior

    def update_batch(self, updates: list[tuple[str, bool, float]]) -> dict[str, float]:
        """Batch update multiple hypotheses."""
        results = {}
        for hypothesis, evidence, likelihood in updates:
            results[hypothesis] = self.update_belief(hypothesis, evidence, likelihood)
        return results

    # ── Belief Retrieval ───────────────────────────────────────────

    def get_belief(self, hypothesis: str) -> float:
        """Return current belief (posterior) for a hypothesis."""
        h = self.hypotheses.get(hypothesis)
        return h.posterior if h else self.default_prior

    def get_all_beliefs(self) -> dict[str, float]:
        """Return all current beliefs."""
        return {name: h.posterior for name, h in self.hypotheses.items()}

    def get_confidence_interval(
        self, hypothesis: str, width: float = 0.95
    ) -> tuple[float, float]:
        """Approximate confidence interval for posterior."""
        h = self.hypotheses.get(hypothesis)
        if h is None:
            return (0.0, 1.0)
        # Use Wilson score interval approximation
        n = max(h.evidence_count, 1)
        p = h.posterior
        z = 1.96 if width == 0.95 else 2.576 if width == 0.99 else 1.0
        denom = 1 + z * z / n
        center = (p + z * z / (2 * n)) / denom
        margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
        return (max(0.0, center - margin), min(1.0, center + margin))

    # ── Hypothesis Comparison ──────────────────────────────────────

    def compare_hypotheses(self, h1: str, h2: str) -> dict[str, Any]:
        """Compare two hypotheses by their posteriors."""
        b1 = self.get_belief(h1)
        b2 = self.get_belief(h2)
        ratio = b1 / b2 if b2 > 0 else float("inf")
        return {
            "h1": h1,
            "h2": h2,
            "belief_h1": b1,
            "belief_h2": b2,
            "ratio": round(ratio, 4),
            "winner": h1 if b1 > b2 else h2 if b2 > b1 else "tie",
        }

    def rank_hypotheses(self) -> list[tuple[str, float]]:
        """Rank hypotheses by posterior probability."""
        ranked = sorted(
            self.hypotheses.items(), key=lambda x: x[1].posterior, reverse=True
        )
        return [(name, h.posterior) for name, h in ranked]

    def most_probable(self) -> str | None:
        """Return the most probable hypothesis."""
        if not self.hypotheses:
            return None
        return max(self.hypotheses.items(), key=lambda x: x[1].posterior)[0]

    # ── Marginal Likelihood ────────────────────────────────────────

    def marginal_likelihood(self, evidence: bool, likelihood: float = 0.8) -> float:
        """Compute marginal likelihood P(E) across all hypotheses."""
        total = 0.0
        for h in self.hypotheses.values():
            prior = h.posterior
            lh = likelihood if evidence else 1 - likelihood
            total += lh * prior
        return total if total > 0 else 0.5

    # ── Reset ──────────────────────────────────────────────────────

    def reset_hypothesis(self, name: str, prior: float = 0.5) -> None:
        """Reset a hypothesis to a new prior."""
        h = self.hypotheses.get(name)
        if h:
            h.prior = prior
            h.posterior = prior
            h.evidence_count = 0

    def reset_all(self) -> None:
        """Reset all hypotheses to their original priors."""
        for h in self.hypotheses.values():
            h.posterior = h.prior
            h.evidence_count = 0

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        beliefs = [h.posterior for h in self.hypotheses.values()]
        avg = sum(beliefs) / len(beliefs) if beliefs else 0.5
        return {
            "hypotheses": len(self.hypotheses),
            "avg_belief": round(avg, 4),
            "evidence_count": sum(h.evidence_count for h in self.hypotheses.values()),
            "most_probable": self.most_probable(),
        }
