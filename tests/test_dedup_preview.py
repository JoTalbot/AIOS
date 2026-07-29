"""Tests for the dedup dry-run merge preview + endpoint (v11.10.0)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

import aios_core.dashboard as dashboard_module
from aios_core.agent_memory_system import AgentMemorySystem, MemoryType
from aios_core.dashboard import create_dashboard


@pytest.fixture()
def duped_system() -> AgentMemorySystem:
    system = AgentMemorySystem()
    system.record("olx", "login", "success", memory_type=MemoryType.LONG_TERM)
    system.record("olx", "login", "success", memory_type=MemoryType.LONG_TERM)
    system.record("rozetka", "collect", "success", memory_type=MemoryType.LONG_TERM)
    system.optimize_storage()
    return system


def test_preview_matches_merge_policy_without_mutating(duped_system):
    lt = duped_system._long_term
    lt[0].access_count = 3
    lt[1].access_count = 1
    preview = duped_system.preview_dedup(threshold=0.92)
    assert preview["dry_run"] is True
    assert preview["groups"] == 1
    assert preview["would_remove"] == 1
    assert preview["counts_after"] == {"long_term": 2, "episodic": 0}
    plan = preview["plans"][0]
    assert len(plan["absorbed_ids"]) == 1
    # Projection follows the real merge: absorb access counts, best confidence.
    assert plan["projected"]["access_count"] == lt[0].access_count + lt[1].access_count
    assert plan["projected"]["confidence"] == max(lt[0].confidence, lt[1].confidence)

    # Nothing was merged by the preview itself.
    assert duped_system.stats()["long_term_count"] == 3
    assert duped_system.dedup_stats()["removed_total"] == 0

    # And the real deduplicate() removes exactly the previewed ids.
    report = duped_system.deduplicate(threshold=0.92)
    assert set(report["removed_ids"]) == set(plan["absorbed_ids"])
    assert duped_system.stats()["long_term_count"] == preview["counts_after"]["long_term"]


def test_preview_uses_tuned_default_and_honors_override(duped_system):
    duped_system.tune_dedup_threshold(apply=True)  # identical pair -> 0.98
    tuned = duped_system.preview_dedup()
    assert tuned["threshold"] == 0.98
    assert tuned["would_remove"] == 1
    # An explicit threshold wins over the tuned default; 1.0 > cos 1.0 pair
    # stays exclusive of nothing since similarity equal 1.0 qualifies.
    strict = duped_system.preview_dedup(threshold=1.0)
    assert strict["threshold"] == 1.0
    assert strict["would_remove"] == 1


def test_preview_no_duplicates(duped_system):
    preview = duped_system.preview_dedup(threshold=1.0, pool="episodic")
    assert preview["would_remove"] == 0
    assert preview["plans"] == []
    assert preview["counts_after"] == {"long_term": 3, "episodic": 0}


def test_preview_validates_threshold(duped_system):
    with pytest.raises(ValueError, match="threshold"):
        duped_system.preview_dedup(threshold=1.5)
    with pytest.raises(ValueError, match="threshold"):
        duped_system.preview_dedup(threshold=0.0)


def test_preview_counts_episodic_pool_separately():
    system = AgentMemorySystem()
    for _ in range(2):
        system.record("olx", "login", "success", memory_type=MemoryType.LONG_TERM)
    for _ in range(2):
        system.record("olx", "login", "success", memory_type=MemoryType.EPISODIC)
    system.optimize_storage()
    preview = system.preview_dedup(threshold=0.92)
    # LT pair merges (2 -> 1); LT+EP cross-similarity may enlarge groups,
    # but remove count must equal the sum of per-pool absorptions.
    assert preview["counts_after"]["long_term"] + preview["counts_after"]["episodic"] == 4 - preview["would_remove"]
    assert preview["would_remove"] >= 1


# ----------------------------------------------------------------------
# Dashboard endpoint + panel button
# ----------------------------------------------------------------------


@pytest.fixture()
def client():
    dashboard_module._memory_system = None
    orch = MagicMock()
    orch.stats.return_value = {"total_steps_executed": 0}
    orch.version = "11.10.0"
    app = create_dashboard(orch)
    yield TestClient(app)
    dashboard_module._memory_system = None


def test_preview_endpoint_shape(client):
    resp = client.post("/api/memory/dedup/preview", json={"threshold": 0.92})
    assert resp.status_code == 200
    data = resp.json()
    assert data["dry_run"] is True
    assert data["threshold"] == 0.92
    # Seeded singleton at 0.92: exactly the identical LT pair qualifies.
    assert data["would_remove"] == 1
    assert data["counts_after"] == {"long_term": 2, "episodic": 4}
    assert data["plans"][0]["absorbed_ids"][0].startswith("mem_")
    # Preview never mutates: seeded counts unchanged.
    stats = client.get("/api/memory/stats").json()
    assert stats["long_term_count"] == 3
    assert stats["dedup"]["removed_total"] == 0


def test_preview_endpoint_uses_tuned_default(client):
    client.post("/api/memory/dedup/tune", json={"apply": True})
    data = client.post("/api/memory/dedup/preview", json={}).json()
    assert data["threshold"] == 0.8  # seeded tuner recommendation


def test_preview_endpoint_validation(client):
    assert client.post("/api/memory/dedup/preview", json={"threshold": "x"}).status_code == 400
    assert client.post("/api/memory/dedup/preview", json={"threshold": 2.0}).status_code == 400
    assert client.post("/api/memory/dedup/preview", json={"threshold": True}).status_code == 400
    assert client.post("/api/memory/dedup/preview", json={"pool": "short_term"}).status_code == 400
    bad = client.post("/api/memory/dedup/preview", content="[3]", headers={"Content-Type": "application/json"})
    assert bad.status_code == 400
    ok = client.post("/api/memory/dedup/preview", json={"pool": "episodic"})
    assert ok.status_code == 200
    assert ok.json()["pool"] == "episodic"


def test_memory_page_has_preview_button(client):
    resp = client.get("/memory")
    assert "/api/memory/dedup/preview" in resp.text
    assert "runDedupPreview" in resp.text
