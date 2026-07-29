# AIOS v11.4.0 — Release Notes

**Date:** 2026-07-29 · **Tests:** ~4066, 0 failures · **Ruff:** 0 errors, format clean

## Highlights

### 🧠 Memory Deduplication Engine

New module `aios_core/memory_dedup.py` detects near-duplicate agent memories
using the compressed vector index introduced in v11.3.0 — no extra storage,
all comparisons happen in 64-dim uint8 space.

- `MemoryDeduplicator(threshold=0.92)` clusters memory ids whose pairwise
  cosine similarity meets the threshold (union-find; O(n²) over 80-byte
  vectors — fine at agent-memory scale).
- `AgentMemorySystem.find_duplicates(threshold, pool)` — read-only detection,
  returns groups sorted by size.
- `AgentMemorySystem.deduplicate(threshold, pool)` — merges each group into
  its strongest entry: the representative absorbs access counts and the best
  confidence of merged members; merged entries leave the pools and the
  compressed index.
- `AgentMemorySystem.dedup_stats()` + `stats()["dedup"]` — lifetime removal
  counter and the last report.

```python
from aios_core.agent_memory_system import AgentMemorySystem

mem = AgentMemorySystem()
mem.record("olx", "login", "success", context={"proxy": "a"})
mem.record("olx", "login", "success", context={"proxy": "a"})  # duplicate
mem.deduplicate()  # -> {"groups_found": 1, "entries_removed": 1, ...}
```

### ⚡ Energy-Aware Substrate Scheduler

New module `aios_core/substrate_energy_scheduler.py` adds an energy-first
routing policy on top of `SubstrateConvergenceEngine`:

- `EnergyAwareScheduler(engine, latency_budget_ms=None, energy_budget=None)`
- `candidates(task)` — active, healthy substrates with expected energy and
  health-normalized latency (affinity narrows the pool, mirroring the engine).
- `plan(task)` — dry-run decision: min-energy selection, the engine's own
  baseline choice, and expected savings.
- `dispatch(task)` — steers execution via `preferred_type`; on constraint
  violations (no substrate within the latency budget, rolling energy budget
  exceeded) degrades gracefully to engine routing (`policy="fallback"`).
- `RollingEnergyBudget(limit, window_seconds)` — sliding-window budget with
  `can_afford` / `record` / `remaining`.
- `report()` — dispatches, fallbacks, energy spent, energy saved vs the
  engine baseline, savings percentage.

New endpoint `POST /api/substrate/schedule`:

```bash
curl -X POST localhost:8888/api/substrate/schedule \
  -d '{"id": "task-1", "category": "signal", "compute_units": 2}'
# dry-run plan; add "execute": true to actually dispatch
```

### 📊 Live Agent Memory Dashboard

`/memory` is a live page (5-second polling) backed by a real shared
`AgentMemorySystem` singleton, demo-seeded on first creation:

- `GET /api/memory/stats` — pool counters, strengths, distribution, dedup
- `GET /api/memory/patterns` — extracted `SuccessPattern` objects
- `GET /api/memory/compression` — v11.3.0 compression report
- `GET /api/memory/duplicates?threshold=…` — near-duplicate groups
  (threshold clamped to (0.01, 1.0], non-numeric falls back to 0.92)

### 🔧 VPS Emulator Provisioning Fixed

`setup/android-emulator-env.sh` rewritten with the CI lessons from v11.3.0:

- system image actually installed by sdkmanager (was: empty `mkdir`)
- cmdline-tools unpacked to `cmdline-tools/latest` (was: ZIP downloaded over
  the `sdkmanager` binary path)
- ABI normalized to the `;` package-id form (slash form still accepted)
- `config.ini` append-only (overwrite wiped `abi.type` → QEMU errors)
- pipefail-safe license acceptance, best-effort KVM udev rule

## Compatibility

- All v11.3.0 APIs unchanged; `stats()` responses only gain new keys.
- Requires no new dependencies (numpy + starlette already required).

## Tests

36 new tests: `test_memory_dedup.py` (12), `test_substrate_energy_scheduler.py`
(18, incl. dashboard API), `test_memory_dashboard.py` (6).
Full suite: **~4066 passed, 0 failed**; `ruff check` and `ruff format --check`
both clean.
