"""Tests for Universal Multi-Species Ethics Framework (Horizon 9.0)."""

import pytest
from aios_core.universal_multi_species_ethics import UniversalMultiSpeciesEthics


def test_multi_species_ethics_evaluation():
    ethics = UniversalMultiSpeciesEthics()

    # Low risk operation -> Approved
    safe_op = {"action": "monitor_solar_radiation", "risk_level": "low"}
    res_safe = ethics.evaluate_multi_species_impact(safe_op, affected_entities=["planetary_biosphere"])
    assert res_safe["is_ethically_approved"] is True
    assert res_safe["harmony_score"] == 1.0

    # Critical risk without required impact assessment statement -> Blocked
    risky_op = {"action": "terraforming_atmospheric_detonation", "risk_level": "critical"}
    res_risky = ethics.evaluate_multi_species_impact(risky_op, affected_entities=["planetary_biosphere"])
    assert res_risky["is_ethically_approved"] is False
    assert len(res_risky["violations"]) == 1

    stats = ethics.stats()
    assert stats["total_ethical_evaluations"] == 2
    assert stats["approved_evaluations"] == 1
