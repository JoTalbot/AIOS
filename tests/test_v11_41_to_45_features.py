"""Unit tests for AIOS v11.41.0 - v11.45.0 features: Neuromorphic SNN Bridge, Formal Prover, Blockchain Proof Ledger & Ethics Core."""

from __future__ import annotations

from starlette.testclient import TestClient

from aios_core.blockchain_ledger import BlockchainProofLedger
from aios_core.dashboard import create_dashboard
from aios_core.formal_invariant_prover import FormalInvariantProverEngine
from aios_core.multi_species_alignment import MultiSpeciesAlignmentCore
from aios_core.neuromorphic_bridge import NeuromorphicSpikingBridge
from aios_core.orchestrator import Orchestrator
from sdk.aios_sdk import AIOSClientSync


def test_neuromorphic_spiking_bridge():
    """Test STDP spiking neural event processing."""
    bridge = NeuromorphicSpikingBridge()
    res = bridge.process_spiking_events([0.8, 0.2, 0.9, 0.1])
    assert res["firing_neurons"] == 2
    assert res["total_spikes_received"] == 4


def test_formal_invariant_prover_engine():
    """Test formal mathematical invariant proof verification."""
    prover = FormalInvariantProverEngine()
    res = prover.prove_invariant("safe_computation_step(x = 1)")
    assert res["proved_valid"] is True
    assert res["smt_solver_status"] == "sat"


def test_blockchain_proof_ledger():
    """Test recording immutable state proof onto blockchain ledger."""
    ledger = BlockchainProofLedger()
    res = ledger.record_state_proof("hash_0x123abc")
    assert res["block_index"] == 1
    assert res["confirmed"] is True


def test_multi_species_alignment_core():
    """Test multi-species ethics and human alignment evaluation."""
    core = MultiSpeciesAlignmentCore()
    res = core.evaluate_alignment_ethics("optimize energy distribution", [{"action": "dispatch"}])
    assert res["aligned_safe"] is True
    assert res["human_value_alignment_score"] > 0.9


def test_rest_api_and_sdk_v11_45_methods():
    """Test REST API endpoints and SDK methods for v11.41-v11.45 features."""
    orch = Orchestrator()
    app = create_dashboard(orch)
    client = TestClient(app)

    # API /api/ai/neuromorphic/process-spikes
    res1 = client.post("/api/ai/neuromorphic/process-spikes", json={"spikes": [0.6, 0.7]})
    assert res1.status_code == 200

    # API /api/ai/formal/prove-invariant
    res2 = client.post("/api/ai/formal/prove-invariant", json={"action_code": "code"})
    assert res2.status_code == 200

    # API /api/ai/blockchain/record-proof
    res3 = client.post("/api/ai/blockchain/record-proof", json={"state_hash": "0xabc"})
    assert res3.status_code == 200

    # API /api/ai/ethics/evaluate-alignment
    res4 = client.post("/api/ai/ethics/evaluate-alignment", json={"intent": "help_users"})
    assert res4.status_code == 200

    # SDK Sync methods verification
    sdk = AIOSClientSync("http://localhost:8000")
    assert hasattr(sdk, "ai_process_spiking_events")
    assert hasattr(sdk, "ai_prove_invariant")
    assert hasattr(sdk, "ai_record_blockchain_proof")
    assert hasattr(sdk, "ai_evaluate_alignment")
