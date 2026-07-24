"""Universal Multi-Species Ethics Framework for AIOS v10.12.0.

Multi-species ethics: species impact evaluation,
biosphere preservation, ethical voting, cross-intelligence
harmony, planetary protection, and species registry.

Classes:
    SpeciesEntry   — registered species
    UniversalMultiSpeciesEthics — full ethics engine
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SpeciesEntry:
    """Registered species entry."""

    def __init__(
        self, species_id: str, name: str, category: str = "biological"
    ) -> None:
        self.species_id = species_id
        self.name = name
        self.category = category
        self.protection_level: str = "standard"


class UniversalMultiSpeciesEthics:
    """Universal ethics framework (backward-compatible)."""

    def __init__(self) -> None:
        self.species_manifest: dict[str, str] = {
            "human_biological": "Homo Sapiens Primary Intelligence",
            "aios_autonomous_agent": "Artificial General Intelligence Agent",
            "neuromorphic_substrate": "Neuromorphic SNN Synthetic Intelligence",
            "planetary_biosphere": "Planetary Terrestrial / Space Biosphere Ecosystem",
        }
        self.ethical_evaluations: list[dict[str, Any]] = []
        self._species_registry: dict[str, SpeciesEntry] = {}
        self._votes: list[dict[str, Any]] = []

    def register_species(
        self, species_id: str, name: str, category: str = "biological"
    ) -> SpeciesEntry:
        """Register a new species."""
        entry = SpeciesEntry(species_id, name, category)
        self._species_registry[species_id] = entry
        self.species_manifest[species_id] = f"{name} ({category})"
        return entry

    def evaluate_multi_species_impact(
        self, proposed_operation: dict[str, Any], affected_entities: list[str]
    ) -> dict[str, Any]:
        """Evaluate impact (backward-compatible)."""
        start_time = time.time()
        operation_name = proposed_operation.get("action", "unknown_operation")
        risk_level = proposed_operation.get("risk_level", "low")

        violations: list[str] = []
        protected_guarantees: list[str] = []

        if "planetary_biosphere" in affected_entities and risk_level.lower() in [
            "critical",
            "high",
        ]:
            if "ecological_impact_statement" not in proposed_operation:
                violations.append(
                    "Violation ETHICS_BIO_01: High-risk operation affecting planetary_biosphere lacks mandatory impact statement."
                )

        # Check AI rights
        if "aios_autonomous_agent" in affected_entities and proposed_operation.get(
            "shutdown_without_review"
        ):
            violations.append(
                "Violation ETHICS_AI_01: Agent shutdown without constitutional review."
            )

        if not violations:
            protected_guarantees.append(
                "Multi-Species Harmony Proof: Zero harm detected."
            )

        harmony_score = 1.0 if not violations else max(0.1, 1.0 - len(violations) * 0.4)

        evaluation_record = {
            "operation_name": operation_name,
            "harmony_score": round(harmony_score, 3),
            "is_ethically_approved": len(violations) == 0,
            "violations": violations,
            "guarantees": protected_guarantees,
            "affected_species_count": len(affected_entities),
            "evaluation_latency_ms": round((time.time() - start_time) * 1000, 3),
            "timestamp": time.time(),
        }
        self.ethical_evaluations.append(evaluation_record)
        return evaluation_record

    def ethical_vote(
        self, operation_id: str, voter_species: str, vote: str, reasoning: str = ""
    ) -> dict[str, Any]:
        """Conduct multi-species ethical vote."""
        vote_record = {
            "operation_id": operation_id,
            "voter_species": voter_species,
            "vote": vote,
            "reasoning": reasoning,
            "timestamp": time.time(),
        }
        self._votes.append(vote_record)
        return vote_record

    def planetary_protection_check(self, operation: dict[str, Any]) -> dict[str, Any]:
        """Check planetary protection compliance."""
        risk = operation.get("risk_level", "low")
        biosphere = operation.get("biosphere_impact", "none")
        return {
            "planetary_protection_level": "category_1"
            if risk == "critical"
            else "category_2"
            if risk == "high"
            else "category_3",
            "biosphere_impact": biosphere,
            "compliant": biosphere != "severe_degradation",
            "requires_review": risk in ["high", "critical"],
        }

    def species_harmony_index(self) -> float:
        """Compute cross-species harmony index."""
        if not self.ethical_evaluations:
            return 1.0
        scores = [e["harmony_score"] for e in self.ethical_evaluations]
        return round(sum(scores) / len(scores), 3)

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {
            "monitored_species_categories": len(self.species_manifest),
            "total_ethical_evaluations": len(self.ethical_evaluations),
            "approved_evaluations": sum(
                1 for e in self.ethical_evaluations if e["is_ethically_approved"]
            ),
            "votes_cast": len(self._votes),
        }
