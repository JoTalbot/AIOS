# AIOS v11.7.0 — Release Notes

**Date:** 2026-07-29 · **Tests:** ~4129, 0 failures · **Ruff:** 0 errors, format clean

## Highlights

### 🎛️ Scheduling Policies

The energy-aware scheduler graduated from a single objective to four
selectable policies (`EnergyAwareScheduler(..., policy=…)`, overridable per
`plan()` / `dispatch()` call and via the API):

| Policy | Selection rule |
|---|---|
| `min_energy` (default) | cheapest expected energy among feasible candidates |
| `min_latency` | fastest health-normalized latency |
| `balanced` | weighted blend of normalized energy and latency (`balanced_weights`) |
| `ai_optimized` | **argmax of learned Q-values** from the engine's AI manager |

```python
scheduler.plan({"category": "inference"}, policy="min_latency")
scheduler.dispatch({"category": "learn"}, policy="ai_optimized")
```

Dispatches record `scheduling_policy`; `report()` exposes the default
`policy` and per-policy `policy_dispatches`. `POST /api/substrate/schedule`
accepts `"policy"` (rejecting unknown names with 400), and the dry-run form
on `/substrate` has a policy selector.

### 🧠 AI-Manager Wiring (Q-learning finally routes tasks)

Since v11.1 the engine computed `predict_best_substrate(...)` and discarded
it (`pass` — a dead hook, and a random-exploration one at that). v11.7.0
replaces it with a controlled deterministic path: the `ai_optimized`
policy reads the Q-table the `SubstrateAIManager` maintains — and it is
already learning: `update_q_value` runs automatically after every engine
execution. Cold table? All zeros → clean min-energy tie-break, with the
selected `ai_q_value` surfaced in the plan for transparency.

### 📊 Dispatch Analytics

`SubstrateConvergenceEngine.analytics(limit=None)` aggregates the dispatch
history: per-substrate counts, energy sums, average estimated latency and
energy share %. Served via `GET /api/substrate/analytics?limit=` and
visualized on `/substrate` as a per-substrate bar panel refreshed with the
rest of the live data.

## Compatibility

- `min_energy` remains the default; existing plan/dispatch results are
  unchanged (reports only gain keys).
- No new dependencies.

## Tests

16 new: `test_scheduler_policies.py` (11: policy validation, per-policy
selections incl. contrast substrate, balanced extremes, cold/warm Q-table,
learning loop, API) and `test_substrate_analytics.py` (5).
Full suite: **~4129 passed, 0 failed**; `ruff check` + `ruff format --check`
clean; `mkdocs build --strict` clean.
