"""Unit tests for AIOS v11.31.0 - v11.35.0 features: Neural Memory Consolidation, Causal What-If, Swarm Auto-Scaler & Privacy Data Vault."""

from __future__ import annotations

from starlette.testclient import TestClient

from aios_core.agent_memory_system import AgentMemorySystem, MemoryEntry, MemoryType
from aios_core.agent_swarm import AgentRole, AgentSwarm, SwarmAgent
from aios_core.causal_counterfactual import CausalCounterfactualEngine
from aios_core.dashboard import create_dashboard
from aios_core.neural_memory_consolidation import NeuralMemoryConsolidator
from aios_core.orchestrator import Orchestrator
from aios_core.privacy_data_vault import PrivacyDataVault
from aios_core.swarm_auto_scaler import SwarmAutoScaler
from sdk.aios_sdk import AIOSClientSync


def test_neural_memory_consolidator():
    """Test short-term memory scanning and neural consolidation."""
    mem = AgentMemorySystem()
    entry = MemoryEntry(
        memory_id="s1",
        memory_type=MemoryType.EPISODIC,
        platform="test",
        action="act",
        result="success",
    )
    mem._short_term.append(entry)

    consolidator = NeuralMemoryConsolidator()
    res = consolidator.consolidate_and_compact(memory_system=mem)
    assert res["short_term_scanned"] == 1
    assert res["vector_index_compacted"] is True


def test_causal_counterfactual_engine():
    """Test Causal What-If scenario evaluation."""
    causal = CausalCounterfactualEngine()
    res = causal.evaluate_what_if(action={"name": "deploy_new_agent_shard"})
    assert "causal_utility" in res
    assert "recommended_scenario" in res


def test_swarm_auto_scaler():
    """Test dynamic swarm worker auto-scaling matching task demand."""
    swarm = AgentSwarm(name="autoscale_swarm")
    swarm.add_agent(SwarmAgent(id="w1", name="Worker 1", role=AgentRole.WORKER))

    scaler = SwarmAutoScaler(swarm=swarm)
    pending_tasks = [{"id": "t1"}, {"id": "t2"}, {"id": "t3"}]

    res = scaler.auto_scale_swarm_roles(pending_tasks=pending_tasks)
    assert res["spawned_workers"] == 2
    assert res["total_agents_after"] == 3


def test_privacy_data_vault():
    """Test PII redaction and differential privacy payload masking."""
    vault = PrivacyDataVault()
    payload = {"user_email": "user@example.com", "action": "query_database"}

    res = vault.mask_sensitive_payload(payload)
    assert res["pii_redacted_count"] == 1
    assert res["masked_payload"]["user_email"] == "[REDACTED_EMAIL]"


def test_rest_api_and_sdk_v11_35_methods():
    """Test REST API endpoints and SDK methods for v11.31-v11.35 features."""
    orch = Orchestrator()
    app = create_dashboard(orch)
    client = TestClient(app)

    # API /api/ai/memory/consolidate-neural
    res1 = client.post("/api/ai/memory/consolidate-neural", json={})
    assert res1.status_code == 200

    # API /api/ai/causal/what-if
    res2 = client.post("/api/ai/causal/what-if", json={"action": {"name": "test_action"}})
    assert res2.status_code == 200

    # API /api/ai/swarm/autoscale
    res3 = client.post("/api/ai/swarm/autoscale", json={"pending_tasks": [{"id": "t1"}]})
    assert res3.status_code == 200

    # API /api/ai/privacy/mask
    res4 = client.post("/api/ai/privacy/mask", json={"payload": {"email": "test@domain.com"}})
    assert res4.status_code == 200

    # SDK Sync methods verification
    sdk = AIOSClientSync("http://localhost:8000")
    assert hasattr(sdk, "ai_consolidate_neural_memory")
    assert hasattr(sdk, "ai_evaluate_what_if")
    assert hasattr(sdk, "ai_autoscale_swarm")
    assert hasattr(sdk, "ai_mask_privacy_payload")
