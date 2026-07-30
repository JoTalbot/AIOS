"""Unit tests for AIOS Major Release v15.0.0 features."""

from __future__ import annotations

from starlette.testclient import TestClient

from aios_core.dashboard import create_dashboard
from aios_core.graph_rag_v4 import GraphRAGQueryEngineV4
from aios_core.infinite_cognition_nexus_v15 import AIOSInfiniteCognitionNexusV15
from aios_core.infinite_goals import InfiniteGoalSynthesizer
from aios_core.multimodal_v4 import MultiModalVisionProcessorV4
from aios_core.orchestrator import Orchestrator
from aios_core.prompt_tuner_v4 import PromptAutoTunerV4
from aios_core.swarm_federated_v4 import SwarmFederatedOptimizerV4
from sdk.aios_sdk import AIOSClientSync


def test_v15_infinite_cognition_modules():
    """Verify v15 Infinite Cognition modules functionality."""
    synth = InfiniteGoalSynthesizer()
    assert len(synth.synthesize_infinite_goals({})["infinite_goals"]) == 2

    rag4 = GraphRAGQueryEngineV4()
    assert "V4 GraphRAG" in rag4.query_v4("prompt")["context_v4"]

    vision4 = MultiModalVisionProcessorV4()
    assert vision4.process_vision_v4("data")["detected_objects_v4"] == 10

    fed4 = SwarmFederatedOptimizerV4()
    assert fed4.optimize_federated_v4([0.1, 0.2])["optimized_weight"] == 0.99

    tuner4 = PromptAutoTunerV4()
    assert "Optimized V4" in tuner4.tune_prompt_v4("prompt")["tuned_v4"]

    nexus15 = AIOSInfiniteCognitionNexusV15()
    assert nexus15.get_v15_infinite_status()["status"] == "v15_infinite_cognition_integrated"


def test_v15_api_and_sdk():
    """Test REST API and SDK for v15.0.0 Infinite Cognition status."""
    orch = Orchestrator()
    app = create_dashboard(orch)
    client = TestClient(app)

    res = client.get("/api/ai/infinite/status")
    assert res.status_code == 200
    assert res.json()["version"] == "15.0.0"

    sdk = AIOSClientSync("http://localhost:8000")
    assert hasattr(sdk, "ai_get_infinite_status")
