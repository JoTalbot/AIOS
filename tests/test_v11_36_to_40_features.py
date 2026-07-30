"""Unit tests for AIOS v11.36.0 - v11.40.0 features: Code Synthesizer, Vision RPA Grounding, Quantum AI & Planetary Sync."""

from __future__ import annotations

from starlette.testclient import TestClient

from aios_core.code_synthesis import AICodeSynthesizer
from aios_core.dashboard import create_dashboard
from aios_core.orchestrator import Orchestrator
from aios_core.planetary_ai_sync import PlanetaryAISyncEngine
from aios_core.quantum_ai_pipeline import QuantumAIOptimizer
from aios_core.vision_rpa_grounding import VisionRPAGroundingEngine
from sdk.aios_sdk import AIOSClientSync


def test_ai_code_synthesizer():
    """Test AI code patch synthesis and verification."""
    synth = AICodeSynthesizer()
    res = synth.synthesize_patch("ZeroDivisionError: division by zero", "x = 10 / 0")
    assert "synthesized_patch" in res
    assert res["verification_status"] == "verified_safe"


def test_vision_rpa_grounding_engine():
    """Test natural language RPA action grounding to UI coordinates."""
    grounder = VisionRPAGroundingEngine()
    res = grounder.ground_action_to_coordinates("click login button")
    assert res["target_element_id"] == "btn_login"
    assert "x" in res["click_coordinates"]


def test_quantum_ai_optimizer():
    """Test hybrid quantum variational circuit optimization of routing weights."""
    opt = QuantumAIOptimizer(qubits_count=4)
    res = opt.optimize_routing_weights([0.8, 0.2])
    assert len(res["optimized_weights"]) == 2
    assert res["quantum_fidelity"] == 0.98


def test_planetary_ai_sync_engine():
    """Test planetary edge mesh state ledger synchronization."""
    sync_eng = PlanetaryAISyncEngine()
    res = sync_eng.synchronize_mesh_state([{"node_id": "us_east_1"}, {"node_id": "eu_west_1"}])
    assert res["nodes_synced"] == 2
    assert res["mesh_status"] == "synchronized"


def test_rest_api_and_sdk_v11_40_methods():
    """Test REST API endpoints and SDK methods for v11.36-v11.40 features."""
    orch = Orchestrator()
    app = create_dashboard(orch)
    client = TestClient(app)

    # API /api/ai/code/synthesize-patch
    res1 = client.post("/api/ai/code/synthesize-patch", json={"error_log": "err", "source_code": "code"})
    assert res1.status_code == 200

    # API /api/ai/perception/ground-action
    res2 = client.post("/api/ai/perception/ground-action", json={"action_description": "click button"})
    assert res2.status_code == 200

    # API /api/ai/quantum/optimize-weights
    res3 = client.post("/api/ai/quantum/optimize-weights", json={"weights": [0.5, 0.5]})
    assert res3.status_code == 200

    # API /api/ai/planetary/sync
    res4 = client.post("/api/ai/planetary/sync", json={"node_states": [{"id": "n1"}]})
    assert res4.status_code == 200

    # SDK Sync methods verification
    sdk = AIOSClientSync("http://localhost:8000")
    assert hasattr(sdk, "ai_synthesize_patch")
    assert hasattr(sdk, "ai_ground_rpa_action")
    assert hasattr(sdk, "ai_quantum_optimize_weights")
    assert hasattr(sdk, "ai_planetary_sync")
