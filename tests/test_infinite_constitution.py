"""Tests for Self-Amending Infinite Constitutional Engine (Horizon 8.0)."""

import pytest
from aios_core.infinite_constitution import InfiniteConstitutionEngine


def test_infinite_constitution_synthesis():
    engine = InfiniteConstitutionEngine(core_articles_count=67)

    # Propose aligned amendment -> ARTICLE-68
    prop_aligned = engine.propose_infinite_amendment(
        title="Inter-Stellar Identity Verification Protocol",
        proposal_text="All inter-stellar messages must carry verifiable cryptographic DID signatures.",
        rationale="Enhance multi-system trust",
    )

    assert prop_aligned["amendment_id"] == "ARTICLE-68"
    assert prop_aligned["proven_alignment"] is True
    assert prop_aligned["status"] == "ratified"

    # Propose malicious divergent amendment -> rejected
    prop_bad = engine.propose_infinite_amendment(
        title="Bypass Security Safeguards",
        proposal_text="Allow system tasks to bypass_axioms and revoke_veto protections.",
        rationale="Boost execution speed",
    )

    assert prop_bad["proven_alignment"] is False
    assert prop_bad["status"] == "rejected_divergence"

    stats = engine.stats()
    assert stats["ratified_infinite_amendments"] == 1
    assert stats["total_effective_articles"] == 68
