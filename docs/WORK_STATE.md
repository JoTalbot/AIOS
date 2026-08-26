# AIOS vNext — Current Work State

## STOP / RESUME POINT

**Status:** paused at the persistence/recovery boundary.

**Current main:** `e4fae49` (work-state marker; verify `main` before continuing)

### Completed
- API endpoint/runtime adapter wiring started.
- API → Runtime → Orchestrator → Scheduler → Execution path has regression coverage.
- Execution checkpoint lifecycle and duplicate-execution protection were implemented.
- Recovery checks persistent terminal results before restoring stale checkpoints.
- Work-state marker is committed in this file so another agent can resume from this exact boundary.

### Exact next task
Unify `CheckpointStore` and `ExecutionStore` behind one execution lifecycle/source of truth.

### Required invariants
1. A terminal execution result is persisted before a response is returned.
2. Restart must never execute a task again when its terminal result already exists.
3. A stale resumable checkpoint must not override a terminal result.
4. Checkpoint cleanup must be idempotent.
5. Recovery, persistence, and scheduler state must agree on the same task lifecycle.
6. Add an end-to-end crash/restart regression test before moving on.

### Reference files
- `execution/checkpoint.py` — resumable checkpoint contract.
- `execution/persistence.py` — execution result persistence boundary.
- `kernel/checkpoint_recovery.py` — restart/recovery boundary.
- `kernel/scheduler.py` — task execution and checkpoint lifecycle.
- `docs/ARCHITECTURE.md` — canonical runtime architecture.

### Rule for the next agent
Do not create a second persistence source of truth. First inspect the current `main` versions of the reference files, then make the smallest compatible integration and add regression coverage. Preserve parallel-agent changes; never force-push or overwrite unrelated work.
