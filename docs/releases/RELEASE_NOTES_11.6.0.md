# AIOS v11.6.0 — Release Notes

**Date:** 2026-07-29 · **Tests:** ~4113, 0 failures · **Ruff:** 0 errors, format clean

## Highlights

### 💾 Agent Memory Persistence

The agent memory system was purely in-memory since v10.3. v11.6.0 adds
versioned snapshots:

```python
mem.save("runtime/memory.json")  # atomic tmp+rename, dirs auto-created
report = mem.load("runtime/memory.json")  # replaces state, returns pool counts
```

- Full-fidelity serialisation: confidence, decay rate, created/last-accessed
  timestamps, access counts, priority, metadata (the lossy `to_dict()` shape
  is NOT reused for storage).
- The four pools (`short_term`, `long_term`, `episodic`, `archive`) plus
  extracted success patterns and the dedup removal counter all round-trip.
- Id-collision guard: the entry counter is raised past the largest restored
  `mem_N` id, so entries recorded after restore are always unique.
- `SNAPSHOT_FORMAT = 1` — incompatible future formats fail loudly
  (`ValueError: unsupported snapshot format`).
- The compressed vector index remains derived state: call
  `optimize_storage()` / `optimize_storage_adaptive()` after `load()`.

### 🔎 Memory Recall Search

New keyword search beside the v11.3 compressed-similarity recall:

```python
mem.search("rozetka 503", limit=10)  # token scoring, strength tie-break
mem.search("zzz-mark", pools="archive")  # cold storage is searchable too
```

API: `GET /api/memory/recall?q=…&mode=keyword|compressed&top_k=…`
(q required; top_k clamped 1–50; unknown modes → 400). The `/memory`
dashboard gains a **Recall Search** panel with live results.

### ♻️ Lifecycle Endpoints + Dashboard Panel

The memory lifecycle (record → consolidate → deduplicate → archive) is now
fully drivable over HTTP:

- `POST /api/memory/consolidate` — short/episodic → long-term insights
- `POST /api/memory/decay` — strength pruning (validated `min_strength`)
- `POST /api/memory/compression/optimize-adaptive` — adaptive-dim compression
  with optional `min_overlap` / `top_k` / `dims` / `probes`
- (`POST /api/memory/archive/run` from v11.5.0 completes the set)

The `/memory` page shows a **Memory Lifecycle** panel: one click per
operation, inline result feedback, auto-refresh.

## Bug Fix

`AgentMemorySystem.decay()` returned the number of memories that SURVIVED
the pruning, not the number removed — it counted the pools after filtering.
Existing tests only asserted `isinstance(result, int)`, so the wrong value
leaked all the way into the new lifecycle API. Now computed as
`before − after`.

## Compatibility

- Additive only; snapshot format versioned for future-proofing.
- No new dependencies (json / pathlib / re from the stdlib).

## Tests

24 new: `test_memory_persistence.py` (9), `test_memory_search.py` (7),
`test_memory_dashboard.py` (+8). Full suite: **~4113 passed, 0 failed**;
`ruff check` + `ruff format --check` clean; `mkdocs build --strict` clean.
