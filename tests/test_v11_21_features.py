"""Unit tests for AIOS v11.21.0 features: Adaptive Self-Healing Substrate Engine & REST/SDK Integration."""

from __future__ import annotations

from starlette.testclient import TestClient

from aios_core.dashboard import create_dashboard
from aios_core.orchestrator import Orchestrator
from aios_core.self_healing import AdaptiveSelfHealingSubstrateEngine
from aios_core.substrate_convergence import SubstrateConvergenceEngine
from sdk.aios_sdk import AIOSClientSync


def test_adaptive_self_healing_substrate_engine():
    """Test adaptive substrate self-healing capacity reduction and deactivation."""
    engine = SubstrateConvergenceEngine()
    s1 = engine.register_substrate("degraded_sub", latency_base_ms=500.0, capacity=10)
    s1["health"] = 0.4
    s1["failure_rate"] = 0.4

    s2 = engine.register_substrate("failed_sub", latency_base_ms=1000.0, capacity=10)
    s2["health"] = 0.2
    s2["failure_rate"] = 0.8

    healer = AdaptiveSelfHealingSubstrateEngine(engine=engine)
    report = healer.run_anomaly_healing_cycle()

    assert report["anomalies_detected"] == 2
    assert report["healed_substrates"] == 2

    # degraded_sub capacity reduced by 50%
    assert engine.substrates["degraded_sub"]["capacity"] == 5
    # failed_sub deactivated
    assert engine.substrates["failed_sub"]["active"] is False


def test_self_healing_api_endpoint():
    """Test POST /api/substrate/self-healing/run REST endpoint."""
    orch = Orchestrator()
    app = create_dashboard(orch)
    client = TestClient(app)

    # Missing confirm -> 400
    res1 = client.post("/api/substrate/self-healing/run", json={})
    assert res1.status_code == 400

    # With confirm: true -> 200
    res2 = client.post("/api/substrate/self-healing/run", json={"confirm": True})
    assert res2.status_code == 200
    assert "healed_substrates" in res2.json()


def test_sdk_run_self_healing_sync():
    """Test AIOSClientSync.run_self_healing method existence."""
    sync_c = AIOSClientSync("http://localhost:8000")
    assert hasattr(sync_c, "run_self_healing")
