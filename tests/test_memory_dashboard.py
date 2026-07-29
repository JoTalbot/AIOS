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
