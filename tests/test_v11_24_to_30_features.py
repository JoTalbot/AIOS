"""Unit tests for AIOS v11.24.0 - v11.30.0 features: AI Planner, GraphRAG, Distillation, Perception, Swarm Federated & Prompt Optimizer."""

from __future__ import annotations

from starlette.testclient import TestClient

from aios_core.ai_planner import AITaskPlanner
from aios_core.dashboard import create_dashboard
from aios_core.graph_rag import GraphRAGEngine
from aios_core.knowledge_distillation import KnowledgeDistillationEngine
from aios_core.multimodal_perception import MultimodalPerceptionEngine
from aios_core.orchestrator import Orchestrator
from aios_core.prompt_optimizer import SelfEvolvingPromptOptimizer
from aios_core.swarm_federated import SwarmFederatedEngine
from sdk.aios_sdk import AIOSClientSync


def test_ai_planner():
    """Test AI Task Planner decomposition and self-correction."""
    planner = AITaskPlanner()
    plan = planner.decompose_goal("Deploy autonomous Kubernetes cluster")
    assert plan["total_steps"] == 3

    corrected = planner.self_correct_plan("step_2", "Connection timeout", plan)
    assert len(corrected["corrected_steps"]) == 2


def test_graph_rag_engine():
    """Test GraphRAG query context fusion."""
    rag = GraphRAGEngine()
    res = rag.query_graph_rag("What are the system safety invariants?")
    assert "fused_context" in res


def test_knowledge_distillation_engine():
    """Test trajectory collection and distillation dataset generation."""
    dist = KnowledgeDistillationEngine()
    dist.collect_trajectory("agent_1", "Task prompt", [{"action": "click"}], score=0.95)

    ds = dist.prepare_distillation_dataset(min_score=0.8)
    assert ds["selected_samples"] == 1
    assert len(ds["dataset"]) == 1


def test_multimodal_perception_engine():
    """Test visual UI processing and element OCR detection."""
    perc = MultimodalPerceptionEngine()
    res = perc.process_visual_ui("base64_screenshot_data", query="click login")
    assert res["detected_elements_count"] >= 1
    assert "btn_login" in res["suggested_action"]


def test_swarm_federated_engine():
    """Test privacy-preserving swarm federated insight aggregation."""
    fed = SwarmFederatedEngine()
    nodes_data = [
        {"sample_count": 10, "metrics": {"accuracy": 0.9}},
        {"sample_count": 20, "metrics": {"accuracy": 0.95}},
    ]
    res = fed.aggregate_swarm_insights(nodes_data)
    assert res["nodes_aggregated"] == 2
    assert res["total_samples"] == 30


def test_self_evolving_prompt_optimizer():
    """Test self-evolving prompt optimization."""
    opt = SelfEvolvingPromptOptimizer()
    res = opt.optimize_prompt("Classify intent", evaluation_metric="accuracy")
    assert "optimized_prompt" in res


def test_rest_api_and_sdk_ai_methods():
    """Test REST API routes and SDK methods for v11.24-v11.30 features."""
    orch = Orchestrator()
    app = create_dashboard(orch)
    client = TestClient(app)

    # API /api/ai/plan/decompose
    res1 = client.post("/api/ai/plan/decompose", json={"goal": "Optimize pipeline"})
    assert res1.status_code == 200

    # API /api/ai/graph-rag/query
    res2 = client.post("/api/ai/graph-rag/query", json={"query": "RAG query"})
    assert res2.status_code == 200

    # API /api/ai/distillation/collect
    res3 = client.post("/api/ai/distillation/collect", json={"agent_id": "a1", "prompt": "p1", "trajectory": []})
    assert res3.status_code == 200

    # API /api/ai/perception/ui
    res4 = client.post("/api/ai/perception/ui", json={"screenshot": "data"})
    assert res4.status_code == 200

    # API /api/ai/prompt/optimize
    res5 = client.post("/api/ai/prompt/optimize", json={"prompt": "prompt"})
    assert res5.status_code == 200

    # SDK Sync methods verification
    sdk = AIOSClientSync("http://localhost:8000")
    assert hasattr(sdk, "ai_decompose_goal")
    assert hasattr(sdk, "ai_correct_plan")
    assert hasattr(sdk, "ai_query_graph_rag")
    assert hasattr(sdk, "ai_collect_trajectory")
    assert hasattr(sdk, "ai_prepare_distillation_dataset")
    assert hasattr(sdk, "ai_process_visual_ui")
    assert hasattr(sdk, "ai_aggregate_swarm_insights")
    assert hasattr(sdk, "ai_optimize_prompt")
