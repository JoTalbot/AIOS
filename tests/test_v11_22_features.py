"""Unit tests for AIOS v11.22.0 features: Multi-Provider LLM Router, RAG Augmentation & Swarm Consensus."""

from __future__ import annotations

from starlette.testclient import TestClient

from aios_core.dashboard import create_dashboard
from aios_core.llm_router import LLMMessage, LLMProvider, LLMRequest, LLMRouter
from aios_core.orchestrator import Orchestrator
from aios_core.rag_augmentation import ContextAugmenter
from aios_core.swarm_consensus import SwarmConsensusEngine
from sdk.aios_sdk import AIOSClientSync


def test_llm_router_generation_and_fallback():
    """Test LLM router request generation and fallback chain execution."""
    router = LLMRouter(default_provider=LLMProvider.MOCK)
    req = LLMRequest(
        messages=[LLMMessage(role="user", content="Test prompt")],
        provider=LLMProvider.OPENAI,
        fallback_chain=[LLMProvider.OPENAI, LLMProvider.ANTHROPIC, LLMProvider.MOCK],
    )
    resp = router.generate(req)
    assert resp.content is not None
    assert resp.tokens_used > 0
    assert resp.estimated_cost >= 0.0

    stats = router.router_stats()
    assert stats["total_requests"] == 1


def test_rag_context_augmenter():
    """Test RAG context augmenter enriching prompt payloads."""
    augmenter = ContextAugmenter()
    res = augmenter.augment_prompt("How to optimize memory in AIOS?", top_k=2)

    assert "augmented_prompt" in res
    assert res["original_prompt"] == "How to optimize memory in AIOS?"


def test_swarm_multi_model_consensus():
    """Test multi-model swarm consensus engine querying providers and scoring agreement."""
    router = LLMRouter()
    consensus = SwarmConsensusEngine(router=router)

    res = consensus.evaluate_consensus(
        prompt="Select optimal architecture for edge swarm",
        providers=[LLMProvider.MOCK, LLMProvider.OPENAI],
    )

    assert res["successful_responses"] == 2
    assert res["agreement_score"] == 1.0
    assert "winning_response" in res


def test_ai_api_endpoints_and_sdk_methods():
    """Test REST API endpoints and SDK methods for AI generation, RAG augmentation & consensus."""
    orch = Orchestrator()
    app = create_dashboard(orch)
    client = TestClient(app)

    # API /api/ai/generate
    res1 = client.post("/api/ai/generate", json={"prompt": "Hello AIOS"})
    assert res1.status_code == 200
    assert "content" in res1.json()

    # API /api/ai/augment
    res2 = client.post("/api/ai/augment", json={"prompt": "RAG test"})
    assert res2.status_code == 200
    assert "augmented_prompt" in res2.json()

    # API /api/ai/consensus
    res3 = client.post("/api/ai/consensus", json={"prompt": "Consensus test"})
    assert res3.status_code == 200
    assert "winning_response" in res3.json()

    # SDK Sync methods
    sdk = AIOSClientSync("http://localhost:8000")
    assert hasattr(sdk, "ai_generate")
    assert hasattr(sdk, "ai_augment")
    assert hasattr(sdk, "ai_consensus")
