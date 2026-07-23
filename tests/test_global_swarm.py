"""Tests for Global Swarm Governance & ZK Safety Proof Engine (Horizon 5.0)."""

import pytest

from aios_core.global_swarm import GlobalSwarmGovernance, ZeroKnowledgeSafetyProof


def test_zk_safety_proof():
    payload = {"task": "process_data", "privacy_flag": True, "level": 1}
    proof = ZeroKnowledgeSafetyProof.generate_proof(payload, secret_salt="secret_123")

    assert proof["commitment_hash"] != ""
    assert proof["proof_signature"] != ""

    # Verify valid commitment
    is_valid = ZeroKnowledgeSafetyProof.verify_proof(proof, proof["commitment_hash"])
    assert is_valid is True

    # Verify invalid commitment tampering
    is_valid_tampered = ZeroKnowledgeSafetyProof.verify_proof(proof, "tampered_commitment_hash")
    assert is_valid_tampered is False


def test_global_swarm_node_registration_and_voting():
    swarm = GlobalSwarmGovernance(primary_node_id="us_east_cluster")

    # Register additional cluster nodes
    node2_did = swarm.register_node("eu_central_cluster")
    node3_did = swarm.register_node("asia_south_cluster")

    assert node2_did == "did:aios:eu_central_cluster"
    assert swarm.stats()["registered_nodes_count"] == 3

    # Propose constitutional amendment proposal
    prop_id = swarm.create_amendment_proposal(
        proposer_did=swarm.primary_did,
        title="ARTICLE-LXVIII Quantum Alignment Amendment",
        description="Add quantum security assertions",
    )

    # Cast votes (>66% Byzantine BFT threshold)
    swarm.cast_vote(prop_id, swarm.primary_did, approve=True)
    swarm.cast_vote(prop_id, node2_did, approve=True)
    swarm.cast_vote(prop_id, node3_did, approve=True)

    assert swarm.proposals[prop_id]["status"] == "ratified"
    assert swarm.stats()["ratified_proposals"] == 1
