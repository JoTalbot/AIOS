"""Unit tests for AIOS Major Release v13.0.0 features."""

from __future__ import annotations

from starlette.testclient import TestClient

from aios_core.behavioral_predictor import AgentBehavioralPredictor
from aios_core.dashboard import create_dashboard
from aios_core.grand_epoch_nexus_v13 import AIOSGrandEpochNexusV13
from aios_core.neural_kg_engine import NeuralKnowledgeGraphEngine
from aios_core.orchestrator import Orchestrator
from aios_core.task_graph_executor import AutonomousTaskGraphExecutor
from sdk.aios_sdk import AIOSClientSync


def test_v13_grand_epoch_modules():
    """Verify v13 Grand Epoch modules functionality."""
    n_kg = NeuralKnowledgeGraphEngine()
    assert "query" in n_kg.query_neural_kg("test")

    pred = AgentBehavioralPredictor()
    assert pred.predict_action("ag1")["confidence"] == 0.98

    exec_graph = AutonomousTaskGraphExecutor()
    assert exec_graph.execute_task_graph("root")["status"] == "completed"

    nexus = AIOSGrandEpochNexusV13()
    assert nexus.get_v13_grand_epoch_status()["status"] == "v13_grand_epoch_integrated"


def test_v13_api_and_sdk():
    """Test REST API and SDK for v13.0.0 Grand Epoch Nexus status."""
    orch = Orchestrator()
    app = create_dashboard(orch)
    client = TestClient(app)

    res = client.get("/api/ai/grand-epoch/status")
    assert res.status_code == 200
    assert res.json()["version"] == "13.0.0"

    sdk = AIOSClientSync("http://localhost:8000")
    assert hasattr(sdk, "ai_get_grand_epoch_status")
