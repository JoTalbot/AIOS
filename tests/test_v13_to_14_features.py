"""Unit tests for AIOS Major Release v14.0.0 features."""

from __future__ import annotations

from starlette.testclient import TestClient

from aios_core.dashboard import create_dashboard
from aios_core.goal_synthesizer import AutonomousGoalSynthesizer
from aios_core.graph_rag_v3 import GraphRAGQueryEngineV3
from aios_core.multimodal_v3 import MultiModalVisionProcessorV3
from aios_core.orchestrator import Orchestrator
from aios_core.prompt_tuner_v3 import PromptAutoTunerV3
from aios_core.singularity_universal_nexus_v14 import AIOSSingularityUniversalNexusV14
from aios_core.swarm_federated_v3 import SwarmFederatedOptimizerV3
from sdk.aios_sdk import AIOSClientSync


def test_v14_universal_singularity_modules():
    """Verify v14 Universal Singularity modules functionality."""
    synth = AutonomousGoalSynthesizer()
    assert len(synth.synthesize_meta_goals({})["synthesized_goals"]) == 2

    rag3 = GraphRAGQueryEngineV3()
    assert "V3 GraphRAG" in rag3.query_v3("prompt")["context_v3"]

    vision3 = MultiModalVisionProcessorV3()
    assert vision3.process_vision_v3("data")["detected_objects_v3"] == 5

    fed3 = SwarmFederatedOptimizerV3()
    assert fed3.optimize_federated_v3([0.1, 0.2])["optimized_weight"] == 0.95

    tuner3 = PromptAutoTunerV3()
    assert "Optimized V3" in tuner3.tune_prompt_v3("prompt")["tuned_v3"]

    nexus14 = AIOSSingularityUniversalNexusV14()
    assert nexus14.get_v14_universal_status()["status"] == "v14_universal_singularity_integrated"


def test_v14_api_and_sdk():
    """Test REST API and SDK for v14.0.0 Universal Singularity status."""
    orch = Orchestrator()
    app = create_dashboard(orch)
    client = TestClient(app)

    res = client.get("/api/ai/universal/status")
    assert res.status_code == 200
    assert res.json()["version"] == "14.0.0"

    sdk = AIOSClientSync("http://localhost:8000")
    assert hasattr(sdk, "ai_get_universal_status")
