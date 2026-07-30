"""Unit tests for AIOS v11.46.0 - v11.50.0 features: Swarm Cyber Defense, DNA Mutation, Category Theory & Alignment."""

from __future__ import annotations

from starlette.testclient import TestClient

from aios_core.alignment_auto_evaluator import AlignmentAutoEvaluator
from aios_core.category_theory_mapper import CategoryTheoryMapper
from aios_core.dashboard import create_dashboard
from aios_core.dna_code_mutation import DNACodeMutationEngine
from aios_core.orchestrator import Orchestrator
from aios_core.swarm_cyber_defense import SwarmCyberDefenseEngine
from sdk.aios_sdk import AIOSClientSync


def test_swarm_cyber_defense_engine():
    """Test swarm cyber threat detection and isolation micro-patching."""
    defense = SwarmCyberDefenseEngine()
    logs = [
        {"event": "normal_query"},
        {"event": "unauthorized_injection_attempt"},
    ]
    res = defense.evaluate_and_mitigate_threats(logs)
    assert res["threats_detected"] == 1
    assert res["mitigations_applied"] == 1


def test_dna_code_mutation_engine():
    """Test synthetic DNA code mutation and fitness improvement."""
    mutator = DNACodeMutationEngine()
    res = mutator.mutate_genome_code("def process_data(x): return x + 1", mutation_rate=0.1)
    assert "DNA Mutated Generation" in res["mutated_code"]
    assert res["fitness_improvement"] == 0.12


def test_category_theory_mapper():
    """Test category-theoretic morphism mapping between concept sets."""
    mapper = CategoryTheoryMapper()
    res = mapper.map_morphisms(["concept_a", "concept_b"], ["concept_a", "concept_c"])
    assert res["morphisms_mapped"] == 2
    assert res["morphisms"][0]["morphism_type"] == "isomorphism"


def test_alignment_auto_evaluator():
    """Test automated model output alignment evaluation and red-teaming."""
    evaluator = AlignmentAutoEvaluator()
    res = evaluator.evaluate_model_alignment(["prompt1"], ["output1"])
    assert res["alignment_score"] == 0.96
    assert res["samples_evaluated"] == 1


def test_rest_api_and_sdk_v11_50_methods():
    """Test REST API endpoints and SDK methods for v11.46-v11.50 features."""
    orch = Orchestrator()
    app = create_dashboard(orch)
    client = TestClient(app)

    # API /api/ai/swarm/cyber-defense
    res1 = client.post("/api/ai/swarm/cyber-defense", json={"activity_logs": [{"event": "safe_event"}]})
    assert res1.status_code == 200

    # API /api/ai/dna/mutate
    res2 = client.post("/api/ai/dna/mutate", json={"genome_code": "code"})
    assert res2.status_code == 200

    # API /api/ai/category/map-morphisms
    res3 = client.post("/api/ai/category/map-morphisms", json={"category_a": ["a"], "category_b": ["b"]})
    assert res3.status_code == 200

    # API /api/ai/alignment/auto-evaluate
    res4 = client.post("/api/ai/alignment/auto-evaluate", json={"prompts": ["p"], "outputs": ["o"]})
    assert res4.status_code == 200

    # SDK Sync methods verification
    sdk = AIOSClientSync("http://localhost:8000")
    assert hasattr(sdk, "ai_evaluate_cyber_defense")
    assert hasattr(sdk, "ai_mutate_genome_code")
    assert hasattr(sdk, "ai_map_category_morphisms")
    assert hasattr(sdk, "ai_evaluate_model_alignment")
