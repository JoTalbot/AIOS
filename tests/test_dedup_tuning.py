"""Tests for dedup threshold auto-tuning + endpoint + panel (v11.9.0)."""

from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.agent_memory_system import AgentMemorySystem, MemoryType
from aios_core.dashboard import create_dashboard
from aios_core.memory_dedup import MemoryDeduplicator, tune_dedup_threshold


class _ShimCompressor:
    """Minimal stand-in with the one method find_groups() calls."""

    @staticmethod
    def cosine_similarity(a, b):
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        na, nb = math.hypot(*a), math.hypot(*b)
        return dot / (na * nb) if na and nb else 0.0


def _unit(x_weight: float) -> tuple[float, float]:
    """Unit 2-vector whose cosine with (1, 0) equals x_weight."""
    return (x_weight, math.sqrt(max(0.0, 1.0 - x_weight * x_weight)))


def test_tune_prefers_conservative_threshold_on_ties():
    # One pair at similarity 0.97: candidates 0.90/0.92/0.95 all find it
    # with equal score -> the HIGHEST of them wins.
    vectors = {"a": (1.0, 0.0), "b": _unit(0.97), "c": (0.0, 1.0)}
    report = tune_dedup_threshold(vectors, _ShimCompressor, candidates=[0.90, 0.92, 0.95, 0.98])
    assert report["signatures_scanned"] == 3
    assert report["duplicates_found"] == 1
    assert report["recommended_threshold"] == 0.95
    by_t = {row["threshold"]: row for row in report["candidates"]}
    assert by_t[0.90]["score"] == pytest.approx(0.97, abs=1e-4)
    assert by_t[0.98]["duplicates"] == 0


def test_tune_prefers_more_duplicates_when_confident():
    # Pair {a,b} is identical (sim 1.0), pair {c,d} sits at 0.90: the low
    # candidate merges 2 pairs at avg 0.95 confidence and outscores the
    # conservative single-merge candidates.
    vectors = {
        "a": (1.0, 0.0),
        "b": (1.0, 0.0),
        "c": (0.0, 1.0),
        "d": _flipped(0.90),
    }
    report = tune_dedup_threshold(vectors, _ShimCompressor, candidates=[0.85, 0.92, 0.98])
    assert report["recommended_threshold"] == 0.85
    assert report["duplicates_found"] == 2
    assert report["candidates"][0]["groups"] == 2
    assert "best merge score" in report["rationale"]


def _flipped(x_weight: float) -> tuple[float, float]:
    """Unit 2-vector whose cosine with (0, 1) equals x_weight."""
    return (math.sqrt(max(0.0, 1.0 - x_weight * x_weight)), x_weight)


def test_tune_keeps_default_without_duplicates():
    vectors = {"a": (1.0, 0.0), "b": (0.0, 1.0)}
    report = tune_dedup_threshold(vectors, _ShimCompressor)
    assert report["recommended_threshold"] == MemoryDeduplicator.DEFAULT_THRESHOLD
    assert report["duplicates_found"] == 0
    assert "keeping the default" in report["rationale"]
    assert len(report["candidates"]) == 6  # module default candidate set


def test_tune_handles_empty_index():
    report = tune_dedup_threshold({}, _ShimCompressor)
    assert report["signatures_scanned"] == 0
    assert report["recommended_threshold"] == MemoryDeduplicator.DEFAULT_THRESHOLD
    assert all(row["groups"] == 0 for row in report["candidates"])


def test_tune_validates_candidates():
    vectors = {"a": (1.0, 0.0)}
    with pytest.raises(ValueError, match="non-empty"):
        tune_dedup_threshold(vectors, _ShimCompressor, candidates=[])
    with pytest.raises(ValueError, match=r"\(0.0, 1.0\]"):
        tune_dedup_threshold(vectors, _ShimCompressor, candidates=[1.5])
    with pytest.raises(ValueError):
        tune_dedup_threshold(vectors, _ShimCompressor, candidates=["x"])


@pytest.fixture()
def duped_system() -> AgentMemorySystem:
    system = AgentMemorySystem()
    system.record("olx", "login", "success", memory_type=MemoryType.LONG_TERM)
    system.record("olx", "login", "success", memory_type=MemoryType.LONG_TERM)
    system.record("rozetka", "collect", "success", memory_type=MemoryType.LONG_TERM)
    system.optimize_storage()
    return system


def test_system_tune_recommends_on_real_index(duped_system):
    report = duped_system.tune_dedup_threshold()
    assert report["signatures_scanned"] == 3
    assert report["duplicates_found"] == 1
    # The identical pair scores 1.0 at every candidate -> conservative win.
    assert report["recommended_threshold"] == 0.98
    assert report["pool"] == "all"
    assert report["applied"] is False
    assert duped_system.dedup_threshold == 0.92  # unchanged without apply
    # Tuning never merges anything.
    assert duped_system.dedup_stats()["removed_total"] == 0
    assert duped_system.stats()["long_term_count"] == 3


def test_system_tune_apply_persists_across_snapshot(duped_system):
    report = duped_system.tune_dedup_threshold(apply=True)
    assert report["applied"] is True
    assert duped_system.dedup_threshold == 0.98
    assert duped_system.dedup_stats()["threshold"] == 0.98

    restored = AgentMemorySystem()
    restored.restore(duped_system.snapshot())
    assert restored.dedup_threshold == 0.98

    # Snapshots from older versions without the field fall back to 0.92.
    legacy = duped_system.snapshot()
    del legacy["dedup_threshold"]
    fresh = AgentMemorySystem()
    fresh.restore(legacy)
    assert fresh.dedup_threshold == 0.92


# ----------------------------------------------------------------------
# Dashboard endpoint + panel
# ----------------------------------------------------------------------


@pytest.fixture()
def client():
    dashboard_module._memory_system = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.9.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._memory_system = None


def test_dedup_tune_endpoint_recommend(client):
    resp = client.post("/api/memory/dedup/tune", json={})
    assert resp.status_code == 200
    data = resp.json()
    # Seeded singleton: 4 near-identical episodic entries + 1 identical LT
    # pair -> the 0.80 candidate merges 4 duplicates at 0.91 confidence
    # and outscores the conservative single-merge thresholds.
    assert data["recommended_threshold"] == 0.8
    assert data["duplicates_found"] == 4
    assert data["applied"] is False
    assert len(data["candidates"]) == 6
    # The duplicates endpoint still uses the factory default.
    assert client.get("/api/memory/duplicates").json()["threshold"] == 0.92


def test_dedup_tune_apply_changes_endpoint_default(client):
    resp = client.post("/api/memory/dedup/tune", json={"apply": True})
    assert resp.json()["applied"] is True
    assert client.get("/api/memory/duplicates").json()["threshold"] == 0.8
    assert client.get("/api/memory/stats").json()["dedup"]["threshold"] == 0.8
    # An explicit query parameter still wins over the tuned default.
    assert client.get("/api/memory/duplicates?threshold=0.5").json()["threshold"] == 0.5


def test_dedup_tune_endpoint_validation(client):
    assert client.post("/api/memory/dedup/tune", json={"candidates": []}).status_code == 400
    assert client.post("/api/memory/dedup/tune", json={"candidates": "nope"}).status_code == 400
    assert client.post("/api/memory/dedup/tune", json={"candidates": [1.5]}).status_code == 400
    assert client.post("/api/memory/dedup/tune", json={"candidates": [True]}).status_code == 400
    assert client.post("/api/memory/dedup/tune", json={"pool": "short_term"}).status_code == 400
    assert (
        client.post("/api/memory/dedup/tune", content="[9]", headers={"Content-Type": "application/json"}).status_code
        == 400
    )
    ok = client.post("/api/memory/dedup/tune", json={"candidates": [0.9, 0.95], "pool": "long_term"})
    assert ok.status_code == 200
    assert [c["threshold"] for c in ok.json()["candidates"]] == [0.9, 0.95]


def test_memory_page_has_tune_button(client):
    resp = client.get("/memory")
    assert "/api/memory/dedup/tune" in resp.text
    assert "dedup-tune-result" in resp.text
