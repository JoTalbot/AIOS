# AIOS vNext — Current Work State

## STOP / RESUME POINT

**Status:** crash/restart recovery boundary now covered; ready for the next lifecycle integration batch.

**Current main marker:** `8bc3849`

### Completed
- API → Runtime → Orchestrator → Scheduler → Execution regression coverage.
- Execution terminal results are persisted before response return.
- Duplicate execution is prevented by persisted terminal results.
- `CheckpointStore` is a compatibility facade over canonical `ExecutionStore`.
- Checkpoints and terminal results share one lifecycle store.
- Recovery skips tasks whose terminal result already exists.
- Added crash/restart regression coverage: checkpoint → recovery → terminal result → second recovery does not enqueue again.

### Exact next task
Wire the recovered task through the **real Scheduler execution loop** and prove the full crash/restart path with an actual `ExecutionCoordinator`, not only the recovery boundary test.

### Required invariants
1. Terminal result is persisted before response.
2. Restart never executes a task again when terminal result exists.
3. Stale checkpoint never overrides terminal state.
4. Checkpoint cleanup is idempotent.
5. Recovery and Scheduler share the same lifecycle state.
6. A recovered task executes exactly once after restart.
7. A completed task can be replayed as a stored result without invoking the agent/tool again.

### Reference files
- `execution/checkpoint.py`
- `execution/persistence.py`
- `execution/coordinator.py`
- `kernel/checkpoint_recovery.py`
- `kernel/scheduler.py`
- `docs/ARCHITECTURE.md`

### Rule for the next agent
Start by inspecting the current `main` versions. Do not introduce another persistence store. Preserve parallel-agent changes and never force-push.
