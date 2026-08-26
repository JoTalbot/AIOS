# AIOS vNext — Current Work State

## STOP / RESUME POINT

**Status:** scheduler terminal-persistence/restart boundary covered; ready to integrate real `ExecutionCoordinator` into the recovered Scheduler path.

**Current main marker:** `89d2f12` (latest work-state update should be verified against `main` before continuing)

### Completed
- API → Runtime → Orchestrator → Scheduler → Execution regression coverage.
- Execution terminal results are persisted before response return.
- Duplicate execution is prevented by persisted terminal results.
- `CheckpointStore` is a compatibility facade over canonical `ExecutionStore`.
- Checkpoints and terminal results share one lifecycle store.
- Recovery skips tasks whose terminal result already exists.
- Scheduler now checks persisted terminal results before enqueue/execution.
- Scheduler persists successful terminal results before checkpoint cleanup.
- Added restart regression coverage proving a second Scheduler does not invoke the executor again.

### Exact next task
Wire a recovered task through the **real Scheduler execution loop with `ExecutionCoordinator`**, including an actual interrupted/restart scenario. Prove: checkpoint → restart → recovery → exactly-once continuation → terminal persistence → replay without agent/tool invocation.

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
