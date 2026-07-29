"""Tests for the live Agent Memory dashboard (v11.4.0)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.dashboard import create_dashboard


@pytest.fixture()
def client():
    # Fresh memory system for every test (module-level singleton)
    dashboard_module._memory_system = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.4.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._memory_system = None


def test_memory_page_served(client):
    resp = client.get("/memory")
    assert resp.status_code == 200
    assert "Agent Memory" in resp.text
    assert "/api/memory/stats" in resp.text  # live data wiring
    assert "/api/memory/duplicates" in resp.text


def test_memory_stats_shape(client):
    data = client.get("/api/memory/stats").json()
    for key in [
        "short_term_count",
        "long_term_count",
        "episodic_count",
        "pattern_count",
        "avg_strength_short",
        "avg_strength_long",
        "platform_distribution",
        "compression",
        "dedup",
    ]:
        assert key in data
    # Seeded demo data: 3 long-term + 4 episodic entries
    assert data["long_term_count"] == 3
    assert data["episodic_count"] == 4
    assert data["pattern_count"] >= 1
    assert data["platform_distribution"]["olx"] == 6  # 2 LT + 4 EP
    assert data["dedup"]["removed_total"] == 0


def test_memory_compression_report(client):
    data = client.get("/api/memory/compression").json()
    assert data["entries_compressed"] == 7  # 3 LT + 4 EP seeded
    assert data["source_dim"] == 512
    assert data["target_dim"] == 64
    assert data["ratio"] > 1.0
    assert data["compressed_bytes"] < data["original_bytes"]


def test_memory_duplicates_seeded_pair(client):
    data = client.get("/api/memory/duplicates").json()
    assert data["threshold"] == pytest.approx(0.92)
    assert len(data["groups"]) == 1
    group = data["groups"][0]
    assert group["size"] == 2
    assert group["avg_similarity"] == pytest.approx(1.0, abs=1e-3)


def test_memory_duplicates_threshold_param(client):
    # Non-numeric threshold falls back to default instead of 500-ing
    fallback = client.get("/api/memory/duplicates?threshold=abc")
    assert fallback.status_code == 200
    assert fallback.json()["threshold"] == pytest.approx(0.92)
    # Out-of-range values are clamped, not rejected with an error
    clamped = client.get("/api/memory/duplicates?threshold=2")
    assert clamped.status_code == 200
    assert clamped.json()["threshold"] == pytest.approx(1.0)
    # Identical texts have cosine ~1.0, so they still group at 1.0
    assert len(clamped.json()["groups"]) == 1


def test_memory_patterns_list(client):
    data = client.get("/api/memory/patterns").json()
    assert len(data["patterns"]) >= 1
    pattern = data["patterns"][0]
    assert pattern["platform"] == "olx"
    assert pattern["action"] == "collect"
    assert pattern["sample_size"] >= 3
    for key in ["success_rate", "avg_latency_ms", "avg_items", "best_params", "confidence"]:
        assert key in pattern


# ------------------------------------------------------------------
# Recall search + lifecycle endpoints (v11.7.0)
# ------------------------------------------------------------------


def test_recall_api_keyword_mode(client):
    data = client.get("/api/memory/recall?q=olx&mode=keyword&top_k=3").json()
    assert data["mode"] == "keyword"
    assert data["top_k"] == 3
    assert data["results"]
    assert data["results"][0]["platform"] == "olx"
    assert "score" in data["results"][0]
    assert len(data["results"]) <= 3


def test_recall_api_compressed_mode(client):
    data = client.get("/api/memory/recall?q=olx+login+success&mode=compressed").json()
    assert data["mode"] == "compressed"
    assert data["results"]
    assert data["results"][0]["platform"] == "olx"


def test_recall_api_validation(client):
    missing_q = client.get("/api/memory/recall")
    assert missing_q.status_code == 400
    blank_q = client.get("/api/memory/recall?q=++")
    assert blank_q.status_code == 400
    bad_mode = client.get("/api/memory/recall?q=olx&mode=esoteric")
    assert bad_mode.status_code == 400
    # top_k is clamped / defaulted, never an error
    clamped = client.get("/api/memory/recall?q=olx&top_k=abc")
    assert clamped.status_code == 200
    assert clamped.json()["top_k"] == 5


def test_consolidate_endpoint(client):
    data = client.post("/api/memory/consolidate").json()
    assert isinstance(data["consolidated"], int)
    assert data["pattern_count"] >= 1  # seeded episodic successes


def test_decay_endpoint(client):
    data = client.post("/api/memory/decay", json={}).json()
    assert data["decayed"] == 0  # fresh seeded entries are all strong
    assert data["min_strength"] == 0.05
    bad = client.post("/api/memory/decay", json={"min_strength": "abc"})
    assert bad.status_code == 400
    negative = client.post("/api/memory/decay", json={"min_strength": -1})
    assert negative.status_code == 400


def test_optimize_adaptive_endpoint(client):
    data = client.post(
        "/api/memory/compression/optimize-adaptive",
        json={"min_overlap": 0.5, "top_k": 3, "dims": [16, 64]},
    ).json()
    assert data["adaptive"]["selected_dim"] in (16, 64)
    assert data["target_dim"] == data["adaptive"]["selected_dim"]
    # Compression report now carries the adaptive block for the page
    compression = client.get("/api/memory/compression").json()
    assert compression["adaptive"]["selected_dim"] == data["adaptive"]["selected_dim"]
    bad = client.post("/api/memory/compression/optimize-adaptive", json={"dims": "oops"})
    assert bad.status_code == 400
    bad2 = client.post("/api/memory/compression/optimize-adaptive", json={"min_overlap": 2.0})
    assert bad2.status_code == 400


def test_memory_page_has_search_and_lifecycle_wiring(client):
    resp = client.get("/memory")
    assert resp.status_code == 200
    assert "v11.10.0" in resp.text
    assert "/api/memory/recall" in resp.text
    assert "runSearch" in resp.text
    assert "runLifecycle" in resp.text
    assert "/api/memory/consolidate" in resp.text
