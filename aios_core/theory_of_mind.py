"""Theory of Mind for AIOS Agents v10.8.0.

BDI (Belief-Desire-Intention) model, belief revision,
desire hierarchy, intention tracking, action prediction,
mental state attribution, and social reasoning.

Classes:
    Belief         — agent belief with confidence
    Desire         — agent desire/goal with priority
    Intention      — agent intention with commitment
    TheoryOfMind   — full ToM reasoning engine
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class Belief:
    """Agent belief with confidence and source."""
    content: str
    confidence: float = 0.8  # 0..1
    source: str = "observation"
    timestamp: float = field(default_factory=time.time)


@dataclass
class Desire:
    """Agent desire/goal with priority."""
    content: str
    priority: float = 0.5  # 0..1 (higher = more important)
    achievable: float = 0.7  # 0..1 (estimated feasibility)
    category: str = "general"  # safety, social, achievement, etc.


@dataclass
class Intention:
    """Agent intention with commitment level."""
    content: str
    commitment: float = 0.8  # 0..1
    desire_source: str = ""  # linked desire
    progress: float = 0.0  # 0..1
    created_at: float = field(default_factory=time.time)


class TheoryOfMind:
    """Full Theory of Mind reasoning engine.

    Features:
    - BDI model (Belief-Desire-Intention)
    - Multi-agent mental state modeling
    - Belief revision (update when contradicted)
    - Desire hierarchy (prioritize goals)
    - Intention tracking with progress
    - Action prediction based on mental models
    - Social reasoning (cooperation/competition)
    - Mental state attribution
    """

    def __init__(self) -> None:
        self.models: dict[str, dict[str, Any]] = {}
        self.beliefs: dict[str, dict[str, Belief]] = {}  # agent → belief dict
        self.desires: dict[str, list[Desire]] = {}  # agent → desire list
        self.intentions: dict[str, list[Intention]] = {}  # agent → intention list

    # ── Agent Modeling ──────────────────────────────────────────────

    def model_agent(self, agent_id: str, beliefs: dict[str, Any] | None = None,
                    desires: list[str] | None = None,
                    intentions: list[str] | None = None) -> None:
        """Model an agent's mental state (BDI)."""
        self.models[agent_id] = {
            "beliefs": beliefs or {},
            "desires": desires or [],
            "intentions": intentions or [],
        }

        # Convert to structured BDI objects
        if beliefs:
            self.beliefs[agent_id] = {
                key: Belief(content=str(val)) for key, val in beliefs.items()
            }
        else:
            self.beliefs[agent_id] = {}

        self.desires[agent_id] = [
            Desire(content=d, priority=random.uniform(0.3, 0.9)) for d in (desires or [])
        ]
        self.intentions[agent_id] = [
            Intention(content=i) for i in (intentions or [])
        ]

    def update_model(self, agent_id: str, new_beliefs: dict[str, Any] | None = None,
                     new_desires: list[str] | None = None) -> None:
        """Update an agent's mental model."""
        if agent_id not in self.models:
            self.model_agent(agent_id)

        if new_beliefs:
            for key, val in new_beliefs.items():
                self.beliefs.setdefault(agent_id, {})[key] = Belief(content=str(val))
            self.models[agent_id]["beliefs"].update(new_beliefs)

        if new_desires:
            for d in new_desires:
                self.desires.setdefault(agent_id, []).append(Desire(content=d))
            self.models[agent_id]["desires"].extend(new_desires)

    def remove_agent_model(self, agent_id: str) -> None:
        """Remove an agent's model."""
        self.models.pop(agent_id, None)
        self.beliefs.pop(agent_id, None)
        self.desires.pop(agent_id, None)
        self.intentions.pop(agent_id, None)

    # ── Belief Revision ──────────────────────────────────────────────

    def revise_belief(self, agent_id: str, key: str, new_value: str,
                      confidence: float = 0.8, source: str = "new_observation") -> Belief:
        """Revise an agent's belief with new information."""
        agent_beliefs = self.beliefs.setdefault(agent_id, {})
        old_belief = agent_beliefs.get(key)

        if old_belief and old_belief.confidence >= confidence:
            # Conflicting belief with equal/higher confidence: reduce new confidence
            confidence *= 0.7

        new_belief = Belief(content=new_value, confidence=confidence, source=source)
        agent_beliefs[key] = new_belief
        return new_belief

    def get_beliefs(self, agent_id: str) -> dict[str, Belief]:
        """Return all beliefs for an agent."""
        return self.beliefs.get(agent_id, {})

    def get_confident_beliefs(self, agent_id: str, min_confidence: float = 0.7) -> list[Belief]:
        """Return high-confidence beliefs."""
        beliefs = self.beliefs.get(agent_id, {})
        return [b for b in beliefs.values() if b.confidence >= min_confidence]

    # ── Desire Management ──────────────────────────────────────────

    def add_desire(self, agent_id: str, content: str, priority: float = 0.5,
                   achievable: float = 0.7, category: str = "general") -> Desire:
        """Add a desire/goal for an agent."""
        desire = Desire(content=content, priority=priority,
                        achievable=achievable, category=category)
        self.desires.setdefault(agent_id, []).append(desire)
        return desire

    def prioritize_desires(self, agent_id: str) -> list[Desire]:
        """Return desires sorted by priority (highest first)."""
        desires = self.desires.get(agent_id, [])
        return sorted(desires, key=lambda d: d.priority * d.achievable, reverse=True)

    def top_desire(self, agent_id: str) -> Desire | None:
        """Return the highest-priority achievable desire."""
        prioritized = self.prioritize_desires(agent_id)
        return prioritized[0] if prioritized else None

    # ── Intention Management ────────────────────────────────────────

    def add_intention(self, agent_id: str, content: str,
                      desire_source: str = "", commitment: float = 0.8) -> Intention:
        """Add an intention for an agent."""
        intention = Intention(content=content, desire_source=desire_source,
                              commitment=commitment)
        self.intentions.setdefault(agent_id, []).append(intention)
        return intention

    def update_intention_progress(self, agent_id: str, content: str,
                                  progress: float) -> None:
        """Update progress on an intention."""
        for intention in self.intentions.get(agent_id, []):
            if intention.content == content:
                intention.progress = progress

    def active_intentions(self, agent_id: str) -> list[Intention]:
        """Return active (in-progress) intentions."""
        return [i for i in self.intentions.get(agent_id, [])
                if i.commitment > 0.3 and i.progress < 1.0]

    # ── Action Prediction ──────────────────────────────────────────

    def predict_action(self, agent_id: str, situation: dict[str, Any]) -> str:
        """Predict an agent's action based on their mental model."""
        model = self.models.get(agent_id, {})

        # Check if agent has harmful beliefs or desires
        beliefs = self.beliefs.get(agent_id, {})
        desires = self.desires.get(agent_id, [])
        intentions = self.intentions.get(agent_id, [])

        # Check for harm-related beliefs/desires
        if "harm" in str(situation) or "harm" in str(beliefs):
            # If agent believes situation is harmful
            has_safety_desire = any(d.category == "safety" for d in desires)
            if has_safety_desire:
                return "avoid"
            return "defend"

        # Check desires: top desire drives behavior
        top = self.top_desire(agent_id)
        if top:
            if top.category == "social":
                return "cooperate"
            elif top.category == "achievement":
                return "strive"
            elif top.category == "safety":
                return "protect"

        # Default: based on situation context
        if "collaborate" in str(situation):
            return "cooperate"
        if "compete" in str(situation):
            return "compete"

        return "observe"

    # ── Mental State Attribution ────────────────────────────────────

    def attribute_mental_state(self, agent_id: str, observed_action: str) -> dict[str, Any]:
        """Attribute mental state based on observed action."""
        if observed_action in ("cooperate", "share", "help"):
            return {
                "likely_desires": "social harmony",
                "likely_beliefs": "trustworthy environment",
                "emotional_state": "positive",
                "confidence": 0.7,
            }
        elif observed_action in ("defect", "attack", "hoard"):
            return {
                "likely_desires": "self-interest",
                "likely_beliefs": "competitive/threatening environment",
                "emotional_state": "negative",
                "confidence": 0.6,
            }
        elif observed_action in ("avoid", "protect"):
            return {
                "likely_desires": "safety",
                "likely_beliefs": "dangerous environment",
                "emotional_state": "fearful",
                "confidence": 0.5,
            }
        return {
            "likely_desires": "unknown",
            "likely_beliefs": "unknown",
            "emotional_state": "neutral",
            "confidence": 0.3,
        }

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        total_beliefs = sum(len(b) for b in self.beliefs.values())
        total_desires = sum(len(d) for d in self.desires.values())
        total_intentions = sum(len(i) for i in self.intentions.values())
        return {
            "modeled_agents": len(self.models),
            "total_beliefs": total_beliefs,
            "total_desires": total_desires,
            "total_intentions": total_intentions,
        }
