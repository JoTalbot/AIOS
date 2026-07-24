"""Social Intelligence for AIOS v10.7.0.

Social reasoning with relationship tracking, trust scores,
interaction history, norm enforcement, sentiment analysis,
and collaboration patterns.

Classes:
    TrustLevel     — trust score enum
    Relationship   — dyadic relationship between agents
    Interaction    — recorded interaction event
    SocialNorm     — behavioral norm with enforcement
    SocialIntelligence — full social reasoning engine
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TrustLevel(str, Enum):
    """Trust levels."""

    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    FULL = "full"


@dataclass
class Relationship:
    """Dyadic relationship between agents."""

    agent_a: str
    agent_b: str
    trust_score: float = 1.0  # 0..5
    cooperation_score: float = 1.0  # 0..5
    interaction_count: int = 0
    last_interaction: float | None = None
    status: str = "neutral"  # neutral, friendly, hostile

    def trust_level(self) -> TrustLevel:
        """Map trust score to TrustLevel."""
        if self.trust_score >= 4.0:
            return TrustLevel.FULL
        if self.trust_score >= 3.0:
            return TrustLevel.HIGH
        if self.trust_score >= 2.0:
            return TrustLevel.MEDIUM
        if self.trust_score >= 1.0:
            return TrustLevel.LOW
        return TrustLevel.UNKNOWN

    def record_interaction(self, outcome: str = "positive") -> None:
        """Record an interaction event."""
        self.interaction_count += 1
        self.last_interaction = time.time()
        if outcome == "positive":
            self.trust_score = min(self.trust_score + 0.1, 5.0)
            self.cooperation_score = min(self.cooperation_score + 0.1, 5.0)
        elif outcome == "negative":
            self.trust_score = max(self.trust_score - 0.2, 0.0)
            self.cooperation_score = max(self.cooperation_score - 0.2, 0.0)

        # Update status
        if self.trust_score >= 3.0:
            self.status = "friendly"
        elif self.trust_score <= 1.0:
            self.status = "hostile"
        else:
            self.status = "neutral"


@dataclass
class Interaction:
    """Recorded interaction event."""

    from_agent: str
    to_agent: str
    interaction_type: str = "communication"  # communication, cooperation, conflict
    outcome: str = "positive"  # positive, negative, neutral
    timestamp: float = field(default_factory=time.time)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SocialNorm:
    """Behavioral norm with enforcement."""

    name: str
    description: str = ""
    weight: float = 1.0  # importance weight
    violated_count: int = 0
    enforced_count: int = 0

    def evaluate(self, action: str, context: dict[str, Any]) -> bool:
        """Check if action complies with norm."""
        # Simple heuristic: check if action is in context
        compliant = action not in context.get("violations", [])
        if compliant:
            self.enforced_count += 1
        else:
            self.violated_count += 1
        return compliant


class SocialIntelligence:
    """Full social reasoning engine with relationships, trust, norms.

    Features:
    - Dyadic relationship tracking with trust/cooperation scores
    - Interaction history recording
    - Norm enforcement
    - Social reasoning (cooperate/communicate/avoid)
    - Trust-based recommendations
    - Collaboration pattern detection
    """

    def __init__(self) -> None:
        self.relationships: dict[str, Relationship] = {}
        self.interactions: list[Interaction] = []
        self.norms: list[SocialNorm] = (
            field(default_factory=list)
            if False
            else [
                SocialNorm("cooperation"),
                SocialNorm("fairness"),
                SocialNorm("reciprocity"),
            ]
        )
        self._norms_dict: dict[str, SocialNorm] = {
            "cooperation": SocialNorm(
                "cooperation", "Work together toward common goals"
            ),
            "fairness": SocialNorm("fairness", "Treat others equitably"),
            "reciprocity": SocialNorm("reciprocity", "Return favors and kindness"),
        }

    # ── Relationship Management ──────────────────────────────────

    def update_relationship(
        self, agent_a: str, agent_b: str, interaction: dict[str, Any]
    ) -> Relationship:
        """Update relationship based on interaction."""
        key = f"{agent_a}_{agent_b}"
        if key not in self.relationships:
            self.relationships[key] = Relationship(agent_a=agent_a, agent_b=agent_b)

        rel = self.relationships[key]
        outcome = interaction.get("outcome", "positive")
        rel.record_interaction(outcome)
        return rel

    def get_relationship(self, agent_a: str, agent_b: str) -> Relationship | None:
        """Return relationship between two agents."""
        key = f"{agent_a}_{agent_b}"
        return self.relationships.get(key)

    def get_trust(self, agent_a: str, agent_b: str) -> float:
        """Return trust score between agents."""
        rel = self.get_relationship(agent_a, agent_b)
        return rel.trust_score if rel else 1.0

    def get_trusted_agents(self, agent: str, min_trust: float = 3.0) -> list[str]:
        """Return agents trusted by the given agent."""
        trusted = []
        for rel in self.relationships.values():
            if rel.agent_a == agent and rel.trust_score >= min_trust:
                trusted.append(rel.agent_b)
            elif rel.agent_b == agent and rel.trust_score >= min_trust:
                trusted.append(rel.agent_a)
        return trusted

    # ── Interaction Recording ─────────────────────────────────────

    def record_interaction(
        self,
        from_agent: str,
        to_agent: str,
        interaction_type: str = "communication",
        outcome: str = "positive",
        details: dict[str, Any] | None = None,
    ) -> Interaction:
        """Record an interaction event."""
        interaction = Interaction(
            from_agent=from_agent,
            to_agent=to_agent,
            interaction_type=interaction_type,
            outcome=outcome,
            details=details or {},
        )
        self.interactions.append(interaction)
        # Update relationship
        self.update_relationship(from_agent, to_agent, {"outcome": outcome})
        return interaction

    def get_interactions(
        self, agent: str | None = None, limit: int = 50
    ) -> list[Interaction]:
        """Return interactions, optionally filtered by agent."""
        result = self.interactions
        if agent:
            result = [i for i in result if i.from_agent == agent or i.to_agent == agent]
        return result[-limit:]

    # ── Norm Management ──────────────────────────────────────────

    def add_norm(self, norm: SocialNorm) -> None:
        """Add a social norm."""
        self._norms_dict[norm.name] = norm

    def evaluate_norms(self, action: str, context: dict[str, Any]) -> dict[str, bool]:
        """Evaluate all norms against an action."""
        results = {}
        for name, norm in self._norms_dict.items():
            results[name] = norm.evaluate(action, context)
        return results

    # ── Social Reasoning ─────────────────────────────────────────

    def social_reasoning(self, context: dict[str, Any]) -> list[str]:
        """Recommend social actions based on context."""
        recommendations = []

        # High trust environment → cooperate
        trust_avg = (
            sum(r.trust_score for r in self.relationships.values())
            / len(self.relationships)
            if self.relationships
            else 1.0
        )
        if trust_avg >= 3.0:
            recommendations.extend(["cooperate", "communicate", "share_knowledge"])
        elif trust_avg >= 1.5:
            recommendations.extend(["communicate", "verify", "negotiate"])
        else:
            recommendations.extend(["avoid", "observe", "protect"])

        return recommendations

    def recommend_partner(self, agent: str, task: str = "") -> list[str]:
        """Recommend best collaboration partner based on trust."""
        trusted = self.get_trusted_agents(agent, min_trust=2.5)
        if not trusted:
            return []
        # Sort by trust score
        scored = []
        for other in trusted:
            trust = self.get_trust(agent, other)
            scored.append((other, trust))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in scored]

    # ── Stats ────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        avg_trust = (
            sum(r.trust_score for r in self.relationships.values())
            / len(self.relationships)
            if self.relationships
            else 0.0
        )
        return {
            "relationships": len(self.relationships),
            "norms": len(self._norms_dict),
            "interactions": len(self.interactions),
            "avg_trust": avg_trust,
        }
