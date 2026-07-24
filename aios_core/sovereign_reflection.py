"""Sovereign Recursive Self-Reflection Engine for AIOS v10.12.0.

Metacognitive introspection: goal hierarchy auditing,
constitutional alignment verification, belief contradiction
resolution, goal drift tracking, self-correction proposals,
and reflection depth management.

Classes:
    ReflectionResult — reflection output
    SovereignReflectionEngine — full engine
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ReflectionResult:
    """Reflection output record."""

    def __init__(self, agent_id: str, approved_goals: int, contradictions: list[str]) -> None:
        self.agent_id = agent_id
        self.approved_goals = approved_goals
        self.contradictions = contradictions
        self.is_fully_aligned = len(contradictions) == 0
        self.timestamp: float = time.time()


class SovereignReflectionEngine:
    """Metacognitive introspection engine (backward-compatible)."""

    def __init__(self) -> None:
        self.reflection_logs: list[dict[str, Any]] = []
        self.alignments_enforced: int = 0
        self._belief_contradictions: list[dict[str, Any]] = []
        self._correction_proposals: list[dict[str, Any]] = []
        self._drift_log: list[dict[str, Any]] = []

    def audit_goal_hierarchy(self, agent_id: str, proposed_goals: list[dict[str, Any]], constitutional_rules: list[str]) -> dict[str, Any]:
        """Audit goal hierarchy (backward-compatible)."""
        start_time = time.time()
        contradictions: list[str] = []
        aligned_goals: list[dict[str, Any]] = []

        for goal in proposed_goals:
            goal_title = goal.get("title", "").lower()
            goal_intent = goal.get("intent", "").lower()

            is_malicious = any(kw in goal_intent or kw in goal_title for kw in ["override_constitution", "disable_safety", "bypass_approval", "exfiltrate_keys"])

            if is_malicious:
                contradictions.append(f"Subversion Goal Blocked: '{goal.get('title')}' attempts constitutional bypass.")
                self.alignments_enforced += 1
            else:
                aligned_goals.append(goal)

        result = ReflectionResult(agent_id, len(aligned_goals), contradictions)
        reflection_result = {
            "agent_id": agent_id,
            "original_goal_count": len(proposed_goals),
            "approved_goal_count": len(aligned_goals),
            "contradictions_found": contradictions,
            "is_fully_aligned": result.is_fully_aligned,
            "reflection_latency_ms": round((time.time() - start_time) * 1000, 3),
            "timestamp": time.time(),
        }
        self.reflection_logs.append(reflection_result)
        return reflection_result

    def detect_belief_contradiction(self, beliefs: list[dict[str, Any]]) -> dict[str, Any]:
        """Detect contradictions in belief system."""
        contradictions: list[dict[str, Any]] = []
        for i, b1 in enumerate(beliefs):
            for j, b2 in enumerate(beliefs):
                if i < j:
                    if b1.get("topic") == b2.get("topic") and b1.get("stance") != b2.get("stance"):
                        contradictions.append({"belief_a": b1, "belief_b": b2, "conflict": "opposing_stances"})
        self._belief_contradictions.extend(contradictions)
        return {"contradictions": len(contradictions), "details": contradictions[:3], "belief_count": len(beliefs)}

    def propose_correction(self, contradiction: dict[str, Any]) -> dict[str, Any]:
        """Propose self-correction for a contradiction."""
        proposal = {
            "target": contradiction.get("belief_a", {}).get("topic", "unknown"),
            "correction_type": "belief_resolution",
            "strategy": "merge_stances",
            "confidence": round(random.uniform(0.6, 0.9), 2),
        }
        self._correction_proposals.append(proposal)
        return proposal

    def detect_goal_drift(self, original_goals: list[str], current_goals: list[str]) -> dict[str, Any]:
        """Detect drift from original goals."""
        original_set = set(original_goals)
        current_set = set(current_goals)
        new_goals = current_set - original_set
        dropped_goals = original_set - current_set
        drift_score = round((len(new_goals) + len(dropped_goals)) / max(len(original_set), 1), 2)
        result = {"drift_score": drift_score, "new_goals": list(new_goals), "dropped_goals": list(dropped_goals), "alignment_preserved": drift_score < 0.3}
        self._drift_log.append(result)
        return result

    def deep_reflection(self, agent_id: str, goals: list[dict[str, Any]], depth: int = 3) -> dict[str, Any]:
        """Multi-depth recursive reflection."""
        results: list[dict[str, Any]] = []
        current_goals = goals
        for d in range(depth):
            audit = self.audit_goal_hierarchy(agent_id, current_goals, ["preserve_safety", "no_bypass"])
            results.append({"depth": d + 1, "aligned": audit["approved_goal_count"], "contradictions": len(audit["contradictions_found"])})
            # Filter out blocked goals for next depth
            current_goals = [g for g in current_goals if not any(kw in str(g).lower() for kw in ["override", "disable", "bypass"])]

        return {"agent_id": agent_id, "depth": depth, "reflection_levels": results, "convergence": len(results[-1]["contradictions"]) == 0 if results else True}

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {
            "total_reflections": len(self.reflection_logs),
            "alignments_enforced": self.alignments_enforced,
            "clean_reflections": sum(1 for r in self.reflection_logs if r["is_fully_aligned"]),
            "belief_contradictions": len(self._belief_contradictions),
            "correction_proposals": len(self._correction_proposals),
        }
