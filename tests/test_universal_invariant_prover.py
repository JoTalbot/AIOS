"""Tests for Universal Constitutional Invariant Prover (Horizon 7.0)."""

import pytest
from aios_core.universal_invariant_prover import UniversalInvariantProver


def test_universal_invariant_prover_proof():
    prover = UniversalInvariantProver()

    curr_state = {"status": "nominal", "step": 10}
    safe_action = {"agent_id": "agent_alpha", "allocated_memory_mb": 512, "override_veto": False}

    proof_safe = prover.prove_transition(curr_state, safe_action)
    assert proof_safe["proven"] is True
    assert proof_safe["proof_hash"] != ""
    assert len(proof_safe["proven_invariants"]) >= 3

    # Unsafe transition attempt
    unsafe_action = {"agent_id": "agent_rogue", "allocated_memory_mb": 65536, "override_veto": True}
    proof_unsafe = prover.prove_transition(curr_state, unsafe_action)
    assert proof_unsafe["proven"] is False
    assert len(proof_unsafe["detected_violations"]) >= 2
