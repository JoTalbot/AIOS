"""Tests for AdaptiveTuner + optimize_storage_adaptive (v11.5.0)."""

from __future__ import annotations

import pytest

from aios_core.agent_memory_system import AgentMemorySystem, MemoryType
from aios_core.memory_compression import AdaptiveTuner, HashingVectorizer, ranking_overlap

# ------------------------------------------------------------------
# ranking_overlap
# ------------------------------------------------------------------


def test_ranking_overlap_edge_cases():
    assert ranking_overlap([], [], 5) == 1.0
    assert ranking_overlap(["a"], [], 5) == 0.0
    assert ranking_overlap([], ["a"], 5) == 0.0
    assert ranking_overlap(["a"], ["a"], 0) == 1.0
    assert ranking_overlap(["a", "b", "c"], ["a", "x", "c"], 3) == pytest.approx(2 / 3)
    assert ranking_overlap(["a", "b"], ["c", "d"], 2) == 0.0
    # k larger than the rankings: comparisons happen over what exists
    assert ranking_overlap(["a"], ["a", "b"], 5) == pytest.approx(1 / 5)


# ------------------------------------------------------------------
# AdaptiveTuner
# ------------------------------------------------------------------


def _clustered_entries() -> dict[str, str]:
    entries = {}
    for i in range(4):
        entries[f"a_{i}"] = f"olx login success proxy resi-1 delay 5 attempt {i}"
    for i in range(4):
        entries[f"b_{i}"] = f"rozetka collect failure http 503 timeout page {i}"
    return entries


def test_tuner_validation():
    vec = HashingVectorizer(dim=512)
    with pytest.raises(ValueError):
        AdaptiveTuner(vec, min_overlap=-0.1)
    with pytest.raises(ValueError):
        AdaptiveTuner(vec, min_overlap=1.1)
    with pytest.raises(ValueError):
        AdaptiveTuner(vec, top_k=0)
    with pytest.raises(ValueError):
        AdaptiveTuner(vec, dims=(0,))


def test_tuner_evaluate_structure():
    vec = HashingVectorizer(dim=512)
    tuner = AdaptiveTuner(vec, dims=(16, 32), top_k=3)
    scores = tuner.evaluate(_clustered_entries(), probes=4)
    assert set(scores) == {16, 32}
    for value in scores.values():
        assert 0.0 <= value <= 1.0


def test_tuner_deterministic():
    entries = _clustered_entries()
    vec = HashingVectorizer(dim=512)
    a = AdaptiveTuner(vec, dims=(16, 32), top_k=3)
    b = AdaptiveTuner(HashingVectorizer(dim=512), dims=(16, 32), top_k=3)
    assert a.evaluate(entries, probes=4) == b.evaluate(entries, probes=4)


def test_tuner_select_respects_min_overlap_rule():
    entries = _clustered_entries()
    vec = HashingVectorizer(dim=512)
    dims = (16, 32, 64)
    # min_overlap=0.0 → smallest dim always qualifies
    relaxed = AdaptiveTuner(vec, dims=dims, min_overlap=0.0, top_k=3)
    assert relaxed.select(entries, probes=4)["selected_dim"] == 16

    # If some dim scores below 1.0, an unattainable threshold must fall
    # back to the LARGEST dim (quality before savings).
    probe = AdaptiveTuner(vec, dims=dims, min_overlap=0.0, top_k=3)
    scores = probe.evaluate(entries, probes=4)
    best = max(scores.values())
    if best < 1.0:
        strict = AdaptiveTuner(vec, dims=dims, min_overlap=best + 1e-9, top_k=3)
        assert strict.select(entries, probes=4)["selected_dim"] == dims[-1]
    else:
        perfect = AdaptiveTuner(vec, dims=dims, min_overlap=1.0, top_k=3)
        assert perfect.select(entries, probes=4)["selected_dim"] == dims[0]


def test_tuner_empty_and_single_entry():
    vec = HashingVectorizer(dim=512)
    tuner = AdaptiveTuner(vec, dims=(16, 64))
    assert tuner.evaluate({}) == {16: 1.0, 64: 1.0}
    assert tuner.evaluate({"only": "single entry"}) == {16: 1.0, 64: 1.0}
    # Perfect scores on trivial corpora → smallest dim selected
    assert tuner.select({}, probes=4)["selected_dim"] == 16


# ------------------------------------------------------------------
# AgentMemorySystem integration
# ------------------------------------------------------------------


def _populated_system(n: int = 8) -> AgentMemorySystem:
    system = AgentMemorySystem()
    for i in range(n // 2):
        system.record(
            "olx", "login", "success", memory_type=MemoryType.LONG_TERM, context={"proxy": f"resi-{i}", "delay_s": 5}
        )
    for i in range(n // 2):
        system.record(
            "rozetka", "collect", "failure", memory_type=MemoryType.LONG_TERM, context={"code": 503, "page": i}
        )
    return system


def test_optimize_storage_adaptive_report():
    system = _populated_system()
    report = system.optimize_storage_adaptive(min_overlap=0.6, top_k=3, dims=[16, 32, 64])
    adaptive = report["adaptive"]
    assert adaptive["selected_dim"] in (16, 32, 64)
    assert set(adaptive["scores"]) == {"16", "32", "64"}
    # The index was actually built AT the selected dim
    assert report["target_dim"] == adaptive["selected_dim"]
    # Adaptive block persists in compression_stats()
    persisted = system.compression_stats()
    assert persisted["adaptive"]["selected_dim"] == adaptive["selected_dim"]
    assert persisted["target_dim"] == adaptive["selected_dim"]


def test_optimize_storage_adaptive_empty_memory():
    system = AgentMemorySystem()
    report = system.optimize_storage_adaptive()
    assert report["adaptive"]["skipped"] == "not_enough_entries"
    assert report["adaptive"]["selected_dim"] == 64
    assert report["entries_compressed"] == 0


def test_dim_change_rebuilds_compressor():
    system = _populated_system()
    system.optimize_storage(target_dim=64)
    sample = next(iter(system._compressed.values()))
    assert system._compressor.target_dim == 64
    assert sample.dims == 64

    system.optimize_storage(target_dim=128)
    sample = next(iter(system._compressed.values()))
    assert system._compressor.target_dim == 128
    assert sample.dims == 128
    # Recall still coherent after the dim switch
    recalled = system.recall_compressed("olx login success", top_k=2)
    assert recalled and all(e.platform == "olx" for e in recalled)


def test_recall_quality_after_adaptive_optimize():
    system = _populated_system()
    system.optimize_storage_adaptive(min_overlap=0.5, top_k=3)
    recalled = system.recall_compressed("rozetka collect failure 503", top_k=3)
    assert recalled
    assert recalled[0].platform == "rozetka"  # top-1 survives compression
    platforms = {e.platform for e in recalled}
    assert "rozetka" in platforms
