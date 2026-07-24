"""Personalization Engine for AIOS v10.8.0.

User/agent personalization with profile management,
preference learning, recommendation scoring, feedback
integration, similarity-based recommendation, and
personalization metrics.

Classes:
    UserProfile    — entity profile with preferences
    PersonalizationEngine — full personalization engine
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """Entity profile with preferences and interaction history."""

    entity_id: str
    preferences: dict[str, Any] = field(default_factory=dict)
    interactions: int = 0
    feedback: list[dict[str, Any]] = field(default_factory=list)
    preference_scores: dict[str, float] = field(default_factory=dict)  # item → score
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)

    def preference_vector(self) -> list[float]:
        """Return preference scores as a vector."""
        if not self.preference_scores:
            return [0.5]
        return list(self.preference_scores.values())

    def top_preferences(self, limit: int = 5) -> list[tuple[str, float]]:
        """Return top preferences sorted by score."""
        sorted_prefs = sorted(
            self.preference_scores.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_prefs[:limit]


class PersonalizationEngine:
    """Full personalization engine.

    Features:
    - Profile creation and management
    - Preference learning from interactions
    - Recommendation scoring (cosine similarity)
    - Feedback integration (positive/negative)
    - Similarity-based recommendation
    - Personalization metrics (coverage, diversity)
    """

    def __init__(self, similarity_threshold: float = 0.3) -> None:
        self.profiles: dict[str, UserProfile] = {}
        self.similarity_threshold = similarity_threshold
        self._recommendation_history: list[dict[str, Any]] = []

    # ── Profile Management ──────────────────────────────────────────

    def create_profile(
        self, entity_id: str, preferences: dict[str, Any] | None = None
    ) -> UserProfile:
        """Create a new user/agent profile."""
        profile = UserProfile(entity_id=entity_id, preferences=preferences or {})
        self.profiles[entity_id] = profile
        return profile

    def get_profile(self, entity_id: str) -> UserProfile | None:
        """Return profile by ID."""
        return self.profiles.get(entity_id)

    def delete_profile(self, entity_id: str) -> None:
        """Delete a profile."""
        self.profiles.pop(entity_id, None)

    # ── Preference Learning ──────────────────────────────────────────

    def update(self, entity_id: str, interaction: dict[str, Any]) -> None:
        """Update profile based on interaction."""
        profile = self.profiles.get(entity_id)
        if profile is None:
            profile = self.create_profile(entity_id)
            self.profiles[entity_id] = profile

        profile.interactions += 1
        profile.last_updated = time.time()

        # Learn preferences from interaction
        item = interaction.get("item", "")
        action = interaction.get("action", "view")
        rating = interaction.get("rating", 0.5)

        if item:
            # Update preference score using EMA
            current_score = profile.preference_scores.get(item, 0.5)
            if action == "purchase" or action == "like":
                weight = 0.5
            elif action == "view":
                weight = 0.1
            elif action == "dislike":
                weight = -0.3
            else:
                weight = 0.1

            new_score = current_score + weight * (rating - current_score)
            profile.preference_scores[item] = round(new_score, 4)

            # Update category preferences
            category = interaction.get("category", "")
            if category:
                cat_score = profile.preferences.get(f"cat_{category}", 0.5)
                profile.preferences[f"cat_{category}"] = round(
                    cat_score + weight * 0.2, 4
                )

    # ── Recommendation ──────────────────────────────────────────────

    def recommend(
        self, entity_id: str, candidates: list[str] | None = None, limit: int = 10
    ) -> dict[str, Any]:
        """Recommend items based on profile preferences."""
        profile = self.profiles.get(entity_id)
        if profile is None:
            return {"recommended_action": "default", "confidence": 0.5, "items": []}

        # Score candidates
        scored_items = []
        if candidates:
            for item in candidates:
                score = profile.preference_scores.get(item, 0.5)
                # Boost score for items in preferred categories
                scored_items.append((item, score))
        else:
            # Recommend from known preferences
            scored_items = list(profile.preference_scores.items())

        # Sort by score
        scored_items.sort(key=lambda x: x[1], reverse=True)
        top_items = scored_items[:limit]

        avg_confidence = (
            (sum(s for _, s in top_items) / len(top_items)) if top_items else 0.5
        )

        result = {
            "recommended_action": "personalized",
            "confidence": round(avg_confidence, 4),
            "items": [
                {"item": item, "score": round(score, 4)} for item, score in top_items
            ],
            "profile_interactions": profile.interactions,
        }
        self._recommendation_history.append(result)
        return result

    def similar_users(self, entity_id: str, limit: int = 5) -> list[tuple[str, float]]:
        """Find similar users based on preference vectors."""
        target = self.profiles.get(entity_id)
        if target is None:
            return []

        similarities = []
        for other_id, other in self.profiles.items():
            if other_id == entity_id:
                continue
            sim = self._cosine_similarity(
                target.preference_vector(), other.preference_vector()
            )
            if sim >= self.similarity_threshold:
                similarities.append((other_id, round(sim, 4)))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Cosine similarity between two vectors."""
        max_len = max(len(a), len(b))
        a_pad = a + [0.0] * (max_len - len(a))
        b_pad = b + [0.0] * (max_len - len(b))
        dot = sum(x * y for x, y in zip(a_pad, b_pad, strict=False))
        na = math.sqrt(sum(x * x for x in a_pad))
        nb = math.sqrt(sum(y * y for y in b_pad))
        return dot / (na * nb) if na > 0 and nb > 0 else 0.0

    # ── Feedback ────────────────────────────────────────────────────

    def add_feedback(
        self, entity_id: str, item: str, rating: float, feedback_type: str = "explicit"
    ) -> None:
        """Add explicit or implicit feedback."""
        profile = self.profiles.get(entity_id)
        if profile is None:
            profile = self.create_profile(entity_id)
            self.profiles[entity_id] = profile

        feedback_entry = {
            "item": item,
            "rating": rating,
            "type": feedback_type,
            "timestamp": time.time(),
        }
        profile.feedback.append(feedback_entry)

        # Update preference score
        current = profile.preference_scores.get(item, 0.5)
        new_score = current + 0.3 * (rating - current)
        profile.preference_scores[item] = round(new_score, 4)

    # ── Metrics ──────────────────────────────────────────────────────

    def coverage(self) -> float:
        """Profile coverage (fraction of entities with sufficient interactions)."""
        if not self.profiles:
            return 0.0
        sufficient = sum(1 for p in self.profiles.values() if p.interactions >= 5)
        return sufficient / len(self.profiles)

    def diversity(self, entity_id: str) -> float:
        """Preference diversity for a user (entropy of scores)."""
        profile = self.profiles.get(entity_id)
        if profile is None or not profile.preference_scores:
            return 0.0

        scores = list(profile.preference_scores.values())
        total = sum(scores)
        if total == 0:
            return 0.0
        probs = [s / total for s in scores]
        entropy = -sum(p * math.log(p) for p in probs if p > 0)
        return round(entropy, 4)

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        avg_interactions = (
            (sum(p.interactions for p in self.profiles.values()) / len(self.profiles))
            if self.profiles
            else 0.0
        )
        return {
            "profiles": len(self.profiles),
            "avg_interactions": round(avg_interactions, 2),
            "recommendations": len(self._recommendation_history),
            "coverage": round(self.coverage(), 4),
        }
