"""Tests for the guarded dedup merge endpoint + panel button (v11.12.0)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.dashboard import create_dashboard


@pytest.fixture()
def client():
    dashboard_module._memory_system = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.12.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._memory_system = None


def test_dedup_run_requires_explicit_confirm(client):
    missing = client.post("/api/memory/dedup/run", json={})
    assert missing.status_code == 400
    assert "confirm" in missing.json()["error"]
    assert "preview" in missing.json()["error"]
    assert client.post("/api/memory/dedup/run", json={"confirm": False}).status_code == 400
    assert client.post("/api/memory/dedup/run", json={"confirm": "yes"}).status_code == 400
    # Guarded endpoint merges nothing when confirm is missing.
    assert client.get("/api/memory/stats").json()["dedup"]["removed_total"] == 0


def test_dedup_run_merges_seeded_pair(client):
    resp = client.post("/api/memory/dedup/run", json={"confirm": True})
    assert resp.status_code == 200
    report = resp.json()
    # Seeded singleton at the default 0.92: the identical LT pair merges.
    assert report["groups_found"] == 1
    assert report["entries_removed"] == 1
    assert len(report["removed_ids"]) == 1
    assert report["merged"][0]["size"] == 2
    stats = client.get("/api/memory/stats").json()
    assert stats["long_term_count"] == 2
    assert stats["dedup"]["removed_total"] == 1
    # Second run is a no-op (pair is gone).
    again = client.post("/api/memory/dedup/run", json={"confirm": True}).json()
    assert again["entries_removed"] == 0


def test_dedup_run_threshold_and_pool_params(client):
    strict = client.post("/api/memory/dedup/run", json={"confirm": True, "threshold": 0.99, "pool": "episodic"})
    assert strict.status_code == 200
    # Seeded episodic entries are similar but below 0.99: nothing merges.
    assert strict.json()["entries_removed"] == 0
    assert client.get("/api/memory/stats").json()["episodic_count"] == 4


def test_dedup_run_uses_tuned_default(client):
    client.post("/api/memory/dedup/tune", json={"apply": True})  # seeded tuner -> 0.8
    resp = client.post("/api/memory/dedup/run", json={"confirm": True})
    report = resp.json()
    assert report["threshold"] == 0.8
    # At 0.8 the four near-identical episodic entries also merge.
    assert report["entries_removed"] >= 3


def test_dedup_run_validation(client):
    assert client.post("/api/memory/dedup/run", json={"confirm": True, "threshold": "x"}).status_code == 400
    assert client.post("/api/memory/dedup/run", json={"confirm": True, "threshold": 1.5}).status_code == 400
    assert client.post("/api/memory/dedup/run", json={"confirm": True, "threshold": True}).status_code == 400
    assert client.post("/api/memory/dedup/run", json={"confirm": True, "pool": "short_term"}).status_code == 400
    bad = client.post("/api/memory/dedup/run", content="[8]", headers={"Content-Type": "application/json"})
    assert bad.status_code == 400


def test_memory_page_has_merge_button(client):
    resp = client.get("/memory")
    assert "/api/memory/dedup/run" in resp.text
    assert "runDedupMerge" in resp.text
